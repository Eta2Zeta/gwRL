"""Exact current native action-ID families and scheduler wrappers on MPS.

Explicit construction families avoid guessing a factory from its kind. Input
fields are exact resident byte ranges; hashing reuses canonical parameter SHA256
without downloading strings or serializing on the host. This primitive does not
generate legal menus, infer actors, assign decisions or establish legal actions.
"""
from dataclasses import dataclass
from enum import IntEnum
from functools import lru_cache
import threading

import torch

from .device_state import _device
from .metal_state_schema import METAL_STATE_SOURCE


class ActionIdFamily(IntEnum):
    END_PHASE=0
    POLITICAL=1
    MOVEMENT_ROUTE=2
    FACTORY_RAIL=3
    KIND_UNDERSCORE20=4  # Land combat and naval movement.
    KIND_COLON64=5       # Economy, lend-lease, air, naval combat.
    KIND_UNDERSCORE64=6  # Naval operations.
    AIR_DECISION=7       # decisionID:kind:SHA64 (the only native decision prefix).
    RAIL_PERMISSION=8
    SCHEDULED_PLAY=9
    SCHEDULED_INTERRUPT=10
    SCHEDULED_PASS=11


@dataclass(frozen=True)
class ActionIdStrings:
    data: object            # uint8 [storage capacity], exact raw byte strings.
    ranges: object          # int64 [Q,4,2]: kind/rawID,nation/actor,secondary,decision.
    # [-1,-1] is absent, [start,start] is a present empty string.


@dataclass(frozen=True)
class ActionIdBatch:
    data: object            # uint8 [Q,byte capacity], raw IDs, never JSON quoted.
    lengths: object
    required_bytes: object
    errors: object          # int32: descriptor1,capacity2,digest4,source8.
    count: object           # int64[1], actual ordered rows, not capacity.
    batch_error: object


