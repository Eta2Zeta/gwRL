"""Exact LandAttack declaration permission on resident state and relation arrays.

The complete native boolean predicate is implemented, with its original early
denials and lazy errors. This does not declare war, alter alignment or advance
the calendar. All unit/territory presence is read from the current packed state.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import _device
from .resident_relations import SOURCE as RELATIONS_SOURCE


@dataclass(frozen=True)
class LandAttackDeclarations:
    source: object
    relations: object
    allowed: torch.Tensor
    errors: torch.Tensor
    presence: torch.Tensor  # [B,N,3]: units anywhere, home presence, land reference.


SOURCE=RELATIONS_SOURCE+r"""
kernel void resident_land_attack_declarations(
    device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],
    device const uchar* prefix_bytes [[buffer(2)]],device const long* prefix_offsets [[buffer(3)]],
    device const uchar* suffix_bytes [[buffer(4)]],device const long* suffix_offsets [[buffer(5)]],
    device const long* usage [[buffer(6)]],device const long* ids [[buffer(7)]],
    device const long* definition [[buffer(8)]],device const long* source_errors [[buffer(9)]],
    device const long* meta_all [[buffer(10)]],device const long* pairs_all [[buffer(11)]],
    device const long* pair_errors [[buffer(12)]],device const long* geography [[buffer(13)]],
    device const long* home [[buffer(14)]],device const long* warlords [[buffer(15)]],
    device long* allowed_all [[buffer(16)]],device long* errors_all [[buffer(17)]],
    device long* presence_all [[buffer(18)]],device const long* dims [[buffer(19)]],
    uint lane [[thread_position_in_grid]]) {
    const long B=dims[0],C=dims[1],N=dims[2],P=dims[3],T=dims[9];if(long(lane)>=B)return;
    device const long* meta=meta_all+ulong(lane)*N*10;device const long* pairs=pairs_all+ulong(lane)*N*N*7;
    device long* allowed=allowed_all+ulong(lane)*N*N;device long* errors=errors_all+ulong(lane)*N*N;
    device long* presence=presence_all+ulong(lane)*N*3;
    for(long i=0;i<N*N;++i){allowed[i]=0;errors[i]=0;}for(long i=0;i<N*3;++i)presence[i]=0;
    bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
        prefix_bytes,prefix_offsets,dims[4],dims[5],suffix_bytes,suffix_offsets,dims[6],dims[7],usage,valid);
    if(source_errors[lane]||pair_errors[ulong(lane)*N*N*7]==3)valid=false;
    relations_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);relations_container(v,state,10,19,valid);
    const long land=state_child(v,state,1,valid),units=state_child(v,state,2,valid);
    const long clock=state_child(v,state,7,valid),politics=state_child(v,state,8,valid);
    relations_container(v,clock,10,6,valid);relations_container(v,politics,10,11,valid);
    const long phase=state_signed_value(v,state_child(v,clock,2,valid),valid);
    const long activeIndex=state_signed_value(v,state_child(v,clock,1,valid),valid);
    const bool truce=state_boolean_value(v,state_child(v,politics,0,valid),valid);
    PackedStateView d={definition,dims[8],dims[8],prefix_bytes,prefix_offsets,dims[4],dims[5],suffix_bytes,suffix_offsets,0,0};
    relations_container(d,0,10,11,valid);const long order=state_child(d,0,6,valid);long active=-1;
    if(valid&&activeIndex>=0&&activeIndex<state_record(d,order)[1])
        active=relations_index(ids,N,state_string_id(d,state_child(d,order,activeIndex,valid),valid));
    else valid=false;
    relations_container(v,land,7,-1,valid);relations_container(v,units,7,-1,valid);
    if(valid){const long end=state_end(v,land,valid),count=state_record(v,land)[1];long cursor=land+1;
        for(long entry=0;valid&&entry<count;++entry){const long zone=state_string_id(v,cursor,valid),z=relations_index(geography,T,zone);
            const long value=state_end(v,cursor,valid);relations_container(v,value,10,2,valid);
            const long owner=relations_optional_id(v,value,0,valid),n=owner<0?-1:relations_index(ids,N,owner);
            if(z<0||(owner>=0&&(n<0||!meta[n*10]))){valid=false;break;}
            if(n>=0){presence[n*3+2]=1;if(home[z])presence[n*3+1]=1;}
            cursor=state_end(v,value,valid);}
        if(valid&&cursor!=end)valid=false;}
    if(valid){const long end=state_end(v,units,valid),count=state_record(v,units)[1];long cursor=units+1;
        for(long entry=0;valid&&entry<count;++entry){state_string_id(v,cursor,valid);
            const long value=state_end(v,cursor,valid);relations_container(v,value,10,14,valid);
            const long owner=state_string_id(v,state_child(v,value,2,valid),valid),n=relations_index(ids,N,owner);
            const long zone=state_string_id(v,state_child(v,value,3,valid),valid);
            if(n<0||!meta[n*10]){valid=false;break;}presence[n*3]=1;
            if(state_map_find_id(v,land,zone,valid)>=0){const long z=relations_index(geography,T,zone);
                if(z<0){valid=false;break;}presence[n*3+2]=1;if(home[z])presence[n*3+1]=1;}
            cursor=state_end(v,value,valid);}
        if(valid&&cursor!=end)valid=false;}
    if(!valid||active<0){for(long i=0;i<N*N;++i)errors[i]=3;return;}
    const long ccp=ids[N+P],kmt=ids[N+P+1],japan=ids[N+P+2],dadao=ids[N+P+3];
    const long mongolia=dims[11];
    for(long a=0;a<N;++a)for(long b=0;b<N;++b){const long index=a*N+b,base=index*7;
        if(!meta[a*10]||!meta[b*10]||a==b)continue;
        if(meta[a*10+6]||meta[a*10+5]||meta[b*10+6]||meta[b*10+5])continue;
        if(pairs[base+1])continue;
        if(meta[a*10+3]>=0&&pairs[base+4])continue;
        if(truce&&((a==ccp&&b==kmt)||(a==kmt&&b==ccp)))continue;
        if(phase!=1||(a!=active&&!pairs[(a*N+active)*7]))continue;
        if(a==kmt&&(warlords[b]||b==mongolia)){if(ccp<0||!presence[ccp*3])allowed[index]=1;continue;}
        if(a==ccp&&warlords[b]){allowed[index]=1;continue;}
        if(a==ccp||a==kmt){if(meta[a*10+4])allowed[index]=1;
            else if(!dims[10]&&presence[b*3+2])errors[index]=1;
            else allowed[index]=presence[b*3+1];continue;}
        if(a==japan){allowed[index]=1;continue;}
        if(a==dadao&&(b==ccp||b==kmt||b==dadao||warlords[b]))allowed[index]=1;
    }
}
"""

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


class ResidentLandAttackDeclarations:
    def __init__(self,relations_context):
        self.relations_context=relations_context
        self.state_context=relations_context.state_context
        native=relations_context.native_context
        self.territory_ids=tuple(native.territories)
        self.geography=torch.tensor(self.state_context.prefix_lookup_ids(self.territory_ids),dtype=torch.int64,device=self.state_context.device)
        self.home=torch.tensor(native.chinese_home_array(),dtype=torch.int64,device=self.state_context.device)
        self.warlords=torch.tensor(native.warlord_array(),dtype=torch.int64,device=self.state_context.device)
        self.home_valid=int(native.chinese_home_valid)

    def compute(self,state,relations=None):
        state._metadata();_device(state.device)
        if state.context.identity!=self.state_context.identity:raise ValueError("Declaration packed wire context differs")
        if relations is None:relations=self.relations_context.compute(state)
        if relations.source is not state:raise ValueError("Declaration relations belong to a different complete source state")
        B,C=state.records.shape[:2];N=len(self.relations_context.nation_ids);device=state.device
        for tensor,shape in ((relations.pairs,(B,N,N,7)),(relations.pair_errors,(B,N,N,7)),(relations.metadata,(B,N,10))):
            if tensor.dtype!=torch.int64 or tensor.device!=device or tensor.shape!=shape or not tensor.is_contiguous():
                raise ValueError("Declaration relation shape/device/layout differs")
        alloc=lambda *shape:torch.empty(shape,dtype=torch.int64,device=device)
        allowed,errors,presence=alloc(B,N,N),alloc(B,N,N),alloc(B,N,3)
        if B:
            mongolia=self.relations_context.nation_ids.index("mongolia") if "mongolia" in self.relations_context.nation_ids else -1
            dims=(B,C,N,len(self.relations_context.player_ids),state.context.string_count,state.context.string_bytes.numel(),
                  state.string_offsets.numel()-1,state.string_bytes.numel(),state.context.records.shape[0],
                  len(self.territory_ids),self.home_valid,mongolia)
            args=(state.records,state.lengths,state.context.string_bytes,state.context.string_offsets,state.string_bytes,
                  state.string_offsets,state.suffix_usage,self.relations_context.ids,state.context.records,state.errors,
                  relations.metadata,relations.pairs,relations.pair_errors,self.geography,self.home,self.warlords,
                  allowed,errors,presence,_dimensions(dims))
            if any(not value.is_contiguous() for value in args):raise ValueError("Declaration inputs must be contiguous; no hidden copy")
            _kernels().resident_land_attack_declarations(*(value if value.numel() else _dummy() for value in args),threads=B)
        return LandAttackDeclarations(state,relations,allowed,errors,presence)
