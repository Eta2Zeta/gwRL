"""Complete read-only campaign wealth on packed Apple GPU state.

Components are stored as exact twice-native-component integers. Each component
addition emulates binary64 nearest-even rounding, including very large totals.
Legacy rational totals remain explicitly named. scores() computes exact native
binary64 totals/gaps and once-rounded float32 terminal targets entirely on Metal.
The original native fused multiply-add and component ordering are retained.
"""
from dataclasses import dataclass
from functools import lru_cache
import math
import threading

import torch

from .resident_state_income import ResidentIncomeContext
from .metal_state_schema import METAL_STATE_SOURCE

PLAYERS=("axis","allies","comintern")
COMPONENTS=("income_rate","units","infrastructure","treasury","paid_construction")


@dataclass(frozen=True)
class ResidentWealthResult:
    components_twice: torch.Tensor
    rational_wealth_twentieths: torch.Tensor
    rational_gaps_twentieths: torch.Tensor
    rational_terminal_twentieths: torch.Tensor
    errors: torch.Tensor
    terminal_errors: torch.Tensor
    terminal: torch.Tensor
    context_identity: tuple


SOURCE=r"""
#include <metal_stdlib>
using namespace metal;
"""+METAL_STATE_SOURCE+r"""
inline void wealth_fail(long code,thread bool& valid,thread long& error){valid=false;if(!error)error=code;}
inline bool wealth_container(thread const PackedStateView& v,long node,long tag,long count,thread bool& valid) {
    state_end(v,node,valid);if(!valid)return false;device const long* r=state_record(v,node);
    if(r[0]!=tag||r[1]<0||(count>=0&&r[1]!=count)||r[2]||r[3])valid=false;return valid;
}
inline long wealth_index(device const long* ids,long count,long id){for(long i=0;i<count;++i)if(ids[i]==id)return i;return -1;}
inline long wealth_int(thread const PackedStateView& v,long node,thread bool& valid){long x=state_signed_value(v,node,valid);
    if(x<(-2147483647L-1L)||x>2147483647L)valid=false;return x;}
inline bool wealth_add_long(long a,long b,thread long& result,thread bool& valid,thread long& error) {
    const long high=0x7fffffffffffffffL,low=(-0x7fffffffffffffffL-1L);
    if((b>0&&a>high-b)||(b<0&&a<low-b)){wealth_fail(4,valid,error);result=0;return false;}
    result=a+b;return true;
}
inline long wealth_int_domain(long value,thread bool& valid,thread long& error) {
    if(value<(-2147483647L-1L)||value>2147483647L)wealth_fail(4,valid,error);return value;
}
inline void wealth_add_component(thread long* values,long actor,long field,long amount,
                                  thread bool& valid,thread long& error) {
    if(!valid)return;long total;
    if(!wealth_add_long(values[actor*5+field],amount,total,valid,error))return;
    const bool negative=total<0;
    ulong magnitude=negative?ulong(0)-as_type<ulong>(total):ulong(total);
    if(magnitude){const uint bits=64-uint(clz(magnitude));
        if(bits>53){const uint shift=bits-53;const ulong mask=(ulong(1)<<shift)-1,rounding_half=ulong(1)<<(shift-1);
            ulong quotient=magnitude>>shift,remainder=magnitude&mask;
            if(remainder>rounding_half||(remainder==rounding_half&&(quotient&1)))++quotient;
            magnitude=quotient<<shift;}}
    if((!negative&&magnitude>0x7fffffffffffffffUL)||(negative&&magnitude>0x8000000000000000UL)){
        wealth_fail(4,valid,error);return;}
    values[actor*5+field]=as_type<long>(negative?ulong(0)-magnitude:magnitude);
}
inline long wealth_recipient(long owner,device const long* ids,long N,device const long* players,
                             thread bool& valid,thread long& error) {
    if(owner<0)return -1;const long n=wealth_index(ids,N,owner);
    if(n<0||players[n]==-3){wealth_fail(1,valid,error);return -1;}
    if(players[n]==-2){wealth_fail(2,valid,error);return -1;}return players[n];
}
inline long wealth_owner(thread const PackedStateView& v,long territories,long zone,
                         thread bool& valid,thread long& error) {
    const long t=state_map_find_id(v,territories,zone,valid);
    if(!valid)return -1;if(t<0){wealth_fail(1,valid,error);return -1;}
    wealth_container(v,t,10,2,valid);bool present=false;
    const long value=state_optional(v,state_child(v,t,0,valid),present,valid);
    return present?state_string_id(v,value,valid):-1;
}
inline bool wealth_crew_prefix(thread const PackedStateView& v,long key,thread bool& valid) {
    const long id=state_string_id(v,key,valid);if(!valid)return false;
    const bool prefix=id<v.prefix_count;const long local=prefix?id:id-v.prefix_count;
    device const long* offsets=prefix?v.prefix_offsets:v.suffix_offsets;
    device const uchar* bytes=prefix?v.prefix_bytes:v.suffix_bytes;
    const long start=offsets[local],end=offsets[local+1],capacity=prefix?v.prefix_bytes_length:v.suffix_bytes_length;
    if(start<0||end<start||end>capacity){valid=false;return false;}if(end-start<10)return false;
    constant char* text="ship_crew:";for(long i=0;i<10;++i)if(bytes[start+i]!=uchar(text[i]))return false;return true;
}
inline bool wealth_is_crew(thread const PackedStateView& v,long flags,thread bool& valid) {
    if(!wealth_container(v,flags,7,-1,valid))return false;
    long cursor=flags+1;const long end=state_end(v,flags,valid),count=state_record(v,flags)[1];
    if(count>(end-flags-1)/2){valid=false;return false;}
    for(long entry=0;valid&&entry<count;++entry){const bool crew=wealth_crew_prefix(v,cursor,valid);
        const long value=state_end(v,cursor,valid);const long active=wealth_int(v,value,valid);
        if(crew&&active)return true;cursor=state_end(v,value,valid);}
    if(valid&&cursor!=end)valid=false;return false;
}
inline long wealth_prepaid(thread const PackedStateView& v,long repairs,long target,long owner,long endpoint,
                           thread bool& valid,thread long& error) {
    if(!wealth_container(v,repairs,7,-1,valid))return 0;
    long cursor=repairs+1,paid=0;const long end=state_end(v,repairs,valid),count=state_record(v,repairs)[1];
    if(count>(end-repairs-1)/2){valid=false;return 0;}
    for(long entry=0;valid&&entry<count;++entry){const long job=state_end(v,cursor,valid);
        wealth_container(v,job,10,7,valid);
        const long jt=state_string_id(v,state_child(v,job,2,valid),valid);
        const long jo=state_string_id(v,state_child(v,job,1,valid),valid);
        bool present=false;const long optional=state_optional(v,state_child(v,job,6,valid),present,valid);
        const long je=present?state_string_id(v,optional,valid):-1;
        if(jt==target&&jo==owner&&je==endpoint&&wealth_int(v,state_child(v,job,4,valid),valid)==0){
            const long amount=wealth_int(v,state_child(v,job,3,valid),valid);
            paid=wealth_int_domain(paid+amount,valid,error);}
        cursor=state_end(v,job,valid);}
    if(valid&&cursor!=end)valid=false;return paid;
}

kernel void resident_wealth(
    device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],
    device const uchar* prefix_bytes [[buffer(2)]],device const long* prefix_offsets [[buffer(3)]],
    device const uchar* suffix_bytes [[buffer(4)]],device const long* suffix_offsets [[buffer(5)]],
    device const long* usage [[buffer(6)]],device const long* ids [[buffer(7)]],
    device const long* unit_types [[buffer(8)]],device const long* facility_types [[buffer(9)]],
    device const long* rail_types [[buffer(10)]],device const long* income [[buffer(11)]],
    device const long* national [[buffer(12)]],device const long* cash [[buffer(13)]],
    device long* output [[buffer(14)]],device long* players_all [[buffer(15)]],
    device long* errors [[buffer(16)]],device long* terminal_flags [[buffer(17)]],
    device const long* source_errors [[buffer(18)]],device long* totals [[buffer(19)]],
    device long* gaps [[buffer(20)]],device const long* dims [[buffer(21)]],uint lane [[thread_position_in_grid]]) {
    const long B=dims[0],C=dims[1],N=dims[2],T=dims[3],U=dims[4],F=dims[5];
    if(long(lane)>=B)return;
    bool valid=true;long error=0;
    PackedStateView v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
        prefix_bytes,prefix_offsets,dims[6],dims[7],suffix_bytes,suffix_offsets,dims[8],dims[9],usage,valid);
    long values[15];for(long i=0;i<15;++i)values[i]=0;
    device long* players=players_all+ulong(lane)*N;
    for(long n=0;n<N;++n)players[n]=-3;terminal_flags[lane]=0;
    if(source_errors[lane])valid=false;
    wealth_container(v,0,10,2,valid);const long state=state_child(v,0,0,valid);wealth_container(v,state,10,19,valid);
    const long nations=state_child(v,state,0,valid),land=state_child(v,state,1,valid);
    const long units=state_child(v,state,2,valid),facilities=state_child(v,state,3,valid);
    const long rails=state_child(v,state,4,valid),projects=state_child(v,state,5,valid),repairs=state_child(v,state,6,valid);
    terminal_flags[lane]=state_boolean_value(v,state_child(v,state,18,valid),valid);
    wealth_container(v,nations,7,-1,valid);
    if(valid){const long count=state_record(v,nations)[1],end=state_end(v,nations,valid);long cursor=nations+1,previous=-1;
        if(count>N)wealth_fail(1,valid,error);
        for(long entry=0;valid&&entry<count;++entry){const long id=state_string_id(v,cursor,valid),n=wealth_index(ids,N,id);
            if(n<0||n<=previous){wealth_fail(1,valid,error);break;}previous=n;
            const long value=state_end(v,cursor,valid);cursor=state_end(v,value,valid);}
        if(valid&&cursor!=end)valid=false;}
    for(long n=0;valid&&n<N;++n){const long root=state_map_find_id(v,nations,ids[n],valid);if(root<0)continue;
        wealth_container(v,root,10,12,valid);bool assigned=false;
        const long player=state_optional(v,state_child(v,root,1,valid),assigned,valid);
        players[n]=assigned?wealth_index(ids+N+T+U+F,3,state_string_id(v,player,valid)):-1;
        if(assigned&&players[n]<0){players[n]=-2;wealth_fail(2,valid,error);break;}
        const long actor=players[n];if(actor<0)continue;
        const long native_error=income[(ulong(lane)*N+n)*6];
        if(native_error){wealth_fail(native_error==1||native_error==2?1:native_error==4?4:2,valid,error);break;}
        wealth_add_component(values,actor,0,income[(ulong(lane)*N+n)*6+5]*2,valid,error);
        wealth_add_component(values,actor,3,cash[(ulong(lane)*N+n)*2]*2,valid,error);
    }
    const long roots[4]={units,facilities,rails,projects};
    for(long category=0;valid&&category<4;++category){const long map=roots[category];
        wealth_container(v,map,7,-1,valid);if(!valid)break;
        const long count=state_record(v,map)[1],end=state_end(v,map,valid);long cursor=map+1;
        if(count>(end-map-1)/2){valid=false;break;}
        for(long entry=0;valid&&entry<count;++entry){const long id=state_string_id(v,cursor,valid),root=state_end(v,cursor,valid);
            if(category==0){wealth_container(v,root,10,14,valid);
                const long owner=state_string_id(v,state_child(v,root,2,valid),valid);
                const long actor=wealth_recipient(owner,ids,N,players,valid,error);
                if(actor>=0&&!wealth_is_crew(v,state_child(v,root,13,valid),valid)){
                    const long type=wealth_index(ids+N+T,U,state_string_id(v,state_child(v,root,1,valid),valid));
                    if(type<0){wealth_fail(1,valid,error);break;}
                    if(!unit_types[type*4+1]||!unit_types[type*4+3]){wealth_fail(2,valid,error);break;}
                    const long paid=wealth_prepaid(v,repairs,id,owner,-1,valid,error);
                    const long damage=wealth_int(v,state_child(v,root,10,valid),valid);
                    const long left=max(0L,wealth_int_domain(damage-paid,valid,error));
                    const long deduction=wealth_int_domain(unit_types[type*4+2]*left,valid,error);
                    const long value=wealth_int_domain(unit_types[type*4]-deduction,valid,error);
                    wealth_add_component(values,actor,1,value*2,valid,error);
                }
            }else if(category==1){wealth_container(v,root,10,5,valid);
                const long zone=state_string_id(v,state_child(v,root,2,valid),valid);
                const long owner=wealth_owner(v,land,zone,valid,error),actor=wealth_recipient(owner,ids,N,players,valid,error);
                if(actor>=0){const long type=wealth_index(ids+N+T+U,F,state_string_id(v,state_child(v,root,1,valid),valid));
                    if(type<0){wealth_fail(1,valid,error);break;}
                    const long paid=wealth_prepaid(v,repairs,id,owner,-1,valid,error);
                    const long damage=wealth_int(v,state_child(v,root,3,valid),valid);
                    const long left=max(0L,wealth_int_domain(damage-paid,valid,error));
                    const long deduction=wealth_int_domain(left*facility_types[type*2+1],valid,error);
                    const long value=wealth_int_domain(facility_types[type*2]-deduction,valid,error);
                    wealth_add_component(values,actor,2,value*2,valid,error);}
            }else if(category==2){wealth_container(v,root,10,4,valid);
                const long a=state_string_id(v,state_child(v,root,1,valid),valid),b=state_string_id(v,state_child(v,root,2,valid),valid);
                long previous=map+1;
                for(long earlier=0;valid&&earlier<entry;++earlier){const long item=state_end(v,previous,valid);
                    const long x=state_string_id(v,state_child(v,item,1,valid),valid),y=state_string_id(v,state_child(v,item,2,valid),valid);
                    if((a==x&&b==y)||(a==y&&b==x)){wealth_fail(2,valid,error);break;}previous=state_end(v,item,valid);}
                long remaining=0;const long damaged=state_child(v,root,3,valid);wealth_container(v,damaged,7,-1,valid);
                if(!valid)break;long dcursor=damaged+1;const long dcount=state_record(v,damaged)[1],dend=state_end(v,damaged,valid);
                if(dcount>(dend-damaged-1)/2){valid=false;break;}
                for(long d=0;valid&&d<dcount;++d){const long endpoint=state_string_id(v,dcursor,valid),value=state_end(v,dcursor,valid);
                    const long owner=wealth_owner(v,land,endpoint,valid,error);
                    const long paid=owner<0?0:wealth_prepaid(v,repairs,id,owner,endpoint,valid,error);
                    remaining=wealth_int_domain(remaining+max(0L,wealth_int_domain(wealth_int(v,value,valid)-paid,valid,error)),valid,error);
                    dcursor=state_end(v,value,valid);}
                if(valid&&dcursor!=dend)valid=false;
                const long ai=wealth_index(ids+N,T,a),bi=wealth_index(ids+N,T,b);
                if(ai<0||bi<0){wealth_fail(1,valid,error);break;}
                if(!rail_types[(ai*T+bi)*2+1]){wealth_fail(2,valid,error);break;}
                const long half_twice=rail_types[(ai*T+bi)*2]-remaining;
                for(long side=0;valid&&side<2;++side){const long owner=wealth_owner(v,land,side?b:a,valid,error);
                    const long actor=wealth_recipient(owner,ids,N,players,valid,error);
                    if(actor>=0)wealth_add_component(values,actor,2,half_twice,valid,error);}
            }else{wealth_container(v,root,10,8,valid);
                const long owner=state_string_id(v,state_child(v,root,1,valid),valid);
                const long actor=wealth_recipient(owner,ids,N,players,valid,error);
                if(actor>=0)wealth_add_component(values,actor,4,wealth_int(v,state_child(v,root,5,valid),valid)*2,valid,error);}
            cursor=state_end(v,root,valid);}
        if(valid&&cursor!=end)valid=false;
    }
    long total[3]={0,0,0},sum=0;
    for(long actor=0;valid&&actor<3;++actor){const long base=actor*5,rate=values[base];
        if(rate>0x7fffffffffffffffL/10||rate<(-0x7fffffffffffffffL-1L)/10){wealth_fail(4,valid,error);break;}
        total[actor]=rate*10;
        for(long f=1;valid&&f<5;++f)wealth_add_long(total[actor],values[base+f],total[actor],valid,error);
        wealth_add_long(sum,total[actor],sum,valid,error);}
    long gap[3]={0,0,0};
    for(long actor=0;valid&&actor<3;++actor){long twice;
        wealth_add_long(total[actor],total[actor],twice,valid,error);
        if(sum==(-0x7fffffffffffffffL-1L)){wealth_fail(4,valid,error);break;}
        wealth_add_long(twice,-sum,gap[actor],valid,error);}
    if(!valid&&!error)error=3;errors[lane]=error;
    for(long i=0;i<15;++i)output[ulong(lane)*15+i]=valid?values[i]:0;
    for(long actor=0;actor<3;++actor){totals[ulong(lane)*3+actor]=valid?total[actor]:0;gaps[ulong(lane)*3+actor]=valid?gap[actor]:0;}
}

// Test-only native-double component-addition conformance, including 2^53 ties.
kernel void wealth_component_sum_probe(device const long* input [[buffer(0)]],device long* output [[buffer(1)]],
    device long* errors [[buffer(2)]],device const long* dims [[buffer(3)]],uint lane [[thread_position_in_grid]]) {
    if(long(lane)>=dims[0])return;long values[15];for(long i=0;i<15;++i)values[i]=0;
    bool valid=true;long error=0;
    for(long item=0;valid&&item<dims[1];++item)wealth_add_component(values,0,0,input[ulong(lane)*dims[1]+item],valid,error);
    output[lane]=values[0];errors[lane]=error;
}
"""

