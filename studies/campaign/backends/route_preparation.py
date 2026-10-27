"""One-slab, one-dispatch route preparation using the audited reference bodies.

All complete relation/declaration diagnostics and route indexes are retained as
contiguous disjoint views. The source identity is the complete immutable native
snapshot, including calendar, politics, pending continuations and string pool.
This changes allocation and scheduling only; no board-only cache is introduced.
"""
from functools import lru_cache
import re
import threading

import torch

from .resident_relations import PoliticalRelationsBatch, SOURCE as RELATIONS_SOURCE
from .resident_declarations import LandAttackDeclarations, SOURCE as DECLARATION_SOURCE


FIELDS=("metadata","pairs","pair_errors","nations","nation_errors","present",
        "permission_scratch","declarations","declaration_errors","presence","indexes")
ROUTE_DIMS,RELATION_DIMS,DECLARATION_DIMS,STATIC_COUNT=26,9,12,6
STATIC_START=ROUTE_DIMS+RELATION_DIMS+DECLARATION_DIMS
OUTPUT_START=STATIC_START+STATIC_COUNT


def _kernel_parts(source,name):
    """Extract one known kernel, respecting braces in strings and comments."""
    prefix="kernel void "+name+"("
    if source.count(prefix)!=1:raise RuntimeError("Audited preparation kernel marker changed: "+name)
    signature,tail=source.split(prefix,1)[1].split(") {",1)
    level=1;mode="code";escaped=False;position=0
    while position<len(tail):
        char=tail[position];following=tail[position+1] if position+1<len(tail) else ""
        if mode=="line":
            if char=="\n":mode="code"
        elif mode=="comment":
            if char=="*" and following=="/":mode="code";position+=1
        elif mode in {"single","double"}:
            if escaped:escaped=False
            elif char=="\\":escaped=True
            elif char==("'" if mode=="single" else '"'):mode="code"
        elif char=="/" and following=="/":mode="line";position+=1
        elif char=="/" and following=="*":mode="comment";position+=1
        elif char=="'":mode="single"
        elif char=='"':mode="double"
        elif char=="{":level+=1
        elif char=="}":
            level-=1
            if level==0:return re.sub(r"\[\[.*?\]\]","",signature),tail[:position]
        position+=1
    raise RuntimeError("Audited preparation kernel has no balanced end: "+name)


