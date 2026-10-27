"""Exact stored recruitment-choice effects using one cached current menu.

This calls the complete political refresh after placement/free work, as the
original rule helper does. Income, TrainingRules hooks, Engine validation,
Events, calendar and execution RNG are deliberately outside this effect seam.
The selected stored Action6 remains available through source/option roots for
the later Engine transaction. A public roll-dispatch entry is a separate
capability, not misreported as this private choice rule's result.
"""
from dataclasses import dataclass,fields,replace
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_state_edits import replace_subtrees
from .device_map_edits import SOURCE as MAP_SOURCE,MapMode,build_map_edits,build_sequence_splices,commit_container_edits
from .resident_chance_io import _pool
from .resident_recruitment import RecruitmentMenu
from .resident_political_refresh import PoliticalRefreshCapacities

LITERALS=("recruitment_choice","beneficiary","recruitment_place_infantry","recruitment_place_militia",
          "recruitment_advance_ship","recruitment_repair_facility","zone","zones","project","facility",
          "infantry","militia","completed")
UNSUPPORTED_ENTRY=6


@dataclass(frozen=True)
class RecruitmentChoiceCapacities:
    creation_capacity:int
    creation_id_byte_capacity:int
    political_refresh:PoliticalRefreshCapacities

    def validate(self,state,arena):
        if type(self.creation_capacity) is not int or self.creation_capacity<0 or type(self.creation_id_byte_capacity) is not int or self.creation_id_byte_capacity<0:
            raise ValueError("Recruitment creation capacities must be explicit nonnegative allocations")
        if not isinstance(self.political_refresh,PoliticalRefreshCapacities):raise TypeError("Recruitment choice needs complete political-refresh capacities")
        self.political_refresh.validate(state);self.political_refresh.validate(arena)


