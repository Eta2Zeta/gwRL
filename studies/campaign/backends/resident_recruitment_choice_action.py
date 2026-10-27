"""Complete stored recruitment-choice Engine action, without menu regeneration.

The input is a native-validated immutable State and its checked complete Engine
identity. A cached current eligibility menu belongs to that exact source. Rule
effects, income, optional TrainingRules hooks, changed-footprint validation and
the original Action Event publish as one selected cohort, including its string
arena. An unsupported reached service is reported distinctly and rolls back.
"""
from dataclasses import dataclass,replace
from enum import IntFlag
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .metal_state_schema import METAL_STATE_SOURCE
from .resident_events import EventKind,EventLabels,EventPayloads,append_events
from .resident_state_json import StateIdentityBatch
from .resident_training_reset import ResidentTrainingReset
from .resident_recruitment_choice import RecruitmentChoiceCapacities
from .resident_recruitment import RecruitmentMenu
from .resident_recruitment_chance import (POLITICS_RULES_COMPONENT,ECONOMY_RULES_COMPONENT,
    RecruitmentForwardError,forward_training_decision,_invalid_identities)


class RecruitmentChoiceActionError(IntFlag):
    PREFLIGHT=1
    CAPABILITY=2
    EFFECTS=4
    INCOME=8
    RESET=16
    FORWARD_CAPABILITY=32
    FORWARD=64
    CLOCK=128
    RANDOM=256
    VALIDATION=512
    VALIDATION_CAPABILITY=1024
    IDENTITY=2048
    PAYLOAD=4096
    EVENT=8192


@dataclass(frozen=True)
class RecruitmentChoiceActionCapacities:
    choice:RecruitmentChoiceCapacities
    payload_capacity:int
    json_byte_capacity:int

    @property
    def state_capacity(self):return self.choice.political_refresh.state_capacity
    @property
    def block_capacity(self):return self.choice.political_refresh.block_capacity
    @property
    def string_capacity(self):return self.choice.political_refresh.string_capacity
    @property
    def byte_capacity(self):return self.choice.political_refresh.byte_capacity

    def validate(self,state,menu=None):
        if not isinstance(self.choice,RecruitmentChoiceCapacities):raise TypeError("Choice action requires its complete rule capacity contract")
        self.choice.validate(state,state if menu is None else menu.arena)
        if any(type(value) is not int or value<0 for value in (self.payload_capacity,self.json_byte_capacity)):
            raise ValueError("Choice action payload/JSON capacities must be explicit nonnegative allocations")
        if max(self.payload_capacity,self.json_byte_capacity)>2**63-1 or state.lane_count*max(self.state_capacity,self.block_capacity,self.payload_capacity,1)*5>2**63-1:
            raise OverflowError("Choice action arenas are not representable")


