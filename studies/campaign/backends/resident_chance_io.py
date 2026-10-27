"""Resident chance audit payloads and an explicit, atomic RNG commit.

Sampling remains uncommitted until the caller has applied every rule effect.
These helpers do not resolve a rule, reset chance, refresh menus or append an
Event. Outer orchestration retains the original source until all those pieces
have succeeded. No state, face or random value is read back on the hot path.
"""
from dataclasses import dataclass
from enum import IntFlag
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch, _device
from .metal_state_schema import METAL_STATE_SOURCE
from .packed_chance_metal import PackedChanceResult
from .resident_events import EventPayloads


class ChanceIOError(IntFlag):
    SOURCE = 1
    STRING_POOL = 2
    SAMPLER = 4
    RANDOM_CHANGED = 8
    CAPACITY = 16
    REQUEST = 32
    SAMPLE_CONTENT = 64


@dataclass(frozen=True)
class ChancePayloadResult:
    payloads: EventPayloads
    required_capacity: torch.Tensor

    @property
    def errors(self):
        return self.payloads.errors


@dataclass(frozen=True)
class ChanceRandomCommitResult:
    state: DeviceStateBatch
    errors: torch.Tensor
    accepted: torch.Tensor
    committed: torch.Tensor


SOURCE = "#include <metal_stdlib>\nusing namespace metal;\n" + METAL_STATE_SOURCE + r'''
inline bool chance_io_container(thread const PackedStateView& v,long root,long tag,long count,thread bool& valid){
 const long end=state_end(v,root,valid);if(!valid)return false;device const long* row=state_record(v,root);
 if(row[0]!=tag||row[1]<0||(count>=0&&row[1]!=count)||row[2]||row[3]||
    row[1]>(tag==13?(end-root-1)/2:end-root-1))valid=false;return valid;
}
inline long chance_io_random(thread const PackedStateView& v,device const long* sections,thread bool& valid){
 chance_io_container(v,0,10,2,valid);if(!valid)return -1;
 const long state=state_child(v,0,0,valid),root=state_child(v,0,1,valid);
 chance_io_container(v,state,10,19,valid);chance_io_container(v,root,10,6,valid);
 if(!valid||state!=sections[0]||root!=sections[1]||state_end(v,0,valid)!=v.length||
    state_end(v,state,valid)!=root||state_end(v,root,valid)!=v.length){valid=false;return -1;}
 for(long field=0;valid&&field<6;++field)
   if(state_child(v,root,field,valid)!=sections[21+field])valid=false;
 for(long field=0;valid&&field<3;++field)(void)state_unsigned_value(v,sections[21+field],valid);
 const long active=sections[24];
 if(valid&&!state_string_equals(v,active,"actual",6,valid)&&!state_string_equals(v,active,"search",6,valid)&&
    !state_string_equals(v,active,"training",8,valid))valid=false;
 const long tape=sections[25];chance_io_container(v,tape,6,-1,valid);if(!valid)return -1;
 const long count=state_record(v,tape)[1];
 if(state_end(v,tape,valid)!=tape+1+count||sections[26]!=tape+1+count){valid=false;return -1;}
 for(long i=0;valid&&i<count;++i){const long face=state_signed_value(v,tape+1+i,valid);
   if(face<=0||face>2147483647L)valid=false;}
 const ulong position=state_unsigned_value(v,sections[26],valid);
 if(position>ulong(count)||state_end(v,sections[26],valid)!=v.length)valid=false;
 return valid?root:-1;
}
inline void chance_io_row(device long* output,long index,long tag,long count,long end){
 device long* row=output+ulong(index)*5;row[0]=tag;row[1]=count;row[2]=0;row[3]=0;row[4]=end;
}
kernel void chance_io_pool(
 device const uchar* old_bytes[[buffer(0)]],device const long* old_offsets[[buffer(1)]],device const long* old_usage[[buffer(2)]],
 device const uchar* new_bytes[[buffer(3)]],device const long* new_offsets[[buffer(4)]],device const long* new_usage[[buffer(5)]],
 device long* error[[buffer(6)]],device const long* dims[[buffer(7)]],uint tid[[thread_position_in_grid]]){
 if(tid)return;const long os=old_usage[0],ob=old_usage[1],ns=new_usage[0],nb=new_usage[1];
 bool valid=os>=0&&os<=dims[0]&&ob>=0&&ob<=dims[1]&&ns>=os&&ns<=dims[2]&&nb>=ob&&nb<=dims[3];
 if(valid)valid=old_offsets[0]==0&&new_offsets[0]==0&&old_offsets[os]==ob&&new_offsets[ns]==nb;
 for(long i=0;valid&&i<os;++i)valid=old_offsets[i]>=0&&old_offsets[i]<=old_offsets[i+1]&&old_offsets[i+1]<=ob;
 for(long i=0;valid&&i<ns;++i)valid=new_offsets[i]>=0&&new_offsets[i]<=new_offsets[i+1]&&new_offsets[i+1]<=nb;
 for(long i=0;valid&&i<=os;++i)valid=old_offsets[i]==new_offsets[i];
 for(long i=0;valid&&i<ob;++i)valid=old_bytes[i]==new_bytes[i];
 error[0]=valid?0:2;
}
kernel void build_chance_payload(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* sections[[buffer(2)]],
 device const long* source_errors[[buffer(3)]],device const long* after_errors[[buffer(4)]],
 device const uchar* prefix_bytes[[buffer(5)]],device const long* prefix_offsets[[buffer(6)]],
 device const uchar* suffix_bytes[[buffer(7)]],device const long* suffix_offsets[[buffer(8)]],device const long* usage[[buffer(9)]],
 device const int* faces[[buffer(10)]],device const int* counts[[buffer(11)]],device const long* dice[[buffer(12)]],
 device const int* sample_errors[[buffer(13)]],device const long* pool_error[[buffer(14)]],
 device long* output[[buffer(15)]],device long* actual[[buffer(16)]],device long* errors[[buffer(17)]],
 device long* required[[buffer(18)]],device const long* dims[[buffer(19)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],D=dims[2],R=dims[3],O=dims[4];if(long(lane)>=B)return;
 device long* out=output+ulong(lane)*ulong(O)*5;for(long i=0;i<O*5;++i)out[i]=0;
 actual[lane]=0;required[lane]=0;long error=pool_error[0];
 if(source_errors[lane]||after_errors[lane])error|=1;
 if(sample_errors[lane])error|=4|(long(uint(sample_errors[lane]))<<16);
 if(error){errors[lane]=error;return;}
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*ulong(C)*5,lengths[lane],C,
   prefix_bytes,prefix_offsets,dims[5],dims[6],suffix_bytes,suffix_offsets,dims[7],dims[8],usage,valid);
 bool present=false;const long chance=state_optional(v,sections[ulong(lane)*27+16],present,valid);
 if(!valid||!present){errors[lane]=32;return;}chance_io_container(v,chance,10,5,valid);
 const long id=state_string_id(v,state_child(v,chance,0,valid),valid);
 const long specs=state_child(v,chance,4,valid);chance_io_container(v,specs,6,-1,valid);
 const long n=dice[lane];long total=7;
 if(!valid||n<=0||n>D||n!=state_record(v,specs)[1])valid=false;
 for(long die=0;valid&&die<n;++die){const long rolls=counts[ulong(lane)*ulong(D)+ulong(die)];
   if(rolls<=0||rolls>R||total>LONG_MAX-1-rolls){valid=false;break;}total+=1+rolls;
   for(long roll=0;valid&&roll<rolls;++roll)if(faces[(ulong(lane)*ulong(D)+ulong(die))*ulong(R)+ulong(roll)]<=0)valid=false;
 }
 if(!valid){errors[lane]=64;return;}required[lane]=total;
 if(total>O){errors[lane]=16;return;}
 chance_io_row(out,0,13,2,total);chance_io_row(out,1,5,dims[9],2);
 chance_io_row(out,2,13,1,total-2);chance_io_row(out,3,5,dims[10],4);
 chance_io_row(out,4,12,n,total-2);long at=5;
 for(long die=0;die<n;++die){const long rolls=counts[ulong(lane)*ulong(D)+ulong(die)];
   chance_io_row(out,at,12,rolls,at+1+rolls);++at;
   for(long roll=0;roll<rolls;++roll){const long face=faces[(ulong(lane)*ulong(D)+ulong(die))*ulong(R)+ulong(roll)];
     const ulong bits=state_json_integer_bits(face,valid);chance_io_row(out,at,4,0,at+1);
     out[ulong(at)*5+2]=long(bits&0xffffffffUL);out[ulong(at)*5+3]=long(bits>>32);++at;}
 }
 chance_io_row(out,at,5,dims[11],at+1);++at;chance_io_row(out,at,5,id,at+1);
 if(!valid){for(long i=0;i<O*5;++i)out[i]=0;errors[lane]=64;return;}
 actual[lane]=total;errors[lane]=0;
}
kernel void install_chance_randomness(
 device const long* before_records[[buffer(0)]],device const long* before_lengths[[buffer(1)]],device const long* before_sections[[buffer(2)]],
 device const long* before_errors[[buffer(3)]],device const long* after_records[[buffer(4)]],device const long* after_lengths[[buffer(5)]],
 device const long* after_sections[[buffer(6)]],device const long* after_errors[[buffer(7)]],
 device const uchar* prefix_bytes[[buffer(8)]],device const long* prefix_offsets[[buffer(9)]],
 device const uchar* old_bytes[[buffer(10)]],device const long* old_offsets[[buffer(11)]],device const long* old_usage[[buffer(12)]],
 device const uchar* new_bytes[[buffer(13)]],device const long* new_offsets[[buffer(14)]],device const long* new_usage[[buffer(15)]],
 device const ulong* next_streams[[buffer(16)]],device const ulong* next_positions[[buffer(17)]],device const int* sample_errors[[buffer(18)]],
 device const bool* selected[[buffer(19)]],device const long* pool_error[[buffer(20)]],device long* output[[buffer(21)]],
 device long* errors[[buffer(22)]],device const long* dims[[buffer(23)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],A=dims[2];if(long(lane)>=B)return;
 device const long* old=before_records+ulong(lane)*ulong(C)*5;device const long* now=after_records+ulong(lane)*ulong(A)*5;
 device long* out=output+ulong(lane)*ulong(A)*5;for(long i=0;i<A*5;++i)out[i]=now[i];errors[lane]=0;
 if(!selected[lane])return;long error=pool_error[0];
 if(before_errors[lane]||after_errors[lane])error|=1;
 if(sample_errors[lane])error|=4|(long(uint(sample_errors[lane]))<<16);
 if(error){errors[lane]=error;return;}
 bool valid=true;PackedStateView v=make_packed_state_view(old,before_lengths[lane],C,prefix_bytes,prefix_offsets,dims[3],dims[4],
   old_bytes,old_offsets,dims[5],dims[6],old_usage,valid);
 PackedStateView a=make_packed_state_view(now,after_lengths[lane],A,prefix_bytes,prefix_offsets,dims[3],dims[4],
   new_bytes,new_offsets,dims[7],dims[8],new_usage,valid);
 device const long* vs=before_sections+ulong(lane)*27;device const long* as=after_sections+ulong(lane)*27;
 const long vr=chance_io_random(v,vs,valid),ar=chance_io_random(a,as,valid);
 if(!valid){errors[lane]=1;return;}
 const long span=state_end(v,vr,valid)-vr;
 if(state_end(a,ar,valid)-ar!=span){errors[lane]=8;return;}
 for(long i=0;i<span;++i){device const long* x=state_record(v,vr+i);device const long* y=state_record(a,ar+i);
   for(long col=0;col<4;++col)if(x[col]!=y[col])error|=8;
   if(x[4]-vr!=y[4]-ar)error|=8;}
 if(error){errors[lane]=error;return;}
 int active=-1;if(state_string_equals(v,vs[24],"actual",6,valid))active=0;
 else if(state_string_equals(v,vs[24],"search",6,valid))active=1;
 else if(state_string_equals(v,vs[24],"training",8,valid))active=2;
 if(!valid||active<0){errors[lane]=1;return;}
 for(long stream=0;stream<3;++stream)if(stream!=active&&next_streams[ulong(lane)*3+ulong(stream)]!=state_unsigned_value(v,vs[21+stream],valid))error|=64;
 const ulong position=next_positions[lane],previous=state_unsigned_value(v,vs[26],valid);
 const long tape=state_record(v,vs[25])[1];
 if(position<previous||position>ulong(tape)||(!tape&&position!=previous))error|=64;
 bool changed=position!=previous;
 for(long stream=0;stream<3;++stream)changed|=next_streams[ulong(lane)*3+ulong(stream)]!=state_unsigned_value(v,vs[21+stream],valid);
 if(!changed)error|=8;
 if(!valid)error|=1;if(error){errors[lane]=error;return;}
 for(long field=0;field<4;++field){const long root=as[field<3?21+field:26];
   const ulong bits=field<3?next_streams[ulong(lane)*3+ulong(field)]:position;
   out[ulong(root)*5+2]=long(bits&0xffffffffUL);out[ulong(root)*5+3]=long(bits>>32);}
 errors[lane]=0;
}
'''

