"""Exact evolving-owner movement refresh from resident canonical State.

Only the selected owner's existing units are queried against the source-bound
Catalog. Used movement is preserved; an absent new allowance clears that
optional while retaining the old remaining-movement optional. This helper does
not promote a nation, refresh politics/income, advance time or resolve combat.
Like its native helper, it does not replace outer Engine State validation.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_state_edits import replace_subtrees
from .metal_state_schema import METAL_STATE_SOURCE

LOOKUP_ERROR,NATIVE_ERROR,PACKED_ERROR,INT_OVERFLOW,CAPACITY_ERROR=1,2,3,4,5


@dataclass(frozen=True)
class PoliticalMovementResult:
    state:DeviceStateBatch
    errors:torch.Tensor
    requests:torch.Tensor
    query_errors:torch.Tensor
    message_ids:torch.Tensor
    count:torch.Tensor
    required_count:torch.Tensor
    required_state_capacity:torch.Tensor
    required_block_capacity:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE="#include <metal_stdlib>\nusing namespace metal;\n"+METAL_STATE_SOURCE+r'''
inline bool pu_container(thread const PackedStateView& v,long at,long tag,long count,thread bool& valid){
 const long end=state_end(v,at,valid);if(!valid)return false;device const long* row=state_record(v,at);
 const long maximum=tag==7?(end-at-1)/2:end-at-1;
 if(row[0]!=tag||row[1]<0||row[1]>maximum||(count>=0&&row[1]!=count)||row[2]||row[3])valid=false;return valid;
}
kernel void political_movement_count(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const long* owners[[buffer(3)]],device const bool* selected[[buffer(4)]],device const uchar* prefix[[buffer(5)]],
 device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],device const long* soffsets[[buffer(8)]],
 device const long* usage[[buffer(9)]],device long* counts[[buffer(10)]],device long* roots[[buffer(11)]],
 device long* errors[[buffer(12)]],device const long* dims[[buffer(13)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;counts[lane]=errors[lane]=0;roots[lane]=-1;if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
   prefix,poffsets,dims[3],dims[4],suffix,soffsets,dims[5],dims[6],usage,valid);
 if(inherited[lane]||owners[lane]<0||owners[lane]>=v.prefix_count+v.suffix_count)valid=false;
 pu_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);pu_container(v,state,10,19,valid);
 const long units=state_child(v,state,2,valid);pu_container(v,units,7,-1,valid);
 if(!valid){errors[lane]=3;return;}roots[lane]=units;long cursor=units+1;
 for(long i=0;i<state_record(v,units)[1];++i){
   (void)state_string_id(v,cursor,valid);const long unit=cursor+1;pu_container(v,unit,10,14,valid);
   const long owner=state_string_id(v,state_child(v,unit,2,valid),valid);
   if(!valid){errors[lane]=3;return;}if(owner==owners[lane])++counts[lane];cursor=state_end(v,unit,valid);
 }
 if(!valid||cursor!=state_record(v,units)[4])errors[lane]=3;
}
kernel void political_movement_rank(device const long* counts[[buffer(0)]],device const long* errors[[buffer(1)]],
 device long* ranks[[buffer(2)]],device long* count[[buffer(3)]],device long* required[[buffer(4)]],
 device long* batch[[buffer(5)]],device const long* dims[[buffer(6)]],uint tid[[thread_position_in_grid]]){
 if(tid)return;long total=0,error=0;
 for(long lane=0;lane<dims[0];++lane){ranks[lane]=total;if(errors[lane])error=3;
   if(counts[lane]<0||counts[lane]>LONG_MAX-total){error=3;continue;}total+=counts[lane];}
 required[0]=total;if(!error&&total>dims[2])error=5;batch[0]=error;count[0]=error?0:total;
}
kernel void political_movement_requests(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* owners[[buffer(2)]],
 device const bool* selected[[buffer(3)]],device const long* roots[[buffer(4)]],device const long* ranks[[buffer(5)]],
 device const long* batch[[buffer(6)]],device const uchar* prefix[[buffer(7)]],device const long* poffsets[[buffer(8)]],
 device const uchar* suffix[[buffer(9)]],device const long* soffsets[[buffer(10)]],device const long* usage[[buffer(11)]],
 device long* requests[[buffer(12)]],device long* unit_roots[[buffer(13)]],device long* errors[[buffer(14)]],
 device const long* dims[[buffer(15)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0]||!selected[lane]||batch[0]||errors[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
   prefix,poffsets,dims[3],dims[4],suffix,soffsets,dims[5],dims[6],usage,valid);
 const long units=roots[lane];long cursor=units+1,row=ranks[lane];
 for(long i=0;valid&&i<state_record(v,units)[1];++i){const long unit=cursor+1;
   const long owner=state_string_id(v,state_child(v,unit,2,valid),valid);
   if(owner==owners[lane]){
     if(row<0||row>=dims[2]){errors[lane]=3;return;}device long* out=requests+ulong(row)*5;
     out[0]=lane;out[1]=state_string_id(v,state_child(v,unit,1,valid),valid);
     out[2]=state_signed_value(v,state_child(v,unit,10,valid),valid);out[3]=owner;
     out[4]=state_string_id(v,state_child(v,unit,3,valid),valid);unit_roots[row]=unit;++row;
   }cursor=state_end(v,unit,valid);
 }if(!valid)errors[lane]=3;
}
kernel void political_movement_values(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* requests[[buffer(2)]],
 device const long* roots[[buffer(3)]],device const long* count[[buffer(4)]],device const long* stats[[buffer(5)]],
 device const long* stats_errors[[buffer(6)]],device const uchar* prefix[[buffer(7)]],device const long* poffsets[[buffer(8)]],
 device const uchar* suffix[[buffer(9)]],device const long* soffsets[[buffer(10)]],device const long* usage[[buffer(11)]],
 device long* values[[buffer(12)]],device long* delta[[buffer(13)]],device long* errors[[buffer(14)]],
 device const long* dims[[buffer(15)]],uint row[[thread_position_in_grid]]){
 if(long(row)>=dims[2])return;errors[row]=delta[row]=0;for(long i=0;i<4;++i)values[ulong(row)*4+i]=0;
 if(long(row)>=count[0]||stats_errors[row])return;const long lane=requests[ulong(row)*5],unit=roots[row];
 if(lane<0||lane>=dims[0]){errors[row]=3;return;}
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
   prefix,poffsets,dims[3],dims[4],suffix,soffsets,dims[5],dims[6],usage,valid);
 pu_container(v,unit,10,14,valid);bool remaining_present=false,allowance_present=false;
 const long remaining_node=state_optional(v,state_child(v,unit,4,valid),remaining_present,valid);
 const long allowance_node=state_optional(v,state_child(v,unit,5,valid),allowance_present,valid);
 const long remaining=remaining_present?state_signed_value(v,remaining_node,valid):0;
 const long allowance=allowance_present?state_signed_value(v,allowance_node,valid):0;
 if(!valid||remaining<INT_MIN||remaining>INT_MAX||allowance<INT_MIN||allowance>INT_MAX){errors[row]=3;return;}
 long used=0;if(remaining_present&&allowance_present){const long difference=allowance-remaining;
   if(difference<INT_MIN||difference>INT_MAX){errors[row]=4;return;}used=max(0L,difference);}
 const long present=stats[ulong(row)*18+8],movement=stats[ulong(row)*18+9];
 if(present<0||present>1||(present&&(movement<INT_MIN||movement>INT_MAX))){errors[row]=3;return;}
 device long* out=values+ulong(row)*4;out[0]=remaining_present;out[1]=remaining;out[2]=present;out[3]=present?movement:0;
 if(present){const long flags=state_child(v,unit,12,valid),placed=state_map_find_literal(v,flags,"placed_this_turn",16,valid);
   const bool fresh=placed>=0&&state_signed_value(v,placed,valid)!=0;
   if(!valid){errors[row]=3;return;}
   long next=0;if(!fresh){const long difference=movement-used;
     if(difference<INT_MIN||difference>INT_MAX){errors[row]=4;return;}next=max(0L,difference);}
   out[0]=1;out[1]=next;
 }delta[row]=out[0]-long(remaining_present)+present-long(allowance_present);
}
kernel void political_movement_summary(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* roots[[buffer(2)]],
 device const long* counts[[buffer(3)]],device const long* ranks[[buffer(4)]],device const long* batch[[buffer(5)]],
 device const long* lane_errors[[buffer(6)]],device const long* stats_errors[[buffer(7)]],device const long* value_errors[[buffer(8)]],
 device const long* delta[[buffer(9)]],device const bool* selected[[buffer(10)]],device long* errors[[buffer(11)]],
 device long* required_block[[buffer(12)]],device long* required_state[[buffer(13)]],device const long* dims[[buffer(14)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;errors[lane]=0;required_block[lane]=0;required_state[lane]=lengths[lane];if(!selected[lane])return;
 if(lane_errors[lane]){errors[lane]=lane_errors[lane];return;}if(batch[0]){errors[lane]=batch[0];return;}
 if(!counts[lane])return;
 const long root=roots[lane];if(root<0||root>=lengths[lane]||root>=dims[1]){errors[lane]=3;return;}
 long difference=0;
 for(long q=ranks[lane];q<ranks[lane]+counts[lane];++q){
   if(q<0||q>=dims[2]){errors[lane]=3;return;}
   if(stats_errors[q]){errors[lane]=stats_errors[q];return;}if(value_errors[q]){errors[lane]=value_errors[q];return;}
   difference+=delta[q];
 }
 required_block[lane]=records[(ulong(lane)*dims[1]+root)*5+4]-root+difference;
 required_state[lane]=lengths[lane]+difference;
 if(required_block[lane]<0||required_state[lane]<0){errors[lane]=3;return;}
 if(required_block[lane]>dims[8]||required_state[lane]>dims[7])errors[lane]=5;
}
inline void pu_copy(thread const PackedStateView& v,long start,long end,device long* out,long destination){
 for(long i=start;i<end;++i){for(long c=0;c<4;++c)out[ulong(destination+i-start)*5+c]=state_record(v,i)[c];
   out[ulong(destination+i-start)*5+4]=state_record(v,i)[4]+destination-start;}
}
inline void pu_optional(device long* out,long at,long present,long value){
 device long* r=out+ulong(at)*5;r[0]=9;r[1]=present;r[2]=r[3]=0;r[4]=at+1+present;
 if(present){r+=5;r[0]=2;r[1]=0;r[2]=long(as_type<ulong>(value)&0xffffffffUL);r[3]=long(as_type<ulong>(value)>>32);r[4]=at+2;}
}
kernel void political_movement_write(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* roots[[buffer(2)]],
 device const long* owners[[buffer(3)]],device const long* ranks[[buffer(4)]],device const long* values[[buffer(5)]],
 device const long* delta[[buffer(6)]],device const long* required[[buffer(7)]],device const bool* selected[[buffer(8)]],
 device const uchar* prefix[[buffer(9)]],device const long* poffsets[[buffer(10)]],device const uchar* suffix[[buffer(11)]],
 device const long* soffsets[[buffer(12)]],device const long* usage[[buffer(13)]],device long* output[[buffer(14)]],
 device long* actual[[buffer(15)]],device long* errors[[buffer(16)]],device const long* dims[[buffer(17)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;actual[lane]=errors[lane]=0;if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
   prefix,poffsets,dims[3],dims[4],suffix,soffsets,dims[5],dims[6],usage,valid);
 const long root=roots[lane],R=dims[8];if(required[lane]>R){errors[lane]=5;return;}
 device long* out=output+ulong(lane)*R*5;pu_copy(v,root,root+1,out,0);out[4]=required[lane];
 long cursor=root+1,destination=1,q=ranks[lane];
 for(long i=0;i<state_record(v,root)[1];++i){const long unit=cursor+1,end=state_end(v,unit,valid);
   pu_copy(v,cursor,cursor+1,out,destination++);
   const long owner=state_string_id(v,state_child(v,unit,2,valid),valid);
   if(!valid){errors[lane]=3;return;}
   if(owner!=owners[lane]){pu_copy(v,unit,end,out,destination);destination+=end-unit;cursor=end;continue;}
   if(q<0||q>=dims[2]){errors[lane]=3;return;}
   pu_copy(v,unit,unit+1,out,destination);out[ulong(destination)*5+4]=destination+end-unit+delta[q];++destination;
   long field=unit+1;
   for(long child=0;child<14;++child){const long stop=state_end(v,field,valid);
     if(!valid){errors[lane]=3;return;}
     if(child==4||child==5){const long item=(child==4?0:2),present=values[ulong(q)*4+item];
       pu_optional(out,destination,present,values[ulong(q)*4+item+1]);destination+=1+present;
     }else{pu_copy(v,field,stop,out,destination);destination+=stop-field;}field=stop;
   }++q;cursor=end;
 }
 if(!valid||destination!=required[lane]){errors[lane]=3;return;}actual[lane]=destination;
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
        raise ValueError("Political unit refresh requires complete contiguous resident inputs")


class ResidentPoliticalUnits:
    def __init__(self,state_context,catalog_stats):
        if _device(state_context.device).type!="mps" or catalog_stats.state_context is not state_context:
            raise ValueError("Political unit refresh requires exact shared Apple GPU state/catalog contexts")
        self.state_context=state_context;self.catalog_stats=catalog_stats

    def reserve(self,state,*,unit_capacity):
        """Metadata-only worst-case optional-field headroom, not an entity limit."""
        if type(unit_capacity) is not int or unit_capacity<0:raise ValueError("Unit capacity must be a nonnegative allocation")
        C=state.records.shape[1]
        # Q spans the whole batch; a single lane has at most C//16 native
        # key+UnitState entries, even when every optional field is absent.
        extra=2*min(unit_capacity,C//16)
        return dict(unit_capacity=unit_capacity,state_capacity=C+extra,block_capacity=max(1,C+extra))

    def refresh_movement(self,state,owners,selected=None,*,unit_capacity,state_capacity=None,block_capacity=None):
        """Refresh every selected owner's unit in native lane/map order.

        unit_capacity is an explicit reusable query allocation. An insufficient
        allocation reports the complete required count and publishes no partial
        refresh. Only matching units are ever evaluated by Catalog::stats.
        """
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Political unit source context differs")
        state._metadata();_device(state.device);B,C=state.records.shape[:2];dev=state.device
        _tensor(owners,state,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,state,torch.bool,(B,))
        Q=unit_capacity;S=C if state_capacity is None else state_capacity;K=max(1,C) if block_capacity is None else block_capacity
        if type(Q) is not int or Q<0 or Q>2**32-1 or type(S) is not int or S<C or type(K) is not int or K<1:
            raise ValueError("Political unit allocations must be complete and preserve the source arena")
        if B>2**32-1 or B*max(C,S,K,1)*5>2**63-1 or Q*max(C,1)*19>2**63-1:raise OverflowError("Political unit allocations are not representable")
        for value in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets,state.suffix_usage,
                      state.context.string_bytes,state.context.string_offsets):
            if value.device!=dev or not value.is_contiguous():raise ValueError("Political unit buffers must stay resident and contiguous")
        zeros=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        counts,roots,lane_errors,ranks=zeros(B),zeros(B),zeros(B),zeros(B)
        count,required_count,batch=zeros(1),zeros(1),zeros(1)
        dims=_dimensions((B,C,Q,state.context.string_count,state.context.string_bytes.numel(),state.string_offsets.numel()-1,state.string_bytes.numel(),S,K))
        _call(_kernels().political_movement_count,(state.records,state.lengths,state.errors,owners,selected,state.context.string_bytes,
            state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage,counts,roots,lane_errors,dims),B)
        _call(_kernels().political_movement_rank,(counts,lane_errors,ranks,count,required_count,batch,dims),1)
        requests=zeros(Q,5);unit_roots=torch.full((Q,),-1,dtype=torch.int64,device=dev)
        _call(_kernels().political_movement_requests,(state.records,state.lengths,owners,selected,roots,ranks,batch,state.context.string_bytes,
            state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage,requests,unit_roots,lane_errors,dims),B)
        # These requests contain selected owners only; querying the full unit
        # inventory and masking its errors would violate native lazy semantics.
        stats=self.catalog_stats.query(state,requests,count=count)
        values,delta,value_errors=zeros(Q,4),zeros(Q),zeros(Q)
        _call(_kernels().political_movement_values,(state.records,state.lengths,requests,unit_roots,count,stats.stats,stats.errors,
            state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage,values,delta,value_errors,dims),Q)
        errors,required_block,required_state=zeros(B),zeros(B),zeros(B)
        _call(_kernels().political_movement_summary,(state.records,state.lengths,roots,counts,ranks,batch,lane_errors,stats.errors,value_errors,delta,
            selected,errors,required_block,required_state,dims),B)
        errors=torch.where(selected&((stats.batch_error!=0).any())&(errors==0),PACKED_ERROR,errors)
        healthy=~(errors!=0).any();writing=selected&(counts>0)&healthy
        blocks,lengths,write_errors=zeros(B,K,5),zeros(B),zeros(B)
        _call(_kernels().political_movement_write,(state.records,state.lengths,roots,owners,ranks,values,delta,required_block,writing,
            state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage,blocks,lengths,write_errors,dims),B)
        errors=torch.where(selected&(errors==0)&(write_errors!=0),write_errors,errors)
        edited=replace_subtrees(state,roots,blocks,lengths,writing&~(errors!=0).any(),capacity=S)
        details=torch.where(edited.errors!=0,torch.where((edited.errors&8)!=0,CAPACITY_ERROR,PACKED_ERROR),0)
        errors=torch.where(selected&(errors==0)&(details!=0),details,errors)
        committed=~(errors!=0).any()
        return PoliticalMovementResult(edited.state,errors,requests,stats.errors,stats.message_ids,count,required_count,
            torch.maximum(required_state,edited.required_capacity),required_block,selected&committed,committed)
