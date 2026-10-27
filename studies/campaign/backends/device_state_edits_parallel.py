"""Parallel arena copy for the exact existing subtree replacement contract.

The reference-container policy keeps serial replacement grammar validation;
the parallel-container policy recomputes the equivalent per-node predicate.
Section discovery and all plan checks keep their original behavior, while arena
copy/relocation is distributed over records. Cohort publication is unchanged.
"""
import threading

import torch

from .device_state_edits import SOURCE as REFERENCE_SOURCE, _dimensions, _dummy


_MARKER="kernel void edit_subtrees("
if REFERENCE_SOURCE.count(_MARKER)!=1:raise RuntimeError("Audited subtree editor kernel changed")
SOURCE=REFERENCE_SOURCE.split(_MARKER,1)[0]+r'''
kernel void parallel_edit_plan(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* source_errors[[buffer(2)]],
 device const long* roots[[buffer(3)]],device const long* blocks[[buffer(4)]],device const long* block_lengths[[buffer(5)]],
 device const bool* selected[[buffer(6)]],device long* lengths_out[[buffer(7)]],device long* errors[[buffer(8)]],
 device long* required[[buffer(9)]],device long* plans[[buffer(10)]],device long* stack_ends[[buffer(11)]],
 device long* stack_remaining[[buffer(12)]],device long* stack_previous[[buffer(13)]],device const long* dims[[buffer(14)]],
 device const uchar* prefix_bytes[[buffer(15)]],device const long* prefix_offsets[[buffer(16)]],
 device const uchar* suffix_bytes[[buffer(17)]],device const long* suffix_offsets[[buffer(18)]],
 device const long* suffix_usage[[buffer(19)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],O=dims[2],R=dims[3];if(long(lane)>=B)return;
 const long old_length=lengths[lane],root=roots[lane],n=block_lengths[lane];long error=0;
 device const long* old=records+ulong(lane)*C*5;device const long* block=blocks+ulong(lane)*R*5;
 errors[lane]=0;required[lane]=lengths_out[lane]=old_length;
 device long* plan=plans+ulong(lane)*4;plan[0]=root;plan[1]=n;plan[2]=0;plan[3]=old_length;
 if(!selected[lane])return;
 bool usage_valid=true;
 PackedStateView before=make_packed_state_view(old,old_length,C,prefix_bytes,prefix_offsets,dims[4],dims[5],
   suffix_bytes,suffix_offsets,dims[6],dims[7],suffix_usage,usage_valid);
 if(!usage_valid||source_errors[lane]||old_length<=0||old_length>C)error|=1;
 if(!error&&(!state_node(before,root)||old[root*5+4]<=root||old[root*5+4]>old_length))error|=2;
 if(n<=0||n>R)error|=4;
 if(!error){
   PackedStateView replacement=before;replacement.records=block;replacement.length=n;replacement.capacity=R;
   if(!edit_tree(replacement,stack_ends+ulong(lane)*R,stack_remaining+ulong(lane)*R,stack_previous+ulong(lane)*R*2))error|=4;
   if(!dims[8]&&block[0]!=old[root*5])error|=4;
   if((old[root*5]==10||old[root*5]==11)&&block[1]!=old[root*5+1])error|=4;
   const long delta=n-(old[root*5+4]-root),total=old_length+delta;
   plan[2]=delta;plan[3]=total;required[lane]=total;
   if(total>O)error|=8;
 }
 if(!error)lengths_out[lane]=plan[3];errors[lane]=error;
}
kernel void parallel_edit_copy(device const long* records[[buffer(0)]],device const long* blocks[[buffer(1)]],
 device const bool* selected[[buffer(2)]],device const long* plans[[buffer(3)]],device const long* errors[[buffer(4)]],
 device long* output[[buffer(5)]],device const long* dims[[buffer(6)]],uint row[[thread_position_in_grid]]){
 const long C=dims[1],O=dims[2],R=dims[3],lane=long(row)/O,i=long(row)%O;if(lane>=dims[0])return;
 device const long* old=records+ulong(lane)*C*5;device long* dest=output+ulong(row)*5;
 if(!selected[lane]||errors[lane]){for(long c=0;c<5;++c)dest[c]=i<C?old[ulong(i)*5+c]:0;return;}
 device const long* plan=plans+ulong(lane)*4;const long root=plan[0],n=plan[1],delta=plan[2],total=plan[3];
 if(i>=total){for(long c=0;c<5;++c)dest[c]=0;return;}
 if(i>=root&&i<root+n){device const long* source=blocks+(ulong(lane)*R+i-root)*5;
   for(long c=0;c<5;++c)dest[c]=source[c];dest[4]+=root;
 }else{const long at=i<root?i:i-delta;device const long* source=old+ulong(at)*5;
   for(long c=0;c<5;++c)dest[c]=source[c];if(dest[4]>root)dest[4]+=delta;}
}
kernel void parallel_edit_sections(device const long* output[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const bool* selected[[buffer(2)]],device long* errors[[buffer(3)]],device long* sections[[buffer(4)]],
 device const long* dims[[buffer(5)]],device const uchar* prefix_bytes[[buffer(6)]],device const long* prefix_offsets[[buffer(7)]],
 device const uchar* suffix_bytes[[buffer(8)]],device const long* suffix_offsets[[buffer(9)]],
 device const long* suffix_usage[[buffer(10)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0]||!selected[lane]||errors[lane])return;
 bool valid=true;auto after=make_packed_state_view(output+ulong(lane)*dims[2]*5,lengths[lane],dims[2],
   prefix_bytes,prefix_offsets,dims[4],dims[5],suffix_bytes,suffix_offsets,dims[6],dims[7],suffix_usage,valid);
 // The original kernel had already checked these same immutable pool values.
 if(!valid||!edit_sections(after,sections+ulong(lane)*27))errors[lane]|=16;
}
'''

