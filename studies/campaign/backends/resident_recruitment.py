"""Recruitment queries and ordered political choices from resident State.

Recruitment has no garrison requirement; that predicate belongs to influence.
These read-only services do not collect income, pay IPP, advance ship queues,
place units, repair facilities, consume RNG or append Engine history. Generated
Action records use a separate menu arena; the source game's namespace is intact.
"""
from dataclasses import dataclass,replace
from functools import lru_cache
from types import SimpleNamespace
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .resident_relations import SOURCE as RELATIONS_SOURCE
from .canonical_json_metal import canonical_json_subtrees,canonical_json_digests
from .resident_action_ids import ActionIdFamily,action_id_strings,construct_action_ids
from .device_strings import intern_bytes

LITERALS=("beneficiary","zone","zones","project","facility","recruitment_roll",
          "recruitment_place_infantry","recruitment_place_militia","recruitment_advance_ship",
          "recruitment_repair_facility","recruitment_choice","politics_sequence")


@dataclass(frozen=True)
class RecruitmentQueries:
    source: DeviceStateBatch
    requests: torch.Tensor              # [Q,2]: lane,minor string ID
    metadata: torch.Tensor              # available,threshold,quiet,Z,S,F,choices,emit,player
    errors: torch.Tensor                # [Q,5]: available,threshold,zones,choices,roll
    zones: torch.Tensor                 # [Q,T] actual ordered strings; count in metadata
    relations: object
    rolls: bool


@dataclass(frozen=True)
class RecruitmentMenu:
    source: DeviceStateBatch
    arena: DeviceStateBatch             # Ephemeral namespace, not a game transition.
    queries: RecruitmentQueries
    actions: torch.Tensor               # [capacity,13,5], native Action6 roots
    lengths: torch.Tensor
    count: torch.Tensor
    required_count: torch.Tensor
    batch_error: torch.Tensor
    errors: torch.Tensor
    required_usage: torch.Tensor
    parameter_json: object
    id_bytes: object


