"""Exact read-only validateRoute queries on resident campaign state.

This component validates supplied ordered paths; it neither generates a complete
legal-action menu nor moves units/advances politics. Immutable geography/catalog
data are prepared once. Dynamic indexes and shared political/declaration results
are bound to one complete immutable snapshot. Execution never serializes a game,
reads GPU values on CPU, or substitutes a CPU legality fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import _device
from .resident_relations import SOURCE as RELATIONS_SOURCE, ResidentPoliticalRelations
from .resident_declarations import ResidentLandAttackDeclarations

MODES=("ordinary","blitz","strategic_rail","strategic_river","narrow_crossing")
CORE_FIELDS=("allowed","reason","cost","exhausts_movement","from","to","river","river_known",
             "exception","message","supported","detail")
REASONS=("", "Unknown moving unit", "Towed artillery must continue with its motorized partner",
 "Only ordinary Motorized Infantry movement can tow one unit", "This unit cannot be towed",
 "Tow pair must be the same nation's units in the same zone", "Tow pair must start together before either moves",
 "Motorized Infantry is already paired with another towed unit", "Artillery is already paired with another towing unit",
 "Towed unit has no movement remaining", "Unknown unit", "Not this nation's movement turn",
 "Unit is committed to an unresolved battle", "Cargo must be moved by its transport",
 "Transported units cannot move further after unloading", "Unit is committed to repair",
 "Artillery used an attrition attack this turn", "Newly placed units cannot move this turn",
 "Route must start at the unit's current zone", "Strategic rail is noncombat movement", "Unit already moved this turn",
 "Ordinary land movement requires a land unit", "Combat movement phase required", "Noncombat movement phase required",
 "Unit combat moved this turn", "No movement remaining", "Unit cannot use strategic rail",
 "Militia must start and end in its Home Country", "Unit is not eligible to blitz",
 "Blitz companion must follow its paired armor to the same target", "Land route left the selected map",
 "Land routes cannot contain loops", "Nonadjacent land route", "Impassable land boundary",
 "Narrow crossing requires its own movement mode", "Strategic destination must be continuously possessed with permission",
 "No undamaged railroad or usable river", "This route is not a river route", "Gauge change requires Improved Logistics",
 "Land access is prohibited", "Enemy land ends ordinary movement; resolve combat before blitzing", "Militia cannot attack",
 "Cannot enter land captured this turn", "Terrain, city or fortification prohibits blitzing", "Cannot blitz into friendly land",
 "Terrain ends movement immediately", "Crossing must begin and end the unit's movement",
 "Only Marines attack; infantry-class units may noncombat cross", "Enemy units prevent the narrow crossing",
 "Narrow crossing capacity exhausted", "Insufficient movement points", "Regional rail capacity exhausted")

# Static flat-buffer offsets. Sizes derive from the entire native definition.
STATIC_FIELDS=("nodes","edges","node_terrain","border_terrain","river_banks","crossing_seas",
 "bank_unknown","crossing_missing","home","classes","fort_borders","fort_errors","capacities",
 "crossing_counters","crossing_counter_errors","rail_counters","counter_offsets",
 "zone_ids","nation_ids","type_ids","fort_ids","restricted_terrain","blitz_types","turn_nations")


@dataclass(frozen=True)
class TensorRouteRequests:
    metadata: torch.Tensor          # int64[Q,7]: lane,unit,length,mode,combat,towed,present
    paths: torch.Tensor             # static zone indices, ordered [Q,P]

    @property
    def lanes(self):return self.metadata[:,0]
    @property
    def units(self):return self.metadata[:,1]
    @property
    def path_lengths(self):return self.metadata[:,2]
    @property
    def modes(self):return self.metadata[:,3]
    @property
    def combat(self):return self.metadata[:,4]
    @property
    def towed(self):return self.metadata[:,5]
    @property
    def has_towed(self):return self.metadata[:,6]


@dataclass(frozen=True)
class PreparedRoutes:
    source: object
    relations: object
    declarations: object
    indexes: torch.Tensor           # [B,S+Z+N+13], complete dense SID/record indexes


@dataclass(frozen=True)
class ResidentRouteResult:
    source: object
    requests: TensorRouteRequests
    core: torch.Tensor              # [Q,12], includes native partial results
    regions: torch.Tensor           # [Q,R], complete set membership
    node_terrain: torch.Tensor      # [Q,K], complete approach sets
    border_terrain: torch.Tensor
    context_identity: tuple

    @property
    def allowed(self):return self.core[:,0]
    @property
    def errors(self):return self.core[:,8]
    @property
    def supported(self):return self.core[:,10]


SOURCE=RELATIONS_SOURCE+r"""
struct RouteView {
    PackedStateView v;
    device const long* data;device const long* offsets;device const uchar* counter_bytes;
    device const long* roots;device const long* units;device const long* territories;device const long* nations;
    device const long* pairs;device const long* pair_errors;device const long* national;device const long* national_errors;
    device const long* declarations;device const long* declaration_errors;device const long* dims;
};
inline device const long* route_static(thread const RouteView& g,long field){return g.data+g.offsets[field];}
inline long route_index(device const long* ids,long count,long id){for(long i=0;i<count;++i)if(ids[i]==id)return i;return -1;}
inline long route_int(thread const PackedStateView& v,long node,thread bool& valid){
    long result=state_signed_value(v,node,valid);if(result<(-2147483647L-1L)||result>2147483647L)valid=false;return result;
}
inline long route_flag(thread const PackedStateView& v,long map,constant char* key,long length,thread bool& valid){
    long node=state_map_find_literal(v,map,key,length,valid);return node<0?0:route_int(v,node,valid);
}
inline bool route_set_literal(thread const PackedStateView& v,long root,constant char* key,long size,thread bool& valid){
    relations_container(v,root,8,-1,valid);if(!valid)return false;long cursor=root+1,end=state_end(v,root,valid),count=state_record(v,root)[1];
    if(count>end-root-1){valid=false;return false;}for(long i=0;valid&&i<count;++i){
        bool found=state_string_equals(v,cursor,key,size,valid);cursor=state_end(v,cursor,valid);if(found)return true;}
    if(valid&&cursor!=end)valid=false;return false;
}
inline bool route_prefix(thread const PackedStateView& v,long id,constant char* prefix,long length,thread bool& valid){
    long start,end;bool fixed;relations_span(v,id,start,end,fixed,valid);if(!valid||end-start<length)return false;
    device const uchar* bytes=fixed?v.prefix_bytes:v.suffix_bytes;
    for(long i=0;i<length;++i)if(bytes[start+i]!=uchar(prefix[i]))return false;return true;
}
inline bool route_join_equal(thread const PackedStateView& v,long candidate,constant char* prefix,long length,long tail,
                              thread bool& valid){
    long a,b,x,y;bool cp,tp;relations_span(v,candidate,a,b,cp,valid);relations_span(v,tail,x,y,tp,valid);
    if(!valid||b-a!=length+y-x)return false;device const uchar* c=cp?v.prefix_bytes:v.suffix_bytes;
    device const uchar* t=tp?v.prefix_bytes:v.suffix_bytes;
    for(long i=0;i<length;++i)if(c[a+i]!=uchar(prefix[i]))return false;
    for(long i=0;i<y-x;++i)if(c[a+length+i]!=t[x+i])return false;return true;
}
inline bool route_set_join(thread const PackedStateView& v,long set,constant char* prefix,long length,long tail,
                           thread bool& valid){
    relations_container(v,set,8,-1,valid);if(!valid)return false;long cursor=set+1,count=state_record(v,set)[1],end=state_end(v,set,valid);
    if(count>end-set-1){valid=false;return false;}for(long i=0;valid&&i<count;++i){
        const long id=state_string_id(v,cursor,valid);cursor=state_end(v,cursor,valid);
        if(route_join_equal(v,id,prefix,length,tail,valid))return true;}if(valid&&cursor!=end)valid=false;return false;
}
inline bool route_has_prefix(thread const PackedStateView& v,long set,constant char* prefix,long length,thread bool& valid){
    relations_container(v,set,8,-1,valid);if(!valid)return false;long cursor=set+1,count=state_record(v,set)[1],end=state_end(v,set,valid);
    if(count>end-set-1){valid=false;return false;}for(long i=0;valid&&i<count;++i){
        const long id=state_string_id(v,cursor,valid);cursor=state_end(v,cursor,valid);if(route_prefix(v,id,prefix,length,valid))return true;}
    if(valid&&cursor!=end)valid=false;return false;
}
inline bool route_other_pair(thread const PackedStateView& v,long set,constant char* prefix,long length,long tail,
                             thread bool& valid){
    relations_container(v,set,8,-1,valid);if(!valid)return false;long cursor=set+1,count=state_record(v,set)[1],end=state_end(v,set,valid);
    if(count>end-set-1){valid=false;return false;}for(long i=0;valid&&i<count;++i){
        const long id=state_string_id(v,cursor,valid);cursor=state_end(v,cursor,valid);
        if(route_prefix(v,id,prefix,length,valid)&&!route_join_equal(v,id,prefix,length,tail,valid))return true;}
    if(valid&&cursor!=end)valid=false;return false;
}
inline long route_counter_flag(thread const RouteView& g,long flags,long counter,thread bool& present,thread bool& valid){
    present=false;if(counter<0){valid=false;return 0;}device const long* offsets=route_static(g,16);
    const long a=offsets[counter],b=offsets[counter+1];relations_container(g.v,flags,7,-1,valid);if(!valid)return 0;
    long cursor=flags+1,count=state_record(g.v,flags)[1],end=state_end(g.v,flags,valid);
    if(count>(end-flags-1)/2){valid=false;return 0;}
    for(long i=0;valid&&i<count;++i){const long id=state_string_id(g.v,cursor,valid);long x,y;bool fixed;
        relations_span(g.v,id,x,y,fixed,valid);device const uchar* bytes=fixed?g.v.prefix_bytes:g.v.suffix_bytes;
        bool match=valid&&y-x==b-a;for(long k=0;match&&k<b-a;++k)match=bytes[x+k]==g.counter_bytes[a+k];
        const long value=state_end(g.v,cursor,valid);cursor=state_end(g.v,value,valid);
        if(match){present=true;return route_int(g.v,value,valid);}}
    if(valid&&cursor!=end)valid=false;return 0;
}
inline void route_default(device long* out){for(long i=0;i<12;++i)out[i]=0;out[4]=-1;out[5]=-1;out[7]=1;out[9]=-1;out[10]=1;out[11]=-1;}
inline bool route_exception(device long* out,long code,long message=-1,long detail=-1){out[8]=code;out[9]=message;out[11]=detail;return false;}
inline bool route_relation(thread const RouteView& g,long a,long b,long field,device long* out){
    const long N=g.dims[3];if(a<0||a>=N||b<0||b>=N){route_exception(out,3);return false;}
    const long at=(a*N+b)*7+field;if(g.pair_errors[at]){route_exception(out,g.pair_errors[at],-2,a);return false;}
    return g.pairs[at]!=0;
}
inline long route_owner(thread const RouteView& g,long zone,thread bool& present,thread bool& valid){
    present=false;if(zone<0||zone>=g.dims[2])return -1;const long root=g.territories[zone];if(root<0)return -1;
    relations_container(g.v,root,10,2,valid);const long value=state_optional(g.v,state_child(g.v,root,0,valid),present,valid);
    if(!present)return -1;const long result=route_index(route_static(g,18),g.dims[3],state_string_id(g.v,value,valid));
    if(result<0)valid=false;return result;
}
inline bool route_held(thread const RouteView& g,long actor,long zone,device long* out,thread bool& valid){
    bool owned=false;long owner=route_owner(g,zone,owned,valid);if(!owned)return false;
    const long past=state_map_find_id(g.v,g.roots[3],route_static(g,17)[zone],valid);if(past<0)return false;
    bool existed=false;const long value=state_optional(g.v,past,existed,valid);if(!existed)return false;
    if(state_string_id(g.v,value,valid)!=route_static(g,18)[owner])return false;
    const long flags=state_child(g.v,g.territories[zone],1,valid);
    const long changed=state_map_find_literal(g.v,flags,"last_possession_change_turn",27,valid);
    if(changed>=0&&route_int(g.v,changed,valid)==g.roots[9])return false;
    return owner==actor||route_relation(g,actor,owner,3,out);
}
struct RouteUnit {long id,type,owner,zone,remaining;bool has_remaining;long origin,route,carried,commitments,turn,game;};
inline RouteUnit route_unit(thread const RouteView& g,long id,thread bool& valid){
    RouteUnit out={id,-1,-1,-1,0,false,-1,-1,-1,-1,-1,-1};
    if(id<0||id>=g.dims[9]||g.units[id]<0){valid=false;return out;}const long root=g.units[id];
    relations_container(g.v,root,10,14,valid);if(!valid)return out;
    if(state_string_id(g.v,state_child(g.v,root,0,valid),valid)!=id)valid=false;
    out.type=route_index(route_static(g,19),g.dims[4],state_string_id(g.v,state_child(g.v,root,1,valid),valid));
    out.owner=route_index(route_static(g,18),g.dims[3],state_string_id(g.v,state_child(g.v,root,2,valid),valid));
    out.zone=route_index(route_static(g,17),g.dims[2],state_string_id(g.v,state_child(g.v,root,3,valid),valid));
    const long remaining=state_optional(g.v,state_child(g.v,root,4,valid),out.has_remaining,valid);
    if(out.has_remaining)out.remaining=route_int(g.v,remaining,valid);
    out.origin=state_string_id(g.v,state_child(g.v,root,6,valid),valid);out.route=state_child(g.v,root,7,valid);
    bool carried=false;(void)state_optional(g.v,state_child(g.v,root,8,valid),carried,valid);out.carried=carried;
    out.commitments=state_child(g.v,root,11,valid);out.turn=state_child(g.v,root,12,valid);out.game=state_child(g.v,root,13,valid);
    if(out.type<0||out.owner<0||out.zone<0)valid=false;return out;
}
inline bool route_player_exception(thread const RouteView& g,long actor,long code,device long* out,thread bool& valid){
    long current=actor;
    for(long depth=0;valid&&depth<g.dims[3];++depth){
        if(current<0||current>=g.dims[3]||g.nations[current]<0)return route_exception(out,code,-2,actor);
        const long nation=g.nations[current];bool present=false;
        (void)state_optional(g.v,state_child(g.v,nation,1,valid),present,valid);
        if(present)return route_exception(out,code,-2,actor);
        const long controller=state_optional(g.v,state_child(g.v,nation,0,valid),present,valid);
        if(present){current=route_index(route_static(g,18),g.dims[3],state_string_id(g.v,controller,valid));continue;}
        const long state=state_child(g.v,0,0,valid),politics=state_child(g.v,state,8,valid);
        const long pending=state_child(g.v,politics,10,valid);
        const long temporary=relations_named_flag(g.v,pending,"warlord_defense_player:",23,route_static(g,18)[current],valid);
        if(temporary<0)return route_exception(out,code,-3,current);
        if(state_record(g.v,temporary)[0]!=5)return route_exception(out,code,-5,current);
        return route_exception(out,code,-4,current);
    }
    return route_exception(out,valid?code:3,-2,actor);
}
inline bool route_class(thread const RouteView& g,thread const RouteUnit& u,long kind){return route_static(g,9)[u.type*8+kind]!=0;}
inline bool route_empty(thread const PackedStateView& v,long sequence,thread bool& valid){relations_container(v,sequence,6,-1,valid);return valid&&state_record(v,sequence)[1]==0;}
inline bool route_tech(thread const RouteView& g,long actor,thread bool& valid){
    if(actor<0||actor>=g.dims[3]||g.nations[actor]<0){valid=false;return false;}
    const long tech=state_child(g.v,g.nations[actor],7,valid);
    const long value=state_map_find_literal(g.v,tech,"improved_logistics",18,valid);return value>=0&&route_int(g.v,value,valid)==4;
}

