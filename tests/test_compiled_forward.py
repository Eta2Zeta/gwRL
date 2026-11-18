"""One network's zone and position layers, compiled for fixed numbers of states, answer as written."""
from __future__ import annotations

import unittest

import torch

from studies.campaign.features import default_zone_spec, make_zone_input, pack_zone_arrays
from studies.campaign.neural import (CampaignModelConfig, CampaignPolicyValueNet, NetworkStack, STATE_BUCKETS,
                                     state_bucket)
from tests.test_shared_evaluator import positions, prepared, restore


def batch_of(items):
    return pack_zone_arrays(items, default_zone_spec())


class CompiledForwardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads()
        torch.set_num_threads(1)
        torch.manual_seed(1952)
        cls.model = CampaignPolicyValueNet(CampaignModelConfig(hidden_dim=16, message_layers=2)).eval()
        for table in (cls.model.zone_columns, cls.model.global_columns, cls.model.option_columns):
            table.weight.data.normal_(0.0, 0.5)  # A fresh network's rows are zero: give the answers weight.
        cls.decisions, chance = positions()
        envs = [restore(text) for text in cls.decisions] + [restore(chance)]
        cls.items = [prepared(env, () if env.decision_kind() == "chance" else tuple(env.legal_actions()))[1]
                     for env in envs]

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)

    def test_the_run_setting_is_off_unless_asked_for(self):
        from studies.campaign.run import RunConfig
        self.assertFalse(RunConfig().compiled_forward)
        self.assertTrue(RunConfig(compiled_forward=True).compiled_forward)
        with self.assertRaisesRegex(ValueError, "compiled_forward must be Boolean"):
            RunConfig(compiled_forward="yes")

    def test_buckets_hold_every_count_with_at_most_a_third_more(self):
        self.assertEqual(list(STATE_BUCKETS), sorted(STATE_BUCKETS))
        for count in range(1, 700):
            size = state_bucket(count)
            self.assertGreaterEqual(size, count)
            if count > 2:
                self.assertLessEqual(size, count * 4 / 3 + 1, count)

    def test_the_averaging_matrix_takes_each_zones_mean_of_its_messages(self):
        model = self.model
        sent = torch.randn(3, len(model.edge_source), 5)
        zones = model.border_average.shape[0]
        expected = torch.zeros(3, zones, 5).index_add_(1, model.edge_target, sent)
        degree = torch.bincount(model.edge_target, minlength=zones).clamp(min=1).view(1, zones, 1)
        torch.testing.assert_close(torch.matmul(model.border_average, sent), expected / degree)

    def test_compiled_layers_answer_as_written_with_padded_states(self):
        eager = NetworkStack([self.model])
        compiled = NetworkStack([self.model], compiled=True)
        self.assertTrue(compiled.compiled)
        with torch.inference_mode():
            # 3 states fill their bucket; 5 are padded to 6 with empty states.
            for count in (3, 5):
                items = self.items[:count]
                self.assertIn(state_bucket(count), (3, 6))
                want_scores, want_values = eager.forward_packed(batch_of(items))
                got_scores, got_values = compiled.forward_packed(batch_of(items))
                torch.testing.assert_close(got_scores, want_scores, rtol=0, atol=1e-5)
                torch.testing.assert_close(got_values, want_values, rtol=0, atol=1e-5)
        # New weights copied in are read by the stack built next, as the inference
        # server builds one after each network update, with no new compilation.
        with torch.no_grad():
            for parameter in self.model.parameters():
                parameter.add_(0.01)
        with torch.inference_mode():
            want_scores, want_values = NetworkStack([self.model]).forward_packed(batch_of(self.items[:3]))
            got_scores, got_values = NetworkStack([self.model], compiled=True).forward_packed(batch_of(self.items[:3]))
        torch.testing.assert_close(got_values, want_values, rtol=0, atol=1e-5)
        torch.testing.assert_close(got_scores, want_scores, rtol=0, atol=1e-5)

    def test_only_one_network_compiles_and_training_runs_as_written(self):
        three = [CampaignPolicyValueNet(self.model.config).eval() for _ in range(3)]
        self.assertFalse(NetworkStack(three, compiled=True).compiled)
        # A network's own pass, which training uses, runs the layers as written, and its
        # gradients reach the parameters through the fixed averaging matrix.
        env = restore(self.decisions[0])
        logits, values = self.model.forward_batch([make_zone_input(env, tuple(env.legal_actions()))])
        (logits[0].sum() + values.sum()).backward()
        self.assertGreater(float(self.model.messages[0].weight.grad.abs().sum()), 0.0)
        self.assertTrue(all(parameter.grad is None or torch.isfinite(parameter.grad).all()
                            for parameter in self.model.parameters()))
        self.model.zero_grad(set_to_none=True)


if __name__ == "__main__":
    unittest.main()
