"""Changed-footprint State validation for the recruitment-choice transaction.

This is deliberately not an importer or a general validator for arbitrary State
data. ``before`` is a native-validated source, and ``after`` must be the output of
the exact recruitment-choice, political-refresh, income, optional training-reset
and screening-forward writers. Those writers preserve the definition, territory
inventory/metadata, rails, turn snapshots, completed turns and history. The outer
Engine transaction checks its unchanged Clock, terminal and execution RNG. Cargo
closure and all finite generic JSON are guaranteed by the typed checked writers.

Here we close the changed cross-reference invariants: surviving/new units and
movement, newly inserted construction, repairs, controllers, decisions, battles,
the new surrender chance and the still-contextual order interface. No catalog
statistics or legal menus are regenerated. A nonempty visited-configuration
registry in unwrapped CoreRules needs the separate naval configuration port and
is explicitly unsupported; it is never accepted by assuming its bytes suffice.
"""
from dataclasses import dataclass
from enum import IntFlag
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch, _device
from .resident_relations import SOURCE as RELATIONS_SOURCE


class RecruitmentOutputError(IntFlag):
    PACKED = 1
    INTERFACE = 2
    NATION = 4
    UNIT = 8
    CONSTRUCTION = 16
    REPAIR = 32
    CONTINUATION = 64
    DECISION = 128
    ENTITLEMENT = 256
    OPTION = 512
    BATTLE = 1024
    CHANCE = 2048
    FOOTPRINT = 4096


class RecruitmentOutputUnsupported(IntFlag):
    VISITED_CONFIGURATION = 1
    CONTROLLER_CYCLE = 2


@dataclass(frozen=True)
class RecruitmentOutputValidation:
    source: DeviceStateBatch
    state: DeviceStateBatch
    errors: torch.Tensor
    unsupported: torch.Tensor
    valid: torch.Tensor


