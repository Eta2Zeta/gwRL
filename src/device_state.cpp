#include "game/device_state.hpp"
#include "game/catalog.hpp"

#include <bit>
#include <cmath>
#include <limits>
#include <tuple>
#include <type_traits>

namespace game::campaign {
struct DeviceStateAccess {
    static const RandomStreams& random(const Engine& engine) { return engine.random_; }
    static std::shared_ptr<const Rules> rules(const Engine& engine) { return engine.rules_; }
    static Engine restore(State state, std::shared_ptr<const Rules> rules, RandomStreams random) {
        if (random.active != "actual" && random.active != "search" && random.active != "training")
            throw std::invalid_argument("Unknown device random stream");
        if (random.tapePosition > random.testTape.size()) throw std::invalid_argument("Device dice tape cursor outside tape");
        for (int face : random.testTape) if (face <= 0) throw std::invalid_argument("Device dice tape has invalid face");
        Engine result(std::move(state), std::move(rules));
        result.random_ = std::move(random);
        return result;
    }
};
namespace {
using V = json::Value;
void require(bool yes, const char* message) { if (!yes) throw std::invalid_argument(message); }
std::int64_t count(std::size_t value) {
    if (value > static_cast<std::size_t>(std::numeric_limits<std::int64_t>::max()))
        throw std::length_error("Device state count is not representable; no truncation");
    return static_cast<std::int64_t>(value);
}
template<class T> using Bare = std::remove_cvref_t<T>;
template<class T> constexpr bool record =
    std::is_same_v<T, FactionDefinition> || std::is_same_v<T, NationState> || std::is_same_v<T, TerritoryState> ||
    std::is_same_v<T, UnitState> || std::is_same_v<T, FacilityState> || std::is_same_v<T, RailState> ||
    std::is_same_v<T, BuildProject> || std::is_same_v<T, RepairJob> || std::is_same_v<T, Action> ||
    std::is_same_v<T, Decision> || std::is_same_v<T, BattleState> || std::is_same_v<T, DieSpec> ||
    std::is_same_v<T, ChanceRequest> || std::is_same_v<T, TurnSnapshot> || std::is_same_v<T, Clock> ||
    std::is_same_v<T, PoliticalState> || std::is_same_v<T, Event> || std::is_same_v<T, State> ||
    std::is_same_v<T, RandomStreams>;

// Structured bindings deliberately name EVERY member, including derived members
// which are explicitly excluded. A newly added native member fails compilation
// until its transport/derived status is consciously assigned here.
template<class T> auto members(T& v) {
    using U = Bare<T>;
    if constexpr (std::is_same_v<U, FactionDefinition>) { auto&[a,b,c,d,e]=v;return std::tie(a,b,c,d,e); }
    else if constexpr (std::is_same_v<U, NationState>) { auto&[a,b,c,d,e,f,g,h,i,j,k,l]=v;return std::tie(a,b,c,d,e,f,g,h,i,j,k,l); }
    else if constexpr (std::is_same_v<U, TerritoryState>) { auto&[a,b]=v;return std::tie(a,b); }
    else if constexpr (std::is_same_v<U, UnitState>) { auto&[a,b,c,d,e,f,g,h,i,j,k,l,m,n]=v;return std::tie(a,b,c,d,e,f,g,h,i,j,k,l,m,n); }
    else if constexpr (std::is_same_v<U, FacilityState>) { auto&[a,b,c,d,e]=v;return std::tie(a,b,c,d,e); }
    else if constexpr (std::is_same_v<U, RailState>) { auto&[a,b,c,d]=v;return std::tie(a,b,c,d); }
    else if constexpr (std::is_same_v<U, BuildProject>) { auto&[a,b,c,d,e,f,g,h]=v;return std::tie(a,b,c,d,e,f,g,h); }
    else if constexpr (std::is_same_v<U, RepairJob>) { auto&[a,b,c,d,e,f,g]=v;return std::tie(a,b,c,d,e,f,g); }
    else if constexpr (std::is_same_v<U, Action>) { auto&[a,b,c,d,e,f,derived]=v;(void)derived;return std::tie(a,b,c,d,e,f); }
    else if constexpr (std::is_same_v<U, Decision>) { auto&[a,b,c,d,e,f]=v;return std::tie(a,b,c,d,e,f); }
    else if constexpr (std::is_same_v<U, BattleState>) { auto&[a,b,c,d,e,f,g,h,i,j]=v;return std::tie(a,b,c,d,e,f,g,h,i,j); }
    else if constexpr (std::is_same_v<U, DieSpec>) { auto&[a,b,c,d]=v;return std::tie(a,b,c,d); }
    else if constexpr (std::is_same_v<U, ChanceRequest>) { auto&[a,b,c,d,e]=v;return std::tie(a,b,c,d,e); }
    else if constexpr (std::is_same_v<U, TurnSnapshot>) { auto&[a,b]=v;return std::tie(a,b); }
    else if constexpr (std::is_same_v<U, Clock>) { auto&[a,b,c,d,e,f]=v;return std::tie(a,b,c,d,e,f); }
    else if constexpr (std::is_same_v<U, PoliticalState>) { auto&[a,b,c,d,e,f,g,h,i,j,k]=v;return std::tie(a,b,c,d,e,f,g,h,i,j,k); }
    else if constexpr (std::is_same_v<U, Event>) { auto&[a,b,c]=v;return std::tie(a,b,c); }
    else if constexpr (std::is_same_v<U, State>) { auto&[definition,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s]=v;(void)definition;return std::tie(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s); }
    else if constexpr (std::is_same_v<U, RandomStreams>) { auto&[a,b,c,d,e,f]=v;return std::tie(a,b,c,d,e,f); }
}
template<class T> struct is_vector : std::false_type {};
template<class T, class A> struct is_vector<std::vector<T,A>> : std::true_type {};
template<class T> struct is_map : std::false_type {};
template<class K,class T,class C,class A> struct is_map<std::map<K,T,C,A>> : std::true_type {};
template<class T> struct is_set : std::false_type {};
template<class T,class C,class A> struct is_set<std::set<T,C,A>> : std::true_type {};
template<class T> struct is_optional : std::false_type {};
template<class T> struct is_optional<std::optional<T>> : std::true_type {};
template<class T> struct is_pair : std::false_type {};
template<class A,class B> struct is_pair<std::pair<A,B>> : std::true_type {};

struct Pool {
    const std::vector<std::string>& prefix;
    std::vector<std::string>& suffix;
    std::map<std::string,std::int64_t> index;
    Pool(const std::vector<std::string>& p, std::vector<std::string>& s):prefix(p),suffix(s) {
        for (const auto& text : prefix) index.emplace(text,count(index.size()));
        for (const auto& text : suffix) index.emplace(text,count(index.size()));
    }
    std::int64_t intern(const std::string& text) {
        const auto found=index.find(text);if(found!=index.end())return found->second;
        const auto id=count(prefix.size()+suffix.size());suffix.push_back(text);index.emplace(text,id);return id;
    }
};
struct Writer {
    std::vector<DeviceRecord>& nodes;
    Pool& pool;
    std::size_t begin(DeviceTag tag, std::int64_t size=0, std::uint64_t bits=0) {
        const auto i=nodes.size();count(i+1);
        nodes.push_back({static_cast<std::int64_t>(tag),size,static_cast<std::int64_t>(bits&UINT64_C(0xffffffff)),
                         static_cast<std::int64_t>(bits>>32),0});return i;
    }
    void end(std::size_t i) { nodes[i][4]=count(nodes.size()); }
    template<class T> void put(const T& value) {
        using U=Bare<T>;
        if constexpr (std::is_same_v<U,V>) json(value);
        else if constexpr (std::is_same_v<U,bool>) {auto i=begin(DeviceTag::Boolean,value);end(i);}
        else if constexpr (std::is_integral_v<U> && std::is_signed_v<U>) {
            auto i=begin(DeviceTag::SignedInteger,0,std::bit_cast<std::uint64_t>(static_cast<std::int64_t>(value)));end(i);
        } else if constexpr (std::is_integral_v<U> && std::is_unsigned_v<U>) {auto i=begin(DeviceTag::UnsignedInteger,0,value);end(i);}
        else if constexpr (std::is_enum_v<U>) {put(static_cast<std::underlying_type_t<U>>(value));}
        else if constexpr (std::is_same_v<U,std::string>) {auto i=begin(DeviceTag::String,pool.intern(value));end(i);}
        else if constexpr (is_optional<U>::value) {auto i=begin(DeviceTag::Optional,value.has_value());if(value)put(*value);end(i);}
        else if constexpr (is_vector<U>::value || is_set<U>::value) {
            auto i=begin(is_vector<U>::value?DeviceTag::Sequence:DeviceTag::Set,count(value.size()));
            for(const auto& child:value)put(child);end(i);
        } else if constexpr (is_map<U>::value) {
            auto i=begin(DeviceTag::Map,count(value.size()));for(const auto&[key,child]:value){put(key);put(child);}end(i);
        } else if constexpr (is_pair<U>::value) {auto i=begin(DeviceTag::Pair,2);put(value.first);put(value.second);end(i);}
        else if constexpr (record<U>) tuple(members(value));
        else static_assert(sizeof(U)==0,"Device state member has no lossless encoding");
    }
    template<class... T> void tuple(const std::tuple<T...>& values) {
        auto i=begin(DeviceTag::Record,sizeof...(T));std::apply([&](const auto&...item){(put(item),...);},values);end(i);
    }
    void json(const V& value) {
        if(value.isNull()){auto i=begin(DeviceTag::Null);end(i);}
        else if(value.isBool())put(value.asBool());
        else if(value.isNumber()) {
            const double number=value.asNumber();require(std::isfinite(number),"Device JSON contains a nonfinite number");
            auto i=begin(DeviceTag::NumberBits,0,std::bit_cast<std::uint64_t>(number));end(i);
        } else if(value.isString())put(value.asString());
        else if(value.isArray()) {auto i=begin(DeviceTag::JsonArray,count(value.asArray().size()));for(const auto&child:value.asArray())json(child);end(i);}
        else {auto i=begin(DeviceTag::JsonObject,count(value.asObject().size()));for(const auto&[key,child]:value.asObject()){put(key);json(child);}end(i);}
    }
};
void flattenStrings(const std::vector<std::string>& strings,std::vector<std::uint8_t>& bytes,std::vector<std::int64_t>& offsets) {
    bytes.clear();offsets={0};for(const auto& value:strings){count(bytes.size()+value.size());bytes.insert(bytes.end(),value.begin(),value.end());offsets.push_back(count(bytes.size()));}
}
struct Reader {
    const DeviceRecord* nodes;
    std::size_t size, cursor=0;
    const std::vector<std::string>& prefix;
    const std::vector<std::string>& suffix;
    const DeviceRecord& next(DeviceTag expected) {
        require(cursor<size,"Truncated device state");const auto& row=nodes[cursor];
        require(row[0]==static_cast<std::int64_t>(expected),"Device state field has a wrong type");
        require(row[1]>=0&&row[2]>=0&&row[2]<=UINT32_MAX&&row[3]>=0&&row[3]<=UINT32_MAX&&
                row[4]>count(cursor)&&row[4]<=count(size),"Invalid device state record");++cursor;return row;
    }
    void finish(const DeviceRecord& node) {require(count(cursor)==node[4],"Unknown/missing device state fields or invalid subtree length");}
    std::uint64_t bits(const DeviceRecord& node) {return static_cast<std::uint64_t>(node[2])|(static_cast<std::uint64_t>(node[3])<<32);}
    void length(const DeviceRecord& node,std::size_t factor=1) {
        require(static_cast<std::uint64_t>(node[1])<=static_cast<std::uint64_t>(size-cursor)/factor,"Impossible device state container count");
        require(node[2]==0&&node[3]==0,"Container has unexpected scalar bits");
    }
    template<class T> void get(T& value) {
        using U=Bare<T>;
        if constexpr (std::is_same_v<U,V>) value=json();
        else if constexpr (std::is_same_v<U,bool>) {const auto& n=next(DeviceTag::Boolean);require(n[1]<=1&&bits(n)==0,"Invalid device boolean");value=n[1];finish(n);}
        else if constexpr (std::is_integral_v<U>) {
            const auto& n=next(std::is_signed_v<U>?DeviceTag::SignedInteger:DeviceTag::UnsignedInteger);
            require(n[1]==0,"Integer has unexpected metadata");
            if constexpr (std::is_signed_v<U>) {
                const auto v=std::bit_cast<std::int64_t>(bits(n));
                require(v>=std::numeric_limits<U>::min()&&v<=std::numeric_limits<U>::max(),"Device signed integer outside native range");value=static_cast<U>(v);
            } else {const auto v=bits(n);require(v<=std::numeric_limits<U>::max(),"Device unsigned integer outside native range");value=static_cast<U>(v);}
            finish(n);
        } else if constexpr (std::is_enum_v<U>) {
            std::underlying_type_t<U> n;get(n);require(n>=0&&n<=4,"Unknown device phase");value=static_cast<U>(n);
        } else if constexpr (std::is_same_v<U,std::string>) {
            const auto& n=next(DeviceTag::String);require(bits(n)==0,"String has unexpected bits");
            auto id=static_cast<std::uint64_t>(n[1]);require(id<prefix.size()+suffix.size(),"Device string ID outside table");
            value=id<prefix.size()?prefix[id]:suffix[id-prefix.size()];finish(n);
        } else if constexpr (is_optional<U>::value) {
            const auto& n=next(DeviceTag::Optional);require(n[1]<=1&&bits(n)==0,"Invalid device optional");
            if(n[1]){typename U::value_type child;get(child);value=std::move(child);}else value.reset();finish(n);
        } else if constexpr (is_vector<U>::value) {
            const auto& n=next(DeviceTag::Sequence);length(n);value.clear();value.reserve(n[1]);
            for(std::int64_t i=0;i<n[1];++i){typename U::value_type child;get(child);value.push_back(std::move(child));}finish(n);
        } else if constexpr (is_set<U>::value) {
            const auto& n=next(DeviceTag::Set);length(n);value.clear();
            for(std::int64_t i=0;i<n[1];++i){typename U::value_type child;get(child);require(value.empty()||*value.rbegin()<child,"Unsorted/duplicate device set value");value.insert(std::move(child));}finish(n);
        } else if constexpr (is_map<U>::value) {
            const auto& n=next(DeviceTag::Map);length(n,2);value.clear();
            for(std::int64_t i=0;i<n[1];++i){typename U::key_type key;typename U::mapped_type child;get(key);get(child);
                require(value.empty()||value.rbegin()->first<key,"Unsorted/duplicate device map key");value.emplace(std::move(key),std::move(child));}finish(n);
        } else if constexpr (is_pair<U>::value) {
            const auto& n=next(DeviceTag::Pair);require(n[1]==2&&bits(n)==0,"Invalid device pair");get(value.first);get(value.second);finish(n);
        } else if constexpr (record<U>) tuple(members(value));
        else static_assert(sizeof(U)==0,"Device state member has no lossless decoding");
    }
    template<class... T> void tuple(const std::tuple<T...>& values) {
        const auto& n=next(DeviceTag::Record);require(n[1]==sizeof...(T)&&bits(n)==0,"Unknown/missing device record fields");
        std::apply([&](auto&...item){(get(item),...);},values);finish(n);
    }
    V json() {
        require(cursor<size,"Truncated device JSON");const auto tag=static_cast<DeviceTag>(nodes[cursor][0]);
        if(tag==DeviceTag::Null){const auto& n=next(tag);require(n[1]==0&&bits(n)==0,"Invalid device null");finish(n);return V(nullptr);}
        if(tag==DeviceTag::Boolean){bool v;get(v);return V(v);}
        if(tag==DeviceTag::String){std::string v;get(v);return V(std::move(v));}
        if(tag==DeviceTag::NumberBits){const auto& n=next(tag);require(n[1]==0,"Number has unexpected metadata");const auto v=std::bit_cast<double>(bits(n));require(std::isfinite(v),"Nonfinite device JSON number");finish(n);return V(v);}
        if(tag==DeviceTag::JsonArray){const auto& n=next(tag);length(n);V::Array a;for(std::int64_t i=0;i<n[1];++i)a.push_back(json());finish(n);return V(std::move(a));}
        require(tag==DeviceTag::JsonObject,"Unknown device JSON type");const auto& n=next(tag);length(n,2);V::Object o;
        for(std::int64_t i=0;i<n[1];++i){std::string key;get(key);require(o.empty()||o.rbegin()->first<key,"Unsorted/duplicate device JSON key");o.emplace(std::move(key),json());}finish(n);return V(std::move(o));
    }
};
std::vector<std::int64_t> children(const DeviceRecord* nodes,std::size_t size,std::int64_t root) {
    require(root>=0&&static_cast<std::uint64_t>(root)<size,"Invalid device section root");
    std::vector<std::int64_t> out;auto cursor=root+1;
    for(std::int64_t i=0;i<nodes[root][1];++i){require(cursor>root&&static_cast<std::uint64_t>(cursor)<size,"Truncated device sections");out.push_back(cursor);auto next=nodes[cursor][4];require(next>cursor&&next<=count(size),"Invalid device section subtree");cursor=next;}
    require(cursor==nodes[root][4],"Unknown/missing device sections");return out;
}
std::vector<std::int64_t> sections(const DeviceRecord* nodes,std::size_t size) {
    auto roots=children(nodes,size,0);require(roots.size()==2,"Invalid device engine record");
    auto state=children(nodes,size,roots[0]),random=children(nodes,size,roots[1]);
    require(state.size()==19&&random.size()==6,"Unknown device state/RNG fields");
    std::vector<std::int64_t> out=roots;out.insert(out.end(),state.begin(),state.end());out.insert(out.end(),random.begin(),random.end());return out;
}
void validateOffsets(const std::vector<std::int64_t>& offsets,std::size_t size,const char* message) {
    require(!offsets.empty()&&offsets.front()==0&&offsets.back()==count(size),message);
    for(std::size_t i=1;i<offsets.size();++i)require(offsets[i]>=offsets[i-1],message);
}
}

namespace {
void fingerprintWord(std::string& bytes,std::uint64_t value) {
    for(int byte=0;byte<8;++byte)bytes.push_back(static_cast<char>((value>>(byte*8))&255));
}
void fingerprintText(std::string& bytes,const std::string& text) {
    fingerprintWord(bytes,text.size());bytes.append(text);
}
std::string wireFingerprint(const DeviceStateContext& context) {
    std::string bytes;
    fingerprintText(bytes,deviceStateSchema);fingerprintText(bytes,context.definitionFingerprint);fingerprintText(bytes,context.rulesId);
    fingerprintWord(bytes,context.records.size());
    for(const auto& row:context.records)for(const auto value:row)fingerprintWord(bytes,std::bit_cast<std::uint64_t>(value));
    fingerprintWord(bytes,context.stringBytes.size());
    bytes.append(reinterpret_cast<const char*>(context.stringBytes.data()),context.stringBytes.size());
    fingerprintWord(bytes,context.stringOffsets.size());
    for(const auto value:context.stringOffsets)fingerprintWord(bytes,std::bit_cast<std::uint64_t>(value));
    return contentDigest(bytes);
}
}

DeviceStateContext::DeviceStateContext(const Engine& engine):definition(engine.state().definition),
    rules(DeviceStateAccess::rules(engine)),definitionFingerprint(definition->fingerprint),rulesId(rules->id()) {
    require(!definitionFingerprint.empty()&&!rulesId.empty(),"Device state requires an identified frozen definition/rules");
    const std::vector<std::string> empty;Pool pool(empty,strings);Writer writer{records,pool};
    const auto&[scenario,fingerprint,geography,indexed,rulesData,catalog,factions,order,players,year,month,rounds]=*definition;
    (void)indexed;
    const V catalogSource=catalog?catalog->sourceData():V(nullptr);
    writer.tuple(std::tie(scenario,fingerprint,geography,rulesData,catalogSource,factions,order,players,year,month,rounds));
    // Fixed spellings needed by device rule handlers even when the corresponding
    // dynamic flag/component map is empty. Append only after definition data.
    for(const auto* text:{"actual","search","training","territorial","china_control_bonus","major","city_ipp_lost","city_damage"})pool.intern(text);
    stringIds=pool.index;
    flattenStrings(strings,stringBytes,stringOffsets);
    wireContextFingerprint=wireFingerprint(*this);
}
std::vector<std::int64_t> DeviceStateContext::prefixLookupIds(const std::vector<std::string>& names) const {
    std::vector<std::int64_t> result;result.reserve(names.size());
    for(const auto& name:names){const auto found=stringIds.find(name);if(found==stringIds.end())throw std::out_of_range("Unknown static device string: "+name);result.push_back(found->second);}
    return result;
}
DeviceStateBatch::DeviceStateBatch(std::shared_ptr<const DeviceStateContext> c):context(std::move(c)),laneOffsets{0},stringOffsets{0} {
    require(context!=nullptr,"Absent device state context");
}
void DeviceStateBatch::append(const Engine& engine) {
    require(engine.rulesId()==context->rulesId&&engine.state().definition->fingerprint==context->definitionFingerprint,
            "Device state definition/rules mismatch");
    const auto start=records.size();Pool pool(context->strings,strings);Writer writer{records,pool};
    writer.tuple(std::tie(engine.state(),DeviceStateAccess::random(engine)));
    for(std::size_t i=start;i<records.size();++i)records[i][4]-=count(start);
    const auto length=records.size()-start;auto indexes=::game::campaign::sections(records.data()+start,length);
    sections.insert(sections.end(),indexes.begin(),indexes.end());laneOffsets.push_back(count(records.size()));
    maxLaneRecords=std::max(maxLaneRecords,length);flattenStrings(strings,stringBytes,stringOffsets);
}
const std::vector<std::string>& DeviceStateBatch::sectionNames() {
    static const std::vector<std::string> names{"state","random","state.nations","state.territories","state.units",
        "state.facilities","state.rails","state.construction","state.repairs","state.clock","state.politics",
        "state.turn_start","state.completed_turns","state.decisions","state.battles","state.battle_order",
        "state.chance","state.flags","state.history","state.action_interface","state.terminal",
        "random.actual","random.search","random.training","random.active","random.test_tape","random.tape_position"};
    return names;
}
Engine DeviceStateBatch::restore(std::size_t lane) const {
    require(lane<rows(),"Device state lane outside batch");
    validateOffsets(laneOffsets,records.size(),"Invalid device lane offsets");
    const auto start=static_cast<std::size_t>(laneOffsets[lane]),length=static_cast<std::size_t>(laneOffsets[lane+1]-laneOffsets[lane]);
    Reader reader{records.data()+start,length,0,context->strings,strings};
    State state;state.definition=context->definition;RandomStreams random;
    reader.tuple(std::tie(state,random));require(reader.cursor==length,"Trailing unknown device state records");
    return DeviceStateAccess::restore(std::move(state),context->rules,std::move(random));
}
void DeviceStateBatch::validate() const {
    validateOffsets(laneOffsets,records.size(),"Invalid device lane offsets");
    for(std::size_t lane=0;lane<rows();++lane)(void)restore(lane);
}
DeviceStateBatch DeviceStateBatch::fromPacked(std::shared_ptr<const DeviceStateContext> context,
    std::vector<DeviceRecord> records,std::vector<std::int64_t> offsets,std::vector<std::uint8_t> bytes,
    std::vector<std::int64_t> stringsOffsets,const std::string& expectedWireContextFingerprint) {
    require(context&&context->wireContextFingerprint==expectedWireContextFingerprint,"Device wire context mismatch; raw buffers cannot be retagged");
    DeviceStateBatch result(std::move(context));result.records=std::move(records);result.laneOffsets=std::move(offsets);
    validateOffsets(result.laneOffsets,result.records.size(),"Invalid device lane offsets");
    validateOffsets(stringsOffsets,bytes.size(),"Invalid device string offsets");
    std::set<std::string> identities(result.context->strings.begin(),result.context->strings.end());
    for(std::size_t i=1;i<stringsOffsets.size();++i) {
        const auto start=static_cast<std::size_t>(stringsOffsets[i-1]),length=static_cast<std::size_t>(stringsOffsets[i]-stringsOffsets[i-1]);
        std::string text=length?std::string(reinterpret_cast<const char*>(bytes.data()+start),length):std::string{};
        require(identities.insert(text).second,"Noncanonical duplicate device string identity");
        result.strings.push_back(std::move(text));
    }
    result.stringBytes=std::move(bytes);result.stringOffsets=std::move(stringsOffsets);
    for(std::size_t lane=0;lane<result.rows();++lane) {
        const auto start=result.laneOffsets[lane],length=result.laneOffsets[lane+1]-start;
        auto indexes=::game::campaign::sections(result.records.data()+start,length);
        result.sections.insert(result.sections.end(),indexes.begin(),indexes.end());
        result.maxLaneRecords=std::max(result.maxLaneRecords,static_cast<std::size_t>(length));
    }
    result.validate();return result;
}
} // namespace game::campaign