@dataclass(frozen=True)
class RecruitmentChoiceActionResult:
    source:DeviceStateBatch
    state:DeviceStateBatch
    identities:StateIdentityBatch
    errors:torch.Tensor
    stage_errors:dict
    required:dict
    attempted:dict
    handled:torch.Tensor
    unsupported:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE="#include <metal_stdlib>\nusing namespace metal;\n"+METAL_STATE_SOURCE+r'''
inline bool rqa_container(thread const PackedStateView& v,long root,long tag,long count,thread bool& valid){
 const long end=state_end(v,root,valid);if(!valid)return false;device const long* row=state_record(v,root);
 const long maximum=(tag==7||tag==13)?(end-root-1)/2:end-root-1;
 if(row[0]!=tag||row[1]<0||row[1]>maximum||(count>=0&&row[1]!=count)||row[2]||row[3])valid=false;return valid;
}
inline bool rqa_nonempty(thread const PackedStateView& v,long id,thread bool& valid){
 if(id<0||id>=v.prefix_count+v.suffix_count){valid=false;return false;}const bool p=id<v.prefix_count;
 const long local=p?id:id-v.prefix_count;device const long* offsets=p?v.prefix_offsets:v.suffix_offsets;
 const long a=offsets[local],b=offsets[local+1];if(a<0||b<a||b>(p?v.prefix_bytes_length:v.suffix_bytes_length)){valid=false;return false;}return b>a;
}
kernel void recruitment_choice_action_preflight(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* inherited[[buffer(2)]],device const long* selections[[buffer(3)]],device const bool* selected[[buffer(4)]],
 device const uchar* prefix[[buffer(5)]],device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],
 device const long* soffsets[[buffer(8)]],device const long* usage[[buffer(9)]],device long* roots[[buffer(10)]],
 device long* errors[[buffer(11)]],device const long* dims[[buffer(12)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;roots[lane]=-1;errors[lane]=0;if(!selected[lane])return;bool valid=true;
 auto v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],prefix,poffsets,dims[2],dims[3],suffix,soffsets,dims[4],dims[5],usage,valid);
 if(inherited[lane])valid=false;rqa_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);rqa_container(v,state,10,19,valid);
 if(!valid){errors[lane]=1;return;}const bool terminal=state_boolean_value(v,state_child(v,state,18,valid),valid);
 bool chance=false;state_optional(v,state_child(v,state,14,valid),chance,valid);
 if(!valid){errors[lane]=1;return;}if(terminal||chance){errors[lane]=2;return;}
 const long decisions=state_child(v,state,11,valid);rqa_container(v,decisions,6,-1,valid);if(!valid){errors[lane]=1;return;}
 const long amount=state_record(v,decisions)[1];if(!amount){errors[lane]=2;return;}
 const long decision=state_child(v,decisions,amount-1,valid);rqa_container(v,decision,10,6,valid);
 const long options=state_child(v,decision,5,valid);rqa_container(v,options,6,-1,valid);if(!valid){errors[lane]=1;return;}
 const long count=state_record(v,options)[1];long at=options+1;
 // State.validate already establishes unique IDs and each option's complete
 // entitlement. Engine.actionMenu additionally rejects a reserved identity
 // anywhere in this last menu, including an unselected option.
 for(long i=0;valid&&i<count;++i){rqa_container(v,at,10,6,valid);
   const long id=state_string_id(v,state_child(v,at,0,valid),valid),kind=state_string_id(v,state_child(v,at,1,valid),valid);
   if(!rqa_nonempty(v,id,valid)||!rqa_nonempty(v,kind,valid))errors[lane]|=2;
   if(state_string_id_equals(v,id,"end_phase",9,valid)||state_string_id_equals(v,kind,"end_phase",9,valid))errors[lane]|=2;
   rqa_container(v,state_child(v,at,5,valid),13,-1,valid);
   if(i==selections[lane])roots[lane]=at;at=state_end(v,at,valid);}
 if(!valid||at!=state_end(v,options,valid)){errors[lane]|=1;return;}
 if(selections[lane]<0||selections[lane]>=count)errors[lane]|=2;
}
inline bool rqa_same(device const long* a,long alength,long acap,long ar,device const long* b,long blength,long bcap,long br){
 if(ar<0||br<0||ar>=alength||br>=blength||alength>acap||blength>bcap)return false;
 const long ae=a[ulong(ar)*5+4],be=b[ulong(br)*5+4];if(ae<=ar||be<=br||ae>alength||be>blength||ae-ar!=be-br)return false;
 for(long i=0;i<ae-ar;++i){for(long c=0;c<4;++c)if(a[ulong(ar+i)*5+c]!=b[ulong(br+i)*5+c])return false;
   if(a[ulong(ar+i)*5+4]-ar!=b[ulong(br+i)*5+4]-br)return false;}return true;
}
kernel void recruitment_choice_action_invariants(device const long* before[[buffer(0)]],device const long* blengths[[buffer(1)]],
 device const long* bsections[[buffer(2)]],device const long* after[[buffer(3)]],device const long* alengths[[buffer(4)]],
 device const long* asections[[buffer(5)]],device const bool* selected[[buffer(6)]],device long* errors[[buffer(7)]],
 device const long* dims[[buffer(8)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;device long* out=errors+ulong(lane)*2;out[0]=out[1]=0;if(!selected[lane])return;
 device const long* old=before+ulong(lane)*dims[1]*5;device const long* now=after+ulong(lane)*dims[2]*5;
 if(!rqa_same(old,blengths[lane],dims[1],bsections[ulong(lane)*27+9],now,alengths[lane],dims[2],asections[ulong(lane)*27+9])||
    !rqa_same(old,blengths[lane],dims[1],bsections[ulong(lane)*27+20],now,alengths[lane],dims[2],asections[ulong(lane)*27+20]))out[0]=1;
 if(!rqa_same(old,blengths[lane],dims[1],bsections[ulong(lane)*27+1],now,alengths[lane],dims[2],asections[ulong(lane)*27+1]))out[1]=1;
}
inline void rqa_row(device long* out,long at,long tag,long meta,long end){out+=ulong(at)*5;out[0]=tag;out[1]=meta;out[2]=out[3]=0;out[4]=end;}
kernel void recruitment_choice_action_payload(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* roots[[buffer(2)]],device const bool* selected[[buffer(3)]],device const long* labels[[buffer(4)]],
 device const uchar* prefix[[buffer(5)]],device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],
 device const long* soffsets[[buffer(8)]],device const long* usage[[buffer(9)]],device long* output[[buffer(10)]],
 device long* actual[[buffer(11)]],device long* required[[buffer(12)]],device long* errors[[buffer(13)]],device const long* dims[[buffer(14)]],
 uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],R=dims[6];if(long(lane)>=B)return;actual[lane]=required[lane]=errors[lane]=0;if(!selected[lane])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix,poffsets,dims[2],dims[3],suffix,soffsets,dims[4],dims[5],usage,valid);
 const long action=roots[lane];rqa_container(v,action,10,6,valid);const long params=state_child(v,action,5,valid),end=state_end(v,params,valid);
 const long count=end-params;if(!valid||count>LONG_MAX-12){errors[lane]=1;return;}required[lane]=12+count;
 if(required[lane]>R){errors[lane]=2;return;}device long* out=output+ulong(lane)*R*5;
 rqa_row(out,0,13,6,required[lane]);rqa_row(out,1,5,labels[0],2);bool present=false;
 const long decision=state_optional(v,state_child(v,action,4,valid),present,valid);
 rqa_row(out,2,present?5:0,present?state_string_id(v,decision,valid):0,3);
 rqa_row(out,3,5,labels[1],4);rqa_row(out,4,5,state_string_id(v,state_child(v,action,0,valid),valid),5);
 rqa_row(out,5,5,labels[2],6);rqa_row(out,6,5,state_string_id(v,state_child(v,action,1,valid),valid),7);
 rqa_row(out,7,5,labels[3],8);rqa_row(out,8,5,state_string_id(v,state_child(v,action,3,valid),valid),9);
 rqa_row(out,9,5,labels[4],10);
 for(long i=0;i<count;++i){for(long c=0;c<4;++c)out[ulong(10+i)*5+c]=state_record(v,params+i)[c];out[ulong(10+i)*5+4]=state_record(v,params+i)[4]-params+10;}
 rqa_row(out,10+count,5,labels[5],11+count);rqa_row(out,11+count,5,state_string_id(v,state_child(v,action,2,valid),valid),12+count);
 if(!valid){errors[lane]=1;return;}actual[lane]=required[lane];
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
        raise ValueError("Recruitment choice action inputs must remain resident contiguous tensors")
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    out=torch.zeros(shape,dtype=value.dtype,device=value.device);out[tuple(slice(0,n) for n in value.shape)]=value;return out


class ResidentRecruitmentChoiceAction:
    def __init__(self,state_context,choice_effects,income_context,state_json,output_validation,*,reuse_certified_source=False):
        if type(reuse_certified_source) is not bool:raise TypeError("Certified source reuse must be an explicit bool")
        if _device(state_context.device).type!="mps":raise ValueError("Recruitment choice action requires explicit exact Apple GPU execution")
        if not {POLITICS_RULES_COMPONENT,ECONOMY_RULES_COMPONENT}.issubset(set(state_context.rules_id.split("+"))):
            raise ValueError("Recruitment choice action requires corrected politics/economy income-refresh rules")
        if any(service.state_context is not state_context for service in (choice_effects,income_context,state_json,output_validation)):
            raise ValueError("Recruitment choice action services must share the exact resident source context")
        self.state_context=state_context;self.effects=choice_effects;self.income=income_context;self.state_json=state_json;self.validation=output_validation
        self.reuse_certified_source=reuse_certified_source
        self.training_reset=ResidentTrainingReset(state_context) if state_context.rules_id.startswith("campaign-orders-v1+") else None
        self.event_labels=EventLabels(state_context,torch.tensor(state_context.prefix_lookup_ids(("action","interrupt","chance")),dtype=torch.int64,device=state_context.device))
        self.action_labels=torch.tensor(state_context.prefix_lookup_ids(("decision","id","kind","nation","parameters","player")),dtype=torch.int64,device=state_context.device)

    def capacities(self,before,menu,*,payload_capacity=64,json_byte_capacity,**refresh_arguments):
        """One warm conservative reservation, shared by every rule/outer stage."""
        choice=self.effects.reserve(before,menu,**refresh_arguments);base=choice.political_refresh
        extra=4*len(self.income.ledger_context.nation_ids)+6+payload_capacity+3
        common=replace(base,state_capacity=base.state_capacity+extra,block_capacity=max(base.block_capacity,base.state_capacity+extra),
            string_capacity=base.string_capacity+before.lane_count,byte_capacity=base.byte_capacity+64*before.lane_count)
        return RecruitmentChoiceActionCapacities(replace(choice,political_refresh=common),payload_capacity,json_byte_capacity)

    def reserve(self,state,capacities):
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Choice action source belongs to another context")
        if not isinstance(capacities,RecruitmentChoiceActionCapacities):raise TypeError("Choice action needs explicit fixed capacities")
        state._metadata();capacities.validate(state);B=state.lane_count
        return DeviceStateBatch(state.context,_pad(state.records,(B,capacities.state_capacity,5)),state.lengths,state.sections,
            _pad(state.string_bytes,(capacities.byte_capacity,)),_pad(state.string_offsets,(capacities.string_capacity+1,)),state.errors,state.suffix_usage)

    def apply(self,before,expected,current_choices,option_indices,selected=None,*,capacities):
        if not isinstance(before,DeviceStateBatch) or before.context is not self.state_context:raise ValueError("Choice action source belongs to another context")
        before._metadata();_device(before.device)
        if not isinstance(expected,StateIdentityBatch) or expected.source is not before:raise ValueError("Choice action expected identity belongs to a stale or foreign source")
        if not isinstance(current_choices,RecruitmentMenu) or current_choices.source is not before:
            raise ValueError("Choice action needs the cached current choices for this exact immutable source")
        if not isinstance(capacities,RecruitmentChoiceActionCapacities):raise TypeError("Choice action needs explicit fixed capacities")
        capacities.validate(before,current_choices);B,C=before.records.shape[:2];dev=before.device
        _tensor(option_indices,before,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,before,torch.bool,(B,))
        for keys in (expected.state_keys,expected.engine_keys):
            for value,dtype,shape in ((keys.hex_bytes,torch.uint8,(B,64)),(keys.errors,torch.int32,(B,)),(keys.batch_error,torch.int32,(1,)),(keys.count,torch.int64,(1,))):
                _tensor(value,before,dtype,shape)
        errors=torch.zeros(B,dtype=torch.int64,device=dev);stage_errors,required,attempted={},{},{}
        def stage(name,code,details,mask,committed=None):
            nonlocal errors
            details=details.to(torch.int64);stage_errors[name]=torch.where(mask,details,0);attempted[name]=mask
            failure=mask&(details!=0)
            if committed is not None:failure|=mask&~committed
            errors|=failure.to(torch.int64)*int(code)
            return selected&~(errors!=0).any()
        def dims(source,extra=()):return _dimensions((B,source.records.shape[1],source.context.string_count,source.context.string_bytes.numel(),
            source.string_offsets.numel()-1,source.string_bytes.numel(),*extra))
        def pool(source):return (source.context.string_bytes,source.context.string_offsets,source.string_bytes,source.string_offsets,source.suffix_usage)
        roots=torch.full((B,),-1,dtype=torch.int64,device=dev);preflight=torch.zeros_like(errors)
        _call(_kernels().recruitment_choice_action_preflight,(before.records,before.lengths,before.errors,option_indices,selected,*pool(before),roots,preflight,dims(before)),B)
        from .resident_identity_certificates import source_identity_check
        checked=source_identity_check(self.state_json,before,expected,byte_capacity=capacities.json_byte_capacity,reuse=self.reuse_certified_source)
        bad=(checked.engine_keys.errors!=0)|(checked.engine_keys.batch_error!=0).any()|(checked.engine_keys.count!=B).any()
        bad|=(expected.engine_keys.errors!=0)|(expected.engine_keys.batch_error!=0).any()|(expected.engine_keys.count!=B).any()
        mismatch=(checked.engine_keys.hex_bytes!=expected.engine_keys.hex_bytes).any(1)
        required["before_json_bytes"]=checked.state_json.required_bytes
        active=stage("preflight",RecruitmentChoiceActionError.PREFLIGHT,preflight|bad.to(torch.int64)*8|mismatch.to(torch.int64)*4,selected)
        effect_mask=active;effect=self.effects.apply(before,current_choices,option_indices,effect_mask,capacities=capacities.choice)
        required.update(effects_state=effect.required_state_capacity,effects_block=effect.required_block_capacity,effects_strings=effect.required_string_usage,effects_stages=effect.required)
        unsupported=effect_mask&(effect.unsupported_entry|~effect.handled)
        active=stage("effects",RecruitmentChoiceActionError.EFFECTS,effect.errors,effect_mask,effect.committed)
        # Capability diagnostics remain meaningful even when the pure dispatch
        # already reported its public-roll capability code and stopped writes.
        active=stage("capability",RecruitmentChoiceActionError.CAPABILITY,unsupported.to(torch.int64),effect_mask)
        active=stage("selected_action",RecruitmentChoiceActionError.PREFLIGHT,
            ((effect.selected_option_roots!=roots)&effect.handled).to(torch.int64),active)
        income=self.income.refresh(effect.state,active,capacity=capacities.state_capacity);required["income_state"]=income.required_capacity
        active=stage("income",RecruitmentChoiceActionError.INCOME,income.errors,active);current=income.state
        if self.training_reset is not None:
            reset=self.training_reset.reset(current,active,capacity=capacities.state_capacity);required["reset_state"]=reset.required_capacity
            active=stage("reset",RecruitmentChoiceActionError.RESET,reset.errors,active,reset.committed);current=reset.state
            forward=forward_training_decision(current,active,capacities)
            required.update(forward_state=forward.required_state_capacity,forward_block=forward.required_block_capacity)
            unsupported|=forward.unsupported
            active=stage("forward_capability",RecruitmentChoiceActionError.FORWARD_CAPABILITY,
                forward.unsupported.to(torch.int64)*int(RecruitmentForwardError.UNSUPPORTED_NAVAL_FORCE),active)
            active=stage("forward",RecruitmentChoiceActionError.FORWARD,forward.errors,active,forward.committed);current=forward.state
        else:
            required.update(reset_state=current.lengths,forward_state=current.lengths,forward_block=torch.zeros_like(errors))
            for name,code in (("reset",RecruitmentChoiceActionError.RESET),("forward_capability",RecruitmentChoiceActionError.FORWARD_CAPABILITY),("forward",RecruitmentChoiceActionError.FORWARD)):
                active=stage(name,code,torch.zeros_like(errors),active)
        invariants=torch.zeros((B,2),dtype=torch.int64,device=dev)
        _call(_kernels().recruitment_choice_action_invariants,(before.records,before.lengths,before.sections,current.records,current.lengths,current.sections,
            active,invariants,_dimensions((B,C,current.records.shape[1]))),B)
        active=stage("clock",RecruitmentChoiceActionError.CLOCK,invariants[:,0],active)
        active=stage("random",RecruitmentChoiceActionError.RANDOM,invariants[:,1],active)
        validation=self.validation.validate(before,current,active,training_reset_applied=self.training_reset is not None)
        unsupported|=validation.unsupported!=0
        active=stage("validation_capability",RecruitmentChoiceActionError.VALIDATION_CAPABILITY,validation.unsupported.to(torch.int64),active)
        active=stage("validation",RecruitmentChoiceActionError.VALIDATION,validation.errors,active)
        identities=self.state_json.identities(current,byte_capacity=capacities.json_byte_capacity);required["after_json_bytes"]=identities.state_json.required_bytes
        active=stage("identity",RecruitmentChoiceActionError.IDENTITY,identities.engine_keys.errors.to(torch.int64)|identities.engine_keys.batch_error.to(torch.int64),active)
        R=capacities.payload_capacity;payload_records=torch.zeros((B,R,5),dtype=torch.int64,device=dev)
        payload_lengths,payload_required,payload_errors=(torch.zeros(B,dtype=torch.int64,device=dev) for _ in range(3))
        _call(_kernels().recruitment_choice_action_payload,(before.records,before.lengths,roots,active,self.action_labels,*pool(before),
            payload_records,payload_lengths,payload_required,payload_errors,dims(before,(R,))),B)
        required["payload"]=payload_required;active=stage("payload",RecruitmentChoiceActionError.PAYLOAD,payload_errors,active)
        payload=EventPayloads(current,payload_records,payload_lengths,payload_errors)
        event=append_events(current,identities,payload,torch.full((B,),EventKind.ACTION,dtype=torch.int64,device=dev),self.event_labels,selected=active,
            state_capacity=capacities.state_capacity,block_capacity=capacities.block_capacity,string_capacity=capacities.string_capacity,byte_capacity=capacities.byte_capacity)
        required.update(event_state=event.required_state_capacity,event_block=event.required_block_capacity,event_strings=event.required_string_usage)
        active=stage("event",RecruitmentChoiceActionError.EVENT,event.errors,active,event.committed)
        committed=~(errors!=0).any();baseline=self.reserve(before,capacities);candidate=event.state
        output=DeviceStateBatch(before.context,torch.where(committed,candidate.records,baseline.records),torch.where(committed,candidate.lengths,before.lengths),
            torch.where(committed,candidate.sections,before.sections),torch.where(committed,candidate.string_bytes,baseline.string_bytes),
            torch.where(committed,candidate.string_offsets,baseline.string_offsets),before.errors,torch.where(committed,candidate.suffix_usage,before.suffix_usage))
        identities=_invalid_identities(event.identities,output,selected&~committed)
        return RecruitmentChoiceActionResult(before,output,identities,errors,stage_errors,required,attempted,effect.handled,unsupported,selected&committed,committed)
