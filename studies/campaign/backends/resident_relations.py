"""Exact read-only political permissions derived once from resident state.

These tensors are privileged rules inputs, never neural observations. Each result
is bound to its immutable source snapshot. Missing dormant factions and neutral
playerless nations have per-query errors rather than invalidating other queries.
This computes permissions; declaration legality and movement routes remain separate.
"""
from dataclasses import dataclass
from functools import lru_cache
import re
import threading

import torch

from .device_state import _device
from .metal_state_schema import METAL_STATE_SOURCE

PAIR_FIELDS=("controlled","at_war","friendly","logistics_friendly",
             "same_alliance","shared_alliance","rail_permission")
NATION_FIELDS=("player","war_major","movement_controller")


@dataclass(frozen=True)
class PoliticalRelationsBatch:
    source: object
    pairs: torch.Tensor
    pair_errors: torch.Tensor
    nations: torch.Tensor
    nation_errors: torch.Tensor
    present: torch.Tensor
    metadata: torch.Tensor  # Resident nation fields reused by declaration gates.

    def _pair(self,name):return self.pairs[:,:,:,PAIR_FIELDS.index(name)]
    @property
    def controlled(self):return self._pair("controlled")
    @property
    def at_war(self):return self._pair("at_war")
    @property
    def friendly(self):return self._pair("friendly")
    @property
    def logistics_friendly(self):return self._pair("logistics_friendly")
    @property
    def same_alliance(self):return self._pair("same_alliance")
    @property
    def shared_alliance(self):return self._pair("shared_alliance")
    @property
    def rail_permission(self):return self._pair("rail_permission")
    @property
    def player(self):return self.nations[:,:,0]
    @property
    def player_errors(self):return self.nation_errors[:,:,0]
    @property
    def war_major(self):return self.nations[:,:,1]
    @property
    def movement_controller(self):return self.nations[:,:,2]


