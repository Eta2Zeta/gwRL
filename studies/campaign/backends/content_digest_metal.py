"""Native-compatible SHA-256 identities over resident exact byte messages.

No canonicalization, encoding, normalization or game rule is performed here.
Callers retain complete bytes and actual message count; spare capacity is masked,
not treated as additional actions. Native action IDs use these same digest bytes.
"""
from dataclasses import dataclass
from functools import lru_cache
import os
import threading

import torch


@dataclass(frozen=True)
class MessageBatch:
    data: object             # uint8 [allocated bytes]
    offsets: object          # int64 [message capacity+1]
    count: object            # int64 [1], actual messages


@dataclass(frozen=True)
class RangedMessageBatch:
    data: object             # uint8 [allocated bytes], may contain padding/gaps
    ranges: object           # int64 [capacity,2], exact start/end for each message
    count: object


@dataclass(frozen=True)
class DigestBatch:
    words: object            # int32 [capacity,8], raw unsigned32 payload bits
    hex_bytes: object        # uint8 [capacity,64], native lowercase ASCII hex
    errors: object           # int32 [capacity]
    batch_error: object      # int32 [1], including malformed empty-count cases
    count: object


def pack_messages(messages, *, device='cpu'):
    """Explicit initial byte packing; resident menu builders bypass this path."""
    messages=tuple(messages)
    if any(type(value) is not bytes for value in messages):
        raise TypeError('Digest messages must be exact bytes; encoding is explicit')
    offsets=[0]
    for value in messages:offsets.append(offsets[-1]+len(value))
    return MessageBatch(torch.tensor(bytearray(b''.join(messages)),dtype=torch.uint8,device=device),
        torch.tensor(offsets,dtype=torch.int64,device=device),
        torch.tensor([len(messages)],dtype=torch.int64,device=device))


SOURCE=r"""
#include <metal_stdlib>
using namespace metal;
constant uint digest_k[64]={
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
constant char digest_hex[17]="0123456789abcdef";
inline uint digest_rotr(uint x,int n){return (x>>n)|(x<<(32-n));}

kernel void content_digests(device const uchar* data [[buffer(0)]],
    device const long* offsets [[buffer(1)]],device const long* count [[buffer(2)]],
    device uint* words [[buffer(3)]],device uchar* hex [[buffer(4)]],
    device int* errors [[buffer(5)]],device int* batch_error [[buffer(6)]],
    device const long* dimensions [[buffer(7)]],uint row [[thread_position_in_grid]]) {
    const long capacity=dimensions[0],bytes=dimensions[1],actual=count[0];
    const bool bad_count=actual<0||actual>capacity;
    if(row==0)batch_error[0]=bad_count?1:0;
    if(long(row)>=capacity)return;
    errors[row]=0;
    for(int i=0;i<8;++i)words[ulong(row)*8+ulong(i)]=0;
    for(int i=0;i<64;++i)hex[ulong(row)*64+ulong(i)]=0;
    if(bad_count){errors[row]=1;return;}
    if(long(row)>=actual)return;
    const bool ranged=dimensions[2]!=0;
    const long start=offsets[ranged?ulong(row)*2:ulong(row)],
               end=offsets[ranged?ulong(row)*2+1:ulong(row)+1];
    if(start<0||end<start||end>bytes){errors[row]=2;return;}
    const ulong length=ulong(end-start),bits=length*8;
    const ulong blocks=(length+9+63)/64,total=blocks*64;
    uint h[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    for(ulong block=0;block<blocks;++block){
        uint w[64];
        for(int i=0;i<16;++i){
            uint value=0;
            for(int j=0;j<4;++j){
                const ulong index=block*64+ulong(i*4+j);uint byte=0;
                if(index<length)byte=data[ulong(start)+index];
                else if(index==length)byte=0x80;
                else if(index>=total-8)byte=uint((bits>>(8*uint(total-1-index)))&255);
                value=(value<<8)|byte;
            }
            w[i]=value;
        }
        for(int i=16;i<64;++i){
            const uint a=digest_rotr(w[i-15],7)^digest_rotr(w[i-15],18)^(w[i-15]>>3);
            const uint b=digest_rotr(w[i-2],17)^digest_rotr(w[i-2],19)^(w[i-2]>>10);
            w[i]=w[i-16]+a+w[i-7]+b;
        }
        uint a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],z=h[7];
        for(int i=0;i<64;++i){
            const uint s1=digest_rotr(e,6)^digest_rotr(e,11)^digest_rotr(e,25);
            const uint t1=z+s1+((e&f)^((~e)&g))+digest_k[i]+w[i];
            const uint s0=digest_rotr(a,2)^digest_rotr(a,13)^digest_rotr(a,22);
            const uint t2=s0+((a&b)^(a&c)^(b&c));
            z=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
        }
        h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=z;
    }
    for(int i=0;i<8;++i){
        words[ulong(row)*8+ulong(i)]=h[i];
        for(int digit=0;digit<8;++digit)
            hex[ulong(row)*64+ulong(i*8+digit)]=uchar(digest_hex[(h[i]>>(28-4*digit))&15]);
    }
}
"""

