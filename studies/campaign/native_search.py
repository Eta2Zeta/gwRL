"""One campaign decision searched in C++ (game/search.hpp, src/search.cpp).

The search is VectorMCTS's multiplayer mode (studies/shared/multiplayer_mcts.py)
with a new tree each decision, on CampaignAdapter's declaration-offer
scheduling. It runs every simulation in C++ without Python's lock, so a game
thread comes back to Python once a decision rather than once an engine call.
Given the same network outputs and seed it makes the same choices and returns
the same numbers as VectorMCTS (tests/test_campaign_native_search.py).

The search reaches a network three ways: through a RemoteEvaluator's native
client, which talks to the inference server without Python; not at all for
UniformEvaluator, whose priors are uniform and values zero; or through any
other evaluator's evaluate_zone(zone_input, actor), which the search calls with
Python's lock.
"""
from __future__ import annotations

from typing import Any

import gwrl_cpp

from studies.shared.campaign_adapter import CampaignAdapter
from studies.shared.multiplayer_mcts import MctsConfig, NoLegalActionError, SearchResult, UniformEvaluator


class _Position:
    """A decision's position as the C++ search wrote it, for NoLegalActionError."""

    def __init__(self, serialized: str) -> None:
        self._serialized = serialized

    def serialize(self) -> str:
        return self._serialized


def native_evaluator(evaluator: Any) -> Any:
    """What the C++ search calls for network evaluations: a native client, None
    for uniform priors and zero values, or an evaluator with evaluate_zone."""
    client = getattr(evaluator, "client", None)
    if isinstance(client, gwrl_cpp.InferenceClient):
        return client
    if type(evaluator) is UniformEvaluator:
        return None
    if callable(getattr(evaluator, "evaluate_zone", None)):
        return evaluator
    raise TypeError("The C++ search needs a RemoteEvaluator, a UniformEvaluator or an evaluator with evaluate_zone")


def search_decision(env: CampaignAdapter, evaluator: Any, config: MctsConfig, *, add_root_noise: bool) -> SearchResult:
    """Search env's decision, as VectorMCTS(evaluator, config).search(env,
    add_root_noise=add_root_noise, reuse_root=False) would."""
    if config.mode != "multiplayer" or config.record_trace:
        raise ValueError("The C++ search plays multiplayer mode and records no traces")
    if not isinstance(env, CampaignAdapter) or not isinstance(env.raw, gwrl_cpp.CampaignEnv):
        raise TypeError("The C++ search needs a CampaignAdapter around the native campaign")
    passed, order = env.scheduling()
    try:
        outcome = gwrl_cpp.search_campaign(
            env.raw, passed, order, native_evaluator(evaluator), simulations=config.simulations,
            c_puct=config.c_puct, max_depth=config.max_depth, seed=config.seed, root_noise=add_root_noise,
            dirichlet_alpha=config.root_dirichlet_alpha, dirichlet_epsilon=config.root_dirichlet_epsilon,
            search_forced_root=config.search_forced_root)
    except gwrl_cpp.NoLegalSearchAction as error:
        raise NoLegalActionError(_Position(str(error))) from None
    actions = env.legal_actions()
    if [action.id for action in actions] != outcome["action_ids"]:
        raise RuntimeError("The C++ search's root options differ from the adapter's")
    return SearchResult(actions, outcome["visit_counts"], outcome["policy"], outcome["priors"], outcome["values"],
                        outcome["action_values"], None, (), False, [], outcome["zone_input"])