SOURCE = RELATIONS_SOURCE + r'''
inline bool rov_nonempty(thread const PackedStateView& v,long id,thread bool& ok){
 long a,b;bool prefix;relations_span(v,id,a,b,prefix,ok);return ok&&b>a;
}
inline bool rov_prefix(thread const PackedStateView& v,long id,constant char* text,long size,thread bool& ok){
 long a,b;bool prefix;relations_span(v,id,a,b,prefix,ok);if(!ok||b-a<size)return false;
 device const uchar* bytes=prefix?v.prefix_bytes:v.suffix_bytes;
 for(long i=0;i<size;++i)if(bytes[a+i]!=uchar(text[i]))return false;return true;
}
inline bool rov_political(thread const PackedStateView& v,long id,thread bool& ok){
 return rov_prefix(v,id,"politics_",9,ok)||rov_prefix(v,id,"warlord_",8,ok)||rov_prefix(v,id,"truce_",6,ok)||
        rov_prefix(v,id,"influence_",10,ok)||rov_prefix(v,id,"recruitment_",12,ok);
}
inline long rov_int(thread const PackedStateView& v,long root,thread bool& ok){
 const long value=state_signed_value(v,root,ok);if(value<INT_MIN||value>INT_MAX)ok=false;return value;
}
inline bool rov_nation(thread const PackedStateView& v,long nations,long id,thread bool& ok){
 return state_map_find_id(v,nations,id,ok)>=0;
}
inline bool rov_optional_int(thread const PackedStateView& v,long root,thread bool& present,thread long& value,thread bool& ok){
 const long child=state_optional(v,root,present,ok);value=present?rov_int(v,child,ok):0;return ok;
}
inline bool rov_interface(thread const PackedStateView& v,long state,bool reset,thread long& unsupported,thread bool& ok){
 const long interface=state_child(v,state,17,ok);relations_container(v,interface,13,-1,ok);if(!ok)return false;
 const long size=state_record(v,interface)[1];if(!size)return !reset;
 if(size!=3)return false;
 const long schema=state_map_find_literal(v,interface,"schema",6,ok),
   visited=state_map_find_literal(v,interface,"visited_configurations",22,ok),
   declined=state_map_find_literal(v,interface,"declined_rail_requests",22,ok);
 if(schema<0||visited<0||declined<0)return false;
 if(!state_string_equals(v,schema,"campaign-orders-v1",18,ok))return false;
 relations_container(v,visited,12,-1,ok);relations_container(v,declined,12,-1,ok);if(!ok)return false;
 const long vc=state_record(v,visited)[1],dc=state_record(v,declined)[1];
 if(reset)return vc==0&&dc==0;
 if(vc)unsupported|=1;
 // All static keys, sender/current-nation, row types and signatures were
 // validated in the unchanged source interface. Only these two relationships
 // can change through the trusted helper chain.
 const long territories=state_child(v,state,1,ok),projects=state_child(v,state,5,ok);long cursor=declined+1;
 for(long i=0;ok&&i<dc;++i){relations_container(v,cursor,13,3,ok);
   const long parameters=state_map_find_literal(v,cursor,"parameters",10,ok),
     recipient=state_map_find_literal(v,cursor,"recipient",9,ok);
   if(parameters<0||recipient<0)return false;
   const long target=state_map_find_literal(v,parameters,"border",6,ok);
   if(target<0)return false;const long border=state_string_id(v,target,ok),owner=state_string_id(v,recipient,ok);
   const long territory=state_map_find_id(v,territories,border,ok);if(territory<0)return false;
   bool present=false;const long possessor=state_optional(v,state_child(v,territory,0,ok),present,ok);
   if(!present||state_string_id(v,possessor,ok)!=owner)return false;
   const long project=state_map_find_literal(v,parameters,"project",7,ok);
   if(project>=0&&state_map_find_id(v,projects,state_string_id(v,project,ok),ok)<0)return false;
   cursor=state_end(v,cursor,ok);
 }return ok&&cursor==state_end(v,declined,ok);
}
inline bool rov_unit_type(device const long* types,device const long* meta,device const long* damage,
 long U,long type,long value){
 const long index=relations_index(types,U,type);if(index<0)return false;
 for(long i=0;i<meta[index*4+1];++i)if(damage[(meta[index*4]+i)*19]==value)return true;return false;
}
inline bool rov_in_list(thread const PackedStateView& v,long root,long id,thread bool& ok){
 relations_container(v,root,6,-1,ok);if(!ok)return false;
 long at=root+1;for(long i=0;ok&&i<state_record(v,root)[1];++i){
   if(state_string_id(v,at,ok)==id)return true;at=state_end(v,at,ok);}return false;
}
inline bool rov_controller_cycle(device const long* meta,long N,long current){
 // Relations intentionally groups playerless graphs and cycle exhaustion into
 // error2. Distinguish only the latter here without invoking native recursion.
 // N is the complete national inventory, not an arbitrary traversal cap.
 for(long visit=0;visit<=N;++visit){
   if(current<0||current>=N||!meta[current*10]||meta[current*10+2]!=-1)return false;
   const long next=meta[current*10+1];if(next<0)return false;current=next;
 }return true;
}
kernel void validate_recruitment_output(
 device const long* before[[buffer(0)]],device const long* blengths[[buffer(1)]],device const long* bsections[[buffer(2)]],
 device const long* records[[buffer(3)]],device const long* lengths[[buffer(4)]],device const long* sections[[buffer(5)]],
 device const long* inherited[[buffer(6)]],device const bool* selected[[buffer(7)]],
 device const uchar* prefix[[buffer(8)]],device const long* poffsets[[buffer(9)]],
 device const uchar* suffix[[buffer(10)]],device const long* soffsets[[buffer(11)]],device const long* usage[[buffer(12)]],
 device const long* ids[[buffer(13)]],device const long* unit_types[[buffer(14)]],device const long* unit_meta[[buffer(15)]],
 device const long* damage[[buffer(16)]],device const long* facilities[[buffer(17)]],
 device const long* players[[buffer(18)]],device const long* player_errors[[buffer(19)]],device const long* metadata[[buffer(20)]],
 device long* errors[[buffer(21)]],device long* unsupported[[buffer(22)]],device const long* dims[[buffer(23)]],
 uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],BC=dims[2],N=dims[7],P=dims[8],U=dims[9],F=dims[10];
 if(long(lane)>=B)return;errors[lane]=unsupported[lane]=0;if(!selected[lane])return;
 bool ok=true;long error=0,capability=0;
 auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix,poffsets,dims[3],dims[4],suffix,soffsets,dims[5],dims[6],usage,ok);
 auto old=make_packed_state_view(before+ulong(lane)*BC*5,blengths[lane],BC,prefix,poffsets,dims[3],dims[4],suffix,soffsets,dims[5],dims[6],usage,ok);
 if(inherited[lane])ok=false;
 relations_container(v,0,10,2,ok);relations_container(old,0,10,2,ok);
 const long state=state_child(v,0,0,ok),source=state_child(old,0,0,ok);
 relations_container(v,state,10,19,ok);relations_container(old,source,10,19,ok);
 if(!ok){errors[lane]=1;return;}
 const bool interface_ok=rov_interface(v,state,dims[11]!=0,capability,ok);if(!interface_ok)error|=2;
 const long nations=state_child(v,state,0,ok),oldnations=state_child(old,source,0,ok),
   units=state_child(v,state,2,ok),oldunits=state_child(old,source,2,ok),
   facilities_map=state_child(v,state,3,ok),rails=state_child(v,state,4,ok),
   projects=state_child(v,state,5,ok),oldprojects=state_child(old,source,5,ok),repairs=state_child(v,state,6,ok),
   politics=state_child(v,state,8,ok),decisions=state_child(v,state,11,ok),battles=state_child(v,state,12,ok),order=state_child(v,state,13,ok);
 relations_container(v,nations,7,-1,ok);relations_container(old,oldnations,7,-1,ok);
 relations_container(v,units,7,-1,ok);relations_container(old,oldunits,7,-1,ok);
 relations_container(v,facilities_map,7,-1,ok);relations_container(v,rails,7,-1,ok);
 relations_container(v,projects,7,-1,ok);relations_container(old,oldprojects,7,-1,ok);relations_container(v,repairs,7,-1,ok);
 relations_container(v,politics,10,11,ok);relations_container(v,decisions,6,-1,ok);
 relations_container(v,battles,7,-1,ok);relations_container(v,order,6,-1,ok);
 if(!ok){errors[lane]=error|1;unsupported[lane]=capability;return;}
 if(state_record(v,nations)[1]!=state_record(old,oldnations)[1])error|=4096;
 long cursor=nations+1;
 for(long i=0;ok&&i<state_record(v,nations)[1];++i){
   const long id=state_string_id(v,cursor,ok),nation=state_end(v,cursor,ok);relations_container(v,nation,10,12,ok);
   if(state_map_find_id(old,oldnations,id,ok)<0)error|=4096;
   bool present=false;long child=state_optional(v,state_child(v,nation,0,ok),present,ok);
   if(present&&!rov_nation(v,nations,state_string_id(v,child,ok),ok))error|=4;
   child=state_optional(v,state_child(v,nation,1,ok),present,ok);
   if(present&&relations_index(ids+N,P,state_string_id(v,child,ok))<0)error|=4;
   child=state_optional(v,state_child(v,nation,2,ok),present,ok);
   if(present&&!rov_nonempty(v,state_string_id(v,child,ok),ok))error|=4;
   if(!rov_nonempty(v,state_string_id(v,state_child(v,nation,3,ok),ok),ok))error|=4;
   long value=0;rov_optional_int(v,state_child(v,nation,4,ok),present,value,ok);if(present&&value<0)error|=4;
   // Allies are rebuilt by refresh; technology and war inventories are unchanged.
   const long allies=state_child(v,nation,9,ok);relations_container(v,allies,8,-1,ok);long ally=allies+1;
   for(long j=0;ok&&j<state_record(v,allies)[1];++j){const long other=state_string_id(v,ally,ok);
     if(other==id||!rov_nation(v,nations,other,ok))error|=4;ally=state_end(v,ally,ok);}
   cursor=state_end(v,nation,ok);
 }
 cursor=units+1;
 for(long i=0;ok&&i<state_record(v,units)[1];++i){const long id=state_string_id(v,cursor,ok),unit=state_end(v,cursor,ok);
   relations_container(v,unit,10,14,ok);const long stored=state_string_id(v,state_child(v,unit,0,ok),ok),
     type=state_string_id(v,state_child(v,unit,1,ok),ok),owner=state_string_id(v,state_child(v,unit,2,ok),ok),
     value=rov_int(v,state_child(v,unit,10,ok),ok);
   if(id!=stored||!rov_nonempty(v,id,ok)||!rov_nonempty(v,type,ok)||!rov_nation(v,nations,owner,ok)||value<0||
      !rov_unit_type(unit_types,unit_meta,damage,U,type,value))error|=8;
   bool remaining_present=false,allowance_present=false;long remaining=0,allowance=0;
   rov_optional_int(v,state_child(v,unit,4,ok),remaining_present,remaining,ok);
   rov_optional_int(v,state_child(v,unit,5,ok),allowance_present,allowance,ok);
   if(!remaining_present||!allowance_present||remaining<0||allowance<0||remaining>allowance)error|=8;
   if(state_map_find_id(v,facilities_map,id,ok)>=0||state_map_find_id(v,rails,id,ok)>=0)error|=8;
   cursor=state_end(v,unit,ok);
 }
 cursor=projects+1;
 for(long i=0;ok&&i<state_record(v,projects)[1];++i){const long id=state_string_id(v,cursor,ok),project=state_end(v,cursor,ok);
   relations_container(v,project,10,8,ok);const long stored=state_string_id(v,state_child(v,project,0,ok),ok),
     owner=state_string_id(v,state_child(v,project,1,ok),ok),type=state_string_id(v,state_child(v,project,2,ok),ok);
   if(id!=stored||!rov_nonempty(v,id,ok)||!rov_nonempty(v,type,ok)||!rov_nation(v,nations,owner,ok))error|=16;
   // A collided emplace retains an old type, but surrender may first erase a
   // project and then reinsert the SAME key as an award with a different type.
   // Validate absent OR changed types against the complete catalog inventory.
   const long prior=state_map_find_id(old,oldprojects,id,ok);
   const bool changed_type=prior<0||state_string_id(old,state_child(old,prior,2,ok),ok)!=type;
   if(changed_type&&relations_index(unit_types,U,type)<0&&relations_index(facilities,F,type)<0)error|=16;
   if(rov_int(v,state_child(v,project,4,ok),ok)<1||rov_int(v,state_child(v,project,5,ok),ok)<0)error|=16;
   const long payments=state_child(v,project,6,ok);relations_container(v,payments,6,-1,ok);long payment=payments+1;
   for(long j=0;ok&&j<state_record(v,payments)[1];++j){if(rov_int(v,payment,ok)<0)error|=16;payment=state_end(v,payment,ok);}
   cursor=state_end(v,project,ok);
 }
 cursor=repairs+1;
 for(long i=0;ok&&i<state_record(v,repairs)[1];++i){const long repair=state_end(v,cursor,ok);relations_container(v,repair,10,7,ok);
   const long target=state_string_id(v,state_child(v,repair,2,ok),ok);
   if(state_map_find_id(v,units,target,ok)<0&&state_map_find_id(v,facilities_map,target,ok)<0&&state_map_find_id(v,rails,target,ok)<0&&
      state_map_find_id(v,state_child(v,state,1,ok),target,ok)<0&&state_map_find_id(v,projects,target,ok)<0)error|=32;
   cursor=state_end(v,repair,ok);
 }
 const long pending=state_child(v,politics,10,ok);relations_container(v,pending,7,-1,ok);cursor=decisions+1;
 for(long i=0;ok&&i<state_record(v,decisions)[1];++i){const long decision=cursor;relations_container(v,decision,10,6,ok);
   const long id=state_string_id(v,state_child(v,decision,0,ok),ok),kind=state_string_id(v,state_child(v,decision,1,ok),ok),
     nation=state_string_id(v,state_child(v,decision,2,ok),ok),continuation=state_string_id(v,state_child(v,decision,4,ok),ok);
   if(!rov_nonempty(v,id,ok)||!rov_nonempty(v,kind,ok))error|=128;
   long previous=decisions+1;for(long j=0;ok&&j<i;++j){if(state_string_id(v,state_child(v,previous,0,ok),ok)==id)error|=128;previous=state_end(v,previous,ok);}
   if(rov_political(v,kind,ok)&&state_map_find_id(v,pending,continuation,ok)<0)error|=64;
   const long ni=relations_index(ids,N,nation);long player=-1;
   if(ni<0||!rov_nation(v,nations,nation,ok))error|=256;
   else {const long pe=player_errors[(ulong(lane)*N+ni)*3];
     if(pe==3)error|=1;
     else if(pe==2&&rov_controller_cycle(metadata+ulong(lane)*N*10,N,ni))capability|=2;
     else if(pe)error|=256;
     else {const long pi=players[(ulong(lane)*N+ni)*3];if(pi<0||pi>=P)error|=256;else player=ids[N+pi];}}
   const long options=state_child(v,decision,5,ok);relations_container(v,options,6,-1,ok);long action=options+1;
   for(long j=0;ok&&j<state_record(v,options)[1];++j){relations_container(v,action,10,6,ok);
     const long aid=state_string_id(v,state_child(v,action,0,ok),ok),akind=state_string_id(v,state_child(v,action,1,ok),ok);
     if(!rov_nonempty(v,aid,ok)||!rov_nonempty(v,akind,ok))error|=512;
     long previous_action=options+1;for(long k=0;ok&&k<j;++k){if(state_string_id(v,state_child(v,previous_action,0,ok),ok)==aid)error|=512;previous_action=state_end(v,previous_action,ok);}
     const long actor=state_string_id(v,state_child(v,action,2,ok),ok),owner=state_string_id(v,state_child(v,action,3,ok),ok);
     bool present=false;const long ref=state_optional(v,state_child(v,action,4,ok),present,ok);
     if(owner!=nation||!present||(player>=0&&actor!=player))error|=256;
     if(present&&state_string_id(v,ref,ok)!=id)error|=256;
     const long params=state_child(v,action,5,ok);if(ok&&state_record(v,params)[0]!=13)error|=512;
     action=state_end(v,action,ok);
   }cursor=state_end(v,decision,ok);
 }
 // Removal filters existing participants; truce queues new mandatory battles.
 cursor=battles+1;
 for(long i=0;ok&&i<state_record(v,battles)[1];++i){const long battle=state_end(v,cursor,ok);relations_container(v,battle,10,10,ok);
   const long attackers=state_child(v,battle,5,ok),defenders=state_child(v,battle,6,ok);
   for(long side=0;ok&&side<2;++side){const long list=side?defenders:attackers;relations_container(v,list,6,-1,ok);long at=list+1;
     for(long j=0;ok&&j<state_record(v,list)[1];++j){const long id=state_string_id(v,at,ok);
       if(state_map_find_id(v,units,id,ok)<0||(side&&rov_in_list(v,attackers,id,ok)))error|=1024;
       long previous=list+1;for(long k=0;ok&&k<j;++k){if(state_string_id(v,previous,ok)==id)error|=1024;previous=state_end(v,previous,ok);}
       at=state_end(v,at,ok);}}
   cursor=state_end(v,battle,ok);
 }
 cursor=order+1;
 for(long i=0;ok&&i<state_record(v,order)[1];++i){const long id=state_string_id(v,cursor,ok);
   if(state_map_find_id(v,battles,id,ok)<0)error|=1024;long previous=order+1;
   for(long j=0;ok&&j<i;++j){if(state_string_id(v,previous,ok)==id)error|=1024;previous=state_end(v,previous,ok);}cursor=state_end(v,cursor,ok);}
 bool present=false;const long chance=state_optional(v,state_child(v,state,14,ok),present,ok);
 if(present){relations_container(v,chance,10,5,ok);
   const long id=state_string_id(v,state_child(v,chance,0,ok),ok),purpose=state_string_id(v,state_child(v,chance,1,ok),ok),
     nation=state_string_id(v,state_child(v,chance,2,ok),ok),continuation=state_string_id(v,state_child(v,chance,3,ok),ok),
     dice=state_child(v,chance,4,ok);relations_container(v,dice,6,-1,ok);
   if(!rov_nonempty(v,id,ok)||!rov_nonempty(v,purpose,ok)||!rov_nation(v,nations,nation,ok)||state_record(v,dice)[1]==0)error|=2048;
   if(rov_political(v,purpose,ok)&&state_map_find_id(v,pending,continuation,ok)<0)error|=64;
   long die=dice+1;for(long i=0;ok&&i<state_record(v,dice)[1];++i){relations_container(v,die,10,4,ok);
     const long sides=rov_int(v,state_child(v,die,0,ok),ok),rerolls=rov_int(v,state_child(v,die,3,ok),ok),faces=state_child(v,die,2,ok);
     if(sides<2||rerolls<0)error|=2048;relations_container(v,faces,8,-1,ok);long face=faces+1;
     for(long j=0;ok&&j<state_record(v,faces)[1];++j){const long value=rov_int(v,face,ok);if(value<1||value>sides)error|=2048;face=state_end(v,face,ok);}
     die=state_end(v,die,ok);}}
 if(!ok)error|=1;errors[lane]=error;unsupported[lane]=capability;
}
'''

