"""Exact copy-on-write byte interning in resident campaign string arenas.

Actual suffix usage stays on device; allocated shapes are capacities only. No
normalization, replacement characters, hash collisions or silent truncation are
allowed. Optional UTF8 validation is an explicit additional constraint on new
requests, not a restriction on the native byte-string transport domain.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntFlag
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch


class InternError(IntFlag):
    SOURCE = 1
    LENGTH = 2
    UTF8 = 4
    CAPACITY = 8


@dataclass(frozen=True)
class DeviceInternResult:
    state: DeviceStateBatch
    ids: torch.Tensor
    errors: torch.Tensor
    pool_error: torch.Tensor
    required_usage: torch.Tensor
    accepted: torch.Tensor
    committed: torch.Tensor


SOURCE = r"""
#include <metal_stdlib>
using namespace metal;
inline bool intern_equal(device const uchar* a,long start,device const uchar* b,long other,long length){
 for(long i=0;i<length;++i)if(a[start+i]!=b[other+i])return false;return true;
}
inline bool intern_utf8(device const uchar* bytes,long start,long length){
 long i=0;
 while(i<length){uint first=bytes[start+i++];if(first<128)continue;
   long count=0;uint low=128,high=191;
   if(first>=194&&first<=223)count=1;
   else if(first>=224&&first<=239){count=2;if(first==224)low=160;if(first==237)high=159;}
   else if(first>=240&&first<=244){count=3;if(first==240)low=144;if(first==244)high=143;}
   else return false;
   if(count>length-i)return false;
   uint second=bytes[start+i++];if(second<low||second>high)return false;
   for(long j=1;j<count;++j){uint next=bytes[start+i++];if(next<128||next>191)return false;}
 }
 return true;
}
kernel void validate_intern_pool(device const long* usage[[buffer(0)]],device const long* offsets[[buffer(1)]],
 device const long* prefix_offsets[[buffer(2)]],device long* error[[buffer(3)]],device const long* dims[[buffer(4)]],
 uint index[[thread_position_in_grid]]){
 if(index)return;long count=usage[0],bytes=usage[1];bool valid=count>=0&&count<=dims[2]&&bytes>=0&&bytes<=dims[3];
 if(valid){valid=offsets[0]==0&&offsets[count]==bytes;
   for(long i=0;valid&&i<count;++i)valid=offsets[i]>=0&&offsets[i]<=offsets[i+1]&&offsets[i+1]<=bytes;
 }
 valid=valid&&prefix_offsets[0]==0&&prefix_offsets[dims[4]]==dims[5];error[0]=valid?0:1;
}
kernel void match_intern_requests(device const uchar* requests[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const bool* selected[[buffer(2)]],device const uchar* prefix_bytes[[buffer(3)]],
 device const long* prefix_offsets[[buffer(4)]],device const uchar* old_bytes[[buffer(5)]],
 device const long* old_offsets[[buffer(6)]],device const long* usage[[buffer(7)]],device const long* pool_error[[buffer(8)]],
 device long* existing[[buffer(9)]],device long* representatives[[buffer(10)]],device long* errors[[buffer(11)]],
 device const long* dims[[buffer(12)]],uint thread_index[[thread_position_in_grid]]){
 long q=long(thread_index),Q=dims[0],L=dims[1];if(q>=Q)return;
 existing[q]=-1;representatives[q]=-1;errors[q]=0;if(!selected[q])return;
 if(pool_error[0]){errors[q]=1;return;}
 long size=lengths[q],start=q*L;
 if(size<0||size>L){errors[q]=2;return;}
 if(dims[6]&&!intern_utf8(requests,start,size)){errors[q]=4;return;}
 for(long id=0;id<dims[4];++id){long a=prefix_offsets[id],b=prefix_offsets[id+1];
   if(a<0||b<a||b>dims[5]){errors[q]=1;return;}
   if(b-a==size&&intern_equal(prefix_bytes,a,requests,start,size)){existing[q]=id;return;}
 }
 for(long id=0;id<usage[0];++id){long a=old_offsets[id],b=old_offsets[id+1];
   if(b-a==size&&intern_equal(old_bytes,a,requests,start,size)){existing[q]=dims[4]+id;return;}
 }
 for(long prior=0;prior<q;++prior)if(selected[prior]&&lengths[prior]==size&&
   intern_equal(requests,prior*L,requests,start,size)){representatives[q]=prior;return;}
 representatives[q]=q;
}
kernel void rank_intern_requests(device const long* lengths[[buffer(0)]],device const bool* selected[[buffer(1)]],
 device const long* existing[[buffer(2)]],device const long* representatives[[buffer(3)]],device long* errors[[buffer(4)]],
 device const long* old_usage[[buffer(5)]],device const long* pool_error[[buffer(6)]],device long* ranks[[buffer(7)]],
 device long* byte_ranks[[buffer(8)]],device long* required[[buffer(9)]],device bool* committed[[buffer(10)]],
 device const long* dims[[buffer(11)]],uint thread_index[[thread_position_in_grid]]){
 if(thread_index)return;long count=0,bytes=0;bool valid=pool_error[0]==0;
 for(long q=0;q<dims[0];++q){
   if(selected[q]&&errors[q])valid=false;
   if(selected[q]&&!errors[q]&&existing[q]<0&&representatives[q]==q){
     if(lengths[q]>0x7fffffffffffffffL-bytes){errors[q]|=2;valid=false;}
     else {++count;bytes+=lengths[q];}
   }
   ranks[q]=count;byte_ranks[q]=bytes;
 }
 long old_count=clamp(old_usage[0],0L,dims[2]),old_bytes=clamp(old_usage[1],0L,dims[3]);
 bool representable=count<=0x7fffffffffffffffL-old_count&&bytes<=0x7fffffffffffffffL-old_bytes;
 required[0]=representable?old_count+count:0x7fffffffffffffffL;
 required[1]=representable?old_bytes+bytes:0x7fffffffffffffffL;
 bool capacity=representable&&required[0]<=dims[7]&&required[1]<=dims[8];
 if(!capacity){valid=false;for(long q=0;q<dims[0];++q)if(selected[q])errors[q]|=8;}
 committed[0]=valid;
}
kernel void append_intern_requests(device const uchar* requests[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const bool* selected[[buffer(2)]],device const long* existing[[buffer(3)]],device const long* representatives[[buffer(4)]],
 device const long* ranks[[buffer(5)]],device const long* byte_ranks[[buffer(6)]],device const long* old_usage[[buffer(7)]],
 device const long* next_usage[[buffer(8)]],device const bool* committed[[buffer(9)]],device uchar* bytes[[buffer(10)]],
 device long* offsets[[buffer(11)]],device long* ids[[buffer(12)]],device const long* dims[[buffer(13)]],
 uint thread_index[[thread_position_in_grid]]){
 long q=long(thread_index),Q=dims[0],L=dims[1];if(q>=Q)return;ids[q]=-1;
 if(!committed[0]||!selected[q])return;
 if(existing[q]>=0){ids[q]=existing[q];return;}
 long representative=representatives[q];
 if(representative<0||representative>=Q)return;
 long relative=ranks[representative]-1;ids[q]=dims[4]+old_usage[0]+relative;
 if(representative!=q)return;
 long id=old_usage[0]+relative,size=lengths[q],start=old_usage[1]+byte_ranks[q]-size;
 offsets[id]=start;
 for(long i=0;i<size;++i)bytes[start+i]=requests[q*L+i];
 // Only the last unique request owns the final offset; no concurrent writes,
 // even when adjacent start/end values are mathematically identical.
 if(id+1==next_usage[0])offsets[id+1]=start+size;
}
"""
_library = None
_lock = threading.Lock()


@lru_cache(maxsize=64)
def _dimensions(values):
    return torch.tensor(values, dtype=torch.int64, device="mps")


@lru_cache(maxsize=1)
def _dummy():
    return torch.zeros(1, dtype=torch.int64, device="mps")


def pack_byte_requests(values, *, device="cpu"):
    """Explicit host ingress for external/literal requests, not a rules path."""
    values = tuple(values)
    if any(not isinstance(value, bytes) for value in values):
        raise TypeError("Byte requests require exact bytes; encode text explicitly")
    capacity = max(map(len, values), default=0)
    data = torch.zeros((len(values), capacity), dtype=torch.uint8)
    for index, value in enumerate(values):
        if value:
            data[index, :len(value)] = torch.tensor(list(value), dtype=torch.uint8)
    return data.to(device), torch.tensor(list(map(len, values)), dtype=torch.int64, device=device)


def _layout(state, requests, lengths, selected, string_capacity, byte_capacity):
    if not isinstance(state, DeviceStateBatch):
        raise TypeError("Expected complete resident state and shared string pool")
    state._metadata()
    if not isinstance(requests, torch.Tensor) or requests.ndim != 2 or requests.dtype != torch.uint8:
        raise ValueError("Requests must retain the complete [request,byte_capacity] byte buffer")
    Q = requests.shape[0]
    if Q > 2**32-1:
        raise OverflowError("Interning request grid is not representable; no requests truncated")
    for value, shape, dtype in ((requests, tuple(requests.shape), torch.uint8), (lengths, (Q,), torch.int64), (selected, (Q,), torch.bool)):
        if not isinstance(value, torch.Tensor) or value.device != state.device or value.dtype != dtype or tuple(value.shape) != shape or not value.is_contiguous():
            raise ValueError("Interning inputs must have complete contiguous resident shapes/dtypes")
    old_strings, old_bytes = state.string_offsets.numel()-1, state.string_bytes.numel()
    string_capacity = old_strings if string_capacity is None else string_capacity
    byte_capacity = old_bytes if byte_capacity is None else byte_capacity
    if (type(string_capacity) is not int or type(byte_capacity) is not int or
            string_capacity < old_strings or byte_capacity < old_bytes):
        raise ValueError("New capacities must preserve the complete original pool for rollback")
    for value in (state.string_offsets, state.string_bytes, state.suffix_usage, state.context.string_offsets, state.context.string_bytes):
        if not value.is_contiguous():
            raise ValueError("Interning requires contiguous pool buffers; no hidden conversion")
    return Q, requests.shape[1], old_strings, old_bytes, string_capacity, byte_capacity


def _cpu(state, requests, lengths, selected, strings_capacity, bytes_capacity, validate_utf8):
    usage = state.suffix_usage.tolist();used, byte_count = usage
    offsets, raw = state.string_offsets.tolist(), bytes(state.string_bytes.tolist())
    prefix_offsets, prefix_bytes = state.context.string_offsets.tolist(), bytes(state.context.string_bytes.tolist())
    source_valid = (0 <= used < len(offsets) and 0 <= byte_count <= len(raw) and offsets[0] == 0 and
                    offsets[used] == byte_count and all(0 <= a <= b <= byte_count for a,b in zip(offsets[:used], offsets[1:used+1])))
    source_valid = source_valid and prefix_offsets[0] == 0 and prefix_offsets[-1] == len(prefix_bytes)
    pool = [prefix_bytes[a:b] for a,b in zip(prefix_offsets,prefix_offsets[1:])]
    if source_valid: pool += [raw[a:b] for a,b in zip(offsets[:used], offsets[1:used+1])]
    table = {value:index for index,value in enumerate(pool)}
    candidate, ids, errors = [], [], []
    values, sizes, flags = requests.tolist(), lengths.tolist(), selected.tolist()
    for value,size,active in zip(values,sizes,flags):
        error, identity = 0, -1
        if active:
            if not source_valid: error = int(InternError.SOURCE)
            elif not 0 <= size <= len(value): error = int(InternError.LENGTH)
            else:
                text = bytes(value[:size])
                if validate_utf8:
                    try: text.decode("utf8")
                    except UnicodeDecodeError: error = int(InternError.UTF8)
                if not error:
                    if text not in table:
                        table[text] = len(pool) + len(candidate);candidate.append(text)
                    identity = table[text]
        ids.append(identity);errors.append(error)
    required = [used+len(candidate),byte_count+sum(map(len,candidate))] if source_valid else [max(0,min(used,len(offsets)-1)),max(0,min(byte_count,len(raw)))]
    capacity_ok = required[0] <= strings_capacity and required[1] <= bytes_capacity
    if not capacity_ok: errors = [value | (int(InternError.CAPACITY) if active else 0) for value,active in zip(errors,flags)]
    committed = source_valid and not any(errors) and capacity_ok
    new_bytes = list(raw)+[0]*(bytes_capacity-len(raw))
    new_offsets = offsets+[0]*(strings_capacity+1-len(offsets))
    if committed:
        cursor=byte_count
        for index,value in enumerate(candidate):
            new_offsets[used+index]=cursor;new_bytes[cursor:cursor+len(value)]=list(value);cursor+=len(value)
        new_offsets[required[0]]=cursor
    else: ids=[-1]*len(ids)
    return (torch.tensor(new_bytes,dtype=torch.uint8),torch.tensor(new_offsets,dtype=torch.int64),
        torch.tensor(required if committed else usage,dtype=torch.int64),torch.tensor(ids,dtype=torch.int64),
        torch.tensor(errors,dtype=torch.int64),torch.tensor(0 if source_valid else int(InternError.SOURCE),dtype=torch.int64),
        torch.tensor(required,dtype=torch.int64),torch.tensor(committed))


def _rank_probe(lengths):
    """Test the ACTUAL integer scan with wide lengths, without allocating bytes."""
    global _library
    if (not isinstance(lengths, torch.Tensor) or lengths.device.type != "mps" or
            lengths.dtype != torch.int64 or lengths.ndim != 1 or not lengths.is_contiguous()):
        raise ValueError("Rank probe requires a contiguous resident int64 vector")
    if _library is None:
        with _lock:
            if _library is None: _library=torch.mps.compile_shader(SOURCE)
    Q=lengths.shape[0]
    selected=torch.ones(Q,dtype=torch.bool,device=lengths.device)
    existing=torch.full((Q,),-1,dtype=torch.int64,device=lengths.device)
    representatives=torch.arange(Q,dtype=torch.int64,device=lengths.device)
    errors=torch.zeros_like(existing);usage=torch.zeros(2,dtype=torch.int64,device=lengths.device)
    pool_error=torch.zeros((),dtype=torch.int64,device=lengths.device)
    ranks=torch.empty_like(existing);byte_ranks=torch.empty_like(existing)
    required=torch.empty_like(usage);committed=torch.empty((),dtype=torch.bool,device=lengths.device)
    args=(lengths,selected,existing,representatives,errors,usage,pool_error,ranks,byte_ranks,required,committed,
          _dimensions((Q,0,0,0,0,0,0,2**63-1,2**63-1)))
    _library.rank_intern_requests(*(value if value.numel() else _dummy() for value in args),threads=1)
    return ranks,byte_ranks,required,errors,committed


def intern_bytes(state, requests, lengths, selected=None, *, string_capacity=None, byte_capacity=None, validate_utf8=False):
    """Intern complete resident byte requests with exact COW/cohort semantics.

    Retry bounds old_string_capacity+Q and old_byte_capacity+Q*Lcap use metadata
    alone. No device counter is read to choose tensor shapes or dispatch work.
    """
    if selected is None:
        selected = torch.ones(requests.shape[0], dtype=torch.bool, device=state.device)
    if type(validate_utf8) is not bool: raise ValueError("UTF8 validation must be an explicit bool")
    Q,L,S,H,O,P = _layout(state,requests,lengths,selected,string_capacity,byte_capacity)
    if state.device.type == "cpu":
        output,offsets,usage,ids,errors,pool_error,required,committed = _cpu(state,requests,lengths,selected,O,P,validate_utf8)
    elif state.device.type == "mps":
        global _library
        if _library is None:
            with _lock:
                if _library is None: _library=torch.mps.compile_shader(SOURCE)
        dims=_dimensions((Q,L,S,H,state.context.string_count,state.context.string_bytes.numel(),int(validate_utf8),O,P))
        pool_error=torch.zeros((),dtype=torch.int64,device=state.device)
        tensors=(state.suffix_usage,state.string_offsets,state.context.string_offsets,pool_error,dims)
        _library.validate_intern_pool(*(value if value.numel() else _dummy() for value in tensors),threads=1)
        existing=torch.full((Q,),-1,dtype=torch.int64,device=state.device)
        representatives=existing.clone();errors=torch.zeros_like(existing)
        if Q:
            tensors=(requests,lengths,selected,state.context.string_bytes,state.context.string_offsets,state.string_bytes,
                state.string_offsets,state.suffix_usage,pool_error,existing,representatives,errors,dims)
            _library.match_intern_requests(*(value if value.numel() else _dummy() for value in tensors),threads=Q)
        ranks=torch.empty((Q,),dtype=torch.int64,device=state.device)
        byte_ranks=torch.empty_like(ranks)
        required=torch.empty((2,),dtype=torch.int64,device=state.device)
        committed=torch.empty((),dtype=torch.bool,device=state.device)
        tensors=(lengths,selected,existing,representatives,errors,state.suffix_usage,pool_error,
                 ranks,byte_ranks,required,committed,dims)
        _library.rank_intern_requests(*(value if value.numel() else _dummy() for value in tensors),threads=1)
        baseline_bytes=torch.cat((state.string_bytes,torch.zeros(P-H,dtype=torch.uint8,device=state.device))) if P>H else state.string_bytes
        baseline_offsets=torch.cat((state.string_offsets,torch.zeros(O-S,dtype=torch.int64,device=state.device))) if O>S else state.string_offsets
        output,offsets=baseline_bytes.clone(),baseline_offsets.clone()
        ids=torch.full((Q,),-1,dtype=torch.int64,device=state.device)
        if Q:
            tensors=(requests,lengths,selected,existing,representatives,ranks,byte_ranks,state.suffix_usage,
                required,committed,output,offsets,ids,dims)
            _library.append_intern_requests(*(value if value.numel() else _dummy() for value in tensors),threads=Q)
        usage=torch.where(committed,required,state.suffix_usage)
    else:
        raise ValueError("Byte interning requires explicit CPU reference or Apple MPS; no fallback")
    result=replace(state,string_bytes=output,string_offsets=offsets,suffix_usage=usage)
    return DeviceInternResult(result,ids,errors,pool_error,required,selected&committed,committed)
