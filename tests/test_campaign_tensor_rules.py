"""Integer dice-kernel conformance; no claim of full GPU game execution."""
from __future__ import annotations

from dataclasses import fields, replace
import json
import os
import random
import unittest
from unittest.mock import patch

import gwrl_cpp
import torch

from studies.campaign.backends.tensor_rules import (
    DiceError, INT32_MAX, INT32_MIN, effective_results, inspect_outcomes, pack_outcomes,
)


def request(dice):
    return {"id": "conformance", "purpose": "conformance", "nation": "japan",
            "continuation": "no-game-mutated", "dice": dice}


def die(sides=12, modifier=0, reroll_faces=(), max_rerolls=0):
    return {"sides": sides, "modifier": modifier, "reroll_faces": list(reroll_faces), "max_rerolls": max_rerolls}


def scalar_results(specification, outcome):
    """Independent scalar oracle, including unbounded Python-integer overflow check."""
    dice = specification["dice"]
    if len(dice) != len(outcome):
        raise ValueError("dice count")
    values = []
    for spec, path in zip(dice, outcome, strict=True):
        sides, maximum = spec["sides"], spec["max_rerolls"]
        rerolls = set(spec["reroll_faces"])
        if sides < 2 or maximum < 0 or any(face <= 0 or face > sides for face in rerolls):
            raise ValueError("specification")
        if not path or len(path) > maximum + 1:
            raise ValueError("roll count")
        for index, face in enumerate(path):
            if not 1 <= face <= sides:
                raise ValueError("face range")
            if (face in rerolls and index < maximum) != (index < len(path) - 1):
                raise ValueError("conditional reroll")
        value = path[-1] + spec["modifier"]
        if not INT32_MIN <= value <= INT32_MAX:
            raise ValueError("overflow")
        values.append(value)
    return tuple(values)


def valid_corpus():
    rng = random.Random(26931)
    requests, outcomes = [], []
    for lane in range(96):
        specs, rolls = [], []
        for _ in range(lane % 9):
            sides = rng.choice((2, 6, 12, 20, INT32_MAX))
            maximum = rng.randrange(3)
            rerolls = sorted(rng.sample(range(1, min(sides, 12) + 1), rng.randrange(3)))
            path = []
            for index in range(maximum + 1):
                face = rng.randint(1, sides)
                path.append(face)
                if face not in rerolls:
                    break
            modifier = rng.choice((0, -5, 8, INT32_MIN, INT32_MAX - path[-1]))
            specs.append(die(sides, modifier, rerolls, maximum))
            rolls.append(path)
        requests.append(request(specs)); outcomes.append(rolls)
    requests.extend([request([die(6, 3, [1], 2), die(12, -2)]),
                     request([die(12, INT32_MIN), die(INT32_MAX, 0), die(12, INT32_MAX - 1)])])
    outcomes.extend([[[1, 1, 6], [12]], [[1], [INT32_MAX], [1]]])
    return requests, outcomes


class TensorDiceRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def test_cpu_results_match_independent_scalar_oracle_and_leave_inputs_unchanged(self):
        requests, outcomes = valid_corpus()
        batch = pack_outcomes(requests, outcomes)
        before = {field.name: getattr(batch, field.name).clone() for field in fields(batch)}
        actual = inspect_outcomes(effective_results(batch))
        self.assertEqual(len(actual), len(requests))
        for row, spec, faces in zip(actual, requests, outcomes, strict=True):
            self.assertTrue(row["valid"], row)
            self.assertEqual(row["effective"], scalar_results(spec, faces))
            self.assertEqual(set(row["die_errors"]), {0} if faces else set())
        for field in fields(batch):
            self.assertTrue(torch.equal(getattr(batch, field.name), before[field.name]), field.name)

    def test_invalid_counts_specs_faces_rerolls_and_overflow_are_device_error_masks(self):
        cases = [(request([die()]), [], DiceError.DICE_COUNT),
                 (request([die()]), [[1], [2]], DiceError.DICE_COUNT),
                 (request([die(1)]), [[1]], DiceError.SPECIFICATION),
                 (request([die(max_rerolls=-1)]), [[1]], DiceError.SPECIFICATION),
                 (request([die(reroll_faces=[0])]), [[1]], DiceError.SPECIFICATION),
                 (request([die(reroll_faces=[13])]), [[1]], DiceError.SPECIFICATION),
                 (request([die()]), [[]], DiceError.ROLL_COUNT),
                 (request([die()]), [[1, 2]], DiceError.ROLL_COUNT),
                 (request([die()]), [[0]], DiceError.FACE_RANGE),
                 (request([die()]), [[13]], DiceError.FACE_RANGE),
                 (request([die(6, 0, [1], 1)]), [[1]], DiceError.REROLL_PATH),
                 (request([die(6, 0, [1], 2)]), [[2, 3]], DiceError.REROLL_PATH),
                 (request([die(12, INT32_MAX)]), [[1]], DiceError.RESULT_OVERFLOW)]
        actual = inspect_outcomes(effective_results(pack_outcomes([c[0] for c in cases], [c[1] for c in cases])))
        for row, (spec, outcome, expected) in zip(actual, cases, strict=True):
            self.assertFalse(row["valid"], row)
            self.assertTrue(row["errors"] & int(expected), (row, expected))
            self.assertEqual(set(row["effective"]), {0} if spec["dice"] else set())
            with self.assertRaises(ValueError):
                scalar_results(spec, outcome)

    def test_padding_is_ignored_and_direct_invalid_tensor_counts_are_rejected(self):
        batch = pack_outcomes([request([die()]), request([die(6, 0, [1], 2), die()])],
                              [[[12]], [[1, 1, 6], [2]]])
        batch.sides[0, 1] = -99
        batch.max_rerolls[0, 1] = -99
        batch.faces[0, 1] = -99
        batch.faces[0, 0, 1:] = INT32_MIN
        self.assertTrue(all(row["valid"] for row in inspect_outcomes(effective_results(batch))))
        for name, value, expected in (("dice_counts", -1, DiceError.DICE_COUNT),
                                       ("dice_counts", 99, DiceError.DICE_COUNT),
                                       ("outcome_counts", 99, DiceError.DICE_COUNT)):
            tensor = getattr(batch, name).clone(); tensor[0] = value
            row = inspect_outcomes(effective_results(replace(batch, **{name: tensor})))[0]
            self.assertTrue(row["errors"] & int(expected))
        for name, value in (("face_counts", -1), ("face_counts", 99), ("reroll_counts", -1), ("reroll_counts", 99)):
            tensor = getattr(batch, name).clone(); tensor[1, 0] = value
            row = inspect_outcomes(effective_results(replace(batch, **{name: tensor})))[1]
            self.assertFalse(row["valid"], name)

    def test_empty_batches_and_empty_generic_requests_are_not_padded_fake_dice(self):
        empty = pack_outcomes([], [])
        result = effective_results(empty)
        self.assertEqual(tuple(result.effective.shape), (0, 0))
        self.assertEqual(inspect_outcomes(result), ())
        self.assertEqual(inspect_outcomes(effective_results(pack_outcomes([request([])], [[]]))),
                         ({"valid": True, "errors": 0, "effective": (), "die_errors": ()},))

    def test_host_packing_rejects_coercion_overflow_duplicate_sets_and_unavailable_devices(self):
        for face in (True, 1.0, "1", INT32_MAX + 1, INT32_MIN - 1):
            with self.subTest(face=face), self.assertRaises((TypeError, OverflowError)):
                pack_outcomes([request([die()])], [[[face]]])
        with self.assertRaises(ValueError):
            pack_outcomes([request([die(reroll_faces=[1, 1])])], [[[2]]])
        with self.assertRaises(ValueError):
            pack_outcomes([request([die()])], [])
        with self.assertRaises(ValueError):
            pack_outcomes([], [], device="meta")
        if not torch.cuda.is_available():
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                pack_outcomes([], [], device="cuda")
        batch = pack_outcomes([request([die()])], [[[2]]])
        with self.assertRaises(ValueError):
            effective_results(replace(batch, modifiers=batch.modifiers.to(torch.float32)))
        with self.assertRaises(ValueError):
            effective_results(replace(batch, face_counts=torch.zeros(2, 1, dtype=torch.int32)))
        with self.assertRaises(TypeError):
            effective_results(replace(batch, faces=[]))

    def test_direct_device_duplicate_reroll_set_is_flagged_without_host_inspection(self):
        batch = pack_outcomes([request([die(12, 0, [1, 2], 1)])], [[[12]]])
        batch.reroll_faces[0, 0, 1] = 1
        result = effective_results(batch)
        self.assertTrue(inspect_outcomes(result)[0]["errors"] & int(DiceError.SPECIFICATION))

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS is unavailable")
    def test_actual_mps_results_and_errors_are_bit_exact_with_cpu_and_stay_on_device(self):
        requests, outcomes = valid_corpus()
        requests.extend([request([die(12, INT32_MAX)]), request([die(12, 0, [1], 1)])])
        outcomes.extend([[[12]], [[1]]])
        batch = pack_outcomes(requests, outcomes)
        expected = effective_results(batch)
        with patch.object(torch.Tensor, "item", side_effect=AssertionError("host scalar read")), \
             patch.object(torch.Tensor, "tolist", side_effect=AssertionError("host list read")), \
             patch.object(torch.Tensor, "cpu", side_effect=AssertionError("host tensor copy")):
            actual = effective_results(batch.to("mps"))
            self.assertEqual(actual.effective.device.type, "mps")
            self.assertEqual(actual.lane_errors.device.type, "mps")
        for field in fields(expected):
            self.assertTrue(torch.equal(getattr(actual, field.name).cpu(), getattr(expected, field.name)), field.name)

    @unittest.skipUnless(torch.backends.mps.is_available(), "MPS is unavailable")
    def test_direct_mps_tensor_calls_reject_fallback_instead_of_running_on_cpu(self):
        batch = pack_outcomes([request([die()])], [[[12]]], device="mps")
        with patch.dict(os.environ, {"PYTORCH_ENABLE_MPS_FALLBACK": "1"}):
            with self.assertRaisesRegex(RuntimeError, "fallback"):
                effective_results(batch)

    @unittest.skipUnless(hasattr(gwrl_cpp, "campaign_effective_results_probe"), "Native probe requires rebuild")
    def test_full_native_results_match_cpu_and_mps_for_rerolls_and_modifier_bounds(self):
        requests, outcomes = valid_corpus()
        native = gwrl_cpp.campaign_effective_results_probe(
            [json.dumps(spec) for spec in requests], [json.dumps({"faces": face}) for face in outcomes], 2)
        self.assertEqual(native["lanes"], len(requests))
        self.assertEqual(native["repetitions"], 2)
        self.assertGreaterEqual(native["preparation_seconds"], 0)
        self.assertGreaterEqual(native["rules_seconds"], 0)
        for device in ("cpu", "mps") if torch.backends.mps.is_available() else ("cpu",):
            actual = inspect_outcomes(effective_results(pack_outcomes(requests, outcomes, device=device)))
            self.assertEqual([list(row["effective"]) for row in actual], native["results"])

    @unittest.skipUnless(hasattr(gwrl_cpp, "campaign_effective_results_probe"), "Native probe requires rebuild")
    def test_native_and_tensor_both_reject_malformed_counts_paths_specs_and_overflow(self):
        for spec, faces in ((die(), []), (die(), [0]), (die(), [13]), (die(), [1, 2]),
                            (die(1), [1]), (die(12, 0, [1], 1), [1]),
                            (die(12, 0, [1], 2), [2, 3]), (die(12, INT32_MAX), [1])):
            req, outcome = request([spec]), [faces]
            with self.subTest(spec=spec, faces=faces):
                with self.assertRaises(RuntimeError):
                    gwrl_cpp.campaign_effective_results_probe([json.dumps(req)], [json.dumps({"faces": outcome})])
                self.assertFalse(inspect_outcomes(effective_results(pack_outcomes([req], [outcome])))[0]["valid"])
        for repetitions in (True, 0, -1, 1000001, 1.5):
            with self.subTest(repetitions=repetitions), self.assertRaises((TypeError, ValueError)):
                gwrl_cpp.campaign_effective_results_probe([], [], repetitions)


if __name__ == "__main__":
    unittest.main()
