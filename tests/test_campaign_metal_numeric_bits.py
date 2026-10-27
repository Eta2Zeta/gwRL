"""Exact generated JSON integer payloads without a float64 GPU conversion."""
import random
import math
import struct
import unittest
from unittest.mock import patch

import torch
from studies.campaign.backends.metal_state_schema import METAL_STATE_SOURCE
from studies.campaign.backends.metal_validation import mps_int64_indexing_supported

EXACT_MPS=torch.backends.mps.is_available() and mps_int64_indexing_supported()
SOURCE=r'''
#include <metal_stdlib>
using namespace metal;
'''+METAL_STATE_SOURCE+r'''
kernel void numeric_bits(device const long* input[[buffer(0)]],device long* output[[buffer(1)]],
                        device long* errors[[buffer(2)]],uint i[[thread_position_in_grid]]) {
    bool valid=true;const ulong bits=state_json_integer_bits(input[i],valid);
    output[ulong(i)*2]=long(bits&0xffffffffUL);output[ulong(i)*2+1]=long(bits>>32);
    errors[i]=valid?0:1;
}
kernel void numeric_values(device const long* words[[buffer(0)]],device long* output[[buffer(1)]],
                          device long* errors[[buffer(2)]],uint i[[thread_position_in_grid]]) {
    const ulong bits=ulong(words[ulong(i)*2])|(ulong(words[ulong(i)*2+1])<<32);
    long value=0;const bool valid=state_json_integer_value(bits,value);
    output[i]=valid?value:0;errors[i]=valid?0:1;
}
'''


@unittest.skipUnless(EXACT_MPS,'Lossless Apple GPU runtime unavailable')
class MetalNumericBitsTests(unittest.TestCase):
    def test_decode_matches_native_as_int_domain_for_arbitrary_binary64(self):
        rng=random.Random(82)
        values=[0.,-0.,1.,-1.,.5,-.5,2**31-1.,float(-2**31),float(2**31),float(-2**31-1),
                1.0000000000000002,2**24+1.,float('nan'),float('inf'),float('-inf')]
        bits=[struct.unpack('<Q',struct.pack('<d',v))[0] for v in values]
        bits.extend(rng.getrandbits(64) for _ in range(2048))
        words=torch.tensor([[v&0xffffffff,v>>32] for v in bits],dtype=torch.int64,device='mps')
        output=torch.empty(len(bits),dtype=torch.int64,device='mps');errors=torch.empty_like(output)
        torch.mps.compile_shader(SOURCE).numeric_values(words,output,errors,threads=len(bits))
        actual,fail=output.cpu().tolist(),errors.cpu().tolist()
        for raw,result,error in zip(bits,actual,fail,strict=True):
            value=struct.unpack('<d',raw.to_bytes(8,'little'))[0]
            valid=math.isfinite(value) and -2**31<=value<=2**31-1 and math.floor(value)==value
            self.assertEqual(error,not valid,hex(raw))
            self.assertEqual(result,int(value) if valid else 0,hex(raw))

    def test_every_sign_exponent_boundary_and_random_int32_value_is_exact(self):
        rng=random.Random(1936)
        values=[0,-1,1,-2**31,2**31-1]
        for exponent in range(31):
            for offset in (-1,0,1):
                value=2**exponent+offset
                if value<2**31:values.extend((value,-value))
        values.extend(rng.randint(-2**31,2**31-1) for _ in range(1024))
        data=torch.tensor(values,dtype=torch.int64,device='mps')
        output=torch.empty((len(values),2),dtype=torch.int64,device='mps')
        errors=torch.empty(len(values),dtype=torch.int64,device='mps')
        library=torch.mps.compile_shader(SOURCE)
        with patch.object(torch.Tensor,'cpu',side_effect=AssertionError('host read')), \
             patch.object(torch.Tensor,'tolist',side_effect=AssertionError('host list')), \
             patch.object(torch.Tensor,'item',side_effect=AssertionError('host scalar')):
            library.numeric_bits(data,output,errors,threads=len(values))
        self.assertEqual(errors.cpu().tolist(),[0]*len(values))
        for value,words in zip(values,output.cpu().tolist(),strict=True):
            expected=struct.unpack('<Q',struct.pack('<d',float(value)))[0]
            self.assertEqual(words[0]|(words[1]<<32),expected,value)

    def test_out_of_int32_range_is_an_error_without_overflow_or_rounding(self):
        values=[-2**63,-2**31-1,2**31,2**63-1]
        data=torch.tensor(values,dtype=torch.int64,device='mps')
        output=torch.empty((len(values),2),dtype=torch.int64,device='mps')
        errors=torch.empty(len(values),dtype=torch.int64,device='mps')
        torch.mps.compile_shader(SOURCE).numeric_bits(data,output,errors,threads=len(values))
        self.assertEqual(errors.cpu().tolist(),[1]*len(values))
        self.assertEqual(output.cpu().tolist(),[[0,0]]*len(values))
