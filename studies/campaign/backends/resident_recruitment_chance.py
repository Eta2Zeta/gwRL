"""Complete sampled recruitment-chance transaction on resident campaign state.

This is one named rule handler, not a general campaign backend. Each stage uses
explicit fixed arena capacities. All selected lanes and the shared suffix pool
publish together, or every original word and logical usage counter survives.
Callers retain the original state/identity until ``committed`` is true. Failed
selected identity rows are deliberately unusable; retry with that original pair.
Retained training naval screening is forwarded exactly. A retained naval force
selection needs the unported completion service and returns an explicit
unsupported-capability result; this never declares that native state illegal.
"""
from dataclasses import dataclass, fields, replace
from enum import IntFlag
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch, _device
from .resident_relations import SOURCE as RELATIONS_SOURCE
from .device_map_edits import build_sequence_splices, commit_container_edits
from .packed_chance_metal import sample_packed_chance
from .resident_chance_io import build_chance_payload, install_sampled_randomness
from .resident_events import EventKind, EventLabels, append_events
from .resident_state_json import StateIdentityBatch
from .resident_training_reset import ResidentTrainingReset


POLITICS_RULES_COMPONENT = "gw36_v43_m4_politics_income_refresh_v1"
ECONOMY_RULES_COMPONENT = "gw36_economy_v43"


class RecruitmentChanceError(IntFlag):
    PREFLIGHT = 1
    SAMPLE = 2
    EFFECTS = 4
    INCOME = 8
    RESET = 16
    CLOCK = 32
    IDENTITY = 64
    PAYLOAD = 128
    EVENT = 256
    RANDOM = 512
    FORWARD_CAPABILITY = 1024
    FORWARD = 2048
    VALIDATION = 4096


class RecruitmentForwardError(IntFlag):
    PACKED = 1
    NATIVE_HOOK = 2
    NO_COMPLETION = 4
    CAPACITY = 8
    UNSUPPORTED_NAVAL_FORCE = 16


class RecruitmentPostconditionError(IntFlag):
    PACKED = 1
    POLITICAL_CONTINUATION = 2
    DECISION_ID = 4
    ENTITLEMENT = 8
    OPTION_ID = 16
    CHANCE_NOT_CLEARED = 32
    CHANCE_STATE = 32


@dataclass(frozen=True)
class RecruitmentChanceCapacities:
    state_capacity: int
    block_capacity: int
    choice_capacity: int
    parameter_byte_capacity: int
    string_capacity: int
    byte_capacity: int
    payload_capacity: int
    json_byte_capacity: int
    dice_capacity: int
    roll_capacity: int

    def validate(self, source):
        if any(type(getattr(self, item.name)) is not int or getattr(self, item.name) < 0 for item in fields(self)):
            raise ValueError("Recruitment chance capacities must be explicit nonnegative integer allocations")
        if (self.state_capacity < source.records.shape[1] or self.block_capacity < 1 or
                self.string_capacity < source.string_offsets.numel()-1 or self.byte_capacity < source.string_bytes.numel()):
            raise ValueError("Recruitment chance capacities cannot shrink any original rollback arena")
        if source.lane_count*max(self.state_capacity,self.block_capacity,self.payload_capacity,1)*5 > (1 << 63)-1:
            raise OverflowError("Recruitment chance arenas cannot be represented")


@dataclass(frozen=True)
class RecruitmentChanceResult:
    source: DeviceStateBatch
    state: DeviceStateBatch
    sampled: object
    identities: StateIdentityBatch
    errors: torch.Tensor
    stage_errors: dict
    required: dict
    attempted: dict
    handled: torch.Tensor
    accepted: torch.Tensor
    committed: torch.Tensor


@dataclass(frozen=True)
class _ForwardResult:
    state: DeviceStateBatch
    errors: torch.Tensor
    unsupported: torch.Tensor
    required_state_capacity: torch.Tensor
    required_block_capacity: torch.Tensor
    committed: torch.Tensor


