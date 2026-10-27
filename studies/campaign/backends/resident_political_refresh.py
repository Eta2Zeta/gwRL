"""Exact single-pass refreshPoliticalState orchestration on resident State.

The order is part of the rule contract: possession flags; CCP then KMT civil
flags and any evolution effects; KMT surrender; objective and bonus; allies.
In particular, surrender does not revisit an earlier civil flag, and the first
evolution can queue a battle using KMT's still-minor status. This rule helper
does not add Engine validation, income, history, calendar or randomness hooks.
"""
from dataclasses import dataclass,fields
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .metal_state_schema import METAL_STATE_SOURCE


@dataclass(frozen=True)
class PoliticalRefreshCapacities:
    state_capacity:int
    block_capacity:int
    string_capacity:int
    byte_capacity:int
    movement_unit_capacity:int  # Across the complete selected batch.
    surrender_unit_capacity:int  # Per lane, including the removal scratch map.
    surrender_project_capacity:int
    surrender_dice_capacity:int
    truce_battle_capacity:int
    evolution_option_capacity:int
    evolution_parameter_byte_capacity:int
    evolution_pending_key_byte_capacity:int
    evolution_action_id_byte_capacity:int
    evolution_decision_id_byte_capacity:int

    def validate(self,state):
        if any(type(getattr(self,item.name)) is not int or getattr(self,item.name)<0 for item in fields(self)):
            raise ValueError("Political refresh capacities must be explicit nonnegative integer allocations")
        if self.state_capacity<state.records.shape[1] or self.block_capacity<1 or self.string_capacity<state.string_offsets.numel()-1 or self.byte_capacity<state.string_bytes.numel():
            raise ValueError("Political refresh arenas must preserve every original rollback word")
        if max(getattr(self,item.name) for item in fields(self))>2**63-1 or state.lane_count>2**32-1 or state.lane_count*max(self.state_capacity,self.block_capacity,1)*5>2**63-1:
            raise OverflowError("Political refresh allocations are not representable")


