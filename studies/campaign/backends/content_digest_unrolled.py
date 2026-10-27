"""Generated Metal SHA-256 rounds with a sixteen-word scalar schedule.

The compression function is sequential within each message. Independent messages
remain independent GPU threads; threadgroup sizing does not split a message or
alter its byte count. This is an explicit alternative to the reference kernel.
"""

ROUND_CONSTANTS = (
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
)


def _rounds():
    # Rotate compile-time register names instead of moving eight values every
    # round. After 64 rounds their original logical order is restored.
    registers = ("a", "b", "c", "d", "e", "f", "g", "z")
    lines = []
    for i, constant in enumerate(ROUND_CONSTANTS):
        word = f"w{i % 16}"
        if i >= 16:
            first, second, seventh = (f"w{(i - n) % 16}" for n in (15, 2, 7))
            lines.append(f"{word} += (digest_u_rotr({first},7)^digest_u_rotr({first},18)^({first}>>3))"
                         f" + {seventh} + (digest_u_rotr({second},17)^digest_u_rotr({second},19)^({second}>>10));")
        a, b, c, d, e, f, g, z = (registers[(j - i) % 8] for j in range(8))
        lines.append("{ const uint t1 = " + z + f" + (digest_u_rotr({e},6)^digest_u_rotr({e},11)^digest_u_rotr({e},25))"
                     f" + (({e}&{f})^((~{e})&{g})) + 0x{constant:08x}u + {word};"
                     f" const uint t2 = (digest_u_rotr({a},2)^digest_u_rotr({a},13)^digest_u_rotr({a},22))"
                     f" + (({a}&{b})^({a}&{c})^({b}&{c})); {d} += t1; {z} = t1+t2; }}")
    return "\n".join(lines)


_HEAD = r"""
#include <metal_stdlib>
using namespace metal;
constant char digest_u_hex[17]="0123456789abcdef";
inline uint digest_u_rotr(uint x,int n){return (x>>n)|(x<<(32-n));}
inline uint digest_u_byte(device const uchar* data,ulong start,ulong index,
                         ulong length,ulong total,ulong bits){
    if(index<length)return data[start+index];
    if(index==length)return 0x80;
    if(index>=total-8)return uint((bits>>(8*uint(total-1-index)))&255);
    return 0;
}
inline uint digest_u_word(device const uchar* data,ulong start,ulong index,
                         ulong length,ulong total,ulong bits,bool full){
    // Four uchar reads retain exact bytes for arbitrary, unaligned ranges.
    if(full)return (uint(data[start+index])<<24)|(uint(data[start+index+1])<<16)|
                   (uint(data[start+index+2])<<8)|uint(data[start+index+3]);
    return (digest_u_byte(data,start,index,length,total,bits)<<24)|
           (digest_u_byte(data,start,index+1,length,total,bits)<<16)|
           (digest_u_byte(data,start,index+2,length,total,bits)<<8)|
            digest_u_byte(data,start,index+3,length,total,bits);
}
inline void digest_u_store(device uint* words,device uchar* hex,ulong row,uint i,uint h){
    words[row*8+i]=h;
    for(uint digit=0;digit<8;++digit)
        hex[row*64+i*8+digit]=uchar(digest_u_hex[(h>>(28-4*digit))&15]);
}
kernel void content_digests_unrolled(device const uchar* data [[buffer(0)]],
    device const long* offsets [[buffer(1)]],device const long* count [[buffer(2)]],
    device uint* words [[buffer(3)]],device uchar* hex [[buffer(4)]],
    device int* errors [[buffer(5)]],device int* batch_error [[buffer(6)]],
    device const long* dimensions [[buffer(7)]],uint row [[thread_position_in_grid]]) {
    const long capacity=dimensions[0],bytes=dimensions[1],actual=count[0];
    const bool bad_count=actual<0||actual>capacity;
    if(row==0)batch_error[0]=bad_count?1:0;
    if(long(row)>=capacity)return;
    errors[row]=0;
    for(int i=0;i<8;++i)words[ulong(row)*8+ulong(i)]=0;
    for(int i=0;i<64;++i)hex[ulong(row)*64+ulong(i)]=0;
    if(bad_count){errors[row]=1;return;}
    if(long(row)>=actual)return;
    const bool ranged=dimensions[2]!=0;
    const long start=offsets[ranged?ulong(row)*2:ulong(row)],
               end=offsets[ranged?ulong(row)*2+1:ulong(row)+1];
    if(start<0||end<start||end>bytes){errors[row]=2;return;}
    const ulong length=ulong(end-start),bits=length*8;
    const ulong blocks=(length+9+63)/64,total=blocks*64;
    uint h0=0x6a09e667,h1=0xbb67ae85,h2=0x3c6ef372,h3=0xa54ff53a,
         h4=0x510e527f,h5=0x9b05688c,h6=0x1f83d9ab,h7=0x5be0cd19;
    for(ulong block=0;block<blocks;++block){
        const ulong base=block*64;const bool full=base+64<=length;
"""

_LOADS = "\n".join(f"uint w{i}=digest_u_word(data,ulong(start),base+{i * 4},length,total,bits,full);" for i in range(16))
_TAIL = r"""
        h0+=a;h1+=b;h2+=c;h3+=d;h4+=e;h5+=f;h6+=g;h7+=z;
    }
    digest_u_store(words,hex,row,0,h0);digest_u_store(words,hex,row,1,h1);
    digest_u_store(words,hex,row,2,h2);digest_u_store(words,hex,row,3,h3);
    digest_u_store(words,hex,row,4,h4);digest_u_store(words,hex,row,5,h5);
    digest_u_store(words,hex,row,6,h6);digest_u_store(words,hex,row,7,h7);
}
"""

UNROLLED_SOURCE = _HEAD + _LOADS + "\nuint a=h0,b=h1,c=h2,d=h3,e=h4,f=h5,g=h6,z=h7;\n" + _rounds() + _TAIL
