"""Append native-exact audit Events with record/string-cohort rollback.

The caller supplies a completed State identity and a generic JSON payload forest
bound to that exact immutable source. This operation records an event; it does
not apply a game rule, change a phase or consume RNG. No historical State copies
are retained. Planning identities remain valid because they exclude history.
"""
from dataclasses import dataclass,replace
from enum import IntEnum,IntFlag
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_state_edits import SOURCE as EDIT_SOURCE
from .device_map_edits import build_sequence_splices,commit_container_edits
from .device_strings import intern_bytes


class EventKind(IntEnum):
    ACTION=0
    INTERRUPT=1
    CHANCE=2


class EventError(IntFlag):
    SOURCE=1
    KIND=2
    PAYLOAD=4
    HASH=8
    STATE_CAPACITY=16
    BLOCK_CAPACITY=32


@dataclass(frozen=True)
class EventLabels:
    context: object
    ids: torch.Tensor


@dataclass(frozen=True)
class PreparedEventLabels:
    state: DeviceStateBatch
    labels: EventLabels
    errors: torch.Tensor
    committed: torch.Tensor
    required_usage: torch.Tensor


@dataclass(frozen=True)
class EventPayloads:
    source: DeviceStateBatch
    records: torch.Tensor     # [B,R,5], one generic JSON subtree at local root0.
    lengths: torch.Tensor     # [B], complete actual payload record counts.
    errors: torch.Tensor      # [B], caller's source/builder errors.


@dataclass(frozen=True)
class EventAppendResult:
    state: DeviceStateBatch
    identities: object
    errors: torch.Tensor      # preflight low byte; interner<<8, builder<<16, editor<<24.
    accepted: torch.Tensor
    committed: torch.Tensor
    required_state_capacity: torch.Tensor
    required_block_capacity: torch.Tensor
    required_string_usage: torch.Tensor
    batch_error: torch.Tensor


