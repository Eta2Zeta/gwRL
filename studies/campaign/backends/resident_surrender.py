"""Exact rule-level surrenderNation and queueObjectiveBonus on resident State.

These helpers preserve the native mutation order and quirks. They do not perform
Engine validation, refresh income/politics, append Events, advance a phase or
consume randomness. Queue capacities are allocations with exact retry sizes.
"""
from dataclasses import dataclass
from functools import lru_cache
import threading

import torch

from .device_state import DeviceStateBatch,_device
from .device_state_edits import replace_subtrees
from .device_map_edits import SOURCE as MAP_SOURCE
from .device_strings import intern_bytes
from .resident_political_unit_removal import ResidentPoliticalUnitRemoval

LITERALS=("surrendered","one_china_bonus_eligible_at_surrender","one_china_bonus_awarded",
          "controller_unresolved","direct_axis_control_after_japan_surrender","politics_surrender_queues",
          "one_china_award","completed","national_objective_award","attacker","nation","ships",
          "cavalry","infantry","axis","politics_sequence","ccp","kmt","japan","dadao")
ID_BYTES=max(len("politics_surrender_queues_"),len("one_china_award_"))+11


@dataclass(frozen=True)
class SurrenderResult:
    state:DeviceStateBatch
    errors:torch.Tensor
    generated_ids:torch.Tensor
    queued_ship_ids:torch.Tensor
    queued_ship_counts:torch.Tensor
    required_unit_capacity:torch.Tensor
    required_project_capacity:torch.Tensor
    required_dice_capacity:torch.Tensor
    required_state_capacity:torch.Tensor
    required_block_capacity:torch.Tensor
    required_string_usage:torch.Tensor
    accepted:torch.Tensor
    committed:torch.Tensor