_library=None
_unrolled_library=None
_lock=threading.Lock()


@lru_cache(maxsize=8)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device='mps')


@lru_cache(maxsize=1)
def _dummy():return torch.empty(1,dtype=torch.int64,device='mps')


def content_digests_metal(batch, *, implementation='reference', group_size=None):
    """Hash exact messages; alternate compression and group sizing are explicit.

    Each thread always hashes one complete message. ``group_size`` controls how
    those independent threads are scheduled, never the number of messages or
    bytes hashed. The unchanged reference implementation remains the default.
    """
    global _library, _unrolled_library
    if implementation not in {'reference','unrolled'}:
        raise ValueError('Digest implementation must be reference or unrolled')
    if group_size is not None and (type(group_size) is not int or group_size<=0):
        raise ValueError('Digest group size must be a positive integer')
    device=batch.data.device
    if device.type!='mps':raise ValueError('Digest execution requires the explicit Apple GPU')
    if os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK','0') not in {'','0'}:
        raise ValueError('MPS CPU fallback is forbidden')
    ranged=isinstance(batch,RangedMessageBatch)
    offsets=batch.ranges if ranged else batch.offsets
    layout=(offsets.ndim==2 and offsets.shape[1]==2) if ranged else (offsets.ndim==1 and offsets.numel()>=1)
    if (batch.data.dtype!=torch.uint8 or batch.data.ndim!=1 or offsets.dtype!=torch.int64 or
        not layout or batch.count.dtype!=torch.int64 or
        batch.count.shape!=(1,) or any(value.device!=device or not value.is_contiguous()
        for value in (batch.data,offsets,batch.count))):
        raise ValueError('Digest buffers must retain complete contiguous byte/offset/count layouts')
    B=offsets.shape[0] if ranged else offsets.shape[0]-1
    if B>(1<<32)-1:raise OverflowError('Digest grid exceeds representable capacity; no messages truncated')
    words=torch.empty((B,8),dtype=torch.int32,device=device)
    hex_bytes=torch.empty((B,64),dtype=torch.uint8,device=device)
    errors=torch.empty(B,dtype=torch.int32,device=device)
    batch_error=torch.empty(1,dtype=torch.int32,device=device)
    if implementation=='reference':
        if _library is None:
            with _lock:
                if _library is None:_library=torch.mps.compile_shader(SOURCE)
        kernel=_library.content_digests
    else:
        if _unrolled_library is None:
            with _lock:
                if _unrolled_library is None:
                    from .content_digest_unrolled import UNROLLED_SOURCE
                    _unrolled_library=torch.mps.compile_shader(UNROLLED_SOURCE)
        kernel=_unrolled_library.content_digests_unrolled
    if group_size is not None and group_size>kernel.max_threads_per_threadgroup:
        raise ValueError('Digest group size exceeds Metal kernel limit')
    args=(batch.data,offsets,batch.count,words,hex_bytes,errors,batch_error,
          _dimensions((B,batch.data.numel(),int(ranged))))
    arguments=tuple(value if value.numel() else _dummy() for value in args)
    if group_size is None:
        kernel(*arguments,threads=max(B,1))
    else:
        threads=((max(B,1)+group_size-1)//group_size)*group_size
        if threads>(1<<32)-1:
            raise OverflowError('Digest thread grid exceeds representable capacity; no messages truncated')
        kernel(*arguments,threads=threads,group_size=group_size)
    return DigestBatch(words,hex_bytes,errors,batch_error,batch.count)


def inspect_digests(result):
    """Explicit host result boundary; unusable messages never become IDs."""
    if result.batch_error.detach().cpu().tolist()!=[0]:raise ValueError('Invalid digest actual count')
    count=result.count.detach().cpu().tolist()[0]
    if any(result.errors[:count].detach().cpu().tolist()):raise ValueError('Invalid digest message offsets')
    return tuple(bytes(row).decode('ascii') for row in result.hex_bytes[:count].detach().cpu().tolist())
