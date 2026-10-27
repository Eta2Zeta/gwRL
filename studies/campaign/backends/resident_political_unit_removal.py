"""Exact resident removePoliticalUnits, including transitive carriedBy closure.

This internal effect does not validate casualty legality, refresh political or
income flags, append destruction Events, finish battles or consume RNG. Initial
requested IDs remain in the removal set even when no matching Unit exists: native
code also cancels repair jobs targeting such IDs. Unrelated payloads stay opaque.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_state_edits import replace_subtrees
from .metal_state_schema import METAL_STATE_SOURCE

PACKED_ERROR,CAPACITY_ERROR=3,5


@dataclass(frozen=True)
class PoliticalRemovalResult:
    state:DeviceStateBatch
    errors:torch.Tensor
    unit_ids:torch.Tensor             # Indexed universe for nonempty seed sets.
    unit_counts:torch.Tensor          # Empty seed sets need no inventory/index.
    removed_mask:torch.Tensor
    removed_counts:torch.Tensor
    required_unit_capacity:torch.Tensor
    required_request_capacity:torch.Tensor
    required_state_capacity:torch.Tensor
    required_block_capacity:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE="#include <metal_stdlib>\nusing namespace metal;\n"+METAL_STATE_SOURCE+r'''
inline bool ru_container(thread const PackedStateView& v,long node,long tag,long count,thread bool& valid){
 const long end=state_end(v,node,valid);if(!valid)return false;device const long* row=state_record(v,node);
 const long maximum=tag==7?(end-node-1)/2:end-node-1;
 if(row[0]!=tag||row[1]<0||row[1]>maximum||(count>=0&&row[1]!=count)||row[2]||row[3])valid=false;return valid;
}
inline bool ru_requested(long id,device const long* requested,long count){
 for(long i=0;i<count;++i)if(requested[i]==id)return true;return false;
}
inline bool ru_removed(long id,device const long* requested,long count,device const long* ids,device const bool* dead,long units){
 if(ru_requested(id,requested,count))return true;
 for(long i=0;i<units;++i)if(dead[i]&&ids[i]==id)return true;return false;
}
inline long ru_kept(thread const PackedStateView& v,long vector,device const long* requested,long count,
 device const long* ids,device const bool* dead,long units,thread bool& valid){
 ru_container(v,vector,6,-1,valid);if(!valid)return 0;long cursor=vector+1,kept=0;
 for(long i=0;i<state_record(v,vector)[1];++i){const long id=state_string_id(v,cursor,valid);
   if(!valid)return 0;if(!ru_removed(id,requested,count,ids,dead,units))++kept;cursor=state_end(v,cursor,valid);}
 if(!valid||cursor!=state_record(v,vector)[4])valid=false;return kept;
}
kernel void political_removal_plan(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const long* requested[[buffer(3)]],device const long* counts[[buffer(4)]],device const bool* selected[[buffer(5)]],
 device const uchar* prefix[[buffer(6)]],device const long* poffsets[[buffer(7)]],device const uchar* suffix[[buffer(8)]],
 device const long* soffsets[[buffer(9)]],device const long* usage[[buffer(10)]],device long* ids[[buffer(11)]],
 device long* unit_roots[[buffer(12)]],device long* parents[[buffer(13)]],device long* parent_indices[[buffer(14)]],
 device bool* dead[[buffer(15)]],device long* unit_counts[[buffer(16)]],device long* removed_counts[[buffer(17)]],
 device long* required_units[[buffer(18)]],device long* required_requests[[buffer(19)]],device long* roots[[buffer(20)]],
 device bool* changed[[buffer(21)]],device long* required_blocks[[buffer(22)]],device long* required_state[[buffer(23)]],
 device long* errors[[buffer(24)]],device const long* dims[[buffer(25)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],R=dims[2],U=dims[3];if(long(lane)>=B)return;
 unit_counts[lane]=removed_counts[lane]=required_units[lane]=required_requests[lane]=required_blocks[lane]=errors[lane]=0;
 required_state[lane]=lengths[lane];roots[lane]=-1;changed[lane]=false;if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
   prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,valid);
 if(inherited[lane]||v.length<=0||v.length>C)valid=false;ru_container(v,0,10,2,valid);
 if(valid&&state_record(v,0)[4]!=v.length)valid=false;
 const long state=state_child(v,0,0,valid);ru_container(v,state,10,19,valid);
 if(!valid){errors[lane]=3;return;}roots[lane]=state;const long amount=counts[lane];
 if(amount<0){errors[lane]=3;return;}required_requests[lane]=amount;
 if(amount>R){errors[lane]=5;return;}if(!amount)return;
 device const long* wanted=requested+ulong(lane)*R;
 for(long i=0;i<amount;++i)if(wanted[i]<0||wanted[i]>=v.prefix_count+v.suffix_count){errors[lane]=3;return;}
 const long units=state_child(v,state,2,valid);ru_container(v,units,7,-1,valid);
 if(!valid){errors[lane]=3;return;}const long N=state_record(v,units)[1];required_units[lane]=N;
 if(N>U){errors[lane]=5;return;}
 device long* names=ids+ulong(lane)*U;device long* nodes=unit_roots+ulong(lane)*U;
 device long* links=parents+ulong(lane)*U;device long* indexes=parent_indices+ulong(lane)*U;device bool* removed=dead+ulong(lane)*U;
 long cursor=units+1;
 for(long i=0;i<N;++i){names[i]=state_string_id(v,cursor,valid);nodes[i]=cursor+1;ru_container(v,nodes[i],10,14,valid);
   bool present=false;const long parent=state_optional(v,state_child(v,nodes[i],8,valid),present,valid);
   links[i]=present?state_string_id(v,parent,valid):-1;removed[i]=ru_requested(names[i],wanted,amount);cursor=state_end(v,nodes[i],valid);
   if(!valid){errors[lane]=3;return;}
 }if(cursor!=state_record(v,units)[4]){errors[lane]=3;return;}
 unit_counts[lane]=N;
 for(long i=0;i<N;++i){indexes[i]=-1;if(links[i]<0)continue;
   if(ru_requested(links[i],wanted,amount)){indexes[i]=-2;continue;}
   for(long j=0;j<N;++j)if(names[j]==links[i]){indexes[i]=j;break;}}
 // A monotone least fixed point, with no nesting-depth cap; cycles are valid
 // inputs to this helper and propagate exactly when connected to the seed set.
 bool progress=true;while(progress){progress=false;for(long i=0;i<N;++i)if(!removed[i]&&
   (indexes[i]==-2||(indexes[i]>=0&&removed[indexes[i]]))){removed[i]=true;progress=true;}}
 long new_units=1;
 for(long i=0;i<N;++i){if(removed[i]){++removed_counts[lane];changed[lane]=true;continue;}
   const long cargo=state_child(v,nodes[i],9,valid),kept=ru_kept(v,cargo,wanted,amount,names,removed,N,valid);
   if(!valid){errors[lane]=3;return;}const long dropped=state_record(v,cargo)[1]-kept;
   if(dropped)changed[lane]=true;new_units+=1+state_end(v,nodes[i],valid)-nodes[i]-dropped;
 }
 const long repairs=state_child(v,state,6,valid);ru_container(v,repairs,7,-1,valid);if(!valid){errors[lane]=3;return;}
 long new_repairs=1;cursor=repairs+1;
 for(long i=0;i<state_record(v,repairs)[1];++i){(void)state_string_id(v,cursor,valid);const long repair=cursor+1;ru_container(v,repair,10,7,valid);
   const long target=state_string_id(v,state_child(v,repair,2,valid),valid),end=state_end(v,repair,valid);
   if(!valid){errors[lane]=3;return;}
   if(ru_removed(target,wanted,amount,names,removed,N))changed[lane]=true;else new_repairs+=end-cursor;cursor=end;
 }if(cursor!=state_record(v,repairs)[4]){errors[lane]=3;return;}
 const long battles=state_child(v,state,12,valid);ru_container(v,battles,7,-1,valid);if(!valid){errors[lane]=3;return;}
 long dropped_battle_ids=0;cursor=battles+1;
 for(long i=0;i<state_record(v,battles)[1];++i){(void)state_string_id(v,cursor,valid);const long battle=cursor+1;ru_container(v,battle,10,10,valid);
   for(long field=5;field<=6;++field){const long group=state_child(v,battle,field,valid),kept=ru_kept(v,group,wanted,amount,names,removed,N,valid);
     if(!valid){errors[lane]=3;return;}dropped_battle_ids+=state_record(v,group)[1]-kept;}
   cursor=state_end(v,battle,valid);
 }if(cursor!=state_record(v,battles)[4]){errors[lane]=3;return;}if(dropped_battle_ids)changed[lane]=true;
 if(!valid){errors[lane]=3;return;}if(!changed[lane])return;
 const long delta=new_units-(state_end(v,units,valid)-units)+new_repairs-(state_end(v,repairs,valid)-repairs)-dropped_battle_ids;
 const long size=state_end(v,state,valid)-state+delta;
 required_blocks[lane]=size;required_state[lane]=lengths[lane]+delta;
 if(!valid||size<=0||delta>0||required_state[lane]<0){errors[lane]=3;return;}
 if(size>dims[9]||required_state[lane]>dims[8])errors[lane]=5;
}
inline void ru_copy(thread const PackedStateView& v,long start,long end,device long* out,long destination,long capacity,thread bool& valid){
 if(!valid)return;if(start<0||end<start||end>v.length||end>v.capacity||destination<0||destination>capacity||end-start>capacity-destination){valid=false;return;}
 for(long i=start;i<end;++i){for(long c=0;c<4;++c)out[ulong(destination+i-start)*5+c]=state_record(v,i)[c];
   out[ulong(destination+i-start)*5+4]=state_record(v,i)[4]+destination-start;}
}
inline void ru_row(device long* out,long at,long tag,long count,long capacity,thread bool& valid){
 if(!valid)return;if(at<0||at>=capacity){valid=false;return;}device long* row=out+ulong(at)*5;
 row[0]=tag;row[1]=count;row[2]=row[3]=0;row[4]=at+1;
}
inline long ru_vector(thread const PackedStateView& v,long source,device long* out,long destination,long capacity,
 device const long* wanted,long amount,device const long* ids,device const bool* dead,long N,thread bool& valid){
 const long root=destination;ru_row(out,root,6,0,capacity,valid);++destination;long kept=0,cursor=source+1;
 for(long i=0;valid&&i<state_record(v,source)[1];++i){const long id=state_string_id(v,cursor,valid),end=state_end(v,cursor,valid);
   if(!ru_removed(id,wanted,amount,ids,dead,N)){ru_copy(v,cursor,end,out,destination,capacity,valid);destination+=end-cursor;++kept;}cursor=end;}
 if(valid){out[ulong(root)*5+1]=kept;out[ulong(root)*5+4]=destination;}return destination;
}
inline long ru_units(thread const PackedStateView& v,long source,device long* out,long destination,long capacity,
 device const long* wanted,long amount,device const long* ids,device const bool* dead,long N,thread bool& valid){
 const long root=destination;ru_row(out,root,7,0,capacity,valid);++destination;long kept=0,cursor=source+1;
 for(long i=0;valid&&i<N;++i){const long unit=cursor+1,end=state_end(v,unit,valid);if(dead[i]){cursor=end;continue;}
   ru_copy(v,cursor,cursor+1,out,destination++,capacity,valid);const long target=destination;
   ru_copy(v,unit,unit+1,out,destination++,capacity,valid);long field=unit+1;
   for(long c=0;valid&&c<14;++c){const long next=state_end(v,field,valid);
     if(c==9)destination=ru_vector(v,field,out,destination,capacity,wanted,amount,ids,dead,N,valid);
     else{ru_copy(v,field,next,out,destination,capacity,valid);destination+=next-field;}field=next;}
   if(valid)out[ulong(target)*5+4]=destination;++kept;cursor=end;
 }if(valid){out[ulong(root)*5+1]=kept;out[ulong(root)*5+4]=destination;}return destination;
}
inline long ru_repairs(thread const PackedStateView& v,long source,device long* out,long destination,long capacity,
 device const long* wanted,long amount,device const long* ids,device const bool* dead,long N,thread bool& valid){
 const long root=destination;ru_row(out,root,7,0,capacity,valid);++destination;long kept=0,cursor=source+1;
 for(long i=0;valid&&i<state_record(v,source)[1];++i){const long repair=cursor+1,end=state_end(v,repair,valid);
   const long target=state_string_id(v,state_child(v,repair,2,valid),valid);
   if(!ru_removed(target,wanted,amount,ids,dead,N)){ru_copy(v,cursor,end,out,destination,capacity,valid);destination+=end-cursor;++kept;}cursor=end;
 }if(valid){out[ulong(root)*5+1]=kept;out[ulong(root)*5+4]=destination;}return destination;
}
inline long ru_battles(thread const PackedStateView& v,long source,device long* out,long destination,long capacity,
 device const long* wanted,long amount,device const long* ids,device const bool* dead,long N,thread bool& valid){
 const long root=destination;ru_copy(v,source,source+1,out,destination++,capacity,valid);long cursor=source+1;
 for(long i=0;valid&&i<state_record(v,source)[1];++i){const long battle=cursor+1,end=state_end(v,battle,valid);
   ru_copy(v,cursor,cursor+1,out,destination++,capacity,valid);const long target=destination;
   ru_copy(v,battle,battle+1,out,destination++,capacity,valid);long field=battle+1;
   for(long c=0;valid&&c<10;++c){const long next=state_end(v,field,valid);
     if(c==5||c==6)destination=ru_vector(v,field,out,destination,capacity,wanted,amount,ids,dead,N,valid);
     else{ru_copy(v,field,next,out,destination,capacity,valid);destination+=next-field;}field=next;}
   if(valid)out[ulong(target)*5+4]=destination;cursor=end;
 }if(valid)out[ulong(root)*5+4]=destination;return destination;
}
kernel void political_removal_write(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* roots[[buffer(2)]],
 device const long* requested[[buffer(3)]],device const long* counts[[buffer(4)]],device const long* ids[[buffer(5)]],
 device const bool* dead[[buffer(6)]],device const long* unit_counts[[buffer(7)]],device const long* required[[buffer(8)]],
 device const bool* selected[[buffer(9)]],device const uchar* prefix[[buffer(10)]],device const long* poffsets[[buffer(11)]],
 device const uchar* suffix[[buffer(12)]],device const long* soffsets[[buffer(13)]],device const long* usage[[buffer(14)]],
 device long* output[[buffer(15)]],device long* actual[[buffer(16)]],device long* errors[[buffer(17)]],
 device const long* dims[[buffer(18)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],R=dims[2],U=dims[3],K=dims[9];if(long(lane)>=B)return;actual[lane]=errors[lane]=0;if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
   prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,valid);
 if(required[lane]<=0||required[lane]>K){errors[lane]=5;return;}
 device long* out=output+ulong(lane)*K*5;device const long* wanted=requested+ulong(lane)*R;
 device const long* names=ids+ulong(lane)*U;device const bool* removed=dead+ulong(lane)*U;
 const long N=unit_counts[lane],amount=counts[lane],state=roots[lane];
 ru_copy(v,state,state+1,out,0,K,valid);long cursor=state+1,destination=1;
 for(long field=0;valid&&field<19;++field){const long end=state_end(v,cursor,valid);
   if(field==2)destination=ru_units(v,cursor,out,destination,K,wanted,amount,names,removed,N,valid);
   else if(field==6)destination=ru_repairs(v,cursor,out,destination,K,wanted,amount,names,removed,N,valid);
   else if(field==12)destination=ru_battles(v,cursor,out,destination,K,wanted,amount,names,removed,N,valid);
   else{ru_copy(v,cursor,end,out,destination,K,valid);destination+=end-cursor;}cursor=end;
 }if(!valid||destination!=required[lane]){errors[lane]=3;return;}out[4]=destination;actual[lane]=destination;
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
        raise ValueError("Political removal requires complete contiguous resident inputs")


class ResidentPoliticalUnitRemoval:
    def __init__(self,state_context):
        if _device(state_context.device).type!="mps":raise ValueError("Political removal requires explicit Apple GPU execution; no fallback")
        self.state_context=state_context

    def remove(self,state,ids,counts,selected=None,*,unit_capacity,state_capacity=None,block_capacity=None):
        """Remove the complete per-lane seed sets and all carried descendants.

        ids[B,R] and counts[B] are a fixed reusable request arena. Capacities
        describe allocations, never unit/choice/depth limits; insufficient space
        reports exact required sizes without publishing a partial deletion.
        Empty seed sets need no unit index. On planning failure masks/counts are
        diagnostic only; accepted/committed determine whether anything happened.
        """
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Political removal source context differs")
        state._metadata();_device(state.device);B,C=state.records.shape[:2];dev=state.device
        if not isinstance(ids,torch.Tensor) or ids.ndim!=2 or ids.shape[0]!=B:raise ValueError("Removal IDs require [lane,request capacity]")
        R=ids.shape[1];_tensor(ids,state,torch.int64,(B,R));_tensor(counts,state,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,state,torch.bool,(B,))
        U=unit_capacity;S=C if state_capacity is None else state_capacity;K=max(1,C) if block_capacity is None else block_capacity
        if type(U) is not int or U<0 or type(S) is not int or S<C or type(K) is not int or K<1:
            raise ValueError("Removal allocations must preserve the complete original state arena")
        if B>2**32-1 or max(C,S,K,U,R)>2**63-1 or max(B*max(C,S,K,1)*5,B*max(U,R,1))*8>2**63-1:
            raise OverflowError("Political removal allocations are not representable; no input truncated")
        for value in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets,state.suffix_usage,
                      state.context.string_bytes,state.context.string_offsets):
            if value.device!=dev or not value.is_contiguous():raise ValueError("Removal buffers must remain contiguous and resident")
        zeros=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        names=torch.full((B,U),-1,dtype=torch.int64,device=dev);nodes=torch.full_like(names,-1)
        parents=torch.full_like(names,-1);parent_indices=torch.full_like(names,-1);dead=torch.zeros((B,U),dtype=torch.bool,device=dev)
        unit_counts,removed_counts,required_units,required_requests,roots,required_blocks,required_state,errors=(zeros(B) for _ in range(8))
        changed=torch.zeros(B,dtype=torch.bool,device=dev)
        dims=_dimensions((B,C,R,U,state.context.string_count,state.context.string_bytes.numel(),state.string_offsets.numel()-1,state.string_bytes.numel(),S,K))
        _call(_kernels().political_removal_plan,(state.records,state.lengths,state.errors,ids,counts,selected,state.context.string_bytes,
            state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage,names,nodes,parents,parent_indices,dead,
            unit_counts,removed_counts,required_units,required_requests,roots,changed,required_blocks,required_state,errors,dims),B)
        writing=selected&changed&~(errors!=0).any();blocks=zeros(B,K,5);lengths=zeros(B);write_errors=zeros(B)
        _call(_kernels().political_removal_write,(state.records,state.lengths,roots,ids,counts,names,dead,unit_counts,required_blocks,writing,
            state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage,blocks,lengths,write_errors,dims),B)
        errors=torch.where(selected&(errors==0)&(write_errors!=0),write_errors,errors)
        edited=replace_subtrees(state,roots,blocks,lengths,writing&~(errors!=0).any(),capacity=S)
        details=torch.where(edited.errors!=0,torch.where((edited.errors&8)!=0,CAPACITY_ERROR,PACKED_ERROR),0)
        errors=torch.where(selected&(errors==0)&(details!=0),details,errors);committed=~(errors!=0).any()
        return PoliticalRemovalResult(edited.state,errors,names,unit_counts,dead,removed_counts,required_units,required_requests,
            torch.maximum(required_state,edited.required_capacity),required_blocks,selected&committed,committed)
