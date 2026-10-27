"""Canonical native JSON bytes from resident generic JSON subtrees.

The immutable number-spelling context is prepared once at native ingress, not on
search steps. Exact newly generated int32 JSON numbers are recognized from their
IEEE bits and formatted without floats. Unseen noninteger numbers fail explicitly;
no CPU fallback or rounding is performed. This is not State.toJson yet.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch
from .metal_state_schema import METAL_STATE_SOURCE


class CanonicalJsonContext:
    def __init__(self,native_batch,state_context):
        import gwrl_cpp
        native=gwrl_cpp.campaign_canonical_number_context(native_batch)
        if native.wire_context_fingerprint!=state_context.wire_context_fingerprint:
            raise ValueError('Canonical JSON context belongs to another state definition')
        self.state_context=state_context
        self.words=torch.tensor(native.word_array(),dtype=torch.int64,device=state_context.device)
        self.offsets=torch.tensor(native.offset_array(),dtype=torch.int64,device=state_context.device)
        self.bytes=torch.tensor(native.byte_array(),dtype=torch.uint8,device=state_context.device)


@dataclass(frozen=True)
class CanonicalJsonBatch:
    data: object                 # uint8 [request capacity,byte capacity]
    lengths: object              # int64 actual bytes, zero when unusable
    required_bytes: object       # int64 exact requirement, including capacity failure
    errors: object               # int32: invalid1, capacity2, unknown number4, source8
    count: object                # int64 [1] actual requests
    batch_error: object          # int32 [1] invalid actual count


SOURCE=r'''
#include <metal_stdlib>
using namespace metal;
'''+METAL_STATE_SOURCE+r'''
constant char canonical_hex[17]="0123456789abcdef";
struct CanonicalWriter {
    PackedStateView view;
    device uchar* bytes;
    long capacity,position;
    int error;
    device const long* number_words;
    device const long* number_offsets;
    device const uchar* number_bytes;
    long number_count,number_byte_count;
};
inline void canonical_put(thread CanonicalWriter& w,uchar c) {
    if(w.position<w.capacity)w.bytes[w.position]=c;
    if(w.position==LONG_MAX){w.error|=1;return;}++w.position;
}
inline void canonical_literal(thread CanonicalWriter& w,constant char* text,long count) {
    for(long i=0;i<count;++i)canonical_put(w,uchar(text[i]));
}
inline bool canonical_span(thread CanonicalWriter& w,long id,thread long& start,thread long& finish,
                           thread bool& prefix) {
    bool valid=true;
    if(id<0||id>=w.view.prefix_count+w.view.suffix_count)valid=false;
    if(!valid){w.error|=1;return false;}
    prefix=id<w.view.prefix_count;const long local=prefix?id:id-w.view.prefix_count;
    device const long* offsets=prefix?w.view.prefix_offsets:w.view.suffix_offsets;
    start=offsets[local];finish=offsets[local+1];
    if(start<0||finish<start||finish>(prefix?w.view.prefix_bytes_length:w.view.suffix_bytes_length))valid=false;
    if(!valid)w.error|=1;return valid;
}
inline bool canonical_less(thread CanonicalWriter& w,long a,long b) {
    long x,y,u,v;bool p,q;if(!canonical_span(w,a,x,y,p)||!canonical_span(w,b,u,v,q))return false;
    device const uchar* ab=p?w.view.prefix_bytes:w.view.suffix_bytes;
    device const uchar* bb=q?w.view.prefix_bytes:w.view.suffix_bytes;
    for(long i=0;i<min(y-x,v-u);++i){if(ab[x+i]!=bb[u+i])return ab[x+i]<bb[u+i];}
    return y-x<v-u;
}
inline void canonical_string(thread CanonicalWriter& w,long id) {
    long start,finish;bool prefix;if(!canonical_span(w,id,start,finish,prefix))return;
    device const uchar* bytes=prefix?w.view.prefix_bytes:w.view.suffix_bytes;
    canonical_put(w,'"');
    for(long i=start;i<finish;++i){const uchar c=bytes[i];
        if(c=='"'||c=='\\'){canonical_put(w,'\\');canonical_put(w,c);}
        else if(c<32){canonical_literal(w,"\\u00",4);canonical_put(w,canonical_hex[c>>4]);canonical_put(w,canonical_hex[c&15]);}
        else canonical_put(w,c);
    }
    canonical_put(w,'"');
}
inline void canonical_integer(thread CanonicalWriter& w,long value) {
    // Native JSON integer fields are int32 and therefore exactly binary64.
    if(value<INT_MIN||value>INT_MAX){w.error|=1;return;}
    uint magnitude=value<0?uint(-value):uint(value);
    if(value<0)canonical_put(w,'-');
    char digits[10];int n=0;
    do{digits[n++]=char('0'+magnitude%10);magnitude/=10;}while(magnitude);
    while(n)canonical_put(w,uchar(digits[--n]));
}
inline bool canonical_number_integer(ulong bits,thread long& value) {
    return state_json_integer_value(bits,value);
}
inline void canonical_number(thread CanonicalWriter& w,ulong bits) {
    if(((bits>>52)&2047)==2047){w.error|=1;return;}
    long integer=0;if(canonical_number_integer(bits,integer)){canonical_integer(w,integer);return;}
    long low=0,high=w.number_count;
    while(low<high){const long mid=low+(high-low)/2;
        const ulong key=ulong(w.number_words[mid*2])|(ulong(w.number_words[mid*2+1])<<32);
        if(key<bits)low=mid+1;else high=mid;
    }
    if(low>=w.number_count){w.error|=4;return;}
    const ulong key=ulong(w.number_words[low*2])|(ulong(w.number_words[low*2+1])<<32);
    if(key!=bits){w.error|=4;return;}
    const long start=w.number_offsets[low],finish=w.number_offsets[low+1];
    if(start<0||finish<start||finish>w.number_byte_count){w.error|=1;return;}
    for(long i=start;i<finish;++i)canonical_put(w,w.number_bytes[i]);
}
// Stack storage scales to the complete source record capacity: no JSON depth
// is truncated. Each frame is end,expected children,seen,tag,previous key ID.
inline void canonical_json(thread CanonicalWriter& w,long root,device long* stack,long stack_capacity) {
    bool valid=true;const long finish=state_end(w.view,root,valid);
    if(!valid){w.error|=1;return;}
    long cursor=root,depth=0;
    while(!w.error){
        while(depth&&cursor==stack[(depth-1)*5]) {
            device long* f=stack+(depth-1)*5;
            if(f[1]!=f[2]){w.error|=1;return;}
            canonical_put(w,f[3]==13?'}':']');--depth;
        }
        if(cursor==finish){if(depth)w.error|=1;return;}
        if(cursor<root||cursor>finish||!state_node(w.view,cursor)){w.error|=1;return;}
        const long end=state_end(w.view,cursor,valid);
        if(!valid||end>finish||(depth&&end>stack[(depth-1)*5])){w.error|=1;return;}
        device const long* r=state_record(w.view,cursor);const long tag=r[0];
        if(depth){device long* parent=stack+(depth-1)*5;
            if(parent[2]>=parent[1]){w.error|=1;return;}
            if(parent[3]==13){
                if(!(parent[2]&1)){
                    if(tag!=5){w.error|=1;return;}
                    const long id=state_string_id(w.view,cursor,valid);
                    if(!valid||(parent[4]>=0&&!canonical_less(w,parent[4],id))){w.error|=1;return;}
                    if(parent[2])canonical_put(w,',');parent[4]=id;
                }else canonical_put(w,':');
            }else if(parent[2])canonical_put(w,',');
            ++parent[2];
        }
        if(tag==12||tag==13){
            const long maximum=tag==13?(end-cursor-1)/2:end-cursor-1;
            if(r[1]<0||r[1]>maximum||r[2]||r[3]||depth>=stack_capacity){w.error|=1;return;}
            canonical_put(w,tag==13?'{':'[');device long* f=stack+depth*5;
            f[0]=end;f[1]=r[1]*(tag==13?2:1);f[2]=0;f[3]=tag;f[4]=-1;
            ++depth;++cursor;continue;
        }
        if(end!=cursor+1){w.error|=1;return;}
        if(tag==0){if(r[1]||r[2]||r[3])w.error|=1;else canonical_literal(w,"null",4);}
        else if(tag==1){const bool value=state_boolean_value(w.view,cursor,valid);
            if(!valid)w.error|=1;else if(value)canonical_literal(w,"true",4);else canonical_literal(w,"false",5);}
        else if(tag==4){const ulong bits=state_raw_bits(w.view,cursor,4,valid);
            if(!valid)w.error|=1;else canonical_number(w,bits);}
        else if(tag==5){const long id=state_string_id(w.view,cursor,valid);
            if(!valid)w.error|=1;else canonical_string(w,id);}
        else w.error|=1;
        cursor=end;
    }
}

kernel void canonical_json_subtrees(
    device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],
    device const long* source_errors [[buffer(2)]],device const uchar* prefix_bytes [[buffer(3)]],
    device const long* prefix_offsets [[buffer(4)]],device const uchar* suffix_bytes [[buffer(5)]],
    device const long* suffix_offsets [[buffer(6)]],device const long* suffix_usage [[buffer(7)]],
    device const long* requests [[buffer(8)]],device const long* count [[buffer(9)]],
    device const long* number_words [[buffer(10)]],device const long* number_offsets [[buffer(11)]],
    device const uchar* number_bytes [[buffer(12)]],device uchar* output [[buffer(13)]],
    device long* output_lengths [[buffer(14)]],device long* required [[buffer(15)]],
    device int* errors [[buffer(16)]],device int* batch_error [[buffer(17)]],
    device long* stacks [[buffer(18)]],device const long* dimensions [[buffer(19)]],
    uint row [[thread_position_in_grid]]) {
    const long Q=dimensions[0],B=dimensions[1],K=dimensions[2],C=dimensions[3],actual=count[0];
    const bool bad_count=actual<0||actual>Q;
    if(row==0)batch_error[0]=bad_count?1:0;
    if(long(row)>=Q)return;
    output_lengths[row]=0;required[row]=0;errors[row]=0;
    if(bad_count){errors[row]=1;return;}if(long(row)>=actual)return;
    const long lane=requests[ulong(row)*2],root=requests[ulong(row)*2+1];
    if(lane<0||lane>=B){errors[row]=1;return;}
    if(source_errors[lane]){errors[row]=8;return;}
    bool valid=lengths[lane]>=0&&lengths[lane]<=K;
    const auto v=make_packed_state_view(records+ulong(lane)*ulong(K)*5,lengths[lane],K,
        prefix_bytes,prefix_offsets,dimensions[4],dimensions[5],suffix_bytes,suffix_offsets,
        dimensions[6],dimensions[7],suffix_usage,valid);
    if(!valid){errors[row]=1;return;}
    CanonicalWriter w{v,output+ulong(row)*ulong(C),C,0,0,number_words,number_offsets,number_bytes,
        dimensions[8],dimensions[9]};
    canonical_json(w,root,stacks+ulong(row)*ulong(K)*5,K);
    required[row]=w.position;errors[row]=w.error|(w.position>C?2:0);
    if(!errors[row])output_lengths[row]=w.position;
}
'''

_library=None
_lock=threading.Lock()

@lru_cache(maxsize=16)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device='mps')

@lru_cache(maxsize=1)
def _dummy():return torch.empty(1,dtype=torch.int64,device='mps')


def canonical_json_subtrees(state,requests,context,*,byte_capacity,count=None):
    """Write complete native canonical JSON with no host state reads or parsing."""
    global _library
    buffers=(state.records,state.lengths,state.sections,state.errors,state.string_bytes,
             state.string_offsets,state.suffix_usage,state.context.string_bytes,state.context.string_offsets)
    if any(isinstance(value,torch.Tensor) and not value.is_contiguous() for value in buffers):
        raise ValueError('Canonical state buffers must retain contiguous native layouts')
    state._metadata()
    if state.device.type!='mps':raise ValueError('Canonical execution requires the explicit Apple GPU')
    if any(value.device!=state.device for value in buffers):
        raise ValueError('Canonical state buffers must reside on the same explicit device')
    if state.context.string_bytes.dtype!=torch.uint8 or state.context.string_bytes.ndim!=1 or \
        state.context.string_offsets.dtype!=torch.int64 or state.context.string_offsets.shape!=(state.context.string_count+1,):
        raise ValueError('Canonical static string arena has an invalid layout')
    if state.context is not context.state_context:
        raise ValueError('Canonical JSON context must match the exact resident state context')
    if type(byte_capacity) is not int or byte_capacity<0:
        raise ValueError('Canonical byte capacity must be a nonnegative integer')
    if (requests.dtype!=torch.int64 or requests.ndim!=2 or requests.shape[1]!=2 or
        requests.device!=state.device or not requests.is_contiguous()):
        raise ValueError('Canonical requests must be contiguous int64 [capacity,2] lane/root indices')
    Q=requests.shape[0];B,K=state.records.shape[:2]
    if count is None:count=torch.full((1,),Q,dtype=torch.int64,device=state.device)
    if count.dtype!=torch.int64 or count.shape!=(1,) or count.device!=state.device or not count.is_contiguous():
        raise ValueError('Canonical actual count must be contiguous resident int64[1]')
    if Q>(1<<32)-1 or Q*max(K,byte_capacity,1)*5>(1<<63)-1:
        raise OverflowError('Canonical allocation exceeds representable capacity; no messages truncated')
    for value in (context.words,context.offsets,context.bytes):
        if value.device!=state.device or not value.is_contiguous():raise ValueError('Canonical number arena must remain resident and contiguous')
    if context.words.dtype!=torch.int64 or context.words.ndim!=2 or context.words.shape[1]!=2 or \
        context.offsets.dtype!=torch.int64 or context.offsets.shape!=(context.words.shape[0]+1,) or \
        context.bytes.dtype!=torch.uint8 or context.bytes.ndim!=1:
        raise ValueError('Canonical number arena has an invalid layout')
    data=torch.zeros((Q,byte_capacity),dtype=torch.uint8,device=state.device)
    lengths=torch.empty(Q,dtype=torch.int64,device=state.device);required=torch.empty_like(lengths)
    errors=torch.empty(Q,dtype=torch.int32,device=state.device);batch_error=torch.empty(1,dtype=torch.int32,device=state.device)
    stack=torch.empty((Q,K,5),dtype=torch.int64,device=state.device)
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    dims=_dimensions((Q,B,K,byte_capacity,state.context.string_count,state.context.string_bytes.numel(),
        state.string_offsets.numel()-1,state.string_bytes.numel(),context.words.shape[0],context.bytes.numel()))
    args=(state.records,state.lengths,state.errors,state.context.string_bytes,state.context.string_offsets,
          state.string_bytes,state.string_offsets,state.suffix_usage,requests,count,context.words,context.offsets,
          context.bytes,data,lengths,required,errors,batch_error,stack,dims)
    _library.canonical_json_subtrees(*(value if value.numel() else _dummy() for value in args),threads=max(Q,1))
    return CanonicalJsonBatch(data,lengths,required,errors,count,batch_error)


def inspect_canonical_json(result):
    """Explicit diagnostic/export boundary; invalid bytes cannot become IDs."""
    if result.batch_error.detach().cpu().tolist()!=[0]:raise ValueError('Invalid canonical actual count')
    count=result.count.detach().cpu().tolist()[0]
    errors=result.errors[:count].detach().cpu().tolist()
    if any(errors):raise ValueError(f'Canonical serialization failed: {errors}')
    lengths=result.lengths[:count].detach().cpu().tolist()
    data=result.data[:count].detach().cpu().tolist()
    return tuple(bytes(row[:length]) for row,length in zip(data,lengths,strict=True))


def canonical_json_digests(result,*,implementation='reference',group_size=None):
    """Hash exact written ranges; serialization errors propagate to identities."""
    from dataclasses import replace
    from .content_digest_metal import RangedMessageBatch,content_digests_metal
    Q,C=result.data.shape
    starts=torch.arange(Q,dtype=torch.int64,device=result.data.device)*C
    ranges=torch.stack((starts,starts+result.lengths),dim=1)
    hashed=content_digests_metal(RangedMessageBatch(result.data.flatten(),ranges,result.count),
                               implementation=implementation,group_size=group_size)
    return replace(hashed,errors=hashed.errors|result.errors,
                   batch_error=hashed.batch_error|result.batch_error)