kernel void prepare_route_indexes(
 device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],device const long* sections [[buffer(2)]],
 device const uchar* prefix_bytes [[buffer(3)]],device const long* prefix_offsets [[buffer(4)]],
 device const uchar* suffix_bytes [[buffer(5)]],device const long* suffix_offsets [[buffer(6)]],device const long* usage [[buffer(7)]],
 device const long* source_errors [[buffer(8)]],device const long* data [[buffer(9)]],device const long* offsets [[buffer(10)]],
 device long* indexes [[buffer(11)]],device const long* dims [[buffer(12)]],uint lane [[thread_position_in_grid]]) {
    const long B=dims[0],C=dims[1],Z=dims[2],N=dims[3],S=dims[9];if(long(lane)>=B)return;
    bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
        prefix_bytes,prefix_offsets,dims[12],dims[13],suffix_bytes,suffix_offsets,dims[14],dims[15],usage,valid);
    const long width=S+Z+N+13;device long* base=indexes+ulong(lane)*width;
    device long* units=base;device long* territories=units+S;device long* nations=territories+Z;device long* meta=nations+N;
    if(source_errors[lane])valid=false;for(long i=0;i<12;++i)meta[i]=-1;
    const long state=sections[ulong(lane)*27];relations_container(v,state,10,19,valid);
    meta[0]=state_child(v,state,2,valid);meta[1]=state_child(v,state,3,valid);meta[2]=state_child(v,state,4,valid);
    meta[3]=state_child(v,state_child(v,state,9,valid),0,valid);meta[4]=state_child(v,state,12,valid);meta[5]=state_child(v,state,15,valid);
    const long clock=state_child(v,state,7,valid);relations_container(v,clock,10,6,valid);meta[11]=clock;
    const long current=route_int(v,state_child(v,clock,1,valid),valid);
    if(current<0||current>=dims[16])valid=false;else meta[6]=data[offsets[23]+current];
    meta[7]=route_int(v,state_child(v,clock,2,valid),valid);meta[8]=route_int(v,state_child(v,clock,0,valid),valid);
    meta[9]=long(as_type<int>(uint(state_unsigned_value(v,state_child(v,clock,4,valid),valid))));
    meta[10]=state_child(v,state,0,valid);
    if(valid){relations_container(v,meta[0],7,-1,valid);long cursor=meta[0]+1,end=state_end(v,meta[0],valid),count=state_record(v,meta[0])[1];
        if(count>(end-meta[0]-1)/2)valid=false;
        for(long i=0;valid&&i<count;++i){long id=state_string_id(v,cursor,valid),root=state_end(v,cursor,valid);
            if(id<0||id>=S){valid=false;break;}units[id]=root;cursor=state_end(v,root,valid);}if(valid&&cursor!=end)valid=false;}
    const long land=state_child(v,state,1,valid);
    for(long z=0;valid&&z<Z;++z)territories[z]=state_map_find_id(v,land,data[offsets[17]+z],valid);
    for(long n=0;valid&&n<N;++n)nations[n]=state_map_find_id(v,meta[10],data[offsets[18]+n],valid);
    meta[12]=valid?0:3;
}
"""

SOURCE+=r"""
inline bool route_sequence_has(thread const PackedStateView& v,long sequence,long id,thread bool& valid){
    relations_container(v,sequence,6,-1,valid);if(!valid)return false;long cursor=sequence+1,count=state_record(v,sequence)[1],end=state_end(v,sequence,valid);
    if(count>end-sequence-1){valid=false;return false;}for(long i=0;valid&&i<count;++i){
        const long key=state_string_id(v,cursor,valid);cursor=state_end(v,cursor,valid);if(key==id)return true;}
    if(valid&&cursor!=end)valid=false;return false;
}
inline bool route_unresolved(thread const RouteView& g,long unit,thread bool& valid){
    const long map=g.roots[4];relations_container(g.v,map,7,-1,valid);if(!valid)return false;
    long cursor=map+1,count=state_record(g.v,map)[1],end=state_end(g.v,map,valid);if(count>(end-map-1)/2){valid=false;return false;}
    for(long i=0;valid&&i<count;++i){const long battle=state_end(g.v,cursor,valid);relations_container(g.v,battle,10,10,valid);
        const long flags=state_child(g.v,battle,8,valid);
        if(!route_flag(g.v,flags,"finished",8,valid)&&!route_flag(g.v,flags,"capture_done",12,valid)&&
           route_sequence_has(g.v,state_child(g.v,battle,5,valid),unit,valid))return true;
        cursor=state_end(g.v,battle,valid);}if(valid&&cursor!=end)valid=false;return false;
}
inline bool route_rail(thread const RouteView& g,long a,long b,bool check_damage,thread bool& undamaged,thread bool& built,thread bool& valid){
    const long Z=g.dims[2],pair=a*Z+b;bool exists=route_static(g,1)[pair*20+2]!=0;undamaged=true;built=false;
    const long map=g.roots[2];relations_container(g.v,map,7,-1,valid);if(!valid)return false;
    long cursor=map+1,count=state_record(g.v,map)[1],end=state_end(g.v,map,valid);if(count>(end-map-1)/2){valid=false;return false;}
    const long as=route_static(g,17)[a],bs=route_static(g,17)[b];
    for(long i=0;valid&&i<count;++i){const long rail=state_end(g.v,cursor,valid);relations_container(g.v,rail,10,4,valid);
        const long first=state_string_id(g.v,state_child(g.v,rail,1,valid),valid),second=state_string_id(g.v,state_child(g.v,rail,2,valid),valid);
        if((first==as&&second==bs)||(first==bs&&second==as)){
            exists=true;built=true;if(check_damage){const long damage=state_child(g.v,rail,3,valid);relations_container(g.v,damage,7,-1,valid);
            long entry=damage+1,entries=state_record(g.v,damage)[1],finish=state_end(g.v,damage,valid);
            if(entries>(finish-damage-1)/2){valid=false;return false;}
            for(long j=0;valid&&j<entries;++j){const long value=state_end(g.v,entry,valid);
                if(route_int(g.v,value,valid)>0)undamaged=false;entry=state_end(g.v,value,valid);}if(valid&&entry!=finish)valid=false;}
        }cursor=state_end(g.v,rail,valid);}if(valid&&cursor!=end)valid=false;
    undamaged=undamaged&&exists;return exists;
}
inline bool route_river(thread const RouteView& g,long actor,long a,long b,device long* out,thread bool& valid){
    const long Z=g.dims[2],pair=a*Z+b;device const long* edge=route_static(g,1)+pair*20;
    if(!edge[3])return false;device const long* meta=route_static(g,6)+pair*3;
    if(meta[1])return route_exception(out,meta[1],meta[2]);if(meta[0])return false;
    for(long z=0;valid&&z<Z;++z)if(z==a||z==b||route_static(g,4)[pair*Z+z]){
        if(g.territories[z]<0)return false;bool owned=false;const long owner=route_owner(g,z,owned,valid);
        if(owned&&owner!=actor&&route_relation(g,actor,owner,1,out))return false;if(out[8])return false;}
    return valid;
}
inline bool route_blitz_pair(thread const RouteView& g,thread const RouteUnit& unit,long from,long to,thread bool& valid){
    if(route_static(g,22)[unit.type])return true;
    const long set=unit.commitments;relations_container(g.v,set,8,-1,valid);if(!valid)return false;
    long cursor=set+1,count=state_record(g.v,set)[1],end=state_end(g.v,set,valid);if(count>end-set-1){valid=false;return false;}
    for(long i=0;valid&&i<count;++i){const long id=state_string_id(g.v,cursor,valid);cursor=state_end(g.v,cursor,valid);
        if(!route_prefix(g.v,id,"blitz_with:",11,valid))continue;
        const long map=g.roots[0];long entry=map+1,entries=state_record(g.v,map)[1],finish=state_end(g.v,map,valid);
        if(entries>(finish-map-1)/2){valid=false;return false;}
        for(long j=0;valid&&j<entries;++j){const long candidate=state_string_id(g.v,entry,valid),root=state_end(g.v,entry,valid);
            if(route_join_equal(g.v,id,"blitz_with:",11,candidate,valid)){
                RouteUnit armor=route_unit(g,candidate,valid);return valid&&armor.zone==to&&
                    route_set_join(g.v,armor.commitments,"blitz_from:",11,route_static(g,17)[from],valid)&&
                    route_set_join(g.v,armor.commitments,"blitz_to:",9,route_static(g,17)[to],valid);}
            entry=state_end(g.v,root,valid);}return false;
    }if(valid&&cursor!=end)valid=false;return false;
}
inline bool route_fortification(thread const RouteView& g,long actor,long from,long to,device long* out,thread bool& valid){
    bool possessed=false;const long owner=route_owner(g,to,possessed,valid);
    if(!possessed||owner==actor||!route_relation(g,actor,owner,1,out))return false;if(out[8])return false;
    const long map=g.roots[1];relations_container(g.v,map,7,-1,valid);if(!valid)return false;
    long cursor=map+1,count=state_record(g.v,map)[1],end=state_end(g.v,map,valid);if(count>(end-map-1)/2){valid=false;return false;}
    for(long i=0;valid&&i<count;++i){const long id=state_string_id(g.v,cursor,valid),facility=state_end(g.v,cursor,valid);
        relations_container(g.v,facility,10,5,valid);
        const long zone=state_string_id(g.v,state_child(g.v,facility,2,valid),valid),type=state_child(g.v,facility,1,valid);
        if(zone==route_static(g,17)[to]&&(state_string_equals(g.v,type,"fortification",13,valid)||
           state_string_equals(g.v,type,"improved_fortification",22,valid))){
            if(route_static(g,0)[to*7+1])return true;
            const long flag=relations_named_flag(g.v,state_child(g.v,facility,4,valid),"border:",7,route_static(g,17)[from],valid);
            if(flag>=0&&route_int(g.v,flag,valid)!=0)return true;
            const long f=route_index(route_static(g,20),g.dims[7],id);
            if(f>=0){device const long* e=route_static(g,11)+f*2;if(e[0])return route_exception(out,e[0],e[1]);
                if(route_static(g,10)[f*g.dims[2]+from])return true;}
        }cursor=state_end(g.v,facility,valid);}if(valid&&cursor!=end)valid=false;return false;
}
inline bool route_narrow_blocked(thread const RouteView& g,long actor,long pair,long target,bool combat,
                                 device long* out,thread bool& valid){
    if(combat){const long map=g.roots[1];relations_container(g.v,map,7,-1,valid);if(!valid)return false;
        long cursor=map+1,count=state_record(g.v,map)[1],end=state_end(g.v,map,valid);if(count>(end-map-1)/2){valid=false;return false;}
        for(long i=0;valid&&i<count;++i){const long facility=state_end(g.v,cursor,valid);relations_container(g.v,facility,10,5,valid);
            if(state_string_id(g.v,state_child(g.v,facility,2,valid),valid)==route_static(g,17)[target]&&
               state_string_equals(g.v,state_child(g.v,facility,1,valid),"coastal_artillery",17,valid))return true;
            cursor=state_end(g.v,facility,valid);}if(valid&&cursor!=end)valid=false;}
    device const long* meta=route_static(g,7)+pair*3;if(meta[1])return route_exception(out,meta[1],meta[2]);if(meta[0])return true;
    const long map=g.roots[0];long cursor=map+1,count=state_record(g.v,map)[1],end=state_end(g.v,map,valid);
    if(count>(end-map-1)/2){valid=false;return false;}
    for(long i=0;valid&&i<count;++i){const long id=state_string_id(g.v,cursor,valid),node=state_end(g.v,cursor,valid);RouteUnit unit=route_unit(g,id,valid);
        if(valid&&route_static(g,5)[pair*g.dims[2]+unit.zone]&&unit.owner!=actor&&route_relation(g,actor,unit.owner,1,out)){
            if(route_class(g,unit,5)||(route_class(g,unit,6)&&!route_flag(g.v,unit.turn,"submerged",9,valid))||
               route_set_literal(g.v,unit.commitments,"maritime_air_patrol",19,valid)||route_flag(g.v,unit.turn,"on_map",6,valid))return true;}
        if(out[8])return false;cursor=state_end(g.v,node,valid);}if(valid&&cursor!=end)valid=false;return false;
}
"""

SOURCE+=r"""
inline bool route_fail(device long* out,long reason){out[1]=reason;return false;}
inline bool route_land_access(thread const RouteView& g,long actor,long zone,bool combat,device long* out,thread bool& valid){
    bool owned=false;const long owner=route_owner(g,zone,owned,valid);if(!owned)return combat;
    if(owner==actor||route_relation(g,actor,owner,2,out))return true;if(out[8])return false;if(!combat)return false;
    const bool enemy=route_relation(g,actor,owner,1,out);if(out[8])return false;
    if(route_relation(g,actor,g.roots[6],0,out))return enemy;if(out[8])return false;if(enemy)return true;
    const long at=actor*g.dims[3]+owner;if(g.declaration_errors[at])return route_exception(out,g.declaration_errors[at],-2,actor);
    return g.declarations[at]!=0;
}
inline bool route_single(thread const RouteView& g,RouteUnit u,device const long* path,long length,long mode,bool combat,
                         device long* out,device long* regions,device long* nt,device long* bt,thread bool& valid){
    route_default(out);for(long r=0;r<g.dims[6];++r)regions[r]=0;
    for(long k=0;k<g.dims[5];++k){nt[k]=0;bt[k]=0;}
    const long N=g.dims[3],Z=g.dims[2],K=g.dims[5];
    if(g.national_errors[u.owner*3+2])return route_exception(out,g.national_errors[u.owner*3+2],-2,u.owner);
    if(!g.national[u.owner*3+2])return route_fail(out,11);
    if(route_unresolved(g,u.id,valid))return route_fail(out,12);
    if(u.carried)return route_fail(out,13);
    const long unloaded=state_map_find_literal(g.v,u.game,"port_unloaded_round",19,valid);
    if(route_flag(g.v,u.turn,"naval_unloaded",14,valid)||route_flag(g.v,u.turn,"air_transport_unloaded",22,valid)||
       route_set_literal(g.v,u.commitments,"transport_unloaded",18,valid)||
       (unloaded>=0&&route_int(g.v,unloaded,valid)==g.roots[8]+1))return route_fail(out,14);
    if(route_flag(g.v,u.turn,"repairing",9,valid)||route_set_literal(g.v,u.commitments,"repair",6,valid))return route_fail(out,15);
    if(route_set_literal(g.v,u.commitments,"attrition",9,valid))return route_fail(out,16);
    if(route_flag(g.v,u.turn,"placed_this_turn",16,valid))return route_fail(out,17);
    if(length<2||path[0]!=u.zone)return route_fail(out,18);
    const bool strategic=mode==2||mode==3;
    if(strategic){
        if(g.roots[7]!=3||combat)return route_fail(out,19);
        if(!route_empty(g.v,u.route,valid)||route_set_literal(g.v,u.commitments,"combat_move",11,valid)||
           route_flag(g.v,u.turn,"strategic_moved",15,valid))return route_fail(out,20);
    }else{
        if(!route_class(g,u,0))return route_fail(out,21);
        if(combat&&g.roots[7]!=1&&!(mode==1&&g.roots[7]==2))return route_fail(out,22);
        if(!combat&&g.roots[7]!=3)return route_fail(out,23);
        if(!combat&&route_set_literal(g.v,u.commitments,"combat_move",11,valid)&&
           !route_flag(g.v,u.turn,"must_withdraw_from_chinese_gift",31,valid))return route_fail(out,24);
    }
    if(!strategic&&(!u.has_remaining||u.remaining<=0))return route_fail(out,25);
    if(route_class(g,u,1)||(strategic&&!route_class(g,u,0)&&!route_class(g,u,2)&&!route_class(g,u,3)))return route_fail(out,26);
    const long last=path[length-1];
    if(u.type==g.dims[17]&&(last<0||last>=Z||!route_static(g,8)[u.owner*Z+path[0]]||!route_static(g,8)[u.owner*Z+last]))return route_fail(out,27);
    if(mode==1&&(!route_flag(g.v,u.turn,"blitz_eligible",14,valid)||route_flag(g.v,u.turn,"crossed_enemy_fortification",27,valid)||
       route_set_literal(g.v,u.commitments,"amphibious_assault",18,valid)))return route_fail(out,28);
    if(mode==1&&!route_blitz_pair(g,u,path[0],last,valid))return route_fail(out,29);
    for(long step=1;valid&&step<length;++step){
        const long a=path[step-1],b=path[step];
        if(a<0||a>=Z||b<0||b>=Z||g.territories[a]<0||g.territories[b]<0)return route_fail(out,30);
        for(long earlier=0;earlier<step;++earlier)if(path[earlier]==b)return route_fail(out,31);
        const long pair=a*Z+b;device const long* e=route_static(g,1)+pair*20;
        bool undamaged=false,built=false,rail=false;
        if(!e[0])rail=route_rail(g,a,b,false,undamaged,built,valid);
        if(!e[0]&&!rail)return route_fail(out,32);
        if(e[0]){if(e[18])return route_exception(out,e[18],e[19]);if(!e[1])return route_fail(out,33);}
        device const long* node=route_static(g,0)+b*7;
        if(node[5])return route_exception(out,node[5],node[6]);
        if(g.dims[25]>=0&&route_static(g,2)[b*K+g.dims[25]])return route_fail(out,33);
        if(e[4]&&mode!=4)return route_fail(out,34);
        if(strategic){
            bool held=route_held(g,u.owner,b,out,valid);if(out[8])return false;if(!held)return route_fail(out,35);
            bool possessed=false;const long owner=route_owner(g,b,possessed,valid);
            bool permission=possessed&&route_relation(g,u.owner,owner,6,out);if(out[8])return false;
            if(!permission)return route_fail(out,35);
            (void)route_rail(g,a,b,true,undamaged,built,valid);
            const bool river=route_river(g,u.owner,a,b,out,valid);if(out[8])return false;
            if(!undamaged&&!river)return route_fail(out,36);
            if(mode==3&&!river)return route_fail(out,37);
            if(undamaged&&!river){const long start=built?15:12;
                if(e[start+1])return route_exception(out,e[start+1],e[start+2]);
                if(e[start]&&!route_tech(g,u.owner,valid))return route_fail(out,38);}
            device const long* first=route_static(g,0)+a*7;
            if(first[3])return route_exception(out,first[3],first[4]);regions[first[2]]=1;
            if(node[3])return route_exception(out,node[3],node[4]);regions[node[2]]=1;
        }else{
            const bool access=route_land_access(g,u.owner,b,combat,out,valid);if(out[8])return false;
            if(!access)return route_fail(out,39);
            bool owned=false;const long owner=route_owner(g,b,owned,valid);
            const bool friendly=owned&&(owner==u.owner||route_relation(g,u.owner,owner,2,out));if(out[8])return false;
            if(!friendly&&step+1<length)return route_fail(out,40);
            if(!friendly&&u.type==g.dims[17])return route_fail(out,41);
            if(!combat&&!route_held(g,u.owner,b,out,valid)){if(out[8])return false;return route_fail(out,42);}
            if(e[10])return route_exception(out,e[10],e[11]);
            bool restricted=false,origin_restricted=false;long union_count=0;bool mountain=false;
            for(long k=0;k<K;++k){const bool in_node=route_static(g,2)[b*K+k],in_border=route_static(g,3)[pair*K+k];
                if(in_node||in_border){++union_count;if(k==g.dims[24])mountain=true;if(route_static(g,21)[k])restricted=true;}}
            if(mode==1){device const long* origin=route_static(g,0)+a*7;if(origin[5])return route_exception(out,origin[5],origin[6]);
                for(long k=0;k<K;++k)if(route_static(g,2)[a*K+k]&&route_static(g,21)[k])origin_restricted=true;
                if(restricted||origin_restricted||origin[1]||route_fortification(g,u.owner,a,b,out,valid))return out[8]?false:route_fail(out,43);
                if(out[8])return false;if(friendly)return route_fail(out,44);}
            bool stops=restricted;if(u.type==g.dims[18]&&union_count==1&&mountain)stops=false;
            if(stops){out[3]=1;if(step+1<length)return route_fail(out,45);}
            if(mode==4){
                if(!e[4]||length!=2||!route_empty(g.v,u.route,valid))return route_fail(out,46);
                if(combat?u.type!=g.dims[20]:!route_class(g,u,4))return route_fail(out,47);
                const bool blocked=route_narrow_blocked(g,u.owner,pair,b,combat,out,valid);if(out[8])return false;
                if(blocked)return route_fail(out,48);
                if(e[6])return route_exception(out,e[6],e[7]);device const long* counter_error=route_static(g,14)+pair*2;
                if(counter_error[0])return route_exception(out,counter_error[0],counter_error[1]);
                bool used=false;const long value=route_counter_flag(g,g.roots[5],route_static(g,13)[pair],used,valid);
                if(used&&value>=e[5])return route_fail(out,49);out[3]=1;
            }
            ++out[2];if(out[2]>u.remaining)return route_fail(out,50);
            out[4]=a;out[5]=b;out[6]=e[8];out[7]=e[9];
            for(long k=0;k<K;++k){nt[k]=route_static(g,2)[b*K+k];bt[k]=route_static(g,3)[pair*K+k];}
        }
    }
    if(!valid)return route_exception(out,3);
    if(strategic){for(long r=0;r<g.dims[6];++r)if(regions[r]){
            const long current=g.roots[6],error=g.national_errors[current*3];if(error)return route_player_exception(g,current,error,out,valid);
            const long player=g.national[current*3];if(player<0||player>=g.dims[8])return route_exception(out,3);
            const long flags=state_child(g.v,g.nations[current],10,valid);
            bool used=false;const long value=route_counter_flag(g,flags,route_static(g,15)[player*g.dims[6]+r],used,valid);
            device const long* capacity=route_static(g,12)+r*3;if(capacity[1])return route_exception(out,capacity[1],capacity[2]);
            const long maximum=capacity[0]+(route_tech(g,current,valid)?1:0);
            if(used&&value>=maximum)return route_fail(out,51);
        }out[3]=1;out[2]=0;}
    if(!valid)return route_exception(out,3);out[0]=1;return true;
}

