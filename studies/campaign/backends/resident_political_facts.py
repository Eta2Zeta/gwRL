"""Exact ordered political-refresh facts, promotion marking and allies writes.

These independent internal seams do not evolve movement, terminate a truce,
queue choices/awards, surrender a nation, refresh income or run Engine hooks.
The full refresh orchestrator owns their original order. In particular, civil
flags are computed at each Chinese faction's original point, not after a later
surrender removes other factions' carried Units.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_state_edits import replace_subtrees
from .device_map_edits import SOURCE as MAP_SOURCE

LITERALS=("possessed_land_ipp","civil_war_eliminated","evolved_turn_serial","evolved_during_own_turn",
          "objective_evolution","objective_one_china","major","city_ipp_lost","city_damage","ccp","kmt")


@dataclass(frozen=True)
class PoliticalFactsResult:
    state:DeviceStateBatch
    errors:torch.Tensor
    message_ids:torch.Tensor
    promoted:torch.Tensor
    possessed_ipp:torch.Tensor  # [B,N]; -1 when this native path did not read it.
    land_counts:torch.Tensor
    has_units:torch.Tensor
    required_state_capacity:torch.Tensor
    required_block_capacity:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE=MAP_SOURCE+r'''
inline bool pf_container(thread const PackedStateView& v,long n,long tag,long count,thread bool& ok){
 const long end=state_end(v,n,ok);if(!ok)return false;device const long* r=state_record(v,n);
 if(r[0]!=tag||r[1]<0||r[1]>(tag==7?(end-n-1)/2:end-n-1)||(count>=0&&r[1]!=count)||r[2]||r[3])ok=false;return ok;
}
inline long pf_index(device const long* ids,long count,long id){for(long i=0;i<count;++i)if(ids[i]==id)return i;return -1;}
inline long pf_int(thread const PackedStateView& v,long n,thread bool& ok){const long value=state_signed_value(v,n,ok);
 if(value<INT_MIN||value>INT_MAX)ok=false;return value;}
inline long pf_flag(thread const PackedStateView& v,long map,long key,thread bool& ok){
 const long n=state_map_find_id(v,map,key,ok);return n<0?0:pf_int(v,n,ok);
}
inline bool pf_contains(thread const PackedStateView& v,long set,long key,thread bool& ok){
 pf_container(v,set,8,-1,ok);long cursor=set+1;for(long i=0;ok&&i<state_record(v,set)[1];++i){
   if(state_string_id(v,cursor,ok)==key)return true;cursor=state_end(v,cursor,ok);}return false;
}
inline long pf_possessor(thread const PackedStateView& v,long territory,thread bool& ok){bool yes=false;
 const long n=state_optional(v,state_child(v,territory,0,ok),yes,ok);return yes?state_string_id(v,n,ok):-1;
}
inline long pf_total(thread const PackedStateView& v,long state,long owner,device const long* zones,long T,
 device const long* ipp,device const long* labels,thread long& count,thread long& error,thread long& message,thread bool& ok){
 const long land=state_child(v,state,1,ok);pf_container(v,land,7,-1,ok);long cursor=land+1,total=0;count=0;
 for(long i=0;ok&&i<state_record(v,land)[1];++i){const long zone=state_string_id(v,cursor,ok),territory=cursor+1;
   pf_container(v,territory,10,2,ok);if(pf_possessor(v,territory,ok)==owner){++count;const long t=pf_index(zones,T,zone);
     if(t<0){error=2;return total;}device const long* base=ipp+t*3;if(base[1]){error=base[1];message=base[2];return total;}
     const long flags=state_child(v,territory,1,ok);pf_container(v,flags,7,-1,ok);
     const long lost=pf_flag(v,flags,labels[7],ok),damage=pf_flag(v,flags,labels[8],ok);
     const long raw=base[0]-max(lost,damage/20);if(!ok)return total;
     if(raw<INT_MIN||raw>INT_MAX){error=4;return total;}total+=max(0L,raw);
     if(total>INT_MAX){error=4;return total;}}
   cursor=state_end(v,territory,ok);}
 return total;
}
kernel void political_facts_plan(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* inherited[[buffer(2)]],device const long* owners[[buffer(3)]],device const bool* selected[[buffer(4)]],
 device const uchar* prefix[[buffer(5)]],device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],
 device const long* soffsets[[buffer(8)]],device const long* usage[[buffer(9)]],device const long* nation_ids[[buffer(10)]],
 device const long* zone_ids[[buffer(11)]],device const long* ipp[[buffer(12)]],device const long* home[[buffer(13)]],
 device const long* labels[[buffer(14)]],device const long* definition[[buffer(15)]],device const long* pairs[[buffer(16)]],
 device const long* pair_errors[[buffer(17)]],device long* changes[[buffer(18)]],device long* facts[[buffer(19)]],
 device bool* promoted[[buffer(20)]],device long* roots[[buffer(21)]],device long* errors[[buffer(22)]],
 device long* messages[[buffer(23)]],device const long* dims[[buffer(24)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],N=dims[2],T=dims[3],mode=dims[9];if(long(lane)>=B)return;
 errors[lane]=0;messages[lane]=-1;roots[lane]=-1;promoted[lane]=false;
 device long* rows=changes+ulong(lane)*N*7;device long* values=facts+ulong(lane)*N*3;
 for(long n=0;n<N;++n){for(long f=0;f<7;++f)rows[n*7+f]=0;rows[n*7]=-1;for(long f=0;f<3;++f)values[n*3+f]=-1;}
 if(!selected[lane])return;bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
 prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,ok);
 if(inherited[lane])ok=false;pf_container(v,0,10,2,ok);const long state=state_child(v,0,0,ok);pf_container(v,state,10,19,ok);
 const long nations=state_child(v,state,0,ok);pf_container(v,nations,7,-1,ok);roots[lane]=nations;
 long cursor=nations+1;for(long i=0;ok&&i<state_record(v,nations)[1];++i){const long id=state_string_id(v,cursor,ok),nation=cursor+1;
   pf_container(v,nation,10,12,ok);const long n=pf_index(nation_ids,N,id);if(n<0){errors[lane]=1;return;}rows[n*7]=nation;cursor=state_end(v,nation,ok);}
 if(!ok){errors[lane]=3;return;}
 if(mode==0){for(long n=0;n<N;++n)if(rows[n*7]>=0){long count=0,error=0,message=-1;
     const long total=pf_total(v,state,nation_ids[n],zone_ids,T,ipp,labels,count,error,message,ok);
     values[n*3]=total;values[n*3+1]=count;if(!ok){errors[lane]=3;return;}if(error){errors[lane]=error;messages[lane]=message;return;}
     rows[n*7+1]=1;rows[n*7+2]=total;}
 }else if(mode==1||mode==2){const long n=pf_index(nation_ids,N,owners[lane]);if(n<0||rows[n*7]<0){errors[lane]=1;return;}
   device long* row=rows+n*7;const long nation=row[0];
   if(mode==1){const long units=state_child(v,state,2,ok);pf_container(v,units,7,-1,ok);cursor=units+1;bool any=false;
     for(long i=0;ok&&i<state_record(v,units)[1];++i){const long unit=cursor+1;pf_container(v,unit,10,14,ok);
       if(state_string_id(v,state_child(v,unit,2,ok),ok)==owners[lane]){any=true;break;}cursor=state_end(v,unit,ok);}
     if(!ok){errors[lane]=3;return;}values[n*3+2]=any?1:0;row[1]=2;row[3]=any?0:1;
   }else{if(state_string_equals(v,state_child(v,nation,3,ok),"major",5,ok)){if(!ok)errors[lane]=3;return;}
     const long politics=state_child(v,state,8,ok);if(pf_contains(v,state_child(v,politics,8,ok),owners[lane],ok)){if(!ok)errors[lane]=3;return;}
     long count=0,error=0,message=-1;const long total=pf_total(v,state,owners[lane],zone_ids,T,ipp,labels,count,error,message,ok);
     values[n*3]=total;values[n*3+1]=count;if(!ok){errors[lane]=3;return;}if(error){errors[lane]=error;messages[lane]=message;return;}if(total<13)return;
     // Native assigns major first, then validates the execution counter. On an
     // exception the public selected cohort is rolled back as one transaction.
     row[1]=4;const long clock=state_child(v,state,7,ok);const ulong serial=state_unsigned_value(v,state_child(v,clock,4,ok),ok);
     if(!ok){errors[lane]=3;return;}if(serial>ulong(INT_MAX)){errors[lane]=2;return;}row[4]=long(serial);
     auto d=v;d.records=definition;d.length=d.capacity=dims[8];d.suffix_count=d.suffix_bytes_length=0;
     const long order=state_child(d,0,6,ok),index=pf_int(v,state_child(v,clock,1,ok),ok);pf_container(d,order,6,-1,ok);
     if(!ok||index<0||index>=state_record(d,order)[1]){errors[lane]=3;return;}
     row[5]=state_string_id(d,state_child(d,order,index,ok),ok)==owners[lane];if(!ok){errors[lane]=3;return;}promoted[lane]=true;
   }
 }else if(mode==3){const long ccp=pf_index(nation_ids,N,labels[9]),kmt=pf_index(nation_ids,N,labels[10]);
   if(ccp<0||kmt<0||rows[ccp*7]<0||rows[kmt*7]<0)return;bool objective=true;
   const long land=state_child(v,state,1,ok);pf_container(v,land,7,-1,ok);cursor=land+1;
   for(long i=0;ok&&i<state_record(v,land)[1];++i){const long zone=state_string_id(v,cursor,ok),territory=cursor+1;
     if(pf_possessor(v,territory,ok)==labels[10]){if(dims[10]){errors[lane]=dims[10];messages[lane]=dims[11];return;}
       const long t=pf_index(zone_ids,T,zone);if(t<0){errors[lane]=2;return;}
       if(home[t]&&!state_string_id_equals(v,zone,"land_hainan",11,ok)&&!state_string_id_equals(v,zone,"land_formosa",12,ok))objective=false;}
     cursor=state_end(v,territory,ok);}
   if(!ok){errors[lane]=3;return;}rows[ccp*7+1]=8;rows[ccp*7+6]=objective;
 }else if(mode==4){for(long a=0;a<N;++a)if(rows[a*7]>=0){rows[a*7+1]=16;
     for(long b=0;b<N;++b)if(a!=b&&rows[b*7]>=0){const ulong at=(ulong(lane)*N*N+a*N+b)*7+2;
       if(pair_errors[at]){errors[lane]=pair_errors[at];return;}if(pairs[at]<0||pairs[at]>1){errors[lane]=3;return;}}}
 }else errors[lane]=3;
}
inline long pf_row(device long* out,long cap,thread long& at,long tag,long meta){const long root=at++;
 if(root<cap){device long* r=out+ulong(root)*5;r[0]=tag;r[1]=meta;r[2]=r[3]=0;r[4]=root+1;}return root;}
inline void pf_end(device long* out,long cap,long root,long end){if(root<cap)out[ulong(root)*5+4]=end;}
inline void pf_id(device long* out,long cap,thread long& at,long id){pf_row(out,cap,at,5,id);}
inline void pf_integer(device long* out,long cap,thread long& at,long value){const long root=pf_row(out,cap,at,2,0);
 if(root<cap){out[ulong(root)*5+2]=long(ulong(value)&0xffffffffUL);out[ulong(root)*5+3]=long((ulong(value)>>32)&0xffffffffUL);}}
inline void pf_flags(thread const PackedStateView& v,long root,thread const long* keys,thread const long* values,long amount,
 device long* out,long cap,thread long& at,thread bool& ok){
 const long target=pf_row(out,cap,at,7,0);bool used[3]={false,false,false};long cursor=root+1,count=0;
 for(long i=0;ok&&i<state_record(v,root)[1];++i){const long key=state_string_id(v,cursor,ok),val=cursor+1;long replacement=-1;
   while(ok){long best=-1;for(long j=0;j<amount;++j)if(!used[j]&&(best<0||container_compare(v,keys[j],keys[best],ok)<0))best=j;
     if(best<0||container_compare(v,keys[best],key,ok)>0)break;used[best]=true;if(keys[best]==key){replacement=best;break;}
     pf_id(out,cap,at,keys[best]);pf_integer(out,cap,at,values[best]);++count;}
   pf_id(out,cap,at,key);if(replacement>=0)pf_integer(out,cap,at,values[replacement]);else container_copy(v,val,out,cap,at,ok);
   ++count;cursor=state_end(v,val,ok);}
 while(ok){long best=-1;for(long j=0;j<amount;++j)if(!used[j]&&(best<0||container_compare(v,keys[j],keys[best],ok)<0))best=j;
   if(best<0)break;used[best]=true;pf_id(out,cap,at,keys[best]);pf_integer(out,cap,at,values[best]);++count;}
 if(target<cap)out[ulong(target)*5+1]=count;pf_end(out,cap,target,at);
}
kernel void political_facts_write(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* roots[[buffer(2)]],device const long* changes[[buffer(3)]],device const bool* selected[[buffer(4)]],
 device const long* nation_ids[[buffer(5)]],device const long* labels[[buffer(6)]],device const long* pairs[[buffer(7)]],
 device const uchar* prefix[[buffer(8)]],device const long* poffsets[[buffer(9)]],device const uchar* suffix[[buffer(10)]],
 device const long* soffsets[[buffer(11)]],device const long* usage[[buffer(12)]],device long* blocks[[buffer(13)]],
 device long* sizes[[buffer(14)]],device long* required[[buffer(15)]],device long* errors[[buffer(16)]],device const long* dims[[buffer(17)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],N=dims[2],K=dims[12];if(long(lane)>=B)return;sizes[lane]=required[lane]=errors[lane]=0;if(!selected[lane])return;
 bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,ok);
 const long nations=roots[lane];device const long* rows=changes+ulong(lane)*N*7;device long* out=blocks+ulong(lane)*K*5;
 long at=0;const long whole=pf_row(out,K,at,7,state_record(v,nations)[1]);
 for(long n=0;ok&&n<N;++n){device const long* row=rows+n*7;if(row[0]<0)continue;pf_id(out,K,at,nation_ids[n]);
   const long root=pf_row(out,K,at,10,12);long field=row[0]+1;
   for(long f=0;ok&&f<12;++f){const long end=state_end(v,field,ok);
     if(f==3&&(row[1]&4))pf_id(out,K,at,labels[6]);
     else if(f==9&&(row[1]&16)){const long allies=pf_row(out,K,at,8,0);long count=0;
       for(long b=0;b<N;++b)if(b!=n&&rows[b*7]>=0&&pairs[(ulong(lane)*N*N+n*N+b)*7+2]){pf_id(out,K,at,nation_ids[b]);++count;}
       if(allies<K)out[ulong(allies)*5+1]=count;pf_end(out,K,allies,at);
     }else if(f==11&&(row[1]&15)){long keys[3],values[3],amount=0;
       if(row[1]&1){keys[amount]=labels[0];values[amount++]=row[2];}
       if(row[1]&2){keys[amount]=labels[1];values[amount++]=row[3];}
       if(row[1]&4){keys[amount]=labels[2];values[amount++]=row[4];keys[amount]=labels[3];values[amount++]=row[5];keys[amount]=labels[4];values[amount++]=1;}
       if(row[1]&8){keys[amount]=labels[5];values[amount++]=row[6];}
       pf_flags(v,field,keys,values,amount,out,K,at,ok);
     }else container_copy(v,field,out,K,at,ok);field=end;
   }pf_end(out,K,root,at);
 }pf_end(out,K,whole,at);required[lane]=at;if(!ok){errors[lane]=3;return;}if(at>K){errors[lane]=5;return;}sizes[lane]=at;
}
'''
_library=None
_lock=threading.Lock()
@lru_cache(maxsize=32)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device="mps")
@lru_cache(maxsize=1)
def _dummy():return torch.zeros(1,dtype=torch.int64,device="mps")
def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    return _library
def _call(kernel,args,count):
    if count:kernel(*(v if v.numel() else _dummy() for v in args),threads=count)
def _tensor(v,state,dtype,shape):
    if not isinstance(v,torch.Tensor) or v.dtype!=dtype or v.device!=state.device or tuple(v.shape)!=tuple(shape) or not v.is_contiguous():
        raise ValueError("Political facts require complete contiguous resident inputs")


class ResidentPoliticalFacts:
    def __init__(self,state_context,native_context,relations_context):
        if _device(state_context.device).type!="mps" or native_context.wire_context_fingerprint!=state_context.wire_context_fingerprint or relations_context.state_context is not state_context:
            raise ValueError("Political facts require exact shared State/static/relations contexts on Apple GPU")
        self.state_context=state_context;self.native_context=native_context;self.relations_context=relations_context
        self.nation_ids=tuple(native_context.nations);self.territory_ids=tuple(native_context.territories);self.messages=tuple(native_context.messages)
        self.home_error=int(native_context.home_error);self.home_message=int(native_context.home_message)
        if self.nation_ids!=relations_context.nation_ids:raise ValueError("Political facts and relations axes differ")
        dev=state_context.device
        self.ids=torch.tensor(state_context.prefix_lookup_ids(self.nation_ids),dtype=torch.int64,device=dev)
        self.zones=torch.tensor(state_context.prefix_lookup_ids(self.territory_ids),dtype=torch.int64,device=dev)
        self.ipp=torch.tensor(native_context.ipp_array(),dtype=torch.int64,device=dev)
        self.home=torch.tensor(native_context.home_array(),dtype=torch.int64,device=dev)
        self.labels=torch.tensor(state_context.prefix_lookup_ids(LITERALS),dtype=torch.int64,device=dev)

    def reserve(self,state):
        N=len(self.nation_ids);S=state.records.shape[1]+N*N+6*N+8
        return dict(state_capacity=S,block_capacity=max(S,1))

    def refresh_possessions(self,state,selected=None,**capacities):return self._apply(state,0,None,selected,None,**capacities)
    def refresh_civil_flag(self,state,owners,selected=None,**capacities):return self._apply(state,1,owners,selected,None,**capacities)
    def mark_evolution_if_due(self,state,owners,selected=None,**capacities):return self._apply(state,2,owners,selected,None,**capacities)
    def refresh_one_china_objective(self,state,selected=None,**capacities):return self._apply(state,3,None,selected,None,**capacities)
    def rebuild_allies(self,state,selected=None,relations=None,**capacities):return self._apply(state,4,None,selected,relations,**capacities)

    def _apply(self,state,mode,owners,selected,relations,*,state_capacity=None,block_capacity=None):
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Political facts source context differs")
        state._metadata();_device(state.device);B,C=state.records.shape[:2];dev=state.device;N=len(self.nation_ids);T=len(self.territory_ids)
        if owners is None:owners=torch.full((B,),-1,dtype=torch.int64,device=dev)
        _tensor(owners,state,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,state,torch.bool,(B,));S=C if state_capacity is None else state_capacity;K=max(C,1) if block_capacity is None else block_capacity
        if type(S) is not int or S<C or type(K) is not int or K<1:raise ValueError("Political facts allocations must preserve the complete source")
        if B>2**32-1 or max(S,K)>2**63-1 or B*max(C,S,K,N,1)*7*8>2**63-1:raise OverflowError("Political facts allocation is not representable")
        for v in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets,state.suffix_usage,
                  state.context.records,state.context.string_bytes,state.context.string_offsets):
            if v.device!=dev or not v.is_contiguous():raise ValueError("Political facts State/context buffers must remain contiguous and resident")
        if mode==4:
            if relations is None:relations=self.relations_context.compute(state)
            if relations.source is not state:raise ValueError("Allies relations must bind the exact final State")
            pairs,pair_errors=relations.pairs,relations.pair_errors
            for v in (pairs,pair_errors):_tensor(v,state,torch.int64,(B,N,N,7))
        else:pairs=pair_errors=torch.empty(0,dtype=torch.int64,device=dev)
        zero=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        changes,facts,roots,errors,messages=zero(B,N,7),zero(B,N,3),zero(B),zero(B),zero(B)
        promoted=torch.zeros(B,dtype=torch.bool,device=dev)
        dims=_dimensions((B,C,N,T,state.context.string_count,state.context.string_bytes.numel(),state.string_offsets.numel()-1,
            state.string_bytes.numel(),state.context.records.shape[0],mode,self.home_error,self.home_message,K))
        pool=(state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage)
        _call(_kernels().political_facts_plan,(state.records,state.lengths,state.errors,owners,selected,*pool,self.ids,self.zones,self.ipp,self.home,
            self.labels,state.context.records,pairs,pair_errors,changes,facts,promoted,roots,errors,messages,dims),B)
        writing=selected&~(errors!=0).any()&(changes[:,:,1]!=0).any(1)
        blocks,lengths,required_blocks,write_errors=zero(B,K,5),zero(B),zero(B),zero(B)
        _call(_kernels().political_facts_write,(state.records,state.lengths,roots,changes,writing,self.ids,self.labels,pairs,*pool,blocks,lengths,
            required_blocks,write_errors,dims),B)
        errors=torch.where(selected&(errors==0)&(write_errors!=0),write_errors,errors)
        edited=replace_subtrees(state,roots,blocks,lengths,writing&~(errors!=0).any(),capacity=S)
        details=torch.where(edited.errors!=0,torch.where((edited.errors&8)!=0,5,3),0)
        errors=torch.where(selected&(errors==0)&(details!=0),details,errors);committed=~(errors!=0).any()
        if S==C:original=state.records
        else:
            original=zero(B,S,5);original[:,:C]=state.records
        output=DeviceStateBatch(state.context,torch.where(committed,edited.state.records,original),
            torch.where(committed,edited.state.lengths,state.lengths),torch.where(committed,edited.state.sections,state.sections),
            state.string_bytes,state.string_offsets,state.errors,state.suffix_usage)
        # Native NationsMap ends at the following TerritoriesMap root.
        old_size=state.section("state.territories")-state.section("state.nations")
        required_state=torch.maximum(edited.required_capacity,state.lengths+required_blocks-old_size)
        return PoliticalFactsResult(output,errors,messages,promoted&committed,facts[:,:,0].contiguous(),facts[:,:,1].contiguous(),facts[:,:,2].contiguous(),
            required_state,required_blocks,selected&committed,committed)
