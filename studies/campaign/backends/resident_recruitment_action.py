"""One complete recruitment-roll Engine action transaction on resident state.

This handler consumes a cached, source-bound recruitment Action6. It does not
run the CampaignAdapter interrupt scheduler or implement recruitment placement.
Input must be a validated canonical state: quiet-placement preflight and the
checked changed footprint preserve State.validate's invariants from that input.
All selected lanes, event data and namespace additions commit together. No
random value is read on the host or consumed by this action.
"""
from dataclasses import dataclass,fields,replace
from enum import IntFlag
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .metal_state_schema import METAL_STATE_SOURCE
from .resident_events import EventKind,EventLabels,EventPayloads,append_events
from .resident_state_json import StateIdentityBatch
from .resident_training_reset import ResidentTrainingReset
from .resident_recruitment_chance import POLITICS_RULES_COMPONENT,ECONOMY_RULES_COMPONENT
from .resident_recruitment import RecruitmentMenu


class RecruitmentActionError(IntFlag):
    PREFLIGHT=1
    EFFECTS=2
    INCOME=4
    RESET=8
    CLOCK=16
    STATE=32
    RANDOM=64
    IDENTITY=128
    PAYLOAD=256
    EVENT=512


@dataclass(frozen=True)
class RecruitmentActionCapacities:
    state_capacity:int
    block_capacity:int
    string_capacity:int
    byte_capacity:int
    payload_capacity:int
    json_byte_capacity:int

    def validate(self,state,menu=None):
        if any(type(getattr(self,f.name)) is not int or getattr(self,f.name)<0 for f in fields(self)):
            raise ValueError("Recruitment action capacities must be explicit nonnegative integer allocations")
        source=state if menu is None else menu.arena
        if (self.state_capacity<state.records.shape[1] or self.block_capacity<1 or
            self.string_capacity<source.string_offsets.numel()-1 or self.byte_capacity<source.string_bytes.numel()):
            raise ValueError("Recruitment action capacities must preserve the original and cached-menu rollback arenas")
        if state.lane_count>2**32-1 or state.lane_count*max(self.state_capacity,self.block_capacity,self.payload_capacity,1)*5>2**63-1:
            raise OverflowError("Recruitment action arenas cannot be represented; no lanes truncated")


