"""Exact chooseEvolution choice construction plus the generic decision queue.

Eligibility/promotion and the 13-IPP trigger belong to refreshPoliticalState.
This helper only mirrors chooseEvolution: awarded/pending guards, all possessed
land with false/true factory options, pending flag, then political decision.
It does not select a capital, create a factory, evolve, consume RNG or run hooks.
"""
from dataclasses import dataclass,replace
from functools import lru_cache
from types import SimpleNamespace
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_map_edits import MapMode,build_map_edits,commit_container_edits
from .device_strings import intern_bytes
from .canonical_json_metal import canonical_json_subtrees,canonical_json_digests
from .resident_action_ids import ActionIdFamily,action_id_strings,construct_action_ids
from .resident_events import EventPayloads
from .resident_political_decisions import SOURCE as QUEUE_SOURCE,PoliticalDecisionOptions


@dataclass(frozen=True)
class EvolutionChoiceResult:
    state:DeviceStateBatch
    errors:torch.Tensor
    queued:torch.Tensor
    generated_ids:torch.Tensor
    required_option_capacity:torch.Tensor
    required_pending_key_bytes:torch.Tensor
    required_parameter_bytes:torch.Tensor
    required_action_id_bytes:torch.Tensor
    required_decision_id_bytes:torch.Tensor
    required_state_capacity:torch.Tensor
    required_block_capacity:torch.Tensor
    required_string_usage:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE=QUEUE_SOURCE+r'''
kernel void evolution_choice_plan(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const long* nations[[buffer(3)]],device const bool* selected[[buffer(4)]],device const uchar* prefix[[buffer(5)]],
 device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],device const long* soffsets[[buffer(8)]],
 device const long* usage[[buffer(9)]],device const long* definition[[buffer(10)]],device long* data[[buffer(11)]],
 device long* zone_ids[[buffer(12)]],device uchar* keys[[buffer(13)]],device long* key_sizes[[buffer(14)]],
 device long* required_options[[buffer(15)]],device long* required_keys[[buffer(16)]],device bool* active[[buffer(17)]],
 device long* errors[[buffer(18)]],device const long* dims[[buffer(19)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],O=dims[2],L=dims[3];if(long(lane)>=B)return;
 errors[lane]=key_sizes[lane]=required_options[lane]=required_keys[lane]=0;active[lane]=false;
 device long* d=data+ulong(lane)*4;d[0]=-1;d[1]=d[2]=d[3]=0;if(!selected[lane])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,valid);
 if(inherited[lane])valid=false;pd_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);pd_container(v,state,10,19,valid);
 const long politics=state_child(v,state,8,valid),awarded=state_child(v,politics,9,valid);pd_container(v,awarded,8,-1,valid);
 long cursor=awarded+1;for(long i=0;valid&&i<state_record(v,awarded)[1];++i){if(state_string_id(v,cursor,valid)==nations[lane])return;cursor=state_end(v,cursor,valid);}
 long a,b;bool p;pd_span(v,nations[lane],a,b,p,valid);device const uchar* nation=p?prefix:suffix;
 const long flags=state_child(v,state,15,valid);pd_container(v,flags,7,-1,valid);d[0]=flags;cursor=flags+1;
 for(long i=0;valid&&i<state_record(v,flags)[1];++i){const long id=state_string_id(v,cursor,valid);long x,y;bool q;pd_span(v,id,x,y,q,valid);
   device const uchar* text=q?prefix:suffix;constant char* stem="evolution_pending_";bool match=y-x==18+b-a;
   for(long j=0;match&&j<18;++j)match=text[x+j]==uchar(stem[j]);for(long j=0;match&&j<b-a;++j)match=text[x+18+j]==nation[a+j];
   const long value=state_end(v,cursor,valid);if(match&&state_signed_value(v,value,valid)!=0)return;cursor=state_end(v,value,valid);}
 if(!valid){errors[lane]=3;return;}active[lane]=true;
 const long land=state_child(v,state,1,valid);pd_container(v,land,7,-1,valid);cursor=land+1;long count=0;
 for(long i=0;valid&&i<state_record(v,land)[1];++i){const long id=state_string_id(v,cursor,valid),territory=cursor+1;
   pd_container(v,territory,10,2,valid);bool present=false;const long possessor=state_optional(v,state_child(v,territory,0,valid),present,valid);
   if(present&&state_string_id(v,possessor,valid)==nations[lane]){if(count<O/2)zone_ids[ulong(lane)*(O/2)+count]=id;++count;}cursor=state_end(v,territory,valid);}
 if(!valid||count>LONG_MAX/2){errors[lane]=3;return;}d[1]=count*2;required_options[lane]=count*2;
 if(!count){errors[lane]=2;return;}
 auto def=v;def.records=definition;def.length=def.capacity=dims[8];def.suffix_count=def.suffix_bytes_length=0;
 long player_error=0;d[2]=pd_player(v,state,nations[lane],def,player_error,valid);
 if(!valid||player_error){errors[lane]=valid?player_error:3;return;}
 const long needed=18+b-a;required_keys[lane]=needed;
 if(count*2>O||needed>L){errors[lane]=5;return;}
 device uchar* out=keys+ulong(lane)*L;constant char* stem="evolution_pending_";
 for(long j=0;j<18;++j)out[j]=uchar(stem[j]);for(long j=0;j<b-a;++j)out[18+j]=nation[a+j];key_sizes[lane]=needed;
}
kernel void evolution_choice_rank(device const long* data[[buffer(0)]],device const long* errors[[buffer(1)]],
 device const bool* active[[buffer(2)]],device long* ranks[[buffer(3)]],device long* count[[buffer(4)]],device const long* dims[[buffer(5)]],uint tid[[thread_position_in_grid]]){
 if(tid)return;long cursor=0;bool healthy=true;for(long lane=0;lane<dims[0];++lane)if(errors[lane])healthy=false;
 for(long lane=0;lane<dims[0];++lane){ranks[lane]=cursor;if(healthy&&active[lane])cursor+=data[ulong(lane)*4+1];}count[0]=cursor;
}
inline void ec_row(device long* out,long at,long tag,long meta,long end){out+=ulong(at)*5;out[0]=tag;out[1]=meta;out[2]=out[3]=0;out[4]=end;}
kernel void evolution_choice_parameters(device const long* data[[buffer(0)]],device const long* ranks[[buffer(1)]],device const long* count[[buffer(2)]],
 device const long* zones[[buffer(3)]],device const long* nations[[buffer(4)]],device const long* labels[[buffer(5)]],device const bool* active[[buffer(6)]],
 device long* params[[buffer(7)]],device long* lengths[[buffer(8)]],device long* descriptors[[buffer(9)]],device const long* dims[[buffer(10)]],uint lane[[thread_position_in_grid]]){
 const long O=dims[1];if(long(lane)>=dims[0]||!active[lane]||!count[0])return;
 for(long i=0;i<data[ulong(lane)*4+1];++i){const long row=ranks[lane]+i;if(row>=count[0])return;device long* out=params+ulong(row)*25;
   ec_row(out,0,13,2,5);ec_row(out,1,5,labels[2],2);ec_row(out,2,1,i%2,3);ec_row(out,3,5,labels[3],4);
   ec_row(out,4,5,zones[ulong(lane)*(O/2)+i/2],5);lengths[row]=5;
   device long* d=descriptors+ulong(row)*4;d[0]=labels[1];d[1]=nations[lane];d[2]=data[ulong(lane)*4+2];d[3]=lane;}
}
kernel void evolution_choice_option_errors(device const long* ranks[[buffer(0)]],device const long* data[[buffer(1)]],
 device const int* parameter_errors[[buffer(2)]],device const int* id_errors[[buffer(3)]],device const int* parameter_batch[[buffer(4)]],
 device const int* id_batch[[buffer(5)]],device long* errors[[buffer(6)]],device const long* dims[[buffer(7)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0]||errors[lane])return;if(parameter_batch[0]||id_batch[0]){errors[lane]=3;return;}
 for(long i=0;i<data[ulong(lane)*4+1];++i){const long row=ranks[lane]+i;if(row>=dims[1]){errors[lane]=5;return;}
   if((parameter_errors[row]&2)||(id_errors[row]&2)){errors[lane]=5;return;}
   if(parameter_errors[row]||id_errors[row]){errors[lane]=3;return;}}
}
kernel void evolution_choice_intern_errors(device const long* ranks[[buffer(0)]],device const long* data[[buffer(1)]],
 device const long* intern_errors[[buffer(2)]],device long* errors[[buffer(3)]],device const long* dims[[buffer(4)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0]||errors[lane])return;
 for(long i=0;i<data[ulong(lane)*4+1];++i){const long row=ranks[lane]+i;if(row<0||row>=dims[1]){errors[lane]=3;return;}
   const long error=intern_errors[row];if(error){errors[lane]=(error&8)?5:3;return;}}
}
kernel void evolution_choice_options(device const long* data[[buffer(0)]],device const long* ranks[[buffer(1)]],device const long* nations[[buffer(2)]],
 device const long* ids[[buffer(3)]],device const long* params[[buffer(4)]],device const long* labels[[buffer(5)]],device const bool* active[[buffer(6)]],
 device long* options[[buffer(7)]],device long* lengths[[buffer(8)]],device const long* dims[[buffer(9)]],uint lane[[thread_position_in_grid]]){
 const long O=dims[1],R=1+11*O;if(long(lane)>=dims[0])return;const long count=active[lane]?data[ulong(lane)*4+1]:0;
 device long* out=options+ulong(lane)*R*5;lengths[lane]=1+11*count;ec_row(out,0,6,count,lengths[lane]);long at=1;
 for(long i=0;i<count;++i){const long row=ranks[lane]+i;ec_row(out,at,10,6,at+11);ec_row(out,at+1,5,ids[row],at+2);
   ec_row(out,at+2,5,labels[1],at+3);ec_row(out,at+3,5,data[ulong(lane)*4+2],at+4);ec_row(out,at+4,5,nations[lane],at+5);
   ec_row(out,at+5,9,0,at+6);for(long j=0;j<5;++j){for(long c=0;c<4;++c)out[ulong(at+6+j)*5+c]=params[ulong(row)*25+j*5+c];
     out[ulong(at+6+j)*5+4]=params[ulong(row)*25+j*5+4]+at+6;}at+=11;}
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
        raise ValueError("Evolution inputs must remain complete resident contiguous tensors")
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    out=torch.zeros(shape,dtype=value.dtype,device=value.device);out[tuple(slice(0,n) for n in value.shape)]=value;return out


class ResidentEvolutionChoice:
    def __init__(self,state_context,decision_queue):
        if _device(state_context.device).type!="mps" or decision_queue.state_context is not state_context:raise ValueError("Evolution requires shared exact State/queue contexts")
        self.state_context=state_context;self.decision_queue=decision_queue
        self.labels=torch.tensor(state_context.prefix_lookup_ids(("politics_evolution","politics_choose_capital","factory","zone")),dtype=torch.int64,device=state_context.device)
        # Immutable raw definition metadata only, outside every rule transition.
        rows=state_context.native.record_array();offsets=state_context.native.string_offsets();node=1
        for _ in range(5):node=int(rows[node,4])
        cursor=node+1;names=[]
        for _ in range(int(rows[node,1])):
            id_=int(rows[cursor,1]);names.append(int(offsets[id_+1]-offsets[id_]));cursor=int(rows[cursor+1,4])
        maximum=max(names,default=0);self.pending_key_capacity=18+maximum
        self.action_id_capacity=len("politics_choose_capital")+2+maximum+16;self.decision_id_capacity=len("politics_evolution_")+11
        self.parameter_context=SimpleNamespace(state_context=state_context,words=torch.empty((0,2),dtype=torch.int64,device=state_context.device),
            offsets=torch.zeros(1,dtype=torch.int64,device=state_context.device),bytes=torch.empty(0,dtype=torch.uint8,device=state_context.device))

    def reserve(self,state,*,option_capacity,parameter_byte_capacity=512):
        B,C=state.records.shape[:2];O=option_capacity;S=C+16+12*O
        return dict(option_capacity=O,parameter_byte_capacity=parameter_byte_capacity,pending_key_byte_capacity=self.pending_key_capacity,
            action_id_byte_capacity=self.action_id_capacity,decision_id_byte_capacity=self.decision_id_capacity,state_capacity=S,block_capacity=max(S,1),
            string_capacity=state.string_offsets.numel()-1+B*(O+2),
            byte_capacity=state.string_bytes.numel()+B*(O*self.action_id_capacity+self.pending_key_capacity+self.decision_id_capacity))

    def queue(self,state,nations,selected=None,*,option_capacity,parameter_byte_capacity,pending_key_byte_capacity,
              action_id_byte_capacity,decision_id_byte_capacity,state_capacity=None,block_capacity=None,string_capacity=None,byte_capacity=None):
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Evolution source context differs")
        state._metadata();_device(state.device);B,C=state.records.shape[:2];dev=state.device;_tensor(nations,state,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,state,torch.bool,(B,))
        O,F,I,D=option_capacity,pending_key_byte_capacity,action_id_byte_capacity,decision_id_byte_capacity
        S=C if state_capacity is None else state_capacity;K=max(C,1) if block_capacity is None else block_capacity
        T=state.string_offsets.numel()-1 if string_capacity is None else string_capacity;A=state.string_bytes.numel() if byte_capacity is None else byte_capacity
        if any(type(v) is not int or v<0 for v in (O,F,I,D,S,K,T,A,parameter_byte_capacity)) or S<C or K<1 or T<state.string_offsets.numel()-1 or A<state.string_bytes.numel():raise ValueError("Evolution arenas must preserve complete source buffers")
        P=B*O;R=1+11*O
        if max(O,F,I,D,S,K,T,A,parameter_byte_capacity)>2**63-1 or B>2**32-1 or P>2**32-1 or max(B*max(C,S,K,R,1)*5,P*max(I,F,parameter_byte_capacity,1))*8>2**63-1:raise OverflowError("Evolution arena is not representable")
        for value in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets,state.suffix_usage,state.context.records,state.context.string_bytes,state.context.string_offsets):
            if value.device!=dev or not value.is_contiguous():raise ValueError("Evolution State/context buffers must stay resident contiguous")
        zero=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        data=zero(B,4);zones=torch.full((B,O//2),-1,dtype=torch.int64,device=dev);keys=torch.zeros((B,F),dtype=torch.uint8,device=dev)
        key_sizes,needed_options,needed_keys,errors=zero(B),zero(B),zero(B),zero(B);active=torch.zeros(B,dtype=torch.bool,device=dev)
        pool=(state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage)
        _call(_kernels().evolution_choice_plan,(state.records,state.lengths,state.errors,nations,selected,*pool,state.context.records,data,zones,keys,key_sizes,
            needed_options,needed_keys,active,errors,_dimensions((B,C,O,F,state.context.string_count,state.context.string_bytes.numel(),
                state.string_offsets.numel()-1,state.string_bytes.numel(),state.context.records.shape[0]))),B)
        ranks,count=zero(B),zero(1);_call(_kernels().evolution_choice_rank,(data,errors,active,ranks,count,_dimensions((B,))),1)
        params,lengths,descriptors=zero(P,5,5),zero(P),zero(P,4)
        _call(_kernels().evolution_choice_parameters,(data,ranks,count,zones,nations,self.labels,active,params,lengths,descriptors,_dimensions((B,O))),B)
        carrier=replace(state,records=params,lengths=lengths,sections=zero(P,27),errors=zero(P))
        rows=torch.arange(P,dtype=torch.int64,device=dev);locations=torch.stack((rows,torch.zeros_like(rows)),1)
        encoded=canonical_json_subtrees(carrier,locations,self.parameter_context,byte_capacity=parameter_byte_capacity,count=count)
        digest=canonical_json_digests(encoded)
        fields=torch.stack((descriptors[:,0],descriptors[:,1],torch.full_like(rows,-1),torch.full_like(rows,-1)),1)
        names=construct_action_ids(torch.full_like(rows,int(ActionIdFamily.POLITICAL)),action_id_strings(state,fields),digest,byte_capacity=I,count=count)
        _call(_kernels().evolution_choice_option_errors,(ranks,data,encoded.errors,names.errors,encoded.batch_error,names.batch_error,errors,_dimensions((B,P))),B)
        healthy=~(errors!=0).any();L=max(I,F)
        requests=torch.cat((_pad(names.data,(P,L)),_pad(keys,(B,L))),0);request_lengths=torch.cat((names.lengths,key_sizes))
        wanted=torch.cat(((rows<count[0])&healthy,active&healthy))
        added=intern_bytes(state,requests,request_lengths,wanted,string_capacity=T,byte_capacity=A)
        def note(details):
            nonlocal errors
            errors=torch.where(selected&(errors==0)&(details!=0),details,errors)
        _call(_kernels().evolution_choice_intern_errors,(ranks,data,added.errors,errors,_dimensions((B,P))),B)
        note(torch.where(added.errors[P:]!=0,torch.where((added.errors[P:]&8)!=0,5,3),0));note(torch.where(added.pool_error!=0,3,0).expand(B))
        current=added.state;options,option_lengths=zero(B,R,5),zero(B)
        _call(_kernels().evolution_choice_options,(data,ranks,nations,added.ids[:P],params,self.labels,active&~(errors!=0).any(),options,option_lengths,_dimensions((B,O))),B)
        flag=zero(B,1,5);flag[:,:,0]=2;flag[:,:,2]=1;flag[:,:,4]=1
        build=build_map_edits(current,data[:,0].contiguous(),added.ids[P:],torch.full((B,),int(MapMode.UPSERT),dtype=torch.int64,device=dev),
            flag,torch.ones(B,dtype=torch.int64,device=dev),active&~(errors!=0).any(),capacity=K)
        changed=commit_container_edits(build,capacity=S)
        cap=((build.errors&64)!=0)|((changed.edit_errors&8)!=0)
        note(torch.where((build.errors!=0)|(changed.edit_errors!=0),torch.where(cap,5,3),0));current=changed.state
        continuation=zero(B,1,5);continuation[:,:,0]=13;continuation[:,:,4]=1
        queued=self.decision_queue.enqueue(current,nations,self.labels[0].expand(B).contiguous(),
            PoliticalDecisionOptions(current,options,option_lengths,zero(B)),EventPayloads(current,continuation,torch.ones(B,dtype=torch.int64,device=dev),zero(B)),
            active&~(errors!=0).any(),id_byte_capacity=D,state_capacity=S,block_capacity=K,string_capacity=T,byte_capacity=A)
        note(queued.errors);committed=~(errors!=0).any()
        output=DeviceStateBatch(state.context,torch.where(committed,queued.state.records,_pad(state.records,(B,S,5))),
            torch.where(committed,queued.state.lengths,state.lengths),torch.where(committed,queued.state.sections,state.sections),
            torch.where(committed,queued.state.string_bytes,_pad(state.string_bytes,(A,))),torch.where(committed,queued.state.string_offsets,_pad(state.string_offsets,(T+1,))),
            state.errors,torch.where(committed,queued.state.suffix_usage,state.suffix_usage))
        required_state=torch.maximum(changed.required_state_capacity,queued.required_state_capacity)
        required_block=torch.maximum(build.required_capacity,queued.required_block_capacity)
        return EvolutionChoiceResult(output,errors,active&committed,queued.generated_ids,needed_options,needed_keys,encoded.required_bytes,
            names.required_bytes,queued.required_id_bytes,required_state,required_block,torch.maximum(added.required_usage,queued.required_string_usage),selected&committed,committed)