def build_source(route_source):
    relation_sig,relation_body=_kernel_parts(RELATIONS_SOURCE,"resident_relations_parallel")
    scratch="threadgroup long roots[5];threadgroup atomic_int invalid;"
    if relation_body.count(scratch)!=1:raise RuntimeError("Parallel relation scratch schema changed")
    relation_body=relation_body.replace(scratch,"").replace("&invalid","invalid_pointer")
    relation_sig+=",threadgroup long* roots,threadgroup atomic_int* invalid_pointer"
    declaration_sig,declaration_body=_kernel_parts(DECLARATION_SOURCE,"resident_land_attack_declarations")
    index_sig,index_body=_kernel_parts(route_source,"prepare_route_indexes")
    helpers=("\ninline void route_prepare_relations("+relation_sig+") {"+relation_body+"}\n"+
             "inline void route_prepare_declarations("+declaration_sig+") {"+declaration_body+"}\n"+
             "inline void route_prepare_indexes("+index_sig+") {"+index_body+"}\n")
    body=r'''
kernel void fused_route_preparation(
 device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],device const long* sections [[buffer(2)]],
 device const uchar* prefix_bytes [[buffer(3)]],device const long* prefix_offsets [[buffer(4)]],
 device const uchar* suffix_bytes [[buffer(5)]],device const long* suffix_offsets [[buffer(6)]],device const long* usage [[buffer(7)]],
 device const long* source_errors [[buffer(8)]],device const long* definition [[buffer(9)]],
 device const long* statics [[buffer(10)]],device long* output [[buffer(11)]],device const long* dims [[buffer(12)]],
 uint3 group [[threadgroup_position_in_grid]],uint tid [[thread_index_in_threadgroup]],uint3 group_size [[threads_per_threadgroup]]) {
    const long lane=long(group.x),B=dims[0],N=dims[3];if(lane>=B)return;
    device const long* data=statics+dims[STATIC_START];device const long* offsets=statics+dims[STATIC_START+1];
    device const long* ids=statics+dims[STATIC_START+2];device const long* geography=statics+dims[STATIC_START+3];
    device const long* home=statics+dims[STATIC_START+4];device const long* warlords=statics+dims[STATIC_START+5];
    device long* metadata=output+dims[OUTPUT_START];device long* pairs=output+dims[OUTPUT_START+1];
    device long* pair_errors=output+dims[OUTPUT_START+2];device long* nations=output+dims[OUTPUT_START+3];
    device long* nation_errors=output+dims[OUTPUT_START+4];device long* present=output+dims[OUTPUT_START+5];
    device long* permission=output+dims[OUTPUT_START+6];device long* allowed=output+dims[OUTPUT_START+7];
    device long* declaration_errors=output+dims[OUTPUT_START+8];device long* presence=output+dims[OUTPUT_START+9];
    device long* indexes=output+dims[OUTPUT_START+10];
    const long index_width=dims[9]+dims[2]+N+13;
    for(long i=tid;i<index_width;i+=long(group_size.x))indexes[ulong(lane)*index_width+i]=-1;
    threadgroup long relation_roots[5];threadgroup atomic_int relation_invalid;
    route_prepare_relations(records,lengths,prefix_bytes,prefix_offsets,suffix_bytes,suffix_offsets,usage,ids,
        definition,source_errors,metadata,pairs,pair_errors,nations,nation_errors,present,permission,
        dims+ROUTE_DIMS,group,tid,group_size,relation_roots,&relation_invalid);
    threadgroup_barrier(mem_flags::mem_threadgroup|mem_flags::mem_device);
    if(tid==0){
        route_prepare_declarations(records,lengths,prefix_bytes,prefix_offsets,suffix_bytes,suffix_offsets,usage,ids,
            definition,source_errors,metadata,pairs,pair_errors,geography,home,warlords,allowed,declaration_errors,presence,
            dims+ROUTE_DIMS+RELATION_DIMS,uint(lane));
        route_prepare_indexes(records,lengths,sections,prefix_bytes,prefix_offsets,suffix_bytes,suffix_offsets,usage,
            source_errors,data,offsets,indexes,dims,uint(lane));
    }
}
'''
    constants="\n".join(f"constant long {name}={value};" for name,value in
                         (("ROUTE_DIMS",ROUTE_DIMS),("RELATION_DIMS",RELATION_DIMS),
                          ("STATIC_START",STATIC_START),("OUTPUT_START",OUTPUT_START)))
    return route_source+helpers+constants+body


_lock=threading.Lock()
_library=None


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:
                from .resident_routes import SOURCE
                _library=torch.mps.compile_shader(build_source(SOURCE))
    return _library


@lru_cache(maxsize=32)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device="mps")


@lru_cache(maxsize=1)
def _dummy():return torch.zeros(1,dtype=torch.int64,device="mps")


