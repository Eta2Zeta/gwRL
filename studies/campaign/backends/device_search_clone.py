"""Exact device-resident Engine.cloneForSearch on privileged packed snapshots.

This implements an environment clone operation, not MCTS or a full GPU campaign
backend. Each destination preserves its whole board/history and old actual and
training streams. Only the native cloneForSearch changes are applied: the search
stream becomes seeded(seed).search, active becomes search, and test tape/cursor
are cleared. No policy receives these privileged random records.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntFlag
from functools import lru_cache
import threading
from typing import Sequence

import torch
from torch import Tensor

from .device_scheduler import (DeviceSchedulerBatch, capture_schedulers, scheduler_decisions)
from .device_state import DeviceStateBatch, SECTION_NAMES
from .random_metal import SOURCE as RANDOM_SOURCE


class SearchCloneError(IntFlag):
    STATE = 1
    RANDOM = 2
    EDITOR = 4
    SCHEDULER = 8


@dataclass(frozen=True, slots=True)
class DeviceSearchCloneResult:
    state: DeviceStateBatch
    scheduler: DeviceSchedulerBatch | None
    errors: Tensor
    accepted: Tensor


@dataclass(frozen=True, slots=True)
class DeviceSearchRoots:
    """Factory-bound native state and public scheduler metadata for one cohort.

    Buffers are trusted resident snapshots; arbitrary serialized state import
    still belongs to the strict native transport decoder. Capture requires an
    unchanged cohort, just as the scalar adapter requires stable selection.
    """
    state: DeviceStateBatch
    scheduler: DeviceSchedulerBatch

    @classmethod
    def capture(cls, adapters: Sequence, *, device="mps") -> DeviceSearchRoots:
        adapters = tuple(adapters)
        if not adapters:
            raise ValueError("Search roots need a real shared definition")
        before = tuple(env.planning_key() for env in adapters)
        scheduler = capture_schedulers(list(adapters), device=device)
        state = DeviceStateBatch.capture([env.raw for env in adapters], device=device)
        if before != tuple(env.planning_key() for env in adapters):
            raise ValueError("Search roots changed during bound snapshot capture")
        return cls(state, scheduler)

    def clone_for_search(self, seeds: Tensor, lanes: Tensor | None = None, *, implementation="fused") -> DeviceSearchCloneResult:
        return clone_for_search(self.state, seeds, lanes, scheduler=self.scheduler, implementation=implementation)


SOURCE = RANDOM_SOURCE + r"""

inline bool clone_scalar(device const long* row, long tag, long end) {
    return row[0] == tag && row[1] == 0 && row[2] >= 0 && row[2] <= 0xffffffffL &&
           row[3] >= 0 && row[3] <= 0xffffffffL && row[4] == end;
}