_library = None
_lock = threading.Lock()


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:
                _library = torch.mps.compile_shader(SOURCE)
    return _library


@lru_cache(maxsize=32)
def _dimensions(values):
    return torch.tensor(values, dtype=torch.int64, device="mps")


@lru_cache(maxsize=1)
def _dummy():
    return torch.zeros(1, dtype=torch.int64, device="mps")


@lru_cache(maxsize=16)
def _labels(context):
    return tuple(int(value) for value in context.prefix_lookup_ids(("outcome", "faces", "request_id")))


def _tensor(value, state, dtype, shape):
    if not isinstance(value, torch.Tensor) or value.dtype != dtype or value.device != state.device or \
            tuple(value.shape) != tuple(shape) or not value.is_contiguous():
        raise ValueError("Chance I/O requires complete contiguous resident buffers with exact native dtypes")


def _bind(before, after, sampled):
    if not isinstance(before, DeviceStateBatch) or not isinstance(after, DeviceStateBatch):
        raise TypeError("Chance I/O requires complete before/after resident states")
    before._metadata(); after._metadata(); _device(before.device)
    if before.device.type != "mps":
        raise ValueError("Chance I/O requires explicit Apple GPU execution; no CPU fallback")
    if not isinstance(sampled, PackedChanceResult) or sampled.source is not before:
        raise ValueError("Sampled chance belongs to another complete source state")
    if before.context is not after.context or before.device != after.device or before.lane_count != after.lane_count:
        raise ValueError("Chance before/after context, device or lane count differs")
    B = before.lane_count
    if not isinstance(sampled.faces, torch.Tensor) or sampled.faces.ndim != 3 or sampled.faces.shape[0] != B:
        raise ValueError("Chance faces must retain all resident lane/die/reroll axes")
    _, D, R = sampled.faces.shape
    for value, dtype, shape in ((sampled.faces, torch.int32, (B,D,R)),
            (sampled.face_counts, torch.int32, (B,D)), (sampled.effective, torch.int32, (B,D)),
            (sampled.dice_counts, torch.int64, (B,)), (sampled.next_streams, torch.int64, (B,3)),
            (sampled.next_tape_positions, torch.int64, (B,)), (sampled.errors, torch.int32, (B,)),
            (sampled.required, torch.int64, (B,2))):
        _tensor(value, before, dtype, shape)
    for state in (before, after):
        for value in (state.records, state.lengths, state.sections, state.errors,
                state.context.string_bytes, state.context.string_offsets, state.string_bytes, state.string_offsets):
            if not value.is_contiguous():
                raise ValueError("Chance I/O source buffers must remain resident and contiguous")
    if B > (1 << 32)-1:
        raise OverflowError("Chance lane count cannot be represented")
    return B, D, R