SOURCE = RELATIONS_SOURCE + r'''
inline bool rc_container(thread const PackedStateView& v,long root,long tag,long count,thread bool& valid){
 const long end=state_end(v,root,valid);if(!valid)return false;device const long* row=state_record(v,root);
 if(row[0]!=tag||row[1]!=count||row[2]||row[3]||count>end-root-1)valid=false;return valid;
}
kernel void recruitment_chance_capability(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* sections[[buffer(2)]],
 device const long* inherited[[buffer(3)]],device const uchar* prefix[[buffer(4)]],device const long* poffsets[[buffer(5)]],
 device const uchar* suffix[[buffer(6)]],device const long* soffsets[[buffer(7)]],device const long* usage[[buffer(8)]],
 device const bool* selected[[buffer(9)]],device long* errors[[buffer(10)]],device bool* handled[[buffer(11)]],
 device const long* dims[[buffer(12)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1];if(long(lane)>=B)return;errors[lane]=0;handled[lane]=false;if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*ulong(C)*5,lengths[lane],C,
   prefix,poffsets,dims[2],dims[3],suffix,soffsets,dims[4],dims[5],usage,valid);
 if(inherited[lane])valid=false;rc_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);
 rc_container(v,state,10,19,valid);device const long* roots=sections+ulong(lane)*27;
 if(!valid||roots[0]!=state){errors[lane]=1;return;}
 const bool terminal=state_boolean_value(v,state_child(v,state,18,valid),valid);
 bool present=false;const long chance=state_optional(v,state_child(v,state,14,valid),present,valid);
 if(!valid||terminal){errors[lane]=1;return;}if(!present){errors[lane]=2;return;}
 rc_container(v,chance,10,5,valid);
 const bool recruitment=state_string_equals(v,state_child(v,chance,1,valid),"recruitment_roll",16,valid);
 if(!valid){errors[lane]=1;return;}handled[lane]=recruitment;if(!recruitment)errors[lane]=2;
}
kernel void recruitment_chance_clock(
 device const long* before[[buffer(0)]],device const long* blengths[[buffer(1)]],device const long* bsections[[buffer(2)]],
 device const long* after[[buffer(3)]],device const long* alengths[[buffer(4)]],device const long* asections[[buffer(5)]],
 device const bool* selected[[buffer(6)]],device long* errors[[buffer(7)]],device const long* dims[[buffer(8)]],
 uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],A=dims[2];if(long(lane)>=B)return;errors[lane]=0;if(!selected[lane])return;
 const long b=bsections[ulong(lane)*27+9],a=asections[ulong(lane)*27+9];
 const long bt=bsections[ulong(lane)*27+20],at=asections[ulong(lane)*27+20];
 if(b<0||a<0||bt<0||at<0||b>=blengths[lane]||a>=alengths[lane]||bt>=blengths[lane]||at>=alengths[lane]){errors[lane]=1;return;}
 device const long* old=before+ulong(lane)*ulong(C)*5;device const long* now=after+ulong(lane)*ulong(A)*5;
 const long count=old[ulong(b)*5+4]-b;
 if(count<=0||b+count>blengths[lane]||now[ulong(a)*5+4]-a!=count||a+count>alengths[lane]){errors[lane]=1;return;}
 for(long i=0;i<count;++i){for(long k=0;k<4;++k)if(old[ulong(b+i)*5+k]!=now[ulong(a+i)*5+k])errors[lane]=1;
   if(old[ulong(b+i)*5+4]-b!=now[ulong(a+i)*5+4]-a)errors[lane]=1;}
 for(long k=0;k<4;++k)if(old[ulong(bt)*5+k]!=now[ulong(at)*5+k])errors[lane]=1;
 if(old[ulong(bt)*5+4]-bt!=now[ulong(at)*5+4]-at)errors[lane]=1;
}
'''