kernel void build_search_random_record(
    device const long* records [[buffer(0)]],
    device const long* lengths [[buffer(1)]],
    device const long* sections [[buffer(2)]],
    device const long* state_errors [[buffer(3)]],
    device const ulong* seeds [[buffer(4)]],
    device long* blocks [[buffer(5)]],
    device long* errors [[buffer(6)]],
    device const long* dims [[buffer(7)]],
    uint lane [[thread_position_in_grid]]) {
    const long lanes = dims[0], capacity = dims[1], fields = dims[2];
    if (ulong(lane) >= ulong(lanes)) return;
    device long* output = blocks + ulong(lane) * 35;
    for (int word = 0; word < 35; ++word) output[word] = 0;
    errors[lane] = 0;
    if (state_errors[lane] != 0) { errors[lane] = 1; return; }
    const long length = lengths[lane];
    if (length <= 0 || length > capacity) { errors[lane] = 1; return; }
    device const long* indexes = sections + ulong(lane) * ulong(fields);
    long roots[7];
    for (int field = 0; field < 7; ++field) {
        roots[field] = indexes[dims[3 + field]];
        if (roots[field] < 0 || roots[field] >= length) { errors[lane] = 2; return; }
    }
    device const long* source = records + ulong(lane) * ulong(capacity) * 5;
    const long root = roots[0], actual = roots[1], search = roots[2], training = roots[3];
    const long active = roots[4], tape = roots[5], cursor = roots[6];
    device const long* header = source + ulong(root) * 5;
    if (header[0] != 10 || header[1] != 6 || header[2] != 0 || header[3] != 0 ||
        header[4] != cursor + 1 || actual != root + 1 || search != root + 2 ||
        training != root + 3 || active != root + 4 || tape != root + 5 ||
        !clone_scalar(source + ulong(actual)*5, 3, actual+1) ||
        !clone_scalar(source + ulong(search)*5, 3, search+1) ||
        !clone_scalar(source + ulong(training)*5, 3, training+1) ||
        !clone_scalar(source + ulong(cursor)*5, 3, cursor+1)) { errors[lane] = 2; return; }
    device const long* old_active = source + ulong(active)*5;
    if (old_active[0] != 5 || old_active[2] != 0 || old_active[3] != 0 || old_active[4] != active+1 ||
        (old_active[1] != dims[10] && old_active[1] != dims[11] && old_active[1] != dims[12])) {
        errors[lane] = 2; return;
    }
    device const long* old_tape = source + ulong(tape)*5;
    const long count = old_tape[1];
    if (old_tape[0] != 6 || count < 0 || count > length-tape-1 || old_tape[2] != 0 ||
        old_tape[3] != 0 || old_tape[4] != tape+1+count || cursor != old_tape[4]) {
        errors[lane] = 2; return;
    }
    device const long* old_cursor = source + ulong(cursor)*5;
    const ulong position = ulong(old_cursor[2]) | (ulong(old_cursor[3]) << 32);
    if (position > ulong(count)) { errors[lane] = 2; return; }
    for (long entry = 0; entry < count; ++entry) {
        const long index = tape + 1 + entry;
        device const long* face = source + ulong(index)*5;
        if (!clone_scalar(face, 2, index+1) || face[2] <= 0 || face[2] > 2147483647 || face[3] != 0) {
            errors[lane] = 2; return;
        }
    }
    ulong seed = seeds[lane];
    (void)next_random(seed);
    const ulong seeded_search = next_random(seed);
    // All subtree_end values are LOCAL to this seven-node replacement.
    output[0]=10; output[1]=6; output[4]=7;
    for (int field=0; field<3; ++field) {
        device long* row=output+(field+1)*5;
        row[0]=3; row[4]=field+2;
        if (field==1) { row[2]=long(seeded_search & 0xffffffffUL); row[3]=long(seeded_search >> 32); }
        else {
            const long index=field==0?actual:training;
            row[2]=source[ulong(index)*5+2]; row[3]=source[ulong(index)*5+3];
        }
    }
    output[20]=5; output[21]=dims[11]; output[24]=5;
    output[25]=6; output[29]=6;
    output[30]=3; output[34]=7;
}
"""

# A workgroup owns one destination. It validates/seeds once, then copies whole
# records in parallel. RandomStreams is the final Engine child, so clearing its
# tape changes no State/history position or bit and needs no general tree edit.
FUSED_SOURCE = SOURCE + r"""
inline long fused_source_error(device const long* source, long length, long capacity,
                               device const long* indexes, device const long* dims,
                               thread long& root) {
    if(length<2||length>capacity)return 1;
    long positions[7];
    for(int field=0;field<7;++field){
        positions[field]=indexes[dims[3+field]];
        if(positions[field]<0||positions[field]>=length)return 2;
    }
    root=positions[0];
    const long state=indexes[0];
    if(state!=1||source[0]!=10||source[1]!=2||source[2]||source[3]||source[4]!=length)return 1;
    device const long* state_header=source+5;
    if(state_header[0]!=10||state_header[1]!=19||state_header[2]||state_header[3]||state_header[4]!=root)return 1;
    device const long* header=source+ulong(root)*5;
    const long cursor=positions[6], tape=positions[5];
    if(header[0]!=10||header[1]!=6||header[2]||header[3]||header[4]!=length||cursor+1!=length||
       positions[1]!=root+1||positions[2]!=root+2||positions[3]!=root+3||positions[4]!=root+4||tape!=root+5)return 2;
    for(int field=1;field<=3;++field)
        if(!clone_scalar(source+ulong(positions[field])*5,3,positions[field]+1))return 2;
    if(!clone_scalar(source+ulong(cursor)*5,3,cursor+1))return 2;
    device const long* active=source+ulong(positions[4])*5;
    if(active[0]!=5||active[2]||active[3]||active[4]!=positions[4]+1||
       (active[1]!=dims[10]&&active[1]!=dims[11]&&active[1]!=dims[12]))return 2;
    device const long* sequence=source+ulong(tape)*5;
    const long count=sequence[1];
    if(sequence[0]!=6||count<0||count>length-tape-1||sequence[2]||sequence[3]||
       sequence[4]!=tape+1+count||cursor!=sequence[4])return 2;
    device const long* counter=source+ulong(cursor)*5;
    if((ulong(counter[2])|(ulong(counter[3])<<32))>ulong(count))return 2;
    for(long entry=0;entry<count;++entry){
        const long index=tape+1+entry;
        device const long* face=source+ulong(index)*5;
        if(!clone_scalar(face,2,index+1)||face[2]<=0||face[2]>2147483647||face[3])return 2;
    }
    return 0;
}

