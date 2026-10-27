"""Exact independent State-field and unit-entry JSON writers on Apple Metal.

The remaining serial prefix measured roughly ten milliseconds per identity.
Each native lexical field now has an independent counting/writing task; Units
also retain independent entry tasks. Offsets are computed in native order.
Invalid lanes run the original serial GPU writer, preserving diagnostic bytes.
"""
import re
import threading

import torch

from .canonical_json_metal import CanonicalJsonBatch
from .resident_state_json import ResidentStateJson, SOURCE as REFERENCE_SOURCE, STATE_FIELDS, SCHEMAS, _literal
from .resident_state_json_parallel import _inputs, _dimensions, _call

FIELDS = tuple(sorted(STATE_FIELDS))


def _source():
    if FIELDS[-1] != "units" or STATE_FIELDS["units"] != (2,"map_unit") or SCHEMAS["unit"][0] != 14:
        raise RuntimeError("Audited State/Unit JSON schema changed")
    marker="kernel void resident_state_json("
    if REFERENCE_SOURCE.count(marker)!=1:raise RuntimeError("Audited serial diagnostic kernel changed")
    tail=REFERENCE_SOURCE.split(marker,1)[1].split("kernel void resident_outer_engine_json",1)[0]
    signature,body=tail.split(") {",1);body=body.rsplit("}",1)[0]
    fallback="inline void pf_serial("+re.sub(r"\[\[.*?\]\]","",signature)+") {"+body+"}\n"
    field=["inline void pf_field(thread CanonicalWriter& w,long state,long field,device long* stack,long K,long fingerprint){switch(field){"]
    for i,name in enumerate(FIELDS):
        index,kind=STATE_FIELDS[name]
        field.extend((f"case {i}:{{",_literal('"'+name+'":')))
        if name=="units":field.append("canonical_put(w,'{');")
        elif kind=="fingerprint":field.append("canonical_string(w,fingerprint);")
        elif kind=="one":field.append("canonical_put(w,'1');")
        else:field.append(f"sj_{kind}(w,sj_child(w,state,{index}),stack,K);")
        field.append("break;}")
    field.append("default:w.error|=1;}}")
    roots=",".join(str(STATE_FIELDS[name][0]) for name in FIELDS)
    return REFERENCE_SOURCE+fallback+"\n".join(field)+f"\nconstant long pf_roots[{len(FIELDS)}]={{{roots}}};\n"+r'''
kernel void pf_plan(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const uchar* prefix[[buffer(3)]],device const long* poffsets[[buffer(4)]],device const uchar* suffix[[buffer(5)]],
 device const long* soffsets[[buffer(6)]],device const long* usage[[buffer(7)]],device const long* numbers[[buffer(8)]],
 device const long* noffsets[[buffer(9)]],device const uchar* nbytes[[buffer(10)]],device uchar* data[[buffer(11)]],
 device long* meta[[buffer(12)]],device long* tasks[[buffer(13)]],device const long* dims[[buffer(14)]],
 uint lane[[thread_position_in_grid]]){
 const long B=dims[0],K=dims[1],C=dims[2],U=dims[10],F=dims[11],T=U+F;if(long(lane)>=B)return;
 device long* m=meta+ulong(lane)*3;m[0]=0;m[1]=m[2]=-1;if(inherited[lane]){m[0]=1;return;}
 bool valid=lengths[lane]>=0&&lengths[lane]<=K;
 auto v=make_packed_state_view(records+ulong(lane)*K*5,lengths[lane],K,prefix,poffsets,dims[3],dims[4],
   suffix,soffsets,dims[5],dims[6],usage,valid);
 CanonicalWriter w{v,data+ulong(lane)*C,0,0,0,numbers,noffsets,nbytes,dims[7],dims[8]};
 if(!valid||!sj_container(w,0,10,2)){m[0]=1;return;}
 const long state=sj_child(w,0,0),interface=sj_child(w,state,17);
 if(!sj_container(w,state,10,19)||!sj_container(w,interface,13,-1)){m[0]=1;return;}m[2]=state;
 for(long i=0;i<F;++i){device long* task=tasks+(ulong(lane)*T+i)*5;
   task[0]=state;task[1]=0;task[2]=task[3]=0;task[4]=1;
   if(pf_roots[i]>=0){task[0]=sj_child(w,state,pf_roots[i]);
     if(pf_roots[i]==17&&!state_record(v,interface)[1])task[4]=0;}}
 const long units=sj_child(w,state,2);if(!sj_container(w,units,7,-1)||w.error){m[0]=1;return;}
 const long count=state_record(v,units)[1];if(count>U){m[0]=1;return;}m[1]=count;
 long cursor=units+1,previous=-1;
 for(long i=0;i<count;++i){const long id=state_string_id(v,cursor,valid);
   if(!valid||(previous>=0&&!canonical_less(w,previous,id))){m[0]=1;return;}previous=id;
   const long root=state_end(v,cursor,valid);if(!valid){m[0]=1;return;}
   device long* task=tasks+(ulong(lane)*T+F+i)*5;task[0]=root;task[1]=id;task[2]=task[3]=0;task[4]=1;
   cursor=state_end(v,root,valid);if(!valid){m[0]=1;return;}}
}
kernel void pf_fragments(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const uchar* prefix[[buffer(2)]],device const long* poffsets[[buffer(3)]],device const uchar* suffix[[buffer(4)]],
 device const long* soffsets[[buffer(5)]],device const long* usage[[buffer(6)]],device const long* numbers[[buffer(7)]],
 device const long* noffsets[[buffer(8)]],device const uchar* nbytes[[buffer(9)]],device uchar* data[[buffer(10)]],
 device long* stacks[[buffer(11)]],device const long* meta[[buffer(12)]],device long* tasks[[buffer(13)]],
 device int* task_errors[[buffer(14)]],device const long* dims[[buffer(15)]],uint row[[thread_position_in_grid]]){
 const long B=dims[0],K=dims[1],C=dims[2],U=dims[10],F=dims[11],T=U+F,lane=long(row)/T,i=long(row)%T;
 if(lane>=B)return;const bool write=dims[12]!=0;if(!write)task_errors[row]=0;
 if(meta[ulong(lane)*3]||i>=F+meta[ulong(lane)*3+1])return;
 device long* task=tasks+ulong(row)*5;if(!task[4])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*K*5,lengths[lane],K,prefix,poffsets,dims[3],dims[4],
   suffix,soffsets,dims[5],dims[6],usage,valid);
 // Constants and the Units opening use no traversal scratch. Other fields
 // own disjoint source subtrees, as do each of the separate unit entries.
 const long root=task[0];long span=1;
 if(i>=F||(pf_roots[i]>=0&&pf_roots[i]!=2))span=state_end(v,root,valid)-root;
 if(!valid||root<0||root>=K||span<=0||root+span>K){if(!write)task_errors[row]=1;return;}
 CanonicalWriter w{v,data+ulong(lane)*C,write?C:0,write?task[3]:0,0,numbers,noffsets,nbytes,dims[7],dims[8]};
 device long* stack=stacks+(ulong(lane)*K+root)*5;
 if(i<F)pf_field(w,meta[ulong(lane)*3+2],i,stack,span,dims[9]);
 else{canonical_string(w,task[1]);canonical_put(w,':');sj_unit(w,root,stack,span);}
 if(!write){task[2]=w.position;task_errors[row]=w.error;}
}
kernel void pf_offsets(device long* meta[[buffer(0)]],device long* tasks[[buffer(1)]],
 device const int* task_errors[[buffer(2)]],device uchar* data[[buffer(3)]],device long* lengths[[buffer(4)]],
 device long* required[[buffer(5)]],device int* errors[[buffer(6)]],device const long* dims[[buffer(7)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[2],F=dims[11],T=F+dims[10];if(long(lane)>=B)return;
 lengths[lane]=required[lane]=0;errors[lane]=0;device long* m=meta+ulong(lane)*3;if(m[0])return;
 const long count=F+m[1];for(long i=0;i<count;++i)if(task_errors[ulong(lane)*T+i]){m[0]=1;return;}
 long cursor=1;bool first=true;if(C)data[ulong(lane)*C]='{';
 for(long i=0;i<count;++i){device long* task=tasks+(ulong(lane)*T+i)*5;if(!task[4])continue;
   const bool comma=i<F?!first:i>F;if(comma){if(cursor==LONG_MAX){m[0]=1;return;}
     if(cursor<C)data[ulong(lane)*C+cursor]=',';++cursor;}
   if(i<F)first=false;task[3]=cursor;
   if(task[2]<0||task[2]>LONG_MAX-cursor){m[0]=1;return;}cursor+=task[2];}
 if(cursor>LONG_MAX-2){m[0]=1;return;}
 if(cursor<C)data[ulong(lane)*C+cursor]='}';++cursor;
 if(cursor<C)data[ulong(lane)*C+cursor]='}';++cursor;
 required[lane]=cursor;errors[lane]=cursor>C?2:0;if(!errors[lane])lengths[lane]=cursor;
}
kernel void pf_fallback(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const uchar* prefix[[buffer(3)]],device const long* poffsets[[buffer(4)]],device const uchar* suffix[[buffer(5)]],
 device const long* soffsets[[buffer(6)]],device const long* usage[[buffer(7)]],device const long* numbers[[buffer(8)]],
 device const long* noffsets[[buffer(9)]],device const uchar* nbytes[[buffer(10)]],device uchar* data[[buffer(11)]],
 device long* output_lengths[[buffer(12)]],device long* required[[buffer(13)]],device int* errors[[buffer(14)]],
 device long* stacks[[buffer(15)]],device const long* dims[[buffer(16)]],device const long* meta[[buffer(17)]],uint lane[[thread_position_in_grid]]){
 if(long(lane)>=dims[0]||!meta[ulong(lane)*3])return;
 for(long i=0;i<dims[2];++i)data[ulong(lane)*dims[2]+i]=0;
 pf_serial(records,lengths,inherited,prefix,poffsets,suffix,soffsets,usage,numbers,noffsets,nbytes,data,
   output_lengths,required,errors,stacks,dims,lane);
}
'''