@dataclass(frozen=True)
class PoliticalRefreshResult:
    state:DeviceStateBatch
    errors:torch.Tensor
    first_failure_stage:torch.Tensor
    stage_errors:dict
    attempted:dict
    required:dict
    message_ids:dict
    promoted:torch.Tensor
    surrender_due:torch.Tensor
    required_state_capacity:torch.Tensor
    required_block_capacity:torch.Tensor
    required_string_usage:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE="#include <metal_stdlib>\nusing namespace metal;\n"+METAL_STATE_SOURCE+r'''
inline bool pr_container(thread const PackedStateView& v,long root,long tag,long count,thread bool& valid){
 const long end=state_end(v,root,valid);if(!valid)return false;device const long* row=state_record(v,root);
 const long maximum=tag==7?(end-root-1)/2:end-root-1;
 if(row[0]!=tag||row[1]<0||row[1]>maximum||(count>=0&&row[1]!=count)||row[2]||row[3])valid=false;return valid;
}
kernel void political_refresh_present(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* inherited[[buffer(2)]],device const bool* selected[[buffer(3)]],device const long* owners[[buffer(4)]],
 device const uchar* prefix[[buffer(5)]],device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],
 device const long* soffsets[[buffer(8)]],device const long* usage[[buffer(9)]],device bool* present[[buffer(10)]],
 device long* errors[[buffer(11)]],device const long* dims[[buffer(12)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;present[lane]=false;errors[lane]=0;if(!selected[lane])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
 prefix,poffsets,dims[2],dims[3],suffix,soffsets,dims[4],dims[5],usage,valid);
 if(inherited[lane])valid=false;pr_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);pr_container(v,state,10,19,valid);
 const long nations=state_child(v,state,0,valid);pr_container(v,nations,7,-1,valid);
 present[lane]=state_map_find_id(v,nations,owners[lane],valid)>=0;if(!valid)errors[lane]=3;
}
kernel void political_refresh_surrender_plan(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* inherited[[buffer(2)]],device const bool* selected[[buffer(3)]],device const long* kmt[[buffer(4)]],
 device const long* definition[[buffer(5)]],device const uchar* prefix[[buffer(6)]],device const long* poffsets[[buffer(7)]],
 device const uchar* suffix[[buffer(8)]],device const long* soffsets[[buffer(9)]],device const long* usage[[buffer(10)]],
 device bool* due[[buffer(11)]],device long* attackers[[buffer(12)]],device long* errors[[buffer(13)]],device const long* dims[[buffer(14)]],
 uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;due[lane]=false;attackers[lane]=-1;errors[lane]=0;if(!selected[lane])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*dims[1]*5,lengths[lane],dims[1],
 prefix,poffsets,dims[2],dims[3],suffix,soffsets,dims[4],dims[5],usage,valid);
 if(inherited[lane])valid=false;pr_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);pr_container(v,state,10,19,valid);
 const long nations=state_child(v,state,0,valid),politics=state_child(v,state,8,valid);pr_container(v,nations,7,-1,valid);
 const long nation=state_map_find_id(v,nations,kmt[0],valid);if(!valid){errors[lane]=3;return;}if(nation<0)return;
 const long surrendered=state_child(v,politics,8,valid);pr_container(v,surrendered,8,-1,valid);long cursor=surrendered+1;
 for(long i=0;valid&&i<state_record(v,surrendered)[1];++i){if(state_string_id(v,cursor,valid)==kmt[0])return;cursor=state_end(v,cursor,valid);}
 const long land=state_child(v,state,1,valid);pr_container(v,land,7,-1,valid);cursor=land+1;
 for(long i=0;valid&&i<state_record(v,land)[1];++i){const long territory=cursor+1;pr_container(v,territory,10,2,valid);
   bool present=false;const long possessor=state_optional(v,state_child(v,territory,0,valid),present,valid);
   if(present&&state_string_id(v,possessor,valid)==kmt[0])return;cursor=state_end(v,territory,valid);}
 if(!valid){errors[lane]=3;return;}due[lane]=true;
 const long pending=state_child(v,politics,10,valid);pr_container(v,pending,7,-1,valid);
 const long invader=state_map_find_literal(v,pending,"last_conqueror_kmt",18,valid);
 if(!valid){errors[lane]=3;return;}if(invader>=0){
   if(state_record(v,invader)[0]!=5){errors[lane]=2;return;}attackers[lane]=state_string_id(v,invader,valid);
 }else{
   const long clock=state_child(v,state,7,valid),turn=state_signed_value(v,state_child(v,clock,1,valid),valid);
   auto d=v;d.records=definition;d.length=d.capacity=dims[6];d.suffix_count=d.suffix_bytes_length=0;
   const long order=state_child(d,0,6,valid);pr_container(d,order,6,-1,valid);
   attackers[lane]=state_string_id(d,state_child(d,order,turn,valid),valid);
 }
 if(!valid)errors[lane]=3;
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
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    out=torch.zeros(shape,dtype=value.dtype,device=value.device);out[tuple(slice(0,n) for n in value.shape)]=value;return out


class ResidentPoliticalRefresh:
    def __init__(self,state_context,facts,movement,truce,evolution,surrender):
        if _device(state_context.device).type!="mps" or any(component.state_context is not state_context for component in (facts,movement,truce,evolution,surrender)):
            raise ValueError("Political refresh needs exact shared resident State component contexts")
        self.state_context=state_context;self.facts=facts;self.movement=movement;self.truce=truce;self.evolution=evolution;self.surrender=surrender
        self.owners=torch.tensor(state_context.prefix_lookup_ids(("ccp","kmt")),dtype=torch.int64,device=state_context.device)

    def reserve(self,state,*,movement_unit_capacity,surrender_unit_capacity,surrender_project_capacity,truce_battle_capacity,
                evolution_option_capacity,evolution_parameter_byte_capacity=512):
        """One explicit warm reservation; capacities are never legal limits."""
        C=state.records.shape[1];facts=self.facts.reserve(state)
        movement=self.movement.reserve(state,unit_capacity=movement_unit_capacity)
        truce=self.truce.reserve(state,battle_capacity=truce_battle_capacity)
        evolution=self.evolution.reserve(state,option_capacity=evolution_option_capacity,parameter_byte_capacity=evolution_parameter_byte_capacity)
        surrender=self.surrender.reserve(state,unit_capacity=surrender_unit_capacity,project_capacity=surrender_project_capacity)
        S=C+7*(facts["state_capacity"]-C)+2*(movement["state_capacity"]-C)+(truce["state_capacity"]-C)+2*(evolution["state_capacity"]-C)+2*(surrender["state_capacity"]-C)
        T=state.string_offsets.numel()-1;A=state.string_bytes.numel()
        string_capacity=T+(truce["string_capacity"]-T)+2*(evolution["string_capacity"]-T)+2*(surrender["string_capacity"]-T)
        byte_capacity=A+(truce["byte_capacity"]-A)+2*(evolution["byte_capacity"]-A)+2*(surrender["byte_capacity"]-A)
        return PoliticalRefreshCapacities(S,max(S,1),string_capacity,byte_capacity,movement_unit_capacity,surrender_unit_capacity,
            surrender_project_capacity,surrender["dice_capacity"],truce_battle_capacity,evolution_option_capacity,evolution_parameter_byte_capacity,
            evolution["pending_key_byte_capacity"],evolution["action_id_byte_capacity"],evolution["decision_id_byte_capacity"])

    def refresh(self,state,selected=None,*,capacities):
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Political refresh source context differs")
        if not isinstance(capacities,PoliticalRefreshCapacities):raise TypeError("Political refresh needs its explicit arena capacity contract")
        state._metadata();_device(state.device);capacities.validate(state);B,C=state.records.shape[:2];dev=state.device
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        if not isinstance(selected,torch.Tensor) or selected.dtype!=torch.bool or selected.device!=dev or tuple(selected.shape)!=(B,) or not selected.is_contiguous():
            raise ValueError("Political refresh selections must be a contiguous resident bool lane vector")
        for value in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets,state.suffix_usage,
                      state.context.records,state.context.string_bytes,state.context.string_offsets):
            if value.device!=dev or not value.is_contiguous():raise ValueError("Political refresh State/context must remain resident contiguous buffers")
        S,K,T,A=capacities.state_capacity,capacities.block_capacity,capacities.string_capacity,capacities.byte_capacity
        arenas=dict(state_capacity=S,block_capacity=K);pools=dict(string_capacity=T,byte_capacity=A)
        errors=torch.zeros(B,dtype=torch.int64,device=dev);first=torch.zeros_like(errors)
        stage_errors,attempted,required,messages={},{},{},{}
        needed_state=state.lengths.clone();needed_block=torch.zeros_like(errors);needed_strings=state.suffix_usage.clone()
        current=state;ordinal=0
        def active():return selected&~(errors!=0).any()
        def record(name,result,mask):
            nonlocal errors,first,ordinal,needed_state,needed_block,needed_strings,current
            ordinal+=1;details=torch.where(mask,result.errors.to(torch.int64),0)
            # A component's shared failure must remain fail-closed even if a
            # defective component omitted its per-lane reason. Ordinary cohort
            # rollback preserves the healthy lanes' zero diagnostic codes.
            absent=(~result.committed)&~(details!=0).any()
            details=torch.where(mask&absent,3,details)
            stage_errors[name]=details;attempted[name]=mask
            first=torch.where((errors==0)&(details!=0),ordinal,first)
            errors=torch.where((errors==0)&(details!=0),details,errors)
            sizes={item.name:getattr(result,item.name) for item in fields(result) if item.name.startswith("required_")}
            required[name]=sizes
            if hasattr(result,"message_ids"):messages[name]=result.message_ids
            if "required_state_capacity" in sizes:needed_state=torch.maximum(needed_state,sizes["required_state_capacity"])
            if "required_block_capacity" in sizes:needed_block=torch.maximum(needed_block,sizes["required_block_capacity"])
            if "required_string_usage" in sizes:needed_strings=torch.maximum(needed_strings,sizes["required_string_usage"])
            current=result.state
        mask=active();record("possessions",self.facts.refresh_possessions(current,mask,**arenas),mask)
        promotions=[]
        for index,nation in enumerate(("ccp","kmt")):
            owner=self.owners[index].expand(B).contiguous()
            present=torch.zeros(B,dtype=torch.bool,device=dev);presence_errors=torch.zeros_like(errors);mask=active()
            _call(_kernels().political_refresh_present,(current.records,current.lengths,current.errors,mask,owner,current.context.string_bytes,
                current.context.string_offsets,current.string_bytes,current.string_offsets,current.suffix_usage,present,presence_errors,
                _dimensions((B,current.records.shape[1],current.context.string_count,current.context.string_bytes.numel(),
                             current.string_offsets.numel()-1,current.string_bytes.numel()))),B)
            ordinal+=1;stage_errors[nation+"_presence"]=torch.where(mask,presence_errors,0);attempted[nation+"_presence"]=mask;required[nation+"_presence"]={}
            first=torch.where((errors==0)&mask&(presence_errors!=0),ordinal,first);errors=torch.where((errors==0)&mask&(presence_errors!=0),presence_errors,errors)
            mask=active()&present;record(nation+"_civil",self.facts.refresh_civil_flag(current,owner,mask,**arenas),mask)
            mask=active()&present;marked=self.facts.mark_evolution_if_due(current,owner,mask,**arenas);record(nation+"_promotion",marked,mask)
            promoted=marked.promoted&mask&~(errors!=0).any();promotions.append(promoted)
            mask=promoted&active();record(nation+"_movement",self.movement.refresh_movement(current,owner,mask,
                unit_capacity=capacities.movement_unit_capacity,**arenas),mask)
            mask=promoted&active();record(nation+"_truce",self.truce.terminate(current,owner,torch.ones(B,dtype=torch.bool,device=dev),mask,
                battle_capacity=capacities.truce_battle_capacity,**arenas,**pools),mask)
            mask=promoted&active();record(nation+"_choice",self.evolution.queue(current,owner,mask,
                option_capacity=capacities.evolution_option_capacity,parameter_byte_capacity=capacities.evolution_parameter_byte_capacity,
                pending_key_byte_capacity=capacities.evolution_pending_key_byte_capacity,action_id_byte_capacity=capacities.evolution_action_id_byte_capacity,
                decision_id_byte_capacity=capacities.evolution_decision_id_byte_capacity,**arenas,**pools),mask)
        due=torch.zeros(B,dtype=torch.bool,device=dev);attackers=torch.full((B,),-1,dtype=torch.int64,device=dev);plan_errors=torch.zeros_like(errors)
        mask=active()
        _call(_kernels().political_refresh_surrender_plan,(current.records,current.lengths,current.errors,mask,self.owners[1:2],current.context.records,
            current.context.string_bytes,current.context.string_offsets,current.string_bytes,current.string_offsets,current.suffix_usage,due,attackers,plan_errors,
            _dimensions((B,current.records.shape[1],current.context.string_count,current.context.string_bytes.numel(),
                         current.string_offsets.numel()-1,current.string_bytes.numel(),current.context.records.shape[0]))),B)
        # The lazy selector has no State write or additional allocation.
        ordinal+=1;stage_errors["surrender_plan"]=torch.where(mask,plan_errors,0);attempted["surrender_plan"]=mask;required["surrender_plan"]={}
        first=torch.where((errors==0)&mask&(plan_errors!=0),ordinal,first);errors=torch.where((errors==0)&mask&(plan_errors!=0),plan_errors,errors)
        mask=due&active();record("kmt_surrender",self.surrender.surrender(current,self.owners[1].expand(B).contiguous(),attackers,mask,
            unit_capacity=capacities.surrender_unit_capacity,project_capacity=capacities.surrender_project_capacity,dice_capacity=capacities.surrender_dice_capacity,
            **arenas,**pools),mask)
        mask=active();record("objective",self.facts.refresh_one_china_objective(current,mask,**arenas),mask)
        mask=active();record("bonus",self.surrender.queue_bonus(current,mask,**arenas,**pools),mask)
        mask=active();record("allies",self.facts.rebuild_allies(current,mask,**arenas),mask)
        committed=~(errors!=0).any()
        output=DeviceStateBatch(state.context,torch.where(committed,current.records,_pad(state.records,(B,S,5))),
            torch.where(committed,current.lengths,state.lengths),torch.where(committed,current.sections,state.sections),
            torch.where(committed,current.string_bytes,_pad(state.string_bytes,(A,))),torch.where(committed,current.string_offsets,_pad(state.string_offsets,(T+1,))),
            state.errors,torch.where(committed,current.suffix_usage,state.suffix_usage))
        return PoliticalRefreshResult(output,errors,first,stage_errors,attempted,required,messages,torch.stack(promotions,1)&committed,
            due&committed,needed_state,needed_block,needed_strings,selected&committed,committed)