def _pool(before, after):
    result = torch.empty(1, dtype=torch.int64, device=before.device)
    args = (before.string_bytes, before.string_offsets, before.suffix_usage,
            after.string_bytes, after.string_offsets, after.suffix_usage, result,
            _dimensions((before.string_offsets.numel()-1, before.string_bytes.numel(),
                         after.string_offsets.numel()-1, after.string_bytes.numel())))
    _kernels().chance_io_pool(*(value if value.numel() else _dummy() for value in args), threads=1)
    return result


def build_chance_payload(before, after, sampled, *, capacity):
    """Build complete generic JSON audit data; capacity failures retain exact sizes."""
    B,D,R = _bind(before, after, sampled)
    if type(capacity) is not int or capacity < 0 or B*max(capacity,1)*5 > (1 << 63)-1:
        raise ValueError("Chance payload capacity must be a representable nonnegative allocation")
    labels = _labels(before.context)
    if any(value < 0 for value in labels):
        raise ValueError("Chance protocol labels are absent from the fixed native prefix")
    records = torch.empty((B,capacity,5), dtype=torch.int64, device=before.device)
    lengths = torch.empty(B, dtype=torch.int64, device=before.device)
    errors = torch.empty_like(lengths); required = torch.empty_like(lengths)
    if B:
        args = (before.records,before.lengths,before.sections,before.errors,after.errors,
                before.context.string_bytes,before.context.string_offsets,before.string_bytes,before.string_offsets,before.suffix_usage,
                sampled.faces,sampled.face_counts,sampled.dice_counts,sampled.errors,_pool(before,after),
                records,lengths,errors,required,_dimensions((B,before.records.shape[1],D,R,capacity,
                    before.context.string_count,before.context.string_bytes.numel(),before.string_offsets.numel()-1,
                    before.string_bytes.numel(),*labels)))
        _kernels().build_chance_payload(*(value if value.numel() else _dummy() for value in args), threads=B)
    return ChancePayloadResult(EventPayloads(after,records,lengths,errors),required)