SOURCE=r"""
#include <metal_stdlib>
using namespace metal;
"""+METAL_STATE_SOURCE+r"""
inline bool relations_container(thread const PackedStateView& v,long node,long tag,long count,thread bool& valid) {
    const long end=state_end(v,node,valid);if(!valid)return false;device const long* r=state_record(v,node);
    const long maximum=(tag==7||tag==13)?(end-node-1)/2:end-node-1;
    if(r[0]!=tag||r[1]<0||r[1]>maximum||(count>=0&&r[1]!=count)||r[2]||r[3])valid=false;return valid;
}
inline long relations_index(device const long* ids,long count,long id){for(long i=0;i<count;++i)if(ids[i]==id)return i;return -1;}
inline void relations_span(thread const PackedStateView& v,long id,thread long& start,thread long& finish,
                           thread bool& prefix,thread bool& valid){
    if(id<0||id>=v.prefix_count+v.suffix_count){valid=false;start=finish=0;prefix=true;return;}
    prefix=id<v.prefix_count;const long index=prefix?id:id-v.prefix_count;
    device const long* offsets=prefix?v.prefix_offsets:v.suffix_offsets;
    start=offsets[index];finish=offsets[index+1];
    if(start<0||finish<start||finish>(prefix?v.prefix_bytes_length:v.suffix_bytes_length))valid=false;
}
// Prefix + existing faction bytes, without constructing strings or host lookup.
inline long relations_named_flag(thread const PackedStateView& v,long map,constant char* prefix,long count,long nation,
                                  thread bool& valid){
    relations_container(v,map,7,-1,valid);if(!valid)return -1;
    long a,b;bool fromPrefix;relations_span(v,nation,a,b,fromPrefix,valid);
    device const uchar* name=fromPrefix?v.prefix_bytes:v.suffix_bytes;
    const long end=state_end(v,map,valid),entries=state_record(v,map)[1];long cursor=map+1;
    if(entries>(end-map-1)/2){valid=false;return -1;}
    for(long entry=0;valid&&entry<entries;++entry){const long id=state_string_id(v,cursor,valid);
        long x,y;bool keyPrefix;relations_span(v,id,x,y,keyPrefix,valid);
        device const uchar* key=keyPrefix?v.prefix_bytes:v.suffix_bytes;
        bool match=valid&&y-x==count+b-a;
        for(long k=0;match&&k<count;++k)match=key[x+k]==uchar(prefix[k]);
        for(long k=0;match&&k<b-a;++k)match=key[x+count+k]==name[a+k];
        const long value=state_end(v,cursor,valid),next=state_end(v,value,valid);
        if(!valid||next>end){valid=false;return -1;}if(match)return value;cursor=next;
    }
    if(valid&&cursor!=end)valid=false;return -1;
}
inline bool relations_set_has(thread const PackedStateView& v,long set,long key,thread bool& valid){
    relations_container(v,set,8,-1,valid);if(!valid)return false;
    const long count=state_record(v,set)[1],end=state_end(v,set,valid);long cursor=set+1;
    if(count>end-set-1){valid=false;return false;}
    for(long i=0;valid&&i<count;++i){const long id=state_string_id(v,cursor,valid);cursor=state_end(v,cursor,valid);
        if(id==key)return true;}if(valid&&cursor!=end)valid=false;return false;
}
inline bool relations_flag(thread const PackedStateView& v,long flags,constant char* name,long length,thread bool& valid){
    const long field=state_map_find_literal(v,flags,name,length,valid);if(field<0)return false;
    const long value=state_signed_value(v,field,valid);
    if(value<(-2147483647L-1L)||value>2147483647L)valid=false;return value!=0;
}
inline long relations_optional_id(thread const PackedStateView& v,long root,long field,thread bool& valid){
    bool present=false;const long node=state_optional(v,state_child(v,root,field,valid),present,valid);
    return present?state_string_id(v,node,valid):-1;
}
inline bool relations_control(device const long* meta,long a,long b){
    return a!=b&&meta[a*10]&&meta[a*10+1]==b&&!meta[a*10+5]&&!meta[a*10+6];
}
inline bool relations_friendly(device const long* meta,device const long* pairs,long N,long a,long b,
                               bool truce,long ccp,long kmt,thread long& error){
    if(a==b||(truce&&((a==ccp&&b==kmt)||(a==kmt&&b==ccp))))return true;
    if(!meta[a*10]||!meta[b*10]){error=1;return false;}
    if(pairs[(a*N+b)*7+1])return false;
    if(relations_control(meta,a,b)||relations_control(meta,b,a))return false;
    if(meta[a*10+3]<0||meta[a*10+3]!=meta[b*10+3]||!meta[a*10+4]||!meta[b*10+4])return false;
    for(long enemy=0;enemy<N;++enemy)if(pairs[(a*N+enemy)*7+1]&&pairs[(b*N+enemy)*7+1]){
        if(!meta[enemy*10]){error=1;return false;}if(meta[enemy*10+4])return true;}
    return false;
}
kernel void resident_relations(
    device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],
    device const uchar* prefix_bytes [[buffer(2)]],device const long* prefix_offsets [[buffer(3)]],
    device const uchar* suffix_bytes [[buffer(4)]],device const long* suffix_offsets [[buffer(5)]],
    device const long* usage [[buffer(6)]],device const long* ids [[buffer(7)]],
    device const long* definition [[buffer(8)]],device const long* source_errors [[buffer(9)]],
    device long* meta_all [[buffer(10)]],device long* pairs_all [[buffer(11)]],device long* pair_errors_all [[buffer(12)]],
    device long* nations_all [[buffer(13)]],device long* nation_errors_all [[buffer(14)]],
    device long* present_all [[buffer(15)]],device long* permission_all [[buffer(16)]],
    device const long* dims [[buffer(17)]],uint lane [[thread_position_in_grid]]) {
    const long B=dims[0],C=dims[1],N=dims[2],P=dims[3];if(long(lane)>=B)return;
    device long* meta=meta_all+ulong(lane)*N*10;
    device long* pairs=pairs_all+ulong(lane)*N*N*7;device long* errors=pair_errors_all+ulong(lane)*N*N*7;
    device long* nations=nations_all+ulong(lane)*N*3;device long* nerrors=nation_errors_all+ulong(lane)*N*3;
    device long* permission=permission_all+ulong(lane)*N*N;
    for(long i=0;i<N*N*7;++i){pairs[i]=0;errors[i]=0;}
    for(long i=0;i<N*3;++i){nations[i]=0;nerrors[i]=0;}
    for(long i=0;i<N*N;++i)permission[i]=0;
    for(long i=0;i<N;++i){present_all[ulong(lane)*N+i]=0;
        for(long k=0;k<10;++k)meta[i*10+k]=0;meta[i*10+1]=-1;meta[i*10+2]=-1;meta[i*10+3]=-1;meta[i*10+8]=-1;}
    bool valid=true;
    PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
        prefix_bytes,prefix_offsets,dims[4],dims[5],suffix_bytes,suffix_offsets,dims[6],dims[7],usage,valid);
    if(source_errors[lane])valid=false;
    relations_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);relations_container(v,state,10,19,valid);
    const long ns=state_child(v,state,0,valid),politics=state_child(v,state,8,valid),clock=state_child(v,state,7,valid);
    relations_container(v,ns,7,-1,valid);relations_container(v,politics,10,11,valid);relations_container(v,clock,10,6,valid);
    const bool truce=state_boolean_value(v,state_child(v,politics,0,valid),valid);
    const long surrendered=state_child(v,politics,8,valid),pending=state_child(v,politics,10,valid);
    // Definition uses the same immutable string prefix and no dynamic suffix.
    PackedStateView d={definition,dims[8],dims[8],prefix_bytes,prefix_offsets,dims[4],dims[5],suffix_bytes,suffix_offsets,0,0};
    relations_container(d,0,10,11,valid);const long turns=state_child(d,0,6,valid);
    const long activeIndex=state_signed_value(v,state_child(v,clock,1,valid),valid);
    long active=-1;if(valid&&activeIndex>=0&&activeIndex<state_record(d,turns)[1])
        active=relations_index(ids,N,state_string_id(d,state_child(d,turns,activeIndex,valid),valid));
    else valid=false;
    const long ccp=ids[N+P],kmt=ids[N+P+1],japan=ids[N+P+2],dadao=ids[N+P+3];
    // Special slots hold faction INDICES, not string IDs; -1 means absent definition.
    for(long a=0;valid&&a<N;++a){const long root=state_map_find_id(v,ns,ids[a],valid);if(root<0)continue;
        relations_container(v,root,10,12,valid);meta[a*10]=1;present_all[ulong(lane)*N+a]=1;
        const long controller=relations_optional_id(v,root,0,valid),player=relations_optional_id(v,root,1,valid);
        meta[a*10+1]=controller<0?-1:relations_index(ids,N,controller);if(controller>=0&&meta[a*10+1]<0)meta[a*10+1]=-2;
        meta[a*10+2]=player<0?-1:relations_index(ids+N,P,player);if(player>=0&&meta[a*10+2]<0)meta[a*10+2]=-2;
        meta[a*10+3]=relations_optional_id(v,root,2,valid);
        meta[a*10+4]=state_string_equals(v,state_child(v,root,3,valid),"major",5,valid);
        const long flags=state_child(v,root,11,valid),turn=state_child(v,root,10,valid);
        meta[a*10+5]=relations_flag(v,flags,"incorporated",12,valid);
        meta[a*10+6]=relations_set_has(v,surrendered,ids[a],valid);
        meta[a*10+7]=relations_flag(v,flags,"direct_axis_control_after_japan_surrender",41,valid);
        // Political pending is a native map whose values are arbitrary JSON.
        long pendingNode=-1;
        const long end=state_end(v,pending,valid);relations_container(v,pending,7,-1,valid);long cursor=pending+1;
        const long count=valid?state_record(v,pending)[1]:0;
        for(long entry=0;valid&&entry<count;++entry){const long key=state_string_id(v,cursor,valid);
            long x,y,na,nb;bool kp,np;relations_span(v,key,x,y,kp,valid);relations_span(v,ids[a],na,nb,np,valid);
            device const uchar* kb=kp?v.prefix_bytes:v.suffix_bytes;device const uchar* names=np?v.prefix_bytes:v.suffix_bytes;
            constant char* pre="warlord_defense_player:";bool match=y-x==23+nb-na;
            for(long k=0;match&&k<23;++k)match=kb[x+k]==uchar(pre[k]);
            for(long k=0;match&&k<nb-na;++k)match=kb[x+23+k]==names[na+k];
            const long value=state_end(v,cursor,valid);if(match)pendingNode=value;cursor=state_end(v,value,valid);}
        if(valid&&cursor!=end)valid=false;
        if(pendingNode>=0){bool pv=true;const long value=state_string_id(v,pendingNode,pv);
            meta[a*10+8]=pv?relations_index(ids+N,P,value):-2;if(meta[a*10+8]<0)meta[a*10+8]=-2;}
        const long wars=state_child(v,root,8,valid);
        for(long b=0;valid&&b<N;++b){pairs[(a*N+b)*7+1]=a!=b&&relations_set_has(v,wars,ids[b],valid);
            const long flag=relations_named_flag(v,turn,"rail_permission:",16,ids[b],valid);
            if(flag>=0){const long value=state_signed_value(v,flag,valid);if(value<(-2147483647L-1L)||value>2147483647L)valid=false;
                permission[b*N+a]=value!=0;}}
    }
    if(!valid){for(long i=0;i<N*N*7;++i)errors[i]=3;for(long i=0;i<N*3;++i)nerrors[i]=3;return;}
    for(long a=0;a<N;++a){long current=a,playerError=2;
        // N is the exact complete graph bound. Exhaustion means a cycle, not truncation.
        for(long visit=0;visit<=N;++visit){if(current<0||current>=N||!meta[current*10]){playerError=1;break;}
            if(meta[current*10+2]>=0){nations[a*3]=meta[current*10+2];playerError=0;break;}
            if(meta[current*10+2]==-2)break;
            if(meta[current*10+1]>=0){current=meta[current*10+1];continue;}
            if(meta[current*10+1]==-2){playerError=1;break;}
            if(meta[current*10+8]>=0){nations[a*3]=meta[current*10+8];playerError=0;}break;}
        nerrors[a*3]=playerError;
        if(!meta[a*10])nerrors[a*3+1]=1;
        else for(long e=0;e<N;++e)if(pairs[(a*N+e)*7+1]){
            if(!meta[e*10]){nerrors[a*3+1]=1;break;}if(meta[e*10+4]){nations[a*3+1]=1;break;}}
        nations[a*3+2]=a==active||relations_control(meta,a,active);
        if(!nations[a*3+2]&&a==dadao&&active==japan){if(!meta[a*10])nerrors[a*3+2]=1;else nations[a*3+2]=meta[a*10+7];}
        for(long b=0;b<N;++b){const long base=(a*N+b)*7;
            pairs[base]=relations_control(meta,a,b);
            if(a!=b&&!meta[a*10])errors[base+1]=1;
            long error=0;const bool friendly=relations_friendly(meta,pairs,N,a,b,truce,ccp,kmt,error);
            pairs[base+2]=friendly;errors[base+2]=error;
            if(!error)pairs[base+3]=a==b||friendly||relations_control(meta,b,a);errors[base+3]=error;
            if(!meta[a*10]||!meta[b*10])errors[base+4]=1;
            else pairs[base+4]=meta[a*10+3]==meta[b*10+3];
            // Like the native optional && expression, an absent first alliance
            // short-circuits before the second nation's lookup.
            if(!meta[a*10])errors[base+5]=1;
            else if(meta[a*10+3]>=0){if(!meta[b*10])errors[base+5]=1;
                else pairs[base+5]=meta[a*10+3]==meta[b*10+3];}
            if(a==b)pairs[base+6]=1;
            else if(error)errors[base+6]=error;
            else if(friendly)pairs[base+6]=meta[a*10+2]==meta[b*10+2]||permission[a*N+b];
        }
    }
}
"""