_lock=threading.Lock()
_library=None


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(_source())
    return _library


class ParallelFieldStateJson(ResidentStateJson):
    def __init__(self,number_context,*,fragment_group_size=1,**digest_options):
        if type(fragment_group_size) is not int or fragment_group_size<=0:
            raise ValueError("Field fragment group size must be a positive integer")
        super().__init__(number_context,**digest_options)
        self.fragment_group_size=fragment_group_size

    def serialize(self,state,*,byte_capacity):
        B,K,C,context,inputs=_inputs(self,state,byte_capacity)
        U=max(K//16,1);F=len(FIELDS);T=F+U
        if B*T>(1<<32)-1:raise OverflowError("Field JSON grid cannot be represented; no fragments truncated")
        data=torch.zeros((B,C),dtype=torch.uint8,device=state.device)
        lengths=torch.empty(B,dtype=torch.int64,device=state.device);required=torch.empty_like(lengths)
        errors=torch.empty(B,dtype=torch.int32,device=state.device)
        count=torch.tensor([B],dtype=torch.int64,device=state.device);batch_error=torch.zeros(1,dtype=torch.int32,device=state.device)
        stacks=torch.empty((B,K,5),dtype=torch.int64,device=state.device)
        meta=torch.empty((B,3),dtype=torch.int64,device=state.device)
        tasks=torch.empty((B,T,5),dtype=torch.int64,device=state.device)
        task_errors=torch.empty((B,T),dtype=torch.int32,device=state.device)
        if B:
            dims=(B,K,C,state.context.string_count,state.context.string_bytes.numel(),state.string_offsets.numel()-1,
                state.string_bytes.numel(),context.words.shape[0],context.bytes.numel(),self.fingerprint,U,F)
            measure=_dimensions((*dims,0));write=_dimensions((*dims,1));library=_kernels()
            if self.fragment_group_size>library.pf_fragments.max_threads_per_threadgroup:
                raise ValueError("Field fragment group size exceeds Metal kernel limit")
            _call(library.pf_plan,(*inputs,data,meta,tasks,measure),B)
            fragment_inputs=(state.records,state.lengths,*inputs[3:],data,stacks,meta,tasks,task_errors)
            _call(library.pf_fragments,(*fragment_inputs,measure),B*T,group_size=self.fragment_group_size)
            _call(library.pf_offsets,(meta,tasks,task_errors,data,lengths,required,errors,measure),B)
            _call(library.pf_fragments,(*fragment_inputs,write),B*T,group_size=self.fragment_group_size)
            _call(library.pf_fallback,(*inputs,data,lengths,required,errors,stacks,measure,meta),B)
        return CanonicalJsonBatch(data,lengths,required,errors,count,batch_error)