SOURCE=r'''
#include <metal_stdlib>
using namespace metal;
'''+METAL_STATE_SOURCE+r'''
struct ActionIdWriter {device uchar* output;long capacity,position;int error;};
inline void aid_byte(thread ActionIdWriter& w,uchar value){
    if(w.position<w.capacity)w.output[w.position]=value;
    if(w.position==LONG_MAX)w.error|=1;else ++w.position;
}
inline void aid_literal(thread ActionIdWriter& w,constant char* value,long length){for(long i=0;i<length;++i)aid_byte(w,uchar(value[i]));}
inline bool aid_span(device const long* ranges,long field,long bytes,thread long& start,thread long& finish){
    start=ranges[field*2];finish=ranges[field*2+1];return start>=0&&finish>=start&&finish<=bytes;
}
inline void aid_field(thread ActionIdWriter& w,device const uchar* bytes,device const long* ranges,long field,long capacity){
    long start,finish;if(!aid_span(ranges,field,capacity,start,finish)){w.error|=1;return;}
    for(long i=start;i<finish;++i)aid_byte(w,bytes[i]);
}
kernel void resident_action_ids(
    device const uchar* strings [[buffer(0)]],device const long* ranges [[buffer(1)]],
    device const long* families [[buffer(2)]],device const uchar* parameter_hex [[buffer(3)]],
    device const int* parameter_errors [[buffer(4)]],device const int* parameter_batch_error [[buffer(5)]],
    device const long* parameter_count [[buffer(6)]],device const long* count [[buffer(7)]],
    device uchar* output [[buffer(8)]],device long* lengths [[buffer(9)]],device long* required [[buffer(10)]],
    device int* errors [[buffer(11)]],device int* batch_error [[buffer(12)]],
    device const long* dimensions [[buffer(13)]],uint row [[thread_position_in_grid]]) {
    const long Q=dimensions[0],S=dimensions[1],C=dimensions[2],actual=count[0];
    const int bad=(actual<0||actual>Q||parameter_count[0]!=actual)?1:0;
    if(row==0)batch_error[0]=bad|parameter_batch_error[0];if(long(row)>=Q)return;
    lengths[row]=required[row]=0;errors[row]=0;
    if(bad||parameter_batch_error[0]){errors[row]=8;return;}if(long(row)>=actual)return;
    const long family=families[row];if(family<0||family>11){errors[row]=1;return;}
    const bool hashed=family>=1&&family<=7;
    if(hashed){if(parameter_errors[row]){errors[row]=4;return;}
        for(long i=0;i<64;++i){const uchar c=parameter_hex[ulong(row)*64+ulong(i)];
            if(!((c>='0'&&c<='9')||(c>='a'&&c<='f'))){errors[row]=4;return;}}}
    ActionIdWriter w{output+ulong(row)*ulong(C),C,0,0};device const long* fields=ranges+ulong(row)*8;
    switch(family){
      case 0:aid_literal(w,"end_phase",9);break;
      case 1:aid_field(w,strings,fields,0,S);aid_byte(w,'_');aid_field(w,strings,fields,1,S);aid_byte(w,'_');break;
      case 2:aid_literal(w,"move_",5);break;
      case 3:aid_literal(w,"factory_rail_",13);break;
      case 4:case 6:aid_field(w,strings,fields,0,S);aid_byte(w,'_');break;
      case 5:aid_field(w,strings,fields,0,S);aid_byte(w,':');break;
      case 7:aid_field(w,strings,fields,3,S);aid_byte(w,':');aid_field(w,strings,fields,0,S);aid_byte(w,':');break;
      case 8:aid_literal(w,"rail_permission_",16);aid_field(w,strings,fields,1,S);aid_byte(w,'_');aid_field(w,strings,fields,2,S);break;
      case 9:aid_literal(w,"campaign-interrupt-scheduler-v1:play:",37);aid_field(w,strings,fields,0,S);break;
      case 10:aid_literal(w,"campaign-interrupt-scheduler-v1:interrupt:",42);aid_field(w,strings,fields,0,S);break;
      case 11:aid_literal(w,"campaign-interrupt-scheduler-v1:pass:",37);aid_field(w,strings,fields,1,S);break;
    }
    if(hashed){const long take=family==1?16:family==4?20:64;
        for(long i=0;i<take;++i)aid_byte(w,parameter_hex[ulong(row)*64+ulong(i)]);}
    if(w.error){errors[row]=w.error;return;}required[row]=w.position;
    if(w.position>C){errors[row]=2;return;}lengths[row]=w.position;
}
kernel void action_id_string_ranges(
    device const long* ids [[buffer(0)]],device const long* prefix_offsets [[buffer(1)]],
    device const long* suffix_offsets [[buffer(2)]],device const long* usage [[buffer(3)]],
    device long* output [[buffer(4)]],device const long* dimensions [[buffer(5)]],
    uint row [[thread_position_in_grid]]) {
    const long Q=dimensions[0],P=dimensions[1],PB=dimensions[2],S=dimensions[3],SB=dimensions[4];
    if(long(row)>=Q*4)return;const long id=ids[row];output[ulong(row)*2]=output[ulong(row)*2+1]=-2;
    if(id==-1){output[ulong(row)*2]=output[ulong(row)*2+1]=-1;return;}
    const long used=usage[0],bytes=usage[1];
    if(used<0||used>S||bytes<0||bytes>SB||prefix_offsets[0]!=0||prefix_offsets[P]!=PB||
       suffix_offsets[0]!=0||suffix_offsets[used]!=bytes||id<0||id>=P+used)return;
    const bool prefix=id<P;const long local=prefix?id:id-P;
    device const long* offsets=prefix?prefix_offsets:suffix_offsets;
    const long start=offsets[local],finish=offsets[local+1],capacity=prefix?PB:bytes;
    if(start<0||finish<start||finish>capacity)return;
    output[ulong(row)*2]=start+(prefix?0:PB);output[ulong(row)*2+1]=finish+(prefix?0:PB);
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
def _dummy():return torch.empty(1,dtype=torch.int64,device='mps')


def action_id_strings(state,string_ids):
    """Resolve resident interned IDs into raw byte ranges, without string copies.

    Exactly one concatenation retains the immutable shared prefix/suffix arena.
    Invalid used IDs become invalid descriptors; unused fields remain lazy.
    """
    state._metadata();_device(state.device)
    if state.device.type!='mps':raise ValueError('Action ID strings require explicit Apple GPU execution')
    if string_ids.dtype!=torch.int64 or string_ids.ndim!=2 or string_ids.shape[1]!=4 or \
       string_ids.device!=state.device or not string_ids.is_contiguous():
        raise ValueError('Action ID string IDs must be resident contiguous int64[capacity,4]')
    for value in (state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage):
        if not value.is_contiguous() or value.device!=state.device:raise ValueError('Action ID string arena layout differs')
    if state.context.string_bytes.dtype!=torch.uint8 or state.context.string_bytes.ndim!=1 or \
       state.context.string_offsets.dtype!=torch.int64 or state.context.string_offsets.shape!=(state.context.string_count+1,):
        raise ValueError('Action ID static string arena layout differs')
    Q=string_ids.shape[0]
    if Q*4>(1<<32)-1:raise OverflowError('Action ID descriptor capacity cannot be represented')
    data=torch.cat((state.context.string_bytes,state.string_bytes))
    ranges=torch.empty((Q,4,2),dtype=torch.int64,device=state.device)
    if Q:_kernels().action_id_string_ranges(string_ids,state.context.string_offsets,state.string_offsets,state.suffix_usage,
        ranges,_dimensions((Q,state.context.string_count,state.context.string_bytes.numel(),state.string_offsets.numel()-1,state.string_bytes.numel())),threads=Q*4)
    return ActionIdStrings(data,ranges)


def construct_action_ids(families,strings,parameter_digests,*,byte_capacity,count=None):
    """Build ordered IDs using exact SHA256 bytes and raw resident descriptors.

    Every parameter-dependent family uses the original 16/20/64 hex characters;
    truncation is never applied elsewhere. Literal families do not inspect an
    irrelevant per-row parameter error. Invalid batch counts remain fatal.
    """
    device=_device(families.device)
    if device.type!='mps':raise ValueError('Action IDs require explicit Apple GPU execution')
    if families.dtype!=torch.int64 or families.ndim!=1 or not families.is_contiguous():
        raise ValueError('Action ID families must be contiguous resident int64[capacity]')
    Q=families.shape[0]
    if type(byte_capacity) is not int or byte_capacity<0:raise ValueError('Action ID byte capacity must be a nonnegative integer')
    C=byte_capacity
    if Q>(1<<32)-1 or Q*max(C,1)>(1<<63)-1:raise OverflowError('Action ID output allocation cannot be represented')
    if count is None:count=parameter_digests.count
    values=((strings.data,torch.uint8,None),(strings.ranges,torch.int64,(Q,4,2)),
            (parameter_digests.hex_bytes,torch.uint8,(Q,64)),(parameter_digests.errors,torch.int32,(Q,)),
            (parameter_digests.batch_error,torch.int32,(1,)),(parameter_digests.count,torch.int64,(1,)),
            (count,torch.int64,(1,)))
    for value,dtype,shape in values:
        if not isinstance(value,torch.Tensor) or value.dtype!=dtype or value.device!=device or not value.is_contiguous() or \
           (shape is not None and value.shape!=shape):raise ValueError('Action ID source shape/device/layout differs')
    if strings.data.ndim!=1:raise ValueError('Action ID strings must be a flat resident byte arena')
    data=torch.zeros((Q,C),dtype=torch.uint8,device=device)
    lengths=torch.empty(Q,dtype=torch.int64,device=device);required=torch.empty_like(lengths)
    errors=torch.empty(Q,dtype=torch.int32,device=device);batch_error=torch.empty(1,dtype=torch.int32,device=device)
    args=(strings.data,strings.ranges,families,parameter_digests.hex_bytes,parameter_digests.errors,
          parameter_digests.batch_error,parameter_digests.count,count,data,lengths,required,errors,batch_error,
          _dimensions((Q,strings.data.numel(),C)))
    _kernels().resident_action_ids(*(value if value.numel() else _dummy() for value in args),threads=max(Q,1))
    return ActionIdBatch(data,lengths,required,errors,count,batch_error)


def inspect_action_ids(result):
    """Explicit diagnostic/export boundary; arbitrary native bytes stay bytes."""
    if result.batch_error.cpu().tolist()!=[0]:raise ValueError('Invalid action ID batch count/source')
    count=result.count.cpu().tolist()[0];errors=result.errors[:count].cpu().tolist()
    if any(errors):raise ValueError('Action ID construction failed: '+str(errors))
    lengths=result.lengths[:count].cpu().tolist();data=result.data[:count].cpu().tolist()
    return tuple(bytes(row[:length]) for row,length in zip(data,lengths,strict=True))
