"""Original political queue/evolution helpers and every raw resident State bit."""
from dataclasses import replace
import copy
import json
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import gwrl_cpp
import numpy as np
import torch

from studies.campaign.backends.device_state import DeviceStateBatch,DeviceStateContext
from studies.campaign.backends.device_strings import pack_byte_requests,intern_bytes
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported
from studies.campaign.backends.resident_events import EventPayloads
from studies.campaign.backends.resident_political_decisions import PoliticalDecisionOptions,ResidentPoliticalDecisionQueue
from studies.campaign.backends.resident_evolution_choices import ResidentEvolutionChoice
from tests import test_campaign_resident_political_unit_creation as creation_tests
from tools.benchmark_campaign_resident_recruitment_chance import canonical_native,require_exact

EXACT=torch.backends.mps.is_available() and mps_int64_indexing_supported()


def option(name="preserved_id",*,decision=None,parameters=None,**changes):
    result=dict(id=name,kind="opaque_kind",player="axis",nation="japan",decision=decision,
                parameters={} if parameters is None else parameters)
    result.update(changes);return result


def fixture(sequence=None,mutate=None):
    return creation_tests.fixture(sequence=sequence,mutate=mutate)


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for key,item in value.items():yield key;yield from strings(item)
    elif isinstance(value,(list,tuple)):
        for item in value:yield from strings(item)


def value_rows(value,tokens):
    """Author generic JSON outside the hot path, preserving binary64 words."""
    rows=[]
    def emit(item):
        at=len(rows);rows.append([0,0,0,0,0])
        if item is None:pass
        elif isinstance(item,bool):rows[at][:4]=[1,int(item),0,0]
        elif isinstance(item,(int,float)):
            low,high=struct.unpack("<II",struct.pack("<d",float(item)));rows[at][:4]=[4,0,low,high]
        elif isinstance(item,str):rows[at][:4]=[5,tokens[item],0,0]
        elif isinstance(item,list):
            rows[at][:4]=[12,len(item),0,0]
            for child in item:emit(child)
        elif isinstance(item,dict):
            rows[at][:4]=[13,len(item),0,0]
            for key in sorted(item):emit(key);emit(item[key])
        else:raise TypeError(item)
        rows[at][4]=len(rows)
    emit(value);return rows


def option_rows(options,tokens):
    rows=[[6,len(options),0,0,0]]
    for action in options:
        at=len(rows);rows.append([10,6,0,0,0])
        for key in ("id","kind","player","nation"):
            rows.append([5,tokens[action[key]],0,0,len(rows)+1])
        start=len(rows);present=action["decision"] is not None
        rows.append([9,int(present),0,0,start+1+int(present)])
        if present:rows.append([5,tokens[action["decision"]],0,0,len(rows)+1])
        offset=len(rows)
        for row in value_rows(action["parameters"],tokens):rows.append([*row[:4],row[4]+offset])
        rows[at][4]=len(rows)
    rows[0][4]=len(rows);return rows


