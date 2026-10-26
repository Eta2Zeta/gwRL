"""Exact native stream/dice conformance for the Apple GPU sampler."""
import json
import random
import unittest
from dataclasses import replace

import torch
import gwrl_cpp

from studies.campaign.backends.random_metal import (
    MASK64, STREAMS, inspect_sampled_chance, pack_chance_requests,
    pack_random_streams, sample_chance_metal,
)
from studies.campaign.backends.tensor_rules import effective_results, inspect_outcomes


def request(dice):
    return dict(id='sample', purpose='probe', nation='japan', continuation='probe', dice=dice)


def die(sides=12, modifier=0, maximum=0, rerolls=()):
    return dict(sides=sides, modifier=modifier, max_rerolls=maximum, reroll_faces=list(rerolls))


def streams(actual=0, search=1, training=2, active='actual', tape=(), position=0):
    return dict(actual=str(actual), search=str(search), training=str(training), active=active,
                test_tape=list(tape), tape_position=str(position))


class RandomPackingTests(unittest.TestCase):
    def test_all_unsigned_bits_and_empty_shapes_preserved(self):
        packed = pack_random_streams([streams(MASK64, 1 << 63, 0)])
        self.assertEqual(packed.streams.tolist(), [[-1, -(1 << 63), 0]])
        self.assertEqual(tuple(packed.test_tape.shape), (1, 0))
        self.assertEqual(tuple(pack_random_streams([]).streams.shape), (0, 3))
        self.assertEqual(tuple(pack_chance_requests([]).faces.shape), (0, 0, 0))

    def test_exact_counter_and_tape_schema_validation(self):
        for change in ({'actual': '00'}, {'actual': str(1 << 64)}, {'actual': True},
                       {'actual': '١'}, {'active': 'unknown'}, {'test_tape': [False]},
                       {'test_tape': [0]}, {'tape_position': '1'}, {'unknown': 1}):
            with self.subTest(change=change), self.assertRaises((ValueError, TypeError)):
                pack_random_streams([{**streams(), **change}])

    def test_actual_full_reroll_capacity_without_fixed_limit(self):
        batch = pack_chance_requests([request([die(maximum=33, rerolls=[1])]), request([])])
        self.assertEqual(tuple(batch.faces.shape), (2, 1, 34))
        self.assertEqual(batch.dice_counts.tolist(), [1, 0])
        with self.assertRaises(OverflowError):
            pack_chance_requests([request([die(maximum=(1 << 31)-1)])])

    def test_no_implicit_cpu_sampler(self):
        with self.assertRaisesRegex(ValueError, 'requires Apple'):
            sample_chance_metal(pack_chance_requests([request([])]), pack_random_streams([streams()]))


