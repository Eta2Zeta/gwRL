"""Exact generic queuePoliticalDecision over source-bound Action6 forests.

This pure helper preserves supplied option IDs/kinds/parameter bits. It replaces
only nation/player/decision, resolves the player AFTER pending upsert, and leaves
duplicate Decision/option IDs and other outer State invariants to the Engine.
No rule choice is invented and no clock, income, Event or RNG hook is run.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_map_edits import SOURCE as MAP_SOURCE,MapMode,build_map_edits,build_sequence_splices,commit_container_edits
from .device_strings import intern_bytes
from .resident_events import EventPayloads


@dataclass(frozen=True)
class PoliticalDecisionOptions:
    source:DeviceStateBatch
    records:torch.Tensor  # [B,R,5], one typed Sequence containing complete Action6 records
    lengths:torch.Tensor
    errors:torch.Tensor


@dataclass(frozen=True)
class PoliticalDecisionResult:
    state:DeviceStateBatch
    errors:torch.Tensor
    generated_ids:torch.Tensor
    reactions:torch.Tensor
    required_id_bytes:torch.Tensor
    required_decision_records:torch.Tensor
    required_state_capacity:torch.Tensor
    required_block_capacity:torch.Tensor
    required_string_usage:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE=MAP_SOURCE+r'''
inline bool pd_container(thread const PackedStateView& v,long root,long tag,long count,thread bool& valid){
 const long end=state_end(v,root,valid);if(!valid)return false;device const long* r=state_record(v,root);
 const long max_count=(tag==7||tag==13)?(end-root-1)/2:end-root-1;
 if(r[0]!=tag||r[1]<0||r[1]>max_count||(count>=0&&r[1]!=count)||r[2]||r[3])valid=false;return valid;
}
inline void pd_span(thread const PackedStateView& v,long id,thread long& begin,thread long& end,thread bool& prefix,thread bool& valid){
 if(id<0||id>=v.prefix_count+v.suffix_count){valid=false;begin=end=0;prefix=true;return;}
 prefix=id<v.prefix_count;const long local=prefix?id:id-v.prefix_count;device const long* offsets=prefix?v.prefix_offsets:v.suffix_offsets;
 begin=offsets[local];end=offsets[local+1];if(begin<0||end<begin||end>(prefix?v.prefix_bytes_length:v.suffix_bytes_length))valid=false;
}
inline bool pd_json(thread const PackedStateView& v,long root,thread bool& valid){
 const long end=state_end(v,root,valid);for(long i=root;valid&&i<end;++i){const long tag=state_record(v,i)[0];
   if(tag!=0&&tag!=1&&tag!=4&&tag!=5&&tag!=12&&tag!=13)valid=false;}
 return valid;
}
inline long pd_player(thread const PackedStateView& v,long state,long owner,thread const PackedStateView& definition,thread long& error,thread bool& valid){
 const long nations=state_child(v,state,0,valid),politics=state_child(v,state,8,valid),pending=state_child(v,politics,10,valid);
 pd_container(v,nations,7,-1,valid);pd_container(v,pending,7,-1,valid);if(!valid){error=3;return -1;}
 for(long visited=0;visited<=state_record(v,nations)[1];++visited){
   const long nation=state_map_find_id(v,nations,owner,valid);if(!valid){error=3;return -1;}if(nation<0){error=1;return -1;}
   pd_container(v,nation,10,12,valid);bool present=false;const long player=state_optional(v,state_child(v,nation,1,valid),present,valid);
   if(present){const long id=state_string_id(v,player,valid);if(!valid)error=3;return id;}
   const long controller=state_optional(v,state_child(v,nation,0,valid),present,valid);
   if(present){owner=state_string_id(v,controller,valid);if(!valid){error=3;return -1;}continue;}
   long a,b;bool p;pd_span(v,owner,a,b,p,valid);device const uchar* name=p?v.prefix_bytes:v.suffix_bytes;
   long cursor=pending+1;const long amount=state_record(v,pending)[1];long fallback=-1;
   for(long i=0;valid&&i<amount;++i){const long id=state_string_id(v,cursor,valid);long x,y;bool q;pd_span(v,id,x,y,q,valid);
     device const uchar* key=q?v.prefix_bytes:v.suffix_bytes;constant char* stem="warlord_defense_player:";
     bool match=y-x==23+b-a;for(long j=0;match&&j<23;++j)match=key[x+j]==uchar(stem[j]);
     for(long j=0;match&&j<b-a;++j)match=key[x+23+j]==name[a+j];
     const long value=state_end(v,cursor,valid);if(match)fallback=value;cursor=state_end(v,value,valid);}
   if(!valid){error=3;return -1;}if(fallback<0){error=2;return -1;}
   if(state_record(v,fallback)[0]!=5){error=2;return -1;}const long id=state_string_id(v,fallback,valid);
   const long players=state_child(definition,0,7,valid);pd_container(definition,players,8,-1,valid);
   long at=players+1;for(long i=0;valid&&i<state_record(definition,players)[1];++i){
     if(state_string_id(definition,at,valid)==id)return id;at=state_end(definition,at,valid);}
   error=valid?2:3;return -1;
 }
 // Recursive native politicalPlayer is undefined for a controller cycle with
 // no direct player. A bounded unsupported-state error never guesses a player.
 error=3;return -1;
}
kernel void political_decision_plan(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const long* nations[[buffer(3)]],device const long* kinds[[buffer(4)]],device const bool* selected[[buffer(5)]],
 device const long* options[[buffer(6)]],device const long* option_lengths[[buffer(7)]],device const long* option_errors[[buffer(8)]],
 device const long* continuation[[buffer(9)]],device const long* continuation_lengths[[buffer(10)]],device const long* continuation_errors[[buffer(11)]],
 device const uchar* prefix[[buffer(12)]],device const long* poffsets[[buffer(13)]],device const uchar* suffix[[buffer(14)]],
 device const long* soffsets[[buffer(15)]],device const long* usage[[buffer(16)]],device const long* definition[[buffer(17)]],
 device long* scratch[[buffer(18)]],device long* remaining[[buffer(19)]],device long* previous[[buffer(20)]],
 device long* data[[buffer(21)]],device uchar* names[[buffer(22)]],device long* name_lengths[[buffer(23)]],
 device long* required_names[[buffer(24)]],device long* required_decision[[buffer(25)]],device long* errors[[buffer(26)]],
 device const long* dims[[buffer(27)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],R=dims[2],P=dims[3],L=dims[4],K=max(R,P);if(long(lane)>=B)return;
 errors[lane]=name_lengths[lane]=required_names[lane]=required_decision[lane]=0;device long* d=data+ulong(lane)*5;
 for(long i=0;i<5;++i)d[i]=0;d[0]=d[1]=-1;if(!selected[lane])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix,poffsets,dims[5],dims[6],suffix,soffsets,dims[7],dims[8],usage,valid);
 auto a=v;a.records=options+ulong(lane)*R*5;a.length=option_lengths[lane];a.capacity=R;
 if(option_errors[lane]||!edit_tree(a,scratch+ulong(lane)*K,remaining+ulong(lane)*K,previous+ulong(lane)*K*2)){
   errors[lane]=option_errors[lane]?option_errors[lane]:3;return;}
 pd_container(a,0,6,-1,valid);if(!valid){errors[lane]=3;return;}const long count=state_record(a,0)[1];
 if(!count){errors[lane]=2;return;}
 if(inherited[lane])valid=false;pd_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);pd_container(v,state,10,19,valid);
 long cursor=1,total=7;
 for(long i=0;valid&&i<count;++i){pd_container(a,cursor,10,6,valid);for(long j=0;j<4;++j)(void)state_string_id(a,state_child(a,cursor,j,valid),valid);
   bool present=false;const long decision=state_optional(a,state_child(a,cursor,4,valid),present,valid);if(present)(void)state_string_id(a,decision,valid);
   pd_json(a,state_child(a,cursor,5,valid),valid);const long end=state_end(a,cursor,valid);
   if(end-cursor+(present?0:1)>LONG_MAX-total)valid=false;else total+=end-cursor+(present?0:1);cursor=end;}
 auto p=v;p.records=continuation+ulong(lane)*P*5;p.length=continuation_lengths[lane];p.capacity=P;
 if(continuation_errors[lane]||!edit_tree(p,scratch+ulong(lane)*K,remaining+ulong(lane)*K,previous+ulong(lane)*K*2)||!pd_json(p,0,valid)){
   errors[lane]=continuation_errors[lane]?continuation_errors[lane]:3;return;}
 const long flags=state_child(v,state,15,valid),politics=state_child(v,state,8,valid);d[0]=flags;d[1]=state_child(v,politics,10,valid);
 const long node=state_map_find_literal(v,flags,"politics_sequence",17,valid),old=node<0?0:state_signed_value(v,node,valid);
 if(!valid||old<INT_MIN||old>INT_MAX){errors[lane]=3;return;}if(old==INT_MAX){errors[lane]=2;return;}d[2]=old+1;
 auto def=v;def.records=definition;def.length=def.capacity=dims[9];def.suffix_count=def.suffix_bytes_length=0;
 const long clock=state_child(v,state,7,valid),turn=state_signed_value(v,state_child(v,clock,1,valid),valid),turns=state_child(def,0,6,valid);
 const long active=state_string_id(def,state_child(def,turns,turn,valid),valid);d[3]=nations[lane]!=active;
 long x,y;bool q;pd_span(v,kinds[lane],x,y,q,valid);long na,nb;bool np;pd_span(v,nations[lane],na,nb,np,valid);
 if(!valid){errors[lane]=3;return;}device const uchar* text=q?prefix:suffix;
 const long value=d[2];ulong magnitude=ulong(value<0?-value:value);char digits[20];long number=0;
 do{digits[number++]=char('0'+magnitude%10);magnitude/=10;}while(magnitude);
 const long needed=y-x+1+(value<0?1:0)+number;required_names[lane]=needed;required_decision[lane]=total;
 if(needed>L){errors[lane]=5;return;}device uchar* out=names+ulong(lane)*L;long at=0;
 for(long i=x;i<y;++i)out[at++]=text[i];out[at++]='_';if(value<0)out[at++]='-';while(number)out[at++]=uchar(digits[--number]);name_lengths[lane]=at;
}
kernel void political_decision_player(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* nations[[buffer(2)]],
 device const bool* selected[[buffer(3)]],device const uchar* prefix[[buffer(4)]],device const long* poffsets[[buffer(5)]],
 device const uchar* suffix[[buffer(6)]],device const long* soffsets[[buffer(7)]],device const long* usage[[buffer(8)]],
 device const long* definition[[buffer(9)]],device long* players[[buffer(10)]],device long* counts[[buffer(11)]],
 device long* errors[[buffer(12)]],device const long* dims[[buffer(13)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;players[lane]=-1;counts[lane]=errors[lane]=0;if(!selected[lane])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],prefix,poffsets,dims[5],dims[6],suffix,soffsets,dims[7],dims[8],usage,valid);
 auto d=v;d.records=definition;d.length=d.capacity=dims[9];d.suffix_count=d.suffix_bytes_length=0;
 const long state=state_child(v,0,0,valid);long error=0;players[lane]=pd_player(v,state,nations[lane],d,error,valid);
 const long decisions=state_child(v,state,11,valid);pd_container(v,decisions,6,-1,valid);if(valid)counts[lane]=state_record(v,decisions)[1];
 errors[lane]=valid?error:3;
}
inline void pd_row(device long* out,long at,long tag,long meta,long end){out+=ulong(at)*5;out[0]=tag;out[1]=meta;out[2]=out[3]=0;out[4]=end;}
kernel void political_decision_write(
 device const long* options[[buffer(0)]],device const long* option_lengths[[buffer(1)]],device const long* data[[buffer(2)]],
 device const long* ids[[buffer(3)]],device const long* nations[[buffer(4)]],device const long* kinds[[buffer(5)]],device const long* players[[buffer(6)]],
 device const bool* selected[[buffer(7)]],device const uchar* prefix[[buffer(8)]],device const long* poffsets[[buffer(9)]],
 device const uchar* suffix[[buffer(10)]],device const long* soffsets[[buffer(11)]],device const long* usage[[buffer(12)]],
 device long* blocks[[buffer(13)]],device long* lengths[[buffer(14)]],device long* required[[buffer(15)]],device long* errors[[buffer(16)]],
 device const long* dims[[buffer(17)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],R=dims[2],K=dims[10];if(long(lane)>=B)return;lengths[lane]=errors[lane]=0;if(!selected[lane])return;
 if(required[lane]>K){errors[lane]=5;return;}bool valid=true;
 auto a=make_packed_state_view(options+ulong(lane)*R*5,option_lengths[lane],R,prefix,poffsets,dims[5],dims[6],suffix,soffsets,dims[7],dims[8],usage,valid);
 device long* out=blocks+ulong(lane)*K*5;const long id=ids[lane],count=state_record(a,0)[1];
 pd_row(out,0,10,6,required[lane]);pd_row(out,1,5,id,2);pd_row(out,2,5,kinds[lane],3);pd_row(out,3,5,nations[lane],4);
 pd_row(out,4,1,data[ulong(lane)*5+3],5);pd_row(out,5,5,id,6);pd_row(out,6,6,count,required[lane]);long cursor=1,at=7;
 for(long i=0;valid&&i<count;++i){const long root=at;pd_row(out,at++,10,6,0);long field=cursor+1;
   for(long j=0;valid&&j<6;++j){const long end=state_end(a,field,valid);
     if(j==2||j==3){pd_row(out,at,5,j==2?players[lane]:nations[lane],at+1);++at;}
     else if(j==4){pd_row(out,at,9,1,at+2);++at;pd_row(out,at,5,id,at+1);++at;}
     else container_copy(a,field,out,K,at,valid);field=end;}
   out[ulong(root)*5+4]=at;cursor=state_end(a,cursor,valid);}
 if(!valid||at!=required[lane]){errors[lane]=3;return;}lengths[lane]=at;
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
    if count:kernel(*(value if value.numel() else _dummy() for value in args),threads=count)
def _tensor(value,state,dtype,shape):
    if not isinstance(value,torch.Tensor) or value.dtype!=dtype or value.device!=state.device or tuple(value.shape)!=tuple(shape) or not value.is_contiguous():
        raise ValueError("Political decision tensors must remain resident and contiguous")
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    out=torch.zeros(shape,dtype=value.dtype,device=value.device);out[tuple(slice(0,n) for n in value.shape)]=value;return out


class ResidentPoliticalDecisionQueue:
    def __init__(self,state_context):
        if _device(state_context.device).type!="mps":raise ValueError("Political decisions require explicit exact MPS")
        self.state_context=state_context;self.sequence=int(state_context.prefix_lookup_ids(("politics_sequence",))[0])

    def reserve(self,state,options,continuation,*,id_byte_capacity):
        R=options.records.shape[1];P=continuation.records.shape[1];S=state.records.shape[1]+R+(R//7)+P+10
        return dict(id_byte_capacity=id_byte_capacity,state_capacity=S,block_capacity=max(S,1),
            string_capacity=state.string_offsets.numel()-1+state.lane_count,
            byte_capacity=state.string_bytes.numel()+state.lane_count*id_byte_capacity)

    def enqueue(self,state,nations,kinds,options,continuation,selected=None,*,id_byte_capacity,
                state_capacity=None,block_capacity=None,string_capacity=None,byte_capacity=None):
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Political decision source context differs")
        if not isinstance(options,PoliticalDecisionOptions) or not isinstance(continuation,EventPayloads) or options.source is not state or continuation.source is not state:
            raise ValueError("Options/continuation must bind the exact complete State and string arena")
        state._metadata();_device(state.device);B,C=state.records.shape[:2];dev=state.device
        for forest in (options,continuation):
            if not isinstance(forest.records,torch.Tensor) or forest.records.ndim!=3 or forest.records.shape[0]!=B or forest.records.shape[2]!=5:raise ValueError("Political forests need [lane,records,5]")
            _tensor(forest.records,state,torch.int64,forest.records.shape);_tensor(forest.lengths,state,torch.int64,(B,));_tensor(forest.errors,state,torch.int64,(B,))
        R,P=options.records.shape[1],continuation.records.shape[1]
        for value in (nations,kinds):_tensor(value,state,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,state,torch.bool,(B,))
        L=id_byte_capacity;S=C if state_capacity is None else state_capacity;K=max(C,1) if block_capacity is None else block_capacity
        T=state.string_offsets.numel()-1 if string_capacity is None else string_capacity;A=state.string_bytes.numel() if byte_capacity is None else byte_capacity
        if any(type(v) is not int or v<0 for v in (L,S,K,T,A)) or S<C or K<1 or T<state.string_offsets.numel()-1 or A<state.string_bytes.numel():raise ValueError("Decision arenas must preserve the entire source")
        if B>2**32-1 or max(L,S,K,T,A)>2**63-1 or B*max(C,S,K,R,P,L,1)*10>2**63-1:raise OverflowError("Decision arena is not representable")
        for value in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets,state.suffix_usage,state.context.records,state.context.string_bytes,state.context.string_offsets):
            if value.device!=dev or not value.is_contiguous():raise ValueError("Decision State/context must stay resident and contiguous")
        zero=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        def dims(source):return _dimensions((B,source.records.shape[1],R,P,L,source.context.string_count,source.context.string_bytes.numel(),
            source.string_offsets.numel()-1,source.string_bytes.numel(),source.context.records.shape[0],K))
        def pool(source):return (source.context.string_bytes,source.context.string_offsets,source.string_bytes,source.string_offsets,source.suffix_usage)
        names=torch.zeros((B,L),dtype=torch.uint8,device=dev);name_lengths,needed_names,needed_decision,errors=zero(B),zero(B),zero(B),zero(B);data=zero(B,5)
        M=max(R,P,1);scratch=(zero(B,M),zero(B,M),zero(B,M*2))
        _call(_kernels().political_decision_plan,(state.records,state.lengths,state.errors,nations,kinds,selected,options.records,options.lengths,options.errors,
            continuation.records,continuation.lengths,continuation.errors,*pool(state),state.context.records,*scratch,data,names,name_lengths,
            needed_names,needed_decision,errors,dims(state)),B)
        required_state=state.lengths.clone();required_block=needed_decision.clone()
        def healthy():return ~(errors!=0).any()
        def note(details):
            nonlocal errors
            errors=torch.where(selected&(errors==0)&(details!=0),details,errors)
        def apply(build):
            nonlocal required_state,required_block
            edited=commit_container_edits(build,capacity=S)
            required_state=torch.maximum(required_state,edited.required_state_capacity);required_block=torch.maximum(required_block,build.required_capacity)
            bad=(build.errors!=0)|(edited.edit_errors!=0);capacity=((build.errors&64)!=0)|((edited.edit_errors&8)!=0)
            note(torch.where(bad,torch.where(capacity,5,3),0));return edited.state
        added=intern_bytes(state,names,name_lengths,selected&healthy(),string_capacity=T,byte_capacity=A)
        note(torch.where(added.errors!=0,torch.where((added.errors&8)!=0,5,3),0));note(torch.where(added.pool_error!=0,3,0).expand(B));current=added.state
        values=zero(B,1,5);values[:,:,0]=2;values[:,:,2]=data[:,2,None]&0xffffffff;values[:,:,3]=(data[:,2,None]>>32)&0xffffffff;values[:,:,4]=1
        current=apply(build_map_edits(current,data[:,0].contiguous(),torch.full((B,),self.sequence,dtype=torch.int64,device=dev),
            torch.full((B,),int(MapMode.UPSERT),dtype=torch.int64,device=dev),values,torch.ones(B,dtype=torch.int64,device=dev),selected&healthy(),capacity=K))
        current=apply(build_map_edits(current,data[:,1].contiguous(),added.ids,torch.full((B,),int(MapMode.UPSERT),dtype=torch.int64,device=dev),
            continuation.records,continuation.lengths,selected&healthy(),capacity=K))
        players,counts,player_errors=zero(B),zero(B),zero(B)
        _call(_kernels().political_decision_player,(current.records,current.lengths,nations,selected&healthy(),*pool(current),current.context.records,
            players,counts,player_errors,dims(current)),B);note(player_errors)
        blocks,lengths,write_errors=zero(B,K,5),zero(B),zero(B)
        _call(_kernels().political_decision_write,(options.records,options.lengths,data,added.ids,nations,kinds,players,selected&healthy(),*pool(current),
            blocks,lengths,needed_decision,write_errors,dims(current)),B);note(write_errors)
        current=apply(build_sequence_splices(current,current.section("state.decisions").contiguous(),counts,zero(B),blocks,lengths,
            torch.ones(B,dtype=torch.int64,device=dev),selected&healthy(),capacity=K))
        committed=healthy();output=DeviceStateBatch(state.context,torch.where(committed,current.records,_pad(state.records,(B,S,5))),
            torch.where(committed,current.lengths,state.lengths),torch.where(committed,current.sections,state.sections),
            torch.where(committed,current.string_bytes,_pad(state.string_bytes,(A,))),torch.where(committed,current.string_offsets,_pad(state.string_offsets,(T+1,))),
            state.errors,torch.where(committed,current.suffix_usage,state.suffix_usage))
        return PoliticalDecisionResult(output,errors,added.ids,data[:,3].to(torch.bool),needed_names,needed_decision,required_state,required_block,
            added.required_usage,selected&committed,committed)