@unittest.skipUnless(EXACT,"Exact MPS required")
class ResidentPoliticalDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=torch.get_num_threads();torch.set_num_threads(2)
        torch.mps.set_per_process_memory_fraction(3_000_000_000/torch.mps.recommended_max_memory())
    @classmethod
    def tearDownClass(cls):torch.set_num_threads(cls.old);torch.mps.empty_cache()

    def setup(self,envs,nations,kinds=None,options=None,continuations=None):
        context=DeviceStateContext(gwrl_cpp.device_state_context(envs[0]),"mps")
        state=DeviceStateBatch.capture(envs,context=context);queue=ResidentPoliticalDecisionQueue(context)
        names=tuple(dict.fromkeys(strings([nations,kinds or [],options or [],continuations or []])))
        tokens={};missing=[]
        for name in names:
            try:tokens[name]=int(context.prefix_lookup_ids((name,))[0])
            except IndexError:missing.append(name)
        if missing:
            data,lengths=pack_byte_requests([name.encode() for name in missing],device="mps")
            added=intern_bytes(state,data,lengths,string_capacity=state.string_offsets.numel()-1+len(missing),
                byte_capacity=state.string_bytes.numel()+data.numel())
            self.assertTrue(added.committed.item());state=added.state;tokens.update(zip(missing,added.ids.cpu().tolist(),strict=True))
        # Input authoring may request spellings already in the source suffix.
        # Remove only unused ingress padding so each byte/slot shortage test
        # actually has one fewer slot than the transaction needs.
        used,size=state.suffix_usage.cpu().tolist()
        state=replace(state,string_offsets=state.string_offsets[:used+1].clone(),string_bytes=state.string_bytes[:size].clone())
        ids=lambda names:torch.tensor([tokens[name] for name in names],dtype=torch.int64,device="mps")
        if kinds is None:return state,ResidentEvolutionChoice(context,queue),ids(nations)
        def forest(rows):
            capacity=max(map(len,rows),default=0);buffer=torch.zeros((len(envs),capacity,5),dtype=torch.int64,device="mps")
            for lane,data in enumerate(rows):buffer[lane,:len(data)]=torch.tensor(data,dtype=torch.int64,device="mps")
            return buffer,torch.tensor(list(map(len,rows)),dtype=torch.int64,device="mps"),torch.zeros(len(envs),dtype=torch.int64,device="mps")
        choices=PoliticalDecisionOptions(state,*forest([option_rows(row,tokens) for row in options]))
        payloads=EventPayloads(state,*forest([value_rows(row,tokens) for row in continuations]))
        return state,queue,ids(nations),ids(kinds),choices,payloads

    def raw(self,state,lane):
        length=state.lengths[lane].cpu().item();used,size=state.suffix_usage.cpu().tolist()
        rows=state.records[lane,:length].cpu().numpy().copy();data=state.string_bytes[:size].cpu().numpy().copy();offsets=state.string_offsets[:used+1].cpu().numpy().copy()
        return SimpleNamespace(context=state.context.native,record_array=lambda:rows,lane_offsets=lambda:np.array([0,length],dtype=np.int64),
            string_bytes=lambda:data,string_offsets=lambda:offsets)

    def compare(self,before,result,envs,nations,*,kinds=None,options=None,continuations=None,selected=None):
        enabled=[True]*len(envs) if selected is None else selected
        if kinds is None:gold=gwrl_cpp.campaign_queue_political_evolution_oracle(before.context.native,envs,nations,enabled)
        else:gold=gwrl_cpp.campaign_queue_political_decision_oracle(before.context.native,envs,nations,kinds,
            [json.dumps(row,ensure_ascii=False) for row in options],[json.dumps(row,ensure_ascii=False) for row in continuations],enabled)
        self.assertEqual(result.errors.cpu().tolist(),[row["error"] for row in gold]);failed=any(row["error"] for row in gold)
        self.assertEqual(result.committed.item(),not failed)
        for lane,row in enumerate(gold):
            native=gwrl_cpp.capture_device_states(before.context.native,[envs[lane]]) if failed else row["packed_state"]
            require_exact(self.raw(result.state,lane),canonical_native(native))
        records=result.state.records.cpu().numpy()
        self.assertTrue(np.any((records[:,:,0]==4)&(records[:,:,2]==0)&(records[:,:,3]==0x80000000)))
        return gold

    def rollback(self,before,result):
        self.assertFalse(result.committed.item());self.assertFalse(result.accepted.any().item())
        for name in ("records","string_bytes","string_offsets"):
            old,new=getattr(before,name),getattr(result.state,name);slices=tuple(slice(0,n) for n in old.shape)
            self.assertTrue(torch.equal(old,new[slices]),name)
            if name=="records":self.assertEqual(new[:,old.shape[1]:].count_nonzero().item(),0)
            else:self.assertEqual(new[old.shape[0]:].count_nonzero().item(),0)
        for name in ("lengths","sections","errors","suffix_usage"):
            self.assertTrue(torch.equal(getattr(before,name),getattr(result.state,name)),name)

    def enqueue(self,setup,*,selected=None,caps=None):
        state,queue,nations,kinds,options,continuation=setup
        if caps is None:caps=queue.reserve(state,options,continuation,id_byte_capacity=128)
        return queue.enqueue(state,nations,kinds,options,continuation,
            None if selected is None else torch.tensor(selected,dtype=torch.bool,device="mps"),**caps)

    def evolve(self,setup,*,selected=None,caps=None):
        state,service,nations=setup
        if caps is None:caps=service.reserve(state,option_capacity=256)
        return service.queue(state,nations,None if selected is None else torch.tensor(selected,dtype=torch.bool,device="mps"),**caps)

    def test_generic_option_identity_bits_reaction_and_controlling_player(self):
        def control(s):s["nations"]["mongolia"].update(controller_nation="japan",player=None)
        envs=[fixture(),fixture(mutate=control)];nations=["ccp","mongolia"];kinds=["opaque_decision","opaque_decision"]
        choices=[option(parameters={"zero":-0.0,"exact":1.0000000000000002,"utf8":"蒙古\u0000","nested":[None,True,{}]}),
                 option("second",decision="previous_choice",parameters=[None,False,-7.5])]
        options=[choices,choices];continuations=[{"zero":-0.0,"unknown":[True,"蒙古"]},[None,-0.0,True]]
        setup=self.setup(envs,nations,kinds,options,continuations);source=[e.serialize() for e in envs]
        result=self.enqueue(setup);self.compare(setup[0],result,envs,nations,kinds=kinds,options=options,continuations=continuations)
        self.assertEqual([e.serialize() for e in envs],source)
        # The helper permits generic option parameters; outer State validation
        # deliberately owns the object-only Action requirement.
        self.assertEqual(result.reactions.cpu().tolist(),[False,True])

    def test_updated_pending_player_resolution_and_approved_dormant_actor_fixture(self):
        source=fixture();actor=gwrl_cpp._campaign_political_decision_actor_test_fixture(source)
        self.assertEqual(json.loads(source.serialize())["random"],json.loads(actor.serialize())["random"])
        envs=[actor,actor.clone()];nations=["queue_actor_1"]*2
        kinds=["warlord_defense_player:queue_actor","noncolliding"]
        options=[[option()],[option()]];continuations=[{},{}]
        setup=self.setup(envs,nations,kinds,options,continuations);result=self.enqueue(setup)
        self.compare(setup[0],result,envs,nations,kinds=kinds,options=options,continuations=continuations);self.rollback(setup[0],result)
        self.assertEqual(result.errors.cpu().tolist(),[2,0])
        setup=self.setup([actor],["queue_actor_1"],["noncolliding"],[[option()]],[{}]);result=self.enqueue(setup)
        self.compare(setup[0],result,[actor],["queue_actor_1"],kinds=["noncolliding"],options=[[option()]],continuations=[{}])
        actual=json.loads(result.state.restore_envs()[0].serialize())["state"]
        self.assertEqual(actual["decisions"][-1]["options"][0]["player"],"axis")

    def test_empty_options_signed_counters_and_native_first_failure_order(self):
        envs=[fixture(sequence=2**31-1),fixture(sequence=-(2**31)),fixture(sequence=-1),fixture(sequence=2**31-1),fixture()]
        nations=["missing_nation","japan","japan","missing_nation","missing_nation"]
        kinds=["counter"]*5;options=[[],[option()],[option()],[option()],[option()]];continuations=[{}]*5
        selected=[True,True,True,True,False];setup=self.setup(envs,nations,kinds,options,continuations)
        result=self.enqueue(setup,selected=selected)
        self.compare(setup[0],result,envs,nations,kinds=kinds,options=options,continuations=continuations,selected=selected);self.rollback(setup[0],result)
        self.assertEqual(result.errors.cpu().tolist(),[2,0,0,2,0])
        envs=envs[1:3];nations=["japan"]*2;kinds=["counter"]*2;options=[[option()]]*2;continuations=[{}]*2
        setup=self.setup(envs,nations,kinds,options,continuations);result=self.enqueue(setup)
        self.compare(setup[0],result,envs,nations,kinds=kinds,options=options,continuations=continuations)
        self.assertEqual([json.loads(e.serialize())["state"]["decisions"][-1]["id"] for e in result.state.restore_envs()],
                         ["counter_-2147483647","counter_0"])
        env=fixture();setup=self.setup([env],["missing_nation"],["counter"],[[option()]],[{}]);result=self.enqueue(setup)
        self.compare(setup[0],result,[env],["missing_nation"],kinds=["counter"],options=[[option()]],continuations=[{}]);self.rollback(setup[0],result)
        self.assertEqual(result.errors.cpu().tolist(),[1])

    def test_queue_preserves_duplicate_decision_ids_for_outer_validation(self):
        def collision(s):
            s["politics"]["pending"]["opaque_decision_1"]={"old":-0.0}
            action=option(decision="opaque_decision_1")
            s["decisions"].append(dict(id="opaque_decision_1",kind="old",nation="japan",reaction=True,
                continuation="opaque_decision_1",options=[action]))
        env=fixture(mutate=collision);nations=["japan"];kinds=["opaque_decision"];options=[[option()]];continuations=[{"new":-0.0}]
        setup=self.setup([env],nations,kinds,options,continuations);result=self.enqueue(setup)
        self.compare(setup[0],result,[env],nations,kinds=kinds,options=options,continuations=continuations)
        with self.assertRaisesRegex(RuntimeError,"Invalid/duplicate pending decision"):result.state.to_native()

    def test_generic_fixed_capacities_report_exact_retry_and_rollback(self):
        env=fixture();nations=["japan"];kinds=["capacity_choice"];options=[[option(),option("two",parameters={"a":[1,2]})]];continuations=[{"opaque":[False,None]}]
        setup=self.setup([env],nations,kinds,options,continuations);before,queue,_,_,choices,payload=setup
        fixed=queue.reserve(before,choices,payload,id_byte_capacity=128);good=self.enqueue(setup,caps=fixed)
        self.compare(before,good,[env],nations,kinds=kinds,options=options,continuations=continuations)
        S=good.required_state_capacity.item();K=good.required_block_capacity.item();T,A=good.required_string_usage.cpu().tolist();L=good.required_id_bytes.item()
        for short in ({"id_byte_capacity":L-1},{"state_capacity":max(before.records.shape[1],S-1)},
                      {"block_capacity":K-1},{"string_capacity":max(before.string_offsets.numel()-1,T-1)},
                      {"byte_capacity":max(before.string_bytes.numel(),A-1)}):
            with self.subTest(short=short):
                failed=self.enqueue(setup,caps={**fixed,**short});self.rollback(before,failed);self.assertEqual(failed.errors.cpu().tolist(),[5])
        exact={**fixed,"id_byte_capacity":L,"state_capacity":max(before.records.shape[1],S),"block_capacity":K,"string_capacity":T,"byte_capacity":A}
        again=self.enqueue(setup,caps=exact);self.compare(before,again,[env],nations,kinds=kinds,options=options,continuations=continuations)

    def test_evolution_all_owned_land_order_boolean_options_and_exact_native_ids(self):
        envs=[fixture(),fixture(mutate=lambda s:s["nations"]["japan"].update(power_status="minor"))];nations=["ccp","japan"]
        setup=self.setup(envs,nations);result=self.evolve(setup);self.compare(setup[0],result,envs,nations)
        actual=[json.loads(e.serialize())["state"] for e in result.state.restore_envs()]
        for lane,(state,nation) in enumerate(zip(actual,nations,strict=True)):
            zones=sorted(z for z,t in state["territories"].items() if t["possessor"]==nation)
            decision=state["decisions"][-1];parameters=[a["parameters"] for a in decision["options"]]
            self.assertEqual(parameters,[{"zone":z,"factory":factory} for z in zones for factory in (False,True)])
            self.assertEqual(result.required_option_capacity[lane].item(),len(zones)*2)
            self.assertEqual(state["flags"]["evolution_pending_"+nation],1)

    def test_evolution_awarded_pending_guards_precede_land_player_and_counter(self):
        def empty(s):
            for territory in s["territories"].values():
                if territory["possessor"]=="ccp":territory["possessor"]="kmt"
            s["nations"]["ccp"].update(player=None,controller_nation=None)
        def awarded(s):empty(s);s["politics"]["evolution_awarded"].append("ccp")
        def pending(s):empty(s);s["flags"]["evolution_pending_ccp"]=-7
        envs=[fixture(sequence=2**31-1,mutate=awarded),fixture(sequence=2**31-1,mutate=pending)]
        setup=self.setup(envs,["ccp"]*2);before,service,_=setup
        caps=service.reserve(before,option_capacity=0,parameter_byte_capacity=0)
        caps.update(pending_key_byte_capacity=0,action_id_byte_capacity=0,decision_id_byte_capacity=0,
                    state_capacity=before.records.shape[1],block_capacity=max(before.records.shape[1],1),
                    string_capacity=before.string_offsets.numel()-1,byte_capacity=before.string_bytes.numel())
        result=self.evolve(setup,caps=caps);self.compare(before,result,envs,["ccp"]*2);self.assertFalse(result.queued.any().item())

    def test_evolution_failures_roll_back_pending_flag_and_all_selected_lanes(self):
        def empty(s):
            for territory in s["territories"].values():
                if territory["possessor"]=="ccp":territory["possessor"]="kmt"
        def missing(s):s["nations"]["ccp"].update(player=None,controller_nation=None)
        # Each later-stage failure is paired with a healthy lane so the exact
        # per-stage diagnostics are observed before the cohort rolls back.
        for bad in (fixture(mutate=empty),fixture(mutate=missing),fixture(sequence=2**31-1)):
            envs=[bad,fixture()];setup=self.setup(envs,["ccp"]*2);result=self.evolve(setup)
            self.compare(setup[0],result,envs,["ccp"]*2);self.rollback(setup[0],result)
            self.assertEqual(result.errors.cpu().tolist(),[2,0])

    def test_evolution_every_fixed_capacity_and_exact_retry(self):
        env=fixture();setup=self.setup([env],["ccp"]);before,service,_=setup
        fixed=service.reserve(before,option_capacity=256);good=self.evolve(setup,caps=fixed);self.compare(before,good,[env],["ccp"])
        O=good.required_option_capacity.item();F=good.required_pending_key_bytes.item();P=good.required_parameter_bytes.max().item()
        I=good.required_action_id_bytes.max().item();D=good.required_decision_id_bytes.item();S=good.required_state_capacity.item();K=good.required_block_capacity.item()
        T,A=good.required_string_usage.cpu().tolist()
        for short in ({"option_capacity":O-1},{"parameter_byte_capacity":P-1},{"pending_key_byte_capacity":F-1},
                      {"action_id_byte_capacity":I-1},{"decision_id_byte_capacity":D-1},
                      {"state_capacity":max(before.records.shape[1],S-1)},{"block_capacity":K-1},
                      {"string_capacity":max(before.string_offsets.numel()-1,T-1)},
                      {"byte_capacity":max(before.string_bytes.numel(),A-1)}):
            with self.subTest(short=short):
                failed=self.evolve(setup,caps={**fixed,**short});self.rollback(before,failed);self.assertEqual(failed.errors.cpu().tolist(),[5])
        exact=dict(option_capacity=O,parameter_byte_capacity=P,pending_key_byte_capacity=F,action_id_byte_capacity=I,decision_id_byte_capacity=D,
                   state_capacity=max(before.records.shape[1],S),block_capacity=K,string_capacity=T,byte_capacity=A)
        self.compare(before,self.evolve(setup,caps=exact),[env],["ccp"])
        # Options are densely ranked across lanes. A failure in active lane1
        # must never be assigned to the unselected lane0's spare capacity.
        paired=self.setup([env,env.clone()],["ccp","ccp"]);source,service,_=paired
        full=service.reserve(source,option_capacity=256);normal=self.evolve(paired,selected=[False,True],caps=full)
        self.compare(source,normal,[env,env.clone()],["ccp","ccp"],selected=[False,True])
        required=normal.required_string_usage.cpu().tolist()
        shortage={**full,"byte_capacity":max(source.string_bytes.numel(),required[1]-1)}
        failed=self.evolve(paired,selected=[False,True],caps=shortage);self.rollback(source,failed)
        self.assertEqual(failed.errors.cpu().tolist(),[0,5])

    def test_source_binding_no_hot_host_reads_and_empty_unselected_cohorts(self):
        env=fixture();setup=self.setup([env],["japan"],["opaque"],[[option()]],[{}]);state,queue,nations,kinds,choices,payload=setup
        caps=queue.reserve(state,choices,payload,id_byte_capacity=128)
        # Warm only the immutable kernels/static descriptors before forbidding
        # synchronization, JSON and fallback calls in the actual helper.
        self.enqueue(setup,caps=caps)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("hot host read")),patch.object(torch.Tensor,"item",side_effect=AssertionError("hot host read")),\
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("hot host read")),\
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("hot host read")),patch.object(json,"loads",side_effect=AssertionError("hot JSON")),\
             patch.object(json,"dumps",side_effect=AssertionError("hot JSON")),\
             patch.object(gwrl_cpp,"campaign_queue_political_decision_oracle",side_effect=AssertionError("CPU fallback")):
            result=self.enqueue(setup,caps=caps)
        self.assertTrue(result.committed.item())
        with self.assertRaisesRegex(ValueError,"exact complete State"):
            queue.enqueue(state,nations,kinds,replace(choices,source=replace(state)),payload,**caps)
        evolution=self.setup([env],["ccp"]);self.evolve(evolution)
        with patch.object(torch.Tensor,"cpu",side_effect=AssertionError("hot host read")),patch.object(torch.Tensor,"item",side_effect=AssertionError("hot host read")),\
             patch.object(torch.Tensor,"__bool__",side_effect=AssertionError("hot host read")),\
             patch.object(torch.Tensor,"tolist",side_effect=AssertionError("hot host read")),patch.object(json,"loads",side_effect=AssertionError("hot JSON")),\
             patch.object(json,"dumps",side_effect=AssertionError("hot JSON")),\
             patch.object(gwrl_cpp,"campaign_queue_political_evolution_oracle",side_effect=AssertionError("CPU fallback")):
            evolved=self.evolve(evolution)
        self.assertTrue(evolved.committed.item())
        disabled=self.enqueue(setup,selected=[False]);self.compare(state,disabled,[env],["japan"],kinds=["opaque"],options=[[option()]],continuations=[{}],selected=[False])
        empty=DeviceStateBatch.capture([],context=state.context);zero=torch.zeros(0,dtype=torch.int64,device="mps")
        empty_options=PoliticalDecisionOptions(empty,torch.empty((0,1,5),dtype=torch.int64,device="mps"),zero,zero)
        empty_payload=EventPayloads(empty,torch.empty((0,1,5),dtype=torch.int64,device="mps"),zero,zero)
        result=queue.enqueue(empty,zero,zero,empty_options,empty_payload,**queue.reserve(empty,empty_options,empty_payload,id_byte_capacity=0))
        self.assertTrue(result.committed.item());self.assertEqual(result.errors.numel(),0)
