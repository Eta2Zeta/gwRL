from __future__ import annotations

import unittest

from japan_mcts import MctsConfig, MctsNode, MinMaxStats, _score_actions


class JapanMctsSelectionTests(unittest.TestCase):
    def test_unvisited_action_uses_optimistic_normalized_q(self) -> None:
        node = MctsNode(
            actions=["visited", "unvisited"],
            priors=[0.5, 0.5],
            selection_priors=[0.5, 0.5],
            children=[None, None],
            visit_counts=[1, 0],
            value_sums=[7.0, 0.0],
            expanded=True,
        )
        min_max_stats = MinMaxStats()
        min_max_stats.update(7.0)

        scores, selected_index = _score_actions(
            node,
            MctsConfig(c_puct=0.0),
            min_max_stats,
        )

        self.assertEqual(scores[0].normalized_q_value, 0.5)
        self.assertEqual(scores[1].normalized_q_value, 1.0)
        self.assertIsNone(scores[1].raw_q_value)
        self.assertEqual(selected_index, 1)


if __name__ == "__main__":
    unittest.main()
