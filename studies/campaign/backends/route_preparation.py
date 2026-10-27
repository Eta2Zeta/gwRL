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
ROUTE_DIMS,RELATION_DIMS,DECLARATION_DIMS,STATIC_COUNT=26,9,12,7
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


def _indexed_declaration_source(signature,body):
    begin='    bool valid=true;PackedStateView v='
    root='    relations_container(v,0,10,2,valid);'
    land_loop='    if(valid){const long end=state_end(v,land,valid)'
    pair_loop='    for(long a=0;a<N;++a)for(long b=0;b<N;++b){'
    for marker in (begin,root,land_loop,pair_loop):
        if body.count(marker)!=1:raise RuntimeError("Audited indexed declaration marker changed")
    view=begin+body.split(begin,1)[1].split(root,1)[0]
    parse=root+body.split(root,1)[1].split(land_loop,1)[0]
    pairs=body.split(pair_loop,1)[1].rsplit('\n    }',1)[0]
    extra=",uint tid,long stride,device const long* route_indexes,device const long* route_dims,"\
          "device const long* route_zone_ids,device const long* route_geo,device long* scratch_all,"\
          "threadgroup atomic_uint* failed,threadgroup atomic_uint* counts,threadgroup long* shared"
    prefix=r'''
    const long B=dims[0],C=dims[1],N=dims[2],P=dims[3],T=dims[9],Z=route_dims[2],S=route_dims[9];
    if(long(lane)>=B)return;
    device const long* meta=meta_all+ulong(lane)*N*10;device const long* pairs=pairs_all+ulong(lane)*N*N*7;
    device long* allowed=allowed_all+ulong(lane)*N*N;device long* errors=errors_all+ulong(lane)*N*N;
    device long* presence=presence_all+ulong(lane)*N*3;
    // Scratch alone is accessed as 32-bit atomics. Every slot occupies eight
    // bytes; public presence values remain exact int64 after the group fence.
    device atomic_uint* scratch=reinterpret_cast<device atomic_uint*>(scratch_all+ulong(lane)*N*3);
    device const long* index=route_indexes+ulong(lane)*(S+Z+N+13);
    for(long i=tid;i<N*N;i+=stride){allowed[i]=0;errors[i]=0;}
    for(long i=tid;i<N*3;i+=stride){presence[i]=0;
        atomic_store_explicit(scratch+i*2,0,memory_order_relaxed);
        atomic_store_explicit(scratch+i*2+1,0,memory_order_relaxed);}
    if(tid==0){atomic_store_explicit(failed,0,memory_order_relaxed);
        atomic_store_explicit(counts,0,memory_order_relaxed);atomic_store_explicit(counts+1,0,memory_order_relaxed);
        for(long i=0;i<8;++i)shared[i]=-1;}
'''
    prelude=prefix+view+r'''
    if(tid==0){
'''+parse+r'''
        shared[0]=land;shared[1]=units;shared[2]=active;shared[3]=phase;shared[4]=truce;
        if(valid){shared[5]=state_record(v,land)[1];shared[6]=state_record(v,units)[1];
            shared[7]=v.prefix_count+v.suffix_count;
            // Larger/malformed domains use the complete serial GPU reference;
            // no entry is dropped or scored as absent because of a fast-path bound.
            if(active<0||index[S+Z+N+12]||shared[5]<0||shared[5]>Z||shared[6]<0||
               shared[6]>shared[7]||shared[7]>long(0xffffffffU))valid=false;}
        if(!valid)atomic_store_explicit(failed,1,memory_order_relaxed);
    }
    threadgroup_barrier(mem_flags::mem_threadgroup|mem_flags::mem_device);
    if(!atomic_load_explicit(failed,memory_order_relaxed)){
        for(long z=tid;z<Z;z+=stride){const long value=index[S+z];if(value<0)continue;
            atomic_fetch_add_explicit(counts,1,memory_order_relaxed);bool ok=true;
            relations_container(v,value,10,2,ok);
            const long owner=relations_optional_id(v,value,0,ok),n=owner<0?-1:relations_index(ids,N,owner),g=route_geo[z];
            if(g<0||g>=T||(owner>=0&&(n<0||!meta[n*10])))ok=false;
            if(ok&&n>=0){atomic_fetch_or_explicit(scratch+(n*3+2)*2,1,memory_order_relaxed);
                if(home[g])atomic_fetch_or_explicit(scratch+(n*3+1)*2,1,memory_order_relaxed);}
            if(!ok)atomic_fetch_or_explicit(failed,1,memory_order_relaxed);
        }
        for(long id=tid;id<shared[7];id+=stride){const long value=index[id];if(value<0)continue;
            atomic_fetch_add_explicit(counts+1,1,memory_order_relaxed);bool ok=true;
            relations_container(v,value,10,14,ok);
            const long owner=state_string_id(v,state_child(v,value,2,ok),ok),n=relations_index(ids,N,owner);
            const long zone=state_string_id(v,state_child(v,value,3,ok),ok),z=relations_index(route_zone_ids,Z,zone);
            if(n<0||!meta[n*10]||z<0)ok=false;
            if(ok){atomic_fetch_or_explicit(scratch+(n*3)*2,1,memory_order_relaxed);
                if(index[S+z]>=0){const long g=route_geo[z];
                    if(g<0||g>=T)ok=false;
                    else{atomic_fetch_or_explicit(scratch+(n*3+2)*2,1,memory_order_relaxed);
                        if(home[g])atomic_fetch_or_explicit(scratch+(n*3+1)*2,1,memory_order_relaxed);}}}
            if(!ok)atomic_fetch_or_explicit(failed,1,memory_order_relaxed);
        }
    }
    threadgroup_barrier(mem_flags::mem_threadgroup|mem_flags::mem_device);
    if(tid==0&&(long(atomic_load_explicit(counts,memory_order_relaxed))!=shared[5]||
                long(atomic_load_explicit(counts+1,memory_order_relaxed))!=shared[6]))
        atomic_store_explicit(failed,1,memory_order_relaxed);
    threadgroup_barrier(mem_flags::mem_threadgroup|mem_flags::mem_device);
    if(atomic_load_explicit(failed,memory_order_relaxed)){
        if(tid==0)route_prepare_declarations(records,lengths,prefix_bytes,prefix_offsets,suffix_bytes,suffix_offsets,
            usage,ids,definition,source_errors,meta_all,pairs_all,pair_errors,geography,home,warlords,
            allowed_all,errors_all,presence_all,dims,lane);
        return;
    }
    for(long i=tid;i<N*3;i+=stride)presence[i]=long(atomic_load_explicit(scratch+i*2,memory_order_relaxed));
    threadgroup_barrier(mem_flags::mem_threadgroup|mem_flags::mem_device);
    const long active=shared[2],phase=shared[3];const bool truce=shared[4]!=0;
    const long ccp=ids[N+P],kmt=ids[N+P+1],japan=ids[N+P+2],dadao=ids[N+P+3],mongolia=dims[11];
    for(long pair=tid;pair<N*N;pair+=stride){const long a=pair/N,b=pair%N;
'''+pairs+r'''
    }
'''
    return '\ninline void route_prepare_declarations_indexed('+signature+extra+') {'+prelude+'}\n'


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
    indexed=body.replace("kernel void fused_route_preparation(","kernel void fused_indexed_route_preparation(")
    serial=body[body.index("    if(tid==0){"):body.rindex("\n}")]
    parallel=r'''    if(tid==0)route_prepare_indexes(records,lengths,sections,prefix_bytes,prefix_offsets,suffix_bytes,suffix_offsets,usage,
        source_errors,data,offsets,indexes,dims,uint(lane));
    threadgroup_barrier(mem_flags::mem_threadgroup|mem_flags::mem_device);
    threadgroup atomic_uint declaration_failed;threadgroup atomic_uint declaration_counts[2];threadgroup long declaration_roots[8];
    route_prepare_declarations_indexed(records,lengths,prefix_bytes,prefix_offsets,suffix_bytes,suffix_offsets,usage,ids,
        definition,source_errors,metadata,pairs,pair_errors,geography,home,warlords,allowed,declaration_errors,presence,
        dims+ROUTE_DIMS+RELATION_DIMS,uint(lane),tid,long(group_size.x),indexes,dims,data+offsets[17],
        statics+dims[STATIC_START+6],output+dims[OUTPUT_START+11],&declaration_failed,declaration_counts,declaration_roots);
'''
    if indexed.count(serial)!=1:raise RuntimeError("Audited fused stage ordering changed")
    indexed=indexed.replace(serial,parallel)
    return route_source+helpers+_indexed_declaration_source(declaration_sig,declaration_body)+constants+body+indexed


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
        geography={name:index for index,name in enumerate(declaration.territory_ids)}
        self.zone_geography=torch.tensor([geography.get(name,-1) for name in routes.zones],dtype=torch.int64,device=routes.state_context.device)
        static_parts=(*self.parts,self.zone_geography)
        for value in static_parts:offsets.append(total);total+=value.numel()
        self.static_offsets=tuple(offsets)
        self.statics=torch.cat(static_parts)

    def prepare(self,routes,state,*,group_size=None,implementation="fused"):
        from .resident_routes import PreparedRoutes
        state._metadata()
        if implementation not in {"fused","fused_indexed"}:raise ValueError("Choose fused or fused_indexed preparation")
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
        if implementation=="fused_indexed":shapes=(*shapes,(B,N,3))
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
            kernel=getattr(_kernels(),"fused_route_preparation" if implementation=="fused" else "fused_indexed_route_preparation")
            size=min(128,kernel.max_threads_per_threadgroup) if group_size is None else group_size
            if size>kernel.max_threads_per_threadgroup:raise ValueError("Fused route group size exceeds Metal limit")
            kernel(*(value if value.numel() else _dummy() for value in args),threads=B*size,group_size=size)
        metadata,pairs,errors,nations,nerrors,present,_,allowed,derrrors,presence,indexes=views[:11]
        relations=PoliticalRelationsBatch(state,pairs,errors,nations,nerrors,present,metadata)
        declarations=LandAttackDeclarations(state,relations,allowed,derrrors,presence)
        return PreparedRoutes(state,relations,declarations,indexes)
