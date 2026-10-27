"""Full native RNG-install contract with the parallel whole-arena copy."""
from dataclasses import replace
import unittest
from unittest.mock import patch

import torch

from studies.campaign.backends.device_state import DeviceStateContext
from studies.campaign.backends.packed_chance_metal import sample_packed_chance
from studies.campaign.backends.resident_chance_io import install_sampled_randomness
from tests import test_campaign_resident_chance_io as original
from tests.test_campaign_packed_chance import chance_env
from tests.test_campaign_random_metal import request, die, streams


class ParallelChanceRandomnessTests(original.ResidentChanceIOTests):
    def capture(self, envs):
        def context(native, device):
            return DeviceStateContext(native, device, editor_implementation="parallel")
        with patch.object(original, "DeviceStateContext", side_effect=context):
            return super().capture(envs)

    def test_reference_and_parallel_preserve_every_padding_and_random_word(self):
        before, _ = self.capture([
            chance_env(request([die(12)]), streams(actual=(1 << 64)-1)),
            chance_env(request([die(12)]), streams(search=1 << 63, active="search")),
            chance_env(request([die(12)]), streams(training=(1 << 63)+17, active="training")),
        ])
        sentinel = torch.tensor([-(1 << 63), (1 << 63)-1, -17, 1 << 62, 0],
                                dtype=torch.int64, device="mps")
        padding = sentinel.expand(3, 2048, 5).contiguous()
        after = replace(before, records=torch.cat((before.records, padding), dim=1))
        sampled = sample_packed_chance(before, dice_capacity=1, roll_capacity=1)
        snapshots = (before.records.clone(), after.records.clone())
        for selected in (None, torch.tensor([False, True, True], device="mps")):
            reference = install_sampled_randomness(before, after, sampled, selected, implementation="reference")
            parallel = install_sampled_randomness(before, after, sampled, selected, implementation="parallel")
            for name in ("errors", "accepted", "committed"):
                self.assertTrue(torch.equal(getattr(reference, name), getattr(parallel, name)), name)
            self.assert_same(reference.state, parallel.state)
            self.assertTrue(torch.equal(parallel.state.records[:, -2048:], padding))
        self.assertTrue(torch.equal(before.records, snapshots[0]))
        self.assertTrue(torch.equal(after.records, snapshots[1]))

    def test_implementation_selection_rejects_unknown_values(self):
        before, _ = self.capture([chance_env(request([die()]), streams())])
        sampled = sample_packed_chance(before, dice_capacity=1, roll_capacity=1)
        for invalid in ("cuda", "automatic", [], 1):
            with self.assertRaisesRegex(ValueError, "implementation"):
                install_sampled_randomness(before, before, sampled, implementation=invalid)


if __name__ == "__main__":
    unittest.main()
