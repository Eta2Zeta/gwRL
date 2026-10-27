"""Resident rule effects for an already listed recruitment-roll action.

The source-bound legal menu remains authoritative: this seam consumes its full
Action and saved threshold without regenerating choices. It marks the minor's
attempt, reserves one continuation and installs one unmodified D12 request.
It does not charge IPP. Outer Engine validation/clock checks, income refresh,
TrainingRules reset and history append remain separate transaction stages.
Recruitment placement and refreshPoliticalState are outside this rule seam.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_state_edits import replace_subtrees
from .device_map_edits import MapMode,build_map_edits,commit_container_edits
from .device_strings import intern_bytes
from .resident_chance_io import _pool
from .resident_recruitment import RecruitmentMenu,SOURCE as QUERY_SOURCE

LOOKUP_ERROR,NATIVE_ERROR,PACKED_ERROR,CAPACITY_ERROR=1,2,3,5


@dataclass(frozen=True)
class RecruitmentStartResult:
    state: DeviceStateBatch
    errors: torch.Tensor
    handled: torch.Tensor
    accepted: torch.Tensor
    committed: torch.Tensor
    required_state_capacity: torch.Tensor
    required_block_capacity: torch.Tensor
    required_string_usage: torch.Tensor


SOURCE=QUERY_SOURCE+r'''
inline bool start_scalar(device const long* row,long tag,long end){
 return row[0]==tag&&!row[2]&&!row[3]&&row[4]==end;
}
kernel void prepare_recruitment_start(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const long* actions[[buffer(3)]],device const long* action_lengths[[buffer(4)]],device const long* action_errors[[buffer(5)]],
 device const long* requests[[buffer(6)]],device const long* metadata[[buffer(7)]],device const long* query_errors[[buffer(8)]],
 device const long* count[[buffer(9)]],device const int* batch_error[[buffer(10)]],device const long* selections[[buffer(11)]],
 device const bool* selected[[buffer(12)]],device const long* ids[[buffer(13)]],device const long* definition[[buffer(14)]],
 device const uchar* prefix[[buffer(15)]],device const long* poffsets[[buffer(16)]],device const uchar* suffix[[buffer(17)]],
 device const long* soffsets[[buffer(18)]],device const long* usage[[buffer(19)]],device const long* pool_error[[buffer(20)]],
 device const uchar* id_bytes[[buffer(21)]],device const long* id_lengths[[buffer(22)]],
 device uchar* names[[buffer(23)]],device long* name_lengths[[buffer(24)]],device long* data[[buffer(25)]],
 device long* errors[[buffer(26)]],device const long* dims[[buffer(27)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],P=dims[2],Q=dims[3],N=dims[4],Players=dims[5];if(long(lane)>=B)return;
 errors[lane]=0;name_lengths[lane]=0;device long* out=data+ulong(lane)*5;
 for(long i=0;i<5;++i)out[i]=-1;if(!selected[lane])return;
 if(inherited[lane]||pool_error[0]){errors[lane]=3;return;}
 if(batch_error[0]){errors[lane]=batch_error[0]==5?5:3;return;}
 if(count[0]<0||count[0]>P){errors[lane]=3;return;}
 const long chosen=selections[lane];if(chosen<0||chosen>=count[0]){errors[lane]=2;return;}
 // The emitter groups full actions by query, preserving native map order.
 long first=0,query=-1;
 for(long q=0;q<Q;++q){const long amount=metadata[ulong(q)*9+7];
   if(amount<0||amount>1||amount>LONG_MAX-first){errors[lane]=3;return;}
   if(chosen>=first&&chosen<first+amount)query=q;first+=amount;}
 if(first!=count[0]||query<0||requests[ulong(query)*2]!=long(lane)){errors[lane]=2;return;}
 if(query_errors[ulong(query)*5+4]||action_errors[chosen]){errors[lane]=3;return;}
 const long threshold=metadata[ulong(query)*9+1],player=metadata[ulong(query)*9+8];
 if(threshold<=0||threshold>INT_MAX||player<0||player>=Players){errors[lane]=3;return;}
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
   prefix,poffsets,dims[6],dims[7],suffix,soffsets,dims[8],dims[9],usage,valid);
 relations_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);relations_container(v,state,10,19,valid);
 const long nations=state_child(v,state,0,valid),minor=requests[ulong(query)*2+1];
 const long nation=state_map_find_id(v,nations,minor,valid);
 if(!valid){errors[lane]=3;return;}if(nation<0){errors[lane]=1;return;}
 relations_container(v,nation,10,12,valid);const long flags=state_child(v,nation,10,valid);relations_container(v,flags,7,-1,valid);
 const long clock=state_child(v,state,7,valid),turn=state_signed_value(v,state_child(v,clock,1,valid),valid);
 PackedStateView d{definition,dims[10],dims[10],prefix,poffsets,dims[6],dims[7],suffix,soffsets,0,0};
 const long order=state_child(d,0,6,valid);relations_container(d,order,6,-1,valid);
 if(!valid||turn<0||turn>=state_record(d,order)[1]){errors[lane]=3;return;}
 const long actor=state_string_id(d,state_child(d,order,turn,valid),valid);
 device const long* a=actions+ulong(chosen)*13*5;
 if(action_lengths[chosen]!=9||!start_scalar(a,10,9)||a[1]!=6||
    !start_scalar(a+5,5,2)||!start_scalar(a+10,5,3)||!start_scalar(a+15,5,4)||!start_scalar(a+20,5,5)||
    !start_scalar(a+25,9,6)||a[26]!=0||!start_scalar(a+30,13,9)||a[31]!=1||
    !start_scalar(a+35,5,8)||!start_scalar(a+40,5,9)){errors[lane]=2;return;}
 if(a[16]!=ids[N+player]||a[21]!=actor||a[41]!=minor){errors[lane]=2;return;}
 PackedStateView action=make_packed_state_view(a,9,13,prefix,poffsets,dims[6],dims[7],suffix,soffsets,dims[8],dims[9],usage,valid);
 if(!state_string_equals(action,2,"recruitment_roll",16,valid)||
    !state_string_equals(action,7,"beneficiary",11,valid)){errors[lane]=2;return;}
 const long action_id=state_string_id(action,1,valid);const bool fixed=action_id<v.prefix_count;
 const long local=fixed?action_id:action_id-v.prefix_count;
 device const long* offsets=fixed?v.prefix_offsets:v.suffix_offsets;
 device const uchar* text=fixed?v.prefix_bytes:v.suffix_bytes;
 if(!valid){errors[lane]=2;return;}
 const long begin=offsets[local],end=offsets[local+1];
 if(begin<0||end<begin||end>(fixed?v.prefix_bytes_length:v.suffix_bytes_length)||
    id_lengths[chosen]<0||id_lengths[chosen]>dims[11]||end-begin!=id_lengths[chosen]){errors[lane]=2;return;}
 for(long i=0;i<end-begin;++i)if(text[begin+i]!=id_bytes[ulong(chosen)*dims[11]+i]){errors[lane]=2;return;}
 // The original native helper requires an empty chance before allocating its ID.
 bool exists=false;(void)state_optional(v,state_child(v,state,14,valid),exists,valid);
 if(!valid){errors[lane]=3;return;}if(exists){errors[lane]=2;return;}
 const long global=state_child(v,state,15,valid),sequence=state_map_find_literal(v,global,"politics_sequence",17,valid);
 const long old=sequence<0?0:state_signed_value(v,sequence,valid);
 if(!valid||old<INT_MIN||old>INT_MAX){errors[lane]=3;return;}if(old==INT_MAX){errors[lane]=2;return;}
 const long next=old+1;out[0]=minor;out[1]=threshold;out[2]=flags;out[3]=next;out[4]=chosen;
 device uchar* name=names+ulong(lane)*28;constant char* stem="recruitment_roll_";long cursor=0;
 for(long i=0;i<17;++i)name[cursor++]=uchar(stem[i]);
 ulong magnitude=next<0?ulong(-next):ulong(next);if(next<0)name[cursor++]='-';
 char digits[10];int used=0;do{digits[used++]=char('0'+magnitude%10);magnitude/=10;}while(magnitude);
 while(used)name[cursor++]=uchar(digits[--used]);name_lengths[lane]=cursor;
}
kernel void recruitment_start_roots(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const bool* selected[[buffer(2)]],
 device const uchar* prefix[[buffer(3)]],device const long* poffsets[[buffer(4)]],device const uchar* suffix[[buffer(5)]],
 device const long* soffsets[[buffer(6)]],device const long* usage[[buffer(7)]],device long* roots[[buffer(8)]],
 device long* errors[[buffer(9)]],device const long* dims[[buffer(10)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;errors[lane]=0;roots[ulong(lane)*2]=roots[ulong(lane)*2+1]=-1;if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
   prefix,poffsets,dims[2],dims[3],suffix,soffsets,dims[4],dims[5],usage,valid);
 const long state=state_child(v,0,0,valid),politics=state_child(v,state,8,valid);
 roots[ulong(lane)*2]=state_child(v,state,15,valid);roots[ulong(lane)*2+1]=state_child(v,politics,10,valid);
 if(!valid)errors[lane]=3;
}
kernel void recruitment_start_blocks(
 device const long* data[[buffer(0)]],device const long* names[[buffer(1)]],device const long* labels[[buffer(2)]],
 device const bool* selected[[buffer(3)]],device long* sequence[[buffer(4)]],device long* parameters[[buffer(5)]],
 device long* chance[[buffer(6)]],device long* errors[[buffer(7)]],device const long* dims[[buffer(8)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;errors[lane]=0;if(!selected[lane])return;
 const long minor=data[ulong(lane)*5],threshold=data[ulong(lane)*5+1],next=data[ulong(lane)*5+3],id=names[lane];
 device long* flag=sequence+ulong(lane)*5;recruit_row(flag,0,2,0,1);
 flag[2]=long(as_type<ulong>(next)&0xffffffffUL);flag[3]=long(as_type<ulong>(next)>>32);
 device long* p=parameters+ulong(lane)*25;recruit_row(p,0,13,2,5);recruit_row(p,1,5,labels[0],2);
 recruit_row(p,2,5,minor,3);recruit_row(p,3,5,labels[2],4);recruit_row(p,4,4,0,5);
 bool valid=true;const ulong bits=state_json_integer_bits(threshold,valid);p[22]=long(bits&0xffffffffUL);p[23]=long(bits>>32);
 if(!valid){errors[lane]=3;return;}
 device long* c=chance+ulong(lane)*60;recruit_row(c,0,9,1,12);recruit_row(c,1,10,5,12);
 recruit_row(c,2,5,id,3);recruit_row(c,3,5,labels[1],4);recruit_row(c,4,5,minor,5);recruit_row(c,5,5,id,6);
 recruit_row(c,6,6,1,12);recruit_row(c,7,10,4,12);recruit_row(c,8,2,0,9);c[42]=12;
 recruit_row(c,9,2,0,10);recruit_row(c,10,8,0,11);recruit_row(c,11,2,0,12);
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
def _call(kernel,args,threads):
    if threads:kernel(*(value if value.numel() else _dummy() for value in args),threads=threads)
def _tensor(value,state,dtype,shape):
    if not isinstance(value,torch.Tensor) or value.dtype!=dtype or value.device!=state.device or tuple(value.shape)!=shape or not value.is_contiguous():
        raise ValueError("Recruitment start requires complete contiguous resident tensors")
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    result=torch.zeros(shape,dtype=value.dtype,device=value.device);result[tuple(slice(0,n) for n in value.shape)]=value;return result


class ResidentRecruitmentStart:
    def __init__(self,recruitment_context):
        self.recruitment=recruitment_context;self.state_context=recruitment_context.state_context
        names=("beneficiary","recruitment_roll","threshold","recruitment_attempted","politics_sequence")
        self.labels=torch.tensor(tuple(int(v) for v in self.state_context.prefix_lookup_ids(names)),dtype=torch.int64,device=self.state_context.device)

    def reserve(self,before,legal_roll_menu):
        """Metadata-only headroom for one start action in each resident lane."""
        B,C=before.records.shape[:2];arena=legal_roll_menu.arena
        return dict(state_capacity=C+24,block_capacity=C+6,
            string_capacity=arena.string_offsets.numel()-1+B,byte_capacity=arena.string_bytes.numel()+28*B)

    def apply(self,before,legal_roll_menu,selections,selected=None,*,state_capacity=None,block_capacity=None,
              string_capacity=None,byte_capacity=None):
        before._metadata();_device(before.device)
        if before.context is not self.state_context or before.device.type!="mps":raise ValueError("Recruitment start source/context differs")
        menu=legal_roll_menu
        if not isinstance(menu,RecruitmentMenu) or menu.source is not before or menu.queries.source is not before or not menu.queries.rolls:
            raise ValueError("Recruitment start requires the exact source-bound legal roll menu")
        arena=menu.arena;arena._metadata()
        if arena.context is not before.context or any(getattr(arena,name) is not getattr(before,name) for name in ("records","lengths","sections","errors")):
            raise ValueError("Recruitment menu arena changed game records instead of extending its namespace")
        if arena.string_offsets.numel()<before.string_offsets.numel() or arena.string_bytes.numel()<before.string_bytes.numel():
            raise ValueError("Recruitment menu namespace must preserve the complete source allocation")
        B,C=before.records.shape[:2];P=menu.actions.shape[0];Q=menu.queries.requests.shape[0];dev=before.device
        _tensor(selections,before,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,before,torch.bool,(B,))
        for value,dtype,shape in ((menu.actions,torch.int64,(P,13,5)),(menu.lengths,torch.int64,(P,)),(menu.errors,torch.int64,(P,)),
            (menu.queries.requests,torch.int64,(Q,2)),(menu.queries.metadata,torch.int64,(Q,9)),(menu.queries.errors,torch.int64,(Q,5)),
            (menu.count,torch.int64,(1,)),(menu.batch_error,torch.int32,(1,)),(menu.id_bytes.lengths,torch.int64,(P,))):_tensor(value,before,dtype,shape)
        if menu.id_bytes.data.ndim!=2 or menu.id_bytes.data.shape[0]!=P:raise ValueError("Recruitment menu ID byte layout differs")
        _tensor(menu.id_bytes.data,before,torch.uint8,tuple(menu.id_bytes.data.shape))
        S=C if state_capacity is None else state_capacity;K=max(C,1) if block_capacity is None else block_capacity
        if type(S) is not int or S<C or type(K) is not int or K<1:raise ValueError("Start capacities must preserve the source allocation")
        if B>2**32-1 or B*max(S,K,C,1)*5>2**63-1:raise OverflowError("Recruitment start allocation is not representable")
        for value in (before.records,before.lengths,before.sections,before.errors,before.context.records,before.context.string_bytes,
                      before.context.string_offsets,arena.string_bytes,arena.string_offsets,arena.suffix_usage):
            if value.device!=dev or not value.is_contiguous():raise ValueError("Recruitment start buffers must remain resident/contiguous")
        zeros=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        data,errors,name_lengths=zeros(B,5),zeros(B),zeros(B);names=torch.zeros((B,28),dtype=torch.uint8,device=dev)
        pool_error=_pool(before,arena)
        context=self.recruitment.relations_context
        if B:_call(_kernels().prepare_recruitment_start,(before.records,before.lengths,before.errors,menu.actions,menu.lengths,menu.errors,
            menu.queries.requests,menu.queries.metadata,menu.queries.errors,menu.count,menu.batch_error,selections,selected,context.ids,
            before.context.records,before.context.string_bytes,before.context.string_offsets,arena.string_bytes,arena.string_offsets,arena.suffix_usage,
            pool_error,menu.id_bytes.data,menu.id_bytes.lengths,names,name_lengths,data,errors,
            _dimensions((B,C,P,Q,len(context.nation_ids),len(context.player_ids),before.context.string_count,before.context.string_bytes.numel(),
                         arena.string_offsets.numel()-1,arena.string_bytes.numel(),before.context.records.shape[0],menu.id_bytes.data.shape[1]))),B)
        required_state=torch.full((B,),C,dtype=torch.int64,device=dev);required_block=torch.ones(B,dtype=torch.int64,device=dev)
        def healthy():return ~(errors!=0).any()
        def note(details):
            nonlocal errors
            errors=torch.where(selected&(errors==0)&(details!=0),details,errors)
        def container(build):
            nonlocal required_state,required_block
            result=commit_container_edits(build,capacity=S)
            required_state=torch.maximum(required_state,result.required_state_capacity);required_block=torch.maximum(required_block,build.required_capacity)
            capacity_bad=((build.errors&64)!=0)|((result.edit_errors&8)!=0)
            note(torch.where(result.errors!=0,torch.where(capacity_bad,5,3),0));return result.state
        interned=intern_bytes(arena,names,name_lengths,selected&healthy(),string_capacity=string_capacity,byte_capacity=byte_capacity)
        note(torch.where(interned.errors!=0,torch.where((interned.errors&8)!=0,5,3),0));current=interned.state
        attempted=zeros(B,1,5);attempted[:,0,0]=2;attempted[:,0,2]=1;attempted[:,0,4]=1
        current=container(build_map_edits(current,data[:,2].contiguous(),self.labels[3].expand(B).contiguous(),
            torch.full((B,),int(MapMode.UPSERT),dtype=torch.int64,device=dev),attempted,torch.ones(B,dtype=torch.int64,device=dev),
            selected&healthy(),capacity=K))
        roots,root_errors=zeros(B,2),zeros(B)
        if B:_call(_kernels().recruitment_start_roots,(current.records,current.lengths,selected&healthy(),current.context.string_bytes,
            current.context.string_offsets,current.string_bytes,current.string_offsets,current.suffix_usage,roots,root_errors,
            _dimensions((B,current.records.shape[1],current.context.string_count,current.context.string_bytes.numel(),
                         current.string_offsets.numel()-1,current.string_bytes.numel()))),B)
        note(root_errors)
        sequence,parameters,chance,block_errors=zeros(B,1,5),zeros(B,5,5),zeros(B,12,5),zeros(B)
        if B:_call(_kernels().recruitment_start_blocks,(data,interned.ids,self.labels,selected&healthy(),sequence,parameters,chance,block_errors,_dimensions((B,))),B)
        note(block_errors)
        current=container(build_map_edits(current,roots[:,0].contiguous(),self.labels[4].expand(B).contiguous(),
            torch.full((B,),int(MapMode.UPSERT),dtype=torch.int64,device=dev),sequence,torch.ones(B,dtype=torch.int64,device=dev),selected&healthy(),capacity=K))
        current=container(build_map_edits(current,roots[:,1].contiguous(),interned.ids,
            torch.full((B,),int(MapMode.UPSERT),dtype=torch.int64,device=dev),parameters,torch.full((B,),5,dtype=torch.int64,device=dev),selected&healthy(),capacity=K))
        installed=replace_subtrees(current,current.section("state.chance").contiguous(),chance,torch.full((B,),12,dtype=torch.int64,device=dev),
            selected&healthy(),capacity=S)
        required_state=torch.maximum(required_state,installed.required_capacity)
        note(torch.where(installed.errors!=0,torch.where((installed.errors&8)!=0,5,3),0));current=installed.state
        committed=healthy();publish=committed&selected.any()
        output=DeviceStateBatch(before.context,torch.where(publish,current.records,_pad(before.records,(B,S,5))),
            torch.where(publish,current.lengths,before.lengths),torch.where(publish,current.sections,before.sections),
            torch.where(publish,current.string_bytes,_pad(before.string_bytes,tuple(current.string_bytes.shape))),
            torch.where(publish,current.string_offsets,_pad(before.string_offsets,tuple(current.string_offsets.shape))),
            before.errors,torch.where(publish,current.suffix_usage,before.suffix_usage))
        return RecruitmentStartResult(output,errors,selected,selected&committed,committed,required_state,required_block,
                                     torch.maximum(menu.required_usage,interned.required_usage))
