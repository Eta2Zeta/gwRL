"""Native State.toJson(false), State SHA256 and outer Engine SHA256 on MPS.

Every typed field follows campaign_state.cpp, including optional-null accounting,
lexical object ordering and decimal-string uint64 turn counters. History and RNG
are excluded from State identities. Generic nested payloads reuse the complete
source-capacity stack and exact native binary64 spelling context. This is a
serializer/hash operation, not a campaign transition or neural observation.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .canonical_json_metal import SOURCE as GENERIC_SOURCE,CanonicalJsonBatch,canonical_json_digests
from .device_state import _device


# (native field ordinal, JSON value kind). Native maps sort keys lexically;
# these explicit field schemas do likewise without constructing Python state.
SCHEMAS={
 "nation":(12,{"controller_nation":(0,"opt_id"),"player":(1,"opt_id"),"alliance":(2,"opt_id"),
    "power_status":(3,"id"),"treasury":(4,"opt_int"),"income_components":(5,"map_int"),
    "income_known":(6,"bool"),"technology_stages":(7,"map_int"),"at_war_with":(8,"set_id"),
    "allies":(9,"set_id"),"turn_flags":(10,"map_int"),"game_flags":(11,"map_int")}),
 "territory":(2,{"possessor":(0,"opt_id"),"flags":(1,"map_int")}),
 "unit":(14,{"id":(0,"id"),"type":(1,"id"),"owner":(2,"id"),"zone":(3,"id"),
    "movement_remaining":(4,"opt_int"),"movement_allowance":(5,"opt_int"),"turn_origin":(6,"id"),
    "route":(7,"vec_id"),"carried_by":(8,"opt_id"),"cargo":(9,"vec_id"),"damage":(10,"int"),
    "commitments":(11,"set_id"),"turn_flags":(12,"map_int"),"game_flags":(13,"map_int")}),
 "facility":(5,{"id":(0,"id"),"type":(1,"id"),"zone":(2,"id"),"damage":(3,"int"),"flags":(4,"map_int")}),
 "rail":(4,{"id":(0,"id"),"endpoint_a":(1,"id"),"endpoint_b":(2,"id"),"damage_by_endpoint":(3,"map_int")}),
 "build":(8,{"id":(0,"id"),"owner":(1,"id"),"type":(2,"id"),"site":(3,"opt_id"),
    "queue_position":(4,"int"),"paid_ipp":(5,"int"),"remaining_payments":(6,"vec_int"),"flags":(7,"map_int")}),
 "repair":(7,{"id":(0,"id"),"owner":(1,"id"),"target":(2,"id"),"remaining_damage":(3,"int"),
    "remaining_cost":(4,"int"),"restricts_action":(5,"bool"),"endpoint":(6,"opt_id")}),
 "action":(6,{"id":(0,"id"),"kind":(1,"id"),"player":(2,"id"),"nation":(3,"id"),
    "decision":(4,"opt_id"),"parameters":(5,"json")}),
 "decision":(6,{"id":(0,"id"),"kind":(1,"id"),"nation":(2,"id"),"reaction":(3,"bool"),
    "continuation":(4,"id"),"options":(5,"vec_action")}),
 "battle":(10,{"id":(0,"id"),"zone":(1,"id"),"attacker":(2,"id"),"defender":(3,"id"),
    "stage":(4,"id"),"attackers":(5,"vec_id"),"defenders":(6,"vec_id"),"pending_hits":(7,"map_int"),
    "flags":(8,"map_int"),"data":(9,"json")}),
 "die":(4,{"sides":(0,"int"),"modifier":(1,"int"),"reroll_faces":(2,"set_int"),"max_rerolls":(3,"int")}),
 "chance":(5,{"id":(0,"id"),"purpose":(1,"id"),"nation":(2,"id"),"continuation":(3,"id"),"dice":(4,"vec_die")}),
 "snapshot":(2,{"possessions":(0,"map_opt_id"),"units":(1,"map_pair_id")}),
 "clock":(6,{"round_index":(0,"int"),"nation_index":(1,"int"),"phase":(2,"phase"),
    "completed_rounds":(3,"int"),"player_turn_serial":(4,"u64string"),"income_collected":(5,"bool")}),
 "politics":(11,{"chinese_truce":(0,"bool"),"truce_permanently_ended":(1,"bool"),
    "foreign_china_war_pending":(2,"bool"),"truce_offer_pending":(3,"bool"),"china_invader":(4,"opt_id"),
    "attacked_warlords":(5,"map_set_id"),"alignment_queue":(6,"vec_id"),"capitals":(7,"map_id"),
    "surrendered":(8,"set_id"),"evolution_awarded":(9,"set_id"),"pending":(10,"map_json")}),
}

STATE_FIELDS={"nations":(0,"map_nation"),"territories":(1,"map_territory"),"units":(2,"map_unit"),
 "facilities":(3,"map_facility"),"rails":(4,"map_rail"),"construction":(5,"map_build"),"repairs":(6,"map_repair"),
 "clock":(7,"clock"),"politics":(8,"politics"),"turn_start":(9,"snapshot"),"completed_turns":(10,"map_int"),
 "decisions":(11,"vec_decision"),"battles":(12,"map_battle"),"battle_order":(13,"vec_id"),
 "chance":(14,"opt_chance"),"flags":(15,"map_int"),"action_interface":(17,"json"),"terminal":(18,"bool"),
 "definition_fingerprint":(-1,"fingerprint"),"schema_version":(-1,"one")}


HELPERS=r'''
inline bool sj_container(thread CanonicalWriter& w,long node,long tag,long expected) {
    bool valid=true;const long end=state_end(w.view,node,valid);if(!valid){w.error|=1;return false;}
    device const long* r=state_record(w.view,node);const long maximum=(tag==7||tag==13)?(end-node-1)/2:end-node-1;
    if(r[0]!=tag||r[1]<0||r[1]>maximum||(expected>=0&&r[1]!=expected)||r[2]||r[3]){w.error|=1;return false;}
    long cursor=node+1;for(long i=0;i<r[1]*(tag==7||tag==13?2:1);++i){cursor=state_end(w.view,cursor,valid);
        if(!valid||cursor>end){w.error|=1;return false;}}
    if(cursor!=end){w.error|=1;return false;}return true;
}
inline long sj_child(thread CanonicalWriter& w,long node,long index) {
    bool valid=true;const long child=state_child(w.view,node,index,valid);if(!valid)w.error|=1;return child;
}
inline void sj_id(thread CanonicalWriter& w,long node,device long* stack,long K) {
    bool valid=true;const long id=state_string_id(w.view,node,valid);if(!valid)w.error|=1;else canonical_string(w,id);
}
inline void sj_int(thread CanonicalWriter& w,long node,device long* stack,long K) {
    bool valid=true;const long value=state_signed_value(w.view,node,valid);if(!valid)w.error|=1;else canonical_integer(w,value);
}
inline void sj_bool(thread CanonicalWriter& w,long node,device long* stack,long K) {
    bool valid=true;const bool value=state_boolean_value(w.view,node,valid);if(!valid)w.error|=1;
    else if(value)canonical_literal(w,"true",4);else canonical_literal(w,"false",5);
}
inline void sj_json(thread CanonicalWriter& w,long node,device long* stack,long K) {canonical_json(w,node,stack,K);}
inline void sj_u64string(thread CanonicalWriter& w,long node,device long* stack,long K) {
    bool valid=true;ulong value=state_raw_bits(w.view,node,3,valid);if(!valid){w.error|=1;return;}
    char digits[20];int n=0;do{digits[n++]=char('0'+value%10);value/=10;}while(value);
    canonical_put(w,'"');while(n)canonical_put(w,uchar(digits[--n]));canonical_put(w,'"');
}
inline void sj_phase(thread CanonicalWriter& w,long node,device long* stack,long K) {
    bool valid=true;const long phase=state_signed_value(w.view,node,valid);if(!valid){w.error|=1;return;}
    switch(phase){case 0:canonical_literal(w,"\"production\"",12);break;
      case 1:canonical_literal(w,"\"combat_movement\"",17);break;
      case 2:canonical_literal(w,"\"combat\"",8);break;
      case 3:canonical_literal(w,"\"non_combat_movement\"",21);break;
      case 4:canonical_literal(w,"\"place_units\"",13);break;
      default:w.error|=1;}
}
inline void sj_pair_id(thread CanonicalWriter& w,long node,device long* stack,long K) {
    if(!sj_container(w,node,11,2))return;canonical_put(w,'[');sj_id(w,sj_child(w,node,0),stack,K);
    canonical_put(w,',');sj_id(w,sj_child(w,node,1),stack,K);canonical_put(w,']');
}
'''


def _literal(text):
    escaped=text.replace('\\','\\\\').replace('"','\\"')
    return f'canonical_literal(w,"{escaped}",{len(text)});'


def _typed_source():
    kinds={kind for _,fields in SCHEMAS.values() for _,kind in fields.values()}
    kinds.update(kind for _,kind in STATE_FIELDS.values())
    # The schemas are acyclic. Forward declarations permit lexical generation
    # order without recursion or a hard-coded traversal-depth limit.
    pending=list(kinds);all_kinds=set(kinds)|set(SCHEMAS)|{"pair_id"}
    while pending:
        kind=pending.pop()
        if kind.startswith(("map_","vec_","set_","opt_")):
            child=kind.split('_',1)[1]
            if child not in all_kinds:all_kinds.add(child);pending.append(child)
    all_kinds-={"fingerprint","one"}
    output=[HELPERS]
    for kind in sorted(all_kinds):output.append(f'inline void sj_{kind}(thread CanonicalWriter&,long,device long*,long);')
    for kind in sorted(all_kinds):
        if kind in {"id","int","bool","json","u64string","phase","pair_id"}:continue
        lines=[f'inline void sj_{kind}(thread CanonicalWriter& w,long node,device long* stack,long K) {{',
               'if(w.error)return;']
        if kind in SCHEMAS:
            count,fields=SCHEMAS[kind];lines.append(f'if(!sj_container(w,node,10,{count}))return;canonical_put(w,\'{{\');')
            for i,(name,(index,child)) in enumerate(sorted(fields.items())):
                if i:lines.append("canonical_put(w,',');")
                lines.extend((_literal('"'+name+'":'),f'sj_{child}(w,sj_child(w,node,{index}),stack,K);'))
            lines.append("canonical_put(w,'}');")
        elif kind.startswith("opt_"):
            child=kind[4:];lines.extend(('bool valid=true,present=false;const long value=state_optional(w.view,node,present,valid);',
                'if(!valid){w.error|=1;return;}if(!present){canonical_literal(w,"null",4);return;}',
                f'sj_{child}(w,value,stack,K);'))
        elif kind.startswith(("vec_","set_")):
            child=kind[4:];tag=6 if kind.startswith("vec_") else 8
            lines.extend((f'if(!sj_container(w,node,{tag},-1))return;',
                'const long count=state_record(w.view,node)[1];long cursor=node+1,previous=-1;canonical_put(w,\'[\');',
                'for(long i=0;i<count&&!w.error;++i){if(i)canonical_put(w,\',\');'))
            if tag==8:
                read='state_string_id' if child=='id' else 'state_signed_value'
                comparison='!canonical_less(w,previous,current)' if child=='id' else 'previous>=current'
                lines.extend((f'bool ordered=true;const long current={read}(w.view,cursor,ordered);',
                    f'if(!ordered||(i&&{comparison})){{w.error|=1;return;}}previous=current;'))
            lines.extend((
                f'sj_{child}(w,cursor,stack,K);bool valid=true;cursor=state_end(w.view,cursor,valid);if(!valid)w.error|=1;}}',
                "canonical_put(w,']');"))
        elif kind.startswith("map_"):
            child=kind[4:];lines.extend(('if(!sj_container(w,node,7,-1))return;',
                'const long count=state_record(w.view,node)[1];long cursor=node+1,previous=-1;canonical_put(w,\'{\');',
                'for(long i=0;i<count&&!w.error;++i){bool valid=true;const long id=state_string_id(w.view,cursor,valid);',
                'if(!valid||(previous>=0&&!canonical_less(w,previous,id))){w.error|=1;return;}previous=id;',
                'if(i)canonical_put(w,\',\');canonical_string(w,id);canonical_put(w,\':\');',
                'const long value=state_end(w.view,cursor,valid);if(!valid){w.error|=1;return;}',
                f'sj_{child}(w,value,stack,K);cursor=state_end(w.view,value,valid);if(!valid)w.error|=1;}}',
                "canonical_put(w,'}');"))
        else:raise ValueError('Unknown native State JSON kind: '+kind)
        lines.append('}');output.extend(lines)
    output.extend(('inline void sj_state(thread CanonicalWriter& w,long node,device long* stack,long K,long fingerprint) {',
        'if(!sj_container(w,node,10,19))return;const long interface=sj_child(w,node,17);',
        'if(!sj_container(w,interface,13,-1))return;const bool include_interface=state_record(w.view,interface)[1]!=0;',
        "canonical_put(w,'{');bool first=true;"))
    for name,(index,kind) in sorted(STATE_FIELDS.items()):
        if name=="action_interface":output.append('if(include_interface){')
        output.extend(("if(!first)canonical_put(w,',');first=false;",_literal('"'+name+'":')))
        if kind=="fingerprint":output.append('canonical_string(w,fingerprint);')
        elif kind=="one":output.append("canonical_put(w,'1');")
        else:output.append(f'sj_{kind}(w,sj_child(w,node,{index}),stack,K);')
        if name=="action_interface":output.append('}')
    output.extend(("canonical_put(w,'}');",'}'))
    return '\n'.join(output)


SOURCE=GENERIC_SOURCE.split('kernel void canonical_json_subtrees',1)[0]+_typed_source()+r'''
kernel void resident_state_json(
    device const long* records [[buffer(0)]],device const long* lengths [[buffer(1)]],
    device const long* source_errors [[buffer(2)]],device const uchar* prefix [[buffer(3)]],
    device const long* prefix_offsets [[buffer(4)]],device const uchar* suffix [[buffer(5)]],
    device const long* suffix_offsets [[buffer(6)]],device const long* usage [[buffer(7)]],
    device const long* number_words [[buffer(8)]],device const long* number_offsets [[buffer(9)]],
    device const uchar* number_bytes [[buffer(10)]],device uchar* data [[buffer(11)]],
    device long* output_lengths [[buffer(12)]],device long* required [[buffer(13)]],
    device int* errors [[buffer(14)]],device long* stacks [[buffer(15)]],
    device const long* dimensions [[buffer(16)]],uint lane [[thread_position_in_grid]]) {
    const long B=dimensions[0],K=dimensions[1],C=dimensions[2];if(long(lane)>=B)return;
    output_lengths[lane]=required[lane]=0;errors[lane]=0;
    if(source_errors[lane]){errors[lane]=8;return;}
    bool valid=lengths[lane]>=0&&lengths[lane]<=K;
    const auto v=make_packed_state_view(records+ulong(lane)*ulong(K)*5,lengths[lane],K,
        prefix,prefix_offsets,dimensions[3],dimensions[4],suffix,suffix_offsets,dimensions[5],dimensions[6],usage,valid);
    CanonicalWriter w{v,data+ulong(lane)*ulong(C),C,0,0,number_words,number_offsets,number_bytes,dimensions[7],dimensions[8]};
    if(!valid||!sj_container(w,0,10,2)){errors[lane]=1;return;}
    sj_state(w,sj_child(w,0,0),stacks+ulong(lane)*ulong(K)*5,K,dimensions[9]);
    required[lane]=w.position;errors[lane]=w.error|(w.position>C?2:0);
    if(!errors[lane])output_lengths[lane]=w.position;
}
kernel void resident_outer_engine_json(
    device const uchar* state_hex [[buffer(0)]],device const int* source_errors [[buffer(1)]],
    device const int* source_batch_error [[buffer(2)]],device const uchar* rules [[buffer(3)]],
    device uchar* output [[buffer(4)]],device long* lengths [[buffer(5)]],device int* errors [[buffer(6)]],
    device const long* dimensions [[buffer(7)]],device const long* count [[buffer(8)]],
    device int* batch_error [[buffer(9)]],uint lane [[thread_position_in_grid]]) {
    const long B=dimensions[0],R=dimensions[1],C=dimensions[2],actual=count[0];
    const int batch=source_batch_error[0]|((actual<0||actual>B)?1:0);if(lane==0)batch_error[0]=batch;
    if(long(lane)>=B)return;
    lengths[lane]=0;errors[lane]=source_errors[lane]|source_batch_error[0];if(errors[lane])return;
    if(batch){errors[lane]|=batch;return;}if(long(lane)>=actual)return;
    device uchar* bytes=output+ulong(lane)*ulong(C);long position=0;
    constant char* first="{\"rules_id\":";for(long i=0;i<12;++i)bytes[position++]=uchar(first[i]);
    for(long i=0;i<R;++i)bytes[position++]=rules[i];
    constant char* second=",\"state_key\":\"";for(long i=0;i<14;++i)bytes[position++]=uchar(second[i]);
    for(long i=0;i<64;++i)bytes[position++]=state_hex[ulong(lane)*64+ulong(i)];
    bytes[position++]='"';bytes[position++]='}';lengths[lane]=position;
}
'''

_library=None
_lock=threading.Lock()


def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    return _library

@lru_cache(maxsize=32)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device='mps')

@lru_cache(maxsize=1)
def _dummy():return torch.empty(1,dtype=torch.int64,device='mps')


def _quote_bytes(raw):
    output=bytearray(b'"')
    for c in raw:
        if c in (34,92):output.extend((92,c))
        elif c<32:output.extend(('\\u00'+format(c,'02x')).encode('ascii'))
        else:output.append(c)
    output.append(34);return bytes(output)


@dataclass(frozen=True)
class StateIdentityBatch:
    source: object
    state_json: object
    state_keys: object
    engine_json: object
    engine_keys: object


class ResidentStateJson:
    def __init__(self,number_context,*,digest_implementation='reference',digest_group_size=None):
        if type(digest_implementation) is not str or digest_implementation not in {'reference','unrolled'}:
            raise ValueError('Digest implementation must be reference or unrolled')
        if digest_group_size is not None and (type(digest_group_size) is not int or digest_group_size<=0):
            raise ValueError('Digest group size must be None or a positive integer')
        self.digest_implementation=digest_implementation;self.digest_group_size=digest_group_size
        self.number_context=number_context;self.state_context=number_context.state_context
        if _device(self.state_context.device).type!='mps':raise ValueError('State JSON requires explicit Apple GPU execution')
        self.fingerprint=int(self.state_context.prefix_lookup_ids((self.state_context.definition_fingerprint,))[0])
        self.rules_literal=_quote_bytes(self.state_context.rules_id.encode('utf8'))
        self.rules=torch.tensor(bytearray(self.rules_literal),dtype=torch.uint8,device=self.state_context.device)

    def serialize(self,state,*,byte_capacity):
        state._metadata();_device(state.device)
        if state.context is not self.state_context:raise ValueError('State JSON context must match the exact resident state context')
        if type(byte_capacity) is not int or byte_capacity<0:raise ValueError('State JSON byte capacity must be a nonnegative integer')
        B,K=state.records.shape[:2];C=byte_capacity;context=self.number_context
        if B>(1<<32)-1 or B*max(K,C,1)*5>(1<<63)-1:raise OverflowError('State JSON allocation cannot be represented')
        inputs=(state.records,state.lengths,state.errors,state.context.string_bytes,state.context.string_offsets,
                state.string_bytes,state.string_offsets,state.suffix_usage,context.words,context.offsets,context.bytes)
        if any(not value.is_contiguous() or value.device!=state.device for value in inputs):
            raise ValueError('State JSON inputs must remain resident and contiguous')
        if state.context.string_bytes.dtype!=torch.uint8 or state.context.string_bytes.ndim!=1 or \
           state.context.string_offsets.dtype!=torch.int64 or state.context.string_offsets.shape!=(state.context.string_count+1,):
            raise ValueError('State JSON static string arena layout differs')
        if context.words.dtype!=torch.int64 or context.words.ndim!=2 or context.words.shape[1]!=2 or \
           context.offsets.dtype!=torch.int64 or context.offsets.shape!=(context.words.shape[0]+1,) or \
           context.bytes.dtype!=torch.uint8 or context.bytes.ndim!=1:
            raise ValueError('State JSON number arena layout differs')
        data=torch.zeros((B,C),dtype=torch.uint8,device=state.device)
        lengths=torch.empty(B,dtype=torch.int64,device=state.device);required=torch.empty_like(lengths)
        errors=torch.empty(B,dtype=torch.int32,device=state.device)
        count=torch.tensor([B],dtype=torch.int64,device=state.device);batch_error=torch.zeros(1,dtype=torch.int32,device=state.device)
        stack=torch.empty((B,K,5),dtype=torch.int64,device=state.device)
        if B:
            dims=_dimensions((B,K,C,state.context.string_count,state.context.string_bytes.numel(),
                state.string_offsets.numel()-1,state.string_bytes.numel(),context.words.shape[0],context.bytes.numel(),self.fingerprint))
            args=(*inputs,data,lengths,required,errors,stack,dims)
            _kernels().resident_state_json(*(value if value.numel() else _dummy() for value in args),threads=B)
        return CanonicalJsonBatch(data,lengths,required,errors,count,batch_error)

    def outer_engine_json(self,state_keys):
        B=state_keys.hex_bytes.shape[0];C=len(self.rules_literal)+92;device=self.state_context.device
        _device(device)
        if state_keys.hex_bytes.device!=device or state_keys.hex_bytes.dtype!=torch.uint8 or \
           state_keys.hex_bytes.shape!=(B,64) or not state_keys.hex_bytes.is_contiguous():
            raise ValueError('Outer Engine keys require resident contiguous native SHA256 hex bytes')
        for value,dtype,shape in ((state_keys.errors,torch.int32,(B,)),(state_keys.batch_error,torch.int32,(1,)),
                                   (state_keys.count,torch.int64,(1,)),(self.rules,torch.uint8,(len(self.rules_literal),))):
            if value.dtype!=dtype or value.shape!=shape or value.device!=device or not value.is_contiguous():
                raise ValueError('Outer Engine source error/count/rules layout differs')
        data=torch.zeros((B,C),dtype=torch.uint8,device=device);lengths=torch.empty(B,dtype=torch.int64,device=device)
        errors=torch.empty(B,dtype=torch.int32,device=device)
        batch_error=torch.empty(1,dtype=torch.int32,device=device)
        args=(state_keys.hex_bytes,state_keys.errors,state_keys.batch_error,self.rules,data,lengths,errors,
              _dimensions((B,len(self.rules_literal),C)),state_keys.count,batch_error)
        _kernels().resident_outer_engine_json(*(value if value.numel() else _dummy() for value in args),threads=max(B,1))
        return CanonicalJsonBatch(data,lengths,torch.full_like(lengths,C),errors,state_keys.count,batch_error)

    def identities(self,state,*,byte_capacity):
        encoded=self.serialize(state,byte_capacity=byte_capacity)
        state_keys=canonical_json_digests(encoded,implementation=self.digest_implementation,group_size=self.digest_group_size)
        outer=self.outer_engine_json(state_keys)
        result=StateIdentityBatch(state,encoded,state_keys,outer,canonical_json_digests(
            outer,implementation=self.digest_implementation,group_size=self.digest_group_size))
        from .resident_identity_certificates import _certify_authoritative
        return _certify_authoritative(self,result,byte_capacity=byte_capacity)