@dataclass(frozen=True)
class RecruitmentActionResult:
    source:DeviceStateBatch
    state:DeviceStateBatch
    identities:StateIdentityBatch
    errors:torch.Tensor
    stage_errors:dict
    required:dict
    attempted:dict
    handled:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE="#include <metal_stdlib>\nusing namespace metal;\n"+METAL_STATE_SOURCE+r'''
inline bool ra_container(thread const PackedStateView& v,long node,long tag,long count,thread bool& valid){
 const long end=state_end(v,node,valid);if(!valid)return false;device const long* row=state_record(v,node);
 const long maximum=(tag==7||tag==13)?(end-node-1)/2:end-node-1;
 if(row[0]!=tag||row[1]<0||row[1]>maximum||(count>=0&&row[1]!=count)||row[2]||row[3])valid=false;return valid;
}
kernel void recruitment_action_capability(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const uchar* prefix[[buffer(3)]],device const long* poffsets[[buffer(4)]],device const uchar* suffix[[buffer(5)]],
 device const long* soffsets[[buffer(6)]],device const long* usage[[buffer(7)]],device const bool* selected[[buffer(8)]],
 device long* errors[[buffer(9)]],device const long* dims[[buffer(10)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;errors[lane]=0;if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
   prefix,poffsets,dims[2],dims[3],suffix,soffsets,dims[4],dims[5],usage,valid);
 if(inherited[lane])valid=false;ra_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);ra_container(v,state,10,19,valid);
 const bool terminal=state_boolean_value(v,state_child(v,state,18,valid),valid);
 const long clock=state_child(v,state,7,valid);ra_container(v,clock,10,6,valid);
 const long phase=state_signed_value(v,state_child(v,clock,2,valid),valid);
 const bool collected=state_boolean_value(v,state_child(v,clock,5,valid),valid);
 bool chance=false;(void)state_optional(v,state_child(v,state,14,valid),chance,valid);
 const long decisions=state_child(v,state,11,valid),battles=state_child(v,state,12,valid),order=state_child(v,state,13,valid);
 ra_container(v,decisions,6,-1,valid);ra_container(v,battles,7,-1,valid);ra_container(v,order,6,-1,valid);
 if(!valid){errors[lane]=1;return;}
 if(terminal||phase!=4||collected||chance||state_record(v,decisions)[1]||state_record(v,battles)[1]||state_record(v,order)[1]){
   errors[lane]=2;return;}
 // Engine::actionMenu independently suppresses ordinary actions for this flag.
 const long flags=state_child(v,state,15,valid),immediate=state_map_find_literal(v,flags,"immediate_land_battles",22,valid);
 if(immediate>=0&&state_signed_value(v,immediate,valid))errors[lane]=4;
 if(!valid)errors[lane]|=1;
}
inline bool ra_same(device const long* a,long alength,long acapacity,long at,
                    device const long* b,long blength,long bcapacity,long bt){
 if(at<0||bt<0||at>=alength||bt>=blength||at>=acapacity||bt>=bcapacity)return false;
 const long end=a[ulong(at)*5+4],other=b[ulong(bt)*5+4],count=end-at;
 if(count<=0||end>alength||end>acapacity||other-bt!=count||other>blength||other>bcapacity)return false;
 for(long i=0;i<count;++i){for(long col=0;col<4;++col)if(a[ulong(at+i)*5+col]!=b[ulong(bt+i)*5+col])return false;
   if(a[ulong(at+i)*5+4]-at!=b[ulong(bt+i)*5+4]-bt)return false;}return true;
}
kernel void recruitment_action_postflight(
 device const long* before[[buffer(0)]],device const long* blengths[[buffer(1)]],device const long* bsections[[buffer(2)]],
 device const long* after[[buffer(3)]],device const long* alengths[[buffer(4)]],device const long* asections[[buffer(5)]],
 device const uchar* prefix[[buffer(6)]],device const long* poffsets[[buffer(7)]],device const uchar* suffix[[buffer(8)]],
 device const long* soffsets[[buffer(9)]],device const long* usage[[buffer(10)]],device const bool* selected[[buffer(11)]],
 device long* output[[buffer(12)]],device const long* dims[[buffer(13)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],A=dims[2];if(long(lane)>=B)return;device long* errors=output+ulong(lane)*3;
 errors[0]=errors[1]=errors[2]=0;if(!selected[lane])return;
 device const long* old=before+ulong(lane)*C*5;device const long* now=after+ulong(lane)*A*5;
 if(!ra_same(old,blengths[lane],C,bsections[ulong(lane)*27+9],now,alengths[lane],A,asections[ulong(lane)*27+9])||
    !ra_same(old,blengths[lane],C,bsections[ulong(lane)*27+20],now,alengths[lane],A,asections[ulong(lane)*27+20]))errors[0]=1;
 if(!ra_same(old,blengths[lane],C,bsections[ulong(lane)*27+1],now,alengths[lane],A,asections[ulong(lane)*27+1]))errors[1]=1;
 bool valid=true;PackedStateView v=make_packed_state_view(now,alengths[lane],A,prefix,poffsets,dims[3],dims[4],
   suffix,soffsets,dims[5],dims[6],usage,valid);
 ra_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);ra_container(v,state,10,19,valid);
 ra_container(v,state_child(v,state,11,valid),6,0,valid);ra_container(v,state_child(v,state,12,valid),7,0,valid);
 ra_container(v,state_child(v,state,13,valid),6,0,valid);
 bool exists=false;const long chance=state_optional(v,state_child(v,state,14,valid),exists,valid);
 if(!valid||!exists){errors[2]=1;return;}ra_container(v,chance,10,5,valid);
 const long id=state_string_id(v,state_child(v,chance,0,valid),valid);
 const long minor=state_string_id(v,state_child(v,chance,2,valid),valid),continuation=state_string_id(v,state_child(v,chance,3,valid),valid);
 if(!state_string_equals(v,state_child(v,chance,1,valid),"recruitment_roll",16,valid)||id!=continuation||
    state_string_id_equals(v,id,"",0,valid))valid=false;
 const long dice=state_child(v,chance,4,valid);ra_container(v,dice,6,1,valid);
 const long die=state_child(v,dice,0,valid);ra_container(v,die,10,4,valid);
 if(state_signed_value(v,state_child(v,die,0,valid),valid)!=12||state_signed_value(v,state_child(v,die,1,valid),valid)!=0||
    state_signed_value(v,state_child(v,die,3,valid),valid)!=0)valid=false;
 ra_container(v,state_child(v,die,2,valid),8,0,valid);
 const long nation=state_map_find_id(v,state_child(v,state,0,valid),minor,valid);
 if(!valid||nation<0){errors[2]=1;return;}ra_container(v,nation,10,12,valid);
 const long attempted=state_map_find_literal(v,state_child(v,nation,10,valid),"recruitment_attempted",21,valid);
 if(attempted<0||state_signed_value(v,attempted,valid)!=1)valid=false;
 const long politics=state_child(v,state,8,valid),pending=state_map_find_id(v,state_child(v,politics,10,valid),continuation,valid);
 if(!valid||pending<0){errors[2]=1;return;}ra_container(v,pending,13,2,valid);
 const long beneficiary=state_map_find_literal(v,pending,"beneficiary",11,valid),threshold=state_map_find_literal(v,pending,"threshold",9,valid);
 if(beneficiary<0||state_string_id(v,beneficiary,valid)!=minor||threshold<0){errors[2]=1;return;}
 long amount=0;const ulong bits=state_raw_bits(v,threshold,4,valid);
 if(!state_json_integer_value(bits,amount)||amount<=0)valid=false;
 if(!valid)errors[2]=1;
}
inline void ra_row(device long* rows,long at,long tag,long value,long end){
 device long* r=rows+ulong(at)*5;r[0]=tag;r[1]=value;r[2]=r[3]=0;r[4]=end;
}
kernel void recruitment_action_payload(
 device const long* actions[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* selections[[buffer(2)]],
 device const long* labels[[buffer(3)]],device const bool* selected[[buffer(4)]],device long* output[[buffer(5)]],
 device long* actual[[buffer(6)]],device long* errors[[buffer(7)]],device long* required[[buffer(8)]],
 device const long* dims[[buffer(9)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],P=dims[1],R=dims[2];if(long(lane)>=B)return;
 actual[lane]=errors[lane]=required[lane]=0;if(!selected[lane])return;required[lane]=15;
 const long chosen=selections[lane];if(chosen<0||chosen>=P||lengths[chosen]!=9){errors[lane]=1;return;}
 if(R<15){errors[lane]=2;return;}device const long* a=actions+ulong(chosen)*65;
 device long* out=output+ulong(lane)*R*5;
 // Native canonical ActionJSON lexical key order, retaining every Action6 field.
 ra_row(out,0,13,6,15);ra_row(out,1,5,labels[0],2);ra_row(out,2,0,0,3);
 ra_row(out,3,5,labels[1],4);ra_row(out,4,5,a[6],5);ra_row(out,5,5,labels[2],6);ra_row(out,6,5,a[11],7);
 ra_row(out,7,5,labels[3],8);ra_row(out,8,5,a[21],9);ra_row(out,9,5,labels[4],10);
 ra_row(out,10,13,1,13);ra_row(out,11,5,a[36],12);ra_row(out,12,5,a[41],13);
 ra_row(out,13,5,labels[5],14);ra_row(out,14,5,a[16],15);actual[lane]=15;
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
        raise ValueError("Recruitment action requires complete contiguous resident buffers")
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    out=torch.zeros(shape,dtype=value.dtype,device=value.device);out[tuple(slice(0,n) for n in value.shape)]=value;return out
def _failed_identities(identities,state,invalid):
    invalid=invalid.to(torch.int32)*(1<<29)
    return replace(identities,source=state,
        state_json=replace(identities.state_json,errors=identities.state_json.errors|invalid),
        state_keys=replace(identities.state_keys,errors=identities.state_keys.errors|invalid),
        engine_json=replace(identities.engine_json,errors=identities.engine_json.errors|invalid),
        engine_keys=replace(identities.engine_keys,errors=identities.engine_keys.errors|invalid))


class ResidentRecruitmentAction:
    def __init__(self,state_context,start_effects,income_context,state_json,*,reuse_certified_source=False):
        if type(reuse_certified_source) is not bool:raise TypeError("Certified source reuse must be an explicit bool")
        self.reuse_certified_source=reuse_certified_source
        if _device(state_context.device).type!="mps":raise ValueError("Recruitment action requires explicit Apple GPU execution; no fallback")
        if not {POLITICS_RULES_COMPONENT,ECONOMY_RULES_COMPONENT}.issubset(set(state_context.rules_id.split("+"))):
            raise ValueError("Recruitment action requires the corrected politics/economy income-refresh rules contract")
        if any(service.state_context is not state_context for service in (start_effects,income_context,state_json)):
            raise ValueError("Recruitment action services must share one exact resident source context")
        self.state_context=state_context;self.effects=start_effects;self.income=income_context;self.state_json=state_json
        self.training_reset=ResidentTrainingReset(state_context) if state_context.rules_id.startswith("campaign-orders-v1+") else None
        self.event_labels=EventLabels(state_context,torch.tensor(state_context.prefix_lookup_ids(("action","interrupt","chance")),dtype=torch.int64,device=state_context.device))
        self.action_labels=torch.tensor(state_context.prefix_lookup_ids(("decision","id","kind","nation","parameters","player")),dtype=torch.int64,device=state_context.device)

    def _context(self,state):
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Recruitment action state belongs to another context")
        state._metadata();_device(state.device)
        if any(not value.is_contiguous() for value in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets)):
            raise ValueError("Recruitment action source buffers must stay contiguous")

    def reserve(self,state,capacities):
        """Reserve once before building a cached menu/key; this returns a new source."""
        self._context(state)
        if not isinstance(capacities,RecruitmentActionCapacities):raise TypeError("Recruitment action needs explicit fixed capacities")
        capacities.validate(state);B=state.lane_count
        return DeviceStateBatch(state.context,_pad(state.records,(B,capacities.state_capacity,5)),state.lengths,state.sections,
            _pad(state.string_bytes,(capacities.byte_capacity,)),_pad(state.string_offsets,(capacities.string_capacity+1,)),state.errors,state.suffix_usage)

    def apply(self,before,expected,legal_roll_menu,selections,*,capacities,selected=None):
        """Apply one listed recruitment-roll action per selected Engine lane.

        This is an atomic Engine action handler, with no CampaignAdapter scheduler
        update. Required sizes are resident per-stage values; later stages after
        an error describe retained intermediates, not a fabricated success.
        """
        self._context(before)
        if not isinstance(expected,StateIdentityBatch) or expected.source is not before:raise ValueError("Recruitment expected key belongs to a stale or foreign source")
        if not isinstance(capacities,RecruitmentActionCapacities):raise TypeError("Recruitment action needs explicit fixed capacities")
        # The effect's source binding also checks the complete cached Action6.
        if not isinstance(legal_roll_menu,RecruitmentMenu) or legal_roll_menu.source is not before:
            raise ValueError("Recruitment cached menu belongs to a stale or foreign source")
        capacities.validate(before,legal_roll_menu);B,C=before.records.shape[:2];dev=before.device
        _tensor(selections,before,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,before,torch.bool,(B,))
        for keys in (expected.state_keys,expected.engine_keys):
            for value,dtype,shape in ((keys.hex_bytes,torch.uint8,(B,64)),(keys.errors,torch.int32,(B,)),(keys.batch_error,torch.int32,(1,)),(keys.count,torch.int64,(1,))):
                _tensor(value,before,dtype,shape)
        errors=torch.zeros(B,dtype=torch.int64,device=dev);stage_errors={};required={};attempted={}
        def stage(name,code,details,active,committed=None):
            nonlocal errors
            details=details.to(torch.int64);stage_errors[name]=torch.where(active,details,0);attempted[name]=active
            failed=active&(details!=0)
            if committed is not None:failed|=active&~committed
            errors|=failed.to(torch.int64)*int(code)
            return selected&~(errors!=0).any()
        capability=torch.zeros(B,dtype=torch.int64,device=dev)
        _call(_kernels().recruitment_action_capability,(before.records,before.lengths,before.errors,before.context.string_bytes,
            before.context.string_offsets,before.string_bytes,before.string_offsets,before.suffix_usage,selected,capability,
            _dimensions((B,C,before.context.string_count,before.context.string_bytes.numel(),before.string_offsets.numel()-1,before.string_bytes.numel()))),B)
        from .resident_identity_certificates import source_identity_check
        checked=source_identity_check(self.state_json,before,expected,byte_capacity=capacities.json_byte_capacity,
                                      reuse=self.reuse_certified_source)
        bad=(checked.engine_keys.errors!=0)|(checked.engine_keys.batch_error!=0).any()|(checked.engine_keys.count!=B).any()
        bad|=(expected.engine_keys.errors!=0)|(expected.engine_keys.batch_error!=0).any()|(expected.engine_keys.count!=B).any()
        mismatch=(checked.engine_keys.hex_bytes!=expected.engine_keys.hex_bytes).any(1)
        required["before_json_bytes"]=checked.state_json.required_bytes
        active=stage("preflight",RecruitmentActionError.PREFLIGHT,capability|bad.to(torch.int64)*8|mismatch.to(torch.int64)*4,selected)
        effect=self.effects.apply(before,legal_roll_menu,selections,active,state_capacity=capacities.state_capacity,block_capacity=capacities.block_capacity,
            string_capacity=capacities.string_capacity,byte_capacity=capacities.byte_capacity)
        required.update(effects_state=effect.required_state_capacity,effects_block=effect.required_block_capacity,effects_strings=effect.required_string_usage)
        active=stage("effects",RecruitmentActionError.EFFECTS,effect.errors,active,effect.committed)
        income=self.income.refresh(effect.state,active,capacity=capacities.state_capacity);required["income_state"]=income.required_capacity
        active=stage("income",RecruitmentActionError.INCOME,income.errors,active);current=income.state
        if self.training_reset is not None:
            reset=self.training_reset.reset(current,active,capacity=capacities.state_capacity);required["reset_state"]=reset.required_capacity
            active=stage("reset",RecruitmentActionError.RESET,reset.errors,active,reset.committed);current=reset.state
        else:
            required["reset_state"]=current.lengths;active=stage("reset",RecruitmentActionError.RESET,torch.zeros_like(errors),active)
        post=torch.zeros((B,3),dtype=torch.int64,device=dev)
        _call(_kernels().recruitment_action_postflight,(before.records,before.lengths,before.sections,current.records,current.lengths,current.sections,
            current.context.string_bytes,current.context.string_offsets,current.string_bytes,current.string_offsets,current.suffix_usage,active,post,
            _dimensions((B,C,current.records.shape[1],current.context.string_count,current.context.string_bytes.numel(),current.string_offsets.numel()-1,current.string_bytes.numel()))),B)
        active=stage("clock",RecruitmentActionError.CLOCK,post[:,0],active)
        active=stage("random",RecruitmentActionError.RANDOM,post[:,1],active)
        active=stage("state",RecruitmentActionError.STATE,post[:,2],active)
        identities=self.state_json.identities(current,byte_capacity=capacities.json_byte_capacity);required["after_json_bytes"]=identities.state_json.required_bytes
        active=stage("identity",RecruitmentActionError.IDENTITY,identities.engine_keys.errors.to(torch.int64)|identities.engine_keys.batch_error.to(torch.int64),active)
        P=legal_roll_menu.actions.shape[0];R=capacities.payload_capacity
        payload_records=torch.zeros((B,R,5),dtype=torch.int64,device=dev)
        payload_lengths=torch.zeros(B,dtype=torch.int64,device=dev);payload_errors=torch.zeros_like(payload_lengths);payload_required=torch.zeros_like(payload_lengths)
        _call(_kernels().recruitment_action_payload,(legal_roll_menu.actions,legal_roll_menu.lengths,selections,self.action_labels,active,
            payload_records,payload_lengths,payload_errors,payload_required,_dimensions((B,P,R))),B)
        required["payload"]=payload_required;active=stage("payload",RecruitmentActionError.PAYLOAD,payload_errors,active)
        payloads=EventPayloads(current,payload_records,payload_lengths,payload_errors)
        event=append_events(current,identities,payloads,torch.full((B,),EventKind.ACTION,dtype=torch.int64,device=dev),self.event_labels,
            selected=active,state_capacity=capacities.state_capacity,block_capacity=capacities.block_capacity,string_capacity=capacities.string_capacity,byte_capacity=capacities.byte_capacity)
        required.update(event_state=event.required_state_capacity,event_block=event.required_block_capacity,event_strings=event.required_string_usage)
        active=stage("event",RecruitmentActionError.EVENT,event.errors,active,event.committed)
        committed=~(errors!=0).any();baseline=self.reserve(before,capacities);candidate=event.state
        output=DeviceStateBatch(before.context,torch.where(committed,candidate.records,baseline.records),torch.where(committed,candidate.lengths,before.lengths),
            torch.where(committed,candidate.sections,before.sections),torch.where(committed,candidate.string_bytes,baseline.string_bytes),
            torch.where(committed,candidate.string_offsets,baseline.string_offsets),torch.where(committed,candidate.errors,before.errors),
            torch.where(committed,candidate.suffix_usage,before.suffix_usage))
        after_identity=identities
        identities=_failed_identities(event.identities,output,selected&~committed)
        if self.reuse_certified_source:
            from .resident_identity_certificates import _certify_recruitment_action_publication
            _certify_recruitment_action_publication(self.state_json,identities,before=before,before_expected=expected,
                before_check=checked,after_identity=after_identity,event=event,committed=committed,
                byte_capacity=capacities.json_byte_capacity)
        return RecruitmentActionResult(before,output,identities,errors,stage_errors,required,attempted,effect.handled,selected&committed,committed)