class FusedRoutePreparation:
    """Immutable device metadata; no source, model or game-position cache."""
    def __init__(self,routes):
        self.state_context=routes.state_context
        self.services=(routes.relations_context,routes.declaration_context)
        declaration=routes.declaration_context
        self.parts=(routes.data,routes.offsets,routes.relations_context.ids,
                    declaration.geography,declaration.home,declaration.warlords)
        offsets=[];total=0
        for value in self.parts:offsets.append(total);total+=value.numel()
        self.static_offsets=tuple(offsets)
        self.statics=torch.cat(self.parts)

    def prepare(self,routes,state,*,group_size=None):
        from .resident_routes import PreparedRoutes
        state._metadata()
        if state.context.identity!=self.state_context.identity or state.device!=self.state_context.device:
            raise ValueError("Fused route preparation requires its exact wire context/device")
        services=(routes.relations_context,routes.declaration_context)
        if (routes.state_context.identity!=self.state_context.identity or routes.state_context.device!=self.state_context.device or
            any(service.state_context.identity!=self.state_context.identity or service.state_context.device!=self.state_context.device
                for service in services)):
            raise ValueError("Fused route service requires its exact wire context/device")
        parts=(routes.data,routes.offsets,routes.relations_context.ids,
               routes.declaration_context.geography,routes.declaration_context.home,routes.declaration_context.warlords)
        if any(a is not b for a,b in zip(services,self.services,strict=True)) or any(a is not b for a,b in zip(parts,self.parts,strict=True)):
            raise ValueError("Fused route preparation belongs to a different static route context")
        if group_size is not None and (type(group_size) is not int or group_size<=0):
            raise ValueError("Fused route group size must be a positive integer")
        route_dims=routes._dims(state)
        if len(route_dims)!=ROUTE_DIMS:raise RuntimeError("Audited route dimensions schema changed")
        B,C,Z,N,S=route_dims[0],route_dims[1],route_dims[2],route_dims[3],route_dims[9]
        shapes=((B,N,10),(B,N,N,7),(B,N,N,7),(B,N,3),(B,N,3),(B,N),
                (B,N,N),(B,N,N),(B,N,N),(B,N,3),(B,S+Z+N+13))
        sizes=[]
        for shape in shapes:
            count=1
            for size in shape:count*=size
            sizes.append(count)
        slab=torch.empty(sum(sizes),dtype=torch.int64,device=state.device)
        views=tuple(part.view(shape) for part,shape in zip(slab.split(sizes),shapes,strict=True))
        offsets=[];total=0
        for size in sizes:offsets.append(total);total+=size
        declaration=routes.declaration_context
        relation_dims=(B,C,N,len(routes.players),state.context.string_count,state.context.string_bytes.numel(),
            state.string_offsets.numel()-1,state.string_bytes.numel(),state.context.records.shape[0])
        mongolia=routes.nations.index("mongolia") if "mongolia" in routes.nations else -1
        declaration_dims=(*relation_dims,len(declaration.territory_ids),declaration.home_valid,mongolia)
        if len(relation_dims)!=RELATION_DIMS or len(declaration_dims)!=DECLARATION_DIMS:
            raise RuntimeError("Audited political preparation dimensions schema changed")
        if B:
            dims=_dimensions((*route_dims,*relation_dims,*declaration_dims,*self.static_offsets,*offsets))
            args=(state.records,state.lengths,state.sections,state.context.string_bytes,state.context.string_offsets,
                  state.string_bytes,state.string_offsets,state.suffix_usage,state.errors,state.context.records,
                  self.statics,slab,dims)
            if any(value.dtype not in {torch.int64,torch.uint8} or not value.is_contiguous() or value.device!=state.device for value in args):
                raise ValueError("Fused route buffers must preserve complete resident dtype/layout/device")
            kernel=_kernels().fused_route_preparation
            size=min(128,kernel.max_threads_per_threadgroup) if group_size is None else group_size
            if size>kernel.max_threads_per_threadgroup:raise ValueError("Fused route group size exceeds Metal limit")
            kernel(*(value if value.numel() else _dummy() for value in args),threads=B*size,group_size=size)
        metadata,pairs,errors,nations,nerrors,present,_,allowed,derrrors,presence,indexes=views
        relations=PoliticalRelationsBatch(state,pairs,errors,nations,nerrors,present,metadata)
        declarations=LandAttackDeclarations(state,relations,allowed,derrrors,presence)
        return PreparedRoutes(state,relations,declarations,indexes)
