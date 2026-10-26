"""Resident packed State -> income accounting -> packed State on Apple GPU.

Only the accounting seam applyIncomeLedger is implemented. The caller must have
completed placement/repairs and reached its placement-phase call point. No phase,
political, surrender, history or RNG transition is invented here. Original maps
are retained in the packed source for atomic rollback; successful accounting
overwrites the income-component maps exactly as refreshIncome does.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch
from .income_ledger import IncomeLedgerTensorContext
from .metal_state_schema import METAL_STATE_SOURCE

PACKED_INPUT, ACCOUNTING_INPUT, WRONG_PHASE, PACKED_OUTPUT = 1, 2, 4, 8


@dataclass(frozen=True)
class ResidentIncomeInputs:
    territories: torch.Tensor
    nations: torch.Tensor
    ledger: torch.Tensor
    clock: torch.Tensor
    phases: torch.Tensor
    roots: torch.Tensor
    errors: torch.Tensor


@dataclass(frozen=True)
class ResidentIncomeResult:
    state: DeviceStateBatch
    errors: torch.Tensor
    accepted: torch.Tensor
    required_capacity: torch.Tensor


SOURCE = r"""
#include <metal_stdlib>
using namespace metal;
""" + METAL_STATE_SOURCE + r"""

inline bool income_container(thread const PackedStateView& v,long node,long tag,long count,thread bool& valid) {
    const long end=state_end(v,node,valid);
    if(!valid)return false;
    device const long* r=state_record(v,node);
    if(r[0]!=tag||r[1]<0||(count>=0&&r[1]!=count)||r[2]||r[3])valid=false;
    return valid&&end>node;
}
inline long income_index(device const long* ids,long count,long key) {
    for(long i=0;i<count;++i)if(ids[i]==key)return i;
    return -1;
}
inline long income_int(thread const PackedStateView& v,long node,thread bool& valid) {
    const long value=state_signed_value(v,node,valid);
    if(value<(-2147483647L-1L)||value>2147483647L)valid=false;
    return value;
}
inline long income_flag(thread const PackedStateView& v,long map,long key,thread bool& valid) {
    const long node=state_map_find_id(v,map,key,valid);
    return node<0?0:income_int(v,node,valid);
}
inline bool income_set_contains(thread const PackedStateView& v,long root,long key,thread bool& valid) {
    if(!income_container(v,root,8,-1,valid))return false;
    const long end=state_end(v,root,valid),count=state_record(v,root)[1];
    if(count>end-root-1){valid=false;return false;}
    long cursor=root+1;bool found=false;
    for(long entry=0;entry<count;++entry) {
        const long id=state_string_id(v,cursor,valid);
        found|=id==key;cursor=state_end(v,cursor,valid);
        if(!valid||cursor>end){valid=false;return false;}
    }
    if(cursor!=end)valid=false;
    return found;
}