@dataclass(frozen=True)
class RecruitmentChoiceResult:
    source:DeviceStateBatch
    state:DeviceStateBatch
    errors:torch.Tensor
    handled:torch.Tensor
    unsupported_entry:torch.Tensor
    selected_option_roots:torch.Tensor
    first_failure_stage:torch.Tensor
    stage_errors:dict
    required:dict
    required_state_capacity:torch.Tensor
    required_block_capacity:torch.Tensor
    required_string_usage:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE=MAP_SOURCE+r'''
inline bool rc_container(thread const PackedStateView& v,long n,long tag,long count,thread bool& ok){
 const long end=state_end(v,n,ok);if(!ok)return false;device const long* r=state_record(v,n);
 if(r[0]!=tag||r[1]<0||r[1]>(tag==7||tag==13?(end-n-1)/2:end-n-1)||(count>=0&&r[1]!=count)||r[2]||r[3])ok=false;return ok;
}
inline bool rc_prefix(thread const PackedStateView& v,long id,constant char* text,long size,thread bool& ok){
 if(id<0||id>=v.prefix_count+v.suffix_count){ok=false;return false;}const bool p=id<v.prefix_count;const long n=p?id:id-v.prefix_count;
 device const long* offsets=p?v.prefix_offsets:v.suffix_offsets;device const uchar* bytes=p?v.prefix_bytes:v.suffix_bytes;
 const long a=offsets[n],b=offsets[n+1];if(a<0||b<a||b>(p?v.prefix_bytes_length:v.suffix_bytes_length)){ok=false;return false;}
 if(b-a<size)return false;for(long i=0;i<size;++i)if(bytes[a+i]!=uchar(text[i]))return false;return true;
}
inline long rc_json_string(thread const PackedStateView& v,long object,constant char* key,long size,thread long& error,thread bool& ok){
 if(!state_node(v,object)||state_record(v,object)[0]!=13){error=2;return -1;}
 const long n=state_map_find_literal(v,object,key,size,ok);if(!ok)return -1;
 if(n<0||state_record(v,n)[0]!=5){error=2;return -1;}return state_string_id(v,n,ok);
}
kernel void recruitment_choice_stored(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* inherited[[buffer(2)]],device const long* selections[[buffer(3)]],device const bool* selected[[buffer(4)]],
 device const uchar* prefix[[buffer(5)]],device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],
 device const long* soffsets[[buffer(8)]],device const long* usage[[buffer(9)]],device const long* labels[[buffer(10)]],
 device long* data[[buffer(11)]],device bool* handled[[buffer(12)]],device bool* unsupported[[buffer(13)]],
 device long* errors[[buffer(14)]],device const long* dims[[buffer(15)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;device long* d=data+ulong(lane)*11;for(long j=0;j<11;++j)d[j]=-1;
 handled[lane]=unsupported[lane]=false;errors[lane]=0;if(!selected[lane])return;
 bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
 prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,ok);
 if(inherited[lane])ok=false;rc_container(v,0,10,2,ok);const long state=state_child(v,0,0,ok);rc_container(v,state,10,19,ok);
 const long decisions=state_child(v,state,11,ok);rc_container(v,decisions,6,-1,ok);if(!ok){errors[lane]=3;return;}
 const long amount=state_record(v,decisions)[1];if(!amount){errors[lane]=2;return;}
 const long decision=state_child(v,decisions,amount-1,ok);rc_container(v,decision,10,6,ok);
 const long options=state_child(v,decision,5,ok);rc_container(v,options,6,-1,ok);
 if(!ok){errors[lane]=3;return;}if(selections[lane]<0||selections[lane]>=state_record(v,options)[1]){errors[lane]=2;return;}
 const long action=state_child(v,options,selections[lane],ok);rc_container(v,action,10,6,ok);d[2]=action;
 const long kind=state_string_id(v,state_child(v,action,1,ok),ok);
 if(!ok){errors[lane]=3;return;}
 if(!rc_prefix(v,kind,"influence_",10,ok)&&!rc_prefix(v,kind,"recruitment_",12,ok)){if(!ok)errors[lane]=3;return;}
 if(state_string_id_equals(v,kind,"influence_roll",14,ok)||state_string_id_equals(v,kind,"recruitment_roll",16,ok)){
   unsupported[lane]=true;errors[lane]=6;return;}
 handled[lane]=true;
 if(!state_string_equals(v,state_child(v,decision,1,ok),"recruitment_choice",18,ok)){errors[lane]=ok?2:3;return;}
 const long continuation=state_string_id(v,state_child(v,decision,4,ok),ok),politics=state_child(v,state,8,ok);
 const long pending=state_child(v,politics,10,ok);rc_container(v,pending,7,-1,ok);
 const long params=state_map_find_id(v,pending,continuation,ok);if(!ok){errors[lane]=3;return;}if(params<0){errors[lane]=1;return;}
 long error=0;const long minor=rc_json_string(v,params,"beneficiary",11,error,ok);if(!ok){errors[lane]=3;return;}if(error){errors[lane]=error;return;}
 const long parameters=state_child(v,action,5,ok),beneficiary=rc_json_string(v,parameters,"beneficiary",11,error,ok);
 if(!ok){errors[lane]=3;return;}if(error||beneficiary!=minor){errors[lane]=2;return;}
 d[0]=minor;d[1]=continuation;d[7]=amount-1;d[8]=pending;d[10]=parameters;
}
kernel void recruitment_choice_query(device const long* requests[[buffer(0)]],device const long* query_errors[[buffer(1)]],
 device const long* data[[buffer(2)]],device const bool* selected[[buffer(3)]],device long* query_rows[[buffer(4)]],
 device long* errors[[buffer(5)]],device const long* dims[[buffer(6)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;query_rows[lane]=-1;errors[lane]=0;if(!selected[lane])return;
 for(long q=0;q<dims[3];++q)if(requests[q*2]==long(lane)&&requests[q*2+1]==data[ulong(lane)*11]){
   query_rows[lane]=q;errors[lane]=query_errors[q*5+3];return;}errors[lane]=3;
}
// Native eligible parameters contain only strings/string arrays. An arbitrary
// extra valid JSON number/object/bool is a semantic mismatch, never a packed
// error. Matching the complete ordered forest is equivalent to canonical JSON
// equality in this known eligible domain; offsets are compared root-relative.
inline bool rc_parameters_equal(thread const PackedStateView& a,long x,thread const PackedStateView& b,long y,thread bool& ok){
 const long ae=state_end(a,x,ok),be=state_end(b,y,ok);if(!ok||ae-x!=be-y)return false;
 for(long j=0;j<ae-x;++j){device const long* one=state_record(a,x+j);device const long* two=state_record(b,y+j);
   if(one[0]!=two[0]||one[1]!=two[1]||one[2]!=two[2]||one[3]!=two[3]||one[4]-x!=two[4]-y)return false;}return true;
}
kernel void recruitment_choice_eligible(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* actions[[buffer(2)]],device const long* action_lengths[[buffer(3)]],device const long* action_errors[[buffer(4)]],
 device const long* metadata[[buffer(5)]],device const long* query_rows[[buffer(6)]],device const long* count[[buffer(7)]],
 device const int* batch_error[[buffer(8)]],device const int* parameter_errors[[buffer(9)]],device const int* id_errors[[buffer(10)]],
 device const int* parameter_batch[[buffer(11)]],device const int* id_batch[[buffer(12)]],device const bool* selected[[buffer(13)]],
 device const uchar* prefix[[buffer(14)]],device const long* poffsets[[buffer(15)]],device const uchar* suffix[[buffer(16)]],
 device const long* soffsets[[buffer(17)]],device const long* usage[[buffer(18)]],device const long* pool_error[[buffer(19)]],
 device const long* labels[[buffer(20)]],device long* data[[buffer(21)]],device long* errors[[buffer(22)]],device const long* dims[[buffer(23)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],P=dims[2],Q=dims[3];if(long(lane)>=B)return;errors[lane]=0;if(!selected[lane])return;
 if(pool_error[0]){errors[lane]=3;return;}if(batch_error[0]){errors[lane]=batch_error[0]==5?5:3;return;}
 if(parameter_batch[0]||id_batch[0]){errors[lane]=((parameter_batch[0]&2)||(id_batch[0]&2))?5:3;return;}
 if(count[0]<0||count[0]>P){errors[lane]=3;return;}
 const long q=query_rows[lane];if(q<0||q>=Q){errors[lane]=3;return;}long first=0,total=0;
 for(long j=0;j<Q;++j){const long amount=metadata[j*9+7];if(amount<0||amount>LONG_MAX-total){errors[lane]=3;return;}
   if(j<q)first+=amount;total+=amount;}if(total!=count[0]){errors[lane]=3;return;}
 bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,ok);
 device long* d=data+ulong(lane)*11;const long action=d[2],kind=state_string_id(v,state_child(v,action,1,ok),ok);
 const long player=state_string_id(v,state_child(v,action,2,ok),ok),nation=state_string_id(v,state_child(v,action,3,ok),ok);
 long match=-1;for(long i=0;ok&&i<metadata[q*9+7];++i){const long row=first+i;
   if(row<0||row>=count[0]){errors[lane]=3;return;}
   if(action_errors[row]||parameter_errors[row]||id_errors[row]){
     errors[lane]=((parameter_errors[row]&2)||(id_errors[row]&2)||(action_errors[row]&8))?5:3;return;}
   auto candidate=v;candidate.records=actions+ulong(row)*13*5;candidate.length=action_lengths[row];candidate.capacity=13;rc_container(candidate,0,10,6,ok);
   if(!ok){errors[lane]=3;return;}
   if(state_string_id(candidate,state_child(candidate,0,1,ok),ok)!=kind||state_string_id(candidate,state_child(candidate,0,2,ok),ok)!=player||
      state_string_id(candidate,state_child(candidate,0,3,ok),ok)!=nation)continue;
   if(rc_parameters_equal(v,d[10],candidate,state_child(candidate,0,5,ok),ok)){match=row;break;}
 }
 if(!ok){errors[lane]=3;return;}if(match<0){errors[lane]=2;return;}d[9]=match;
 long error=0;if(kind==labels[2]){d[3]=1;d[4]=rc_json_string(v,d[10],"zone",4,error,ok);}
 else if(kind==labels[3]){d[3]=2;const long zones=state_map_find_literal(v,d[10],"zones",5,ok);
   if(zones<0||state_record(v,zones)[0]!=12||state_record(v,zones)[1]!=2){errors[lane]=2;return;}
   d[4]=state_string_id(v,state_child(v,zones,0,ok),ok);d[5]=state_string_id(v,state_child(v,zones,1,ok),ok);
 }else if(kind==labels[4]){d[3]=3;d[6]=rc_json_string(v,d[10],"project",7,error,ok);}
 else if(kind==labels[5]){d[3]=4;d[6]=rc_json_string(v,d[10],"facility",8,error,ok);}
 else error=2;if(error)errors[lane]=error;else if(!ok)errors[lane]=3;
}
inline long rc_row(device long* out,long cap,thread long& at,long tag,long meta){const long root=at++;
 if(root<cap){device long* r=out+ulong(root)*5;r[0]=tag;r[1]=meta;r[2]=r[3]=0;r[4]=root+1;}return root;}
inline void rc_end(device long* out,long cap,long root,long end){if(root<cap)out[ulong(root)*5+4]=end;}
inline void rc_int(device long* out,long cap,thread long& at,long value){const long root=rc_row(out,cap,at,2,0);
 if(root<cap){out[ulong(root)*5+2]=long(ulong(value)&0xffffffffUL);out[ulong(root)*5+3]=long((ulong(value)>>32)&0xffffffffUL);}}
inline bool rc_naval(long type,device const long* naval,long count){for(long i=0;i<count;++i)if(naval[i]==type)return true;return false;}
kernel void recruitment_choice_work(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* data[[buffer(2)]],device const bool* selected[[buffer(3)]],device const long* naval[[buffer(4)]],device const long* labels[[buffer(5)]],
 device const uchar* prefix[[buffer(6)]],device const long* poffsets[[buffer(7)]],device const uchar* suffix[[buffer(8)]],
 device const long* soffsets[[buffer(9)]],device const long* usage[[buffer(10)]],device long* roots[[buffer(11)]],device long* blocks[[buffer(12)]],
 device long* sizes[[buffer(13)]],device long* required[[buffer(14)]],device long* errors[[buffer(15)]],device const long* dims[[buffer(16)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],K=dims[8];if(long(lane)>=B)return;roots[lane]=-1;sizes[lane]=required[lane]=errors[lane]=0;if(!selected[lane])return;
 bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,ok);
 device const long* d=data+ulong(lane)*11;const long state=state_child(v,0,0,ok),kind=d[3],entity=d[6];device long* out=blocks+ulong(lane)*K*5;long at=0;
 if(kind==3){const long projects=state_child(v,state,5,ok),project=state_map_find_id(v,projects,entity,ok);
   if(!ok){errors[lane]=3;return;}if(project<0){errors[lane]=1;return;}rc_container(v,project,10,8,ok);roots[lane]=project;
   const long payments=state_child(v,project,6,ok);rc_container(v,payments,6,-1,ok);
   const long amount=state_record(v,payments)[1],position=state_signed_value(v,state_child(v,project,4,ok),ok);
   const bool own=state_string_id(v,state_child(v,project,1,ok),ok)==d[0];
   const bool ship=rc_naval(state_string_id(v,state_child(v,project,2,ok),ok),naval,dims[9]);
   if(!ok){errors[lane]=3;return;}if(!own||!amount||position<=1||!dims[10]||!ship){errors[lane]=2;return;}
   const long root=rc_row(out,K,at,10,8);long field=project+1;
   for(long f=0;ok&&f<8;++f){const long end=state_end(v,field,ok);
     if(f==4)rc_int(out,K,at,position-1);
     else if(f==6){const long seq=rc_row(out,K,at,6,amount-1);long cursor=state_end(v,payments+1,ok);
       for(long i=1;ok&&i<amount;++i){container_copy(v,cursor,out,K,at,ok);cursor=state_end(v,cursor,ok);}rc_end(out,K,seq,at);}
     else if(f==7&&amount==1){const long flags=rc_row(out,K,at,7,0);long cursor=field+1,count=0;bool added=false;
       for(long i=0;ok&&i<state_record(v,field)[1];++i){const long key=state_string_id(v,cursor,ok),value=cursor+1;
         if(!added&&container_compare(v,labels[12],key,ok)<=0){rc_row(out,K,at,5,labels[12]);rc_int(out,K,at,1);added=true;++count;
           if(key==labels[12]){cursor=state_end(v,value,ok);continue;}}
         container_copy(v,cursor,out,K,at,ok);container_copy(v,value,out,K,at,ok);++count;cursor=state_end(v,value,ok);}
       if(!added){rc_row(out,K,at,5,labels[12]);rc_int(out,K,at,1);++count;}if(flags<K)out[ulong(flags)*5+1]=count;rc_end(out,K,flags,at);
     }else container_copy(v,field,out,K,at,ok);field=end;}rc_end(out,K,root,at);
 }else if(kind==4){const long facilities=state_child(v,state,3,ok),facility=state_map_find_id(v,facilities,entity,ok);
   if(!ok){errors[lane]=3;return;}if(facility<0){errors[lane]=1;return;}rc_container(v,facility,10,5,ok);roots[lane]=facility;
   const long damage=state_signed_value(v,state_child(v,facility,3,ok),ok);if(!ok){errors[lane]=3;return;}if(damage<=0){errors[lane]=2;return;}
   const long territory=state_map_find_id(v,state_child(v,state,1,ok),state_string_id(v,state_child(v,facility,2,ok),ok),ok);
   if(!ok){errors[lane]=3;return;}if(territory<0){errors[lane]=1;return;}bool present=false;
   const long possessor=state_optional(v,state_child(v,territory,0,ok),present,ok);
   if(!ok){errors[lane]=3;return;}if(!present||state_string_id(v,possessor,ok)!=d[0]){errors[lane]=2;return;}
   const long root=rc_row(out,K,at,10,5);long field=facility+1;
   for(long f=0;ok&&f<5;++f){const long end=state_end(v,field,ok);if(f==3)rc_int(out,K,at,0);else container_copy(v,field,out,K,at,ok);field=end;}rc_end(out,K,root,at);
 }else{errors[lane]=3;return;}
 required[lane]=at;if(!ok){errors[lane]=3;return;}if(at>K){errors[lane]=5;return;}sizes[lane]=at;
}
kernel void recruitment_choice_repairs(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* data[[buffer(2)]],device const bool* selected[[buffer(3)]],device const uchar* prefix[[buffer(4)]],
 device const long* poffsets[[buffer(5)]],device const uchar* suffix[[buffer(6)]],device const long* soffsets[[buffer(7)]],
 device const long* usage[[buffer(8)]],device long* roots[[buffer(9)]],device long* blocks[[buffer(10)]],device long* sizes[[buffer(11)]],
 device long* required[[buffer(12)]],device long* errors[[buffer(13)]],device const long* dims[[buffer(14)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],K=dims[8];if(long(lane)>=B)return;roots[lane]=-1;sizes[lane]=required[lane]=errors[lane]=0;if(!selected[lane])return;
 bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,ok);
 const long repairs=state_child(v,state_child(v,0,0,ok),6,ok);rc_container(v,repairs,7,-1,ok);roots[lane]=repairs;
 device long* out=blocks+ulong(lane)*K*5;long at=0,count=0;const long root=rc_row(out,K,at,7,0);long cursor=repairs+1;
 for(long i=0;ok&&i<state_record(v,repairs)[1];++i){const long job=cursor+1;rc_container(v,job,10,7,ok);
   if(state_string_id(v,state_child(v,job,2,ok),ok)!=data[ulong(lane)*11+6]){container_copy(v,cursor,out,K,at,ok);container_copy(v,job,out,K,at,ok);++count;}
   cursor=state_end(v,job,ok);}
 if(root<K)out[ulong(root)*5+1]=count;rc_end(out,K,root,at);required[lane]=at;
 if(!ok){errors[lane]=3;return;}if(at>K){errors[lane]=5;return;}sizes[lane]=at;
}
'''
_library=None
_lock=threading.Lock()
@lru_cache(maxsize=32)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device="mps")
@lru_cache(maxsize=1)
def _dummy():return torch.zeros(1,dtype=torch.int64,device="mps")
def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    return _library
def _call(kernel,args,count):
    if count:kernel(*(v if v.numel() else _dummy() for v in args),threads=count)
