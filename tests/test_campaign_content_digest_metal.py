import hashlib
import random
import unittest
from dataclasses import replace
from unittest.mock import patch

import torch
import gwrl_cpp
from studies.campaign.backends.content_digest_metal import pack_messages,content_digests_metal,inspect_digests


class DigestPackingTests(unittest.TestCase):
    def test_bytes_and_empty_messages_remain_distinct(self):
        batch=pack_messages([b'',b'\x00',b'abc',b''])
        self.assertEqual(batch.data.tolist(),[0,97,98,99])
        self.assertEqual(batch.offsets.tolist(),[0,0,1,4,4])
        with self.assertRaises(TypeError):pack_messages(['implicit Unicode'])
        with self.assertRaisesRegex(ValueError,'Apple GPU'):content_digests_metal(batch)


@unittest.skipUnless(torch.backends.mps.is_available(),'Apple GPU unavailable')
class MetalDigestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(2)

    def test_native_and_hashlib_for_boundaries_unicode_and_all_bytes(self):
        rng=random.Random(1936)
        data=[b'',b'abc',b'\x00',bytes(range(256)),'蒙古 / Ma Clique'.encode(),b'\xff\x80\x00']
        data += [rng.randbytes(n) for n in [1,7,55,56,63,64,65,111,112,119,120,127,128,129,1000,10000]]
        native=gwrl_cpp.campaign_content_digest_probe(data)['digests']
        self.assertEqual(native,[hashlib.sha256(row).hexdigest() for row in data])
        batch=pack_messages(data,device='mps')
        with patch.object(torch.Tensor,'cpu',side_effect=AssertionError('host read')), \
             patch.object(torch.Tensor,'tolist',side_effect=AssertionError('host list')), \
             patch.object(torch.Tensor,'item',side_effect=AssertionError('host scalar')):
            result=content_digests_metal(batch)
        self.assertEqual(inspect_digests(result),tuple(native))
        for words,value in zip(result.words.cpu().tolist(),native):
            self.assertEqual(''.join(f'{word&0xffffffff:08x}' for word in words),value)

    def test_actual_count_masks_spare_capacity_and_rejects_bad_ranges(self):
        batch=pack_messages([b'abc',b'wrong'],device='mps')
        result=content_digests_metal(replace(batch,count=torch.tensor([1],dtype=torch.int64,device='mps')))
        self.assertEqual(inspect_digests(result),(hashlib.sha256(b'abc').hexdigest(),))
        self.assertEqual(result.hex_bytes[1].cpu().tolist(),[0]*64)
        bad=replace(batch,offsets=torch.tensor([0,999,1000],dtype=torch.int64,device='mps'))
        result=content_digests_metal(bad)
        with self.assertRaisesRegex(ValueError,'offsets'):inspect_digests(result)
        self.assertTrue(all(result.errors.cpu().tolist()))

    def test_empty_count_and_invalid_empty_count_are_reported(self):
        batch=pack_messages([],device='mps')
        self.assertEqual(inspect_digests(content_digests_metal(batch)),())
        forged=replace(batch,count=torch.tensor([1],dtype=torch.int64,device='mps'))
        with self.assertRaisesRegex(ValueError,'count'):inspect_digests(content_digests_metal(forged))


if __name__=='__main__':unittest.main()