def _parallel_source(reference):
    """Reuse the audited bodies, changing their scheduling rather than rules.

    The serial kernel remains intact. The fallback deliberately runs that full
    original body so malformed inputs preserve even its partial diagnostic data.
    Each required marker is explicit: edits to the reference must consciously
    update this construction rather than silently selecting a different block.
    """
    signature,body=reference.split('kernel void resident_relations(',1)[1].split(') {',1)
    body=body.rsplit('}',1)[0]
    plain=re.sub(r'\[\[.*?\]\]','',signature)
    fallback='inline void relations_reference_fallback('+plain+') {'+body+'}\n'
    argument_names=('records','lengths','prefix_bytes','prefix_offsets','suffix_bytes','suffix_offsets','usage','ids',
                    'definition','source_errors','meta_all','pairs_all','pair_errors_all','nations_all','nation_errors_all',
                    'present_all','permission_all','dims')
    call='relations_reference_fallback('+','.join(argument_names)+',uint(lane));'
    parallel_signature=signature.rsplit('uint lane [[thread_position_in_grid]]',1)[0]+\
        'uint3 group [[threadgroup_position_in_grid]],uint tid [[thread_index_in_threadgroup]],uint3 group_size [[threads_per_threadgroup]]'
    prelude=body.split('    if(source_errors[lane])valid=false;',1)[1].split('    const long ccp=',1)[0]
    meta=body.split('    for(long a=0;valid&&a<N;++a){',1)[1].split('    if(!valid){',1)[0]
    meta=meta.rsplit('\n    }',1)[0]
    meta=meta.replace('if(root<0)continue;',
        'if(root<0){if(!valid)atomic_fetch_or_explicit(&invalid,1,memory_order_relaxed);continue;}')
    post=body.split('    for(long a=0;a<N;++a){',1)[1]
    nation,pairs=post.split('        for(long b=0;b<N;++b){',1)
    pairs=pairs.rsplit('\n        }\n    }',1)[0]
    parallel=r'''
    const long lane=long(group.x),B=dims[0],C=dims[1],N=dims[2],P=dims[3],stride=long(group_size.x);
    if(lane>=B)return;
    device long* meta=meta_all+ulong(lane)*N*10;
    device long* pairs=pairs_all+ulong(lane)*N*N*7;device long* errors=pair_errors_all+ulong(lane)*N*N*7;
    device long* nations=nations_all+ulong(lane)*N*3;device long* nerrors=nation_errors_all+ulong(lane)*N*3;
    device long* permission=permission_all+ulong(lane)*N*N;
    threadgroup long roots[5];threadgroup atomic_int invalid;
    bool valid=true;
    PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
        prefix_bytes,prefix_offsets,dims[4],dims[5],suffix_bytes,suffix_offsets,dims[6],dims[7],usage,valid);
    if(tid==0){atomic_store_explicit(&invalid,0,memory_order_relaxed);
        if(source_errors[lane])valid=false;
''' + prelude + r'''
        roots[0]=ns;roots[1]=surrendered;roots[2]=pending;roots[3]=active;roots[4]=truce;
        if(!valid)atomic_store_explicit(&invalid,1,memory_order_relaxed);
    }
    for(long i=tid;i<N*N*7;i+=stride){pairs[i]=0;errors[i]=0;}
    for(long i=tid;i<N*3;i+=stride){nations[i]=0;nerrors[i]=0;}
    for(long i=tid;i<N*N;i+=stride)permission[i]=0;
    for(long a=tid;a<N;a+=stride){present_all[ulong(lane)*N+a]=0;
        for(long k=0;k<10;++k)meta[a*10+k]=0;meta[a*10+1]=-1;meta[a*10+2]=-1;meta[a*10+3]=-1;meta[a*10+8]=-1;}
    threadgroup_barrier(mem_flags::mem_threadgroup|mem_flags::mem_device);
    if(atomic_load_explicit(&invalid,memory_order_relaxed)){if(tid==0){''' + call + r'''}return;}
    const long ns=roots[0],surrendered=roots[1],pending=roots[2],active=roots[3];const bool truce=roots[4]!=0;
    const long ccp=ids[N+P],kmt=ids[N+P+1],japan=ids[N+P+2],dadao=ids[N+P+3];
    for(long a=tid;a<N;a+=stride){valid=true;
''' + meta + r'''
        if(!valid)atomic_fetch_or_explicit(&invalid,1,memory_order_relaxed);
    }
    threadgroup_barrier(mem_flags::mem_threadgroup|mem_flags::mem_device);
    if(atomic_load_explicit(&invalid,memory_order_relaxed)){if(tid==0){''' + call + r'''}return;}
    for(long a=tid;a<N;a+=stride){
''' + nation + r'''
    }
    for(long pair=tid;pair<N*N;pair+=stride){const long a=pair/N,b=pair%N;
''' + pairs + r'''
    }
'''
    return fallback+'kernel void resident_relations_parallel('+parallel_signature+') {'+parallel+'}\n'