def install_sampled_randomness(before, after, sampled, selected=None):
    """Commit sampled RNG only if every selected lane still has its original Random subtree.

    The three uint64 stream words and tape cursor are the only modified fields.
    Stale/double commits, pool divergence and sampler errors roll back the whole
    selected cohort to ``after``; neither input is mutated or resampled.
    """
    B,_,_ = _bind(before, after, sampled)
    if selected is None:
        selected = torch.ones(B, dtype=torch.bool, device=before.device)
    _tensor(selected, before, torch.bool, (B,))
    candidate = torch.empty_like(after.records); errors = torch.zeros_like(after.errors)
    if B:
        args = (before.records,before.lengths,before.sections,before.errors,
                after.records,after.lengths,after.sections,after.errors,before.context.string_bytes,before.context.string_offsets,
                before.string_bytes,before.string_offsets,before.suffix_usage,after.string_bytes,after.string_offsets,after.suffix_usage,
                sampled.next_streams,sampled.next_tape_positions,sampled.errors,selected,_pool(before,after),candidate,errors,
                _dimensions((B,before.records.shape[1],after.records.shape[1],before.context.string_count,
                    before.context.string_bytes.numel(),before.string_offsets.numel()-1,before.string_bytes.numel(),
                    after.string_offsets.numel()-1,after.string_bytes.numel())))
        _kernels().install_chance_randomness(*(value if value.numel() else _dummy() for value in args), threads=B)
    committed = ~(errors != 0).any()
    state = DeviceStateBatch(after.context,torch.where(committed,candidate,after.records),after.lengths,after.sections,
            after.string_bytes,after.string_offsets,after.errors,after.suffix_usage)
    return ChanceRandomCommitResult(state,errors,selected & committed,committed)