SOURCE += r'''
inline bool rc_nonempty(thread const PackedStateView& v,long id,thread bool& valid){
 long a,b;bool prefix;relations_span(v,id,a,b,prefix,valid);return valid&&a<b;
}
inline bool rc_prefix(thread const PackedStateView& v,long id,constant char* text,long size,thread bool& valid){
 long a,b;bool prefix;relations_span(v,id,a,b,prefix,valid);if(!valid||b-a<size)return false;
 device const uchar* bytes=prefix?v.prefix_bytes:v.suffix_bytes;
 for(long i=0;i<size;++i)if(bytes[a+i]!=uchar(text[i]))return false;return true;
}
inline bool rc_political(thread const PackedStateView& v,long kind,thread bool& valid){
 return rc_prefix(v,kind,"politics_",9,valid)||rc_prefix(v,kind,"warlord_",8,valid)||
   rc_prefix(v,kind,"truce_",6,valid)||rc_prefix(v,kind,"influence_",10,valid)||rc_prefix(v,kind,"recruitment_",12,valid);
}
inline bool rc_less_equal(thread const PackedStateView& v,long first,long second,thread bool& valid){
 long a,b,c,d;bool p,q;relations_span(v,first,a,b,p,valid);relations_span(v,second,c,d,q,valid);if(!valid)return false;
 device const uchar* x=p?v.prefix_bytes:v.suffix_bytes;device const uchar* y=q?v.prefix_bytes:v.suffix_bytes;
 for(long i=0;i<min(b-a,d-c);++i){if(x[a+i]!=y[c+i])return x[a+i]<y[c+i];}return b-a<=d-c;
}
inline long rc_player(thread const PackedStateView& v,thread const PackedStateView& d,long nations,long pending,
 long nation,thread bool& valid){
 const long maximum=state_record(v,nations)[1];
 for(long visit=0;valid&&visit<=maximum;++visit){
   const long root=state_map_find_id(v,nations,nation,valid);if(root<0){valid=false;return -1;}
   relations_container(v,root,10,12,valid);
   long player=relations_optional_id(v,root,1,valid);
   if(player>=0){if(!relations_set_has(d,state_child(d,0,7,valid),player,valid))valid=false;return player;}
   const long controller=relations_optional_id(v,root,0,valid);if(controller>=0){nation=controller;continue;}
   const long defense=relations_named_flag(v,pending,"warlord_defense_player:",23,nation,valid);
   if(defense>=0){player=state_string_id(v,defense,valid);
     if(!relations_set_has(d,state_child(d,0,7,valid),player,valid))valid=false;return player;}
   valid=false;return -1;
 }valid=false;return -1;
}
kernel void recruitment_screen_forward(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* sections[[buffer(2)]],
 device const long* inherited[[buffer(3)]],device const uchar* prefix[[buffer(4)]],device const long* poffsets[[buffer(5)]],
 device const uchar* suffix[[buffer(6)]],device const long* soffsets[[buffer(7)]],device const long* usage[[buffer(8)]],
 device const bool* selected[[buffer(9)]],device long* blocks[[buffer(10)]],device long* actual[[buffer(11)]],
 device long* counts[[buffer(12)]],device long* roots[[buffer(13)]],device long* errors[[buffer(14)]],
 device bool* unsupported[[buffer(15)]],device long* required[[buffer(16)]],device bool* screens[[buffer(17)]],
 device const long* dims[[buffer(18)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],K=dims[2];if(long(lane)>=B)return;
 actual[lane]=counts[lane]=errors[lane]=required[lane]=0;roots[lane]=-1;unsupported[lane]=screens[lane]=false;
 device long* out=blocks+ulong(lane)*ulong(K)*5;for(long i=0;i<K*5;++i)out[i]=0;if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*ulong(C)*5,lengths[lane],C,
   prefix,poffsets,dims[3],dims[4],suffix,soffsets,dims[5],dims[6],usage,valid);
 if(inherited[lane])valid=false;const long decisions=sections[ulong(lane)*27+13];relations_container(v,decisions,6,-1,valid);
 if(!valid){errors[lane]=1;return;}const long n=state_record(v,decisions)[1];if(!n)return;
 const long decision=state_child(v,decisions,n-1,valid);relations_container(v,decision,10,6,valid);
 const long kind=state_child(v,decision,1,valid);
 if(state_string_equals(v,kind,"naval_force_selection",21,valid)){unsupported[lane]=true;return;}
 if(!state_string_equals(v,kind,"naval_screening_force",21,valid)){if(!valid)errors[lane]=1;return;}
 const long continuation=state_string_id(v,state_child(v,decision,4,valid),valid);
 const long battle=state_map_find_id(v,sections[ulong(lane)*27+14],continuation,valid);
 if(!valid){errors[lane]=1;return;}if(battle<0){errors[lane]=2;return;}
 relations_container(v,battle,10,10,valid);const long data=state_child(v,battle,9,valid);
 const long picked=state_map_find_literal(v,data,"screening",9,valid);long last=-1;
 if(picked>=0){relations_container(v,picked,12,-1,valid);if(valid){
   const long amount=state_record(v,picked)[1];for(long i=0;valid&&i<amount;++i)last=state_string_id(v,state_child(v,picked,i,valid),valid);}}
 if(!valid){errors[lane]=2;return;}
 const long options=state_child(v,decision,5,valid);relations_container(v,options,6,-1,valid);
 if(!valid){errors[lane]=1;return;}roots[lane]=options;screens[lane]=true;
 long cursor=options+1,total=0,kept=0;const long amount=state_record(v,options)[1];
 for(long i=0;valid&&i<amount;++i){const long action=cursor;relations_container(v,action,10,6,valid);
   const long action_kind=state_child(v,action,1,valid),end=state_end(v,action,valid);bool remove=false;
   if(state_string_equals(v,action_kind,"naval_screen_remove",19,valid))remove=true;
   else if(last>=0&&state_string_equals(v,action_kind,"naval_screen_add",16,valid)){
     const long parameters=state_child(v,action,5,valid),unit=state_map_find_literal(v,parameters,"unit",4,valid);
     if(unit<0){errors[lane]=2;return;}remove=rc_less_equal(v,state_string_id(v,unit,valid),last,valid);}
   if(!valid){errors[lane]=2;return;}
   if(!remove){const long size=end-action;if(total>LONG_MAX-size-1){errors[lane]=1;return;}
     if(total+size<=K)for(long row=0;row<size;++row){device const long* old=state_record(v,action+row);
       for(long col=0;col<4;++col)out[ulong(total+row)*5+col]=old[col];out[ulong(total+row)*5+4]=old[4]-action+total;}
     total+=size;++kept;}cursor=end;
 }
 if(!valid||cursor!=state_end(v,options,valid)){errors[lane]=1;return;}
 required[lane]=total+1;if(!kept){errors[lane]=4;return;}if(total+1>K){errors[lane]=8;return;}
 actual[lane]=total;counts[lane]=kept;
}
kernel void validate_recruitment_postconditions(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* sections[[buffer(2)]],
 device const long* inherited[[buffer(3)]],device const long* definition[[buffer(4)]],
 device const uchar* prefix[[buffer(5)]],device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],
 device const long* soffsets[[buffer(8)]],device const long* usage[[buffer(9)]],device const bool* selected[[buffer(10)]],
 device long* errors[[buffer(11)]],device const long* dims[[buffer(12)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1];if(long(lane)>=B)return;errors[lane]=0;if(!selected[lane])return;
 bool valid=true;PackedStateView v=make_packed_state_view(records+ulong(lane)*ulong(C)*5,lengths[lane],C,
   prefix,poffsets,dims[2],dims[3],suffix,soffsets,dims[4],dims[5],usage,valid);
 PackedStateView d{definition,dims[6],dims[6],prefix,poffsets,dims[2],dims[3],suffix,soffsets,0,0};
 if(inherited[lane])valid=false;device const long* index=sections+ulong(lane)*27;
 const long state=index[0],nations=index[2],decisions=index[13];relations_container(v,state,10,19,valid);
 const long politics=state_child(v,state,8,valid),pending=state_child(v,politics,10,valid);
 relations_container(v,nations,7,-1,valid);relations_container(v,pending,7,-1,valid);relations_container(v,decisions,6,-1,valid);
 bool chance=false;const long request=state_optional(v,index[16],chance,valid);
 if(chance!=(dims[7]!=0))errors[lane]|=32;
 if(chance){relations_container(v,request,10,5,valid);
   const long id=state_string_id(v,state_child(v,request,0,valid),valid),purpose=state_string_id(v,state_child(v,request,1,valid),valid);
   if(!rc_nonempty(v,id,valid)||!rc_nonempty(v,purpose,valid))errors[lane]|=32;
   const long continuation=state_string_id(v,state_child(v,request,3,valid),valid);
   if(rc_political(v,purpose,valid)&&state_map_find_id(v,pending,continuation,valid)<0)errors[lane]|=2;}
 if(!valid){errors[lane]|=1;return;}const long count=state_record(v,decisions)[1];long cursor=decisions+1;
 for(long i=0;valid&&i<count;++i){const long decision=cursor;relations_container(v,decision,10,6,valid);
   const long id=state_string_id(v,state_child(v,decision,0,valid),valid),kind=state_string_id(v,state_child(v,decision,1,valid),valid);
   if(!rc_nonempty(v,id,valid)||!rc_nonempty(v,kind,valid))errors[lane]|=4;
   long previous=decisions+1;for(long j=0;valid&&j<i;++j){
     if(state_string_id(v,state_child(v,previous,0,valid),valid)==id)errors[lane]|=4;previous=state_end(v,previous,valid);}
   const long continuation=state_string_id(v,state_child(v,decision,4,valid),valid);
   if(rc_political(v,kind,valid)&&state_map_find_id(v,pending,continuation,valid)<0)errors[lane]|=2;
   const long nation=state_string_id(v,state_child(v,decision,2,valid),valid);
   bool player_valid=valid;const long player=rc_player(v,d,nations,pending,nation,player_valid);
   if(!player_valid)errors[lane]|=8;
   const long options=state_child(v,decision,5,valid);relations_container(v,options,6,-1,valid);long action=options+1;
   if(!valid)break;const long options_count=state_record(v,options)[1];
   for(long j=0;valid&&j<options_count;++j){relations_container(v,action,10,6,valid);
     const long aid=state_string_id(v,state_child(v,action,0,valid),valid),akind=state_string_id(v,state_child(v,action,1,valid),valid);
     if(!rc_nonempty(v,aid,valid)||!rc_nonempty(v,akind,valid))errors[lane]|=16;
     long previous_action=options+1;for(long k=0;valid&&k<j;++k){
       if(state_string_id(v,state_child(v,previous_action,0,valid),valid)==aid)errors[lane]|=16;previous_action=state_end(v,previous_action,valid);}
     const long owner=state_string_id(v,state_child(v,action,3,valid),valid),controller=state_string_id(v,state_child(v,action,2,valid),valid);
     bool present=false;const long decision_ref=state_optional(v,state_child(v,action,4,valid),present,valid);
     if(owner!=nation||controller!=player||!present)errors[lane]|=8;
     if(present&&state_string_id(v,decision_ref,valid)!=id)errors[lane]|=8;
     relations_container(v,state_child(v,action,5,valid),13,-1,valid);action=state_end(v,action,valid);
   }
   if(valid&&action!=state_end(v,options,valid))valid=false;cursor=state_end(v,decision,valid);
 }if(!valid||cursor!=state_end(v,decisions,valid))errors[lane]|=1;
}
'''