_library=None
_lock=threading.Lock()


@lru_cache(maxsize=16)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device="mps")


@lru_cache(maxsize=1)
def _dummy():return torch.zeros(1,dtype=torch.int64,device="mps")


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    return _library


def _component_sum_probe(values):
    if not isinstance(values,torch.Tensor) or values.device.type!="mps" or values.dtype!=torch.int64 or values.ndim!=2 or not values.is_contiguous():
        raise ValueError("Probe requires contiguous resident int64 [lane,term] values")
    output=torch.empty(values.shape[0],dtype=torch.int64,device=values.device);errors=torch.empty_like(output)
    if values.shape[0]:_kernels().wealth_component_sum_probe(values,output,errors,_dimensions(tuple(values.shape)),threads=values.shape[0])
    return output,errors


class ResidentWealthContext:
    def __init__(self,state_context,native_wealth_context):
        self.state_context=state_context
        self.income=ResidentIncomeContext(state_context,native_wealth_context.income_context)
        self.unit_types=tuple(native_wealth_context.unit_types);self.facility_types=tuple(native_wealth_context.facility_types)
        names=(*self.income.ledger_context.nation_ids,*self.income.ledger_context.income.territory_ids,
               *self.unit_types,*self.facility_types,*PLAYERS)
        self.ids=torch.tensor(state_context.prefix_lookup_ids(names),dtype=torch.int64,device=state_context.device)
        self.units=torch.tensor(native_wealth_context.unit_array(),dtype=torch.int64,device=state_context.device)
        self.facilities=torch.tensor(native_wealth_context.facility_array(),dtype=torch.int64,device=state_context.device)
        self.rails=torch.tensor(native_wealth_context.rail_array(),dtype=torch.int64,device=state_context.device)

    def evaluate(self,state):
        values,dimensions=self.income._layout(state)
        inputs=self.income.extract(state)
        income=self.income.ledger_context.income.compute(inputs.territories,inputs.nations)
        B,C,N,T=dimensions[:4];device=state.device
        alloc=lambda *shape:torch.empty(shape,dtype=torch.int64,device=device)
        components,totals,gaps=alloc(B,3,5),alloc(B,3),alloc(B,3)
        errors,terminal,players=alloc(B),alloc(B),alloc(B,N)
        if B:
            records,lengths,_,prefix,poffsets,suffix,soffsets,_,usage=values
            dims=(B,C,N,T,len(self.unit_types),len(self.facility_types),state.context.string_count,
                  prefix.shape[0],soffsets.shape[0]-1,suffix.shape[0])
            source_errors=state.errors|inputs.errors
            args=(records,lengths,prefix,poffsets,suffix,soffsets,usage,self.ids,self.units,self.facilities,self.rails,
                  income.income,inputs.nations,inputs.ledger,components,players,errors,terminal,source_errors,totals,gaps,_dimensions(dims))
            if any(not value.is_contiguous() for value in args):raise ValueError("Wealth inputs must be contiguous; no hidden copy")
            _kernels().resident_wealth(*(value if value.numel() else _dummy() for value in args),threads=B)
        terminal_errors=torch.where(terminal.bool()|(errors==3),errors,0)
        return ResidentWealthResult(components,totals,gaps,torch.where(terminal[:,None].bool(),gaps,0),errors,
                                   terminal_errors,terminal,state.context.identity)

    def scores(self,result):
        """Native score bits and float32 terminal targets, without a host read."""
        if result.context_identity!=self.state_context.identity:raise ValueError("Wealth result wire context differs")
        from .resident_wealth_scores import native_wealth_scores
        return native_wealth_scores(result.components_twice,result.errors,result.terminal_errors,result.terminal,
                                   context_identity=result.context_identity)

    def inspect(self,result,kind="wealth"):
        """Explicit native-double-compatible host output boundary.

        Python float is binary64. math.fma deliberately matches the fused native
        total; Python's compensated sum() is not used. Rational totals are not
        substituted for native-double terminal rewards.
        """
        if result.context_identity!=self.state_context.identity:raise ValueError("Wealth result wire context differs")
        if kind not in {"wealth","gaps","terminal"}:raise ValueError("Choose wealth, gaps or terminal inspection")
        errors=(result.terminal_errors if kind=="terminal" else result.errors).cpu().tolist()
        terminal=result.terminal.cpu().tolist();components=result.components_twice.cpu().tolist()
        rows=[]
        for lane,error in enumerate(errors):
            if error==1:raise IndexError("Wealth entity lookup failed")
            if error==2:raise RuntimeError("Wealth definition/value/physical-rail rule failed")
            if error==3:raise ValueError("Packed wealth input is invalid")
            if error==4:raise OverflowError("Outside native int arithmetic or resident int64 component representation")
            if kind=="terminal" and not terminal[lane]:rows.append((0.,0.,0.));continue
            values=[[float(value)/2 for value in actor] for actor in components[lane]]
            totals=[math.fma(.1,((x[1]+x[2])+x[3])+x[4],x[0]) for x in values]
            combined=(totals[0]+totals[1])+totals[2]
            if kind in {"gaps","terminal"}:rows.append(tuple(2*value-combined for value in totals))
            else:rows.append({player:{**dict(zip(COMPONENTS,values[index],strict=True)),"wealth":totals[index]}
                              for index,player in enumerate(PLAYERS)})
        return rows