_library = None
_lock = threading.Lock()


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:
                _library = torch.mps.compile_shader(SOURCE)
    return _library


@lru_cache(maxsize=32)
def _dimensions(values):
    return torch.tensor(values, dtype=torch.int64, device="mps")


@lru_cache(maxsize=1)
def _dummy():
    return torch.zeros(1, dtype=torch.int64, device="mps")


def _facility_ids(context):
    """Read immutable native typed catalog metadata once; never parse State JSON."""
    rows = context.native.record_array()

    def child(root, index):
        at = root + 1
        for _ in range(index):
            at = int(rows[at, 4])
        return at

    def find(root, token):
        at = root + 1
        for _ in range(int(rows[root, 1])):
            value = int(rows[at, 4])
            if int(rows[at, 1]) == token:
                return value
            at = int(rows[value, 4])
        return -1

    catalog = child(0, 4)
    if int(rows[catalog, 0]) == 0:
        return ()
    facility_key, id_key = map(int, context.prefix_lookup_ids(("facilities", "id")))
    ids = set()
    at = catalog + 1
    for _ in range(int(rows[catalog, 1])):
        document = int(rows[at, 4])
        facilities = find(document, facility_key)
        if facilities >= 0:
            item = facilities + 1
            for _ in range(int(rows[facilities, 1])):
                value = find(item, id_key)
                if value < 0 or int(rows[value, 0]) != 5:
                    raise ValueError("Frozen native facility catalog has no typed identity")
                ids.add(int(rows[value, 1]))
                item = int(rows[item, 4])
        at = int(rows[document, 4])
    return tuple(sorted(ids))


