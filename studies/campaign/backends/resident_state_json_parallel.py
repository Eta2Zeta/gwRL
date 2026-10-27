"""Experimental exact State JSON with independent unit-entry writers on Metal.

Units are the last native lexical State field. Other fields keep their original
writer; unit entries are measured and written independently into disjoint final
byte ranges. Malformed inputs use the unchanged serial GPU writer, including its
partial bytes/errors. No CPU fallback, field omission or fixed unit cap is used.
"""
from functools import lru_cache
import re
import threading

import torch

from .resident_state_json import ResidentStateJson, SOURCE as REFERENCE_SOURCE, STATE_FIELDS, SCHEMAS, _literal
from .canonical_json_metal import CanonicalJsonBatch
from .device_state import _device


def _source():
    if sorted(STATE_FIELDS)[-1] != "units" or STATE_FIELDS["units"] != (2, "map_unit") or SCHEMAS["unit"][0] != 14:
        raise RuntimeError("Audited native State/Unit serialization schema changed")
    marker = "kernel void resident_state_json("
    if REFERENCE_SOURCE.count(marker) != 1:
        raise RuntimeError("Audited State serializer kernel changed")
    tail = REFERENCE_SOURCE.split(marker, 1)[1].split("kernel void resident_outer_engine_json", 1)[0]
    signature, body = tail.split(") {", 1)
    body = body.rsplit("}", 1)[0]
    signature = re.sub(r"\[\[.*?\]\]", "", signature)
    fallback = "inline void pu_serial_reference(" + signature + ") {" + body + "}\n"
    prefix = ["inline void pu_prefix(thread CanonicalWriter& w,long node,device long* stack,long K,long fingerprint) {",
        "if(!sj_container(w,node,10,19))return;const long interface=sj_child(w,node,17);",
        "if(!sj_container(w,interface,13,-1))return;const bool include_interface=state_record(w.view,interface)[1]!=0;",
        "canonical_put(w,'{');bool first=true;"]
    for name, (index, kind) in sorted(STATE_FIELDS.items()):
        if name == "action_interface":prefix.append("if(include_interface){")
        prefix.extend(("if(!first)canonical_put(w,',');first=false;", _literal('"'+name+'":')))
        if name == "units":break
        if kind == "fingerprint":prefix.append("canonical_string(w,fingerprint);")
        elif kind == "one":prefix.append("canonical_put(w,'1');")
        else:prefix.append(f"sj_{kind}(w,sj_child(w,node,{index}),stack,K);")
        if name == "action_interface":prefix.append("}")
    prefix.append("}")
    return REFERENCE_SOURCE + fallback + "\n".join(prefix) + r'''
kernel void pu_plan(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const uchar* prefix[[buffer(3)]],device const long* poffsets[[buffer(4)]],device const uchar* suffix[[buffer(5)]],
 device const long* soffsets[[buffer(6)]],device const long* usage[[buffer(7)]],device const long* numbers[[buffer(8)]],
 device const long* noffsets[[buffer(9)]],device const uchar* nbytes[[buffer(10)]],device uchar* data[[buffer(11)]],
 device long* stacks[[buffer(12)]],device long* meta[[buffer(13)]],device long* tasks[[buffer(14)]],
 device const long* dims[[buffer(15)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],K=dims[1],C=dims[2],U=dims[10];if(long(lane)>=B)return;
 device long* m=meta+ulong(lane)*4;m[0]=m[1]=m[2]=0;m[3]=-1;
 if(inherited[lane]){m[2]=1;return;}
 bool valid=lengths[lane]>=0&&lengths[lane]<=K;
 auto v=make_packed_state_view(records+ulong(lane)*K*5,lengths[lane],K,prefix,poffsets,dims[3],dims[4],
    suffix,soffsets,dims[5],dims[6],usage,valid);
 CanonicalWriter w{v,data+ulong(lane)*C,C,0,0,numbers,noffsets,nbytes,dims[7],dims[8]};
 if(!valid||!sj_container(w,0,10,2)){m[2]=1;return;}
 const long state=sj_child(w,0,0);pu_prefix(w,state,stacks+ulong(lane)*K*5,K,dims[9]);m[0]=w.position;
 if(w.error){m[2]=1;return;}
 const long units=sj_child(w,state,2);
 if(!sj_container(w,units,7,-1)){m[2]=1;return;}
 const long count=state_record(v,units)[1];if(count>U){m[2]=1;return;}m[1]=count;m[3]=units;
 long cursor=units+1,previous=-1;
 for(long i=0;i<count;++i){const long id=state_string_id(v,cursor,valid);
   if(!valid||(previous>=0&&!canonical_less(w,previous,id))){m[2]=1;return;}previous=id;
   const long value=state_end(v,cursor,valid);if(!valid){m[2]=1;return;}
   device long* task=tasks+(ulong(lane)*U+i)*4;task[0]=id;task[1]=value;task[2]=task[3]=0;
   cursor=state_end(v,value,valid);if(!valid){m[2]=1;return;}}
}
kernel void pu_measure(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const uchar* prefix[[buffer(2)]],device const long* poffsets[[buffer(3)]],device const uchar* suffix[[buffer(4)]],
 device const long* soffsets[[buffer(5)]],device const long* usage[[buffer(6)]],device const long* numbers[[buffer(7)]],
 device const long* noffsets[[buffer(8)]],device const uchar* nbytes[[buffer(9)]],device uchar* data[[buffer(10)]],
 device long* stacks[[buffer(11)]],device const long* meta[[buffer(12)]],device long* tasks[[buffer(13)]],
 device int* task_errors[[buffer(14)]],device const long* dims[[buffer(15)]],uint row[[thread_position_in_grid]]){
 const long B=dims[0],K=dims[1],C=dims[2],U=dims[10],lane=long(row)/U,i=long(row)%U;
 if(lane>=B)return;task_errors[row]=0;if(meta[ulong(lane)*4+2]||i>=meta[ulong(lane)*4+1])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*K*5,lengths[lane],K,prefix,poffsets,dims[3],dims[4],
   suffix,soffsets,dims[5],dims[6],usage,valid);
 device long* task=tasks+ulong(row)*4;const long root=task[1],span=state_end(v,root,valid)-root;
 if(!valid||root<0||root>=K||span<=0||root+span>K){task_errors[row]=1;return;}
 CanonicalWriter w{v,data+ulong(lane)*C,0,0,0,numbers,noffsets,nbytes,dims[7],dims[8]};
 canonical_string(w,task[0]);canonical_put(w,':');sj_unit(w,root,stacks+(ulong(lane)*K+root)*5,span);
 task[2]=w.position;task_errors[row]=w.error;
}
kernel void pu_offsets(
 device long* meta[[buffer(0)]],device long* tasks[[buffer(1)]],device const int* task_errors[[buffer(2)]],
 device uchar* data[[buffer(3)]],device long* lengths[[buffer(4)]],device long* required[[buffer(5)]],
 device int* errors[[buffer(6)]],device const long* dims[[buffer(7)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[2],U=dims[10];if(long(lane)>=B)return;lengths[lane]=required[lane]=0;errors[lane]=0;
 device long* m=meta+ulong(lane)*4;if(m[2])return;const long count=m[1];
 for(long i=0;i<count;++i)if(task_errors[ulong(lane)*U+i]){m[2]=1;return;}
 long cursor=m[0];if(cursor<0||cursor==LONG_MAX){m[2]=1;return;}
 if(cursor<C)data[ulong(lane)*C+cursor]='{';++cursor;
 for(long i=0;i<count;++i){device long* task=tasks+(ulong(lane)*U+i)*4;
   if(i){if(cursor==LONG_MAX){m[2]=1;return;}if(cursor<C)data[ulong(lane)*C+cursor]=',';++cursor;}
   task[3]=cursor;if(task[2]<0||task[2]>LONG_MAX-cursor){m[2]=1;return;}cursor+=task[2];}
 if(cursor>LONG_MAX-2){m[2]=1;return;}
 if(cursor<C)data[ulong(lane)*C+cursor]='}';++cursor;
 if(cursor<C)data[ulong(lane)*C+cursor]='}';++cursor;
 required[lane]=cursor;errors[lane]=cursor>C?2:0;if(!errors[lane])lengths[lane]=cursor;
}
kernel void pu_write(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const uchar* prefix[[buffer(2)]],device const long* poffsets[[buffer(3)]],device const uchar* suffix[[buffer(4)]],
 device const long* soffsets[[buffer(5)]],device const long* usage[[buffer(6)]],device const long* numbers[[buffer(7)]],
 device const long* noffsets[[buffer(8)]],device const uchar* nbytes[[buffer(9)]],device uchar* data[[buffer(10)]],
 device long* stacks[[buffer(11)]],device const long* meta[[buffer(12)]],device const long* tasks[[buffer(13)]],
 device const long* dims[[buffer(14)]],uint row[[thread_position_in_grid]]){
 const long B=dims[0],K=dims[1],C=dims[2],U=dims[10],lane=long(row)/U,i=long(row)%U;
 if(lane>=B||meta[ulong(lane)*4+2]||i>=meta[ulong(lane)*4+1])return;
 bool valid=true;auto v=make_packed_state_view(records+ulong(lane)*K*5,lengths[lane],K,prefix,poffsets,dims[3],dims[4],
   suffix,soffsets,dims[5],dims[6],usage,valid);
 device const long* task=tasks+ulong(row)*4;const long root=task[1],span=state_end(v,root,valid)-root;
 CanonicalWriter w{v,data+ulong(lane)*C,C,task[3],0,numbers,noffsets,nbytes,dims[7],dims[8]};
 canonical_string(w,task[0]);canonical_put(w,':');sj_unit(w,root,stacks+(ulong(lane)*K+root)*5,span);
}
kernel void pu_fallback(
 device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],device const long* inherited[[buffer(2)]],
 device const uchar* prefix[[buffer(3)]],device const long* poffsets[[buffer(4)]],device const uchar* suffix[[buffer(5)]],
 device const long* soffsets[[buffer(6)]],device const long* usage[[buffer(7)]],device const long* numbers[[buffer(8)]],
 device const long* noffsets[[buffer(9)]],device const uchar* nbytes[[buffer(10)]],device uchar* data[[buffer(11)]],
 device long* output_lengths[[buffer(12)]],device long* required[[buffer(13)]],device int* errors[[buffer(14)]],
 device long* stacks[[buffer(15)]],device const long* dims[[buffer(16)]],device const long* meta[[buffer(17)]],
 uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[2];if(long(lane)>=B||!meta[ulong(lane)*4+2])return;
 for(long i=0;i<C;++i)data[ulong(lane)*C+i]=0;
 pu_serial_reference(records,lengths,inherited,prefix,poffsets,suffix,soffsets,usage,numbers,noffsets,nbytes,
    data,output_lengths,required,errors,stacks,dims,lane);
}
'''


