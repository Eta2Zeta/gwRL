"""Independent original validateRoute oracle over genuine map/catalog inputs."""
from dataclasses import replace
import copy
import json
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.resident_routes import ResidentRoutes,TensorRouteRequests,MODES
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.curriculum import make_env

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()


@unittest.skipUnless(EXACT_MPS,"Exact Apple MPS state unavailable; use tmp/gpu-mps-env/bin/python")
class CampaignResidentRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
        cls.base=make_env(1951,calendar_rounds=3).raw
        cls.template=json.loads(cls.base.serialize())
        cls.native=gwrl_cpp.campaign_movement_context(cls.base)
        cls.context=DeviceStateContext(gwrl_cpp.device_state_context(cls.base),"mps")
        cls.kernel=ResidentRoutes(cls.context,cls.native)
        cls.zones=tuple(cls.native.zones);cls.zindex={name:i for i,name in enumerate(cls.zones)}
        cls.nodes=np.asarray(cls.native.node_array());cls.edges=np.asarray(cls.native.edge_array())
        cls.nt=np.asarray(cls.native.node_terrain_array());cls.bt=np.asarray(cls.native.border_terrain_array())
        restricted=np.array([x in {"mountain","desert","jungle","marsh","tundra","ice","tundra_ice"} for x in cls.native.terrains])
        cls.stops=np.any((cls.nt[np.newaxis,:,:]|cls.bt).astype(bool)&restricted,axis=2)
        cls.land=[i for i,row in enumerate(cls.nodes) if row[0]]
        cls.pairs=[(a,b) for a in cls.land for b in cls.land if cls.edges[a,b,0] and cls.edges[a,b,1]]
        cls.normal=next((a,b) for a,b in cls.pairs if not cls.edges[a,b,4] and not cls.stops[a,b])
        cls.rail=next((a,b) for a,b in cls.pairs if cls.edges[a,b,2] and not cls.edges[a,b,3] and not cls.edges[a,b,4])
        cls.narrow=next((a,b) for a,b in cls.pairs if cls.edges[a,b,4] and
            np.any(np.asarray(cls.native.crossing_sea_array())[a,b]) and not np.asarray(cls.native.crossing_missing_array())[a,b,0])
        cls.unit_template=copy.deepcopy(next(iter(cls.template["state"]["units"].values())))

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads);torch.mps.empty_cache()

    def fixture(self,phase="non_combat_movement",*,units=None,enemy=None,tech=True,mutate=None):
        value=copy.deepcopy(self.template);s=value["state"]
        for field in ("units","facilities","rails","construction","repairs","battles","flags"):s[field]={}
        s["decisions"]=[];s["battle_order"]=[];s["chance"]=None;s["history"]=[];s["action_interface"]={}
        s["clock"].update(round_index=0,completed_rounds=0,nation_index=2,player_turn_serial="2",phase=phase,income_collected=False)
        s["completed_turns"]={"ccp":1,"mongolia":1,"japan":0,"kmt":0};s["terminal"]=False
        s["politics"]["pending"]={};s["politics"]["surrendered"]=[]
        s["politics"]["chinese_truce"]=False;s["politics"]["truce_permanently_ended"]=False
        for nation in s["nations"].values():nation["turn_flags"]={};nation["at_war_with"]=[]
        s["nations"]["japan"]["at_war_with"]=["kmt"];s["nations"]["kmt"]["at_war_with"]=["japan"]
        s["nations"]["japan"]["technology_stages"]["improved_logistics"]=4 if tech else 0
        for zone,territory in s["territories"].items():territory["possessor"]="kmt" if zone==enemy else "japan";territory["flags"]={}
        for identity,kind,zone,movement in (units or [("u","infantry",self.zones[self.normal[0]],3)]):
            unit=copy.deepcopy(self.unit_template)
            unit.update(id=identity,type=kind,owner="japan",zone=zone,turn_origin=zone,movement_remaining=movement,
                movement_allowance=max(3,movement),route=[],carried_by=None,cargo=[],damage=0,commitments=[],turn_flags={},game_flags={})
            s["units"][identity]=unit
        s["turn_start"]={"possessions":{z:t["possessor"] for z,t in s["territories"].items()},
                         "units":{u:[x["owner"],x["zone"]] for u,x in s["units"].items()}}
        if mutate:mutate(s)
        env=make_env(1951,calendar_rounds=3).raw;env.restore(json.dumps(value));return env

    def check(self,envs,requests,*,no_host=False):
        before=[env.serialize() for env in envs]
        resident=DeviceStateBatch.capture(envs,context=self.context)
        resident_before={name:getattr(resident,name).clone() for name in
            ("records","lengths","sections","errors","string_bytes","string_offsets","suffix_usage")}
        packed=self.kernel.pack_requests(resident,requests)
        oracle=gwrl_cpp.campaign_route_oracle(self.native,envs,[gwrl_cpp.CampaignMovementQuery(r.get("lane",0),r["unit"],r["path"],
            r.get("mode","ordinary"),r.get("combat",False),r.get("towed")) for r in requests])
        if no_host:
            with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("hot CPU copy")), \
                 patch.object(torch.Tensor,"tolist",side_effect=AssertionError("hot list conversion")), \
                 patch.object(torch.Tensor,"item",side_effect=AssertionError("hot scalar")), \
                 patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("hot scalar condition")), \
                 patch.object(gwrl_cpp,"campaign_route_oracle",side_effect=AssertionError("CPU legality fallback")):
                result=self.kernel.query(resident,packed)
                reused=self.kernel.prepare(resident)
                self.assertIs(reused,self.kernel.prepare(resident))
        else:result=self.kernel.query(resident,packed)
        actual=self.kernel.inspect(result)
        for index,(got,expected) in enumerate(zip(actual,oracle,strict=True)):
            with self.subTest(request=requests[index]):
                self.assertTrue(got["supported"],got)
                self.assertEqual({k:v for k,v in got.items() if k!="supported"},dict(expected))
        self.assertEqual([env.serialize() for env in envs],before,"Route queries must preserve state/history/every RNG stream")
        for name,previous in resident_before.items():self.assertTrue(torch.equal(getattr(resident,name),previous),name)
        return actual,resident,packed,result

    def test_all_real_directed_land_edges_all_five_modes_match_every_field(self):
        units=[(f"unit_{i}","light_armor",self.zones[i],3) for i in self.land]
        normal=self.fixture(units=units)
        combat=self.fixture("combat_movement",units=units)
        blitz=self.fixture("combat",units=units,mutate=lambda s:[u["turn_flags"].update(blitz_eligible=1) for u in s["units"].values()])
        requests=[]
        for a,b in self.pairs:
            for mode,lane,attack in (("ordinary",0,False),("ordinary",1,True),("blitz",2,True),
                                      ("strategic_rail",0,False),("strategic_river",0,False),("narrow_crossing",0,False)):
                requests.append(dict(lane=lane,unit=f"unit_{a}",path=[self.zones[a],self.zones[b]],mode=mode,combat=attack))
        actual,*_=self.check([normal,combat,blitz],requests)
        self.assertTrue(any(row["allowed"] for row in actual))
        self.assertTrue(any(row["allowed"] and row["regions"] for row in actual),"Real rail/river successes must be exercised")

    def test_unit_phase_unloading_and_pending_battle_restrictions(self):
        a,b=map(self.zones.__getitem__,self.normal)
        mutations=[lambda s:s["units"]["u"].update(owner="kmt"),
            lambda s:s["units"]["u"]["turn_flags"].update(naval_unloaded=1),
            lambda s:s["units"]["u"]["turn_flags"].update(air_transport_unloaded=1),
            lambda s:s["units"]["u"].update(commitments=["transport_unloaded"]),
            lambda s:s["units"]["u"]["game_flags"].update(port_unloaded_round=1),
            lambda s:s["units"]["u"]["turn_flags"].update(repairing=1),
            lambda s:s["units"]["u"].update(commitments=["repair"]),
            lambda s:s["units"]["u"].update(commitments=["attrition"]),
            lambda s:s["units"]["u"]["turn_flags"].update(placed_this_turn=1),
            lambda s:s["units"]["u"].update(commitments=["combat_move"]),
            lambda s:s["units"]["u"].update(movement_remaining=0),
            lambda s:(s["units"].update(carrier={**copy.deepcopy(s["units"]["u"]),"id":"carrier","cargo":["u"]}),s["units"]["u"].update(carried_by="carrier")),
            lambda s:s["battles"].update(test={"id":"test","zone":a,"attacker":"japan","defender":"kmt","stage":"route_test",
                "attackers":["u"],"defenders":[],"pending_hits":{},"flags":{},"data":{}})]
        envs=[self.fixture(mutate=fn) for fn in mutations]
        actual,*_=self.check(envs,[dict(lane=i,unit="u",path=[a,b]) for i in range(len(envs))])
        self.assertTrue(all(not row["allowed"] for row in actual))
        self.assertEqual(actual[-1]["reason"],"Unit is committed to an unresolved battle")

    def test_partial_cost_approach_terrain_and_cavalry_exemption(self):
        mountain=list(self.native.terrains).index("mountain")
        first_stop=next((a,b,c) for a,b in self.pairs for x,c in self.pairs if x==b and c!=a and
            not self.edges[a,b,4] and not self.edges[b,c,4] and self.stops[a,b] and not self.stops[b,c] and
            int(np.sum(self.nt[b]|self.bt[a,b]))==1 and (self.nt[b,mountain] or self.bt[a,b,mountain]))
        a,b,c=map(self.zones.__getitem__,first_stop)
        env=self.fixture(units=[("foot","infantry",a,3),("horse","cavalry",a,3)])
        actual,*_=self.check([env],[dict(unit="foot",path=[a,b,c]),dict(unit="horse",path=[a,b,c])])
        self.assertEqual(actual[0]["reason"],"Terrain ends movement immediately")
        self.assertEqual(actual[0]["cost"],0);self.assertTrue(actual[0]["exhausts_movement"])
        self.assertTrue(actual[1]["allowed"])
        chain=next((a,b,c) for a,b in self.pairs for x,c in self.pairs if x==b and c!=a and
            not self.edges[a,b,4] and not self.edges[b,c,4] and not self.stops[a,b] and self.stops[b,c])
        a,b,c=map(self.zones.__getitem__,chain)
        actual,*_=self.check([self.fixture(units=[("u","infantry",a,1)])],[dict(unit="u",path=[a,b,c])])
        self.assertEqual(actual[0]["reason"],"Insufficient movement points");self.assertEqual(actual[0]["cost"],2)
        self.assertEqual(actual[0]["approach"]["to"],b)

    def test_narrow_crossing_classes_screens_and_capacity(self):
        ai,bi=self.narrow;a,b=self.zones[ai],self.zones[bi]
        sea=next(self.zones[z] for z,x in enumerate(np.asarray(self.native.crossing_sea_array())[ai,bi]) if x)
        sea_unit=("screen","destroyer",sea,3)
        envs=[self.fixture(units=[("u","infantry",a,3)]),self.fixture("combat_movement",units=[("u","marine",a,3)]),
            self.fixture("combat_movement",units=[("u","infantry",a,3)]),
            self.fixture(units=[("u","infantry",a,3),sea_unit],mutate=lambda s:s["units"]["screen"].update(owner="kmt"))]
        counter=int(np.asarray(self.native.crossing_counter_array())[ai,bi]);offsets=list(self.native.counter_offsets())
        raw=bytes(self.native.counter_bytes());key=raw[offsets[counter]:offsets[counter+1]].decode()
        envs.append(self.fixture(units=[("u","infantry",a,3)],mutate=lambda s:s["flags"].update({key:100})))
        actual,*_=self.check(envs,[dict(lane=i,unit="u",path=[a,b],mode="narrow_crossing",combat=i in (1,2)) for i in range(len(envs))])
        self.assertTrue(actual[0]["allowed"]);self.assertTrue(actual[1]["allowed"])
        self.assertEqual(actual[2]["reason"],"Only Marines attack; infantry-class units may noncombat cross")
        self.assertEqual(actual[3]["reason"],"Enemy units prevent the narrow crossing")
        self.assertEqual(actual[4]["reason"],"Narrow crossing capacity exhausted")

    def test_towing_pairs_and_unescorted_continuation(self):
        a,b=map(self.zones.__getitem__,self.normal)
        units=[("motor","motorized_infantry",a,3),("gun","artillery",a,1)]
        envs=[self.fixture(units=units),self.fixture(units=units,mutate=lambda s:s["units"]["gun"].update(commitments=["attrition"])),
            self.fixture(units=units,mutate=lambda s:s["units"]["gun"].update(commitments=["towed_by:motor"]))]
        requests=[dict(lane=0,unit="motor",path=[a,b],towed="gun"),dict(lane=1,unit="motor",path=[a,b],towed="gun"),
                  dict(lane=2,unit="gun",path=[a,b]),dict(lane=0,unit="motor",path=[a,b],towed="unknown")]
        actual,*_=self.check(envs,requests)
        self.assertTrue(actual[0]["allowed"]);self.assertEqual(actual[1]["reason"],"Artillery used an attrition attack this turn")
        self.assertEqual(actual[2]["reason"],"Towed artillery must continue with its motorized partner")

    def test_rail_damage_regions_counter_and_built_nonadjacent_exception(self):
        a,b=map(self.zones.__getitem__,self.rail)
        units=[("u","infantry",a,3)]
        damaged=self.fixture(units=units,mutate=lambda s:s["rails"].update(test={"id":"test","endpoint_a":a,"endpoint_b":b,"damage_by_endpoint":{a:1}}))
        region_index=int(self.nodes[self.zindex[a],2]);region=self.native.regions[region_index]
        used=self.fixture(units=units,mutate=lambda s:s["nations"]["japan"]["turn_flags"].update({"rail_used:axis:"+region:100}))
        actual,*_=self.check([self.fixture(units=units),damaged,used],[dict(lane=i,unit="u",path=[a,b],mode="strategic_rail") for i in range(3)])
        self.assertTrue(actual[0]["allowed"])
        self.assertEqual(actual[1]["reason"],"No undamaged railroad or usable river")
        self.assertEqual(actual[2]["reason"],"Regional rail capacity exhausted")
        ai,bi=next((a,b) for a in self.land for b in self.land if a!=b and not self.edges[a,b,0] and
            not self.nodes[b,5] and not ("impassable" in self.native.terrains and self.nt[b,list(self.native.terrains).index("impassable")]))
        a,b=self.zones[ai],self.zones[bi]
        env=self.fixture(units=[("u","infantry",a,3)],mutate=lambda s:s["rails"].update(test={"id":"test","endpoint_a":a,"endpoint_b":b,"damage_by_endpoint":{}}))
        actual,*_=self.check([env],[dict(unit="u",path=[a,b])])
        self.assertEqual(actual[0]["exception"],2);self.assertEqual(actual[0]["message"],"Nonadjacent approach edge")

    def test_possession_changes_directed_hostility_control_and_truce(self):
        a,b=map(self.zones.__getitem__,self.normal)
        envs=[self.fixture(mutate=lambda s:s["territories"][b]["flags"].update(last_possession_change_turn=2)),
              self.fixture(mutate=lambda s:s["turn_start"]["possessions"].update({b:"kmt"})),
              self.fixture("combat_movement",enemy=b),
              self.fixture("combat_movement",enemy=b,mutate=lambda s:s["nations"]["japan"].update(at_war_with=[])),
              self.fixture(mutate=lambda s:(s["units"]["u"].update(commitments=["combat_move"]),
                  s["units"]["u"]["turn_flags"].update(must_withdraw_from_chinese_gift=1)))]
        requests=[dict(lane=i,unit="u",path=[a,b],combat=i in (2,3)) for i in range(len(envs))]
        actual,*_=self.check(envs,requests)
        self.assertEqual(actual[0]["reason"],"Cannot enter land captured this turn")
        self.assertEqual(actual[1]["reason"],"Cannot enter land captured this turn")
        self.assertTrue(actual[2]["allowed"]);self.assertTrue(actual[4]["allowed"])
        minor=next(name for name in self.template["state"]["nations"] if name.startswith("warlord_"))
        def controlled(s):
            s["units"]["u"]["owner"]=minor
            s["nations"][minor].update(controller_nation="japan",player=None,at_war_with=[])
            s["territories"][a]["possessor"]=minor;s["turn_start"]["possessions"][a]=minor
            s["nations"]["japan"]["turn_flags"]["rail_permission:"+minor]=1
        env=self.fixture("combat_movement",enemy=b,mutate=controlled)
        rows,*_=self.check([env],[dict(unit="u",path=[a,b],combat=True)])
        self.assertEqual(rows[0]["reason"],"Land access is prohibited","A controlled minor cannot inherit its controller's war")
        def truce(s):
            s["clock"].update(nation_index=0,player_turn_serial="0")
            s["completed_turns"]={"ccp":0,"mongolia":0,"japan":0,"kmt":0}
            s["units"]["u"]["owner"]="ccp";s["politics"]["chinese_truce"]=True
            s["territories"][b]["possessor"]="kmt";s["turn_start"]["possessions"][b]="kmt"
        rows,*_=self.check([self.fixture(mutate=truce)],[dict(unit="u",path=[a,b])])
        self.assertTrue(rows[0]["allowed"])

    def test_narrow_patrol_submergence_and_coastal_artillery(self):
        ai,bi=self.narrow;a,b=self.zones[ai],self.zones[bi]
        sea=next(self.zones[z] for z,x in enumerate(np.asarray(self.native.crossing_sea_array())[ai,bi]) if x)
        def screen(kind,*,turn=None,commitments=None):
            return self.fixture(units=[("u","infantry",a,3),("screen",kind,sea,3)],mutate=lambda s:
                s["units"]["screen"].update(owner="kmt",turn_flags=turn or {},commitments=commitments or []))
        envs=[screen("submarine"),screen("submarine",turn={"submerged":1}),
              screen("fighter",commitments=["maritime_air_patrol"]),screen("fighter",turn={"on_map":1}),
              screen("fighter")]
        envs.append(self.fixture("combat_movement",units=[("u","marine",a,3)],mutate=lambda s:
            s["facilities"].update(coast={"id":"coast","type":"coastal_artillery","zone":b,"damage":0,"flags":{}})))
        actual,*_=self.check(envs,[dict(lane=i,unit="u",path=[a,b],mode="narrow_crossing",combat=i==5) for i in range(len(envs))])
        self.assertEqual([row["allowed"] for row in actual],[False,True,False,False,True,False])

    def test_successful_blitz_companion_order_and_fortification(self):
        ai,bi=next((a,b) for a,b in self.pairs if not self.edges[a,b,4] and not self.stops[a,b] and
            not self.stops[a,a] and not self.nodes[a,1] and not self.nodes[b,1])
        a,b=self.zones[ai],self.zones[bi]
        def eligible(s):s["units"]["u"]["turn_flags"]["blitz_eligible"]=1
        armor=self.fixture("combat",units=[("u","light_armor",a,3)],enemy=b,mutate=eligible)
        def paired(s):
            eligible(s);s["units"]["u"]["commitments"]=["blitz_with:armor"]
            s["units"]["armor"]["commitments"]=["blitz_from:"+a,"blitz_to:"+b]
        companion=self.fixture("combat",units=[("u","infantry",a,3),("armor","light_armor",b,3)],enemy=b,mutate=paired)
        def first_wrong(s):paired(s);s["units"]["u"]["commitments"].append("blitz_with:0missing")
        wrong=self.fixture("combat",units=[("u","infantry",a,3),("armor","light_armor",b,3)],enemy=b,mutate=first_wrong)
        def fortification(s):
            eligible(s);s["facilities"]["fort"]={"id":"fort","type":"fortification","zone":b,"damage":0,"flags":{"border:"+a:1}}
        fort=self.fixture("combat",units=[("u","light_armor",a,3)],enemy=b,mutate=fortification)
        actual,*_=self.check([armor,companion,wrong,fort],[dict(lane=i,unit="u",path=[a,b],mode="blitz",combat=True) for i in range(4)])
        self.assertTrue(actual[0]["allowed"]);self.assertTrue(actual[1]["allowed"])
        self.assertEqual(actual[2]["reason"],"Blitz companion must follow its paired armor to the same target")
        self.assertEqual(actual[3]["reason"],"Terrain, city or fortification prohibits blitzing")

    def test_complete_catalog_classes_ordinary_and_strategic_routes(self):
        a,b=map(self.zones.__getitem__,self.rail)
        # Every catalog type is retained, including aircraft, rockets and ships.
        units=[("type_"+str(i),kind,a,3) for i,kind in enumerate(self.native.unit_types)]
        env=self.fixture(units=units)
        requests=[dict(unit=identity,path=[a,b],mode=mode) for identity,_,_,_ in units
                  for mode in ("ordinary","strategic_rail","strategic_river","narrow_crossing")]
        actual,*_=self.check([env],requests)
        self.assertEqual(len(actual),4*len(self.native.unit_types))
        self.assertTrue(any(row["allowed"] for row in actual))
        self.assertTrue(any(row["reason"]=="Ordinary land movement requires a land unit" for row in actual))
        self.assertTrue(any(row["reason"]=="Unit cannot use strategic rail" for row in actual))

    def test_rail_failure_reports_recursive_controller_and_temporary_player_errors(self):
        a,b=map(self.zones.__getitem__,self.rail);units=[("u","infantry",a,3)]
        neutral=next(name for name,nation in self.template["state"]["nations"].items() if nation["player"] is None and nation["controller_nation"] is None)
        def setup(s):s["nations"]["japan"].update(player=None,controller_nation=neutral)
        def temporary(value):
            def apply(s):setup(s);s["politics"]["pending"]["warlord_defense_player:"+neutral]=value
            return apply
        envs=[self.fixture(units=units,mutate=setup),self.fixture(units=units,mutate=temporary("unknown-player")),
              self.fixture(units=units,mutate=temporary(7))]
        actual,*_=self.check(envs,[dict(lane=i,unit="u",path=[a,b],mode="strategic_rail") for i in range(3)])
        self.assertTrue(all(row["exception"]==2 for row in actual))
        self.assertEqual(actual[0]["message"],"Political nation has no controlling player: "+neutral)
        self.assertEqual(actual[1]["message"],"Invalid temporary warlord defense player")
        self.assertEqual(actual[2]["message"],"JSON value is not a string")

    def test_hot_queries_no_host_reads_cache_reuse_and_stale_source_rejected(self):
        a,b=map(self.zones.__getitem__,self.normal)
        _,resident,packed,_=self.check([self.fixture()],[dict(unit="u",path=[a,b]),dict(unit="missing",path=[a,b])],no_host=True)
        prepared=self.kernel.prepare(resident)
        with self.assertRaises(ValueError):self.kernel.query(resident.snapshot(),packed,prepared=prepared)
        invalid=replace(packed,metadata=packed.metadata.float())
        with self.assertRaises(ValueError):self.kernel.query(resident,invalid)
        bad=packed.metadata.clone();bad[0,0]=-1
        result=self.kernel.query(resident,replace(packed,metadata=bad))
        self.assertEqual(result.errors.cpu().tolist()[0],4);self.assertEqual(result.supported.cpu().tolist()[0],0)
        empty=self.kernel.query(resident,self.kernel.pack_requests(resident,[]))
        self.assertEqual(tuple(empty.core.shape),(0,12))


class CampaignRouteBoundaryTests(unittest.TestCase):
    def test_explicit_cpu_does_not_silently_execute_a_gpu_route(self):
        raw=make_env(7,calendar_rounds=3).raw
        context=DeviceStateContext(gwrl_cpp.device_state_context(raw),"cpu")
        with self.assertRaisesRegex(ValueError,"explicit Apple MPS"):
            ResidentRoutes(context,gwrl_cpp.campaign_movement_context(raw))


if __name__=="__main__":unittest.main()
