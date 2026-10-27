"""Exact terminateChineseTruce and mandatory mixed-stack battle queuing.

This rule helper queues battles; it does not resolve combat, morale, retreats,
declarations or the calendar. Income, Engine validation/Events and randomness
remain separate. Static passable-border/class data are shared once; route
legality and Catalog statistics are deliberately not substituted for this rule.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_state_edits import replace_subtrees
from .device_map_edits import SOURCE as MAP_SOURCE
from .device_strings import intern_bytes

LITERALS=("ccp","kmt","awaiting_combat_rules","chinese_truce_termination","truce_low_morale_eliminates",
          "immediate_land_battles","round","origins","land_entry_origins","truce_breaker",
          "combat_move","airborne_assault","amphibious_assault")


@dataclass(frozen=True)
class ChineseTruceResult:
    state:DeviceStateBatch
    errors:torch.Tensor
    message_ids:torch.Tensor
    battle_ids:torch.Tensor
    battle_counts:torch.Tensor
    required_battle_capacity:torch.Tensor
    required_state_capacity:torch.Tensor
    required_block_capacity:torch.Tensor
    required_string_usage:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE=MAP_SOURCE+r'''
inline bool ct_container(thread const PackedStateView& v,long n,long tag,long count,thread bool& ok){
 const long end=state_end(v,n,ok);if(!ok)return false;device const long* r=state_record(v,n);
 if(r[0]!=tag||r[1]<0||r[1]>(tag==7?(end-n-1)/2:end-n-1)||(count>=0&&r[1]!=count)||r[2]||r[3])ok=false;return ok;
}
inline long ct_index(device const long* ids,long count,long id){for(long i=0;i<count;++i)if(ids[i]==id)return i;return -1;}
inline long ct_optional(thread const PackedStateView& v,long n,thread bool& ok){bool yes=false;const long value=state_optional(v,n,yes,ok);
 return yes?state_string_id(v,value,ok):-1;}
inline bool ct_has(thread const PackedStateView& v,long n,long id,thread bool& ok){ct_container(v,n,8,-1,ok);
 long cursor=n+1;for(long i=0;ok&&i<state_record(v,n)[1];++i){if(state_string_id(v,cursor,ok)==id)return true;cursor=state_end(v,cursor,ok);}return false;
}
inline long ct_text_length(thread const PackedStateView& v,long id,thread bool& ok){
 if(id<0||id>=v.prefix_count+v.suffix_count){ok=false;return 0;}const bool p=id<v.prefix_count;const long i=p?id:id-v.prefix_count;
 device const long* offsets=p?v.prefix_offsets:v.suffix_offsets;const long a=offsets[i],b=offsets[i+1];
 if(a<0||b<a||b>(p?v.prefix_bytes_length:v.suffix_bytes_length)){ok=false;return 0;}return b-a;
}
inline uchar ct_text_byte(thread const PackedStateView& v,long id,long at){const bool p=id<v.prefix_count;const long i=p?id:id-v.prefix_count;
 return p?v.prefix_bytes[v.prefix_offsets[i]+at]:v.suffix_bytes[v.suffix_offsets[i]+at];}
inline long ct_decimal(ulong number,thread char* out){char reverse[20];long n=0;do{reverse[n++]=char('0'+number%10);number/=10;}while(number);
 for(long i=0;i<n;++i)out[i]=reverse[n-i-1];return n;}
inline bool ct_battle_equal(thread const PackedStateView& v,long candidate,ulong serial,long zone,thread bool& ok){
 char digits[20];const long D=ct_decimal(serial,digits),Z=ct_text_length(v,zone,ok),L=ct_text_length(v,candidate,ok);
 if(!ok||L!=14+D+Z)return false;constant char* stem="truce_shared_";
 for(long i=0;i<13;++i)if(ct_text_byte(v,candidate,i)!=uchar(stem[i]))return false;
 for(long i=0;i<D;++i)if(ct_text_byte(v,candidate,13+i)!=uchar(digits[i]))return false;
 if(ct_text_byte(v,candidate,13+D)!='_')return false;
 for(long i=0;i<Z;++i)if(ct_text_byte(v,candidate,14+D+i)!=ct_text_byte(v,zone,i))return false;return true;
}
inline bool ct_member(thread const PackedStateView& v,long unit,long zone,long owner,thread bool& ok){
 if(state_string_id(v,state_child(v,unit,3,ok),ok)!=zone)return false;
 bool carried=false;state_optional(v,state_child(v,unit,8,ok),carried,ok);if(carried)return false;
 return state_string_id(v,state_child(v,unit,2,ok),ok)==owner;
}
inline long ct_origin(thread const PackedStateView& v,long state,long unit,long zone,long active,
 device const long* zones,long Z,device const long* types,long T,device const long* edges,device const long* land,
 device const long* labels,thread bool& is_land,thread long& error,thread long& message,thread bool& ok){
 is_land=false;if(state_string_id(v,state_child(v,unit,2,ok),ok)!=active)return -1;
 const long commitments=state_child(v,unit,11,ok);if(!ct_has(v,commitments,labels[10],ok))return -1;
 const long route=state_child(v,unit,7,ok);ct_container(v,route,6,-1,ok);if(!ok||!state_record(v,route)[1])return -1;
 const long count=state_record(v,route)[1];if(state_string_id(v,state_child(v,route,count-1,ok),ok)!=zone)return -1;
 const long from=count>1?state_string_id(v,state_child(v,route,count-2,ok),ok):state_string_id(v,state_child(v,unit,6,ok),ok);
 const long territories=state_child(v,state,1,ok);if(state_map_find_id(v,territories,from,ok)<0||state_map_find_id(v,territories,zone,ok)<0)return -1;
 const long a=ct_index(zones,Z,from),b=ct_index(zones,Z,zone);if(!ok||a<0||b<0){ok=false;return -1;}
 device const long* edge=edges+(ulong(a)*Z+b)*3;if(edge[1]){error=edge[1];message=edge[2];return -1;}if(!edge[0])return -1;
 const long type=state_string_id(v,state_child(v,unit,1,ok),ok),which=ct_index(types,T,type);
 if(which<0){error=1;return -1;}is_land=land[which]!=0;
 if(is_land&&ct_has(v,commitments,labels[11],ok))is_land=false;
 if(is_land&&ct_has(v,commitments,labels[12],ok))is_land=false;return from;
}
kernel void chinese_truce_plan(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* inherited[[buffer(2)]],device const long* breakers[[buffer(3)]],device const bool* evolution[[buffer(4)]],
 device const bool* selected[[buffer(5)]],device const uchar* prefix[[buffer(6)]],device const long* poffsets[[buffer(7)]],
 device const uchar* suffix[[buffer(8)]],device const long* soffsets[[buffer(9)]],device const long* usage[[buffer(10)]],
 device const long* zones[[buffer(11)]],device const long* types[[buffer(12)]],device const long* edges[[buffer(13)]],
 device const long* land[[buffer(14)]],device const long* order[[buffer(15)]],device const long* labels[[buffer(16)]],
 device long* data[[buffer(17)]],device long* groups[[buffer(18)]],device uchar* names[[buffer(19)]],
 device long* sizes[[buffer(20)]],device bool* wanted[[buffer(21)]],device long* errors[[buffer(22)]],
 device long* messages[[buffer(23)]],device const long* dims[[buffer(24)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],Z=dims[2],T=dims[3],Q=dims[4],L=dims[5];if(long(lane)>=B)return;
 device long* d=data+ulong(lane)*4;d[0]=d[1]=-1;d[2]=d[3]=0;errors[lane]=0;messages[lane]=-1;
 device long* group=groups+ulong(lane)*Z*6;for(long z=0;z<Z;++z){for(long j=0;j<6;++j)group[z*6+j]=0;group[z*6+2]=-1;}
 for(long i=0;i<Q;++i){sizes[ulong(lane)*Q+i]=0;wanted[ulong(lane)*Q+i]=false;}if(!selected[lane])return;
 bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,prefix,poffsets,dims[6],dims[7],suffix,soffsets,dims[8],dims[9],usage,ok);
 ct_container(v,0,10,2,ok);const long state=state_child(v,0,0,ok);ct_container(v,state,10,19,ok);d[0]=state;
 const long politics=state_child(v,state,8,ok);ct_container(v,politics,10,11,ok);
 const bool truce=state_boolean_value(v,state_child(v,politics,0,ok),ok);if(!ok){errors[lane]=3;return;}if(!truce)return;
 if(inherited[lane]){errors[lane]=3;return;}const long breaker=breakers[lane];
 if(breaker!=labels[0]&&breaker!=labels[1]){errors[lane]=2;return;}
 const long clock=state_child(v,state,7,ok);ct_container(v,clock,10,6,ok);long active=-1;
 if(!evolution[lane]){const long phase=state_signed_value(v,state_child(v,clock,2,ok),ok);if(!ok){errors[lane]=3;return;}
   if(phase!=2){errors[lane]=2;return;}const long index=state_signed_value(v,state_child(v,clock,1,ok),ok);
   if(!ok||index<0||index>=dims[10]){errors[lane]=3;return;}active=order[index];if(active!=breaker){errors[lane]=2;return;}}
 d[3]=1;const long units=state_child(v,state,2,ok),territories=state_child(v,state,1,ok);
 ct_container(v,units,7,-1,ok);ct_container(v,territories,7,-1,ok);long cursor=units+1;
 for(long i=0;ok&&i<state_record(v,units)[1];++i){const long unit=cursor+1;ct_container(v,unit,10,14,ok);
   const long zone=state_string_id(v,state_child(v,unit,3,ok),ok);if(state_map_find_id(v,territories,zone,ok)>=0){
     bool carried=false;state_optional(v,state_child(v,unit,8,ok),carried,ok);if(!carried){const long owner=state_string_id(v,state_child(v,unit,2,ok),ok);
       if(owner==labels[0]||owner==labels[1]){const long z=ct_index(zones,Z,zone);if(z<0){ok=false;break;}++group[z*6+(owner==labels[0]?0:1)];}}}
   cursor=state_end(v,unit,ok);}
 if(!ok){errors[lane]=3;return;}long amount=0;for(long z=0;z<Z;++z)if(group[z*6]&&group[z*6+1])group[z*6+2]=amount++;
 d[2]=amount;const long battles=state_child(v,state,12,ok);ct_container(v,battles,7,-1,ok);
 for(long z=0;ok&&z<Z;++z){device long* g=group+z*6;if(g[2]<0)continue;
   const long territory=state_map_find_id(v,territories,zones[z],ok);if(territory<0){errors[lane]=1;return;}
   const long possessor=ct_optional(v,state_child(v,territory,0,ok),ok);
   if(possessor!=labels[0]&&possessor!=labels[1]){errors[lane]=2;return;}
   if(active<0){const long index=state_signed_value(v,state_child(v,clock,1,ok),ok);
     if(!ok||index<0||index>=dims[10]){errors[lane]=3;return;}active=order[index];}
   g[3]=(active==labels[0]||active==labels[1])?active:(possessor==labels[0]?labels[1]:labels[0]);g[4]=g[3]==labels[0]?labels[1]:labels[0];
   if(g[3]==labels[1]){const long nations=state_child(v,state,0,ok),kmt=state_map_find_id(v,nations,labels[1],ok);
     if(kmt<0){errors[lane]=1;return;}g[5]=state_string_equals(v,state_child(v,kmt,3,ok),"minor",5,ok);}
   cursor=units+1;
   for(long i=0;ok&&i<state_record(v,units)[1];++i){const long unit=cursor+1;
     if(ct_member(v,unit,zones[z],g[3],ok)){bool is_land=false;long error=0,message=-1;
       (void)ct_origin(v,state,unit,zones[z],active,zones,Z,types,T,edges,land,labels,is_land,error,message,ok);
       if(error){errors[lane]=error;messages[lane]=message;return;}}cursor=state_end(v,unit,ok);}
   if(!ok){errors[lane]=3;return;}const ulong serial=state_unsigned_value(v,state_child(v,clock,4,ok),ok);
   cursor=battles+1;for(long i=0;ok&&i<state_record(v,battles)[1];++i){const long id=state_string_id(v,cursor,ok),battle=cursor+1;
     if(ct_battle_equal(v,id,serial,zones[z],ok)){errors[lane]=2;return;}cursor=state_end(v,battle,ok);}
   if(!ok){errors[lane]=3;return;}if(g[2]<Q){const long q=long(lane)*Q+g[2];device uchar* out=names+ulong(q)*L;
     char digits[20];const long D=ct_decimal(serial,digits),size=ct_text_length(v,zones[z],ok);constant char* stem="truce_shared_";
     if(14+D+size>L){errors[lane]=5;return;}for(long j=0;j<13;++j)out[j]=uchar(stem[j]);
     for(long j=0;j<D;++j)out[13+j]=uchar(digits[j]);out[13+D]='_';for(long j=0;j<size;++j)out[14+D+j]=ct_text_byte(v,zones[z],j);
     sizes[q]=14+D+size;wanted[q]=true;}
 }
 d[1]=active;if(!ok){errors[lane]=3;return;}if(amount>Q)errors[lane]=5;
}
inline long ct_row(device long* out,long cap,thread long& at,long tag,long meta){const long root=at++;
 if(root<cap){device long* r=out+ulong(root)*5;r[0]=tag;r[1]=meta;r[2]=r[3]=0;r[4]=root+1;}return root;}
inline void ct_end(device long* out,long cap,long root,long end){if(root<cap)out[ulong(root)*5+4]=end;}
inline void ct_id(device long* out,long cap,thread long& at,long id){ct_row(out,cap,at,5,id);}
inline void ct_int(device long* out,long cap,thread long& at,long value){const long root=ct_row(out,cap,at,2,0);
 if(root<cap){out[ulong(root)*5+2]=long(ulong(value)&0xffffffffUL);out[ulong(root)*5+3]=long((ulong(value)>>32)&0xffffffffUL);}}
inline void ct_copy(thread const PackedStateView& v,long node,device long* out,long cap,thread long& at,thread bool& ok){container_copy(v,node,out,cap,at,ok);}
inline void ct_participants(thread const PackedStateView& v,long units,long zone,long owner,device long* out,long cap,thread long& at,thread bool& ok){
 const long root=ct_row(out,cap,at,6,0);long cursor=units+1,count=0;for(long i=0;ok&&i<state_record(v,units)[1];++i){const long unit=cursor+1;
   if(ct_member(v,unit,zone,owner,ok)){ct_id(out,cap,at,state_string_id(v,cursor,ok));++count;}cursor=state_end(v,unit,ok);}
 if(root<cap)out[ulong(root)*5+1]=count;ct_end(out,cap,root,at);
}
inline void ct_battle(thread const PackedStateView& v,long state,long zone,long attacker,long defender,long low,long active,long id,long breaker,
 device const long* zones,long Z,device const long* types,long T,device const long* edges,device const long* land,device const long* labels,
 device long* out,long cap,thread long& at,thread bool& ok){
 const long root=ct_row(out,cap,at,10,10);ct_id(out,cap,at,id);ct_id(out,cap,at,zone);ct_id(out,cap,at,attacker);ct_id(out,cap,at,defender);ct_id(out,cap,at,labels[2]);
 const long units=state_child(v,state,2,ok);ct_participants(v,units,zone,attacker,out,cap,at,ok);ct_participants(v,units,zone,defender,out,cap,at,ok);
 ct_row(out,cap,at,7,0);const long flags=ct_row(out,cap,at,7,low?2:1);ct_id(out,cap,at,labels[3]);ct_int(out,cap,at,1);
 if(low){ct_id(out,cap,at,labels[4]);ct_int(out,cap,at,1);}ct_end(out,cap,flags,at);
 const long data=ct_row(out,cap,at,13,4);ct_id(out,cap,at,labels[8]);const long array=ct_row(out,cap,at,12,0);long cursor=units+1,count=0;
 for(long i=0;ok&&i<state_record(v,units)[1];++i){const long unit=cursor+1;
   if(ct_member(v,unit,zone,attacker,ok)){bool is_land=false;long error=0,message=-1;
     const long from=ct_origin(v,state,unit,zone,active,zones,Z,types,T,edges,land,labels,is_land,error,message,ok);
     if(error){ok=false;return;}if(from>=0&&is_land){ct_id(out,cap,at,from);++count;}}cursor=state_end(v,unit,ok);}
 if(array<cap)out[ulong(array)*5+1]=count;ct_end(out,cap,array,at);
 ct_id(out,cap,at,labels[7]);const long origins=ct_row(out,cap,at,13,0);cursor=units+1;count=0;
 for(long i=0;ok&&i<state_record(v,units)[1];++i){const long unit=cursor+1;
   if(ct_member(v,unit,zone,attacker,ok)){bool is_land=false;long error=0,message=-1;
     const long from=ct_origin(v,state,unit,zone,active,zones,Z,types,T,edges,land,labels,is_land,error,message,ok);
     if(error){ok=false;return;}if(from>=0){ct_id(out,cap,at,state_string_id(v,cursor,ok));ct_id(out,cap,at,from);++count;}}cursor=state_end(v,unit,ok);}
 if(origins<cap)out[ulong(origins)*5+1]=count;ct_end(out,cap,origins,at);
 ct_id(out,cap,at,labels[6]);const long one=ct_row(out,cap,at,4,0);if(one<cap)out[ulong(one)*5+3]=0x3ff00000L;
 ct_id(out,cap,at,labels[9]);ct_id(out,cap,at,breaker);ct_end(out,cap,data,at);ct_end(out,cap,root,at);
}
kernel void chinese_truce_write(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* breakers[[buffer(2)]],device const bool* selected[[buffer(3)]],device const uchar* prefix[[buffer(4)]],
 device const long* poffsets[[buffer(5)]],device const uchar* suffix[[buffer(6)]],device const long* soffsets[[buffer(7)]],
 device const long* usage[[buffer(8)]],device const long* zones[[buffer(9)]],device const long* types[[buffer(10)]],
 device const long* edges[[buffer(11)]],device const long* land[[buffer(12)]],device const long* labels[[buffer(13)]],
 device const long* data[[buffer(14)]],device const long* groups[[buffer(15)]],device const long* ids[[buffer(16)]],
 device long* blocks[[buffer(17)]],device long* sizes[[buffer(18)]],device long* required[[buffer(19)]],
 device long* errors[[buffer(20)]],device const long* dims[[buffer(21)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],Z=dims[2],T=dims[3],Q=dims[4],K=dims[11];if(long(lane)>=B)return;
 sizes[lane]=required[lane]=errors[lane]=0;if(!selected[lane])return;bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
 prefix,poffsets,dims[6],dims[7],suffix,soffsets,dims[8],dims[9],usage,ok);device const long* d=data+ulong(lane)*4;
 device const long* group=groups+ulong(lane)*Z*6;device const long* names=ids+ulong(lane)*Q;const long state=d[0];
 device long* out=blocks+ulong(lane)*K*5;long at=0;const long whole=ct_row(out,K,at,10,19);long field=state+1;
 for(long f=0;ok&&f<19;++f){const long next=state_end(v,field,ok);
   if(f==8){const long root=ct_row(out,K,at,10,11);long cursor=field+1;
     for(long i=0;ok&&i<11;++i){const long end=state_end(v,cursor,ok);
       if(i==0||i==1||i==3)ct_row(out,K,at,1,i==1?1:0);else ct_copy(v,cursor,out,K,at,ok);cursor=end;}ct_end(out,K,root,at);
   }else if(f==12&&d[2]){const long root=ct_row(out,K,at,7,state_record(v,field)[1]+d[2]);long cursor=field+1,z=0;
     for(long i=0;ok&&i<state_record(v,field)[1];++i){const long key=state_string_id(v,cursor,ok),battle=cursor+1;
       while(z<Z){device const long* g=group+z*6;if(g[2]<0){++z;continue;}if(container_compare(v,names[g[2]],key,ok)>0)break;
         ct_id(out,K,at,names[g[2]]);ct_battle(v,state,zones[z],g[3],g[4],g[5],d[1],names[g[2]],breakers[lane],zones,Z,types,T,edges,land,labels,out,K,at,ok);++z;}
       ct_copy(v,cursor,out,K,at,ok);ct_copy(v,battle,out,K,at,ok);cursor=state_end(v,battle,ok);}
     while(ok&&z<Z){device const long* g=group+z*6;if(g[2]>=0){ct_id(out,K,at,names[g[2]]);
         ct_battle(v,state,zones[z],g[3],g[4],g[5],d[1],names[g[2]],breakers[lane],zones,Z,types,T,edges,land,labels,out,K,at,ok);}++z;}ct_end(out,K,root,at);
   }else if(f==13&&d[2]){const long root=ct_row(out,K,at,6,state_record(v,field)[1]+d[2]);long cursor=field+1;
     for(long i=0;ok&&i<state_record(v,field)[1];++i){ct_copy(v,cursor,out,K,at,ok);cursor=state_end(v,cursor,ok);}
     for(long z=0;z<Z;++z)if(group[z*6+2]>=0)ct_id(out,K,at,names[group[z*6+2]]);ct_end(out,K,root,at);
   }else if(f==15&&d[2]){const long root=ct_row(out,K,at,7,0);long cursor=field+1,count=0;bool added=false;
     for(long i=0;ok&&i<state_record(v,field)[1];++i){const long key=state_string_id(v,cursor,ok),value=cursor+1;
       if(!added&&container_compare(v,labels[5],key,ok)<=0){ct_id(out,K,at,labels[5]);ct_int(out,K,at,1);added=true;++count;
         if(key==labels[5]){cursor=state_end(v,value,ok);continue;}}
       ct_copy(v,cursor,out,K,at,ok);ct_copy(v,value,out,K,at,ok);++count;cursor=state_end(v,value,ok);}
     if(!added){ct_id(out,K,at,labels[5]);ct_int(out,K,at,1);++count;}if(root<K)out[ulong(root)*5+1]=count;ct_end(out,K,root,at);
   }else ct_copy(v,field,out,K,at,ok);field=next;
 }
 ct_end(out,K,whole,at);required[lane]=at;if(!ok){errors[lane]=3;return;}if(at>K){errors[lane]=5;return;}sizes[lane]=at;
}
'''
_library=None
_lock=threading.Lock()
@lru_cache(maxsize=32)
def _dimensions(values):return torch.tensor(values,dtype=torch.int64,device="mps")
@lru_cache(maxsize=1)
def _dummy():return torch.zeros(1,dtype=torch.int64,device="mps")
def _kernels():
    global _library
    if _library is None:
        with _lock:
            if _library is None:_library=torch.mps.compile_shader(SOURCE)
    return _library
def _call(kernel,args,count):
    if count:kernel(*(v if v.numel() else _dummy() for v in args),threads=count)
def _tensor(v,state,dtype,shape):
    if not isinstance(v,torch.Tensor) or v.dtype!=dtype or v.device!=state.device or tuple(v.shape)!=tuple(shape) or not v.is_contiguous():
        raise ValueError("Chinese Truce requires complete contiguous resident inputs")
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    output=torch.zeros(shape,dtype=value.dtype,device=value.device);output[tuple(slice(0,n) for n in value.shape)]=value;return output


class ResidentChineseTruce:
    def __init__(self,state_context,native_movement_context):
        if _device(state_context.device).type!="mps" or state_context.definition_fingerprint!=native_movement_context.definition_fingerprint:
            raise ValueError("Chinese Truce requires exact shared Apple GPU State/movement metadata")
        self.state_context=state_context;self.native_context=native_movement_context;self.zones=tuple(native_movement_context.zones)
        self.unit_types=tuple(native_movement_context.unit_types);self.exception_messages=tuple(native_movement_context.exception_messages)
        dev=state_context.device
        self.zone_ids=torch.tensor(state_context.prefix_lookup_ids(self.zones),dtype=torch.int64,device=dev)
        self.type_ids=torch.tensor(state_context.prefix_lookup_ids(self.unit_types),dtype=torch.int64,device=dev)
        edges=torch.tensor(native_movement_context.edge_array(),dtype=torch.int64)
        self.edges=edges[:,:,(1,18,19)].contiguous().to(dev)
        self.land=torch.tensor(native_movement_context.class_array(),dtype=torch.int64)[:,0].contiguous().to(dev)
        self.labels=torch.tensor(state_context.prefix_lookup_ids(LITERALS),dtype=torch.int64,device=dev)
        definition=state_context.native.record_array();node=1
        for _ in range(6):node=int(definition[node,4])
        count=int(definition[node,1]);tokens=[];cursor=node+1
        for _ in range(count):tokens.append(int(definition[cursor,1]));cursor=int(definition[cursor,4])
        self.order=torch.tensor(tokens,dtype=torch.int64,device=dev)
        self.id_bytes=14+20+max((len(z.encode()) for z in self.zones),default=0)

    def reserve(self,state,*,battle_capacity):
        # Each Unit has at least16 packed words/nodes and contributes at most
        # four extra participant/origin nodes. Reserve once, then reuse it.
        # This is headroom, never a legal unit/zone/route/depth limit.
        C=state.records.shape[1];S=C+4*(C//16)+40*battle_capacity+3
        return dict(battle_capacity=battle_capacity,state_capacity=S,block_capacity=max(S,1),
            string_capacity=state.string_offsets.numel()-1+state.lane_count*battle_capacity,
            byte_capacity=state.string_bytes.numel()+state.lane_count*battle_capacity*self.id_bytes)

    def terminate(self,state,breakers,evolution,selected=None,*,battle_capacity,state_capacity=None,block_capacity=None,
                  string_capacity=None,byte_capacity=None):
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Chinese Truce source context differs")
        state._metadata();_device(state.device);B,C=state.records.shape[:2];dev=state.device
        _tensor(breakers,state,torch.int64,(B,));_tensor(evolution,state,torch.bool,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,state,torch.bool,(B,));Q=battle_capacity;S=C if state_capacity is None else state_capacity;K=max(C,1) if block_capacity is None else block_capacity
        T=state.string_offsets.numel()-1 if string_capacity is None else string_capacity;A=state.string_bytes.numel() if byte_capacity is None else byte_capacity
        if any(type(v) is not int or v<0 for v in (Q,S,K,T,A)) or S<C or K<1 or T<state.string_offsets.numel()-1 or A<state.string_bytes.numel():
            raise ValueError("Chinese Truce allocations must preserve all original buffers for rollback")
        if B>2**32-1 or B*Q>2**32-1 or max(Q,S,K,T,A)>2**63-1 or max(B*max(C,S,K,1)*5,B*max(Q,1)*self.id_bytes)*8>2**63-1:
            raise OverflowError("Chinese Truce allocation is not representable; no input truncated")
        for v in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets,state.suffix_usage,
                  state.context.string_bytes,state.context.string_offsets):
            if v.device!=dev or not v.is_contiguous():raise ValueError("Chinese Truce State buffers must stay resident and contiguous")
        zero=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        Z=len(self.zones)
        def dims(source):return _dimensions((B,source.records.shape[1],Z,len(self.unit_types),Q,self.id_bytes,
            source.context.string_count,source.context.string_bytes.numel(),source.string_offsets.numel()-1,source.string_bytes.numel(),self.order.numel(),K))
        def pool(source):return (source.context.string_bytes,source.context.string_offsets,source.string_bytes,source.string_offsets,source.suffix_usage)
        data,groups,errors,messages=zero(B,4),zero(B,Z,6),zero(B),zero(B)
        names=torch.zeros((B*Q,self.id_bytes),dtype=torch.uint8,device=dev);sizes=zero(B*Q);wanted=torch.zeros(B*Q,dtype=torch.bool,device=dev)
        _call(_kernels().chinese_truce_plan,(state.records,state.lengths,state.errors,breakers,evolution,selected,*pool(state),self.zone_ids,self.type_ids,
            self.edges,self.land,self.order,self.labels,data,groups,names,sizes,wanted,errors,messages,dims(state)),B)
        def note(details):
            nonlocal errors
            errors=torch.where(selected&(errors==0)&(details!=0),details,errors)
        wanted&=~(errors!=0).any();added=intern_bytes(state,names,sizes,wanted,string_capacity=T,byte_capacity=A)
        if Q:note(torch.where((added.errors.reshape(B,Q)&8)!=0,5,torch.where(added.errors.reshape(B,Q)!=0,3,0)).amax(1))
        note(torch.where(added.pool_error!=0,3,0).expand(B));current=added.state
        blocks,lengths,required_blocks,write_errors=zero(B,K,5),zero(B),zero(B),zero(B)
        writing=selected&(data[:,3]!=0)&~(errors!=0).any()
        _call(_kernels().chinese_truce_write,(current.records,current.lengths,breakers,writing,*pool(current),self.zone_ids,self.type_ids,
            self.edges,self.land,self.labels,data,groups,added.ids.reshape(B,Q),blocks,lengths,required_blocks,write_errors,dims(current)),B)
        note(write_errors);edited=replace_subtrees(current,data[:,0].contiguous(),blocks,lengths,writing&~(errors!=0).any(),capacity=S)
        note(torch.where(edited.errors!=0,torch.where((edited.errors&8)!=0,5,3),0));committed=~(errors!=0).any()
        output=DeviceStateBatch(state.context,torch.where(committed,edited.state.records,_pad(state.records,(B,S,5))),
            torch.where(committed,edited.state.lengths,state.lengths),torch.where(committed,edited.state.sections,state.sections),
            torch.where(committed,current.string_bytes,_pad(state.string_bytes,(A,))),torch.where(committed,current.string_offsets,_pad(state.string_offsets,(T+1,))),
            state.errors,torch.where(committed,current.suffix_usage,state.suffix_usage))
        old_size=state.section("random")-state.section("state")
        required_state=torch.maximum(edited.required_capacity,state.lengths+required_blocks-old_size)
        return ChineseTruceResult(output,errors,messages,added.ids.reshape(B,Q),data[:,2].contiguous(),data[:,2].contiguous(),
            required_state,required_blocks,added.required_usage,selected&committed,committed)