_library = None
_lock = threading.Lock()


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:
                _library = torch.mps.compile_shader(SOURCE)
    return _library


@lru_cache(maxsize=32)
def _dimensions(values):
    return torch.tensor(values,dtype=torch.int64,device="mps")


@lru_cache(maxsize=1)
def _dummy():
    return torch.zeros(1,dtype=torch.int64,device="mps")


def _call(kernel,args,count):
    if count:
        kernel(*(value if value.numel() else _dummy() for value in args),threads=count)


def _tensor(value,state,dtype,shape):
    if not isinstance(value,torch.Tensor) or value.dtype!=dtype or value.device!=state.device or \
            tuple(value.shape)!=tuple(shape) or not value.is_contiguous():
        raise ValueError("Recruitment chance requires complete contiguous resident buffers")


def validate_recruitment_postconditions(state,selected=None,*,pending_chance=False):
    """Validate the State invariants touched by recruitment start/chance effects.

    The source must already be native-validated. These operations preserve the
    inventories, units, facilities, rails, battles, clock and turn snapshots.
    New numeric/JSON data are typed finite values from the exact effect builders;
    income refresh and training reset retain their own checked writer contracts.
    This checks the changed decision/continuation relationships and entitlement,
    rather than pretending to be a validator for arbitrary imported State data.
    """
    state._metadata();_device(state.device)
    if state.device.type!="mps":raise ValueError("Recruitment postconditions require explicit Apple GPU execution")
    if type(pending_chance) is not bool:raise ValueError("Expected chance presence must be explicit bool")
    B,C=state.records.shape[:2]
    if selected is None:selected=torch.ones(B,dtype=torch.bool,device=state.device)
    _tensor(selected,state,torch.bool,(B,))
    values=(state.records,state.lengths,state.sections,state.errors,state.context.records,state.context.string_bytes,
            state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage)
    if any(not value.is_contiguous() for value in values):raise ValueError("Postcondition buffers must remain resident and contiguous")
    errors=torch.zeros(B,dtype=torch.int64,device=state.device)
    _call(_kernels().validate_recruitment_postconditions,(*values,selected,errors,
        _dimensions((B,C,state.context.string_count,state.context.string_bytes.numel(),state.string_offsets.numel()-1,
                     state.string_bytes.numel(),state.context.records.shape[0],int(pending_chance)))),B)
    return errors


