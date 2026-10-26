"""Read and sample pending chance directly from complete resident state.

The source remains immutable. Returned faces/next RNG are an uncommitted
transaction: the appropriate combat/political handler must commit both together.
Capacities are allocation sizes, not dice/reroll limits; capacity errors retain
required sizes and consume no randomness. No state/JSON/face data crosses to CPU.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import SECTION_NAMES
from .metal_state_schema import METAL_STATE_SOURCE
from .random_metal import SOURCE as RANDOM_SOURCE

INVALID_STATE, NO_CHANCE, CAPACITY = 1, 128, 256


@dataclass(frozen=True)
class PackedChanceResult:
    source: object
    faces: object
    face_counts: object
    effective: object
    dice_counts: object
    next_streams: object
    next_tape_positions: object
    errors: object
    required: object


_SAMPLER = r"""
kernel void sample_packed_chance(
    device const long* records [[buffer(0)]], device const long* lengths [[buffer(1)]],
    device const long* sections [[buffer(2)]], device const uchar* prefix_bytes [[buffer(3)]],
    device const long* prefix_offsets [[buffer(4)]], device const uchar* suffix_bytes [[buffer(5)]],
    device const long* suffix_offsets [[buffer(6)]], device const long* source_errors [[buffer(7)]],
    device int* faces [[buffer(8)]], device int* counts [[buffer(9)]],
    device int* effective [[buffer(10)]], device long* dice_counts [[buffer(11)]],
    device ulong* next_streams [[buffer(12)]], device ulong* next_positions [[buffer(13)]],
    device int* errors [[buffer(14)]], device long* required [[buffer(15)]],
    device const long* dimensions [[buffer(16)]], uint lane [[thread_position_in_grid]]) {
    const long B=dimensions[0], C=dimensions[1], S=dimensions[2], D=dimensions[3], R=dimensions[4];
    if (long(lane)>=B) return;
    PackedStateView v={records+ulong(lane)*ulong(C)*5,lengths[lane],C,
        prefix_bytes,prefix_offsets,dimensions[5],dimensions[7],
        suffix_bytes,suffix_offsets,dimensions[6],dimensions[8]};
    for (long die=0;die<D;++die) {
        const ulong i=ulong(lane)*ulong(D)+ulong(die);counts[i]=0;effective[i]=0;
        for(long roll=0;roll<R;++roll)faces[i*ulong(R)+ulong(roll)]=0;
    }
    dice_counts[lane]=0;required[ulong(lane)*2]=0;required[ulong(lane)*2+1]=0;
    next_positions[lane]=0;
    for(int s=0;s<3;++s)next_streams[ulong(lane)*3+ulong(s)]=0;
    bool valid=source_errors[lane]==0 && v.length>0 && v.length<=C;
    const ulong base=ulong(lane)*ulong(S);
    ulong original[3]={0,0,0};
    if(valid)for(int s=0;s<3;++s)
        original[s]=state_unsigned_value(v,sections[base+ulong($ACTUAL+s)],valid);
    int selected=-1;
    if(valid) {
        const long active=sections[base+$ACTIVE];
        if(state_string_equals(v,active,"actual",6,valid))selected=0;
        else if(valid&&state_string_equals(v,active,"search",6,valid))selected=1;
        else if(valid&&state_string_equals(v,active,"training",8,valid))selected=2;
        if(selected<0)valid=false;
    }
    ulong old_position=0;long tape=-1,tape_count=0;
    if(valid) {
        old_position=state_unsigned_value(v,sections[base+$POSITION],valid);
        tape=sections[base+$TAPE];
        if(!state_node(v,tape))valid=false;
        else {
            device const long* row=state_record(v,tape);tape_count=row[1];
            if(row[0]!=6 || tape_count<0 || tape_count>C-tape-1 || row[4]!=tape+1+tape_count || old_position>ulong(tape_count))valid=false;
            if(valid)for(long i=0;i<tape_count;++i)if(state_signed_value(v,tape+1+i,valid)<=0)valid=false;
        }
    }
    int error=valid?0:1;
    long dice=-1,die_count=0,roll_need=0;
    if(valid) {
        bool exists=false;
        const long chance=state_optional(v,sections[base+$CHANCE],exists,valid);
        if(valid&&!exists)error|=128;
        if(valid&&exists) {
            if(state_record(v,chance)[0]!=10 || state_record(v,chance)[1]!=5)valid=false;
            if(valid)dice=state_child(v,chance,4,valid);
            if(valid) {
                device const long* row=state_record(v,dice);die_count=row[1];
                if(row[0]!=6||die_count<=0||die_count>(state_end(v,dice,valid)-dice-1)/5)valid=false;
            }
        }
    }
    long cursor=dice+1;
    if(valid&&!error)for(long die=0;die<die_count;++die) {
        if(!state_node(v,cursor)||state_record(v,cursor)[0]!=10||state_record(v,cursor)[1]!=4){valid=false;break;}
        const long side=state_signed_value(v,state_child(v,cursor,0,valid),valid);
        const long modifier=state_signed_value(v,state_child(v,cursor,1,valid),valid);
        const long set=state_child(v,cursor,2,valid);
        const long maximum=state_signed_value(v,state_child(v,cursor,3,valid),valid);
        if(!valid)break;
        device const long* setrow=state_record(v,set);const long entries=setrow[1];
        if(side<2||side>2147483647L||modifier<(-2147483647L-1)||modifier>2147483647L||maximum<0||maximum>2147483647L||
           setrow[0]!=8||entries<0||entries>C-set-1||setrow[4]!=set+1+entries){valid=false;break;}
        long previous=0;
        for(long entry=0;entry<entries;++entry) {
            const long face=state_signed_value(v,set+1+entry,valid);
            if(face<=previous||face>side)valid=false;previous=face;
        }
        roll_need=max(roll_need,maximum+1);cursor=state_end(v,cursor,valid);
    }
    if(valid&&!error&&cursor!=state_end(v,dice,valid))valid=false;
    if(!valid)error|=1;
    dice_counts[lane]=die_count;required[ulong(lane)*2]=die_count;required[ulong(lane)*2+1]=roll_need;
    if(valid&&!error&&(die_count>D||roll_need>R))error|=256;
    ulong state=selected>=0?original[selected]:0,position=old_position;
    cursor=dice+1;
    if(!error)for(long die=0;die<die_count;++die) {
        const long side=state_signed_value(v,state_child(v,cursor,0,valid),valid);
        const long modifier=state_signed_value(v,state_child(v,cursor,1,valid),valid);
        const long set=state_child(v,cursor,2,valid);
        const long maximum=state_signed_value(v,state_child(v,cursor,3,valid),valid);
        const long entries=state_record(v,set)[1];
        const ulong i=ulong(lane)*ulong(D)+ulong(die);int final_face=0;
        for(long roll=0;roll<=maximum;++roll) {
            int face;
            if(tape_count) {
                if(position>=ulong(tape_count)){error|=16;break;}
                const long raw=state_signed_value(v,tape+1+long(position),valid);
                if(!valid||raw<=0||raw>side){error|=32;break;}
                face=int(raw);++position;
            } else face=native_roll(state,int(side));
            faces[i*ulong(R)+ulong(roll)]=face;counts[i]=int(roll+1);final_face=face;
            bool again=false;
            for(long entry=0;entry<entries;++entry)again|=face==state_signed_value(v,set+1+entry,valid);
            if(!again)break;
        }
        if(error)break;
        if(modifier>2147483647L-final_face){error|=64;break;}
        effective[i]=int(modifier+final_face);cursor=state_end(v,cursor,valid);
    }
    if(!valid)error|=1;
    for(int s=0;s<3;++s)next_streams[ulong(lane)*3+ulong(s)]=!error&&s==selected?state:original[s];
    next_positions[lane]=error?old_position:position;errors[lane]=error;
    if(error)for(long die=0;die<D;++die){const ulong i=ulong(lane)*ulong(D)+ulong(die);counts[i]=0;effective[i]=0;
        for(long roll=0;roll<R;++roll)faces[i*ulong(R)+ulong(roll)]=0;}
}
"""
for _name, _section in (("ACTUAL", "random.actual"), ("ACTIVE", "random.active"),
                        ("POSITION", "random.tape_position"), ("TAPE", "random.test_tape"),
                        ("CHANCE", "state.chance")):
    _SAMPLER = _SAMPLER.replace("$" + _name, str(SECTION_NAMES.index(_section)))

_library = None
_lock = threading.Lock()


@lru_cache(maxsize=8)
def _dimensions(values):
    return torch.tensor(values, dtype=torch.int64, device="mps")


@lru_cache(maxsize=1)
def _dummy():
    return torch.empty(1, dtype=torch.int64, device="mps")


def sample_packed_chance(state, *, dice_capacity, roll_capacity):
    """Sample the native pending request without host decoding or mutation."""
    global _library
    state._metadata()
    if state.device.type != "mps":
        raise ValueError("Packed chance sampling requires the explicit Apple GPU")
    if any(type(n) is not int or not 0 <= n <= (1 << 31)-1 for n in (dice_capacity, roll_capacity)):
        raise ValueError("Dice/roll capacities must be nonnegative representable allocations")
    B,C=state.records.shape[:2];D,R=dice_capacity,roll_capacity
    values=(state.records,state.lengths,state.sections,state.context.string_bytes,
            state.context.string_offsets,state.string_bytes,state.string_offsets,state.errors)
    if any(not value.is_contiguous() for value in values):
        raise ValueError("Packed sampling requires contiguous resident buffers")
    faces=torch.empty((B,D,R),dtype=torch.int32,device=state.device)
    counts=torch.empty((B,D),dtype=torch.int32,device=state.device)
    effective=torch.empty_like(counts)
    dice=torch.empty(B,dtype=torch.int64,device=state.device)
    streams=torch.empty((B,3),dtype=torch.int64,device=state.device)
    positions=torch.empty(B,dtype=torch.int64,device=state.device)
    errors=torch.empty(B,dtype=torch.int32,device=state.device)
    required=torch.empty((B,2),dtype=torch.int64,device=state.device)
    result=PackedChanceResult(state,faces,counts,effective,dice,streams,positions,errors,required)
    if not B:return result
    if _library is None:
        with _lock:
            if _library is None:
                _library=torch.mps.compile_shader(RANDOM_SOURCE+METAL_STATE_SOURCE+_SAMPLER)
    dims=(B,C,len(SECTION_NAMES),D,R,state.context.string_count,state.string_offsets.shape[0]-1,
          state.context.string_bytes.numel(),state.string_bytes.numel())
    args=(*values,faces,counts,effective,dice,streams,positions,errors,required,_dimensions(dims))
    _library.sample_packed_chance(*(value if value.numel() else _dummy() for value in args),threads=B)
    return result