# Preserve the original plan as a selectable reference. The second plan changes
# only its grammar predicate and adds one read-only bool input. Bounds, lazy
# consultation, combined error bits and required-size calculation stay in place.
_PLAN_BEGIN = "kernel void parallel_edit_plan("
_PLAN_END = "kernel void parallel_edit_copy("
_plan = SOURCE[SOURCE.index(_PLAN_BEGIN):SOURCE.index(_PLAN_END)]
_predicate = "edit_tree(replacement,stack_ends+ulong(lane)*R,stack_remaining+ulong(lane)*R,stack_previous+ulong(lane)*R*2)"
_signature = "device const long* suffix_usage[[buffer(19)]],uint lane[[thread_position_in_grid]]){"
if _plan.count(_predicate) != 1 or _plan.count(_signature) != 1:
    raise RuntimeError("Audited parallel replacement plan changed")
_validated_plan = _plan.replace(_PLAN_BEGIN, "kernel void parallel_edit_plan_validated(", 1)
_validated_plan = _validated_plan.replace(_signature,
    "device const long* suffix_usage[[buffer(19)]],device const bool* replacement_valid[[buffer(20)]],uint lane[[thread_position_in_grid]]){", 1)
_validated_plan = _validated_plan.replace(_predicate, "replacement_valid[lane]", 1)
if any(name in _validated_plan.split("){", 1)[1] for name in ("stack_ends", "stack_remaining", "stack_previous")):
    raise RuntimeError("Validated replacement plan still uses scratch stacks")
SOURCE += _validated_plan

_lock=threading.Lock()
_library=None


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    return _library


def _candidate(state,roots,blocks,block_lengths,selected,layout,allow_type_change):
    B,C,O,R=layout
    if B*O>(1<<32)-1:raise OverflowError("Parallel edit grid cannot be represented; no records truncated")
    candidate=torch.empty((B,O,5),dtype=torch.int64,device=state.device)
    lengths=torch.empty_like(state.lengths);sections=torch.empty_like(state.sections)
    errors=torch.zeros_like(state.errors);required=torch.empty_like(state.lengths)
    if B:
        library=_kernels();plans=torch.empty((B,4),dtype=torch.int64,device=state.device)
        validated=getattr(state.context,"container_implementation","reference")=="parallel"
        if validated:
            from .device_state_edits_validated import validate_replacement
            checked=validate_replacement(state,blocks,block_lengths,selected)
            # Generated plan body has no stack references; validities remain
            # resident until its original replacement-grammar branch.
            scratch=(_dummy(),)*3
            plan_kernel=library.parallel_edit_plan_validated
        else:
            scratch=[torch.empty((B,max(1,R)*factor),dtype=torch.int64,device=state.device) for factor in (1,1,2)]
            plan_kernel=library.parallel_edit_plan
        dims=_dimensions((B,C,O,R,state.context.string_count,state.context.string_bytes.numel(),
            state.string_offsets.numel()-1,state.string_bytes.numel(),int(allow_type_change)))
        pools=(state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage)
        def call(kernel,args,count):
            if count:kernel(*(value if value.numel() else _dummy() for value in args),threads=count)
        plan_args=(state.records,state.lengths,state.errors,roots,blocks,block_lengths,selected,
            lengths,errors,required,plans,*scratch,dims,*pools)
        call(plan_kernel,(*plan_args,checked.valid) if validated else plan_args,B)
        call(library.parallel_edit_copy,(state.records,blocks,selected,plans,errors,candidate,dims),B*O)
        call(library.parallel_edit_sections,(candidate,lengths,selected,errors,sections,dims,*pools),B)
    return candidate,lengths,sections,errors,required