kernel void extract_resident_income(
    device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],
    device const uchar* prefix_bytes [[buffer(2)]],device const long* prefix_offsets [[buffer(3)]],
    device const uchar* suffix_bytes [[buffer(4)]],device const long* suffix_offsets [[buffer(5)]],
    device const long* definition [[buffer(6)]],device const long* ids [[buffer(7)]],
    device long* territories [[buffer(8)]],device long* nations [[buffer(9)]],
    device long* ledger [[buffer(10)]],device long* clock [[buffer(11)]],
    device long* phases [[buffer(12)]],device long* roots [[buffer(13)]],
    device long* errors [[buffer(14)]],device const long* dims [[buffer(15)]],
    uint lane [[thread_position_in_grid]]) {
    const long B=dims[0],C=dims[1],N=dims[2],T=dims[3];
    if(long(lane)>=B)return;
    PackedStateView v{records+ulong(lane)*ulong(C)*5,lengths[lane],C,
        prefix_bytes,prefix_offsets,dims[4],dims[5],suffix_bytes,suffix_offsets,dims[6],dims[7]};
    PackedStateView def{definition,dims[8],dims[8],prefix_bytes,prefix_offsets,dims[4],dims[5],
        suffix_bytes,suffix_offsets,0,0};
    bool valid=v.length>0&&v.length<=C;
    for(long t=0;t<T;++t){const ulong out=(ulong(lane)*T+t)*4;
        territories[out]=0;territories[out+1]=-1;territories[out+2]=territories[out+3]=0;}
    for(long n=0;n<N;++n){const ulong out=(ulong(lane)*N+n)*6;
        for(long f=0;f<6;++f)nations[out+f]=0;nations[out+5]=-1;
        ledger[(ulong(lane)*N+n)*2]=ledger[(ulong(lane)*N+n)*2+1]=0;}
    clock[ulong(lane)*2]=-1;clock[ulong(lane)*2+1]=0;phases[lane]=-1;roots[lane]=-1;
    if(!valid){errors[lane]=1;return;}
    income_container(v,0,10,2,valid);
    const long state=state_child(v,0,0,valid);
    income_container(v,state,10,19,valid);roots[lane]=state;
    const long national=state_child(v,state,0,valid),land=state_child(v,state,1,valid);
    const long timer=state_child(v,state,7,valid),politics=state_child(v,state,8,valid);
    income_container(v,national,7,-1,valid);income_container(v,land,7,-1,valid);
    income_container(v,timer,10,6,valid);income_container(v,politics,10,11,valid);
    const long capitals=state_child(v,politics,7,valid),surrendered=state_child(v,politics,8,valid);
    const long turn_index=income_int(v,state_child(v,timer,1,valid),valid);
    phases[lane]=income_int(v,state_child(v,timer,2,valid),valid);
    clock[ulong(lane)*2+1]=state_boolean_value(v,state_child(v,timer,5,valid),valid);
    income_container(def,0,10,11,valid);
    const long order=state_child(def,0,6,valid);
    income_container(def,order,6,-1,valid);
    if(valid&&(turn_index<0||turn_index>=state_record(def,order)[1]))valid=false;
    if(valid){const long active=state_string_id(def,state_child(def,order,turn_index,valid),valid);
        clock[ulong(lane)*2]=income_index(ids,N,active);if(clock[ulong(lane)*2]<0)valid=false;}
    for(long t=0;valid&&t<T;++t) {
        const long root=state_map_find_id(v,land,ids[N+t],valid);
        if(root<0)continue;
        income_container(v,root,10,2,valid);
        const ulong out=(ulong(lane)*T+t)*4;territories[out]=1;
        bool possessed=false;const long owner=state_optional(v,state_child(v,root,0,valid),possessed,valid);
        if(possessed)territories[out+1]=income_index(ids,N,state_string_id(v,owner,valid));
        const long flags=state_child(v,root,1,valid);
        territories[out+2]=income_flag(v,flags,ids[N+T+3],valid);
        territories[out+3]=income_flag(v,flags,ids[N+T+4],valid);
    }
    for(long n=0;valid&&n<N;++n) {
        const long root=state_map_find_id(v,national,ids[n],valid);
        if(root<0)continue;
        income_container(v,root,10,12,valid);
        const ulong out=(ulong(lane)*N+n)*6;nations[out]=1;
        const long power=state_string_id(v,state_child(v,root,3,valid),valid);
        nations[out+2]=power==ids[N+T+2];
        bool account=false;const long cash=state_optional(v,state_child(v,root,4,valid),account,valid);
        nations[out+1]=account;
        if(account)ledger[(ulong(lane)*N+n)*2]=income_int(v,cash,valid);
        ledger[(ulong(lane)*N+n)*2+1]=state_boolean_value(v,state_child(v,root,6,valid),valid);
        nations[out+3]=income_set_contains(v,surrendered,ids[n],valid);
        const long capital=state_map_find_id(v,capitals,ids[n],valid);
        if(capital>=0){nations[out+4]=1;nations[out+5]=income_index(ids+N,T,state_string_id(v,capital,valid));}
    }
    errors[lane]=valid?0:1;
}

inline long income_copy(thread const PackedStateView& v,long root,device long* out,long cursor,long capacity,
                        thread bool& valid) {
    const long end=state_end(v,root,valid),size=end-root;
    if(!valid||size<1||cursor<0||cursor>capacity-size){valid=false;return cursor;}
    for(long i=root;i<end;++i){const long next=state_end(v,i,valid);
        if(!valid||next>end){valid=false;return cursor;}
        for(long field=0;field<4;++field)out[(cursor+i-root)*5+field]=state_record(v,i)[field];
        out[(cursor+i-root)*5+4]=next+cursor-root;}
    return cursor+size;
}
inline void income_scalar(device long* out,long node,long tag,long meta,ulong bits,long capacity,thread bool& valid) {
    if(node<0||node>=capacity){valid=false;return;}
    out[node*5]=tag;out[node*5+1]=meta;out[node*5+2]=long(bits&0xffffffffUL);
    out[node*5+3]=long(bits>>32);out[node*5+4]=node+1;
}
inline void income_finish(device long* out,long node,long end,long capacity,thread bool& valid) {
    if(node<0||node>=capacity||end>capacity){valid=false;return;}out[node*5+4]=end;
}

