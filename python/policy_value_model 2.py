from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn


@dataclass
class PolicyValueModelConfig:
    state_dim: int
    action_dim: int
    state_hidden_dim: int = 128
    action_hidden_dim: int = 64
    joint_hidden_dim: int = 128


class LegalActionPolicyValueNet(nn.Module):
    """
    Scores only the legal actions for a given state.

    Expected shapes:
    - state_features: [batch, state_dim]
    - legal_action_features: [batch, legal_count, action_dim]
    - legal_action_mask: [batch, legal_count] or None

    Returns:
    - policy_logits: [batch, legal_count]
    - value: [batch]
    """

    def __init__(self, config: PolicyValueModelConfig) -> None:
        super().__init__()
        self.config = config

        self.state_encoder = nn.Sequential(
            nn.Linear(config.state_dim, config.state_hidden_dim),
            nn.ReLU(),
            nn.Linear(config.state_hidden_dim, config.state_hidden_dim),
            nn.ReLU(),
        )

        self.action_encoder = nn.Sequential(
            nn.Linear(config.action_dim, config.action_hidden_dim),
            nn.ReLU(),
            nn.Linear(config.action_hidden_dim, config.action_hidden_dim),
            nn.ReLU(),
        )

        self.policy_head = nn.Sequential(
            nn.Linear(config.state_hidden_dim + config.action_hidden_dim, config.joint_hidden_dim),
            nn.ReLU(),
            nn.Linear(config.joint_hidden_dim, 1),
        )

        self.value_head = nn.Sequential(
            nn.Linear(config.state_hidden_dim, config.joint_hidden_dim),
            nn.ReLU(),
            nn.Linear(config.joint_hidden_dim, 1),
        )

    def forward(
        self,
        state_features: Tensor,
        legal_action_features: Tensor,
        legal_action_mask: Tensor | None = None,
    ) -> tuple[Tensor, Tensor]:
        if state_features.ndim != 2:
            raise ValueError(f"Expected state_features [batch, state_dim], got {tuple(state_features.shape)}")
        if legal_action_features.ndim != 3:
            raise ValueError(
                "Expected legal_action_features [batch, legal_count, action_dim], "
                f"got {tuple(legal_action_features.shape)}"
            )

        batch_size, legal_count, _ = legal_action_features.shape
        state_latent = self.state_encoder(state_features)
        action_latent = self.action_encoder(legal_action_features)
        state_latent_expanded = state_latent.unsqueeze(1).expand(batch_size, legal_count, -1)

        joint_latent = torch.cat((state_latent_expanded, action_latent), dim=-1)
        policy_logits = self.policy_head(joint_latent).squeeze(-1)
        if legal_action_mask is not None:
            if legal_action_mask.shape != policy_logits.shape:
                raise ValueError(
                    f"legal_action_mask shape {tuple(legal_action_mask.shape)} "
                    f"does not match logits shape {tuple(policy_logits.shape)}"
                )
            policy_logits = policy_logits.masked_fill(~legal_action_mask, -1e9)

        value = self.value_head(state_latent).squeeze(-1)
        return policy_logits, value