class ResidentRecruitmentOutputValidation:
    def __init__(self, state_context, catalog_stats, relations):
        if (_device(state_context.device).type != "mps" or catalog_stats.state_context is not state_context or
                relations.state_context is not state_context):
            raise ValueError("Recruitment output validation requires the exact shared Apple GPU contexts")
        self.state_context = state_context
        self.catalog_stats = catalog_stats
        self.relations = relations
        self.unit_types = catalog_stats.tokens.index_select(0, catalog_stats.unit_token).contiguous()
        self.facilities = torch.tensor(_facility_ids(state_context), dtype=torch.int64, device=state_context.device)

    def validate(self, before, after, selected=None, *, training_reset_applied):
        """Check only the documented trusted helper footprint, without host reads.

        The caller must check the unchanged Clock/terminal/RNG and publish neither
        state nor Event if any selected lane has errors or unsupported capability.
        Results for unselected lanes remain zero, including all lazy player errors.
        """
        if type(training_reset_applied) is not bool:
            raise ValueError("Training reset application must be an explicit bool")
        for state in (before, after):
            if not isinstance(state, DeviceStateBatch) or state.context is not self.state_context:
                raise ValueError("Recruitment validation source context differs")
            state._metadata()
            _device(state.device)
        if before.lane_count != after.lane_count:
            raise ValueError("Recruitment validation lane inventories differ")
        B, C = after.records.shape[:2]
        if selected is None:
            selected = torch.ones(B, dtype=torch.bool, device=after.device)
        if (not isinstance(selected, torch.Tensor) or selected.dtype != torch.bool or selected.shape != (B,) or
                selected.device != after.device or not selected.is_contiguous()):
            raise ValueError("Recruitment validation selection must be contiguous resident bool[lane]")
        # Relations computes exact native player resolution. Only final pending
        # decisions consume its player results: unused neutral/cyclic nations do
        # not reject an otherwise valid output. There is no native hot callback.
        relations = self.relations.compute(after)
        values = (before.records, before.lengths, before.sections, after.records, after.lengths, after.sections,
            before.errors | after.errors, selected, after.context.string_bytes, after.context.string_offsets,
            after.string_bytes, after.string_offsets, after.suffix_usage, self.relations.ids, self.unit_types,
            self.catalog_stats.unit, self.catalog_stats.state, self.facilities, relations.nations, relations.nation_errors, relations.metadata)
        if any(value.device != after.device or not value.is_contiguous() for value in values):
            raise ValueError("Recruitment validation buffers must remain complete and contiguous")
        errors = torch.zeros(B, dtype=torch.int64, device=after.device)
        unsupported = torch.zeros_like(errors)
        if B:
            dims = _dimensions((B, C, before.records.shape[1], after.context.string_count,
                after.context.string_bytes.numel(), after.string_offsets.numel()-1, after.string_bytes.numel(),
                len(self.relations.nation_ids), len(self.relations.player_ids), self.unit_types.numel(),
                self.facilities.numel(), int(training_reset_applied)))
            _kernels().validate_recruitment_output(*(value if value.numel() else _dummy() for value in values),
                errors, unsupported, dims, threads=B)
        return RecruitmentOutputValidation(before, after, errors, unsupported, selected & (errors == 0) & (unsupported == 0))
