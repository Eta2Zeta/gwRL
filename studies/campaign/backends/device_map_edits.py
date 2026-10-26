"""Exact resident map, set and sequence construction over packed native state.

These are internal structural builders, not game-action legality handlers. Keys
are compared as native byte strings, never by intern ID. Complete unmodified
subtrees are copied verbatim. Allocation failures return required sizes and an
unchanged state; callers may retry with larger buffers without changing rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch
from .device_state_edits import SOURCE as EDIT_SOURCE, _host_tree, _strings, replace_subtrees


class MapMode(IntEnum):
    UPSERT = 0
    INSERT_IF_ABSENT = 1
    REPLACE_EXISTING = 2
    ERASE = 3


class SetMode(IntEnum):
    INSERT = 1
    ERASE = 3


class ContainerError(IntFlag):
    SOURCE = 1
    TARGET = 2
    KEY = 4
    VALUE = 8
    MODE = 16
    BOUNDS = 32
    CAPACITY = 64
    MISSING = 128


@dataclass(frozen=True)
class ContainerBuildResult:
    source: DeviceStateBatch
    roots: torch.Tensor
    selected: torch.Tensor
    blocks: torch.Tensor
    lengths: torch.Tensor
    errors: torch.Tensor
    required_capacity: torch.Tensor
    changed: torch.Tensor


@dataclass(frozen=True)
class ContainerEditResult:
    state: DeviceStateBatch
    build: ContainerBuildResult
    errors: torch.Tensor  # builder bits in low byte; generic editor bits << 8
    edit_errors: torch.Tensor
    required_state_capacity: torch.Tensor
    accepted: torch.Tensor
    committed: torch.Tensor
    changed: torch.Tensor


SOURCE = EDIT_SOURCE + r"""
inline void container_copy(thread const PackedStateView& src,long root,
 device long* out,long capacity,thread long& cursor,thread bool& valid){
 long end=state_end(src,root,valid);if(!valid)return;
 long size=end-root,start=cursor;
 if(size>0x7fffffffffffffffL-cursor){valid=false;return;}
 cursor+=size;
 for(long i=root;i<end;++i){
   device const long* row=state_record(src,i);
   if(row[4]<=i||row[4]>end){valid=false;return;}
   long next=start+i-root;
   if(next<capacity){for(long col=0;col<4;++col)out[next*5+col]=row[col];out[next*5+4]=row[4]+start-root;}
 }
}
inline void container_key(long id,device long* out,long capacity,thread long& cursor){
 if(cursor<capacity){out[cursor*5]=5;out[cursor*5+1]=id;out[cursor*5+2]=0;out[cursor*5+3]=0;out[cursor*5+4]=cursor+1;}++cursor;
}
inline int container_compare(thread const PackedStateView& view,long first,long second,thread bool& valid){
 if(first<0||second<0||first>=view.prefix_count+view.suffix_count||second>=view.prefix_count+view.suffix_count){valid=false;return 0;}
 if(first==second)return 0;
 if(edit_string_less(view,first,second,valid))return -1;
 if(edit_string_less(view,second,first,valid))return 1;
 // Validated resident string pools contain one ID per exact byte spelling.
 return 0;
}
kernel void build_containers(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* inherited[[buffer(2)]],device const long* controls[[buffer(3)]],
 device const long* values[[buffer(4)]],device const long* value_lengths[[buffer(5)]],
 device const bool* selected[[buffer(6)]],device long* output[[buffer(7)]],
 device long* output_lengths[[buffer(8)]],device long* errors[[buffer(9)]],
 device long* required[[buffer(10)]],device long* changed[[buffer(11)]],
 device long* stack_ends[[buffer(12)]],device long* stack_remaining[[buffer(13)]],
 device long* stack_previous[[buffer(14)]],device const long* dims[[buffer(15)]],
 device const uchar* prefix_bytes[[buffer(16)]],device const long* prefix_offsets[[buffer(17)]],
 device const uchar* suffix_bytes[[buffer(18)]],device const long* suffix_offsets[[buffer(19)]],
 device const long* suffix_usage[[buffer(20)]],uint thread_index[[thread_position_in_grid]]){
 long lane=long(thread_index),B=dims[0],C=dims[1],R=dims[2],V=dims[3],kind=dims[8],S=max(C,max(R,V));
 if(lane>=B)return;
 device long* out=output+ulong(lane)*ulong(R)*5;
 for(long i=0;i<R*5;++i)out[i]=0;
 output_lengths[lane]=0;errors[lane]=0;required[lane]=0;changed[lane]=0;
 if(!selected[lane])return;
 bool valid=true;
 PackedStateView src=make_packed_state_view(records+ulong(lane)*ulong(C)*5,lengths[lane],C,
   prefix_bytes,prefix_offsets,dims[4],dims[5],suffix_bytes,suffix_offsets,dims[6],dims[7],suffix_usage,valid);
 device long* ends=stack_ends+ulong(lane)*ulong(S);
 device long* remaining=stack_remaining+ulong(lane)*ulong(S);
 device long* previous=stack_previous+ulong(lane)*ulong(S)*2;
 if(!valid||inherited[lane]||!edit_tree(src,ends,remaining,previous)){errors[lane]=1;return;}
 device const long* ctl=controls+ulong(lane)*6;
 long root=ctl[0],key=ctl[1],mode=ctl[2],begin=ctl[3],remove=ctl[4],added=ctl[5];
 long target_end=state_end(src,root,valid);
 if(!valid){errors[lane]=2;return;}
 device const long* header=state_record(src,root);long tag=header[0],count=header[1];
 if((kind==0&&tag!=7&&tag!=13)||(kind==1&&tag!=8)||(kind==2&&tag!=6&&tag!=12)){errors[lane]=2;return;}
 if(kind<2&&((kind==0&&(mode<0||mode>3))||(kind==1&&mode!=1&&mode!=3))){errors[lane]=16;return;}
 if(kind==0&&(key<0||key>=src.prefix_count+src.suffix_count)){errors[lane]=4;return;}
 PackedStateView val=src;val.records=values+ulong(lane)*ulong(V)*5;val.capacity=V;val.length=value_lengths[lane];
 bool value_ready=false;
 if(kind==1){
   if(val.length!=1||V<1||!edit_tree(val,ends,remaining,previous)||(val.records[0]!=2&&val.records[0]!=5)){errors[lane]=8;return;}
   if(count&&state_record(src,root+1)[0]!=val.records[0]){errors[lane]=8;return;}
 }
 if(kind==2&&(begin<0||begin>count||remove<0||remove>count-begin||added<0||added>V||val.length<0||val.length>V)){
   errors[lane]=32;return;
 }
 long cursor=1,next_count=count,position=root+1;bool found=false,inserted=false,did_change=false;
 for(long entry=0;entry<count;++entry){
   if(kind==0){
     long current=state_string_id(src,position,valid),value_root=position+1;
     int comparison=container_compare(src,current,key,valid);
     long value_end=state_end(src,value_root,valid);if(!valid||value_end>target_end){errors[lane]=1;return;}
     bool add_before=!inserted&&comparison>0&&mode!=3&&mode!=2;
     if(add_before||comparison==0){
       if(comparison==0){found=true;inserted=true;}
       if(mode!=3){
         bool use_new=add_before||mode!=1;
         if(use_new&&!value_ready){
           if(val.length<=0||val.length>V||!edit_tree(val,ends,remaining,previous)){errors[lane]=8;return;}value_ready=true;
         }
         container_key(key,out,R,cursor);
         container_copy(use_new?val:src,use_new?0:value_root,out,R,cursor,valid);
         if(use_new)did_change=true;
       }else did_change=true;
       if(add_before){inserted=true;++next_count;}
       if(comparison==0){if(mode==3)--next_count;position=value_end;continue;}
     }
     container_copy(src,position,out,R,cursor,valid);container_copy(src,value_root,out,R,cursor,valid);position=value_end;
   }else if(kind==1){
     device const long* old=state_record(src,position);int comparison=0;
     if(old[0]==5)comparison=container_compare(src,old[1],val.records[1],valid);
     else {long a=state_signed_value(src,position,valid),b=state_signed_value(val,0,valid);comparison=a<b?-1:(a>b?1:0);}
     if(!inserted&&comparison>0&&mode==1){container_copy(val,0,out,R,cursor,valid);inserted=true;++next_count;did_change=true;}
     if(comparison==0){found=true;inserted=true;if(mode==3){--next_count;did_change=true;}else container_copy(src,position,out,R,cursor,valid);}
     else container_copy(src,position,out,R,cursor,valid);
     position=state_end(src,position,valid);
   }else{
     if(entry==begin){
       long value_pos=0;
       for(long j=0;j<added;++j){container_copy(val,value_pos,out,R,cursor,valid);value_pos=state_end(val,value_pos,valid);if(!valid)break;}
       if(!valid||value_pos!=val.length){errors[lane]=8;return;}inserted=true;
     }
     if(entry<begin||entry>=begin+remove)container_copy(src,position,out,R,cursor,valid);
     position=state_end(src,position,valid);
   }
   if(!valid){errors[lane]=8;return;}
 }
 if(position!=target_end){errors[lane]=1;return;}
 if(kind==0&&!found&&!inserted&&mode!=3){
   if(mode==2){errors[lane]=128;return;}
   if(val.length<=0||val.length>V||!edit_tree(val,ends,remaining,previous)){errors[lane]=8;return;}
   container_key(key,out,R,cursor);container_copy(val,0,out,R,cursor,valid);++next_count;did_change=true;
 }else if(kind==1&&!found&&!inserted&&mode==1){container_copy(val,0,out,R,cursor,valid);++next_count;did_change=true;}
 else if(kind==2){
   if(!inserted){long value_pos=0;for(long j=0;j<added;++j){container_copy(val,value_pos,out,R,cursor,valid);value_pos=state_end(val,value_pos,valid);if(!valid)break;}
     if(!valid||value_pos!=val.length){errors[lane]=8;return;}}
   next_count=count-remove+added;did_change=remove!=0||added!=0;
 }
 required[lane]=cursor;
 if(!valid){errors[lane]=8;return;}
 if(cursor>R){errors[lane]=64;return;}
 out[0]=tag;out[1]=next_count;out[2]=0;out[3]=0;out[4]=cursor;
 PackedStateView result=src;result.records=out;result.length=cursor;result.capacity=R;
 if(!edit_tree(result,ends,remaining,previous)){errors[lane]=8;return;}
 output_lengths[lane]=cursor;changed[lane]=did_change?1:0;
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


def _check_tensor(state, value, shape, dtype):
    if (not isinstance(value, torch.Tensor) or value.device != state.device or value.dtype != dtype or
            tuple(value.shape) != shape or not value.is_contiguous()):
        raise ValueError("Container edits require complete contiguous resident tensors with exact dtypes")


def _build(state, roots, controls, values, value_lengths, selected, kind, capacity):
    if not isinstance(state, DeviceStateBatch):
        raise TypeError("Expected complete resident state")
    state._metadata()
    B, C = state.records.shape[:2]
    if B > 2**32-1:
        raise OverflowError("Container grid is not representable; no lanes truncated")
    if not isinstance(values, torch.Tensor) or values.ndim != 3 or values.shape[0] != B or values.shape[2] != 5:
        raise ValueError("Complete replacement values require [lane,capacity,5] shape")
    V = values.shape[1]
    R = max(C, 1) if capacity is None else capacity
    if type(R) is not int or R < 1:
        raise ValueError("Container block capacity must be a positive explicit allocation")
    for value, shape, dtype in ((roots, (B,), torch.int64), (controls, (B, 6), torch.int64),
            (values, (B, V, 5), torch.int64), (value_lengths, (B,), torch.int64), (selected, (B,), torch.bool)):
        _check_tensor(state, value, shape, dtype)
    for value in (state.records, state.lengths, state.errors, state.context.string_bytes,
                  state.context.string_offsets, state.string_bytes, state.string_offsets):
        if not value.is_contiguous():
            raise ValueError("Container source buffers must be contiguous; no hidden conversion")
    if state.device.type == "cpu":
        blocks, lengths, errors, required, changed = _cpu_build(state, controls, values, value_lengths, selected, kind, R)
    elif state.device.type == "mps":
        global _library
        blocks = torch.zeros((B, R, 5), dtype=torch.int64, device=state.device)
        lengths, errors, required = (torch.zeros_like(state.lengths) for _ in range(3))
        changed = torch.zeros_like(state.lengths)
        if B:
            if _library is None:
                with _lock:
                    if _library is None:
                        _library = torch.mps.compile_shader(SOURCE)
            S = max(C, R, V, 1)
            scratch = [torch.empty((B, S*factor), dtype=torch.int64, device=state.device) for factor in (1, 1, 2)]
            tensors = (state.records, state.lengths, state.errors, controls, values, value_lengths, selected,
                blocks, lengths, errors, required, changed, *scratch,
                _dimensions((B, C, R, V, state.context.string_count, state.context.string_bytes.numel(),
                    state.string_offsets.numel()-1, state.string_bytes.numel(), kind)),
                state.context.string_bytes, state.context.string_offsets, state.string_bytes, state.string_offsets, state.suffix_usage)
            _library.build_containers(*(value if value.numel() else _dummy() for value in tensors), threads=B)
    else:
        raise ValueError("Container builders require explicit CPU or Apple MPS; no fallback")
    return ContainerBuildResult(state, roots, selected, blocks, lengths, errors, required, changed != 0)


def _cpu_build(state, controls, values, value_lengths, selected, kind, capacity):
    """Independent scalar oracle, never used as a GPU implementation."""
    raw, ctls, vals = state.records.tolist(), controls.tolist(), values.tolist()
    sizes, enabled, inherited = state.lengths.tolist(), selected.tolist(), state.errors.tolist()
    vsizes = value_lengths.tolist()
    try:
        count, used = state.suffix_usage.tolist()
        valid_pool = (0 <= count < state.string_offsets.numel() and 0 <= used <= state.string_bytes.numel() and
                      state.string_offsets[0].item() == 0 and state.string_offsets[count].item() == used)
        strings = _strings(state) if valid_pool else []
    except (IndexError, ValueError):
        valid_pool, strings = False, []
    blocks, lengths, errors, required, changed = [], [], [], [], []
    for lane, ctl in enumerate(ctls):
        rows, error, needed, did_change = [], 0, 0, False
        source = raw[lane][:sizes[lane]]
        if enabled[lane]:
            root, key, mode, begin, remove, added = ctl
            if not valid_pool or inherited[lane] or not 0 < sizes[lane] <= len(raw[lane]) or not _host_tree(source, strings):
                error = ContainerError.SOURCE
            elif not 0 <= root < len(source):
                error = ContainerError.TARGET
            elif source[root][0] not in ((7, 13) if kind == 0 else (8,) if kind == 1 else (6, 12)):
                error = ContainerError.TARGET
            else:
                tag, count, _, _, end = source[root]
                def subtree(data, at):
                    if not 0 <= at < len(data) or not at < data[at][4] <= len(data):
                        raise ValueError("Invalid subtree")
                    return [[*row[:4], row[4]-at] for row in data[at:data[at][4]]]
                entries, cursor = [], root+1
                for _ in range(count):
                    if kind == 0:
                        entries.append((source[cursor][1], subtree(source, cursor+1)))
                        cursor = source[cursor+1][4]
                    else:
                        entries.append(subtree(source, cursor)); cursor = source[cursor][4]
                value = vals[lane][:vsizes[lane]]
                if kind < 2 and mode not in ((0, 1, 2, 3) if kind == 0 else (1, 3)):
                    error = ContainerError.MODE
                elif kind == 0:
                    if not 0 <= key < len(strings):
                        error = ContainerError.KEY
                    else:
                        found = next((i for i, (old, _) in enumerate(entries) if strings[old] == strings[key]), None)
                        use_value = mode != MapMode.ERASE and not (mode == MapMode.INSERT_IF_ABSENT and found is not None)
                        if mode == MapMode.REPLACE_EXISTING and found is None:
                            error = ContainerError.MISSING
                        elif use_value and (not 0 < vsizes[lane] <= values.shape[1] or not _host_tree(value, strings)):
                            error = ContainerError.VALUE
                        elif mode == MapMode.ERASE:
                            if found is not None: entries.pop(found); did_change = True
                        elif use_value:
                            if found is not None: entries[found] = (key, value)
                            else: entries.append((key, value))
                            entries.sort(key=lambda pair: strings[pair[0]]); did_change = True
                    payload = []
                    for old, value in entries:
                        payload.append([[5, old, 0, 0, 1]]); payload.append(value)
                    count = len(entries)
                elif kind == 1:
                    if (vsizes[lane] != 1 or values.shape[1] < 1 or not _host_tree(value, strings) or
                            value[0][0] not in (2, 5) or (entries and entries[0][0][0] != value[0][0])):
                        error = ContainerError.VALUE
                    else:
                        def sort_key(block):
                            row = block[0]
                            if row[0] == 5: return strings[row[1]]
                            result = row[2] | row[3] << 32
                            return result-(1 << 64) if result >= 1 << 63 else result
                        found = next((i for i, block in enumerate(entries) if sort_key(block) == sort_key(value)), None)
                        if mode == SetMode.ERASE and found is not None: entries.pop(found); did_change = True
                        elif mode == SetMode.INSERT and found is None: entries.append(value); entries.sort(key=sort_key); did_change = True
                    payload, count = entries, len(entries)
                else:
                    if not (0 <= begin <= count and 0 <= remove <= count-begin and 0 <= added <= values.shape[1] and 0 <= vsizes[lane] <= values.shape[1]):
                        error = ContainerError.BOUNDS
                    else:
                        pieces, at = [], 0
                        try:
                            for _ in range(added):
                                pieces.append(subtree(value, at)); at = value[at][4]
                            if at != vsizes[lane]: raise ValueError("Incomplete forest")
                        except (ValueError, IndexError): error = ContainerError.VALUE
                        if not error: entries[begin:begin+remove] = pieces; did_change = bool(remove or added)
                    payload, count = entries, len(entries)
                if not error:
                    rows = [[tag, count, 0, 0, 0]]
                    for part in payload:
                        start = len(rows)
                        rows.extend([[*row[:4], row[4]+start] for row in part])
                    rows[0][4] = len(rows); needed = len(rows)
                    if not _host_tree(rows, strings): error = ContainerError.VALUE
                    elif needed > capacity: error = ContainerError.CAPACITY
        blocks.append((rows[:capacity]+[[0]*5]*capacity)[:capacity])
        lengths.append(len(rows) if not error else 0); errors.append(int(error)); required.append(needed); changed.append(did_change and not error)
    B = state.lane_count
    return (torch.tensor(blocks, dtype=torch.int64).reshape(B, capacity, 5), torch.tensor(lengths, dtype=torch.int64),
            torch.tensor(errors, dtype=torch.int64), torch.tensor(required, dtype=torch.int64), torch.tensor(changed, dtype=torch.bool))


def build_map_edits(state, roots, keys, modes, values, value_lengths, selected, *, capacity=None):
    """Build one byte-sorted native map/JSON-object edit per selected lane.

    INSERT_IF_ABSENT on an existing key and ERASE do not consume the value.
    A safe metadata-only block retry capacity is old_state_capacity+1+value_capacity.
    """
    B = state.lane_count
    for value in (roots, keys, modes): _check_tensor(state, value, (B,), torch.int64)
    zero = torch.zeros_like(roots)
    controls = torch.stack((roots, keys, modes, zero, zero, zero), dim=1)
    return _build(state, roots, controls, values, value_lengths, selected, 0, capacity)


def build_set_edits(state, roots, modes, elements, selected, *, capacity=None):
    """Build idempotent insert/erase for native string or signed-int32 sets.

    Elements have [lane,1,5] shape and use local scalar end=1. Empty sets
    retain their native contextual element type in the calling rule handler.
    """
    B = state.lane_count
    for value in (roots, modes): _check_tensor(state, value, (B,), torch.int64)
    zero = torch.zeros_like(roots)
    controls = torch.stack((roots, zero, modes, zero, zero, zero), dim=1)
    return _build(state, roots, controls, elements, torch.ones_like(roots), selected, 1, capacity)


def build_sequence_splices(state, roots, begins, remove_counts, values, value_lengths, value_counts, selected, *, capacity=None):
    """Splice complete native-vector/JSON-array forests without reordering.

    End indices in the incoming forest are local absolute indices within that
    forest. Empty replacement has count=length=0. A safe metadata-only block
    retry capacity is old_state_capacity+value_capacity.
    """
    B = state.lane_count
    for value in (roots, begins, remove_counts, value_counts): _check_tensor(state, value, (B,), torch.int64)
    zero = torch.zeros_like(roots)
    controls = torch.stack((roots, zero, zero, begins, remove_counts, value_counts), dim=1)
    return _build(state, roots, controls, values, value_lengths, selected, 2, capacity)


def commit_container_edits(build, *, capacity=None):
    """Atomically commit built container blocks, preserving complete rollback.

    Output state capacity must retain the original allocation. If either the
    builder or generic editor fails, every selected lane remains unchanged.
    No-op lanes are accepted without rewriting their source records.
    """
    if not isinstance(build, ContainerBuildResult): raise TypeError("Expected complete container build")
    healthy = ~(build.errors != 0).any()
    edit = replace_subtrees(build.source, build.roots, build.blocks, build.lengths,
                            build.selected & build.changed & healthy, capacity=capacity)
    committed = healthy & edit.committed
    accepted = build.selected & committed
    return ContainerEditResult(edit.state, build, build.errors | (edit.errors << 8), edit.errors,
        edit.required_capacity, accepted, committed, build.changed & accepted)