SOURCE=RELATIONS_SOURCE+r'''
inline long recruit_offshore(long zone,device const long* tokens,device const long* steps,
 long count,long pre_error,thread long& error){
 if(pre_error){error=pre_error;return 0;}
 for(long i=0;i<count;++i){if(steps[i*3+1]){error=steps[i*3+1];return 0;}
   if(tokens[steps[i*3]]==zone)return 1;}
 return 0;
}
inline bool recruit_ship(thread const PackedStateView& v,long root,long minor,
 device const long* naval,long count,thread bool& valid){
 relations_container(v,root,10,8,valid);
 if(state_string_id(v,state_child(v,root,1,valid),valid)!=minor)return false;
 const long payments=state_child(v,root,6,valid);relations_container(v,payments,6,-1,valid);
 if(!valid||!state_record(v,payments)[1])return false;
 if(state_signed_value(v,state_child(v,root,4,valid),valid)<=1)return false;
 const long type=state_string_id(v,state_child(v,root,2,valid),valid);
 for(long i=0;i<count;++i)if(naval[i]==type)return true;return false;
}
inline bool recruit_facility(thread const PackedStateView& v,long root,long land,long minor,
 thread long& error,thread bool& valid){
 relations_container(v,root,10,5,valid);
 if(state_signed_value(v,state_child(v,root,3,valid),valid)<=0)return false;
 const long zone=state_string_id(v,state_child(v,root,2,valid),valid);
 const long territory=state_map_find_id(v,land,zone,valid);
 if(territory<0){error=1;return false;}
 return relations_optional_id(v,territory,0,valid)==minor;
}
kernel void query_recruitment(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const long* requests[[buffer(3)]],device long* output[[buffer(4)]],device long* errors[[buffer(5)]],
 device long* zones[[buffer(6)]],device const long* metadata[[buffer(7)]],device const long* pairs[[buffer(8)]],
 device const long* pair_errors[[buffer(9)]],device const long* players[[buffer(10)]],device const long* player_errors[[buffer(11)]],
 device const long* ids[[buffer(12)]],device const long* definition[[buffer(13)]],device const long* territories[[buffer(14)]],
 device const long* home[[buffer(15)]],device const long* offshore[[buffer(16)]],device const long* offshore_steps[[buffer(17)]],
 device const long* naval[[buffer(18)]],device const uchar* prefix[[buffer(19)]],device const long* poffsets[[buffer(20)]],
 device const uchar* suffix[[buffer(21)]],device const long* soffsets[[buffer(22)]],device const long* usage[[buffer(23)]],
 device const long* dims[[buffer(24)]],device const bool* selected[[buffer(25)]],uint q[[thread_position_in_grid]]){
 const long Q=dims[0],B=dims[1],C=dims[2],N=dims[3],T=dims[5];if(long(q)>=Q)return;
 device long* out=output+ulong(q)*9;device long* err=errors+ulong(q)*5;
 for(long i=0;i<9;++i)out[i]=0;out[8]=-1;for(long i=0;i<5;++i)err[i]=0;
 for(long i=0;i<T;++i)zones[ulong(q)*T+i]=-1;
 if(!selected[q])return;
 const long lane=requests[ulong(q)*2],minor=requests[ulong(q)*2+1];
 if(lane<0||lane>=B){for(long i=0;i<5;++i)err[i]=3;return;}
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
   prefix,poffsets,dims[6],dims[7],suffix,soffsets,dims[8],dims[9],usage,valid);
 if(inherited[lane]||v.length<=0||v.length>C||minor<0||minor>=v.prefix_count+v.suffix_count)valid=false;
 relations_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);relations_container(v,state,10,19,valid);
 const long national=state_child(v,state,0,valid),land=state_child(v,state,1,valid),clock=state_child(v,state,7,valid);
 const long decisions=state_child(v,state,11,valid),battles=state_child(v,state,12,valid),battle_order=state_child(v,state,13,valid);
 bool chance=false;state_optional(v,state_child(v,state,14,valid),chance,valid);
 const bool terminal=state_boolean_value(v,state_child(v,state,18,valid),valid);
 const long phase=state_signed_value(v,state_child(v,clock,2,valid),valid);
 const bool collected=state_boolean_value(v,state_child(v,clock,5,valid),valid);
 const ulong serial=state_unsigned_value(v,state_child(v,clock,4,valid),valid);
 relations_container(v,decisions,6,-1,valid);relations_container(v,battles,7,-1,valid);relations_container(v,battle_order,6,-1,valid);
 const bool quiet=!terminal&&phase==4&&!collected&&!chance&&!state_record(v,decisions)[1]&&!state_record(v,battles)[1]&&!state_record(v,battle_order)[1];
 out[2]=quiet;
 if(!valid){for(long i=0;i<5;++i)err[i]=3;return;}
 if(dims[15]&&!quiet)return;
 PackedStateView d{definition,dims[10],dims[10],prefix,poffsets,dims[6],dims[7],suffix,soffsets,0,0};
 const long turn_index=state_signed_value(v,state_child(v,clock,1,valid),valid),order=state_child(d,0,6,valid);
 const long active_id=state_string_id(d,state_child(d,order,turn_index,valid),valid),active=relations_index(ids,N,active_id);
 const long n=relations_index(ids,N,minor),nation=state_map_find_id(v,national,minor,valid);
 const bool ccp=state_string_id_equals(v,minor,"ccp",3,valid);
 device const long* meta=metadata+ulong(lane)*N*10;
 if(!valid||active<0){for(long i=0;i<5;++i)err[i]=3;return;}
 if(dims[15]&&(n<0||nation<0))return; // Native actions iterate present nations only.
 if(nation<0||n<0)err[0]=1;
 else {
   relations_container(v,nation,10,12,valid);const long flags=state_child(v,nation,10,valid);
   const bool attempted=relations_flag(v,flags,"recruitment_attempted",21,valid);
   const bool is_minor=state_string_equals(v,state_child(v,nation,3,valid),"minor",5,valid);
   if(!attempted){
     if(ccp)out[0]=minor==active_id&&is_minor;
     else if(is_minor&&!state_string_id_equals(v,minor,"kmt",3,valid)&&!meta[n*10+5]&&!meta[n*10+6]){
       if(state_string_id_equals(v,minor,"dadao",5,valid)&&state_string_id_equals(v,active_id,"japan",5,valid)&&
          meta[n*10+2]==dims[17]&&meta[n*10+7]){
         const long japan=relations_index(ids,N,active_id);out[0]=japan>=0&&meta[japan*10+6];
         // The special branch returns true only when all of its clauses hold;
         // otherwise ordinary direct control remains available below.
         if(!out[0])out[0]=minor!=active_id&&pairs[(ulong(lane)*N*N+n*N+active)*7];
       }else if(state_string_id_equals(v,minor,"mongolia",8,valid)&&minor==active_id)out[0]=meta[n*10+2]!=-1;
       else out[0]=minor!=active_id&&pairs[(ulong(lane)*N*N+n*N+active)*7];
     }
   }
 }
 if(!valid){for(long i=0;i<5;++i)err[i]=3;return;}
 if(dims[15]&&(err[0]||!out[0])){err[4]=err[0];return;}
 const long snapshot=state_child(v,state,9,valid),possessions=state_child(v,snapshot,0,valid);
 relations_container(v,land,7,-1,valid);const long end=state_end(v,land,valid),amount=state_record(v,land)[1];
 long cursor=land+1;
 for(long i=0;valid&&i<amount;++i){
   const long zone=state_string_id(v,cursor,valid),territory=state_end(v,cursor,valid);
   relations_container(v,territory,10,2,valid);
   if(relations_optional_id(v,territory,0,valid)==minor){
     if(!err[1]){long failure=0;const bool sea=!ccp&&recruit_offshore(zone,offshore,offshore_steps,dims[11],dims[13],failure);
       if(failure)err[1]=failure;else if(!sea)++out[1];}
     const long beginning=state_map_find_id(v,possessions,zone,valid);
     bool retained=false;
     if(beginning>=0){bool present=false;const long owner=state_optional(v,beginning,present,valid);
       retained=present&&state_string_id(v,owner,valid)==minor;}
     if(retained){
       const long flags=state_child(v,territory,1,valid),change=state_map_find_literal(v,flags,"last_possession_change_turn",27,valid);
       if(change>=0){const long value=state_signed_value(v,change,valid);if(value>=0&&ulong(value)==serial)retained=false;}
       if(retained&&ccp){const long index=relations_index(territories,T,zone);
         if(!dims[14])err[2]=1;else if(index<0)valid=false;else retained=home[index]!=0;}
       if(retained&&!err[2]){if(out[3]>=T){valid=false;break;}zones[ulong(q)*T+out[3]++]=zone;}
     }
   }
   cursor=state_end(v,territory,valid);
 }
 if(cursor!=end)valid=false;
 if(!valid){for(long i=0;i<5;++i)err[i]=3;return;}
 if(dims[15]&&(err[1]||out[1]<=0)){err[4]=err[1];return;}
 err[3]=err[2];
 const long player=n>=0?players[(ulong(lane)*N+n)*3]:-1;
 const long player_error=n>=0?player_errors[(ulong(lane)*N+n)*3]:1;
 if(out[3]&&!err[3]&&player_error)err[3]=player_error;
 if(!ccp&&!err[3]){
   const long builds=state_child(v,state,5,valid);relations_container(v,builds,7,-1,valid);
   const long finish=state_end(v,builds,valid),count=state_record(v,builds)[1];long at=builds+1;
   for(long i=0;valid&&!err[3]&&i<count;++i){state_string_id(v,at,valid);const long project=state_end(v,at,valid);
     if(recruit_ship(v,project,minor,naval,dims[12],valid)){if(player_error)err[3]=player_error;else ++out[4];}
     at=state_end(v,project,valid);}
   if(valid&&!err[3]&&at!=finish)valid=false;
   if(!err[3]){
     const long facilities=state_child(v,state,3,valid);relations_container(v,facilities,7,-1,valid);
     const long fe=state_end(v,facilities,valid),fc=state_record(v,facilities)[1];at=facilities+1;
     for(long i=0;valid&&!err[3]&&i<fc;++i){state_string_id(v,at,valid);const long facility=state_end(v,at,valid);
       long failure=0;if(recruit_facility(v,facility,land,minor,failure,valid)){if(player_error)err[3]=player_error;else ++out[5];}
       if(failure)err[3]=failure;at=state_end(v,facility,valid);}
     if(valid&&!err[3]&&at!=fe)valid=false;
   }
 }
 if(!valid){for(long i=0;i<5;++i)err[i]=3;out[7]=0;return;}
 if(!err[3])out[6]=out[3]+out[3]*(out[3]+1)/2+out[4]+out[5];
 if(!dims[15]){out[7]=out[6];out[8]=player;}
 else {
   if(err[3])err[4]=err[3];
   else if(out[6]){err[4]=player_errors[(ulong(lane)*N+active)*3];
     if(!err[4]){out[7]=1;out[8]=players[(ulong(lane)*N+active)*3];}}
 }
}
kernel void rank_recruitment(device const long* metadata[[buffer(0)]],device const long* errors[[buffer(1)]],
 device long* ranks[[buffer(2)]],device long* count[[buffer(3)]],device long* required[[buffer(4)]],
 device int* batch_error[[buffer(5)]],device const long* dims[[buffer(6)]],uint row[[thread_position_in_grid]]){
 if(row)return;long total=0;int error=0;
 for(long i=0;i<dims[0];++i){ranks[i]=total;const long amount=metadata[i*9+7];
   if(errors[i*5+dims[2]])error=int(errors[i*5+dims[2]]);
   if(amount<0||amount>LONG_MAX-total)error=3;else total+=amount;}
 required[0]=total;if(!error&&total>dims[1])error=5;batch_error[0]=error;count[0]=error?0:total;
}
inline void recruit_row(device long* rows,long at,long tag,long value,long end){
 rows[at*5]=tag;rows[at*5+1]=value;rows[at*5+2]=rows[at*5+3]=0;rows[at*5+4]=end;
}
inline void recruit_emit(long position,long query,long actor,long minor,long player,long kind,long first,long second,
 device long* params,device long* param_lengths,device long* descriptors,device const long* labels){
 device long* out=params+ulong(position)*7*5;const long len=kind==1?7:(kind==4?3:5);
 recruit_row(out,0,13,kind==4?1:2,len);recruit_row(out,1,5,labels[0],2);recruit_row(out,2,5,minor,3);
 if(kind!=4){const long key=kind==0?labels[1]:(kind==1?labels[2]:(kind==2?labels[3]:labels[4]));
   recruit_row(out,3,5,key,4);
   if(kind==1){recruit_row(out,4,12,2,7);recruit_row(out,5,5,first,6);recruit_row(out,6,5,second,7);}
   else recruit_row(out,4,5,first,5);}
 param_lengths[position]=len;
 device long* item=descriptors+ulong(position)*5;
 item[0]=query;item[1]=actor;item[2]=player;item[3]=labels[kind==4?5:6+kind];item[4]=kind;
}
kernel void emit_recruitment(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* requests[[buffer(2)]],device const long* metadata[[buffer(3)]],device const long* zones[[buffer(4)]],
 device const long* ranks[[buffer(5)]],device const int* batch_error[[buffer(6)]],device const long* ids[[buffer(7)]],
 device const long* definition[[buffer(8)]],device const long* naval[[buffer(9)]],device const long* labels[[buffer(10)]],
 device const uchar* prefix[[buffer(11)]],device const long* poffsets[[buffer(12)]],device const uchar* suffix[[buffer(13)]],
 device const long* soffsets[[buffer(14)]],device const long* usage[[buffer(15)]],device long* params[[buffer(16)]],
 device long* param_lengths[[buffer(17)]],device long* descriptors[[buffer(18)]],device const long* dims[[buffer(19)]],
 uint q[[thread_position_in_grid]]){
 const long Q=dims[0],C=dims[2],N=dims[3],T=dims[5];if(long(q)>=Q||batch_error[0])return;
 device const long* meta=metadata+ulong(q)*9;if(!meta[7])return;
 const long lane=requests[ulong(q)*2],minor=requests[ulong(q)*2+1];bool valid=true;
 PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix,poffsets,dims[6],dims[7],
   suffix,soffsets,dims[8],dims[9],usage,valid);const long state=state_child(v,0,0,valid);
 const long player=ids[N+meta[8]];long position=ranks[q];
 if(dims[15]){
   PackedStateView d{definition,dims[10],dims[10],prefix,poffsets,dims[6],dims[7],suffix,soffsets,0,0};
   const long clock=state_child(v,state,7,valid),turn=state_signed_value(v,state_child(v,clock,1,valid),valid);
   const long actor=state_string_id(d,state_child(d,state_child(d,0,6,valid),turn,valid),valid);
   recruit_emit(position,q,actor,minor,player,4,0,0,params,param_lengths,descriptors,labels);return;
 }
 for(long first=0;first<meta[3];++first)recruit_emit(position++,q,minor,minor,player,0,zones[ulong(q)*T+first],0,params,param_lengths,descriptors,labels);
 for(long first=0;first<meta[3];++first)for(long second=first;second<meta[3];++second)
   recruit_emit(position++,q,minor,minor,player,1,zones[ulong(q)*T+first],zones[ulong(q)*T+second],params,param_lengths,descriptors,labels);
 if(state_string_id_equals(v,minor,"ccp",3,valid))return;
 const long builds=state_child(v,state,5,valid),bc=state_record(v,builds)[1];long at=builds+1;
 for(long i=0;i<bc;++i){const long key=state_string_id(v,at,valid),project=state_end(v,at,valid);
   if(recruit_ship(v,project,minor,naval,dims[12],valid))recruit_emit(position++,q,minor,minor,player,2,key,0,params,param_lengths,descriptors,labels);
   at=state_end(v,project,valid);}
 const long land=state_child(v,state,1,valid),facilities=state_child(v,state,3,valid),fc=state_record(v,facilities)[1];at=facilities+1;
 for(long i=0;i<fc;++i){const long key=state_string_id(v,at,valid),facility=state_end(v,at,valid);long failure=0;
   if(recruit_facility(v,facility,land,minor,failure,valid))recruit_emit(position++,q,minor,minor,player,3,key,0,params,param_lengths,descriptors,labels);
   at=state_end(v,facility,valid);}
}
kernel void pack_recruitment_actions(device const long* descriptors[[buffer(0)]],device const long* params[[buffer(1)]],
 device const long* param_lengths[[buffer(2)]],device const long* ids[[buffer(3)]],device const long* count[[buffer(4)]],
 device const long* pooled_errors[[buffer(5)]],device const bool* committed[[buffer(6)]],
 device long* actions[[buffer(7)]],device long* lengths[[buffer(8)]],device long* errors[[buffer(9)]],
 device const long* dims[[buffer(10)]],uint row[[thread_position_in_grid]]){
 if(long(row)>=dims[0])return;lengths[row]=0;errors[row]=0;if(long(row)>=count[0])return;
 if(!committed[0]||pooled_errors[row]){errors[row]=8;return;}
 device long* out=actions+ulong(row)*13*5;device const long* item=descriptors+ulong(row)*5;
 const long len=param_lengths[row],total=6+len;
 recruit_row(out,0,10,6,total);recruit_row(out,1,5,ids[row],2);recruit_row(out,2,5,item[3],3);
 recruit_row(out,3,5,item[2],4);recruit_row(out,4,5,item[1],5);recruit_row(out,5,9,0,6);
 for(long node=0;node<len;++node){for(long col=0;col<4;++col)out[(6+node)*5+col]=params[(ulong(row)*7+node)*5+col];
   out[(6+node)*5+4]=params[(ulong(row)*7+node)*5+4]+6;}
 lengths[row]=total;
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
def _call(kernel,args,threads):kernel(*(x if x.numel() else _dummy() for x in args),threads=max(threads,1))


class ResidentRecruitment:
    def __init__(self,relations_context,native):
        self.relations_context=relations_context;self.state_context=relations_context.state_context
        if self.state_context.wire_context_fingerprint!=native.wire_context_fingerprint:
            raise ValueError("Recruitment static source/wire context differs")
        self.native_context=native;self.territories=tuple(native.territories)
        dev=self.state_context.device
        self.territory_tokens=torch.tensor(self.state_context.prefix_lookup_ids(self.territories),dtype=torch.int64,device=dev)
        self.naval_tokens=torch.tensor(self.state_context.prefix_lookup_ids(native.naval_types),dtype=torch.int64,device=dev)
        self.offshore_tokens=torch.tensor(self.state_context.prefix_lookup_ids(native.offshore_ids),dtype=torch.int64,device=dev)
        self.offshore_steps=torch.tensor(native.offshore_step_array(),dtype=torch.int64,device=dev)
        self.home=torch.tensor(native.chinese_home_array(),dtype=torch.int64,device=dev)
        self.labels=torch.tensor(self.state_context.prefix_lookup_ids(LITERALS),dtype=torch.int64,device=dev)
        self.parameter_context=SimpleNamespace(state_context=self.state_context,words=torch.empty((0,2),dtype=torch.int64,device=dev),
            offsets=torch.zeros(1,dtype=torch.int64,device=dev),bytes=torch.empty(0,dtype=torch.uint8,device=dev))
        self.id_capacity=max(len(x.encode()) for x in LITERALS[5:10])+max(len(x.encode()) for x in relations_context.nation_ids)+18

    def _layout(self,state,requests,relations,rolls):
        state._metadata();_device(state.device)
        if state.context.identity!=self.state_context.identity:raise ValueError("Recruitment state/source context differs")
        if state.device.type!="mps":raise ValueError("Recruitment requires explicit Apple MPS")
        if (not isinstance(requests,torch.Tensor) or requests.dtype!=torch.int64 or requests.ndim!=2 or requests.shape[1]!=2 or
                requests.device!=state.device or not requests.is_contiguous()):raise ValueError("Recruitment queries require resident contiguous int64[Q,2]")
        if relations.source is not state:raise ValueError("Recruitment relations belong to another complete source state")
        Q=requests.shape[0];B,C=state.records.shape[:2];N=len(self.relations_context.nation_ids);P=len(self.relations_context.player_ids)
        for value,shape in ((relations.metadata,(B,N,10)),(relations.pairs,(B,N,N,7)),(relations.pair_errors,(B,N,N,7)),
                            (relations.nations,(B,N,3)),(relations.nation_errors,(B,N,3))):
            if value.dtype!=torch.int64 or value.device!=state.device or tuple(value.shape)!=shape or not value.is_contiguous():
                raise ValueError("Recruitment relation tensor shape/dtype/device/layout differs")
        if Q>2**32-1:raise OverflowError("Recruitment query count is not representable; no truncation")
        axis=self.relations_context.player_ids.index("axis") if "axis" in self.relations_context.player_ids else -2
        dims=(Q,B,C,N,P,len(self.territories),state.context.string_count,state.context.string_bytes.numel(),
            state.string_offsets.numel()-1,state.string_bytes.numel(),state.context.records.shape[0],self.offshore_steps.shape[0],
            self.naval_tokens.shape[0],self.native_context.offshore_error,int(self.native_context.chinese_home_present),int(rolls),
            self.offshore_tokens.shape[0],axis)
        buffers=(state.records,state.lengths,state.errors,requests,relations.metadata,relations.pairs,relations.pair_errors,
            relations.nations,relations.nation_errors,self.relations_context.ids,state.context.records,self.territory_tokens,self.home,
            self.offshore_tokens,self.offshore_steps,self.naval_tokens,state.context.string_bytes,state.context.string_offsets,
            state.string_bytes,state.string_offsets,state.suffix_usage)
        if any(x.device!=state.device or not x.is_contiguous() for x in buffers):raise ValueError("Recruitment input buffers must retain contiguous resident layouts")
        return dims

    def query(self,state,requests,*,relations=None,rolls=False,selected=None):
        """Read raw Available/Threshold/Zones/Choices eligibility independently.

        rolls=True instead follows the legal recruitment-roll gates lazily:
        quiet placement -> availability -> threshold -> nonempty choices.
        This is recruitment only; influence/garrison actions are separate.
        """
        if type(rolls) is not bool:raise ValueError("Recruitment query mode must be explicit bool")
        if relations is None:relations=self.relations_context.compute(state)
        dims=self._layout(state,requests,relations,rolls);Q,B,C,N,P,T=dims[:6]
        if selected is None:selected=torch.ones(Q,dtype=torch.bool,device=state.device)
        if (not isinstance(selected,torch.Tensor) or selected.dtype!=torch.bool or selected.device!=state.device or
                selected.shape!=(Q,) or not selected.is_contiguous()):raise ValueError("Recruitment query selection must be a contiguous resident bool[Q]")
        metadata=torch.zeros((Q,9),dtype=torch.int64,device=state.device)
        errors=torch.zeros((Q,5),dtype=torch.int64,device=state.device)
        zones=torch.full((Q,T),-1,dtype=torch.int64,device=state.device)
        if Q:
            args=(state.records,state.lengths,state.errors,requests,metadata,errors,zones,relations.metadata,relations.pairs,
                relations.pair_errors,relations.nations,relations.nation_errors,self.relations_context.ids,state.context.records,
                self.territory_tokens,self.home,self.offshore_tokens,self.offshore_steps,self.naval_tokens,
                state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage,_dimensions(dims),selected)
            _call(_kernels().query_recruitment,args,Q)
        return RecruitmentQueries(state,requests,metadata,errors,zones,relations,rolls)

    def choices(self,state,requests,*,relations=None,capacity=None,parameter_byte_capacity=512,string_capacity=None,byte_capacity=None,selected=None):
        """Generate complete ordered choices in an explicit retryable arena.

        The default allocation covers geographic infantry/militia combinations,
        independently of State/history allocation. Extra ship/facility options
        that exceed it return exact required_count with no partial menu. The
        eventual game pipeline should reserve a measured fixed arena explicitly.
        """
        return self._menu(self.query(state,requests,relations=relations,selected=selected),capacity,parameter_byte_capacity,string_capacity,byte_capacity)

    def rolls(self,state,*,relations=None,capacity=None,parameter_byte_capacity=512,string_capacity=None,byte_capacity=None):
        B=state.lane_count;N=len(self.relations_context.nation_ids);dev=state.device
        requests=torch.stack((torch.arange(B,dtype=torch.int64,device=dev).repeat_interleave(N),
            self.relations_context.ids[:N].repeat(B)),1)
        return self._menu(self.query(state,requests,relations=relations,rolls=True),capacity,parameter_byte_capacity,string_capacity,byte_capacity)

    def _menu(self,queries,capacity,param_capacity,string_capacity,byte_capacity):
        state=queries.source;dims=self._layout(state,queries.requests,queries.relations,queries.rolls);Q,B,C,N,P,T=dims[:6];dev=state.device
        if capacity is None:capacity=Q if queries.rolls else Q*(T+T*(T+1)//2)
        if type(capacity) is not int or capacity<0 or capacity>2**32-1:raise ValueError("Recruitment menu capacity must be a representable allocation")
        if type(param_capacity) is not int or param_capacity<0:raise ValueError("Recruitment parameter byte capacity must be a nonnegative allocation")
        ranks=torch.zeros(Q,dtype=torch.int64,device=dev);count=torch.zeros(1,dtype=torch.int64,device=dev);required=torch.zeros_like(count)
        batch_error=torch.zeros(1,dtype=torch.int32,device=dev)
        _call(_kernels().rank_recruitment,(queries.metadata,queries.errors,ranks,count,required,batch_error,
              _dimensions((Q,capacity,4 if queries.rolls else 3))),1)
        params=torch.zeros((capacity,7,5),dtype=torch.int64,device=dev);lengths=torch.zeros(capacity,dtype=torch.int64,device=dev)
        descriptors=torch.zeros((capacity,5),dtype=torch.int64,device=dev)
        if Q:_call(_kernels().emit_recruitment,(state.records,state.lengths,queries.requests,queries.metadata,queries.zones,ranks,batch_error,
            self.relations_context.ids,state.context.records,self.naval_tokens,self.labels,state.context.string_bytes,state.context.string_offsets,
            state.string_bytes,state.string_offsets,state.suffix_usage,params,lengths,descriptors,_dimensions(dims)),Q)
        # Generic JSON subtree carrier only; never exposed as a playable State.
        parameter_arena=replace(state,records=params,lengths=lengths,sections=torch.zeros((capacity,27),dtype=torch.int64,device=dev),
                                errors=torch.zeros(capacity,dtype=torch.int64,device=dev))
        rows=torch.arange(capacity,dtype=torch.int64,device=dev)
        locations=torch.stack((rows,torch.zeros_like(rows)),1)
        encoded=canonical_json_subtrees(parameter_arena,locations,self.parameter_context,byte_capacity=param_capacity,count=count)
        encoded=replace(encoded,batch_error=encoded.batch_error|batch_error)
        digests=canonical_json_digests(encoded)
        fields=torch.stack((descriptors[:,3],descriptors[:,1],torch.full_like(rows,-1),torch.full_like(rows,-1)),1)
        strings=action_id_strings(state,fields)
        id_bytes=construct_action_ids(torch.full_like(rows,int(ActionIdFamily.POLITICAL)),strings,digests,byte_capacity=self.id_capacity,count=count)
        healthy=(id_bytes.batch_error==0).all()&~((id_bytes.errors!=0)&(rows<count[0])).any()
        pool=intern_bytes(state,id_bytes.data,id_bytes.lengths,(rows<count[0])&healthy,
                          string_capacity=string_capacity,byte_capacity=byte_capacity)
        actions=torch.zeros((capacity,13,5),dtype=torch.int64,device=dev);action_lengths=torch.zeros(capacity,dtype=torch.int64,device=dev)
        errors=torch.zeros(capacity,dtype=torch.int64,device=dev)
        _call(_kernels().pack_recruitment_actions,(descriptors,params,lengths,pool.ids,count,pool.errors,pool.committed,
            actions,action_lengths,errors,_dimensions((capacity,))),capacity)
        errors|=id_bytes.errors.to(torch.int64)
        errors|=torch.where((rows<count[0])&~healthy,8,0)
        return RecruitmentMenu(state,pool.state,queries,actions,action_lengths,count,required,batch_error,errors,pool.required_usage,encoded,id_bytes)

    def reserve(self,state,*,capacity):
        """Metadata-only safe namespace headroom for one eventual menu commit.

        Ordinary query callers can keep menu arenas ephemeral. Explicit reserve
        permits exact capacity retry and repeated unchanged queries reuse the
        same allocation; no per-call automatic padding growth is introduced.
        """
        if type(capacity) is not int or capacity<0:raise ValueError("Menu reserve capacity must be nonnegative")
        return dict(string_capacity=state.string_offsets.numel()-1+capacity,
                    byte_capacity=state.string_bytes.numel()+capacity*self.id_capacity)

    @staticmethod
    def inspect(menu):
        """Explicit byte-level diagnostic boundary, preserving arbitrary strings."""
        if menu.batch_error.detach().cpu().item():raise ValueError("Recruitment query/menu failed or needs capacity retry")
        count=menu.count.detach().cpu().item()
        if any(menu.errors[:count].detach().cpu().tolist()):raise ValueError("Recruitment encoding/intern capacity failed; retry required sizes")
        state=menu.arena;used,size=state.suffix_usage.detach().cpu().tolist()
        tables=[]
        for data,offsets in ((state.context.string_bytes,state.context.string_offsets),
            (state.string_bytes[:size],state.string_offsets[:used+1])):
            raw=bytes(data.detach().cpu().tolist());indices=offsets.detach().cpu().tolist()
            tables.extend(raw[a:b] for a,b in zip(indices,indices[1:]))
        def quote(raw):
            out=bytearray(b'"')
            for value in raw:
                if value in (34,92):out.extend((92,value))
                elif value<32:out.extend(("\\u%04x"%value).encode())
                else:out.append(value)
            out.append(34);return bytes(out)
        def encode(rows,root):
            tag,meta,_,_,end=rows[root]
            if tag==5:return quote(tables[meta])
            if tag==13:
                parts=[];at=root+1
                for _ in range(meta):
                    key=encode(rows,at);value=at+1;parts.append(key+b":"+encode(rows,value));at=rows[value][4]
                if at!=end:raise ValueError("Invalid generated JSON object")
                return b"{"+b",".join(parts)+b"}"
            if tag==12:
                parts=[];at=root+1
                for _ in range(meta):parts.append(encode(rows,at));at=rows[at][4]
                if at!=end:raise ValueError("Invalid generated JSON array")
                return b"["+b",".join(parts)+b"]"
            raise ValueError("Unexpected recruitment parameter type")
        result=[]
        for rows,length in zip(menu.actions[:count].detach().cpu().tolist(),menu.lengths[:count].detach().cpu().tolist(),strict=True):
            if rows[0]!=[10,6,0,0,length] or rows[5]!=[9,0,0,0,6]:raise ValueError("Invalid generated native Action")
            fields={key:encode(rows,index) for key,index in (("id",1),("kind",2),("player",3),("nation",4))}
            fields["decision"]=b"null";fields["parameters"]=encode(rows,6)
            result.append(b"{"+b",".join(quote(key.encode())+b":"+value for key,value in sorted(fields.items()))+b"}")
        return tuple(result)