kernel void resident_validate_routes(
 device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],
 device const uchar* prefix_bytes [[buffer(2)]],device const long* prefix_offsets [[buffer(3)]],
 device const uchar* suffix_bytes [[buffer(4)]],device const long* suffix_offsets [[buffer(5)]],device const long* usage [[buffer(6)]],
 device const long* source_errors [[buffer(7)]],device const long* data [[buffer(8)]],device const long* offsets [[buffer(9)]],
 device const uchar* counter_bytes [[buffer(10)]],device const long* indexes [[buffer(11)]],
 device const long* pairs [[buffer(12)]],device const long* pair_errors [[buffer(13)]],
 device const long* national [[buffer(14)]],device const long* national_errors [[buffer(15)]],
 device const long* declarations [[buffer(16)]],device const long* declaration_errors [[buffer(17)]],
 device const long* requests [[buffer(18)]],device const long* paths [[buffer(19)]],device long* output [[buffer(20)]],
 device const long* dims [[buffer(21)]],uint query [[thread_position_in_grid]]) {
    const long B=dims[0],C=dims[1],Z=dims[2],N=dims[3],K=dims[5],R=dims[6],S=dims[9],Q=dims[10],P=dims[11];
    if(long(query)>=Q)return;const long W=12+R+K*2;
    device long* out=output+ulong(query)*2*W;device long* scratch=out+W;
    for(long i=0;i<W*2;++i)out[i]=0;route_default(out);
    device const long* request=requests+ulong(query)*7;
    const long lane=request[0],id=request[1],count=request[2],mode=request[3],towed=request[5];
    if(lane<0||lane>=B||count<0||count>P||mode<0||mode>4||request[4]<0||request[4]>1||request[6]<0||request[6]>1){out[8]=4;out[10]=0;return;}
    device const long* base=indexes+ulong(lane)*(S+Z+N+13);device const long* roots=base+S+Z+N;
    if(source_errors[lane]||roots[12]){out[8]=3;out[10]=0;return;}
    bool valid=true;
    PackedStateView view=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix_bytes,prefix_offsets,
        dims[12],dims[13],suffix_bytes,suffix_offsets,dims[14],dims[15],usage,valid);
    if(!valid){out[8]=3;out[10]=0;return;}
    RouteView g={view,data,offsets,counter_bytes,roots,base,base+S,base+S+Z,
        pairs+ulong(lane)*N*N*7,pair_errors+ulong(lane)*N*N*7,national+ulong(lane)*N*3,national_errors+ulong(lane)*N*3,
        declarations+ulong(lane)*N*N,declaration_errors+ulong(lane)*N*N,dims};
    if(id<0||id>=S||g.units[id]<0){route_fail(out,1);return;}
    RouteUnit motor=route_unit(g,id,valid);device const long* path=paths+ulong(query)*P;
    if(!valid){out[8]=3;out[10]=0;return;}
    if(!request[6]){
        if(route_has_prefix(g.v,motor.commitments,"towed_by:",9,valid))route_fail(out,2);
        else route_single(g,motor,path,count,mode,request[4],out,out+12,out+12+R,out+12+R+K,valid);
    }else if(mode!=0||motor.type!=dims[19]||towed<0||towed>=S||g.units[towed]<0||towed==id)route_fail(out,3);
    else{
        RouteUnit artillery=route_unit(g,towed,valid);
        if(artillery.type!=dims[21]&&artillery.type!=dims[22]&&artillery.type!=dims[23])route_fail(out,4);
        else if(artillery.owner!=motor.owner||artillery.zone!=motor.zone||artillery.carried)route_fail(out,5);
        else{
            const bool continuing=route_set_join(g.v,motor.commitments,"towing:",7,towed,valid)&&
                                  route_set_join(g.v,artillery.commitments,"towed_by:",9,id,valid);
            if(!continuing&&(!route_empty(g.v,motor.route,valid)||!route_empty(g.v,artillery.route,valid)||motor.origin!=artillery.origin))route_fail(out,6);
            else if(route_other_pair(g.v,motor.commitments,"towing:",7,towed,valid))route_fail(out,7);
            else if(route_other_pair(g.v,artillery.commitments,"towed_by:",9,id,valid))route_fail(out,8);
            else if(!artillery.has_remaining||artillery.remaining<=0)route_fail(out,9);
            else if(route_single(g,motor,path,count,mode,request[4],out,out+12,out+12+R,out+12+R+K,valid)){
                artillery.has_remaining=true;artillery.remaining=min(2L,motor.has_remaining?motor.remaining:0L);
                if(route_single(g,artillery,path,count,mode,request[4],scratch,scratch+12,scratch+12+R,scratch+12+R+K,valid))out[3]=out[3]||scratch[3];
                else for(long i=0;i<W;++i)out[i]=scratch[i];
            }
        }
    }
    if(!valid){out[0]=0;out[8]=3;out[10]=0;}
    if(out[8]){
        const long error=out[8],message=out[9],detail=out[11];
        for(long i=0;i<W;++i)out[i]=0;route_default(out);
        out[8]=error;out[9]=message;out[11]=detail;if(error>=3)out[10]=0;
    }
}
"""

_library=None
_lock=threading.Lock()


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    return _library


@lru_cache(maxsize=16)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device="mps")


@lru_cache(maxsize=1)
def _dummy():return torch.zeros(1,dtype=torch.int64,device="mps")


class ResidentRoutes:
    def __init__(self,state_context,native_context,*,relations_context=None):
        if _device(state_context.device).type!="mps":raise ValueError("Resident route execution requires explicit Apple MPS; no CPU fallback")
        if state_context.definition_fingerprint!=native_context.definition_fingerprint:raise ValueError("Route definition differs from resident state")
        self.state_context,self.native_context=state_context,native_context
        self.zones=tuple(native_context.zones);self.nations=tuple(native_context.nations);self.players=tuple(native_context.players)
        self.unit_types=tuple(native_context.unit_types);self.terrains=tuple(native_context.terrains);self.regions=tuple(native_context.regions)
        self.facilities=tuple(native_context.facility_ids);self.exception_messages=tuple(native_context.exception_messages)
        self._special=tuple(self.unit_types.index(name) if name in self.unit_types else -1 for name in
            ("militia","cavalry","motorized_infantry","marine","artillery","advanced_artillery","anti_aircraft_artillery"))
        self._terrain_special=tuple(self.terrains.index(name) if name in self.terrains else -1 for name in ("mountain","impassable"))
        self.relations_context=relations_context or ResidentPoliticalRelations(state_context,native_context.relations_context)
        if self.relations_context.nation_ids!=self.nations or self.relations_context.player_ids!=self.players:
            raise ValueError("Route and political axes must be identical")
        self.declaration_context=ResidentLandAttackDeclarations(self.relations_context)
        methods=("node_array","edge_array","node_terrain_array","border_terrain_array","river_bank_array","crossing_sea_array",
            "bank_unknown_array","crossing_missing_array","home_array","class_array","fort_array","fort_error_array","capacity_array",
            "crossing_counter_array","crossing_counter_error_array","rail_counter_array","counter_offsets")
        fields=[torch.tensor(getattr(native_context,name)(),dtype=torch.int64).flatten() for name in methods]
        for names in (self.zones,self.nations,self.unit_types,self.facilities):
            fields.append(torch.tensor(state_context.prefix_lookup_ids(names),dtype=torch.int64))
        restricted={"mountain","desert","jungle","marsh","tundra","ice","tundra_ice"}
        fields.append(torch.tensor([name in restricted for name in self.terrains],dtype=torch.int64))
        blitz={"light_armor","medium_armor","t_34","heavy_armor","tiger_i","panzergrenadier"}
        fields.append(torch.tensor([name in blitz for name in self.unit_types],dtype=torch.int64))
        # One-time direct immutable native definition traversal, not a game JSON
        # conversion. Structured Record11/Sequence/String tags are versioned by
        # DeviceStateContext and rejected rather than guessed when unsupported.
        definition=state_context.native.record_array()
        if tuple(definition[0,:4])!=(10,11,0,0):raise ValueError("Unsupported frozen definition record schema")
        children=[];cursor=1
        for _ in range(11):
            children.append(cursor);end=int(definition[cursor,4])
            if not cursor<end<=len(definition):raise ValueError("Invalid immutable definition subtree")
            cursor=end
        turns=children[6]
        if int(definition[turns,0])!=6:raise ValueError("Frozen national turn order is not a sequence")
        namespace={int(sid):index for index,sid in enumerate(state_context.prefix_lookup_ids(self.nations))}
        order=[];cursor=turns+1
        for _ in range(int(definition[turns,1])):
            if int(definition[cursor,0])!=5 or int(definition[cursor,1]) not in namespace:raise ValueError("Unknown turn-order national identity")
            order.append(namespace[int(definition[cursor,1])]);cursor=int(definition[cursor,4])
        self.turn_count=len(order);fields.append(torch.tensor(order,dtype=torch.int64))
        offsets=[];total=0
        for field in fields:offsets.append(total);total+=field.numel()
        if len(fields)!=len(STATIC_FIELDS):raise RuntimeError("Movement static field layout mismatch")
        self.data=torch.cat(fields).to(state_context.device)
        self.offsets=torch.tensor(offsets,dtype=torch.int64,device=state_context.device)
        self.counter_bytes=torch.tensor(native_context.counter_bytes(),dtype=torch.uint8,device=state_context.device)
        self._prepared=None

    def _dims(self,state,Q=0,P=0):
        return (state.lane_count,state.records.shape[1],len(self.zones),len(self.nations),len(self.unit_types),len(self.terrains),
            len(self.regions),len(self.facilities),len(self.players),state.context.string_count+state.string_offsets.numel()-1,Q,P,
            state.context.string_count,state.context.string_bytes.numel(),state.string_offsets.numel()-1,state.string_bytes.numel(),
            self.turn_count,*self._special,*self._terrain_special)

    def prepare(self,state,*,relations=None,declarations=None):
        state._metadata();_device(state.device)
        if state.context.identity!=self.state_context.identity or state.device!=self.state_context.device:raise ValueError("Route wire context/device differs")
        current=self._prepared
        if (current is not None and current.source is state and
            (relations is None or current.relations is relations) and (declarations is None or current.declarations is declarations)):
            return current
        relations=relations or self.relations_context.compute(state)
        if relations.source is not state:raise ValueError("Route relations belong to another complete state")
        declarations=declarations or self.declaration_context.compute(state,relations=relations)
        if declarations.source is not state or declarations.relations is not relations:raise ValueError("Route declarations belong to another complete state/relations")
        dims=self._dims(state);B,C,Z,N,S=dims[0],dims[1],dims[2],dims[3],dims[9]
        indexes=torch.full((B,S+Z+N+13),-1,dtype=torch.int64,device=state.device)
        if B:
            args=(state.records,state.lengths,state.sections,state.context.string_bytes,state.context.string_offsets,
                state.string_bytes,state.string_offsets,state.suffix_usage,state.errors,self.data,self.offsets,indexes,_dimensions(dims))
            if any(not value.is_contiguous() for value in args):raise ValueError("Route preparation buffers must be contiguous")
            _kernels().prepare_route_indexes(*(value if value.numel() else _dummy() for value in args),threads=B)
        result=PreparedRoutes(state,relations,declarations,indexes);self._prepared=result;return result

    def query(self,state,requests,*,prepared=None,relations=None,declarations=None):
        state._metadata();_device(state.device)
        if state.context.identity!=self.state_context.identity or state.device!=self.state_context.device:raise ValueError("Route wire context/device differs")
        if not isinstance(requests,TensorRouteRequests):raise TypeError("Route queries require resident TensorRouteRequests")
        if (not isinstance(requests.metadata,torch.Tensor) or requests.metadata.ndim!=2 or requests.metadata.shape[1]!=7 or
            not isinstance(requests.paths,torch.Tensor) or requests.paths.ndim!=2 or requests.paths.shape[0]!=requests.metadata.shape[0]):
            raise ValueError("Route metadata and ordered paths require complete matching [query,field] buffers")
        for value in (requests.metadata,requests.paths):
            if value.dtype!=torch.int64 or value.device!=state.device or not value.is_contiguous():raise ValueError("Route requests must be contiguous resident int64 buffers")
        prepared=prepared or self.prepare(state,relations=relations,declarations=declarations)
        if prepared.source is not state:raise ValueError("Prepared route indexes belong to a stale/foreign complete state")
        Q,P=requests.paths.shape;dims=self._dims(state,Q,P);B,N,R,K=dims[0],dims[3],dims[6],dims[5]
        if (prepared.relations.source is not state or prepared.declarations.source is not state or
            prepared.declarations.relations is not prepared.relations):raise ValueError("Prepared route political data belong to a stale/foreign complete state")
        if (prepared.indexes.dtype!=torch.int64 or prepared.indexes.device!=state.device or
            prepared.indexes.shape!=(B,dims[9]+dims[2]+N+13) or not prepared.indexes.is_contiguous()):
            raise ValueError("Prepared route indexes have an invalid layout")
        for value,shape in ((prepared.relations.pairs,(B,N,N,7)),(prepared.relations.pair_errors,(B,N,N,7)),
            (prepared.relations.nations,(B,N,3)),(prepared.relations.nation_errors,(B,N,3)),
            (prepared.declarations.allowed,(B,N,N)),(prepared.declarations.errors,(B,N,N))):
            if value.dtype!=torch.int64 or value.device!=state.device or value.shape!=shape or not value.is_contiguous():
                raise ValueError("Route political buffers must preserve exact packed axes, dtype and device")
        W=12+R+K*2;work=torch.empty((Q,2,W),dtype=torch.int64,device=state.device)
        if Q:
            args=(state.records,state.lengths,state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,
                state.suffix_usage,state.errors,self.data,self.offsets,self.counter_bytes,prepared.indexes,
                prepared.relations.pairs,prepared.relations.pair_errors,prepared.relations.nations,prepared.relations.nation_errors,
                prepared.declarations.allowed,prepared.declarations.errors,requests.metadata,requests.paths,work,_dimensions(dims))
            if any(not value.is_contiguous() for value in args):raise ValueError("Route execution requires contiguous source buffers")
            _kernels().resident_validate_routes(*(value if value.numel() else _dummy() for value in args),threads=Q)
        out=work[:,0]
        return ResidentRouteResult(state,requests,out[:,:12],out[:,12:12+R],out[:,12+R:12+R+K],out[:,12+R+K:],state.context.identity)

    def pack_requests(self,state,requests):
        """Explicit host authoring boundary; hot callers produce these tensors directly."""
        if state.context.identity!=self.state_context.identity:raise ValueError("Request pool belongs to another wire context")
        used,byte_count=state.suffix_usage.detach().cpu().tolist()
        prefix=bytes(state.context.native.string_bytes());po=list(state.context.native.string_offsets())
        suffix=bytes(state.string_bytes[:byte_count].detach().cpu().tolist());so=state.string_offsets[:used+1].detach().cpu().tolist()
        strings=[prefix[a:b].decode("utf8") for a,b in zip(po,po[1:])]+[suffix[a:b].decode("utf8") for a,b in zip(so,so[1:])]
        ids={name:index for index,name in enumerate(strings)};zones={name:index for index,name in enumerate(self.zones)}
        rows=[];paths=[]
        for request in requests:
            if not isinstance(request,dict):raise TypeError("Host route requests must expose named complete fields")
            lane=request.get("lane",0);unit=request["unit"];path=request["path"];mode=request.get("mode","ordinary");combat=request.get("combat",False);towed=request.get("towed")
            if (type(lane) is not int or not isinstance(unit,str) or not isinstance(path,(list,tuple)) or
                any(not isinstance(zone,str) for zone in path) or mode not in MODES or type(combat) is not bool or
                (towed is not None and not isinstance(towed,str))):raise ValueError("Invalid host route request field type")
            rows.append((lane,ids.get(unit,-1),len(path),MODES.index(mode),int(combat),ids.get(towed,-1),int(towed is not None)))
            paths.append([zones.get(zone,-1) for zone in path])
        Q=len(rows);P=max(map(len,paths),default=0)
        path_tensor=torch.full((Q,P),-1,dtype=torch.int64)
        for index,path in enumerate(paths):
            if path:path_tensor[index,:len(path)]=torch.tensor(path,dtype=torch.int64)
        return TensorRouteRequests(torch.tensor(rows,dtype=torch.int64).reshape(Q,7).to(state.device),path_tensor.to(state.device))

    def inspect(self,result):
        """Explicit host display of all RouteResult fields and error status."""
        if result.context_identity!=self.state_context.identity:raise ValueError("Foreign route result context")
        core=result.core.detach().cpu().tolist();regions=result.regions.detach().cpu().tolist()
        nodes=result.node_terrain.detach().cpu().tolist();borders=result.border_terrain.detach().cpu().tolist()
        output=[]
        for row,rs,ns,bs in zip(core,regions,nodes,borders,strict=True):
            message=self.exception_messages[row[9]] if row[9]>=0 else ("Malformed resident route input" if row[8]>=3 else "")
            if row[8] and row[9]==-2:message="Native political relation/declaration query failed"
            if row[8] and row[9]==-3:message="Political nation has no controlling player: "+self.nations[row[11]]
            if row[8] and row[9]==-4:message="Invalid temporary warlord defense player"
            if row[8] and row[9]==-5:message="JSON value is not a string"
            output.append({"allowed":bool(row[0]),"reason":REASONS[row[1]],"cost":row[2],"exhausts_movement":bool(row[3]),
                "regions":{name for name,active in zip(self.regions,rs,strict=True) if active},
                "approach":{"from":self.zones[row[4]] if row[4]>=0 else "","to":self.zones[row[5]] if row[5]>=0 else "",
                    "node_terrain":{name for name,active in zip(self.terrains,ns,strict=True) if active},
                    "border_terrain":{name for name,active in zip(self.terrains,bs,strict=True) if active},"river":bool(row[6]),"river_known":bool(row[7])},
                "exception":row[8],"message":message,"supported":bool(row[10])})
        return tuple(output)
