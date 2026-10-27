"""Exact TrainingRules reset hook over resident state; no phase/rule dispatch.

Only the public order-construction metadata changes. Full rule/chance effects,
naval decision forwarding and audit Event append belong to the calling handler.
"""
import torch
from .device_state_edits import replace_subtrees


class ResidentTrainingReset:
    def __init__(self,state_context):
        if state_context.device.type!='mps':raise ValueError('Training reset requires explicit Apple GPU execution')
        if not state_context.rules_id.startswith('campaign-orders-v1+'):
            raise ValueError('Training reset belongs to the campaign-orders-v1 rules profile')
        self.state_context=state_context
        declined,schema,value,visited=map(int,state_context.prefix_lookup_ids(
            ('declined_rail_requests','schema','campaign-orders-v1','visited_configurations')))
        # Canonical JSON object field order and exact empty arrays.
        rows=[[13,3,0,0,7],[5,declined,0,0,2],[12,0,0,0,3],
              [5,schema,0,0,4],[5,value,0,0,5],[5,visited,0,0,6],[12,0,0,0,7]]
        self.template=torch.tensor(rows,dtype=torch.int64,device=state_context.device)

    def reset(self,state,selected=None,*,capacity=None):
        state._metadata()
        if state.context is not self.state_context:
            raise ValueError('Training reset must use the exact resident state context')
        B=state.lane_count
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=state.device)
        if (not isinstance(selected,torch.Tensor) or selected.dtype!=torch.bool or selected.shape!=(B,) or
            selected.device!=state.device or not selected.is_contiguous()):
            raise ValueError('Training reset selection must be contiguous resident bool[lane]')
        if self.template.shape!=(7,5) or self.template.dtype!=torch.int64 or \
           self.template.device!=state.device or not self.template.is_contiguous():
            raise ValueError('Training reset template lost its complete native layout')
        roots=state.section('state.action_interface').contiguous()
        blocks=self.template.unsqueeze(0).repeat(B,1,1)
        lengths=torch.full((B,),7,dtype=torch.int64,device=state.device)
        # A fixed default allocation prevents padding growth on repeated hooks.
        return replace_subtrees(state,roots,blocks,lengths,selected,
                                capacity=state.records.shape[1] if capacity is None else capacity)