SOURCE+=_parallel_source(SOURCE)

_lock=threading.Lock()
_library=None

def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    return _library

@lru_cache(maxsize=32)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device="mps")

@lru_cache(maxsize=1)
def _dummy():return torch.zeros(1,dtype=torch.int64,device="mps")


class ResidentPoliticalRelations:
    def __init__(self,state_context,native_relations_context):
        if _device(state_context.device).type!="mps":raise ValueError("Resident relations require explicit MPS execution")
        if state_context.definition_fingerprint!=native_relations_context.definition_fingerprint:
            raise ValueError("Relations definition differs from packed state")
        self.state_context=state_context
        self.native_context=native_relations_context
        self.nation_ids=tuple(native_relations_context.nations);self.player_ids=tuple(native_relations_context.players)
        special=tuple(self.nation_ids.index(name) if name in self.nation_ids else -1 for name in ("ccp","kmt","japan","dadao"))
        fixed=tuple(int(x) for x in state_context.prefix_lookup_ids((*self.nation_ids,*self.player_ids)))
        self.ids=torch.tensor((*fixed,*special),dtype=torch.int64,device=state_context.device)

    def compute(self,state,*,implementation="parallel",group_size=None):
        state._metadata();_device(state.device)
        if state.context.identity!=self.state_context.identity:raise ValueError("Relations packed wire context differs")
        if implementation not in {"reference","parallel"}:raise ValueError("Choose reference or parallel relations implementation")
        if group_size is not None and (type(group_size) is not int or group_size<=0):
            raise ValueError("Relations group size must be a positive integer")
        if implementation=="reference" and group_size is not None:
            raise ValueError("Reference relations do not use a threadgroup override")
        B,C=state.records.shape[:2];N=len(self.nation_ids);device=state.device
        alloc=lambda *shape:torch.empty(shape,dtype=torch.int64,device=device)
        pairs,errors=alloc(B,N,N,7),alloc(B,N,N,7)
        nations,nerrors,present=alloc(B,N,3),alloc(B,N,3),alloc(B,N)
        metadata=alloc(B,N,10)
        if B:
            dims=(B,C,N,len(self.player_ids),state.context.string_count,state.context.string_bytes.numel(),
                  state.string_offsets.numel()-1,state.string_bytes.numel(),state.context.records.shape[0])
            args=(state.records,state.lengths,state.context.string_bytes,state.context.string_offsets,state.string_bytes,
                  state.string_offsets,state.suffix_usage,self.ids,state.context.records,state.errors,metadata,pairs,
                  errors,nations,nerrors,present,alloc(B,N,N),_dimensions(dims))
            if any(not x.is_contiguous() for x in args):raise ValueError("Relations inputs must be contiguous; no hidden copy")
            kernel=getattr(_kernels(),"resident_relations" if implementation=="reference" else "resident_relations_parallel")
            if implementation=="reference":kernel(*(x if x.numel() else _dummy() for x in args),threads=B)
            else:
                size=min(128,kernel.max_threads_per_threadgroup) if group_size is None else group_size
                if size>kernel.max_threads_per_threadgroup:raise ValueError("Relations group size exceeds Metal kernel limit")
                kernel(*(x if x.numel() else _dummy() for x in args),threads=B*size,group_size=size)
        return PoliticalRelationsBatch(state,pairs,errors,nations,nerrors,present,metadata)

    def inspect(self,result,field):
        """Explicit host boundary; device consumers read tensors/error masks directly."""
        if result.source.context.identity!=self.state_context.identity:raise ValueError("Relations result context differs")
        if field in PAIR_FIELDS:
            index=PAIR_FIELDS.index(field);values=result.pairs[:,:,:,index];errors=result.pair_errors[:,:,:,index]
        elif field in NATION_FIELDS:
            index=NATION_FIELDS.index(field);values=result.nations[:,:,index];errors=result.nation_errors[:,:,index]
        else:raise ValueError("Unknown political relation field")
        return {"values":values.cpu().tolist(),"errors":errors.cpu().tolist()}