SOURCE=MAP_SOURCE+r'''
inline bool ss_container(thread const PackedStateView& v,long n,long tag,long count,thread bool& ok){
 const long end=state_end(v,n,ok);if(!ok)return false;device const long* r=state_record(v,n);
 if(r[0]!=tag||r[1]<0||r[1]>(tag==7?(end-n-1)/2:end-n-1)||(count>=0&&r[1]!=count)||r[2]||r[3])ok=false;return ok;
}
inline long ss_optional(thread const PackedStateView& v,long root,thread bool& ok){bool yes=false;
 const long n=state_optional(v,root,yes,ok);return yes?state_string_id(v,n,ok):-1;}
inline bool ss_contains(thread const PackedStateView& v,long root,long id,thread bool& ok){
 ss_container(v,root,8,-1,ok);long cursor=root+1;for(long i=0;ok&&i<state_record(v,root)[1];++i){
   if(state_string_id(v,cursor,ok)==id)return true;cursor=state_end(v,cursor,ok);}return false;
}
inline long ss_flag(thread const PackedStateView& v,long root,long id,thread bool& ok){
 ss_container(v,root,7,-1,ok);const long n=state_map_find_id(v,root,id,ok);return n<0?0:state_signed_value(v,n,ok);
}
inline bool ss_naval(long type,device const long* types,long count){for(long i=0;i<count;++i)if(types[i]==type)return true;return false;}
kernel void surrender_units(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* inherited[[buffer(2)]],device const long* nations[[buffer(3)]],device const bool* selected[[buffer(4)]],
 device const uchar* prefix[[buffer(5)]],device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],
 device const long* soffsets[[buffer(8)]],device const long* usage[[buffer(9)]],device long* ids[[buffer(10)]],
 device long* counts[[buffer(11)]],device long* required[[buffer(12)]],device bool* active[[buffer(13)]],
 device long* errors[[buffer(14)]],device const long* labels[[buffer(15)]],device const long* dims[[buffer(16)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],U=dims[2];if(long(lane)>=B)return;counts[lane]=required[lane]=errors[lane]=0;active[lane]=false;
 if(!selected[lane])return;bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
 prefix,poffsets,dims[5],dims[6],suffix,soffsets,dims[7],dims[8],usage,ok);
 if(inherited[lane])ok=false;ss_container(v,0,10,2,ok);const long state=state_child(v,0,0,ok);ss_container(v,state,10,19,ok);
 if(!ok){errors[lane]=3;return;}if(dims[10]){active[lane]=true;return;}
 const long nation=nations[lane];if(nation<0||nation>=v.prefix_count+v.suffix_count){errors[lane]=3;return;}
 const long politics=state_child(v,state,8,ok),surrendered=state_child(v,politics,8,ok);
 if(ss_contains(v,surrendered,nation,ok))return;if(!ok){errors[lane]=3;return;}
 if(nation==labels[16]){errors[lane]=2;return;}active[lane]=true;
 const long units=state_child(v,state,2,ok);ss_container(v,units,7,-1,ok);if(!ok){errors[lane]=3;return;}
 const long amount=state_record(v,units)[1];long cursor=units+1,count=0;
 for(long i=0;ok&&i<amount;++i){const long id=state_string_id(v,cursor,ok),unit=cursor+1;ss_container(v,unit,10,14,ok);
   if(state_string_id(v,state_child(v,unit,2,ok),ok)==nation){if(count<U)ids[ulong(lane)*U+count]=id;++count;}cursor=state_end(v,unit,ok);}
 if(!ok){errors[lane]=3;return;}counts[lane]=count;required[lane]=count?amount:0;if(count>U||required[lane]>U)errors[lane]=5;
}
// scratch nations: exact map order; id,root,controller,player,alliance,major,flagmask.
// flags:1surrendered,2eligible-write,4awarded,8unresolved,16direct-axis.
kernel void surrender_plan(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* nations[[buffer(2)]],device const long* attackers[[buffer(3)]],device const bool* selected[[buffer(4)]],
 device const uchar* prefix[[buffer(5)]],device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],
 device const long* soffsets[[buffer(8)]],device const long* usage[[buffer(9)]],device const long* labels[[buffer(10)]],
 device const long* naval[[buffer(11)]],device long* scratch[[buffer(12)]],device long* ships[[buffer(13)]],
 device long* data[[buffer(14)]],device uchar* names[[buffer(15)]],device long* sizes[[buffer(16)]],device bool* wanted[[buffer(17)]],
 device long* errors[[buffer(18)]],device const long* dims[[buffer(19)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],N=dims[3],P=dims[4];if(long(lane)>=B)return;
 device long* d=data+ulong(lane)*10;for(long i=0;i<10;++i)d[i]=0;d[1]=d[8]=-1;errors[lane]=0;
 for(long i=0;i<6;++i){sizes[ulong(lane)*6+i]=0;wanted[ulong(lane)*6+i]=false;}
 if(!selected[lane])return;bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
 prefix,poffsets,dims[5],dims[6],suffix,soffsets,dims[7],dims[8],usage,ok);
 ss_container(v,0,10,2,ok);const long state=state_child(v,0,0,ok);ss_container(v,state,10,19,ok);d[1]=state;
 const long national=state_child(v,state,0,ok),politics=state_child(v,state,8,ok),dead=state_child(v,politics,8,ok);
 ss_container(v,national,7,-1,ok);if(!ok){errors[lane]=3;return;}const long amount=state_record(v,national)[1];d[9]=amount;
 if(amount>N){errors[lane]=3;return;}device long* table=scratch+ulong(lane)*N*7;long cursor=national+1,who=-1,ccp=-1;
 for(long i=0;ok&&i<amount;++i){device long* row=table+i*7;row[0]=state_string_id(v,cursor,ok);row[1]=cursor+1;
   ss_container(v,row[1],10,12,ok);row[2]=ss_optional(v,state_child(v,row[1],0,ok),ok);
   row[3]=ss_optional(v,state_child(v,row[1],1,ok),ok);row[4]=ss_optional(v,state_child(v,row[1],2,ok),ok);
   row[5]=state_string_equals(v,state_child(v,row[1],3,ok),"major",5,ok);row[6]=0;
   if(row[0]==nations[lane])who=i;if(row[0]==labels[16])ccp=i;cursor=state_end(v,row[1],ok);}
 if(!ok){errors[lane]=3;return;}d[8]=ccp;
 if(!dims[10]){
   if(who<0){errors[lane]=1;return;}d[0]=1;table[who*7+6]|=1;
   if(nations[lane]==labels[17]&&ccp>=0){const long land=state_child(v,state,1,ok);ss_container(v,land,7,-1,ok);cursor=land+1;
     for(long i=0;ok&&i<state_record(v,land)[1];++i){const long territory=cursor+1;ss_container(v,territory,10,2,ok);
       if(ss_optional(v,state_child(v,territory,0,ok),ok)==labels[16])d[5]=1;cursor=state_end(v,territory,ok);}table[ccp*7+6]|=2;}
   const long alliance=table[who*7+4];
   for(long i=0;ok&&i<amount;++i){device long* row=table+i*7;if(row[0]==nations[lane]||row[2]!=nations[lane])continue;
     const long flags=state_child(v,row[1],11,ok),inc=state_map_find_literal(v,flags,"incorporated",12,ok);
     if(inc>=0&&state_signed_value(v,inc,ok))continue;long controller=-1;
     for(long j=0;ok&&j<amount;++j){device long* candidate=table+j*7;
       if(candidate[0]!=nations[lane]&&candidate[4]==alliance&&candidate[5]&&!ss_contains(v,dead,candidate[0],ok)){controller=j;break;}}
     row[2]=controller<0?-1:table[controller*7];
     if(controller>=0)row[3]=table[controller*7+3];
     else if(nations[lane]==labels[18]&&row[0]==labels[19]){row[3]=row[4]=labels[14];row[6]|=16;}
     else{row[3]=-1;row[6]|=8;}}
   const long projects=state_child(v,state,5,ok);ss_container(v,projects,7,-1,ok);cursor=projects+1;long count=0;
   for(long i=0;ok&&i<state_record(v,projects)[1];++i){const long id=state_string_id(v,cursor,ok),p=cursor+1;ss_container(v,p,10,8,ok);
     if(state_string_id(v,state_child(v,p,1,ok),ok)==nations[lane]&&ss_naval(state_string_id(v,state_child(v,p,2,ok),ok),naval,dims[9])){
       if(count<P)ships[ulong(lane)*P+count]=id;++count;}cursor=state_end(v,p,ok);}d[3]=count;
   if(!ok){errors[lane]=3;return;}if(count){bool pending=false;state_optional(v,state_child(v,state,14,ok),pending,ok);
     if(pending){errors[lane]=2;return;}if(attackers[lane]<0||attackers[lane]>=v.prefix_count+v.suffix_count){errors[lane]=3;return;}}
 }
 if(ccp>=0){const long flags=state_child(v,table[ccp*7+1],11,ok);
   const bool eligible=(table[ccp*7+6]&2)?bool(d[5]):bool(ss_flag(v,flags,labels[1],ok));
   d[4]=eligible&&!ss_flag(v,flags,labels[2],ok);if(d[4])table[ccp*7+6]|=4;}
 if(!ok){errors[lane]=3;return;}d[6]=bool(d[3])||bool(d[4]);
 if(d[6]){const long flags=state_child(v,state,15,ok),seq=state_map_find_id(v,flags,labels[15],ok);
   const long start=seq<0?0:state_signed_value(v,seq,ok),steps=long(bool(d[3]))+5*d[4];
   if(!ok||start<INT_MIN||start>INT_MAX){errors[lane]=3;return;}
   if(start>long(INT_MAX)-steps){errors[lane]=2;return;}d[2]=start+steps;long counter=start;
   for(long i=0;i<6;++i){const bool use=i==0?bool(d[3]):bool(d[4]);if(!use)continue;++counter;
     const long row=long(lane)*6+i;device uchar* out=names+ulong(row)*dims[12];constant char* stem=i==0?"politics_surrender_queues_":"one_china_award_";
     const long stem_size=i==0?26:16;for(long j=0;j<stem_size;++j)out[j]=uchar(stem[j]);long at=stem_size;
     if(counter<0)out[at++]='-';ulong number=ulong(counter<0?-counter:counter);char digits[20];long length=0;
     do{digits[length++]=char('0'+number%10);number/=10;}while(number);while(length)out[at++]=uchar(digits[--length]);
     sizes[row]=at;wanted[row]=true;}
 }
 if(d[3]>P||d[3]>dims[11])errors[lane]=5;
}
inline long ss_row(device long* out,long cap,thread long& at,long tag,long meta){const long root=at++;
 if(root<cap){device long* r=out+ulong(root)*5;r[0]=tag;r[1]=meta;r[2]=r[3]=0;r[4]=root+1;}return root;}
inline void ss_end(device long* out,long cap,long root,long end){if(root<cap)out[ulong(root)*5+4]=end;}
inline void ss_int(device long* out,long cap,thread long& at,long value){const long root=ss_row(out,cap,at,2,0);
 if(root<cap){out[ulong(root)*5+2]=long(ulong(value)&0xffffffffUL);out[ulong(root)*5+3]=long((ulong(value)>>32)&0xffffffffUL);}}
inline void ss_id(device long* out,long cap,thread long& at,long id){ss_row(out,cap,at,5,id);}
inline void ss_optional_write(device long* out,long cap,thread long& at,long id){const long root=ss_row(out,cap,at,9,id<0?0:1);
 if(id>=0)ss_id(out,cap,at,id);ss_end(out,cap,root,at);}
inline void ss_copy(thread const PackedStateView& v,long node,device long* out,long cap,thread long& at,thread bool& ok){container_copy(v,node,out,cap,at,ok);}
inline void ss_flags(thread const PackedStateView& v,long node,thread const long* keys,thread const long* values,long count,
 device long* out,long cap,thread long& at,thread bool& ok){
 ss_container(v,node,7,-1,ok);const long root=ss_row(out,cap,at,7,0);long kept=0,cursor=node+1,next=0;bool used[5]={false,false,false,false,false};
 for(long i=0;ok&&i<state_record(v,node)[1];++i){const long key=state_string_id(v,cursor,ok),val=cursor+1;long replacement=-1;
   while(ok){long best=-1;for(long j=0;j<count;++j)if(!used[j]&&(best<0||container_compare(v,keys[j],keys[best],ok)<0))best=j;
     if(best<0||container_compare(v,keys[best],key,ok)>0)break;used[best]=true;
     if(keys[best]==key){replacement=best;break;}ss_id(out,cap,at,keys[best]);ss_int(out,cap,at,values[best]);++kept;}
   ss_id(out,cap,at,key);if(replacement>=0)ss_int(out,cap,at,values[replacement]);else ss_copy(v,val,out,cap,at,ok);++kept;cursor=state_end(v,val,ok);}
 while(ok){long best=-1;for(long j=0;j<count;++j)if(!used[j]&&(best<0||container_compare(v,keys[j],keys[best],ok)<0))best=j;
   if(best<0)break;used[best]=true;ss_id(out,cap,at,keys[best]);ss_int(out,cap,at,values[best]);++kept;}
 if(root<cap)out[ulong(root)*5+1]=kept;ss_end(out,cap,root,at);
}
inline void ss_award(device long* out,long cap,thread long& at,long id,long ordinal,device const long* labels){
 const long root=ss_row(out,cap,at,10,8);ss_id(out,cap,at,id);ss_id(out,cap,at,labels[16]);ss_id(out,cap,at,ordinal<3?labels[12]:labels[13]);
 ss_row(out,cap,at,9,0);ss_int(out,cap,at,1);ss_int(out,cap,at,0);ss_row(out,cap,at,6,0);
 const long flags=ss_row(out,cap,at,7,2);ss_id(out,cap,at,labels[7]);ss_int(out,cap,at,1);ss_id(out,cap,at,labels[8]);ss_int(out,cap,at,1);
 ss_end(out,cap,flags,at);ss_end(out,cap,root,at);
}
inline bool ss_keep_project(thread const PackedStateView& v,long p,long nation,bool surrender,device const long* naval,long count,thread bool& ok){
 if(!surrender||state_string_id(v,state_child(v,p,1,ok),ok)!=nation)return true;
 return ss_naval(state_string_id(v,state_child(v,p,2,ok),ok),naval,count);
}
inline void ss_projects(thread const PackedStateView& v,long node,long nation,bool surrender,bool bonus,device const long* naval,long count,
 device const long* ids,device const long* labels,device long* out,long cap,thread long& at,thread bool& ok){
 ss_container(v,node,7,-1,ok);const long root=ss_row(out,cap,at,7,0);long kept=0,cursor=node+1;bool used[5]={false,false,false,false,false};
 for(long i=0;ok&&i<state_record(v,node)[1];++i){const long key=state_string_id(v,cursor,ok),p=cursor+1;
   if(!ss_keep_project(v,p,nation,surrender,naval,count,ok)){cursor=state_end(v,p,ok);continue;}
   while(bonus&&ok){long best=-1;for(long j=0;j<5;++j)if(!used[j]&&(best<0||container_compare(v,ids[j+1],ids[best+1],ok)<0))best=j;
     if(best<0||container_compare(v,ids[best+1],key,ok)>0)break;used[best]=true;if(ids[best+1]==key)break;
     ss_id(out,cap,at,ids[best+1]);ss_award(out,cap,at,ids[best+1],best,labels);++kept;}
   ss_id(out,cap,at,key);ss_copy(v,p,out,cap,at,ok);++kept;cursor=state_end(v,p,ok);}
 while(bonus&&ok){long best=-1;for(long j=0;j<5;++j)if(!used[j]&&(best<0||container_compare(v,ids[j+1],ids[best+1],ok)<0))best=j;
   if(best<0)break;used[best]=true;ss_id(out,cap,at,ids[best+1]);ss_award(out,cap,at,ids[best+1],best,labels);++kept;}
 if(root<cap)out[ulong(root)*5+1]=kept;ss_end(out,cap,root,at);
}
inline void ss_parameters(device long* out,long cap,thread long& at,long nation,long attacker,device const long* ships,long count,device const long* labels){
 const long root=ss_row(out,cap,at,13,3);ss_id(out,cap,at,labels[9]);ss_id(out,cap,at,attacker);
 ss_id(out,cap,at,labels[10]);ss_id(out,cap,at,nation);ss_id(out,cap,at,labels[11]);const long array=ss_row(out,cap,at,12,count);
 for(long i=0;i<count;++i)ss_id(out,cap,at,ships[i]);ss_end(out,cap,array,at);ss_end(out,cap,root,at);
}
inline void ss_pending(thread const PackedStateView& v,long node,long id,long nation,long attacker,device const long* ships,long count,
 device const long* labels,device long* out,long cap,thread long& at,thread bool& ok){
 ss_container(v,node,7,-1,ok);const long root=ss_row(out,cap,at,7,0);long cursor=node+1,kept=0;bool added=false;
 for(long i=0;ok&&i<state_record(v,node)[1];++i){const long key=state_string_id(v,cursor,ok),val=cursor+1;
   if(!added&&container_compare(v,id,key,ok)<=0){ss_id(out,cap,at,id);ss_parameters(out,cap,at,nation,attacker,ships,count,labels);added=true;++kept;
     if(id==key){cursor=state_end(v,val,ok);continue;}}
   ss_id(out,cap,at,key);ss_copy(v,val,out,cap,at,ok);++kept;cursor=state_end(v,val,ok);}
 if(!added){ss_id(out,cap,at,id);ss_parameters(out,cap,at,nation,attacker,ships,count,labels);++kept;}
 if(root<cap)out[ulong(root)*5+1]=kept;ss_end(out,cap,root,at);
}
inline void ss_dead(thread const PackedStateView& v,long node,long nation,device long* out,long cap,thread long& at,thread bool& ok){
 const long root=ss_row(out,cap,at,8,state_record(v,node)[1]+1);bool added=false;long cursor=node+1;
 for(long i=0;ok&&i<state_record(v,node)[1];++i){const long id=state_string_id(v,cursor,ok);
   if(!added&&container_compare(v,nation,id,ok)<0){ss_id(out,cap,at,nation);added=true;}ss_id(out,cap,at,id);cursor=state_end(v,cursor,ok);}
 if(!added)ss_id(out,cap,at,nation);ss_end(out,cap,root,at);
}
kernel void surrender_write(device const long* records[[buffer(0)]],device const long* lengths[[buffer(1)]],
 device const long* nations[[buffer(2)]],device const long* attackers[[buffer(3)]],device const bool* selected[[buffer(4)]],
 device const uchar* prefix[[buffer(5)]],device const long* poffsets[[buffer(6)]],device const uchar* suffix[[buffer(7)]],
 device const long* soffsets[[buffer(8)]],device const long* usage[[buffer(9)]],device const long* labels[[buffer(10)]],
 device const long* naval[[buffer(11)]],device const long* scratch[[buffer(12)]],device const long* ships[[buffer(13)]],
 device const long* data[[buffer(14)]],device const long* ids[[buffer(15)]],device long* blocks[[buffer(16)]],
 device long* sizes[[buffer(17)]],device long* required[[buffer(18)]],device long* errors[[buffer(19)]],device const long* dims[[buffer(20)]],uint lane[[thread_position_in_grid]]){
 const long B=dims[0],C=dims[1],N=dims[3],P=dims[4],K=dims[13];if(long(lane)>=B)return;
 sizes[lane]=required[lane]=errors[lane]=0;if(!selected[lane])return;bool ok=true;auto v=make_packed_state_view(records+ulong(lane)*C*5,lengths[lane],C,
 prefix,poffsets,dims[5],dims[6],suffix,soffsets,dims[7],dims[8],usage,ok);
 device const long* d=data+ulong(lane)*10;device const long* table=scratch+ulong(lane)*N*7;
 device const long* generated=ids+ulong(lane)*6;device const long* ship=ships+ulong(lane)*P;
 const bool surrender=d[0],bonus=d[4];const long state=d[1],nation=nations[lane],attacker=attackers[lane];
 device long* out=blocks+ulong(lane)*K*5;long at=0;const long whole=ss_row(out,K,at,10,19);long field=state+1;
 for(long f=0;ok&&f<19;++f){const long next=state_end(v,field,ok);
   if(f==0){const long root=ss_row(out,K,at,7,d[9]);
     for(long i=0;ok&&i<d[9];++i){device const long* row=table+i*7;ss_id(out,K,at,row[0]);const long nr=ss_row(out,K,at,10,12);long part=row[1]+1;
       for(long j=0;ok&&j<12;++j){const long end=state_end(v,part,ok);
         if(j<=2)ss_optional_write(out,K,at,row[2+j]);
         else if(j==4&&surrender&&row[0]==nation){bool present=false;state_optional(v,part,present,ok);const long opt=ss_row(out,K,at,9,present?1:0);
           if(present)ss_int(out,K,at,0);ss_end(out,K,opt,at);}
         else if(j==11){long keys[5],values[5];long count=0;
           if(row[6]&1){keys[count]=labels[0];values[count++]=1;}if(row[6]&2){keys[count]=labels[1];values[count++]=d[5];}
           if(row[6]&4){keys[count]=labels[2];values[count++]=1;}if(row[6]&8){keys[count]=labels[3];values[count++]=1;}
           if(row[6]&16){keys[count]=labels[4];values[count++]=1;}ss_flags(v,part,keys,values,count,out,K,at,ok);}
         else ss_copy(v,part,out,K,at,ok);part=end;}ss_end(out,K,nr,at);}ss_end(out,K,root,at);
   }else if(f==1&&surrender){const long root=ss_row(out,K,at,7,state_record(v,field)[1]);long cursor=field+1;
     for(long i=0;ok&&i<state_record(v,field)[1];++i){ss_copy(v,cursor,out,K,at,ok);const long territory=cursor+1,end=state_end(v,territory,ok);
       if(ss_optional(v,state_child(v,territory,0,ok),ok)==nation){const long tr=ss_row(out,K,at,10,2);ss_row(out,K,at,9,0);
         ss_copy(v,state_child(v,territory,1,ok),out,K,at,ok);ss_end(out,K,tr,at);}else ss_copy(v,territory,out,K,at,ok);cursor=end;}
     ss_end(out,K,root,at);
   }else if(f==5)ss_projects(v,field,nation,surrender,bonus,naval,dims[9],generated,labels,out,K,at,ok);
   else if(f==6&&surrender){const long root=ss_row(out,K,at,7,0);long cursor=field+1,kept=0;
     for(long i=0;ok&&i<state_record(v,field)[1];++i){const long repair=cursor+1,end=state_end(v,repair,ok);
       if(state_string_id(v,state_child(v,repair,1,ok),ok)!=nation){ss_copy(v,cursor,out,K,at,ok);ss_copy(v,repair,out,K,at,ok);++kept;}cursor=end;}
     if(root<K)out[ulong(root)*5+1]=kept;ss_end(out,K,root,at);
   }else if(f==8&&surrender){const long root=ss_row(out,K,at,10,11);long cursor=field+1;
     for(long i=0;ok&&i<11;++i){const long end=state_end(v,cursor,ok);if(i==8)ss_dead(v,cursor,nation,out,K,at,ok);
       else if(i==10&&d[3])ss_pending(v,cursor,generated[0],nation,attacker,ship,d[3],labels,out,K,at,ok);
       else ss_copy(v,cursor,out,K,at,ok);cursor=end;}ss_end(out,K,root,at);
   }else if(f==14&&d[3]){const long optional=ss_row(out,K,at,9,1),request=ss_row(out,K,at,10,5);
     ss_id(out,K,at,generated[0]);ss_id(out,K,at,labels[5]);ss_id(out,K,at,attacker);ss_id(out,K,at,generated[0]);const long dice=ss_row(out,K,at,6,d[3]);
     for(long i=0;i<d[3];++i){const long die=ss_row(out,K,at,10,4);ss_int(out,K,at,12);ss_int(out,K,at,0);ss_row(out,K,at,8,0);ss_int(out,K,at,0);ss_end(out,K,die,at);}
     ss_end(out,K,dice,at);ss_end(out,K,request,at);ss_end(out,K,optional,at);
   }else if(f==15&&d[6]){long key=labels[15],value=d[2];ss_flags(v,field,&key,&value,1,out,K,at,ok);}
   else ss_copy(v,field,out,K,at,ok);field=next;
 }
 ss_end(out,K,whole,at);required[lane]=at;if(!ok){errors[lane]=3;return;}if(at>K){errors[lane]=5;return;}sizes[lane]=at;
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
        raise ValueError("Surrender requires complete contiguous resident inputs")
def _pad(value,shape):
    if tuple(value.shape)==tuple(shape):return value
    output=torch.zeros(shape,dtype=value.dtype,device=value.device);output[tuple(slice(0,n) for n in value.shape)]=value;return output


class ResidentSurrender:
    def __init__(self,state_context,removal,native_recruitment_context):
        if _device(state_context.device).type!="mps" or removal.state_context is not state_context:
            raise ValueError("Surrender requires shared exact Apple GPU State/removal contexts")
        if native_recruitment_context.wire_context_fingerprint!=state_context.wire_context_fingerprint:
            raise ValueError("Surrender catalog/static wire context differs")
        self.state_context=state_context;self.removal=removal
        self.labels=torch.tensor(state_context.prefix_lookup_ids(LITERALS),dtype=torch.int64,device=state_context.device)
        self.naval=torch.tensor(state_context.prefix_lookup_ids(native_recruitment_context.naval_types),dtype=torch.int64,device=state_context.device)
        # Once-only typed immutable Definition metadata; no JSON/host state walk.
        rows=state_context.native.record_array();node=1
        for _ in range(5):node=int(rows[node,4])
        self.nation_capacity=int(rows[node,1])

    def reserve(self,state,*,unit_capacity,project_capacity):
        S=state.records.shape[1]+100+6*project_capacity+6*self.nation_capacity
        return dict(unit_capacity=unit_capacity,project_capacity=project_capacity,dice_capacity=project_capacity,
            state_capacity=S,block_capacity=max(S,1),string_capacity=state.string_offsets.numel()-1+6*state.lane_count,
            byte_capacity=state.string_bytes.numel()+6*state.lane_count*ID_BYTES)

    def surrender(self,state,nations,attackers,selected=None,**capacities):
        return self._apply(state,nations,attackers,selected,False,**capacities)

    def queue_bonus(self,state,selected=None,*,state_capacity=None,block_capacity=None,string_capacity=None,byte_capacity=None):
        blank=torch.full((state.lane_count,),-1,dtype=torch.int64,device=state.device)
        return self._apply(state,blank,blank,selected,True,unit_capacity=0,project_capacity=0,dice_capacity=0,
            state_capacity=state_capacity,block_capacity=block_capacity,string_capacity=string_capacity,byte_capacity=byte_capacity)

    def _apply(self,state,nations,attackers,selected,bonus_only,*,unit_capacity,project_capacity,dice_capacity,
               state_capacity=None,block_capacity=None,string_capacity=None,byte_capacity=None):
        if not isinstance(state,DeviceStateBatch) or state.context is not self.state_context:raise ValueError("Surrender State source differs")
        state._metadata();_device(state.device);B,C=state.records.shape[:2];dev=state.device
        for v in (nations,attackers):_tensor(v,state,torch.int64,(B,))
        if selected is None:selected=torch.ones(B,dtype=torch.bool,device=dev)
        _tensor(selected,state,torch.bool,(B,));U,P,D=unit_capacity,project_capacity,dice_capacity
        S=C if state_capacity is None else state_capacity;K=max(C,1) if block_capacity is None else block_capacity
        T=state.string_offsets.numel()-1 if string_capacity is None else string_capacity
        A=state.string_bytes.numel() if byte_capacity is None else byte_capacity
        if any(type(v) is not int or v<0 for v in (U,P,D,S,K,T,A)) or S<C or K<1 or T<state.string_offsets.numel()-1 or A<state.string_bytes.numel():
            raise ValueError("Surrender allocations must preserve complete original buffers for rollback")
        if B>2**32-1 or max(U,P,D,S,K,T,A)>2**63-1 or max(B*max(C,S,K,1)*5,B*max(U,P,self.nation_capacity,1)*7)*8>2**63-1:
            raise OverflowError("Surrender allocation is not representable; no input truncated")
        for v in (state.records,state.lengths,state.sections,state.errors,state.string_bytes,state.string_offsets,state.suffix_usage,
                  state.context.records,state.context.string_bytes,state.context.string_offsets):
            if v.device!=dev or not v.is_contiguous():raise ValueError("Surrender source must stay resident and contiguous")
        zero=lambda *shape:torch.zeros(shape,dtype=torch.int64,device=dev)
        def dims(source):return _dimensions((B,source.records.shape[1],U,self.nation_capacity,P,source.context.string_count,
            source.context.string_bytes.numel(),source.string_offsets.numel()-1,source.string_bytes.numel(),self.naval.numel(),int(bonus_only),D,ID_BYTES,K))
        def pool(source):return (source.context.string_bytes,source.context.string_offsets,source.string_bytes,source.string_offsets,source.suffix_usage)
        owned=torch.full((B,U),-1,dtype=torch.int64,device=dev);counts,needed_units,errors=zero(B),zero(B),zero(B)
        active=torch.zeros(B,dtype=torch.bool,device=dev)
        _call(_kernels().surrender_units,(state.records,state.lengths,state.errors,nations,selected,*pool(state),owned,counts,needed_units,active,errors,self.labels,dims(state)),B)
        def note(details):
            nonlocal errors
            errors=torch.where(selected&(errors==0)&(details!=0),details,errors)
        removed=self.removal.remove(state,owned,counts,active&~(errors!=0).any(),unit_capacity=U,state_capacity=S,block_capacity=K)
        note(removed.errors);current=removed.state
        scratch=zero(B,self.nation_capacity,7);ships=torch.full((B,P),-1,dtype=torch.int64,device=dev);data=zero(B,10)
        names=torch.zeros((B*6,ID_BYTES),dtype=torch.uint8,device=dev);sizes=zero(B*6);wanted=torch.zeros(B*6,dtype=torch.bool,device=dev);plan_errors=zero(B)
        _call(_kernels().surrender_plan,(current.records,current.lengths,nations,attackers,active&~(errors!=0).any(),*pool(current),self.labels,self.naval,
            scratch,ships,data,names,sizes,wanted,plan_errors,dims(current)),B)
        note(plan_errors);wanted&=~(errors!=0).any()
        added=intern_bytes(current,names,sizes,wanted,string_capacity=T,byte_capacity=A)
        note(torch.where((added.errors.reshape(B,6)&8)!=0,5,torch.where(added.errors.reshape(B,6)!=0,3,0)).amax(1))
        note(torch.where(added.pool_error!=0,3,0).expand(B));current=added.state
        blocks,lengths,required_blocks,write_errors=zero(B,K,5),zero(B),zero(B),zero(B)
        writing=active&~(errors!=0).any()&((data[:,0]!=0)|(data[:,4]!=0))
        _call(_kernels().surrender_write,(current.records,current.lengths,nations,attackers,writing,*pool(current),self.labels,self.naval,
            scratch,ships,data,added.ids.reshape(B,6),blocks,lengths,required_blocks,write_errors,dims(current)),B)
        note(write_errors)
        edited=replace_subtrees(current,data[:,1].contiguous(),blocks,lengths,writing&~(errors!=0).any(),capacity=S)
        note(torch.where(edited.errors!=0,torch.where((edited.errors&8)!=0,5,3),0));committed=~(errors!=0).any()
        output=DeviceStateBatch(state.context,torch.where(committed,edited.state.records,_pad(state.records,(B,S,5))),
            torch.where(committed,edited.state.lengths,state.lengths),torch.where(committed,edited.state.sections,state.sections),
            torch.where(committed,current.string_bytes,_pad(state.string_bytes,(A,))),torch.where(committed,current.string_offsets,_pad(state.string_offsets,(T+1,))),
            state.errors,torch.where(committed,current.suffix_usage,state.suffix_usage))
        # Exact complete-State replacement requirement, independent of padding.
        old_size=current.section("random")-current.section("state")
        required_state=torch.maximum(torch.maximum(removed.required_state_capacity,edited.required_capacity),current.lengths+required_blocks-old_size)
        return SurrenderResult(output,errors,added.ids.reshape(B,6),ships,data[:,3].contiguous(),needed_units,
            data[:,3].contiguous(),data[:,3].contiguous(),required_state,torch.maximum(removed.required_block_capacity,required_blocks),
            added.required_usage,selected&committed,committed)
