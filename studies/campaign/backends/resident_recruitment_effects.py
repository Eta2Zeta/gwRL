"""Exact recruitment roll effects, including the Engine clear-chance pre-hook.

The saved threshold controls success. Only successful rolls regenerate current
choices, after erasing the old continuation. A real queued decision increments
politics_sequence once. Treasury, clock, history, RNG and action_interface remain
unchanged. Full transactions must separately mirror PoliticsRules' guarded income refresh,
TrainingRules' reset/forward hook, Engine validation/history and sampled-RNG commit.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_state_edits import replace_subtrees
from .device_map_edits import MapMode,build_map_edits,build_sequence_splices,commit_container_edits
from .device_strings import intern_bytes
from .packed_chance_metal import PackedChanceResult
from .resident_recruitment import SOURCE as QUERY_SOURCE

LOOKUP_ERROR,NATIVE_ERROR,PACKED_ERROR,SAMPLER_ERROR,CAPACITY_ERROR=1,2,3,4,5


@dataclass(frozen=True)
class RecruitmentEffectResult:
    state: DeviceStateBatch
    errors: torch.Tensor
    handled: torch.Tensor
    accepted: torch.Tensor
    committed: torch.Tensor
    required_state_capacity: torch.Tensor
    required_block_capacity: torch.Tensor
    required_string_usage: torch.Tensor
    required_choice_capacity: torch.Tensor
    required_parameter_bytes: torch.Tensor


SOURCE=QUERY_SOURCE+r'''
inline long recruit_json_int(thread const PackedStateView& v,long node,thread long& error,thread bool& valid){
 if(node<0||!state_node(v,node)||state_record(v,node)[0]!=4){error=2;return 0;}
 const ulong bits=state_raw_bits(v,node,4,valid);long value=0;
 if(valid&&!state_json_integer_value(bits,value))error=2;return value;
}
kernel void validate_recruitment_effect(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* source_errors[[buffer(2)]],
 device const bool* selected[[buffer(3)]],device const int* faces[[buffer(4)]],device const int* face_counts[[buffer(5)]],
 device const int* effective[[buffer(6)]],device const long* dice_counts[[buffer(7)]],device const int* sample_errors[[buffer(8)]],
 device const uchar* prefix[[buffer(9)]],device const long* poffsets[[buffer(10)]],device const uchar* suffix[[buffer(11)]],
 device const long* soffsets[[buffer(12)]],device const long* usage[[buffer(13)]],device long* data[[buffer(14)]],
 device long* pending_roots[[buffer(15)]],device long* errors[[buffer(16)]],device bool* handled[[buffer(17)]],
 device const long* dims[[buffer(18)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],D=dims[2],R=dims[3];if(long(lane)>=B)return;
 device long* out=data+ulong(lane)*3;out[0]=out[1]=-1;out[2]=0;pending_roots[lane]=-1;errors[lane]=0;handled[lane]=false;
 if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
   prefix,poffsets,dims[4],dims[5],suffix,soffsets,dims[6],dims[7],usage,valid);
 if(source_errors[lane]||v.length<=0||v.length>C)valid=false;
 relations_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);relations_container(v,state,10,19,valid);
 bool exists=false;const long request=state_optional(v,state_child(v,state,14,valid),exists,valid);
 if(!valid){errors[lane]=3;return;}if(!exists)return;
 relations_container(v,request,10,5,valid);
 const bool recruitment=state_string_equals(v,state_child(v,request,1,valid),"recruitment_roll",16,valid);
 if(!valid){errors[lane]=3;return;}if(!recruitment)return;handled[lane]=true;
 if(sample_errors[lane]||D<1||R<1){errors[lane]=4;return;}
 const long dice=state_child(v,request,4,valid);relations_container(v,dice,6,-1,valid);
 if(!valid){errors[lane]=3;return;}
 if(state_record(v,dice)[1]!=1||dice_counts[lane]!=1){errors[lane]=2;return;}
 const long die=state_child(v,dice,0,valid);relations_container(v,die,10,4,valid);
 const long sides=state_signed_value(v,state_child(v,die,0,valid),valid);
 const long modifier=state_signed_value(v,state_child(v,die,1,valid),valid);
 const long maximum=state_signed_value(v,state_child(v,die,3,valid),valid);
 if(!valid){errors[lane]=3;return;}
 // Reroll-face membership is irrelevant with maxRerolls0, as in the native rule.
 if(sides!=12||modifier!=0||maximum!=0||face_counts[ulong(lane)*D]!=1){errors[lane]=2;return;}
 const int raw=faces[ulong(lane)*D*R];
 if(raw<1||raw>12){errors[lane]=2;return;}
 if(effective[ulong(lane)*D]!=raw){errors[lane]=4;return;}
 const long nation=state_string_id(v,state_child(v,request,2,valid),valid);
 const long continuation=state_string_id(v,state_child(v,request,3,valid),valid);
 const long politics=state_child(v,state,8,valid),pending=state_child(v,politics,10,valid);
 const long parameters=state_map_find_id(v,pending,continuation,valid);
 if(!valid){errors[lane]=3;return;}if(parameters<0){errors[lane]=1;return;}
 if(state_record(v,parameters)[0]!=13){errors[lane]=2;return;}
 long error=0;const long threshold=recruit_json_int(v,state_map_find_literal(v,parameters,"threshold",9,valid),error,valid);
 if(!valid){errors[lane]=3;return;}if(error||threshold<=0){errors[lane]=2;return;}
 const long beneficiary=state_map_find_literal(v,parameters,"beneficiary",11,valid);
 if(!valid){errors[lane]=3;return;}
 if(beneficiary<0||state_record(v,beneficiary)[0]!=5){errors[lane]=2;return;}
 const long minor=state_string_id(v,beneficiary,valid);
 if(!valid){errors[lane]=3;return;}if(minor!=nation){errors[lane]=2;return;}
 out[0]=minor;out[1]=continuation;out[2]=raw<=threshold;pending_roots[lane]=pending;
}
kernel void summarize_recruitment_menu(
 device const long* metadata[[buffer(0)]],device const long* query_errors[[buffer(1)]],device const long* menu_errors[[buffer(2)]],
 device const int* parameter_errors[[buffer(3)]],device const int* id_errors[[buffer(4)]],device const int* batch_error[[buffer(5)]],
 device const long* count[[buffer(6)]],device const long* required_usage[[buffer(7)]],device const bool* selected[[buffer(8)]],
 device long* errors[[buffer(9)]],device const long* dims[[buffer(10)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;errors[lane]=0;if(!selected[lane])return;
 if(query_errors[ulong(lane)*5+3]){errors[lane]=query_errors[ulong(lane)*5+3];return;}
 const long amount=metadata[ulong(lane)*9+7];if(!amount)return;
 if(batch_error[0]){if(batch_error[0]==5)errors[lane]=5;return;}
 if(count[0]<0||count[0]>dims[1]){errors[lane]=3;return;}
 if(required_usage[0]>dims[2]||required_usage[1]>dims[3]){errors[lane]=5;return;}
 long result=0;
 for(long row=0;row<count[0];++row){
   if((parameter_errors[row]&2)||(id_errors[row]&2)){result=5;break;}
   if(parameter_errors[row]||id_errors[row]||menu_errors[row])result=3;
 }
 errors[lane]=result;
}
kernel void prepare_recruitment_decision(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* data[[buffer(2)]],
 device const bool* selected[[buffer(3)]],device const long* definition[[buffer(4)]],
 device const uchar* prefix[[buffer(5)]],device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],
 device const long* soffsets[[buffer(8)]],device const long* usage[[buffer(9)]],device uchar* names[[buffer(10)]],
 device long* name_lengths[[buffer(11)]],device long* flag_values[[buffer(12)]],device long* roots[[buffer(13)]],
 device bool* reactions[[buffer(14)]],device long* errors[[buffer(15)]],device const long* dims[[buffer(16)]],
 uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1];if(long(lane)>=B)return;
 name_lengths[lane]=0;errors[lane]=0;reactions[lane]=false;for(long i=0;i<3;++i)roots[ulong(lane)*3+i]=-1;
 if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
   prefix,poffsets,dims[2],dims[3],suffix,soffsets,dims[4],dims[5],usage,valid);
 const long state=state_child(v,0,0,valid),flags=state_child(v,state,15,valid),politics=state_child(v,state,8,valid);
 const long pending=state_child(v,politics,10,valid),decisions=state_child(v,state,11,valid);
 relations_container(v,decisions,6,-1,valid);
 const long sequence=state_map_find_literal(v,flags,"politics_sequence",17,valid);
 long old=sequence<0?0:state_signed_value(v,sequence,valid);
 if(old<INT_MIN||old>INT_MAX)valid=false;
 if(!valid){errors[lane]=3;return;}if(old==INT_MAX){errors[lane]=2;return;}
 const long next=old+1;device long* value=flag_values+ulong(lane)*5;
 value[0]=2;value[1]=0;value[2]=long(as_type<ulong>(next)&0xffffffffUL);value[3]=long(as_type<ulong>(next)>>32);value[4]=1;
 const long clock=state_child(v,state,7,valid),turn=state_signed_value(v,state_child(v,clock,1,valid),valid);
 PackedStateView d{definition,dims[6],dims[6],prefix,poffsets,dims[2],dims[3],suffix,soffsets,0,0};
 const long active=state_string_id(d,state_child(d,state_child(d,0,6,valid),turn,valid),valid);
 if(!valid){errors[lane]=3;return;}
 reactions[lane]=active!=data[ulong(lane)*3];
 roots[ulong(lane)*3]=flags;roots[ulong(lane)*3+1]=pending;roots[ulong(lane)*3+2]=state_record(v,decisions)[1];
 device uchar* out=names+ulong(lane)*30;constant char* stem="recruitment_choice_";long cursor=0;
 for(long i=0;i<19;++i)out[cursor++]=uchar(stem[i]);
 ulong magnitude=next<0?ulong(-next):ulong(next);if(next<0)out[cursor++]='-';
 char digits[10];int used=0;do{digits[used++]=char('0'+magnitude%10);magnitude/=10;}while(magnitude);
 while(used)out[cursor++]=uchar(digits[--used]);name_lengths[lane]=cursor;
}
kernel void write_recruitment_decisions(
 device const long* actions[[buffer(0)]],device const long* action_lengths[[buffer(1)]],device const long* metadata[[buffer(2)]],
 device const long* names[[buffer(3)]],device const long* data[[buffer(4)]],device const bool* reactions[[buffer(5)]],
 device const bool* selected[[buffer(6)]],device const long* labels[[buffer(7)]],device long* output[[buffer(8)]],
 device long* lengths[[buffer(9)]],device long* required[[buffer(10)]],device long* errors[[buffer(11)]],
 device const long* dims[[buffer(12)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],P=dims[1],R=dims[2];if(long(lane)>=B)return;lengths[lane]=required[lane]=errors[lane]=0;
 if(!selected[lane])return;long first=0;for(long i=0;i<long(lane);++i)first+=metadata[ulong(i)*9+7];
 const long amount=metadata[ulong(lane)*9+7];if(amount<=0||first<0||first>P||amount>P-first){errors[lane]=3;return;}
 long total=7;
 for(long i=0;i<amount;++i){const long n=action_lengths[first+i];
   if(n<7||n>13||n+1>LONG_MAX-total){errors[lane]=3;return;}total+=n+1;}
 required[lane]=total;if(total>R){errors[lane]=5;return;}
 device long* out=output+ulong(lane)*R*5;const long id=names[lane],minor=data[ulong(lane)*3];
 recruit_row(out,0,10,6,total);recruit_row(out,1,5,id,2);recruit_row(out,2,5,labels[10],3);recruit_row(out,3,5,minor,4);
 recruit_row(out,4,1,long(reactions[lane]),5);recruit_row(out,5,5,id,6);recruit_row(out,6,6,amount,total);
 long cursor=7;
 for(long i=0;i<amount;++i){const long at=first+i,n=action_lengths[at];device const long* source=actions+ulong(at)*13*5;
   if(source[0]!=10||source[1]!=6||source[4]!=n||source[25]!=9||source[26]!=0){errors[lane]=3;return;}
   for(long node=0;node<n;++node){
     if(node==5){recruit_row(out,cursor+5,9,1,cursor+7);recruit_row(out,cursor+6,5,id,cursor+7);continue;}
     const long dest=cursor+node+(node>=6?1:0);
     for(long col=0;col<4;++col)out[dest*5+col]=source[node*5+col];
     out[dest*5+4]=source[node*5+4]+cursor+((node==0||node>=6)?1:0);
   }
   cursor+=n+1;
 }
 lengths[lane]=total;
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
        raise ValueError("Recruitment effects require complete contiguous resident tensors")
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    result=torch.zeros(shape,dtype=value.dtype,device=value.device);result[tuple(slice(0,n) for n in value.shape)]=value;return result


class ResidentRecruitmentEffects:
    def __init__(self,recruitment_context):
        self.recruitment=recruitment_context;self.state_context=recruitment_context.state_context

    def reserve(self,state,*,choice_capacity):
        """Conservative metadata-only capacities for this rule seam alone."""
        if type(choice_capacity) is not int or choice_capacity<0:raise ValueError("Choice capacity must be nonnegative")
        B,C=state.records.shape[:2];decision=7+14*choice_capacity
        return dict(state_capacity=C+decision+6,block_capacity=C+decision,choice_capacity=choice_capacity,
                    parameter_byte_capacity=512,string_capacity=state.string_offsets.numel()-1+choice_capacity+B,
                    byte_capacity=state.string_bytes.numel()+choice_capacity*self.recruitment.id_capacity+30*B)

    def apply(self,before,sampled,selected=None,*,state_capacity=None,block_capacity=None,choice_capacity=None,
              parameter_byte_capacity=512,string_capacity=None,byte_capacity=None):
        before._metadata();_device(before.device)
        if before.context is not self.state_context or before.device.type!="mps":raise ValueError("Recruitment effect source/context differs")
        if not isinstance(sampled,PackedChanceResult) or sampled.source is not before:raise ValueError("Recruitment sample belongs to another complete source")
        B,C=before.records.shape[:2];dev=before.device
        if sampled.faces.ndim!=3 or sampled.faces.shape[0]!=B:raise ValueError("Recruitment sampled face layout differs")
        D,R=sampled.faces.shape[1:]
        for value,dtype,shape in ((sampled.faces,torch.int32,(B,D,R)),(sampled.face_counts,torch.int32,(B,D)),
                (sampled.effective,torch.int32,(B,D)),(sampled.dice_counts,torch.int64,(B,)),(sampled.errors,torch.int32,(B,))):_tensor(value,before,dtype,shape)
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,before,torch.bool,(B,))
        S=C if state_capacity is None else state_capacity;K=max(C,1) if block_capacity is None else block_capacity
        if type(S) is not int or S<C or type(K) is not int or K<1:raise ValueError("Effect capacities must preserve the full source allocation")
        if B>2**32-1 or B*max(S,K,C,1)*5>2**63-1:raise OverflowError("Recruitment effect allocation is not representable")
        for value in (before.records,before.lengths,before.sections,before.errors,before.context.records,before.context.string_bytes,
                      before.context.string_offsets,before.string_bytes,before.string_offsets,before.suffix_usage):
            if value.device!=dev or not value.is_contiguous():raise ValueError("Recruitment source buffers must remain resident/contiguous")
        zeros=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        data,pending_roots,errors=zeros(B,3),zeros(B),zeros(B)
        handled=torch.zeros(B,dtype=torch.bool,device=dev)
        if B:_call(_kernels().validate_recruitment_effect,(before.records,before.lengths,before.errors,selected,sampled.faces,sampled.face_counts,
            sampled.effective,sampled.dice_counts,sampled.errors,before.context.string_bytes,before.context.string_offsets,before.string_bytes,
            before.string_offsets,before.suffix_usage,data,pending_roots,errors,handled,
            _dimensions((B,C,D,R,before.context.string_count,before.context.string_bytes.numel(),before.string_offsets.numel()-1,before.string_bytes.numel()))),B)
        active=selected&handled
        required_state=torch.full((B,),C,dtype=torch.int64,device=dev);required_block=torch.ones(B,dtype=torch.int64,device=dev)
        def healthy():return ~(errors!=0).any()
        def note(details,mask):
            nonlocal errors
            errors=torch.where(mask&(errors==0)&(details!=0),details,errors)
        def container(build,capacity):
            nonlocal required_state,required_block
            result=commit_container_edits(build,capacity=capacity)
            required_state=torch.maximum(required_state,result.required_state_capacity)
            required_block=torch.maximum(required_block,build.required_capacity)
            capacity_bad=((build.errors&64)!=0)|((result.edit_errors&8)!=0)
            details=torch.where(result.errors!=0,torch.where(capacity_bad,5,3),0)
            note(details,active)
            return result.state
        # The Engine resets chance before invoking the original politics hook.
        empty= zeros(B,1,5);empty[:,0,0]=9;empty[:,0,4]=1
        cleared=replace_subtrees(before,before.section("state.chance").contiguous(),empty,torch.ones(B,dtype=torch.int64,device=dev),
                                 active&healthy(),capacity=S)
        required_state=torch.maximum(required_state,cleared.required_capacity)
        note(torch.where(cleared.errors!=0,torch.where((cleared.errors&8)!=0,5,3),0),active)
        current=cleared.state
        no_values=zeros(B,0,5)
        erased=build_map_edits(current,pending_roots,data[:,1].contiguous(),torch.full((B,),int(MapMode.ERASE),dtype=torch.int64,device=dev),
            no_values,zeros(B),active&healthy(),capacity=K)
        current=container(erased,S)
        requests=torch.stack((torch.arange(B,dtype=torch.int64,device=dev),data[:,0]),1)
        success=active&(data[:,2]!=0)&healthy()
        menu=self.recruitment.choices(current,requests,selected=success,capacity=choice_capacity,
            parameter_byte_capacity=parameter_byte_capacity,string_capacity=string_capacity,byte_capacity=byte_capacity)
        P=menu.actions.shape[0];menu_errors=zeros(B)
        if B:_call(_kernels().summarize_recruitment_menu,(menu.queries.metadata,menu.queries.errors,menu.errors,
            menu.parameter_json.errors,menu.id_bytes.errors,menu.batch_error,menu.count,menu.required_usage,success,menu_errors,
            _dimensions((B,P,menu.arena.string_offsets.numel()-1,menu.arena.string_bytes.numel()))),B)
        note(menu_errors,success);current=menu.arena
        queue=success&(menu.queries.metadata[:,6]>0)&healthy()
        names=torch.zeros((B,30),dtype=torch.uint8,device=dev);name_lengths=zeros(B);flag_values=zeros(B,1,5);roots=zeros(B,3)
        reactions=torch.zeros(B,dtype=torch.bool,device=dev);sequence_errors=zeros(B)
        if B:_call(_kernels().prepare_recruitment_decision,(current.records,current.lengths,data,queue,current.context.records,
            current.context.string_bytes,current.context.string_offsets,current.string_bytes,current.string_offsets,current.suffix_usage,
            names,name_lengths,flag_values,roots,reactions,sequence_errors,
            _dimensions((B,current.records.shape[1],current.context.string_count,current.context.string_bytes.numel(),
                         current.string_offsets.numel()-1,current.string_bytes.numel(),current.context.records.shape[0]))),B)
        note(sequence_errors,queue)
        interned=intern_bytes(current,names,name_lengths,queue&healthy(),string_capacity=string_capacity,byte_capacity=byte_capacity)
        required_usage=torch.maximum(menu.required_usage,interned.required_usage)
        pool_capacity=(interned.errors&8)!=0
        note(torch.where(interned.errors!=0,torch.where(pool_capacity,5,3),0),queue)
        current=interned.state
        flags=build_map_edits(current,roots[:,0].contiguous(),self.recruitment.labels[11].expand(B).contiguous(),
            torch.full((B,),int(MapMode.UPSERT),dtype=torch.int64,device=dev),flag_values,torch.ones(B,dtype=torch.int64,device=dev),queue&healthy(),capacity=K)
        current=container(flags,S)
        continuation=zeros(B,3,5);continuation[:,0,0]=13;continuation[:,0,1]=1;continuation[:,0,4]=3
        continuation[:,1,0]=5;continuation[:,1,1]=self.recruitment.labels[0];continuation[:,1,4]=2
        continuation[:,2,0]=5;continuation[:,2,1]=data[:,0];continuation[:,2,4]=3
        pending=build_map_edits(current,roots[:,1].contiguous(),interned.ids,torch.full((B,),int(MapMode.UPSERT),dtype=torch.int64,device=dev),
            continuation,torch.full((B,),3,dtype=torch.int64,device=dev),queue&healthy(),capacity=K)
        current=container(pending,S)
        decisions=zeros(B,K,5);decision_lengths=zeros(B);decision_required=zeros(B);decision_errors=zeros(B)
        if B:_call(_kernels().write_recruitment_decisions,(menu.actions,menu.lengths,menu.queries.metadata,interned.ids,data,reactions,queue&healthy(),
            self.recruitment.labels,decisions,decision_lengths,decision_required,decision_errors,_dimensions((B,P,K))),B)
        required_block=torch.maximum(required_block,decision_required);note(decision_errors,queue)
        appended=build_sequence_splices(current,current.section("state.decisions").contiguous(),roots[:,2].contiguous(),zeros(B),
            decisions,decision_lengths,torch.ones(B,dtype=torch.int64,device=dev),queue&healthy(),capacity=K)
        current=container(appended,S)
        committed=healthy()
        # One final publish flag covers all selected lanes AND the global COW
        # string arena. No failed intermediate State is retained by the result.
        output=DeviceStateBatch(before.context,torch.where(committed,current.records,_pad(before.records,(B,S,5))),
            torch.where(committed,current.lengths,before.lengths),torch.where(committed,current.sections,before.sections),
            torch.where(committed,current.string_bytes,_pad(before.string_bytes,tuple(current.string_bytes.shape))),
            torch.where(committed,current.string_offsets,_pad(before.string_offsets,tuple(current.string_offsets.shape))),
            before.errors,torch.where(committed,current.suffix_usage,before.suffix_usage))
        return RecruitmentEffectResult(output,errors,handled,active&committed,committed,required_state,required_block,
            required_usage,menu.required_count,menu.parameter_json.required_bytes)