def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):
        return value
    output=torch.zeros(shape,dtype=value.dtype,device=value.device)
    output[tuple(slice(0,n) for n in value.shape)]=value
    return output


def _invalid_identities(identities,state,invalid):
    # A failed candidate hash must never masquerade as the rolled-back State's
    # planning key. Original expected identity remains the caller's retry key.
    invalid=invalid.to(torch.int32)*(1 << 29)
    return replace(identities,source=state,
        state_json=replace(identities.state_json,errors=identities.state_json.errors|invalid),
        state_keys=replace(identities.state_keys,errors=identities.state_keys.errors|invalid),
        engine_json=replace(identities.engine_json,errors=identities.engine_json.errors|invalid),
        engine_keys=replace(identities.engine_keys,errors=identities.engine_keys.errors|invalid))


class ResidentRecruitmentChance:
    def __init__(self,state_context,effects,income_context,state_json,*,reuse_certified_source=False,random_implementation=None):
        if type(reuse_certified_source) is not bool:raise TypeError("Certified source reuse must be an explicit bool")
        if random_implementation is not None and (type(random_implementation) is not str or random_implementation not in {"reference","parallel"}):
            raise ValueError("Recruitment chance RNG installation must use reference, parallel or the context default")
        self.random_implementation=random_implementation
        self.reuse_certified_source=reuse_certified_source
        if _device(state_context.device).type!="mps":
            raise ValueError("Recruitment chance requires explicit Apple GPU execution; no CPU fallback")
        components=set(state_context.rules_id.split("+"))
        if not {POLITICS_RULES_COMPONENT,ECONOMY_RULES_COMPONENT}.issubset(components):
            raise ValueError("Recruitment chance requires the current income-refresh politics/economy rules contract; legacy rules are unsupported")
        for service in (effects,income_context,state_json):
            if service.state_context is not state_context:
                raise ValueError("Recruitment chance services must share the exact resident context")
        self.state_context=state_context;self.effects=effects;self.income=income_context;self.state_json=state_json
        self.training_reset=ResidentTrainingReset(state_context) if state_context.rules_id.startswith("campaign-orders-v1+") else None
        self.labels=EventLabels(state_context,torch.tensor(state_context.prefix_lookup_ids(("action","interrupt","chance")),
                                                         dtype=torch.int64,device=state_context.device))

    def reserve(self,state,capacities):
        """Explicit one-time arena reservation; unchanged resolutions never grow it."""
        state._metadata();self._context(state)
        if not isinstance(capacities,RecruitmentChanceCapacities):
            raise TypeError("Recruitment chance needs explicit fixed capacities")
        capacities.validate(state);B=state.lane_count
        return DeviceStateBatch(state.context,_pad(state.records,(B,capacities.state_capacity,5)),state.lengths,state.sections,
            _pad(state.string_bytes,(capacities.byte_capacity,)),_pad(state.string_offsets,(capacities.string_capacity+1,)),
            state.errors,state.suffix_usage)

    def _context(self,state):
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:
            raise ValueError("Recruitment chance source belongs to another resident context")
        state._metadata();_device(state.device)
        for value in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets):
            if not value.is_contiguous():
                raise ValueError("Recruitment chance source buffers must remain contiguous")

    def _forward(self,state,selected,capacities):
        """Exact bounded screening hook; retained force selection is unsupported."""
        B,C=state.records.shape[:2];K=capacities.block_capacity;dev=state.device
        blocks=torch.empty((B,K,5),dtype=torch.int64,device=dev)
        actual,counts,roots,errors,required=(torch.zeros(B,dtype=torch.int64,device=dev) for _ in range(5))
        unsupported=torch.zeros(B,dtype=torch.bool,device=dev);screens=torch.zeros_like(unsupported)
        _call(_kernels().recruitment_screen_forward,(state.records,state.lengths,state.sections,state.errors,
            state.context.string_bytes,state.context.string_offsets,state.string_bytes,state.string_offsets,state.suffix_usage,
            selected,blocks,actual,counts,roots,errors,unsupported,required,screens,
            _dimensions((B,C,K,state.context.string_count,state.context.string_bytes.numel(),state.string_offsets.numel()-1,
                         state.string_bytes.numel()))),B)
        healthy=~(errors!=0).any()&~unsupported.any()
        lanes=torch.arange(B,dtype=torch.int64,device=dev)
        headers=state.records.reshape(-1,5).index_select(0,lanes*C+roots.clamp(0,max(C-1,0)))
        remove=headers[:,1].contiguous()
        build=build_sequence_splices(state,roots,torch.zeros_like(roots),remove,blocks,actual,counts,
                                     selected&screens&healthy,capacity=K)
        edited=commit_container_edits(build,capacity=capacities.state_capacity)
        bad=(build.errors!=0)|(edited.edit_errors!=0)
        capacity_bad=((build.errors&64)!=0)|((edited.edit_errors&8)!=0)
        errors|=torch.where(bad,torch.where(capacity_bad,int(RecruitmentForwardError.CAPACITY),int(RecruitmentForwardError.PACKED)),0)
        return _ForwardResult(edited.state,errors,unsupported,edited.required_state_capacity,
            torch.maximum(required,build.required_capacity),~(errors!=0).any()&~unsupported.any()&edited.committed)

    def resolve(self,before,expected,*,capacities,selected=None,sampled=None,profile=None):
        """Resolve sampled recruitment only, retaining the original transaction on failure.

        expected is a source-bound StateIdentityBatch carrying the full Engine
        planning key. Sampling is optional only for an already sampled result
        bound to this exact immutable source; no stage resamples a failed draw.
        Required capacities are per-stage device tensors. ``attempted`` tells
        which selected lanes reached each stage; later requirements after a
        failure describe the retained intermediate, not an invented success.
        An explicit diagnostics callback receives stage names after submission.
        Default execution adds no timers, fences or callback invocations.
        """
        self._context(before)
        if not isinstance(expected,StateIdentityBatch) or expected.source is not before:
            raise ValueError("Expected full Engine identity belongs to a stale or foreign source")
        if not isinstance(capacities,RecruitmentChanceCapacities):
            raise TypeError("Recruitment chance needs explicit fixed capacities")
        capacities.validate(before);B,C=before.records.shape[:2];dev=before.device
        if profile is not None and not callable(profile):raise TypeError("Recruitment diagnostics callback must be callable")
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,before,torch.bool,(B,))
        for keys in (expected.state_keys,expected.engine_keys):
            for value,dtype,shape in ((keys.hex_bytes,torch.uint8,(B,64)),(keys.errors,torch.int32,(B,)),
                    (keys.batch_error,torch.int32,(1,)),(keys.count,torch.int64,(1,))):
                _tensor(value,before,dtype,shape)
        if sampled is not None and (sampled.source is not before or tuple(sampled.faces.shape)!=(B,capacities.dice_capacity,capacities.roll_capacity)):
            raise ValueError("Saved sampled chance belongs to a stale source or different fixed arena")
        errors=torch.zeros(B,dtype=torch.int64,device=dev);stage_errors={};required={};attempted={}

        def stage(name,code,details,active,committed=None):
            nonlocal errors
            details=details.to(torch.int64);stage_errors[name]=torch.where(active,details,0);attempted[name]=active
            failed=active&(details!=0)
            if committed is not None:failed|=active&~committed
            errors|=failed.to(torch.int64)*int(code)
            if profile is not None:profile(name)
            return selected&~(errors!=0).any()

        capability=torch.zeros(B,dtype=torch.int64,device=dev);handled=torch.zeros(B,dtype=torch.bool,device=dev)
        _call(_kernels().recruitment_chance_capability,(before.records,before.lengths,before.sections,before.errors,
            before.context.string_bytes,before.context.string_offsets,before.string_bytes,before.string_offsets,before.suffix_usage,
            selected,capability,handled,_dimensions((B,C,before.context.string_count,before.context.string_bytes.numel(),
                before.string_offsets.numel()-1,before.string_bytes.numel()))),B)
        from .resident_identity_certificates import source_identity_check
        checked=source_identity_check(self.state_json,before,expected,byte_capacity=capacities.json_byte_capacity,
                                      reuse=self.reuse_certified_source)
        bad_hash=(checked.engine_keys.errors!=0)|(checked.engine_keys.batch_error!=0).any()|(checked.engine_keys.count!=B).any()
        bad_hash|=(expected.engine_keys.errors!=0)|(expected.engine_keys.batch_error!=0).any()|(expected.engine_keys.count!=B).any()
        mismatch=(checked.engine_keys.hex_bytes!=expected.engine_keys.hex_bytes).any(1)
        preflight=capability|(bad_hash.to(torch.int64)*8)|(mismatch.to(torch.int64)*4)
        required["before_json_bytes"]=checked.state_json.required_bytes
        active=stage("preflight",RecruitmentChanceError.PREFLIGHT,preflight,selected)
        sampled=sample_packed_chance(before,dice_capacity=capacities.dice_capacity,roll_capacity=capacities.roll_capacity) if sampled is None else sampled
        required["sample"]=sampled.required
        active=stage("sample",RecruitmentChanceError.SAMPLE,sampled.errors,active)
        effect=self.effects.apply(before,sampled,active,state_capacity=capacities.state_capacity,block_capacity=capacities.block_capacity,
            choice_capacity=capacities.choice_capacity,parameter_byte_capacity=capacities.parameter_byte_capacity,
            string_capacity=capacities.string_capacity,byte_capacity=capacities.byte_capacity)
        required.update(effects_state=effect.required_state_capacity,effects_block=effect.required_block_capacity,
            effects_strings=effect.required_string_usage,effects_choices=effect.required_choice_capacity,
            effects_parameter_bytes=effect.required_parameter_bytes)
        active=stage("effects",RecruitmentChanceError.EFFECTS,effect.errors,active,effect.committed)
        income=self.income.refresh(effect.state,active,capacity=capacities.state_capacity)
        required["income_state"]=income.required_capacity
        active=stage("income",RecruitmentChanceError.INCOME,income.errors,active)
        current=income.state
        if self.training_reset is not None:
            reset=self.training_reset.reset(current,active,capacity=capacities.state_capacity)
            required["reset_state"]=reset.required_capacity
            active=stage("reset",RecruitmentChanceError.RESET,reset.errors,active,reset.committed);current=reset.state
        else:
            required["reset_state"]=current.lengths
            active=stage("reset",RecruitmentChanceError.RESET,torch.zeros_like(errors),active)
        if self.training_reset is not None:
            forward=self._forward(current,active,capacities)
            required.update(forward_state=forward.required_state_capacity,forward_block=forward.required_block_capacity)
            active=stage("forward_capability",RecruitmentChanceError.FORWARD_CAPABILITY,
                forward.unsupported.to(torch.int64)*int(RecruitmentForwardError.UNSUPPORTED_NAVAL_FORCE),active)
            active=stage("forward",RecruitmentChanceError.FORWARD,forward.errors,active,forward.committed)
            current=forward.state
        else:
            required.update(forward_state=current.lengths,forward_block=torch.zeros_like(errors))
            active=stage("forward_capability",RecruitmentChanceError.FORWARD_CAPABILITY,torch.zeros_like(errors),active)
            active=stage("forward",RecruitmentChanceError.FORWARD,torch.zeros_like(errors),active)
        clock_errors=torch.zeros_like(errors)
        _call(_kernels().recruitment_chance_clock,(before.records,before.lengths,before.sections,current.records,current.lengths,
            current.sections,active,clock_errors,_dimensions((B,C,current.records.shape[1]))),B)
        active=stage("clock",RecruitmentChanceError.CLOCK,clock_errors,active)
        postconditions=validate_recruitment_postconditions(current,active)
        active=stage("validation",RecruitmentChanceError.VALIDATION,postconditions,active)
        identities=self.state_json.identities(current,byte_capacity=capacities.json_byte_capacity)
        required["after_json_bytes"]=identities.state_json.required_bytes
        identity_error=identities.engine_keys.errors.to(torch.int64)|identities.engine_keys.batch_error.to(torch.int64)
        active=stage("identity",RecruitmentChanceError.IDENTITY,identity_error,active)
        payload=build_chance_payload(before,current,sampled,capacity=capacities.payload_capacity)
        required["payload"]=payload.required_capacity
        active=stage("payload",RecruitmentChanceError.PAYLOAD,payload.errors,active)
        event=append_events(current,identities,payload.payloads,torch.full((B,),EventKind.CHANCE,dtype=torch.int64,device=dev),self.labels,
            selected=active,state_capacity=capacities.state_capacity,block_capacity=capacities.block_capacity,
            string_capacity=capacities.string_capacity,byte_capacity=capacities.byte_capacity)
        required.update(event_state=event.required_state_capacity,event_block=event.required_block_capacity,event_strings=event.required_string_usage)
        active=stage("event",RecruitmentChanceError.EVENT,event.errors,active,event.committed)
        random=install_sampled_randomness(before,event.state,sampled,active,implementation=self.random_implementation)
        active=stage("random",RecruitmentChanceError.RANDOM,random.errors,active,random.committed)
        committed=~(errors!=0).any();candidate=random.state
        baseline=self.reserve(before,capacities)
        output=DeviceStateBatch(before.context,torch.where(committed,candidate.records,baseline.records),
            torch.where(committed,candidate.lengths,before.lengths),torch.where(committed,candidate.sections,before.sections),
            torch.where(committed,candidate.string_bytes,baseline.string_bytes),torch.where(committed,candidate.string_offsets,baseline.string_offsets),
            torch.where(committed,candidate.errors,before.errors),torch.where(committed,candidate.suffix_usage,before.suffix_usage))
        after_identity=identities
        identities=_invalid_identities(event.identities,output,selected&~committed)
        if self.reuse_certified_source:
            from .resident_identity_certificates import _certify_recruitment_chance_publication
            _certify_recruitment_chance_publication(self.state_json,identities,before=before,before_expected=expected,
                before_check=checked,after_identity=after_identity,event=event,random=random,committed=committed,
                byte_capacity=capacities.json_byte_capacity)
        if profile is not None:profile("publish")
        return RecruitmentChanceResult(before,output,sampled,identities,errors,stage_errors,required,attempted,handled,selected&committed,committed)