@unittest.skipUnless(torch.backends.mps.is_available(), 'Apple GPU unavailable')
class MetalRandomConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def compare_native(self, requests, initial):
        oracle = gwrl_cpp.campaign_sample_chance_probe(
            [json.dumps(row) for row in requests], [json.dumps(row) for row in initial])['rows']
        spec = pack_chance_requests(requests, device='mps')
        random_state = pack_random_streams(initial, device='mps')
        before = [value.cpu().clone() for value in (random_state.streams, random_state.tape_positions, spec.faces)]
        result = sample_chance_metal(spec, random_state)
        actual = inspect_sampled_chance(result)
        for lane, (got, expected) in enumerate(zip(actual, oracle)):
            with self.subTest(lane=lane):
                self.assertEqual(got['random'], json.loads(expected['random']))
                self.assertEqual(got['error'] == 0, expected['error'] == '')
                if got['error'] == 0:
                    self.assertEqual(got['faces'], expected['faces'])
                    self.assertEqual(got['effective'], expected['effective'])
                else:
                    self.assertTrue(all(value == 0 for value in got['effective']))
        for old, value in zip(before, (random_state.streams, random_state.tape_positions, spec.faces)):
            self.assertTrue(torch.equal(old, value.cpu()), 'Sampler mutated input')
        return spec, random_state, result

    def test_all_streams_large_values_mixed_sides_and_rerolls(self):
        rng = random.Random(9187)
        requests, initial = [], []
        for lane in range(96):
            dice = [die(rng.choice([2, 3, 6, 12, 20, (1 << 31)-1]), rng.randrange(-20, 20),
                        rng.randrange(4), [1, 2]) for _ in range(lane % 9)]
            requests.append(request(dice))
            initial.append(streams(*(rng.getrandbits(64) for _ in range(3)), active=STREAMS[lane % 3]))
        _, _, result = self.compare_native(requests, initial)
        checked = inspect_outcomes(effective_results(result.dice))
        for sampled, validated in zip(inspect_sampled_chance(result), checked):
            self.assertEqual(tuple(sampled['effective']), validated['effective'])
            self.assertEqual(validated['errors'], 0)

    def test_rejected_uniform_draw_consumes_next_native_state(self):
        # SplitMix output is exactly zero when incremented state is zero.
        # A three-sided die rejects zero because uint64(-3)%3 == 1.
        initial = streams(actual=(-0x9e3779b97f4a7c15) & MASK64)
        _, _, result = self.compare_native([request([die(3)])], [initial])
        row = inspect_sampled_chance(result)[0]
        self.assertEqual(row['random']['actual'], str(0x9e3779b97f4a7c15))

    def test_test_tape_rerolls_cursor_and_atomic_failure(self):
        requests = [request([die(6, maximum=2, rerolls=[1, 2]), die(12)]),
                    request([die(12), die(12)]), request([die(6)]),
                    request([die(12, modifier=(1 << 31)-1)])]
        initial = [streams(tape=[6, 1, 2, 5, 12], position=1),
                   streams(tape=[4]), streams(tape=[12]), streams(tape=[1])]
        _, _, result = self.compare_native(requests, initial)
        rows = inspect_sampled_chance(result)
        self.assertEqual(rows[0]['faces'], [[1, 2, 5], [12]])
        self.assertEqual(rows[0]['random']['tape_position'], '5')
        self.assertTrue(all(row['error'] for row in rows[1:]))

    def test_continued_resident_state_matches_uninterrupted_native_sequence(self):
        q = request([die(12, maximum=1, rerolls=[1, 2]), die(6)])
        spec = pack_chance_requests([q], device='mps')
        state = pack_random_streams([streams(MASK64, 7, 8)], device='mps')
        native_state = streams(MASK64, 7, 8)
        for _ in range(20):
            oracle = gwrl_cpp.campaign_sample_chance_probe([json.dumps(q)], [json.dumps(native_state)])['rows'][0]
            result = sample_chance_metal(spec, state)
            got = inspect_sampled_chance(result)[0]
            self.assertEqual(got['faces'], oracle['faces'])
            self.assertEqual(got['random'], json.loads(oracle['random']))
            state, native_state = result.random, got['random']

    def test_empty_batch_and_forged_metadata_preserve_inputs(self):
        result = sample_chance_metal(pack_chance_requests([], device='mps'), pack_random_streams([], device='mps'))
        self.assertEqual(inspect_sampled_chance(result), ())
        spec = pack_chance_requests([request([die()])], device='mps')
        state = pack_random_streams([streams()], device='mps')
        for invalid in (replace(state, active=torch.tensor([3], dtype=torch.int32, device='mps')),
                        replace(state, tape_positions=torch.tensor([1], dtype=torch.int64, device='mps')),
                        replace(state, test_tape=torch.tensor([[1, 0]], dtype=torch.int32, device='mps'),
                                tape_counts=torch.tensor([2], dtype=torch.int32, device='mps'))):
            output = sample_chance_metal(spec, invalid)
            self.assertNotEqual(output.errors.cpu().item(), 0)
            self.assertTrue(torch.equal(output.random.streams.cpu(), invalid.streams.cpu()))
        invalid_spec = replace(spec, max_rerolls=torch.tensor([[1]], dtype=torch.int32, device='mps'))
        output = sample_chance_metal(invalid_spec, state)
        self.assertNotEqual(output.errors.cpu().item(), 0)


if __name__ == '__main__':
    unittest.main()