def _tensor(value,state,dtype,shape):
    if not isinstance(value,torch.Tensor) or value.dtype!=dtype or value.device!=state.device or tuple(value.shape)!=tuple(shape) or not value.is_contiguous():
        raise ValueError("Recruitment-choice tensors must remain complete resident contiguous arrays")
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    out=torch.zeros(shape,dtype=value.dtype,device=value.device);out[tuple(slice(0,n) for n in value.shape)]=value;return out


class ResidentRecruitmentChoice:
    def __init__(self,state_context,recruitment,creation,political_refresh):
        if _device(state_context.device).type!="mps" or any(v.state_context is not state_context for v in (recruitment,creation,political_refresh)):
            raise ValueError("Recruitment choice requires exact shared resident component contexts")
        self.state_context=state_context;self.recruitment=recruitment;self.creation=creation;self.political_refresh=political_refresh
        self.labels=torch.tensor(state_context.prefix_lookup_ids(LITERALS),dtype=torch.int64,device=state_context.device)
        self.catalog_present=int(recruitment.native_context.catalog_present)

    def reserve(self,before,current_choices,**refresh_arguments):
        """One explicit reservation, reused without per-application padding."""
        base=current_choices.arena
        if current_choices.source is not before:raise ValueError("Recruitment menu reservation source differs")
        refresh=self.political_refresh.reserve(base,**refresh_arguments);creation=self.creation.reserve(base,creation_capacity=1)
        S=refresh.state_capacity+2*(creation["state_capacity"]-base.records.shape[1])
        T=refresh.string_capacity+2*before.lane_count;A=refresh.byte_capacity+2*before.lane_count*creation["id_byte_capacity"]
        return RecruitmentChoiceCapacities(1,creation["id_byte_capacity"],replace(refresh,state_capacity=S,block_capacity=max(S,refresh.block_capacity),string_capacity=T,byte_capacity=A))

    def apply(self,before,current_choices,option_indices,selected=None,*,capacities):
        if not isinstance(before,DeviceStateBatch) or before.context is not self.state_context:raise ValueError("Recruitment choice source differs")
        menu=current_choices
        if not isinstance(menu,RecruitmentMenu) or menu.source is not before or menu.queries.source is not before or menu.queries.rolls:
            raise ValueError("Recruitment choice requires the cached complete choices for this exact State")
        arena=menu.arena;before._metadata();arena._metadata();_device(before.device)
        if arena.context is not before.context or any(getattr(arena,key) is not getattr(before,key) for key in ("records","lengths","sections","errors")):
            raise ValueError("Recruitment menu must only append to the source namespace")
        if arena.string_offsets.numel()<before.string_offsets.numel() or arena.string_bytes.numel()<before.string_bytes.numel():raise ValueError("Menu namespace shrank")
        if not isinstance(capacities,RecruitmentChoiceCapacities):raise TypeError("Recruitment choice needs its complete arena contract")
        capacities.validate(before,arena);caps=capacities.political_refresh;S,K,T,A=caps.state_capacity,caps.block_capacity,caps.string_capacity,caps.byte_capacity
        B,C=before.records.shape[:2];P=menu.actions.shape[0];Q=menu.queries.requests.shape[0];dev=before.device
        _tensor(option_indices,before,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,before,torch.bool,(B,))
        for value,dtype,shape in ((menu.actions,torch.int64,(P,13,5)),(menu.lengths,torch.int64,(P,)),(menu.errors,torch.int64,(P,)),
            (menu.queries.requests,torch.int64,(Q,2)),(menu.queries.metadata,torch.int64,(Q,9)),(menu.queries.errors,torch.int64,(Q,5)),
            (menu.count,torch.int64,(1,)),(menu.batch_error,torch.int32,(1,)),(menu.parameter_json.errors,torch.int32,(P,)),
            (menu.id_bytes.errors,torch.int32,(P,)),(menu.parameter_json.batch_error,torch.int32,(1,)),(menu.id_bytes.batch_error,torch.int32,(1,))):_tensor(value,before,dtype,shape)
        for state in (before,arena):
            for value in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets,state.suffix_usage,state.context.records,state.context.string_bytes,state.context.string_offsets):
                if value.device!=dev or not value.is_contiguous():raise ValueError("Recruitment choice buffers must remain resident and contiguous")
        if B>2**32-1 or max(B*max(S,K,C,1)*5,P*13*5,Q*9)*8>2**63-1:raise OverflowError("Recruitment choice arena is not representable")
        zero=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        def dims(source):return _dimensions((B,source.records.shape[1],P,Q,source.context.string_count,source.context.string_bytes.numel(),source.string_offsets.numel()-1,
            source.string_bytes.numel(),K,self.recruitment.naval_tokens.numel(),self.catalog_present))
        def pool(source):return (source.context.string_bytes,source.context.string_offsets,source.string_bytes,source.string_offsets,source.suffix_usage)
        data,errors,first=zero(B,11),zero(B),zero(B);handled=torch.zeros(B,dtype=torch.bool,device=dev);unsupported=torch.zeros_like(handled)
        _call(_kernels().recruitment_choice_stored,(before.records,before.lengths,before.errors,option_indices,selected,*pool(before),self.labels,data,handled,unsupported,errors,dims(before)),B)
        first=torch.where(errors!=0,1,0);stage_errors={"stored":errors.clone()};required={};ordinal=1
        needed_state=before.lengths.clone();needed_block=zero(B);needed_strings=before.suffix_usage.clone()
        def active():return selected&handled&~(errors!=0).any()
        def note(name,details,mask,requirements=None):
            nonlocal errors,first,ordinal,needed_state,needed_block,needed_strings
            ordinal+=1;details=torch.where(mask,details.to(torch.int64),0);stage_errors[name]=details
            first=torch.where((errors==0)&(details!=0),ordinal,first);errors=torch.where((errors==0)&(details!=0),details,errors)
            requirements={} if requirements is None else requirements;required[name]=requirements
            if "required_state_capacity" in requirements:needed_state=torch.maximum(needed_state,requirements["required_state_capacity"])
            if "required_block_capacity" in requirements:needed_block=torch.maximum(needed_block,requirements["required_block_capacity"])
            if "required_string_usage" in requirements:needed_strings=torch.maximum(needed_strings,requirements["required_string_usage"])
        def record(name,result,mask):
            details=result.errors.to(torch.int64);absent=(~result.committed)&~(torch.where(mask,details,0)!=0).any()
            details=torch.where(mask&absent,3,details)
            note(name,details,mask,{f.name:getattr(result,f.name) for f in fields(result) if f.name.startswith("required_")});return result.state
        def container(name,build,mask):
            edited=commit_container_edits(build,capacity=S);bad=(build.errors!=0)|(edited.edit_errors!=0)
            cap=((build.errors&64)!=0)|((edited.edit_errors&8)!=0)
            note(name,torch.where(bad,torch.where(cap,5,3),0),mask,{"required_state_capacity":edited.required_state_capacity,"required_block_capacity":build.required_capacity})
            return edited.state
        # Pure cached validation may diagnose the other lanes after an early
        # error; no mutation is allowed until the complete cohort is healthy.
        query_rows,query_errors=zero(B),zero(B);mask=selected&handled&(errors==0)
        _call(_kernels().recruitment_choice_query,(menu.queries.requests,menu.queries.errors,data,mask,query_rows,query_errors,dims(before)),B)
        note("query",query_errors,mask);eligibility_errors=zero(B)
        materialized=(menu.batch_error==0).all()&(menu.parameter_json.batch_error==0).all()&(menu.id_bytes.batch_error==0).all()
        # A native query error can prevent global menu materialization. Keep
        # that earlier reason instead of attributing a spurious cache error to
        # healthy lanes whose matching actions were never emitted.
        mask=selected&handled&(errors==0)&(materialized|~(errors!=0).any())
        _call(_kernels().recruitment_choice_eligible,(before.records,before.lengths,menu.actions,menu.lengths,menu.errors,menu.queries.metadata,query_rows,
            menu.count,menu.batch_error,menu.parameter_json.errors,menu.id_bytes.errors,menu.parameter_json.batch_error,menu.id_bytes.batch_error,
            mask,*pool(arena),_pool(before,arena),self.labels,data,eligibility_errors,dims(arena)),B)
        note("eligible",eligibility_errors,mask)
        current=arena;empty=zero(B,0,5);lengths=zero(B);mask=active()
        current=container("pop",build_sequence_splices(current,current.section("state.decisions").contiguous(),data[:,7].contiguous(),
            torch.ones(B,dtype=torch.int64,device=dev),empty,lengths,zero(B),mask,capacity=K),mask)
        # Pending precedes Decisions in State, so popping the last Decision did
        # not change its original pending-map root.
        mask=active();current=container("continuation",build_map_edits(current,data[:,8].contiguous(),data[:,1].contiguous(),
            torch.full((B,),int(MapMode.ERASE),dtype=torch.int64,device=dev),empty,lengths,mask,capacity=K),mask)
        for step in (0,1):
            mask=active()&((data[:,3]==2)|((data[:,3]==1)&(step==0)))
            types=torch.where(data[:,3]==1,self.labels[10],self.labels[11]).contiguous();zones=data[:,4+step].contiguous()
            result=self.creation.add(current,data[:,0].contiguous(),types,zones,torch.ones(B,dtype=torch.int64,device=dev),mask,
                creation_capacity=capacities.creation_capacity,id_byte_capacity=capacities.creation_id_byte_capacity,
                state_capacity=S,block_capacity=K,string_capacity=T,byte_capacity=A)
            current=record("create_"+str(step),result,mask)
        roots,blocks,block_lengths,needed,work_errors=zero(B),zero(B,K,5),zero(B),zero(B),zero(B);mask=active()&((data[:,3]==3)|(data[:,3]==4))
        _call(_kernels().recruitment_choice_work,(current.records,current.lengths,data,mask,self.recruitment.naval_tokens,self.labels,*pool(current),roots,blocks,
            block_lengths,needed,work_errors,dims(current)),B)
        note("work",work_errors,mask,{"required_block_capacity":needed});mask&=active()
        edited=replace_subtrees(current,roots,blocks,block_lengths,mask,capacity=S)
        note("work_commit",torch.where(edited.errors!=0,torch.where((edited.errors&8)!=0,5,3),0),mask,{"required_state_capacity":edited.required_capacity});current=edited.state
        roots,blocks,block_lengths,needed,repair_errors=zero(B),zero(B,K,5),zero(B),zero(B),zero(B);mask=active()&(data[:,3]==4)
        _call(_kernels().recruitment_choice_repairs,(current.records,current.lengths,data,mask,*pool(current),roots,blocks,block_lengths,needed,repair_errors,dims(current)),B)
        note("repairs",repair_errors,mask,{"required_block_capacity":needed});mask&=active()
        edited=replace_subtrees(current,roots,blocks,block_lengths,mask,capacity=S)
        note("repairs_commit",torch.where(edited.errors!=0,torch.where((edited.errors&8)!=0,5,3),0),mask,{"required_state_capacity":edited.required_capacity});current=edited.state
        mask=active();refresh=self.political_refresh.refresh(current,mask,capacities=caps);current=record("refresh",refresh,mask)
        committed=~(errors!=0).any();publish=committed&handled.any()
        output=DeviceStateBatch(before.context,torch.where(publish,current.records,_pad(before.records,(B,S,5))),
            torch.where(publish,current.lengths,before.lengths),torch.where(publish,current.sections,before.sections),
            torch.where(publish,current.string_bytes,_pad(before.string_bytes,(A,))),
            torch.where(publish,current.string_offsets,_pad(before.string_offsets,(T+1,))),before.errors,
            torch.where(publish,current.suffix_usage,before.suffix_usage))
        needed_strings=torch.maximum(needed_strings,menu.required_usage)
        return RecruitmentChoiceResult(before,output,errors,handled,unsupported,data[:,2].contiguous(),first,stage_errors,required,needed_state,needed_block,needed_strings,
            selected&handled&committed,committed)
