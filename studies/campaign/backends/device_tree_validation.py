"""Exact source-tree grammar validation with one Metal thread per node.

Every node checks its own scalar/header rules; a container visits only its
direct children. Exact interval coverage and increasing child ends establish
the same nesting as the serial stack validator. This does not validate native
State schemas, inspect unused string bytes, normalize data or cache results.
"""
from dataclasses import dataclass
import threading

import torch

from .device_state import DeviceStateBatch, _device
from .device_state_edits import SOURCE as REFERENCE_SOURCE


@dataclass(frozen=True)
class SourceTreeValidation:
    source: DeviceStateBatch
    valid: torch.Tensor        # bool [lane]; inactive lanes are valid.
    node_errors: torch.Tensor  # int32 [lane,max(capacity,1)], 1=invalid node.


_MARKER="kernel void edit_subtrees("
if REFERENCE_SOURCE.count(_MARKER)!=1:raise RuntimeError("Audited source-tree grammar helper changed")
SOURCE = REFERENCE_SOURCE.split(_MARKER, 1)[0] + r'''
kernel void validate_source_nodes(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* inherited[[buffer(2)]],device const bool* selected[[buffer(3)]],
 device const uchar* prefix[[buffer(4)]],device const long* poffsets[[buffer(5)]],
 device const uchar* suffix[[buffer(6)]],device const long* soffsets[[buffer(7)]],
 device const long* usage[[buffer(8)]],device int* errors[[buffer(9)]],
 device const long* dims[[buffer(10)]],uint row[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],P=dims[2],lane=long(row)/P,i=long(row)%P;
 if(lane>=B)return;errors[row]=0;if(!selected[lane])return;
 const long length=lengths[lane];bool valid=true;
 auto view=make_packed_state_view(records+ulong(lane)*C*5,length,C,prefix,poffsets,dims[3],dims[4],
   suffix,soffsets,dims[5],dims[6],usage,valid);
 if(!valid||inherited[lane]||length<=0||length>C){if(!i)errors[row]=1;return;}
 if(i>=length)return;
 device const long* node=state_record(view,i);
 const long tag=node[0],count=node[1],low=node[2],high=node[3],end=node[4];
 if(tag<0||tag>13||count<0||low<0||low>0xffffffffL||high<0||high>0xffffffffL||
    end<=i||end>length||(!i&&end!=length)){errors[row]=1;return;}
 long children=0;
 if(tag==0){if(count||low||high){errors[row]=1;return;}}
 else if(tag==1){if(count>1||low||high){errors[row]=1;return;}}
 else if(tag==2){
   if(count||!((high==0&&low<=0x7fffffffL)||(high==0xffffffffL&&low>=0x80000000L))){errors[row]=1;return;}
 }else if(tag==3){if(count){errors[row]=1;return;}}
 else if(tag==4){if(count||(ulong(high)&0x7ff00000UL)==0x7ff00000UL){errors[row]=1;return;}}
 else if(tag==5){if(count>=view.prefix_count+view.suffix_count||low||high){errors[row]=1;return;}}
 else{
   if(low||high||count>length||(tag==9&&count>1)||(tag==11&&count!=2)){errors[row]=1;return;}
   children=(tag==7||tag==13)?count*2:count;
   if(children>length-i-1){errors[row]=1;return;}
 }
 if(!children){if(end!=i+1)errors[row]=1;return;}
 long cursor=i+1,previous=-1,previous_tag=-1;
 for(long child=0;child<children;++child){
   // Bound every independent walk before touching its candidate child.
   if(cursor<=i||cursor>=end||!state_node(view,cursor)){errors[row]=1;return;}
   device const long* entry=state_record(view,cursor);
   const long child_end=entry[4],child_tag=entry[0];
   if(child_end<=cursor||child_end>end||child_end>length){errors[row]=1;return;}
   const bool key=(tag==7||tag==13)&&child%2==0,set=tag==8;
   if(key||set){
     if((key&&child_tag!=5)||(set&&child_tag!=2&&child_tag!=5)){errors[row]=1;return;}
     if(previous>=0){
       if(previous_tag!=child_tag){errors[row]=1;return;}
       bool ordered=true;
       if(child_tag==5){
         if(!edit_string_less(view,state_record(view,previous)[1],entry[1],ordered)||!ordered){errors[row]=1;return;}
       }else{
         const long old_value=state_signed_value(view,previous,ordered);
         const long new_value=state_signed_value(view,cursor,ordered);
         if(!ordered||old_value>=new_value){errors[row]=1;return;}
       }
     }
     previous=cursor;previous_tag=child_tag;
   }
   cursor=child_end;
 }
 if(cursor!=end)errors[row]=1;
}
'''

_lock = threading.Lock()
_library = None


def validate_source(state, selected):
    """Validate actual selected nodes on MPS without reading execution values.

    Bad usage, inherited errors and invalid lengths mark node zero, even with
    zero physical record capacity. Inactive lanes and padding have zero errors.
    Strings are ID-checked only; byte offsets are checked lazily by ordering,
    exactly as the original edit_tree predicate.
    """
    global _library
    if not isinstance(state, DeviceStateBatch): raise TypeError("Expected complete resident tree buffers")
    state._metadata(); _device(state.device)
    if state.device.type != "mps": raise ValueError("Parallel source validation requires explicit Apple GPU; no CPU fallback")
    B, C = state.records.shape[:2]; P = max(C, 1)
    if (not isinstance(selected, torch.Tensor) or selected.dtype != torch.bool or selected.device != state.device or
        selected.shape != (B,) or not selected.is_contiguous()):
        raise ValueError("Source validation selection must be contiguous resident bool[lane]")
    context = state.context
    if (type(context.string_count) is not int or context.string_count < 0 or
        context.string_bytes.dtype != torch.uint8 or context.string_bytes.ndim != 1 or
        context.string_offsets.dtype != torch.int64 or context.string_offsets.shape != (context.string_count + 1,)):
        raise ValueError("Source validation requires the exact static string buffer layout")
    inputs = (state.records, state.lengths, state.errors, selected, context.string_bytes, context.string_offsets,
              state.string_bytes, state.string_offsets, state.suffix_usage)
    if any(value.device != state.device or not value.is_contiguous() for value in inputs):
        raise ValueError("Source validation buffers must remain contiguous on their explicit device")
    if B * P > (1 << 32) - 1: raise OverflowError("Source node grid cannot be represented; no nodes truncated")
    errors = torch.empty((B, P), dtype=torch.int32, device=state.device)
    if B:
        if _library is None:
            with _lock:
                if _library is None: _library = torch.mps.compile_shader(SOURCE)
        dims = torch.tensor((B, C, P, context.string_count, context.string_bytes.numel(),
                             state.string_offsets.numel() - 1, state.string_bytes.numel()), dtype=torch.int64, device=state.device)
        dummy = torch.empty(1, dtype=torch.int64, device=state.device)
        _library.validate_source_nodes(*(value if value.numel() else dummy for value in (*inputs, errors, dims)), threads=B * P)
    return SourceTreeValidation(state, (errors == 0).all(dim=1), errors)