kernel void fused_search_clone(
 device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],
 device const long* sections [[buffer(2)]],device const long* inherited_errors [[buffer(3)]],
 device const ulong* seeds [[buffer(4)]],device const long* lanes [[buffer(5)]],
 device const long* scheduler_errors [[buffer(6)]],device long* output [[buffer(7)]],
 device long* output_lengths [[buffer(8)]],device long* output_sections [[buffer(9)]],
 device long* state_errors [[buffer(10)]],device long* errors [[buffer(11)]],
 device bool* accepted [[buffer(12)]],device const long* dims [[buffer(13)]],
 uint3 group [[threadgroup_position_in_grid]],uint tid [[thread_index_in_threadgroup]],
 uint3 group_size [[threads_per_threadgroup]]) {
    const long lane=long(group.x), capacity=dims[1], fields=dims[2];
    if(lane>=dims[13])return;
    threadgroup long source_lane, root, total, error, inherited;
    threadgroup bool source_valid;
    threadgroup long random[35];
    if(tid==0){
        source_lane=lanes[lane];source_valid=source_lane>=0&&source_lane<dims[0];
        error=0;inherited=0;root=0;total=0;
        for(int word=0;word<35;++word)random[word]=0;
        if(!source_valid)error|=1;
        else {
            inherited=inherited_errors[source_lane];total=lengths[source_lane];
            if(inherited)error|=1;
            if(!error){
                long found=0;
                error|=fused_source_error(records+ulong(source_lane)*ulong(capacity)*5,total,capacity,
                    sections+ulong(source_lane)*ulong(fields),dims,found);
                root=found;
            }
        }
        if(dims[14])error|=scheduler_errors[lane]?8:0;
        if(!error){
            device const long* source=records+ulong(source_lane)*ulong(capacity)*5;
            ulong seed=seeds[lane];(void)next_random(seed);const ulong search=next_random(seed);
            total=root+7;
            random[0]=10;random[1]=6;random[4]=root+7;
            for(int field=0;field<3;++field){
                const int row=(field+1)*5;random[row]=3;random[row+4]=root+field+2;
                if(field==1){random[row+2]=long(search&0xffffffffUL);random[row+3]=long(search>>32);}
                else {const long index=root+field+1;random[row+2]=source[ulong(index)*5+2];random[row+3]=source[ulong(index)*5+3];}
            }
            random[20]=5;random[21]=dims[11];random[24]=root+5;
            random[25]=6;random[29]=root+6;random[30]=3;random[34]=root+7;
        }
        output_lengths[lane]=source_valid?total:0;
        state_errors[lane]=inherited|(error?1:0);errors[lane]=error;accepted[lane]=error==0;
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    device long* dest=output+ulong(lane)*ulong(capacity)*5;
    for(ulong word=tid;word<ulong(capacity)*5;word+=group_size.x){
        long value=0;
        if(source_valid){
            device const long* source=records+ulong(source_lane)*ulong(capacity)*5;
            if(error)value=source[word];
            else if(word==4)value=total;
            else if(word<ulong(root)*5)value=source[word];
            else if(word<ulong(root+7)*5)value=random[word-ulong(root)*5];
        }
        dest[word]=value;
    }
    for(long field=tid;field<fields;field+=group_size.x){
        long value=source_valid?sections[ulong(source_lane)*ulong(fields)+ulong(field)]:0;
        if(!error&&field==dims[9])value=root+6;
        output_sections[ulong(lane)*ulong(fields)+ulong(field)]=value;
    }
}
"""

_library = None
_fused_library = None
_lock = threading.Lock()


@lru_cache(maxsize=8)
def _dimensions(values):
    return torch.tensor(values, dtype=torch.int64, device="mps")


@lru_cache(maxsize=1)
def _dummy():
    return torch.empty(1, dtype=torch.int64, device="mps")


def _random_blocks(state, seeds):
    global _library
    count, capacity = state.records.shape[:2]
    if not hasattr(torch.mps, "compile_shader"):
        raise RuntimeError("Resident search clones require torch.mps.compile_shader")
    if _library is None:
        with _lock:
            if _library is None:
                _library = torch.mps.compile_shader(SOURCE)
    columns = tuple(SECTION_NAMES.index(name) for name in
                    ("random", "random.actual", "random.search", "random.training", "random.active",
                     "random.test_tape", "random.tape_position"))
    dimensions = (count, capacity, len(SECTION_NAMES), *columns, *state.context.random_stream_ids)
    blocks = torch.empty((count, 7, 5), dtype=torch.int64, device=state.device)
    errors = torch.empty(count, dtype=torch.int64, device=state.device)
    tensors = (state.records, state.lengths, state.sections, state.errors, seeds, blocks, errors, _dimensions(dimensions))
    if any(not value.is_contiguous() for value in tensors):
        raise ValueError("Resident search-clone buffers must be contiguous; no hidden host or integer cast")
    _library.build_search_random_record(*(value if value.numel() else _dummy() for value in tensors), threads=count)
    return blocks, errors


def _fused_clone(state, seeds, lanes, scheduled):
    global _fused_library
    count, capacity = lanes.shape[0], state.records.shape[1]
    invalid_scheduler = scheduler_decisions(scheduled).errors if scheduled is not None else None
    if _fused_library is None:
        with _lock:
            if _fused_library is None:
                _fused_library = torch.mps.compile_shader(FUSED_SOURCE)
    columns = tuple(SECTION_NAMES.index(name) for name in
        ("random", "random.actual", "random.search", "random.training", "random.active", "random.test_tape", "random.tape_position"))
    dimensions = (state.lane_count, capacity, len(SECTION_NAMES), *columns,
                  *state.context.random_stream_ids, count, int(scheduled is not None))
    records = torch.empty((count, capacity, 5), dtype=torch.int64, device=state.device)
    lengths = torch.empty(count, dtype=torch.int64, device=state.device)
    sections = torch.empty((count, len(SECTION_NAMES)), dtype=torch.int64, device=state.device)
    state_errors, errors = torch.empty_like(lengths), torch.empty_like(lengths)
    accepted = torch.empty(count, dtype=torch.bool, device=state.device)
    tensors = (state.records, state.lengths, state.sections, state.errors, seeds, lanes,
        invalid_scheduler if invalid_scheduler is not None else _dummy(), records, lengths, sections,
        state_errors, errors, accepted, _dimensions(dimensions))
    if any(not value.is_contiguous() for value in tensors):
        raise ValueError("Fused clone buffers must be contiguous; prepare strided selections explicitly on device")
    kernel = _fused_library.fused_search_clone
    group_size = min(256, kernel.max_threads_per_threadgroup)
    kernel(*(value if value.numel() else _dummy() for value in tensors),
           threads=count * group_size, group_size=group_size)
    result = replace(state, records=records, lengths=lengths, sections=sections, errors=state_errors)
    return DeviceSearchCloneResult(result, scheduled, errors, accepted)


def clone_for_search(state: DeviceStateBatch, seeds: Tensor, lanes: Tensor | None = None, *,
                     scheduler: DeviceSchedulerBatch | None = None, implementation="fused") -> DeviceSearchCloneResult:
    """Fork roots and replace RandomStreams once, without reading device values.

    Seeds are int64 *bit storage* for the entire uint64 seed domain. Each seed
    aligns with a destination lane, including repeated roots. Invalid resident
    selections are flagged per destination; no original is ever mutated. When
    supplying scheduler separately, it must belong to these same source roots;
    DeviceSearchRoots.capture provides the normal bound capture path.
    """
    if implementation not in {"fused", "reference"}:
        raise ValueError("Search clone implementation must be explicit fused or reference")
    state._metadata()
    if state.device.type != "mps":
        raise ValueError("Resident search cloning requires Apple MPS; select the CPU backend explicitly")
    from .metal_validation import require_lossless_mps_indexing
    require_lossless_mps_indexing()
    if lanes is None:
        lanes = torch.arange(state.lane_count, dtype=torch.int64, device=state.device)
    if not isinstance(lanes, Tensor) or lanes.ndim != 1 or lanes.dtype != torch.int64 or lanes.device != state.device:
        raise ValueError("Search-clone roots must be a resident int64 lane vector")
    if (not isinstance(seeds, Tensor) or seeds.dtype != torch.int64 or seeds.device != state.device or
            tuple(seeds.shape) != tuple(lanes.shape) or not seeds.is_contiguous()):
        raise ValueError("Search-clone seeds must be an aligned contiguous resident int64 vector of uint64 bits")
    if lanes.shape[0] > 2**32 - 1:
        raise OverflowError("Search-clone grid is not representable; no destination lanes are truncated")
    if scheduler is not None and (scheduler.lane_count != state.lane_count or scheduler.device != state.device):
        raise ValueError("Source state and scheduler must have identical lane counts and device")
    scheduled = scheduler.fork(lanes) if scheduler is not None else None
    if not lanes.shape[0]:
        forked = state.fork(lanes)
        return DeviceSearchCloneResult(forked, scheduled, forked.errors.clone(), forked.errors == 0)
    if not state.lane_count:
        raise ValueError("Cannot clone nonempty search roots from an empty source batch")
    if implementation == "fused":
        return _fused_clone(state, seeds, lanes, scheduled)
    forked = state.fork(lanes)
    blocks, errors = _random_blocks(forked, seeds)
    if scheduled is not None:
        invalid_scheduler = scheduler_decisions(scheduled).errors != 0
        errors = errors | (invalid_scheduler.to(torch.int64) * int(SearchCloneError.SCHEDULER))
    selected = errors == 0
    from .device_state_edits import replace_subtrees
    # A validated native RandomStreams record has seven nodes plus tape faces;
    # clearing the tape cannot grow it. Reusing the existing capacity therefore
    # retains all legal state, rather than imposing an arbitrary allocation cap.
    edited = replace_subtrees(forked, forked.section("random").contiguous(), blocks,
        torch.full_like(forked.lengths, 7), selected, capacity=forked.records.shape[1])
    # The shared editor commits its selected cohort atomically. If one edit
    # fails, flag every requested lane rolled back, not only the first error;
    # otherwise an unseeded old state could appear to be a valid search clone.
    errors = errors | ((selected & ~edited.accepted).to(torch.int64) * int(SearchCloneError.EDITOR))
    # An ignored request error must never leave an apparently valid unseeded
    # destination. The original source and its errors remain untouched.
    result_state = replace(edited.state, errors=edited.state.errors | (errors != 0).to(torch.int64))
    return DeviceSearchCloneResult(result_state, scheduled, errors, edited.accepted & (errors == 0))