kernel void write_resident_income(
    device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],
    device const uchar* prefix_bytes [[buffer(2)]],device const long* prefix_offsets [[buffer(3)]],
    device const uchar* suffix_bytes [[buffer(4)]],device const long* suffix_offsets [[buffer(5)]],
    device const long* ids [[buffer(6)]],device const long* ledger [[buffer(7)]],
    device const long* components [[buffer(8)]],device const long* clock [[buffer(9)]],
    device const long* selected [[buffer(10)]],device long* blocks [[buffer(11)]],
    device long* block_lengths [[buffer(12)]],device long* errors [[buffer(13)]],
    device const long* dims [[buffer(14)]],uint lane [[thread_position_in_grid]]) {
    const long B=dims[0],C=dims[1],N=dims[2],T=dims[3],R=dims[9];
    if(long(lane)>=B)return;block_lengths[lane]=0;errors[lane]=0;if(!selected[lane])return;
    PackedStateView v{records+ulong(lane)*ulong(C)*5,lengths[lane],C,
        prefix_bytes,prefix_offsets,dims[4],dims[5],suffix_bytes,suffix_offsets,dims[6],dims[7]};
    device long* out=blocks+ulong(lane)*ulong(R)*5;bool valid=true;
    const long state=state_child(v,0,0,valid);income_container(v,state,10,19,valid);
    income_scalar(out,0,10,19,0,R,valid);long cursor=1;
    for(long field=0;valid&&field<19;++field) {
        const long original=state_child(v,state,field,valid);
        if(field==0) {
            income_container(v,original,7,-1,valid);if(!valid)break;
            const long count=state_record(v,original)[1],map_out=cursor++;
            income_scalar(out,map_out,7,count,0,R,valid);long entry=original+1;
            for(long item=0;valid&&item<count;++item) {
                const long id=state_string_id(v,entry,valid),n=income_index(ids,N,id);
                const long nation=state_end(v,entry,valid);
                if(n<0){valid=false;break;}
                cursor=income_copy(v,entry,out,cursor,R,valid);
                income_container(v,nation,10,12,valid);
                const long nation_out=cursor++;income_scalar(out,nation_out,10,12,0,R,valid);
                for(long f=0;valid&&f<12;++f) {
                    const long source=state_child(v,nation,f,valid),start=cursor;
                    if(f==5) {
                        const ulong c=(ulong(lane)*N+n)*4;
                        const bool territory=components[c]!=0,bonus=components[c+2]!=0;
                        const long target=cursor++;income_scalar(out,target,7,long(territory)+long(bonus),0,R,valid);
                        // Native std::map order: china_control_bonus < territorial.
                        if(bonus){income_scalar(out,cursor++,5,ids[N+T+1],0,R,valid);
                            income_scalar(out,cursor++,2,0,as_type<ulong>(components[c+3]),R,valid);}
                        if(territory){income_scalar(out,cursor++,5,ids[N+T],0,R,valid);
                            income_scalar(out,cursor++,2,0,as_type<ulong>(components[c+1]),R,valid);}
                        income_finish(out,target,cursor,R,valid);
                    } else {
                        cursor=income_copy(v,source,out,cursor,R,valid);
                        if(f==4){bool present=false;const long cash=state_optional(v,source,present,valid);
                            if(present)income_scalar(out,start+cash-source,2,0,as_type<ulong>(ledger[(ulong(lane)*N+n)*2]),R,valid);}
                        if(f==6)income_scalar(out,start,1,ledger[(ulong(lane)*N+n)*2+1],0,R,valid);
                    }
                }
                income_finish(out,nation_out,cursor,R,valid);entry=state_end(v,nation,valid);
            }
            if(valid&&entry!=state_end(v,original,valid))valid=false;
            income_finish(out,map_out,cursor,R,valid);
        } else {
            const long start=cursor;cursor=income_copy(v,original,out,cursor,R,valid);
            if(field==7){const long flag=state_child(v,original,5,valid);
                income_scalar(out,start+flag-original,1,clock[ulong(lane)*2+1],0,R,valid);}
        }
    }
    if(cursor>R)valid=false;
    income_finish(out,0,cursor,R,valid);block_lengths[lane]=valid?cursor:0;errors[lane]=valid?0:1;
}
"""

_library = None
_lock = threading.Lock()


@lru_cache(maxsize=16)
def _dimensions(values):
    return torch.tensor(values, dtype=torch.int64, device="mps")


@lru_cache(maxsize=1)
def _dummy():
    return torch.zeros(1, dtype=torch.int64, device="mps")


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:
                _library = torch.mps.compile_shader(SOURCE)
    return _library


class ResidentIncomeContext:
    """Shared indexed definition and income tables, prepared once on import."""
    def __init__(self, state_context, native_income_context):
        if state_context.device.type != "mps":
            raise ValueError("Resident packed income currently requires Apple MPS; no CPU fallback")
        if state_context.definition_fingerprint != native_income_context.definition_fingerprint:
            raise ValueError("Resident state/income definitions differ")
        self.state_context = state_context
        self.ledger_context = IncomeLedgerTensorContext(native_income_context, state_context.device)
        names = (*self.ledger_context.nation_ids, *self.ledger_context.income.territory_ids,
                 "territorial", "china_control_bonus", "major", "city_ipp_lost", "city_damage")
        self.ids = torch.tensor(state_context.prefix_lookup_ids(names), dtype=torch.int64, device=state_context.device)

    def _layout(self, state):
        if not isinstance(state, DeviceStateBatch) or state.context.identity != self.state_context.identity:
            raise ValueError("Resident income state/wire context differs")
        state._metadata()
        if state.device.type != "mps":
            raise ValueError("Resident income requires Apple MPS")
        from .device_state import _device
        _device(state.device)
        values = (state.records, state.lengths, state.context.records, state.context.string_bytes,
                  state.context.string_offsets, state.string_bytes, state.string_offsets, self.ids)
        if any(not value.is_contiguous() for value in values):
            raise ValueError("Resident income requires contiguous state buffers; no hidden copy")
        N, T = len(self.ledger_context.nation_ids), len(self.ledger_context.income.territory_ids)
        dims = (state.lane_count, state.records.shape[1], N, T, state.context.string_count,
                state.context.string_bytes.shape[0], state.string_offsets.shape[0]-1, state.string_bytes.shape[0],
                state.context.records.shape[0], state.records.shape[1]+4*N)
        return values, dims

    def extract(self, state):
        values, dims = self._layout(state)
        B, _, N, T = dims[:4]
        alloc = lambda *shape: torch.empty(shape, dtype=torch.int64, device=state.device)
        result = ResidentIncomeInputs(alloc(B,T,4),alloc(B,N,6),alloc(B,N,2),alloc(B,2),alloc(B),alloc(B),alloc(B))
        if B:
            # Explicit ordering matches the shared packed view's prefix/suffix.
            records,lengths,definition,prefix,poffsets,suffix,soffsets,ids=values
            args=(records,lengths,prefix,poffsets,suffix,soffsets,definition,ids,
                  result.territories,result.nations,result.ledger,result.clock,result.phases,result.roots,result.errors,_dimensions(dims))
            _kernels().extract_resident_income(*(value if value.numel() else _dummy() for value in args),threads=B)
        return result

    def apply(self, state, selected=None):
        """Atomically apply only the accounting seam to selected placement lanes.

        Selection and errors remain resident; the selected cohort is all-or-none.
        Failed lanes retain the entire original State, history and all RNG bits.
        """
        from .device_state_edits import replace_subtrees
        values,dims=self._layout(state)
        B,C,N,T=dims[:4]
        if selected is None:
            selected=torch.ones(B,dtype=torch.bool,device=state.device)
        if not isinstance(selected,torch.Tensor) or selected.dtype!=torch.bool or selected.device!=state.device or selected.shape!=(B,):
            raise ValueError("Resident income selection must be a complete device bool vector")
        inputs=self.extract(state)
        # Prior component values are write-only at successful refreshIncome;
        # on error, the original packed State is retained without reading or
        # losing custom component keys. Only the two new component slots matter.
        old_components=torch.zeros((B,N,2,2),dtype=torch.int64,device=state.device)
        proposal=self.ledger_context.compute(inputs.territories,inputs.nations,inputs.ledger,old_components,inputs.clock)
        errors=((inputs.errors!=0)|(state.errors!=0)).to(torch.int64)*PACKED_INPUT
        errors|=(proposal.error!=0).to(torch.int64)*ACCOUNTING_INPUT
        errors|=(inputs.phases!=4).to(torch.int64)*WRONG_PHASE
        errors=torch.where(selected,errors,0)
        cohort_ok=~(errors!=0).any()
        writing=(selected&cohort_ok).to(torch.int64)
        blocks=torch.zeros((B,dims[9],5),dtype=torch.int64,device=state.device)
        lengths=torch.zeros(B,dtype=torch.int64,device=state.device)
        write_errors=torch.zeros_like(lengths)
        if B:
            records,source_lengths,_,prefix,poffsets,suffix,soffsets,ids=values
            args=(records,source_lengths,prefix,poffsets,suffix,soffsets,ids,proposal.ledger,proposal.components,proposal.clock,
                  writing,blocks,lengths,write_errors,_dimensions(dims))
            _kernels().write_resident_income(*(value if value.numel() else _dummy() for value in args),threads=B)
        errors|=torch.where(selected,(write_errors!=0).to(torch.int64)*PACKED_OUTPUT,0)
        cohort_ok=~(errors!=0).any()
        edited=replace_subtrees(state,inputs.roots,blocks,lengths,selected&cohort_ok,capacity=dims[9])
        errors|=edited.errors
        return ResidentIncomeResult(edited.state,errors,edited.accepted,edited.required_capacity)