SOURCE=EDIT_SOURCE+r'''
inline bool event_container(thread const PackedStateView& v,long node,long tag,long count,thread bool& valid){
 const long end=state_end(v,node,valid);if(!valid)return false;device const long* r=state_record(v,node);
 const long maximum=tag==7||tag==13?(end-node-1)/2:end-node-1;
 if(r[0]!=tag||r[1]<0||r[1]>maximum||(count>=0&&r[1]!=count)||r[2]||r[3])valid=false;return valid;
}
inline bool event_string(thread const PackedStateView& v,long id){
 if(id<0||id>=v.prefix_count+v.suffix_count)return false;
 const bool prefix=id<v.prefix_count;const long local=prefix?id:id-v.prefix_count;
 device const long* offsets=prefix?v.prefix_offsets:v.suffix_offsets;
 return offsets[local]>=0&&offsets[local+1]>=offsets[local]&&offsets[local+1]<=(prefix?v.prefix_bytes_length:v.suffix_bytes_length);
}
kernel void validate_event_append(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const uchar* prefix_bytes[[buffer(3)]],device const long* prefix_offsets[[buffer(4)]],
 device const uchar* suffix_bytes[[buffer(5)]],device const long* suffix_offsets[[buffer(6)]],device const long* usage[[buffer(7)]],
 device const long* payloads[[buffer(8)]],device const long* payload_lengths[[buffer(9)]],device const long* payload_errors[[buffer(10)]],
 device const long* kinds[[buffer(11)]],device const long* labels[[buffer(12)]],device const uchar* hashes[[buffer(13)]],
 device const int* hash_errors[[buffer(14)]],device const int* batch_error[[buffer(15)]],device const bool* selected[[buffer(16)]],
 device long* errors[[buffer(17)]],device long* roots[[buffer(18)]],device long* begins[[buffer(19)]],
 device long* required_state[[buffer(20)]],device long* required_block[[buffer(21)]],
 device long* ends[[buffer(22)]],device long* remaining[[buffer(23)]],device long* previous[[buffer(24)]],
 device const long* dims[[buffer(25)]],uint lane[[thread_position_in_grid]]) {
 const long B=dims[0],C=dims[1],R=dims[2];if(long(lane)>=B)return;
 errors[lane]=0;roots[lane]=-1;begins[lane]=0;required_state[lane]=lengths[lane];required_block[lane]=0;
 if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*ulong(C)*5,lengths[lane],C,
   prefix_bytes,prefix_offsets,dims[3],dims[4],suffix_bytes,suffix_offsets,dims[5],dims[6],usage,valid);
 if(!valid||inherited[lane]){errors[lane]|=1;return;}
 event_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);event_container(v,state,10,19,valid);
 const long history=state_child(v,state,16,valid);event_container(v,history,6,-1,valid);
 if(!valid){errors[lane]|=1;return;}roots[lane]=history;begins[lane]=state_record(v,history)[1];
 const long kind=kinds[lane];
 if(kind<0||kind>2)errors[lane]|=2;
 else {bool label_valid=true;const long id=labels[kind];bool match=false;
   if(kind==0)match=state_string_id_equals(v,id,"action",6,label_valid);
   else if(kind==1)match=state_string_id_equals(v,id,"interrupt",9,label_valid);
   else match=state_string_id_equals(v,id,"chance",6,label_valid);
   if(!match||!label_valid)errors[lane]|=2;
 }
 if(hash_errors[lane]||batch_error[0])errors[lane]|=8;
 for(long i=0;i<64;++i){const uchar c=hashes[ulong(lane)*64+ulong(i)];
   if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))errors[lane]|=8;}
 const long L=payload_lengths[lane];bool pv=true;
 PackedStateView p=make_packed_state_view(payloads+ulong(lane)*ulong(R)*5,L,R,
   prefix_bytes,prefix_offsets,dims[3],dims[4],suffix_bytes,suffix_offsets,dims[5],dims[6],usage,pv);
 if(!pv||payload_errors[lane]||!edit_tree(p,ends+ulong(lane)*ulong(R),remaining+ulong(lane)*ulong(R),
     previous+ulong(lane)*ulong(R)*2))errors[lane]|=4;
 else for(long i=0;i<L;++i){device const long* row=state_record(p,i);const long tag=row[0];
   if(tag!=0&&tag!=1&&tag!=4&&tag!=5&&tag!=12&&tag!=13){errors[lane]|=4;break;}
   if(tag==5&&!event_string(p,row[1])){errors[lane]|=4;break;}}
 if(!(errors[lane]&4)){
   const long old=state_end(v,history,valid)-history;
   if(L>LONG_MAX-3||L+3>LONG_MAX-lengths[lane]||L+3>LONG_MAX-old){errors[lane]|=4;return;}
   required_state[lane]=lengths[lane]+L+3;required_block[lane]=old+L+3;
   if(required_state[lane]>dims[7])errors[lane]|=16;
   if(required_block[lane]>dims[8])errors[lane]|=32;
 }
}
kernel void write_event_blocks(device const long* payloads[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* kinds[[buffer(2)]],device const long* labels[[buffer(3)]],device const long* hash_ids[[buffer(4)]],
 device const bool* selected[[buffer(5)]],device long* output[[buffer(6)]],device long* actual[[buffer(7)]],
 device const long* dims[[buffer(8)]],uint lane[[thread_position_in_grid]]) {
 const long B=dims[0],R=dims[1],O=R+3;if(long(lane)>=B)return;
 actual[lane]=0;if(!selected[lane])return;const long L=lengths[lane];device long* out=output+ulong(lane)*ulong(O)*5;
 for(long i=0;i<(L+3)*5;++i)out[i]=0;
 out[0]=10;out[1]=3;out[4]=L+3;
 out[5]=5;out[6]=labels[kinds[lane]];out[9]=2;
 for(long i=0;i<L;++i){device const long* src=payloads+(ulong(lane)*ulong(R)+ulong(i))*5;
   for(long col=0;col<4;++col)out[(i+2)*5+col]=src[col];out[(i+2)*5+4]=src[4]+2;}
 out[(L+2)*5]=5;out[(L+2)*5+1]=hash_ids[lane];out[(L+2)*5+4]=L+3;actual[lane]=L+3;
}
'''

