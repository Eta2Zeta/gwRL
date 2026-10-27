"""Transactional resident subtree replacement for the complete state arena.

This internal structural operation is not action legality or a full campaign
transition. A rule handler supplies an already computed complete replacement.
Every other field and random bit survives. Allocation capacity is explicit:
insufficient space returns CAPACITY and the original state, never truncation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch, SECTION_NAMES
from .metal_state_schema import METAL_STATE_SOURCE


class EditError(IntFlag):
    SOURCE = 1
    TARGET = 2
    BLOCK = 4
    CAPACITY = 8
    SECTIONS = 16


@dataclass(frozen=True)
class DeviceEditResult:
    state: DeviceStateBatch
    errors: torch.Tensor
    required_capacity: torch.Tensor
    accepted: torch.Tensor
    committed: torch.Tensor


SOURCE = "#include <metal_stdlib>\nusing namespace metal;\n" + METAL_STATE_SOURCE + r"""
inline bool edit_string_less(thread const PackedStateView& view, long first, long second, thread bool& valid) {
    if(first<0||second<0||first>=view.prefix_count+view.suffix_count||second>=view.prefix_count+view.suffix_count){valid=false;return false;}
    bool ap=first<view.prefix_count,bp=second<view.prefix_count;
    long ai=ap?first:first-view.prefix_count,bi=bp?second:second-view.prefix_count;
    device const long* ao=ap?view.prefix_offsets:view.suffix_offsets;
    device const long* bo=bp?view.prefix_offsets:view.suffix_offsets;
    device const uchar* ab=ap?view.prefix_bytes:view.suffix_bytes;
    device const uchar* bb=bp?view.prefix_bytes:view.suffix_bytes;
    long as=ao[ai],ae=ao[ai+1],bs=bo[bi],be=bo[bi+1];
    if(as<0||ae<as||ae>(ap?view.prefix_bytes_length:view.suffix_bytes_length)||
       bs<0||be<bs||be>(bp?view.prefix_bytes_length:view.suffix_bytes_length)){valid=false;return false;}
    long count=min(ae-as,be-bs);
    for(long i=0;i<count;++i){if(ab[as+i]!=bb[bs+i])return ab[as+i]<bb[bs+i];}
    return ae-as<be-bs;
}
inline bool edit_tree(thread const PackedStateView& view, device long* ends,device long* remaining,device long* previous) {
    if(view.length<=0||view.length>view.capacity)return false;
    long depth=0;
    for(long i=0;i<view.length;++i){
        while(depth&&i==ends[depth-1]){if(remaining[depth-1])return false;--depth;}
        if(i&&depth==0)return false;
        device const long* row=state_record(view,i);
        long tag=row[0],count=row[1],end=row[4],children=0;
        if(tag<0||tag>13||count<0||row[2]<0||row[2]>0xffffffffL||row[3]<0||row[3]>0xffffffffL||end<=i||end>view.length)return false;
        if(depth){
            long parent=depth-1;
            if(i>=ends[parent]||end>ends[parent]||remaining[parent]<=0)return false;
            long parent_index=previous[view.capacity+parent];
            long parent_tag=state_record(view,parent_index)[0];
            bool key=(parent_tag==7||parent_tag==13)&&remaining[parent]%2==0;
            bool set=parent_tag==8;
            if(key&&tag!=5)return false;
            if(set&&tag!=5&&tag!=2)return false;
            if(key||set){
                long last=previous[parent];
                if(last>=0){
                    device const long* old=state_record(view,last);
                    if(old[0]!=tag)return false;
                    if(tag==5){bool valid=true;if(!edit_string_less(view,old[1],count,valid)||!valid)return false;}
                    else {bool valid=true;if(state_signed_value(view,last,valid)>=state_signed_value(view,i,valid)||!valid)return false;}
                }
                previous[parent]=i;
            }
            --remaining[parent];
        }
        if(tag==0){if(count||row[2]||row[3])return false;}
        else if(tag==1){if(count>1||row[2]||row[3])return false;}
        else if(tag==2){
            if(count||!((row[3]==0&&row[2]<=0x7fffffffL)||(row[3]==0xffffffffL&&row[2]>=0x80000000L)))return false;
        } else if(tag==3){if(count)return false;}
        else if(tag==4){if(count||(ulong(row[3])&0x7ff00000UL)==0x7ff00000UL)return false;}
        else if(tag==5){if(count>=view.prefix_count+view.suffix_count||row[2]||row[3])return false;}
        else {
            if(row[2]||row[3]||count>view.length)return false;
            if(tag==9&&count>1)return false;
            if(tag==11&&count!=2)return false;
            children=(tag==7||tag==13)?count*2:count;
            if(children>view.length-i-1)return false;
        }
        if(children){
            if(depth>=view.capacity)return false;
            ends[depth]=end;remaining[depth]=children;previous[depth]=-1;previous[view.capacity+depth]=i;++depth;
        }else if(end!=i+1)return false;
    }
    while(depth&&view.length==ends[depth-1]){if(remaining[depth-1])return false;--depth;}
    return depth==0;
}
inline bool edit_sections(thread const PackedStateView& view,device long* out){
    bool valid=true;
    if(!state_node(view,0))return false;
    device const long* root=state_record(view,0);
    if(root[0]!=10||root[1]!=2||root[2]||root[3]||root[4]!=view.length)return false;
    long state=state_child(view,0,0,valid),random=state_child(view,0,1,valid);
    if(!valid||state_record(view,state)[0]!=10||state_record(view,state)[1]!=19||
       state_record(view,random)[0]!=10||state_record(view,random)[1]!=6)return false;
    out[0]=state;out[1]=random;
    for(long i=0;i<19;++i)out[2+i]=state_child(view,state,i,valid);
    for(long i=0;i<6;++i)out[21+i]=state_child(view,random,i,valid);
    return valid;
}
kernel void edit_subtrees(
 device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],
 device const long* source_errors [[buffer(2)]],device const long* roots [[buffer(3)]],
 device const long* blocks [[buffer(4)]],device const long* block_lengths [[buffer(5)]],
 device const bool* selected [[buffer(6)]],device long* output [[buffer(7)]],
 device long* output_lengths [[buffer(8)]],device long* output_sections [[buffer(9)]],
 device long* errors [[buffer(10)]],device long* required [[buffer(11)]],
 device long* stack_ends [[buffer(12)]],device long* stack_remaining [[buffer(13)]],
 device long* stack_previous [[buffer(14)]],device const long* dims [[buffer(15)]],
 device const uchar* prefix_bytes [[buffer(16)]],device const long* prefix_offsets [[buffer(17)]],
 device const uchar* suffix_bytes [[buffer(18)]],device const long* suffix_offsets [[buffer(19)]],
 device const long* suffix_usage [[buffer(20)]],uint lane [[thread_position_in_grid]]) {
 long B=dims[0],C=dims[1],O=dims[2],R=dims[3];if(ulong(lane)>=ulong(B))return;
 long old_length=lengths[lane],root=roots[lane],n=block_lengths[lane],error=0;
 device const long* old=records+ulong(lane)*ulong(C)*5;
 device const long* block=blocks+ulong(lane)*ulong(R)*5;
 device long* dest=output+ulong(lane)*ulong(O)*5;
 errors[lane]=0;required[lane]=old_length;output_lengths[lane]=old_length;
 for(long i=0;i<O*5;++i)dest[i]=i<C*5?old[i]:0;
 if(!selected[lane])return;
 bool usage_valid=true;
 PackedStateView before=make_packed_state_view(old,old_length,C,prefix_bytes,prefix_offsets,dims[4],dims[5],suffix_bytes,suffix_offsets,dims[6],dims[7],suffix_usage,usage_valid);
 if(!usage_valid||source_errors[lane]||old_length<=0||old_length>C)error|=1;
 if(!error&&(!state_node(before,root)||old[root*5+4]<=root||old[root*5+4]>old_length))error|=2;
 if(n<=0||n>R)error|=4;
 long end=0,delta=0,total=old_length;
 if(!error){
   PackedStateView replacement=before;replacement.records=block;replacement.length=n;replacement.capacity=R;
   if(!edit_tree(replacement,stack_ends+ulong(lane)*ulong(R),stack_remaining+ulong(lane)*ulong(R),stack_previous+ulong(lane)*ulong(R)*2))error|=4;
   if(!dims[8]&&block[0]!=old[root*5])error|=4;
   if((old[root*5]==10||old[root*5]==11)&&block[1]!=old[root*5+1])error|=4;
   end=old[root*5+4];delta=n-(end-root);total=old_length+delta;required[lane]=total;
   if(total>O)error|=8;
 }
 if(!error){
   for(long i=0;i<total;++i){
     if(i>=root&&i<root+n){for(long col=0;col<5;++col)dest[i*5+col]=block[(i-root)*5+col];dest[i*5+4]+=root;}
     else {long source=i<root?i:i-delta;for(long col=0;col<5;++col)dest[i*5+col]=old[source*5+col];if(dest[i*5+4]>root)dest[i*5+4]+=delta;}
   }
   for(long i=total*5;i<O*5;++i)dest[i]=0;
   PackedStateView after=before;after.records=dest;after.length=total;after.capacity=O;
   if(!edit_sections(after,output_sections+ulong(lane)*27))error|=16;
   output_lengths[lane]=total;
 }
 errors[lane]=error;
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


def _layout(state, roots, blocks, block_lengths, selected, capacity):
    if not isinstance(state, DeviceStateBatch):
        raise TypeError("Expected complete resident state")
    state._metadata()
    B, C = state.records.shape[:2]
    if capacity is None:
        capacity = C
    if type(capacity) is not int or capacity < C:
        raise ValueError("Output capacity must retain the full original allocation for rollback")
    if not isinstance(blocks, torch.Tensor) or blocks.ndim != 3 or blocks.shape[0] != B or blocks.shape[2] != 5:
        raise ValueError("Replacement blocks must have [lane,allocated_capacity,5] shape")
    values = ((roots, (B,), torch.int64), (blocks, tuple(blocks.shape), torch.int64),
              (block_lengths, (B,), torch.int64), (selected, (B,), torch.bool))
    for value, shape, dtype in values:
        if (not isinstance(value, torch.Tensor) or value.device != state.device or value.dtype != dtype or
                tuple(value.shape) != shape or not value.is_contiguous()):
            raise ValueError("Edits require complete contiguous resident buffers and exact native dtypes")
    if any(not value.is_contiguous() for value in (state.records, state.lengths, state.errors,
            state.context.string_bytes, state.context.string_offsets, state.string_bytes, state.string_offsets)):
        raise ValueError("Packed editor requires contiguous buffers; no hidden conversion")
    return B, C, capacity, blocks.shape[1]


def _strings(state):
    tables = []
    used_strings, used_bytes = state.suffix_usage.tolist()
    for raw, offsets in ((state.context.string_bytes, state.context.string_offsets),
                         (state.string_bytes[:used_bytes], state.string_offsets[:used_strings+1])):
        data, indices = bytes(raw.tolist()), offsets.tolist()
        tables.extend(data[a:b] for a, b in zip(indices, indices[1:]))
    return tables


def _host_tree(rows, strings):
    """Independent scalar CPU reference; never used by the MPS implementation."""
    stack = []
    for i, row in enumerate(rows):
        while stack and stack[-1][0] == i:
            if stack[-1][1]: return False
            stack.pop()
        if i and not stack: return False
        tag, count, low, high, end = row
        if not 0 <= tag <= 13 or count < 0 or not 0 <= low <= 0xffffffff or not 0 <= high <= 0xffffffff or not i < end <= len(rows): return False
        if stack:
            parent = stack[-1]
            if end > parent[0] or parent[1] <= 0: return False
            key = parent[3] in (7, 13) and parent[1] % 2 == 0
            if key or parent[3] == 8:
                if tag not in ((5,) if key else (2, 5)): return False
                if tag == 5 and count >= len(strings): return False
                value = strings[count] if tag == 5 and count < len(strings) else (low | high << 32)
                if tag == 2 and value >= 1 << 63: value -= 1 << 64
                if parent[2] is not None and (parent[4] != tag or not parent[2] < value): return False
                parent[2], parent[4] = value, tag
            parent[1] -= 1
        children = 0
        if tag == 0 and (count or low or high): return False
        if tag == 1 and (count > 1 or low or high): return False
        if tag == 2 and (count or not ((high == 0 and low <= 0x7fffffff) or (high == 0xffffffff and low >= 0x80000000))): return False
        if tag == 3 and count: return False
        if tag == 4 and (count or high & 0x7ff00000 == 0x7ff00000): return False
        if tag == 5 and (count >= len(strings) or low or high): return False
        if tag >= 6:
            if low or high or count > len(rows) or (tag == 9 and count > 1) or (tag == 11 and count != 2): return False
            children = count * 2 if tag in (7, 13) else count
            if children > len(rows) - i - 1: return False
        if children: stack.append([end, children, None, tag, None])
        elif end != i + 1: return False
    while stack and stack[-1][0] == len(rows):
        if stack[-1][1]: return False
        stack.pop()
    return not stack and bool(rows)


def _host_sections(rows):
    def children(root, count):
        if not 0 <= root < len(rows) or rows[root][:2] != [10, count]: raise ValueError("Bad sections")
        values, cursor = [], root + 1
        for _ in range(count):
            if not root < cursor < len(rows): raise ValueError("Truncated sections")
            values.append(cursor); end = rows[cursor][4]
            if not cursor < end <= rows[root][4]: raise ValueError("Bad section end")
            cursor = end
        if cursor != rows[root][4]: raise ValueError("Unknown sections")
        return values
    roots = children(0, 2)
    if rows[0][4] != len(rows): raise ValueError("Trailing state")
    return roots + children(roots[0], 19) + children(roots[1], 6)


def _cpu_candidate(state, roots, blocks, block_lengths, selected, capacity, allow_type_change):
    used_strings, used_bytes = state.suffix_usage.tolist()
    valid_usage = (0 <= used_strings < state.string_offsets.numel() and 0 <= used_bytes <= state.string_bytes.numel() and
                   state.string_offsets[0].item() == 0 and state.string_offsets[used_strings].item() == used_bytes)
    strings, raw, patches = (_strings(state) if valid_usage else []), state.records.tolist(), blocks.tolist()
    lengths, indexes, sizes = state.lengths.tolist(), roots.tolist(), block_lengths.tolist()
    enabled, inherited = selected.tolist(), state.errors.tolist()
    output, sections, errors, required, next_lengths = [], [], [], [], []
    for lane, (source, start, size, active) in enumerate(zip(raw, indexes, sizes, enabled)):
        original = [list(row) for row in source[:lengths[lane]]]
        rows, error, needed = original, 0, lengths[lane]
        if active:
            if not valid_usage or inherited[lane] or not 0 < lengths[lane] <= state.records.shape[1]: error |= EditError.SOURCE
            if not error and not (0 <= start < len(original) and start < original[start][4] <= len(original)): error |= EditError.TARGET
            if not 0 < size <= blocks.shape[1]: error |= EditError.BLOCK
            if not error:
                replacement = [list(row) for row in patches[lane][:size]]
                if not _host_tree(replacement, strings): error |= EditError.BLOCK
                if not allow_type_change and replacement[0][0] != original[start][0]: error |= EditError.BLOCK
                if original[start][0] in (10, 11) and replacement[0][1] != original[start][1]: error |= EditError.BLOCK
                end = original[start][4]; delta = size - (end - start); needed = len(original) + delta
                if needed > capacity: error |= EditError.CAPACITY
                if not error:
                    rows = []
                    for source_index, row in enumerate(original):
                        if source_index == start:
                            rows.extend([[*value[:4], value[4] + start] for value in replacement])
                        if start <= source_index < end: continue
                        rows.append([*row[:4], row[4] + (delta if row[4] > start else 0)])
        try: section = _host_sections(rows)
        except (ValueError, IndexError): error |= EditError.SECTIONS; section = state.sections[lane].tolist()
        output.append(rows + [[0]*5 for _ in range(max(0, capacity - len(rows)))])
        sections.append(section); errors.append(int(error)); required.append(needed); next_lengths.append(len(rows))
    B = state.lane_count
    return (torch.tensor(output, dtype=torch.int64).reshape(B, capacity, 5),
            torch.tensor(next_lengths, dtype=torch.int64), torch.tensor(sections, dtype=torch.int64).reshape(B, 27),
            torch.tensor(errors, dtype=torch.int64), torch.tensor(required, dtype=torch.int64))


def replace_subtrees(state, roots, blocks, block_lengths, selected, *, capacity=None, allow_type_change=False, implementation=None):
    """Replace one complete subtree per selected lane, atomically as a cohort.

    A safe metadata-only retry capacity is old_capacity + block_capacity. This
    operation never reads GPU values on the host or silently grows/truncates them.
    Record/Pair arity at the replacement root is preserved even if a trusted
    caller explicitly allows JSON type changes. The rule handler remains
    responsible for nested native field types and complete game invariants.
    """
    B, C, O, R = _layout(state, roots, blocks, block_lengths, selected, capacity)
    if type(allow_type_change) is not bool: raise ValueError("Type-change permission must be explicit bool")
    strategy=state.context.editor_implementation if implementation is None else implementation
    if type(strategy) is not str or strategy not in {"reference","parallel"}:
        raise ValueError("State editor implementation must be reference or parallel")
    if strategy=="parallel" and state.device.type!="mps":
        raise ValueError("Parallel resident editing requires explicit Apple GPU execution")
    if state.device.type == "cpu":
        candidate, lengths, sections, errors, required = _cpu_candidate(state, roots, blocks, block_lengths, selected, O, allow_type_change)
    elif state.device.type == "mps" and strategy=="parallel":
        from .device_state_edits_parallel import _candidate
        candidate,lengths,sections,errors,required=_candidate(state,roots,blocks,block_lengths,selected,(B,C,O,R),allow_type_change)
    elif state.device.type == "mps":
        global _library
        candidate = torch.empty((B, O, 5), dtype=torch.int64, device=state.device)
        lengths, sections = torch.empty_like(state.lengths), torch.empty_like(state.sections)
        errors, required = torch.zeros_like(state.errors), torch.empty_like(state.lengths)
        if B:
            if _library is None:
                with _lock:
                    if _library is None: _library = torch.mps.compile_shader(SOURCE)
            scratch = [torch.empty((B, max(1, R) * factor), dtype=torch.int64, device=state.device) for factor in (1, 1, 2)]
            tensors = (state.records, state.lengths, state.errors, roots, blocks, block_lengths, selected,
                candidate, lengths, sections, errors, required, *scratch,
                _dimensions((B, C, O, R, state.context.string_count, state.context.string_bytes.numel(),
                             state.string_offsets.numel()-1, state.string_bytes.numel(), int(allow_type_change))),
                state.context.string_bytes, state.context.string_offsets, state.string_bytes, state.string_offsets, state.suffix_usage)
            _library.edit_subtrees(*(value if value.numel() else _dummy() for value in tensors), threads=B)
    else:
        raise ValueError("Packed edits require explicit CPU reference or Apple MPS; no fallback")
    errors = torch.where(selected, errors, 0)
    committed = ~(errors != 0).any()
    accepted = selected & committed
    baseline = torch.cat((state.records, torch.zeros((B, O-C, 5), dtype=torch.int64, device=state.device)), dim=1) if O>C else state.records
    result = DeviceStateBatch(state.context, torch.where(accepted[:, None, None], candidate, baseline),
        torch.where(accepted, lengths, state.lengths), torch.where(accepted[:, None], sections, state.sections),
        state.string_bytes, state.string_offsets, state.errors, state.suffix_usage)
    return DeviceEditResult(result, errors, required, accepted, committed)