_lock = threading.Lock()
_library = None


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library = torch.mps.compile_shader(_source())
    return _library


@lru_cache(maxsize=16)
def _dimensions(values):return torch.tensor(values, dtype=torch.int64, device="mps")


@lru_cache(maxsize=1)
def _dummy():return torch.empty(1, dtype=torch.int64, device="mps")


def _call(kernel, args, count, *, group_size=None):
    if count:
        arguments = tuple(value if value.numel() else _dummy() for value in args)
        if group_size is None:kernel(*arguments, threads=count)
        else:kernel(*arguments, threads=count, group_size=group_size)


class ParallelUnitStateJson(ResidentStateJson):
    def serialize(self, state, *, byte_capacity):
        # Keep the original host-side contract. The kernels below change only
        # scheduling/output allocation; neither mutable state nor fields change.
        state._metadata();_device(state.device)
        if state.context is not self.state_context:raise ValueError("State JSON context must match the exact resident state context")
        if type(byte_capacity) is not int or byte_capacity < 0:raise ValueError("State JSON byte capacity must be a nonnegative integer")
        B,K = state.records.shape[:2];C = byte_capacity;context = self.number_context
        if B > (1 << 32)-1 or B*max(K,C,1)*5 > (1 << 63)-1:raise OverflowError("State JSON allocation cannot be represented")
        inputs = (state.records,state.lengths,state.errors,state.context.string_bytes,state.context.string_offsets,
            state.string_bytes,state.string_offsets,state.suffix_usage,context.words,context.offsets,context.bytes)
        if any(not value.is_contiguous() or value.device != state.device for value in inputs):
            raise ValueError("State JSON inputs must remain resident and contiguous")
        if (state.context.string_bytes.dtype != torch.uint8 or state.context.string_bytes.ndim != 1 or
            state.context.string_offsets.dtype != torch.int64 or state.context.string_offsets.shape != (state.context.string_count+1,)):
            raise ValueError("State JSON static string arena layout differs")
        if (context.words.dtype != torch.int64 or context.words.ndim != 2 or context.words.shape[1] != 2 or
            context.offsets.dtype != torch.int64 or context.offsets.shape != (context.words.shape[0]+1,) or
            context.bytes.dtype != torch.uint8 or context.bytes.ndim != 1):
            raise ValueError("State JSON number arena layout differs")
        U = max(K//16,1)  # A map key plus UnitState14 needs at least16 records.
        if B*U > (1 << 32)-1:raise OverflowError("Unit JSON grid cannot be represented; no entries truncated")
        data = torch.zeros((B,C),dtype=torch.uint8,device=state.device)
        lengths = torch.empty(B,dtype=torch.int64,device=state.device);required = torch.empty_like(lengths)
        errors = torch.empty(B,dtype=torch.int32,device=state.device)
        count = torch.tensor([B],dtype=torch.int64,device=state.device);batch_error = torch.zeros(1,dtype=torch.int32,device=state.device)
        stack = torch.empty((B,K,5),dtype=torch.int64,device=state.device)
        meta = torch.empty((B,4),dtype=torch.int64,device=state.device)
        tasks = torch.empty((B,U,4),dtype=torch.int64,device=state.device)
        task_errors = torch.empty((B,U),dtype=torch.int32,device=state.device)
        if B:
            dims = _dimensions((B,K,C,state.context.string_count,state.context.string_bytes.numel(),
                state.string_offsets.numel()-1,state.string_bytes.numel(),context.words.shape[0],context.bytes.numel(),self.fingerprint,U))
            library = _kernels()
            _call(library.pu_plan,(*inputs,data,stack,meta,tasks,dims),B)
            unit_inputs = (state.records,state.lengths,state.context.string_bytes,state.context.string_offsets,
                state.string_bytes,state.string_offsets,state.suffix_usage,context.words,context.offsets,context.bytes)
            _call(library.pu_measure,(*unit_inputs,data,stack,meta,tasks,task_errors,dims),B*U,group_size=32)
            _call(library.pu_offsets,(meta,tasks,task_errors,data,lengths,required,errors,dims),B)
            _call(library.pu_write,(*unit_inputs,data,stack,meta,tasks,dims),B*U,group_size=32)
            _call(library.pu_fallback,(*inputs,data,lengths,required,errors,stack,dims,meta),B)
        return CanonicalJsonBatch(data,lengths,required,errors,count,batch_error)