_library=None
_lock=threading.Lock()

def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    return _library

@lru_cache(maxsize=32)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device='mps')

@lru_cache(maxsize=1)
def _dummy():return torch.zeros(1,dtype=torch.int64,device='mps')

@lru_cache(maxsize=1)
def _label_requests():
    return (torch.tensor([list(b'action')+[0]*3,list(b'interrupt'),list(b'chance')+[0]*3],dtype=torch.uint8,device='mps'),
            torch.tensor([6,9,6],dtype=torch.int64,device='mps'))


def prepare_event_labels(state,*,string_capacity=None,byte_capacity=None):
    """One-time resident label interning; use returned state before hashing it."""
    state._metadata()
    if _device(state.device).type!='mps':raise ValueError('Event append requires explicit Apple GPU execution')
    requests,lengths=_label_requests()
    result=intern_bytes(state,requests,lengths,string_capacity=string_capacity,byte_capacity=byte_capacity)
    return PreparedEventLabels(result.state,EventLabels(state.context,result.ids),result.errors,result.committed,result.required_usage)


def _tensor(value,state,dtype,shape):
    if not isinstance(value,torch.Tensor) or value.dtype!=dtype or value.device!=state.device or \
       value.shape!=shape or not value.is_contiguous():raise ValueError('Event source shape/device/layout differs')


