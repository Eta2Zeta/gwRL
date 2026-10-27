"""Exact resident addPoliticalUnit, including counter/collision ordering.

CatalogContext audit (src/catalog.cpp): nation, power status, calendar, completed
technologies, global/nation game/turn boolean flags, owner Home Country, dormant
USSR/theatre predicates and nation purchases are its complete inputs. Inserting
a Unit changes none of them. Incrementing politics_sequence changes one boolean
global flag. We therefore query the actual first increment, then the opposite
zero/nonzero context only when reached and the first query succeeded. This is
not a cached Catalog result across different States/status/technology changes.

This pure effect does not evolve a nation, refresh income, append Events, update
the calendar, validate placement actions or consume RNG. Outer Engine validation
still owns unresolved Catalog allowance and other complete-State invariants.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_state_edits import replace_subtrees
from .device_map_edits import SOURCE as MAP_SOURCE,MapMode,build_map_edits,commit_container_edits
from .device_strings import intern_bytes

LOOKUP_ERROR,NATIVE_ERROR,PACKED_ERROR,INT_OVERFLOW,CAPACITY_ERROR=1,2,3,4,5


@dataclass(frozen=True)
class PoliticalCreationResult:
    state:DeviceStateBatch
    errors:torch.Tensor
    generated_ids:torch.Tensor
    collision_mask:torch.Tensor
    inserted_counts:torch.Tensor
    query_errors:torch.Tensor
    message_ids:torch.Tensor
    first_failure_ordinal:torch.Tensor
    required_creation_capacity:torch.Tensor
    required_id_bytes:torch.Tensor
    required_state_capacity:torch.Tensor
    required_block_capacity:torch.Tensor
    required_string_usage:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE=MAP_SOURCE+r'''
inline bool pc_container(thread const PackedStateView& v,long root,long tag,long count,thread bool& valid){
 const long end=state_end(v,root,valid);if(!valid)return false;device const long* row=state_record(v,root);
 const long maximum=(tag==7?(end-root-1)/2:end-root-1);
 if(row[0]!=tag||row[1]<0||row[1]>maximum||(count>=0&&row[1]!=count)||row[2]||row[3])valid=false;return valid;
}
inline long pc_text_length(thread const PackedStateView& v,long id,thread bool& valid){
 if(id<0||id>=v.prefix_count+v.suffix_count){valid=false;return 0;}const bool p=id<v.prefix_count;
 device const long* offsets=p?v.prefix_offsets:v.suffix_offsets;const long i=p?id:id-v.prefix_count;
 const long a=offsets[i],b=offsets[i+1];if(a<0||b<a||b>(p?v.prefix_bytes_length:v.suffix_bytes_length)){valid=false;return 0;}return b-a;
}
inline uchar pc_text_byte(thread const PackedStateView& v,long id,long i){
 const bool p=id<v.prefix_count;const long n=p?id:id-v.prefix_count;
 return p?v.prefix_bytes[v.prefix_offsets[n]+i]:v.suffix_bytes[v.suffix_offsets[n]+i];
}
inline long pc_digits(long value){long size=value<0?1:0;ulong n=ulong(value<0?-value:value);do{++size;n/=10;}while(n);return size;}
kernel void political_creation_plan(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const long* nations[[buffer(3)]],device const long* types[[buffer(4)]],device const long* zones[[buffer(5)]],
 device const long* counts[[buffer(6)]],device const bool* selected[[buffer(7)]],device const uchar* prefix[[buffer(8)]],
 device const long* poffsets[[buffer(9)]],device const uchar* suffix[[buffer(10)]],device const long* soffsets[[buffer(11)]],
 device const long* usage[[buffer(12)]],device long* data[[buffer(13)]],device long* errors[[buffer(14)]],
 device long* failed[[buffer(15)]],device long* needed[[buffer(16)]],device long* needed_bytes[[buffer(17)]],
 device const long* dims[[buffer(18)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;errors[lane]=failed[lane]=needed[lane]=needed_bytes[lane]=0;
 device long* d=data+ulong(lane)*9;for(long i=0;i<9;++i)d[i]=0;d[4]=d[5]=d[6]=-1;if(!selected[lane])return;
 const long amount=counts[lane];if(amount<INT_MIN||amount>INT_MAX){errors[lane]=3;return;}
 if(amount<=0){errors[lane]=2;return;}needed[lane]=amount;d[7]=amount;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
   prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,valid);
 if(inherited[lane])valid=false;pc_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);
 pc_container(v,state,10,19,valid);d[6]=state;
 const long territories=state_child(v,state,1,valid);pc_container(v,territories,7,-1,valid);
 (void)pc_text_length(v,zones[lane],valid);if(!valid){errors[lane]=3;return;}
 const long territory=state_map_find_id(v,territories,zones[lane],valid);
 if(!valid){errors[lane]=3;return;}if(territory<0){errors[lane]=1;return;}
 pc_container(v,territory,10,2,valid);bool present=false;
 const long owner=state_optional(v,state_child(v,territory,0,valid),present,valid);
 const long possessor=present?state_string_id(v,owner,valid):-1;
 (void)pc_text_length(v,nations[lane],valid);if(!valid){errors[lane]=3;return;}
 if(possessor!=nations[lane]){errors[lane]=2;return;}
 const long flags=state_child(v,state,15,valid);pc_container(v,flags,7,-1,valid);d[4]=flags;
 const long sequence=state_map_find_literal(v,flags,"politics_sequence",17,valid);d[8]=sequence<0?1:0;
 const long start=sequence<0?0:state_signed_value(v,sequence,valid);
 if(!valid||start<INT_MIN||start>INT_MAX){errors[lane]=3;return;}d[0]=start;
 if(start==INT_MAX){errors[lane]=2;failed[lane]=1;return;}
 d[1]=start+1;d[2]=d[1]==0?1:0;
 const long second=d[1]==0?2:(start<(-1)?-start:0);d[3]=(second>0&&second<=amount)?second:0;
 const long type_bytes=pc_text_length(v,types[lane],valid);
 const long units=state_child(v,state,2,valid);pc_container(v,units,7,-1,valid);d[5]=units;
 if(!valid){errors[lane]=3;return;}
 needed_bytes[lane]=11+type_bytes+max(pc_digits(start+1),pc_digits(start+amount));
}
kernel void political_creation_requests(
 device const long* data[[buffer(0)]],device const long* errors[[buffer(1)]],device const bool* enabled[[buffer(2)]],
 device const long* nations[[buffer(3)]],device const long* types[[buffer(4)]],device const long* zones[[buffer(5)]],
 device long* requests[[buffer(6)]],device long* slots[[buffer(7)]],device long* count[[buffer(8)]],
 device const long* dims[[buffer(9)]],uint tid[[thread_position_in_grid]]){
 if(tid)return;long row=0;for(long lane=0;lane<dims[0];++lane){slots[lane]=-1;
   if(!enabled[lane]||errors[lane])continue;
   if(dims[2]&&data[ulong(lane)*9+3]==0)continue;
   slots[lane]=row;device long* out=requests+ulong(row)*5;out[0]=lane;out[1]=types[lane];out[2]=0;
   out[3]=nations[lane];out[4]=zones[lane];++row;}count[0]=row;
}
kernel void political_creation_catalog(
 device const long* slots[[buffer(0)]],device const long* stats[[buffer(1)]],device const long* query_errors[[buffer(2)]],
 device const long* messages[[buffer(3)]],device const long* batch_error[[buffer(4)]],device const long* data[[buffer(5)]],
 device long* errors[[buffer(6)]],device long* failed[[buffer(7)]],device long* allowance[[buffer(8)]],
 device long* result_errors[[buffer(9)]],device long* result_messages[[buffer(10)]],device const long* dims[[buffer(11)]],
 uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;const long which=dims[2],row=slots[lane];if(row<0)return;
 long error=batch_error[0]?3:query_errors[row];result_errors[ulong(lane)*2+which]=error;
 result_messages[ulong(lane)*2+which]=messages[row];
 if(error){if(!errors[lane]){errors[lane]=error;failed[lane]=which?data[ulong(lane)*9+3]:1;}return;}
 const long present=stats[ulong(row)*18+8],value=stats[ulong(row)*18+9];
 if(present<0||present>1||(present&&(value<INT_MIN||value>INT_MAX))){errors[lane]=3;return;}
 allowance[ulong(lane)*4+which*2]=present;allowance[ulong(lane)*4+which*2+1]=value;
}
kernel void political_creation_capacity(device const long* data[[buffer(0)]],device const bool* selected[[buffer(1)]],
 device const long* required_bytes[[buffer(2)]],device long* errors[[buffer(3)]],device long* failed[[buffer(4)]],
 device const long* dims[[buffer(5)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0]||!selected[lane]||errors[lane])return;device const long* d=data+ulong(lane)*9;
 const long overflow=long(INT_MAX)-d[0]+1;
 if(d[7]>=overflow){errors[lane]=2;failed[lane]=overflow;return;}
 if(d[7]>dims[2]||required_bytes[lane]>dims[3])errors[lane]=5;
}
kernel void political_creation_names(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* data[[buffer(2)]],
 device const long* types[[buffer(3)]],device const bool* enabled[[buffer(4)]],device const uchar* prefix[[buffer(5)]],
 device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],device const long* soffsets[[buffer(8)]],
 device const long* usage[[buffer(9)]],device uchar* names[[buffer(10)]],device long* sizes[[buffer(11)]],
 device bool* selected[[buffer(12)]],device long* errors[[buffer(13)]],device const long* dims[[buffer(14)]],
 uint row[[thread_position_in_grid]]){
 const long Q=dims[2],L=dims[3],lane=long(row)/Q,i=long(row)%Q;if(lane>=dims[0])return;
 sizes[row]=errors[row]=0;selected[row]=false;if(!enabled[lane]||i>=data[ulong(lane)*9+7])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
   prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,valid);
 const long type=types[lane],N=pc_text_length(v,type,valid),value=data[ulong(lane)*9]+i+1;
 const long required=11+N+pc_digits(value);sizes[row]=required;
 if(!valid){errors[row]=3;return;}if(required>L){errors[row]=5;return;}
 device uchar* out=names+ulong(row)*L;constant char* start="political_";for(long j=0;j<10;++j)out[j]=uchar(start[j]);
 for(long j=0;j<N;++j)out[10+j]=pc_text_byte(v,type,j);long at=10+N;out[at++]='_';
 if(value<0)out[at++]='-';ulong number=ulong(value<0?-value:value);char digits[20];long n=0;
 do{digits[n++]=char('0'+number%10);number/=10;}while(number);while(n)out[at++]=uchar(digits[--n]);selected[row]=true;
}
kernel void political_creation_collisions(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* data[[buffer(2)]],
 device const long* ids[[buffer(3)]],device const bool* enabled[[buffer(4)]],device const uchar* prefix[[buffer(5)]],
 device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],device const long* soffsets[[buffer(8)]],
 device const long* usage[[buffer(9)]],device bool* collision[[buffer(10)]],device long* errors[[buffer(11)]],
 device const long* dims[[buffer(12)]],uint row[[thread_position_in_grid]]){
 const long Q=dims[2],lane=long(row)/Q,i=long(row)%Q;if(lane>=dims[0])return;collision[row]=false;errors[row]=0;
 if(!enabled[lane]||i>=data[ulong(lane)*9+7])return;bool valid=true;
 auto v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],prefix,poffsets,dims[4],dims[5],
   suffix,soffsets,dims[6],dims[7],usage,valid);
 collision[row]=state_map_find_id(v,data[ulong(lane)*9+5],ids[row],valid)>=0;if(!valid)errors[row]=3;
}
kernel void political_creation_order(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* data[[buffer(2)]],
 device const long* ids[[buffer(3)]],device const bool* collision[[buffer(4)]],device const bool* enabled[[buffer(5)]],
 device const uchar* prefix[[buffer(6)]],device const long* poffsets[[buffer(7)]],device const uchar* suffix[[buffer(8)]],
 device const long* soffsets[[buffer(9)]],device const long* usage[[buffer(10)]],device long* order[[buffer(11)]],
 device long* errors[[buffer(12)]],device const long* dims[[buffer(13)]],uint row[[thread_position_in_grid]]){
 const long Q=dims[2],lane=long(row)/Q,i=long(row)%Q;if(lane>=dims[0])return;errors[row]=0;
 if(!enabled[lane]||i>=data[ulong(lane)*9+7]||collision[row])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],prefix,poffsets,dims[4],dims[5],
   suffix,soffsets,dims[6],dims[7],usage,valid);long rank=0;
 for(long j=0;j<data[ulong(lane)*9+7];++j)if(j!=i&&!collision[ulong(lane)*Q+j]){
   const int compare=container_compare(v,ids[ulong(lane)*Q+j],ids[row],valid);
   if(compare<0)++rank;else if(compare==0)valid=false;}
 if(!valid||rank<0||rank>=Q){errors[row]=3;return;}order[ulong(lane)*Q+rank]=i;
}
kernel void political_creation_measure(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* data[[buffer(2)]],
 device const bool* collision[[buffer(3)]],device const long* allowance[[buffer(4)]],device const bool* enabled[[buffer(5)]],
 device long* inserted[[buffer(6)]],device long* required_state[[buffer(7)]],device long* required_block[[buffer(8)]],
 device long* errors[[buffer(9)]],device const long* dims[[buffer(10)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;inserted[lane]=required_block[lane]=errors[lane]=0;required_state[lane]=lengths[lane];if(!enabled[lane])return;
 device const long* d=data+ulong(lane)*9;long extra=0;
 for(long i=0;i<d[7];++i)if(!collision[ulong(lane)*dims[2]+i]){
   const long category=((d[0]+i+1==0)==(d[1]==0))?0:1;
   extra+=19+allowance[ulong(lane)*4+category*2];++inserted[lane];}
 const long root=d[5];required_block[lane]=records[(ulong(lane)*dims[1]+root)*5+4]-root+extra;
 required_state[lane]=lengths[lane]+d[8]*2+extra;
 if(required_state[lane]>dims[8]||required_block[lane]>dims[9])errors[lane]=5;
}
inline void pc_row(device long* out,long at,long tag,long value,long end){
 device long* r=out+ulong(at)*5;r[0]=tag;r[1]=value;r[2]=r[3]=0;r[4]=end;
}
inline void pc_int(device long* out,long at,long value){pc_row(out,at,2,0,at+1);
 out[ulong(at)*5+2]=long(as_type<ulong>(value)&0xffffffffUL);out[ulong(at)*5+3]=long(as_type<ulong>(value)>>32);}
inline long pc_new_unit(device long* out,long at,long id,long type,long owner,long zone,long present,long movement,long placed){
 const long root=at;pc_row(out,at++,5,id,root+1);const long unit=at;pc_row(out,at++,10,14,unit+19);
 pc_row(out,at,5,id,at+1);++at;pc_row(out,at,5,type,at+1);++at;pc_row(out,at,5,owner,at+1);++at;pc_row(out,at,5,zone,at+1);++at;
 pc_row(out,at,9,1,at+2);++at;pc_int(out,at++,0);
 pc_row(out,at,9,present,at+1+present);++at;if(present)pc_int(out,at++,movement);
 pc_row(out,at,5,zone,at+1);++at;pc_row(out,at,6,0,at+1);++at;pc_row(out,at,9,0,at+1);++at;
 pc_row(out,at,6,0,at+1);++at;pc_int(out,at++,0);pc_row(out,at,8,0,at+1);++at;
 pc_row(out,at,7,1,at+3);++at;pc_row(out,at,5,placed,at+1);++at;pc_int(out,at++,1);
 pc_row(out,at,7,0,at+1);++at;out[ulong(unit)*5+4]=at;return at;
}
kernel void political_creation_write(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* data[[buffer(2)]],
 device const long* ids[[buffer(3)]],device const long* order[[buffer(4)]],device const long* inserted[[buffer(5)]],
 device const long* allowance[[buffer(6)]],device const long* nations[[buffer(7)]],device const long* types[[buffer(8)]],
 device const long* zones[[buffer(9)]],device const bool* enabled[[buffer(10)]],device const uchar* prefix[[buffer(11)]],
 device const long* poffsets[[buffer(12)]],device const uchar* suffix[[buffer(13)]],device const long* soffsets[[buffer(14)]],
 device const long* usage[[buffer(15)]],device long* output[[buffer(16)]],device long* actual[[buffer(17)]],
 device long* errors[[buffer(18)]],device const long* dims[[buffer(19)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;actual[lane]=errors[lane]=0;if(!enabled[lane])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],prefix,poffsets,dims[4],dims[5],
   suffix,soffsets,dims[6],dims[7],usage,valid);device const long* d=data+ulong(lane)*9;const long root=d[5],Q=dims[2],K=dims[9];
 const long old_count=state_record(v,root)[1];device long* out=output+ulong(lane)*K*5;
 pc_row(out,0,7,old_count+inserted[lane],1);long cursor=root+1,old=0,next=0,destination=1;
 while(valid&&(old<old_count||next<inserted[lane])){
   const long q=next<inserted[lane]?order[ulong(lane)*Q+next]:-1;
   if(next<inserted[lane]&&(q<0||q>=d[7])){valid=false;break;}
   const long id=q<0?-1:ids[ulong(lane)*Q+q];const long previous=old<old_count?state_string_id(v,cursor,valid):-1;
   const int compare=old<old_count&&q>=0?container_compare(v,previous,id,valid):(old<old_count?-1:1);
   if(compare<0){container_copy(v,cursor,out,K,destination,valid);const long unit=cursor+1;
     container_copy(v,unit,out,K,destination,valid);cursor=state_end(v,unit,valid);++old;}
   else if(compare>0){const long category=((d[0]+q+1==0)==(d[1]==0))?0:1;
     const long present=allowance[ulong(lane)*4+category*2],movement=allowance[ulong(lane)*4+category*2+1];
     if(destination>K-(19+present)){valid=false;break;}
     destination=pc_new_unit(out,destination,id,types[lane],nations[lane],zones[lane],present,movement,dims[10]);++next;}
   else valid=false;
 }
 if(!valid||destination>K){errors[lane]=3;return;}out[4]=destination;actual[lane]=destination;
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
    if count:kernel(*(value if value.numel() else _dummy() for value in args),threads=count)
def _tensor(value,state,dtype,shape):
    if not isinstance(value,torch.Tensor) or value.dtype!=dtype or value.device!=state.device or tuple(value.shape)!=tuple(shape) or not value.is_contiguous():
        raise ValueError("Political unit creation inputs must remain complete contiguous resident tensors")
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    result=torch.zeros(shape,dtype=value.dtype,device=value.device);result[tuple(slice(0,n) for n in value.shape)]=value;return result


class ResidentPoliticalUnitCreation:
    def __init__(self,state_context,catalog_stats):
        if _device(state_context.device).type!="mps" or catalog_stats.state_context is not state_context:
            raise ValueError("Political unit creation requires exact shared Apple GPU State/Catalog contexts")
        self.state_context=state_context;self.catalog_stats=catalog_stats
        try:self.sequence,self.placed=(int(value) for value in state_context.prefix_lookup_ids(("politics_sequence","placed_this_turn")))
        except (IndexError,ValueError) as error:
            raise ValueError("Creation requires the appended fixed placed_this_turn wire prefix; recapture, never retag old arenas") from error
        self.id_capacity=max((len(value.encode()) for value in catalog_stats.unit_types),default=0)+22

    def reserve(self,state,*,creation_capacity,id_byte_capacity=None):
        if type(creation_capacity) is not int or creation_capacity<0:raise ValueError("Creation capacity must be a nonnegative allocation")
        L=self.id_capacity if id_byte_capacity is None else id_byte_capacity
        if type(L) is not int or L<0:raise ValueError("Creation ID capacity must be a nonnegative allocation")
        S=state.records.shape[1]+20*creation_capacity+2;Q=state.lane_count*creation_capacity
        return dict(creation_capacity=creation_capacity,id_byte_capacity=L,state_capacity=S,block_capacity=max(S,1),
            string_capacity=state.string_offsets.numel()-1+Q,byte_capacity=state.string_bytes.numel()+Q*L)

    def add(self,state,nations,types,zones,counts,selected=None,*,creation_capacity,id_byte_capacity,
            state_capacity=None,block_capacity=None,string_capacity=None,byte_capacity=None):
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Political creation source context differs")
        state._metadata();_device(state.device);B,C=state.records.shape[:2];dev=state.device
        for value in (nations,types,zones,counts):_tensor(value,state,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,state,torch.bool,(B,))
        Q,L=creation_capacity,id_byte_capacity;S=C if state_capacity is None else state_capacity;K=max(C,1) if block_capacity is None else block_capacity
        string_capacity=state.string_offsets.numel()-1 if string_capacity is None else string_capacity
        byte_capacity=state.string_bytes.numel() if byte_capacity is None else byte_capacity
        if any(type(v) is not int or v<0 for v in (Q,L,S,K,string_capacity,byte_capacity)) or S<C or K<1 or string_capacity<state.string_offsets.numel()-1 or byte_capacity<state.string_bytes.numel():
            raise ValueError("Creation arenas must be explicit and preserve the complete source for rollback")
        if max(Q,L,S,K,string_capacity,byte_capacity)>2**63-1 or B>2**32-1 or B*Q>2**32-1 or max(B*max(C,S,K,1)*5,B*Q*max(L,1))*8>2**63-1:raise OverflowError("Creation allocation is not representable")
        for value in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets,state.suffix_usage,
                      state.context.records,state.context.string_bytes,state.context.string_offsets):
            if value.device!=dev or not value.is_contiguous():raise ValueError("Creation State/context buffers must stay resident and contiguous")
        zero=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        data,errors,failed,needed,needed_bytes=zero(B,9),zero(B),zero(B),zero(B),zero(B)
        def dims(source,which=0):return _dimensions((B,source.records.shape[1],Q,L,source.context.string_count,source.context.string_bytes.numel(),
            source.string_offsets.numel()-1,source.string_bytes.numel(),S,K,which))
        shared=(state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage)
        _call(_kernels().political_creation_plan,(state.records,state.lengths,state.errors,nations,types,zones,counts,selected,*shared,
            data,errors,failed,needed,needed_bytes,dims(state)),B)
        required_state=state.lengths.clone();required_block=zero(B)
        def note(details,active):
            nonlocal errors
            errors=torch.where(active&(errors==0)&(details!=0),details,errors)
        def map_sequence(source,values,active):
            nonlocal required_state,required_block
            blocks=zero(B,1,5);blocks[:,:,0]=2;bits=values.reshape(B,1)
            blocks[:,:,2]=bits&0xffffffff;blocks[:,:,3]=(bits>>32)&0xffffffff;blocks[:,:,4]=1
            build=build_map_edits(source,data[:,4].contiguous(),torch.full((B,),self.sequence,dtype=torch.int64,device=dev),
                torch.full((B,),int(MapMode.UPSERT),dtype=torch.int64,device=dev),blocks,torch.ones(B,dtype=torch.int64,device=dev),active,capacity=K)
            changed=commit_container_edits(build,capacity=S)
            required_state=torch.maximum(required_state,changed.required_state_capacity);required_block=torch.maximum(required_block,build.required_capacity)
            bad=(build.errors!=0)|(changed.edit_errors!=0);capacity=((build.errors&64)!=0)|((changed.edit_errors&8)!=0)
            note(torch.where(bad,torch.where(capacity,5,3),0),active)
            return changed.state,changed.committed
        allowance=zero(B,2,2);query_errors=zero(B,2);messages=zero(B,2)
        first_ready=torch.zeros(B,dtype=torch.bool,device=dev)
        for which in (0,1):
            active=selected&(errors==0)
            if which:active&=(data[:,3]>0)&first_ready
            context,committed=map_sequence(state,data[:,1+which].contiguous(),active)
            requests,slots,count=zero(B,5),torch.full((B,),-1,dtype=torch.int64,device=dev),zero(1)
            _call(_kernels().political_creation_requests,(data,errors,active&committed,nations,types,zones,requests,slots,count,
                _dimensions((B,C,which))),1)
            stats=self.catalog_stats.query(context,requests,count=count)
            _call(_kernels().political_creation_catalog,(slots,stats.stats,stats.errors,stats.message_ids,stats.batch_error,data,
                errors,failed,allowance,query_errors,messages,_dimensions((B,C,which))),B)
            if not which:first_ready=(slots>=0)&(errors==0)
        _call(_kernels().political_creation_capacity,(data,selected,needed_bytes,errors,failed,dims(state)),B)
        healthy=~(errors!=0).any();enabled=selected&healthy
        names=torch.zeros((B*Q,L),dtype=torch.uint8,device=dev);sizes=zero(B*Q);wanted=torch.zeros(B*Q,dtype=torch.bool,device=dev);name_errors=zero(B*Q)
        _call(_kernels().political_creation_names,(state.records,state.lengths,data,types,enabled,*shared,names,sizes,wanted,name_errors,dims(state)),B*Q)
        if Q:note(name_errors.reshape(B,Q).amax(1),selected)
        wanted&=~(errors!=0).any()
        interned=intern_bytes(state,names,sizes,wanted,string_capacity=string_capacity,byte_capacity=byte_capacity)
        if Q:note(torch.where((interned.errors.reshape(B,Q)&8)!=0,5,torch.where(interned.errors.reshape(B,Q)!=0,3,0)).amax(1),selected)
        note(torch.where(interned.pool_error!=0,3,0).expand(B),selected)
        current=interned.state;ids=interned.ids.reshape(B,Q);collision=torch.zeros((B,Q),dtype=torch.bool,device=dev)
        slot_errors=zero(B,Q);order=torch.full((B,Q),-1,dtype=torch.int64,device=dev)
        pool=(current.context.string_bytes,current.context.string_offsets,current.string_bytes,current.string_offsets,current.suffix_usage)
        enabled=selected&~(errors!=0).any()
        _call(_kernels().political_creation_collisions,(current.records,current.lengths,data,ids,enabled,*pool,collision,slot_errors,dims(current)),B*Q)
        if Q:note(slot_errors.amax(1),selected)
        _call(_kernels().political_creation_order,(current.records,current.lengths,data,ids,collision,enabled&~(errors!=0).any(),*pool,order,slot_errors,dims(current)),B*Q)
        if Q:note(slot_errors.amax(1),selected)
        inserted,unit_required_state,unit_required_block,measure_errors=zero(B),zero(B),zero(B),zero(B)
        _call(_kernels().political_creation_measure,(current.records,current.lengths,data,collision,allowance,selected&~(errors!=0).any(),
            inserted,unit_required_state,unit_required_block,measure_errors,dims(current)),B)
        required_state=torch.maximum(required_state,unit_required_state);required_block=torch.maximum(required_block,unit_required_block);note(measure_errors,selected)
        current,_=map_sequence(current,(data[:,0]+data[:,7]).contiguous(),selected&~(errors!=0).any())
        blocks,block_lengths,write_errors=zero(B,K,5),zero(B),zero(B)
        pool=(current.context.string_bytes,current.context.string_offsets,current.string_bytes,current.string_offsets,current.suffix_usage)
        _call(_kernels().political_creation_write,(current.records,current.lengths,data,ids,order,inserted,allowance,nations,types,zones,
            selected&~(errors!=0).any(),*pool,blocks,block_lengths,write_errors,dims(current,self.placed)),B)
        note(write_errors,selected)
        edited=replace_subtrees(current,data[:,5].contiguous(),blocks,block_lengths,selected&~(errors!=0).any(),capacity=S)
        required_state=torch.maximum(required_state,edited.required_capacity)
        note(torch.where(edited.errors!=0,torch.where((edited.errors&8)!=0,5,3),0),selected)
        committed=~(errors!=0).any();baseline_records=_pad(state.records,(B,S,5))
        output=DeviceStateBatch(state.context,torch.where(committed,edited.state.records,baseline_records),
            torch.where(committed,edited.state.lengths,state.lengths),torch.where(committed,edited.state.sections,state.sections),
            torch.where(committed,current.string_bytes,_pad(state.string_bytes,(byte_capacity,))),
            torch.where(committed,current.string_offsets,_pad(state.string_offsets,(string_capacity+1,))),state.errors,
            torch.where(committed,current.suffix_usage,state.suffix_usage))
        return PoliticalCreationResult(output,errors,ids,collision,inserted,query_errors,messages,failed,needed,needed_bytes,
            required_state,required_block,interned.required_usage,selected&committed,committed)
