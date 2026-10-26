"""Exact read-only native unit statistics from complete resident campaign state.

Damage tables and ordered rule/technology descriptors are compiled once from the
primary native Catalog. Current technologies and flags are read on the GPU.
No state, history or random bits are modified; this is not a combat transition.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch
from .metal_state_schema import METAL_STATE_SOURCE

STAT_NAMES=("attack","defense","attack_dice","defense_dice","movement","bombardment",
            "bombardment_dice","cargo_capacity","carrier_capacity")
LOOKUP_ERROR,NATIVE_ERROR,PACKED_ERROR,INT_OVERFLOW,CAPACITY_ERROR=1,2,3,4,5


@dataclass(frozen=True)
class ResidentCatalogStatsResult:
    source: DeviceStateBatch
    requests: torch.Tensor       # [Q,5]: lane,type token,damage,owner token,zone token/-1
    stats: torch.Tensor          # [Q,9,2]: optional presence/value; dice always present
    errors: torch.Tensor
    message_ids: torch.Tensor
    count: torch.Tensor          # [1] usable query count; capacity failure never truncates
    required_count: torch.Tensor
    batch_error: torch.Tensor
    unit_ids: torch.Tensor       # [Q], -1 for explicit hypothetical queries
    unit_roots: torch.Tensor     # [Q], -1 for explicit hypothetical queries


SOURCE="#include <metal_stdlib>\nusing namespace metal;\n"+METAL_STATE_SOURCE+r'''
inline bool stats_record(thread const PackedStateView& v,long at,long tag,long count,thread bool& valid){
 const long end=state_end(v,at,valid);if(!valid)return false;
 device const long* row=state_record(v,at);
 if(row[0]!=tag||row[1]<0||(count>=0&&row[1]!=count)||row[2]||row[3])valid=false;
 return valid&&end>at;
}
inline long stats_index(device const long* indices,device const long* tokens,long count,long id){
 for(long i=0;i<count;++i)if(tokens[indices[i]]==id)return i;return -1;
}
inline bool stats_id(thread const PackedStateView& v,long id){return id>=0&&id<v.prefix_count+v.suffix_count;}
inline bool stats_map_flag(thread const PackedStateView& v,long map,long key,thread bool& present,thread bool& valid){
 const long node=state_map_find_id(v,map,key,valid);present=node>=0;
 return present?state_signed_value(v,node,valid)!=0:false;
}
struct StatsRuntime {
 PackedStateView view;
 device const long* tokens;
 device const long* flags;
 long global_flags,game_flags,turn_flags;
 bool major,home,zone_provided,ussr_present,closed;
};
inline bool stats_flags(thread const StatsRuntime& rt,device const long* instruction,thread long& error,thread long& message){
 if(instruction[4]){error=instruction[4];message=instruction[5];return false;}
 for(long i=0;i<instruction[3];++i){
   device const long* flag=rt.flags+(instruction[2]+i)*4;
   if(flag[2]){error=flag[2];message=flag[3];return false;}
   const long kind=flag[1];bool value=false,valid=true,present=false;
   if(kind==3&&!rt.ussr_present)return false;
   if(kind==4&&rt.closed)return false;
   if(kind==1)value=rt.major;
   else if(kind==2&&rt.zone_provided)value=rt.home;
   else {
     const long key=rt.tokens[flag[0]];
     value=stats_map_flag(rt.view,rt.global_flags,key,present,valid);
     const bool game=stats_map_flag(rt.view,rt.game_flags,key,present,valid);if(present)value=game;
     const bool turn=stats_map_flag(rt.view,rt.turn_flags,key,present,valid);if(present)value=turn;
   }
   if(!valid){error=3;return false;}if(!value)return false;
 }
 return true;
}
inline bool stats_instruction(thread const StatsRuntime& rt,device const long* instruction,bool assignment,
 thread long* values,thread long& error,thread long& message){
 if(instruction[0]){error=instruction[0];message=instruction[1];return false;}
 if(!stats_flags(rt,instruction,error,message))return error==0;
 if(instruction[7]){error=instruction[7];message=instruction[8];return false;}
 if(instruction[10]){error=instruction[10];message=instruction[11];return false;}
 const long stat=instruction[9],add=instruction[6];
 if(stat<0||stat>=9){error=3;return false;}
 if(assignment){values[stat*2]=1;values[stat*2+1]=add;}
 else if(values[stat*2]){
   const long sum=values[stat*2+1]+add;
   if(sum<INT_MIN||sum>INT_MAX){error=4;return false;}values[stat*2+1]=sum;
 }
 return true;
}
kernel void query_catalog_stats(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* source_errors[[buffer(2)]],device const long* requests[[buffer(3)]],
 device const long* count[[buffer(4)]],device const long* inherited_batch[[buffer(5)]],
 device long* output[[buffer(6)]],device long* errors[[buffer(7)]],device long* messages[[buffer(8)]],
 device long* batch_error[[buffer(9)]],device const long* dims[[buffer(10)]],
 device const uchar* prefix_bytes[[buffer(11)]],device const long* prefix_offsets[[buffer(12)]],
 device const uchar* suffix_bytes[[buffer(13)]],device const long* suffix_offsets[[buffer(14)]],
 device const long* usage[[buffer(15)]],device const long* tokens[[buffer(16)]],
 device const long* unit_tokens[[buffer(17)]],device const long* tech_tokens[[buffer(18)]],
 device const long* faction_tokens[[buffer(19)]],device const long* homes[[buffer(20)]],
 device const long* home_tokens[[buffer(21)]],device const long* units[[buffer(22)]],
 device const long* states[[buffer(23)]],device const long* conditionals[[buffer(24)]],
 device const long* techs[[buffer(25)]],device const long* modifiers[[buffer(26)]],
 device const long* matches[[buffer(27)]],device const long* flags[[buffer(28)]],uint row[[thread_position_in_grid]]){
 const long Q=dims[0],B=dims[1],C=dims[2],U=dims[7],K=dims[8],N=dims[9],actual=count[0];
 const bool bad_count=actual<0||actual>Q;
 if(row==0)batch_error[0]=bad_count?3:inherited_batch[0];
 if(long(row)>=Q)return;
 for(long i=0;i<18;++i)output[ulong(row)*18+i]=0;errors[row]=messages[row]=0;
 if(bad_count||inherited_batch[0]||long(row)>=actual)return;
 device const long* query=requests+ulong(row)*5;
 const long lane=query[0],type=query[1],damage=query[2],owner=query[3],zone=query[4];
 if(lane<0||lane>=B){errors[row]=3;return;}
 bool valid=true;
 PackedStateView v=make_packed_state_view(records+ulong(lane)*ulong(C)*5,lengths[lane],C,
   prefix_bytes,prefix_offsets,dims[3],dims[4],suffix_bytes,suffix_offsets,dims[5],dims[6],usage,valid);
 if(!valid||source_errors[lane]||v.length<=0||v.length>C||damage<INT_MIN||damage>INT_MAX||
    !stats_id(v,type)||!stats_id(v,owner)||(zone!=-1&&!stats_id(v,zone))){errors[row]=3;return;}
 stats_record(v,0,10,2,valid);const long state=state_child(v,0,0,valid);stats_record(v,state,10,19,valid);
 const long nations=state_child(v,state,0,valid),global=state_child(v,state,15,valid);
 const long nation=state_map_find_id(v,nations,owner,valid);
 if(!valid){errors[row]=3;return;}if(nation<0){errors[row]=1;messages[row]=dims[10];return;}
 stats_record(v,nation,10,12,valid);
 const long power=state_string_id(v,state_child(v,nation,3,valid),valid);
 const bool major=state_string_id_equals(v,power,"major",5,valid);
 const long faction=stats_index(faction_tokens,tokens,N,owner);bool home=false;
 if(zone!=-1){
   if(faction<0){errors[row]=1;messages[row]=dims[10];return;}
   if(homes[faction*3])for(long i=0;i<homes[faction*3+2];++i)home|=tokens[home_tokens[homes[faction*3+1]+i]]==zone;
 }
 const long game=state_child(v,nation,11,valid),turn=state_child(v,nation,10,valid),technology=state_child(v,nation,7,valid);
 const bool ussr=state_map_find_literal(v,nations,"ussr",4,valid)>=0;
 if(!valid){errors[row]=3;return;}
 StatsRuntime rt{v,tokens,flags,global,game,turn,major,home,zone!=-1,ussr,dims[11]!=0};
 const long unit=stats_index(unit_tokens,tokens,U,type);
 if(unit<0){errors[row]=1;messages[row]=dims[10];return;}
 device const long* meta=units+unit*4;long state_index=-1;
 for(long i=0;i<meta[1];++i)if(states[(meta[0]+i)*19]==damage){state_index=meta[0]+i;break;}
 if(state_index<0){errors[row]=1;messages[row]=dims[10];return;}
 long values[18];for(long i=0;i<18;++i)values[i]=states[state_index*19+1+i];
 long error=0,message=0;
 for(long i=0;i<meta[3];++i)if(!stats_instruction(rt,conditionals+(meta[2]+i)*12,true,values,error,message))break;
 if(!error){
   stats_record(v,technology,7,-1,valid);
   const long end=state_end(v,technology,valid);long cursor=technology+1;
   const long amount=valid?state_record(v,technology)[1]:0;
   for(long i=0;valid&&!error&&i<amount;++i){
     const long tech_id=state_string_id(v,cursor,valid),value=state_end(v,cursor,valid);
     const long stage=state_signed_value(v,value,valid);cursor=state_end(v,value,valid);
     if(!valid||cursor>end){valid=false;break;}if(stage!=4)continue;
     const long tech=stats_index(tech_tokens,tokens,K,tech_id);
     if(tech<0){error=1;message=dims[10];break;}
     device const long* tm=techs+tech*4;
     if(tm[2]){error=tm[2];message=tm[3];break;}
     for(long j=0;j<tm[1];++j){const long m=tm[0]+j;device const long* instruction=modifiers+m*12;
       if(instruction[0]){error=instruction[0];message=instruction[1];break;}
       if(matches[m*U+unit]&&!stats_instruction(rt,instruction,false,values,error,message))break;
     }
   }
   if(valid&&!error&&cursor!=end)valid=false;
 }
 if(!valid&&!error)error=3;
 errors[row]=error;messages[row]=message;if(error)return;
 for(long i=0;i<18;++i)output[ulong(row)*18+i]=values[i];
}

kernel void count_catalog_units(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* source_errors[[buffer(2)]],device const uchar* prefix_bytes[[buffer(3)]],
 device const long* prefix_offsets[[buffer(4)]],device const uchar* suffix_bytes[[buffer(5)]],
 device const long* suffix_offsets[[buffer(6)]],device const long* usage[[buffer(7)]],
 device long* counts[[buffer(8)]],device long* lane_errors[[buffer(9)]],device const long* dims[[buffer(10)]],
 uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1];if(long(lane)>=B)return;counts[lane]=0;lane_errors[lane]=0;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*ulong(C)*5,lengths[lane],C,
   prefix_bytes,prefix_offsets,dims[2],dims[3],suffix_bytes,suffix_offsets,dims[4],dims[5],usage,valid);
 if(!valid||source_errors[lane]){lane_errors[lane]=3;return;}
 stats_record(v,0,10,2,valid);const long state=state_child(v,0,0,valid);stats_record(v,state,10,19,valid);
 const long map=state_child(v,state,2,valid);stats_record(v,map,7,-1,valid);
 if(valid)counts[lane]=state_record(v,map)[1];
 if(!valid||counts[lane]>(state_end(v,map,valid)-map-1)/16){counts[lane]=0;lane_errors[lane]=3;}
}
kernel void rank_catalog_units(device const long* counts[[buffer(0)]],device const long* lane_errors[[buffer(1)]],
 device long* ranks[[buffer(2)]],device long* count[[buffer(3)]],device long* required[[buffer(4)]],
 device long* batch_error[[buffer(5)]],device const long* dims[[buffer(6)]],uint row[[thread_position_in_grid]]){
 if(row)return;long total=0,error=0;
 for(long lane=0;lane<dims[0];++lane){ranks[lane]=total;
   if(lane_errors[lane]||counts[lane]<0||counts[lane]>LONG_MAX-total)error=3;
   else total+=counts[lane];}
 required[0]=total;if(!error&&total>dims[6])error=5;
 batch_error[0]=error;count[0]=error?0:total;
}
kernel void write_catalog_units(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const uchar* prefix_bytes[[buffer(2)]],device const long* prefix_offsets[[buffer(3)]],
 device const uchar* suffix_bytes[[buffer(4)]],device const long* suffix_offsets[[buffer(5)]],
 device const long* usage[[buffer(6)]],device const long* counts[[buffer(7)]],device const long* ranks[[buffer(8)]],
 device const long* batch_error[[buffer(9)]],device long* requests[[buffer(10)]],device long* ids[[buffer(11)]],
 device long* roots[[buffer(12)]],device long* lane_errors[[buffer(13)]],device const long* dims[[buffer(14)]],
 uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1];if(long(lane)>=B||batch_error[0])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*ulong(C)*5,lengths[lane],C,
   prefix_bytes,prefix_offsets,dims[2],dims[3],suffix_bytes,suffix_offsets,dims[4],dims[5],usage,valid);
 const long state=state_child(v,0,0,valid),map=state_child(v,state,2,valid),end=state_end(v,map,valid);
 long cursor=map+1;
 for(long i=0;valid&&i<counts[lane];++i){
   const long id=state_string_id(v,cursor,valid),unit=state_end(v,cursor,valid);stats_record(v,unit,10,14,valid);
   long values[5]={long(lane),state_string_id(v,state_child(v,unit,1,valid),valid),
     state_signed_value(v,state_child(v,unit,10,valid),valid),state_string_id(v,state_child(v,unit,2,valid),valid),
     state_string_id(v,state_child(v,unit,3,valid),valid)};
   const long row=ranks[lane]+i;
   if(!valid||row<0||row>=dims[6]){valid=false;break;}
   for(long field=0;field<5;++field)requests[row*5+field]=values[field];ids[row]=id;roots[row]=unit;
   cursor=state_end(v,unit,valid);if(cursor>end)valid=false;
 }
 if(!valid||cursor!=end)lane_errors[lane]=3;
}
kernel void finalize_catalog_units(device const long* lane_errors[[buffer(0)]],device long* count[[buffer(1)]],
 device long* batch_error[[buffer(2)]],device const long* dims[[buffer(3)]],uint row[[thread_position_in_grid]]){
 if(row)return;for(long lane=0;lane<dims[0];++lane)if(lane_errors[lane]){batch_error[0]=3;count[0]=0;return;}
}
'''
_library=None
_lock=threading.Lock()


@lru_cache(maxsize=32)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device="mps")


@lru_cache(maxsize=1)
def _dummy():return torch.empty(1,dtype=torch.int64,device="mps")


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    return _library


def _call(kernel,values,threads):
    kernel(*(value if value.numel() else _dummy() for value in values),threads=max(threads,1))


class ResidentCatalogStatsContext:
    def __init__(self,state_context,native):
        if state_context.device.type!="mps":raise ValueError("Resident catalog stats require Apple MPS; no CPU fallback")
        if (state_context.definition_fingerprint!=native.definition_fingerprint or
                state_context.wire_context_fingerprint!=native.wire_context_fingerprint):
            raise ValueError("Catalog statistics source/wire context differs")
        self.state_context=state_context
        self.catalog_fingerprint=native.catalog_fingerprint
        self.unit_types=tuple(native.unit_types);self.technologies=tuple(native.technologies);self.factions=tuple(native.factions)
        self.messages=tuple(native.messages);self.lookup_message=native.lookup_message;self.closed_theatre=native.closed_theatre
        self.tokens=torch.tensor(state_context.prefix_lookup_ids(native.strings),dtype=torch.int64,device=state_context.device)
        for name in ("unit_token","technology_token","faction_token","home_token","unit","state","home","technology",
                     "conditional","modifier","match","flag"):
            setattr(self,name,torch.tensor(getattr(native,name+"_array")(),dtype=torch.int64,device=state_context.device))

    def _layout(self,state):
        if not isinstance(state,DeviceStateBatch) or state.context.identity!=self.state_context.identity:
            raise ValueError("Catalog-stat state/source context differs")
        state._metadata()
        if state.device.type!="mps":raise ValueError("Resident catalog stats require explicit Apple MPS")
        from .device_state import _device
        _device(state.device)
        tensors=(state.records,state.lengths,state.errors,state.context.string_bytes,state.context.string_offsets,
                 state.string_bytes,state.string_offsets,state.suffix_usage,self.tokens,self.unit_token,self.technology_token,
                 self.faction_token,self.home_token,self.unit,self.state,self.home,self.technology,self.conditional,
                 self.modifier,self.match,self.flag)
        if any(value.device!=state.device or not value.is_contiguous() for value in tensors):
            raise ValueError("Catalog-stat buffers must retain complete contiguous resident layouts")
        return state.lane_count,state.records.shape[1]

    def query(self,state,requests,*,count=None):
        """Query explicit resident lane/type/damage/owner/optional-zone rows.

        Type, owner and zone address the state's exact shared byte namespace.
        The -1 zone means catalogContext(...,nullopt), not an unknown territory.
        """
        self._layout(state)
        if (not isinstance(requests,torch.Tensor) or requests.dtype!=torch.int64 or requests.ndim!=2 or
            requests.shape[1]!=5 or requests.device!=state.device or not requests.is_contiguous()):
            raise ValueError("Catalog-stat requests require contiguous resident int64[capacity,5]")
        Q=requests.shape[0]
        if count is None:count=torch.full((1,),Q,dtype=torch.int64,device=state.device)
        self._vector(state,count,(1,),torch.int64)
        return self._query(state,requests,count,count,torch.zeros(1,dtype=torch.int64,device=state.device),
                           torch.full((Q,),-1,dtype=torch.int64,device=state.device),
                           torch.full((Q,),-1,dtype=torch.int64,device=state.device))

    @staticmethod
    def _vector(state,value,shape,dtype):
        if (not isinstance(value,torch.Tensor) or value.device!=state.device or value.dtype!=dtype or
                tuple(value.shape)!=shape or not value.is_contiguous()):
            raise ValueError("Catalog-stat query metadata must be complete contiguous resident tensors")

    def _query(self,state,requests,count,required,inherited,ids,roots):
        B,C=self._layout(state);Q=requests.shape[0]
        if Q>2**32-1 or Q*max(C,1)*19>2**63-1:raise OverflowError("Catalog-stat query allocation is not representable; no truncation")
        stats=torch.zeros((Q,9,2),dtype=torch.int64,device=state.device)
        errors=torch.zeros(Q,dtype=torch.int64,device=state.device);messages=torch.zeros_like(errors)
        batch_error=torch.zeros(1,dtype=torch.int64,device=state.device)
        dims=_dimensions((Q,B,C,state.context.string_count,state.context.string_bytes.numel(),state.string_offsets.numel()-1,
            state.string_bytes.numel(),len(self.unit_types),len(self.technologies),len(self.factions),self.lookup_message,int(self.closed_theatre)))
        args=(state.records,state.lengths,state.errors,requests,count,inherited,stats,errors,messages,batch_error,dims,
              state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage,
              self.tokens,self.unit_token,self.technology_token,self.faction_token,self.home,self.home_token,self.unit,self.state,
              self.conditional,self.technology,self.modifier,self.match,self.flag)
        _call(_kernels().query_catalog_stats,args,Q)
        return ResidentCatalogStatsResult(state,requests,stats,errors,messages,count,required,batch_error,ids,roots)

    def all_units(self,state,*,capacity=None):
        """Query every current unit in native lane/map order, including new IDs.

        Default allocation uses the complete arena's proven minimum16 records
        per map entry+UnitState. An explicitly smaller capacity returns the exact
        required count and no usable partial inventory. It is an allocation
        bound, never a gameplay/entity limit.
        """
        B,C=self._layout(state)
        if capacity is None:capacity=B*(C//16)
        if type(capacity) is not int or capacity<0 or capacity>2**32-1 or capacity*5>2**63-1:
            raise ValueError("Catalog-stat inventory capacity must be a representable nonnegative allocation")
        device=state.device
        requests=torch.zeros((capacity,5),dtype=torch.int64,device=device)
        ids=torch.full((capacity,),-1,dtype=torch.int64,device=device);roots=torch.full_like(ids,-1)
        counts=torch.zeros(B,dtype=torch.int64,device=device);lane_errors=torch.zeros_like(counts);ranks=torch.zeros_like(counts)
        count=torch.zeros(1,dtype=torch.int64,device=device);required=torch.zeros_like(count);batch_error=torch.zeros_like(count)
        dims=_dimensions((B,C,state.context.string_count,state.context.string_bytes.numel(),state.string_offsets.numel()-1,
                          state.string_bytes.numel(),capacity))
        if B:
            _call(_kernels().count_catalog_units,(state.records,state.lengths,state.errors,state.context.string_bytes,
                state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage,counts,lane_errors,dims),B)
        _call(_kernels().rank_catalog_units,(counts,lane_errors,ranks,count,required,batch_error,dims),1)
        if B:
            _call(_kernels().write_catalog_units,(state.records,state.lengths,state.context.string_bytes,state.context.string_offsets,
                state.string_bytes,state.string_offsets,state.suffix_usage,counts,ranks,batch_error,requests,ids,roots,lane_errors,dims),B)
        _call(_kernels().finalize_catalog_units,(lane_errors,count,batch_error,dims),1)
        return self._query(state,requests,count,required,batch_error,ids,roots)

    def inspect(self,result):
        """Explicit diagnostic boundary; no failed/partial rows become stats."""
        if result.source.context.identity!=self.state_context.identity:raise ValueError("Catalog-stat result source differs")
        batch=result.batch_error.detach().cpu().item()
        if batch==CAPACITY_ERROR:raise BufferError("Catalog-stat inventory capacity insufficient; retry required_count")
        if batch:raise ValueError("Malformed catalog-stat inventory/count")
        count=result.count.detach().cpu().item()
        errors=result.errors.detach().cpu().tolist()[:count];messages=result.message_ids.detach().cpu().tolist()[:count]
        values=result.stats.detach().cpu().tolist()[:count]
        output=[]
        for error,message,stats in zip(errors,messages,values,strict=True):
            if error:
                why=self.messages[message] if 0<=message<len(self.messages) else "Unknown catalog-stat error"
                if error==LOOKUP_ERROR:raise IndexError(why)
                if error==NATIVE_ERROR:raise RuntimeError(why)
                if error==INT_OVERFLOW:raise OverflowError("Outside defined native signed-int statistic arithmetic")
                raise ValueError("Malformed resident catalog-stat input")
            output.append({name:value if present else None for name,(present,value) in zip(STAT_NAMES,stats,strict=True)})
        return output