def append_events(state,identities,payloads,kinds,labels,*,selected=None,state_capacity=None,block_capacity=None,
                  string_capacity=None,byte_capacity=None):
    """Append one complete Event per selected lane, atomically across the cohort.

    Every capacity defaults to its current allocation. A failed append reports
    exact requirements; retry never drops payloads, entries or random state.
    Unselected malformed payloads do not veto selected lanes.
    """
    state._metadata();_device(state.device)
    if state.device.type!='mps':raise ValueError('Event append requires explicit Apple GPU execution')
    if identities.source is not state or payloads.source is not state:
        raise ValueError('Event identity and payload must belong to the exact complete source state')
    if labels.context is not state.context:raise ValueError('Event labels belong to another packed context')
    B,C=state.records.shape[:2]
    if not isinstance(payloads.records,torch.Tensor) or payloads.records.ndim!=3 or payloads.records.shape[0]!=B or payloads.records.shape[2]!=5:
        raise ValueError('Event payloads must retain complete [lane,capacity,5] generic JSON records')
    R=payloads.records.shape[1]
    if B>(1<<32)-1 or B*max(C,R+3,1)*5>(1<<63)-1:raise OverflowError('Event arena allocation cannot be represented')
    state_capacity=C if state_capacity is None else state_capacity
    block_capacity=max(C,1) if block_capacity is None else block_capacity
    if type(state_capacity) is not int or state_capacity<C or type(block_capacity) is not int or block_capacity<1:
        raise ValueError('Event capacities must preserve the complete original allocation')
    if selected is None:selected=torch.ones(B,dtype=torch.bool,device=state.device)
    keys=identities.state_keys
    for value,dtype,shape in ((payloads.records,torch.int64,(B,R,5)),(payloads.lengths,torch.int64,(B,)),
          (payloads.errors,torch.int64,(B,)),(kinds,torch.int64,(B,)),(labels.ids,torch.int64,(3,)),
          (keys.hex_bytes,torch.uint8,(B,64)),(keys.errors,torch.int32,(B,)),(keys.batch_error,torch.int32,(1,)),
          (keys.count,torch.int64,(1,)),(selected,torch.bool,(B,))):_tensor(value,state,dtype,shape)
    for value in (state.records,state.lengths,state.errors,state.context.string_bytes,state.context.string_offsets,
                  state.string_bytes,state.string_offsets,state.suffix_usage):
        if not value.is_contiguous() or value.device!=state.device:raise ValueError('Event state buffers must remain resident and contiguous')
    if state.context.string_bytes.dtype!=torch.uint8 or state.context.string_bytes.ndim!=1 or \
       state.context.string_offsets.dtype!=torch.int64 or state.context.string_offsets.shape!=(state.context.string_count+1,):
        raise ValueError('Event static string arena layout differs')
    batch_error=keys.batch_error|((keys.count!=B).to(torch.int32))
    alloc=lambda *shape:torch.empty(shape,dtype=torch.int64,device=state.device)
    errors,roots,begins,required_state,required_block=(alloc(B) for _ in range(5))
    if B:
        scratch=(alloc(B,max(R,1)),alloc(B,max(R,1)),alloc(B,max(R,1)*2))
        args=(state.records,state.lengths,state.errors,state.context.string_bytes,state.context.string_offsets,
              state.string_bytes,state.string_offsets,state.suffix_usage,payloads.records,payloads.lengths,payloads.errors,
              kinds,labels.ids,keys.hex_bytes,keys.errors,batch_error,selected,errors,roots,begins,required_state,required_block,
              *scratch,_dimensions((B,C,R,state.context.string_count,state.context.string_bytes.numel(),
                  state.string_offsets.numel()-1,state.string_bytes.numel(),state_capacity,block_capacity)))
        _kernels().validate_event_append(*(value if value.numel() else _dummy() for value in args),threads=B)
    healthy=~(errors!=0).any()&(batch_error==0).all()
    # Capacity errors do not hide the exact hash-pool requirement for retry.
    valid_content=selected&((errors&15)==0)
    interned=intern_bytes(state,keys.hex_bytes,torch.full((B,),64,dtype=torch.int64,device=state.device),valid_content,
        string_capacity=string_capacity,byte_capacity=byte_capacity)
    event_selected=valid_content&interned.accepted
    blocks=alloc(B,R+3,5);event_lengths=alloc(B)
    if B:_kernels().write_event_blocks(payloads.records,payloads.lengths,kinds,labels.ids,interned.ids,event_selected,
        blocks,event_lengths,_dimensions((B,R)),threads=B)
    build=build_sequence_splices(interned.state,roots,begins,torch.zeros_like(begins),blocks,event_lengths,
        torch.ones_like(begins),event_selected,capacity=block_capacity)
    edited=commit_container_edits(build,capacity=state_capacity)
    committed=healthy&interned.committed&edited.committed
    # Both independent COW arenas roll back under the same final device flag.
    old_records=torch.cat((state.records,torch.zeros((B,state_capacity-C,5),dtype=torch.int64,device=state.device)),dim=1) if state_capacity>C else state.records
    old_bytes=torch.cat((state.string_bytes,torch.zeros(interned.state.string_bytes.numel()-state.string_bytes.numel(),dtype=torch.uint8,device=state.device)))
    old_offsets=torch.cat((state.string_offsets,torch.zeros(interned.state.string_offsets.numel()-state.string_offsets.numel(),dtype=torch.int64,device=state.device)))
    output=DeviceStateBatch(state.context,torch.where(committed,edited.state.records,old_records),
        torch.where(committed,edited.state.lengths,state.lengths),torch.where(committed,edited.state.sections,state.sections),
        torch.where(committed,interned.state.string_bytes,old_bytes),torch.where(committed,interned.state.string_offsets,old_offsets),
        state.errors,torch.where(committed,interned.state.suffix_usage,state.suffix_usage))
    all_errors=errors|(interned.errors<<8)|(build.errors<<16)|(edited.edit_errors<<24)
    all_errors|=(selected&(interned.pool_error!=0)).to(torch.int64)<<14
    return EventAppendResult(output,replace(identities,source=output),all_errors,selected&committed,committed,
        required_state,required_block,interned.required_usage,batch_error)
