"""Exact native binary64 wealth/terminal arithmetic using integer Metal work.

Inputs are the five already rounded half-unit components from resident wealth.
No rational approximation or float32 intermediate substitutes for native scores.
The 0.1 product plus income is fused, as in the authoritative native expression.
Float32 training targets are rounded once from the resulting binary64 gap bits.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch


@dataclass(frozen=True)
class ResidentWealthScores:
    wealth_bits: torch.Tensor
    gap_bits: torch.Tensor
    terminal_bits: torch.Tensor
    terminal_targets: torch.Tensor
    errors: torch.Tensor
    terminal_errors: torch.Tensor
    context_identity: tuple | None


SOURCE = r'''
#include <metal_stdlib>
using namespace metal;
struct WealthWide { ulong hi; ulong lo; };
inline WealthWide ww_right_jam(WealthWide a, uint n) {
 if(!n)return a;
 if(n>=128)return {0,ulong(a.hi!=0||a.lo!=0)};
 if(n>=64){const uint k=n-64;const ulong lost=a.lo|(k?(a.hi&((ulong(1)<<k)-1)):0);
   return {0,(a.hi>>k)|ulong(lost!=0)};}
 return {a.hi>>n,(a.hi<<(64-n))|(a.lo>>n)|ulong((a.lo&((ulong(1)<<n)-1))!=0)};
}
inline WealthWide ww_left(WealthWide a,uint n){
 if(!n)return a;if(n>=128)return {0,0};if(n>=64)return {a.lo<<(n-64),0};
 return {(a.hi<<n)|(a.lo>>(64-n)),a.lo<<n};
}
inline WealthWide ww_add(WealthWide a,WealthWide b){const ulong lo=a.lo+b.lo;return {a.hi+b.hi+ulong(lo<a.lo),lo};}
inline WealthWide ww_sub(WealthWide a,WealthWide b){return {a.hi-b.hi-ulong(a.lo<b.lo),a.lo-b.lo};}
inline bool ww_less(WealthWide a,WealthWide b){return a.hi<b.hi||(a.hi==b.hi&&a.lo<b.lo);}
inline WealthWide ww_multiply(ulong a,ulong b){
 const ulong mask=0xffffffffUL,a0=a&mask,a1=a>>32,b0=b&mask,b1=b>>32;
 const ulong first=a0*b0,middle=a1*b0+(first>>32),last=a0*b1+(middle&mask);
 return {a1*b1+(middle>>32)+(last>>32),(last<<32)|(first&mask)};
}
inline ulong ws_sig(ulong bits){return (bits&0x000fffffffffffffUL)|0x0010000000000000UL;}
inline long ws_exp(ulong bits){return long((bits>>52)&2047)-1023;}
inline ulong ws_pack(WealthWide value,long exponent,bool negative,thread bool& valid){
 if(!(value.hi|value.lo))return 0;
 if(value.hi&0x8000000000000000UL){value=ww_right_jam(value,1);++exponent;}
 else {const uint highest=value.hi?127-uint(clz(value.hi)):63-uint(clz(value.lo));
   if(highest<126){const uint n=126-highest;value=ww_left(value,n);exponent-=long(n);}}
 // Half-integer inputs and the fixed tenth coefficient cannot produce a
 // nonzero subnormal or overflow in this bounded scoring domain.
 if(exponent<=-1023||exponent>=1024){valid=false;return 0;}
 ulong main=value.hi>>10;const bool guard=(value.hi&512)!=0,sticky=(value.hi&511)!=0||value.lo!=0;
 if(guard&&(sticky||(main&1)))++main;
 if(main==0x0020000000000000UL){main>>=1;++exponent;}
 if(exponent>=1024){valid=false;return 0;}
 return (ulong(negative)<<63)|(ulong(exponent+1023)<<52)|(main&0x000fffffffffffffUL);
}
inline ulong ws_half_integer(long number){
 const bool negative=number<0;const ulong magnitude=negative?ulong(0)-as_type<ulong>(number):ulong(number);
 if(!magnitude)return 0;long top=63-long(clz(magnitude));ulong main;
 if(top<=52)main=magnitude<<uint(52-top);
 else {const uint shift=uint(top-52);main=magnitude>>shift;
   const ulong remainder=magnitude&((ulong(1)<<shift)-1),midpoint=ulong(1)<<(shift-1);
   if(remainder>midpoint||(remainder==midpoint&&(main&1)))++main;
   if(main==0x0020000000000000UL){main>>=1;++top;}}
 return (ulong(negative)<<63)|(ulong(top+1022)<<52)|(main&0x000fffffffffffffUL);
}
inline ulong ws_add(ulong a,ulong b,thread bool& valid){
 const ulong aa=a&0x7fffffffffffffffUL,bb=b&0x7fffffffffffffffUL;
 if(!aa&&!bb)return ((a&b)>>63)<<63;if(!aa)return b;if(!bb)return a;
 if(aa<bb){const ulong t=a;a=b;b=t;}
 const long ea=ws_exp(a),eb=ws_exp(b);const bool sa=(a>>63)!=0,sb=(b>>63)!=0;
 WealthWide x={ws_sig(a)<<10,0},y=ww_right_jam({ws_sig(b)<<10,0},uint(ea-eb));
 return ws_pack(sa==sb?ww_add(x,y):ww_sub(x,y),ea,sa,valid);
}
inline ulong ws_tenth_fma(ulong a,ulong c,thread bool& valid){
 if(!(a&0x7fffffffffffffffUL))return c;
 WealthWide product=ww_multiply(ws_sig(a),0x001999999999999aUL);
 const bool carry=(product.hi&(ulong(1)<<41))!=0;
 long exponent=ws_exp(a)-4+long(carry);product=ww_left(product,carry?21:22);
 bool sign=(a>>63)!=0;
 if(c&0x7fffffffffffffffUL){
   const long ec=ws_exp(c);WealthWide addend={ws_sig(c)<<10,0};
   if(exponent<ec){product=ww_right_jam(product,uint(ec-exponent));exponent=ec;}
   else addend=ww_right_jam(addend,uint(exponent-ec));
   if(sign==((c>>63)!=0))product=ww_add(product,addend);
   else if(ww_less(product,addend)){product=ww_sub(addend,product);sign=(c>>63)!=0;}
   else product=ww_sub(product,addend);
 }
 return ws_pack(product,exponent,sign,valid);
}
inline uint ws_float32(ulong bits,thread bool& valid){
 if(!(bits&0x7fffffffffffffffUL))return uint(bits>>32)&0x80000000U;
 long exponent=ws_exp(bits);ulong main=ws_sig(bits)>>29;
 const ulong remainder=ws_sig(bits)&((ulong(1)<<29)-1),midpoint=ulong(1)<<28;
 if(remainder>midpoint||(remainder==midpoint&&(main&1)))++main;
 if(main==(ulong(1)<<24)){main>>=1;++exponent;}
 // The fixed tenth of half-integer assets is on a 2^-56 grid. Rounding
 // components/scores cannot introduce a smaller quantum. Bounded int64
 // components also keep all three-side gaps far below float32 overflow.
 if(exponent<=-127||exponent>=128){valid=false;return 0;}
 return (uint(bits>>32)&0x80000000U)|(uint(exponent+127)<<23)|(uint(main)&0x007fffffU);
}
kernel void wealth_native_scores(
 device const long* components[[buffer(0)]],device const long* source_errors[[buffer(1)]],
 device const long* source_terminal_errors[[buffer(2)]],device const long* terminal[[buffer(3)]],
 device long* wealth[[buffer(4)]],device long* gaps[[buffer(5)]],device long* returns[[buffer(6)]],
 device float* targets[[buffer(7)]],device long* errors[[buffer(8)]],device long* terminal_errors[[buffer(9)]],
 device const long* dims[[buffer(10)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0])return;bool valid=true;ulong values[3];
 for(long player=0;player<3;++player){device const long* x=components+(ulong(lane)*3+player)*5;
   ulong assets=ws_add(ws_half_integer(x[1]),ws_half_integer(x[2]),valid);
   assets=ws_add(assets,ws_half_integer(x[3]),valid);assets=ws_add(assets,ws_half_integer(x[4]),valid);
   values[player]=ws_tenth_fma(assets,ws_half_integer(x[0]),valid);}
 const ulong sum=ws_add(ws_add(values[0],values[1],valid),values[2],valid);
 for(long player=0;player<3;++player){const ulong value=values[player];ulong twice=value;
   if(value&0x7fffffffffffffffUL)twice=value+(ulong(1)<<52);
   const ulong gap=ws_add(twice,sum^(ulong(1)<<63),valid),result=terminal[lane]?gap:0;
   const ulong row=ulong(lane)*3+player;wealth[row]=as_type<long>(value);gaps[row]=as_type<long>(gap);
   returns[row]=as_type<long>(result);targets[row]=as_type<float>(ws_float32(result,valid));}
 errors[lane]=source_errors[lane]?source_errors[lane]:(valid?0:4);
 terminal_errors[lane]=source_terminal_errors[lane]?source_terminal_errors[lane]:((terminal[lane]&&!valid)?4:0);
}
'''

_lock = threading.Lock()
_library = None


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:
                _library = torch.mps.compile_shader(SOURCE)
    return _library


@lru_cache(maxsize=16)
def _dimensions(count):
    return torch.tensor([count], dtype=torch.int64, device="mps")


def native_wealth_scores(components_twice, errors, terminal_errors, terminal, *, context_identity=None):
    """Preserve raw native scores, with explicit once-rounded training targets."""
    if (not isinstance(components_twice, torch.Tensor) or components_twice.ndim != 3
            or tuple(components_twice.shape[1:]) != (3, 5)):
        raise ValueError("Wealth scoring requires complete [lane,3,5] components")
    B = components_twice.shape[0]
    for tensor, shape in ((components_twice, (B, 3, 5)), (errors, (B,)),
                          (terminal_errors, (B,)), (terminal, (B,))):
        if (not isinstance(tensor, torch.Tensor) or tensor.device.type != "mps" or tensor.dtype != torch.int64
                or tensor.shape != shape or not tensor.is_contiguous()):
            raise ValueError("Wealth scoring requires contiguous resident Apple int64 buffers")
    allocate = lambda *shape: torch.empty(shape, dtype=torch.int64, device=components_twice.device)
    wealth, gaps, returns, output_errors, output_terminal_errors = (
        allocate(B, 3), allocate(B, 3), allocate(B, 3), allocate(B), allocate(B))
    targets = torch.empty((B, 3), dtype=torch.float32, device=components_twice.device)
    if B:
        _kernels().wealth_native_scores(components_twice, errors, terminal_errors, terminal, wealth, gaps, returns,
            targets, output_errors, output_terminal_errors, _dimensions(B), threads=B)
    return ResidentWealthScores(wealth, gaps, returns, targets, output_errors, output_terminal_errors, context_identity)
