#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <initializer_list>
#include <iterator>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

// Things created during play, held by slot.
//
// Zones, nations and the other kinds in names.hpp are fixed by the definition,
// so each name's number is its place in a sorted table. Units and facilities
// are not: a game creates and destroys them, and a new unit's name may sort
// anywhere among the others. A position therefore keeps each kind of such
// thing in a SlotMap, which gives every thing a *slot* when it enters the
// position: a small number, fixed while the thing exists, that reaches it
// without comparing names. A SlotMap still lists its things in name order,
// as the std::map keyed by name it replaced did, so every list of moves comes
// out in the same order. docs/engine/names.md says which references hold
// slots.
//
// A slot says nothing about name order: slots follow the order things were
// created in, which differs between two copies of a game that reached the
// same position by different moves, and between a position and the same
// position read back from its saved form. So a slot has no order and no hash,
// and no set or map can be keyed by slots; whatever must be listed in order is
// listed in name order through its SlotMap.

namespace game::campaign {

template <class KindTag>
class Slot {
  public:
    using Kind = KindTag;

    constexpr Slot() = default;
    // The slot at this place in its SlotMap. Only a SlotMap makes one.
    static constexpr Slot fromIndex(std::size_t index) {
        if (index >= none) throw std::out_of_range("A slot beyond what a SlotMap holds");
        Slot slot;
        slot.value_ = static_cast<std::uint32_t>(index);
        return slot;
    }
    constexpr std::size_t index() const { return value_; }
    // A default slot names nothing.
    constexpr bool valid() const { return value_ != none; }

    friend constexpr bool operator==(Slot, Slot) = default;

  private:
    static constexpr std::uint32_t none = std::numeric_limits<std::uint32_t>::max();
    std::uint32_t value_ {none};
};

// Things keyed by name, each with a slot. It offers the parts of std::map's
// interface the engine uses, by name, and lists its entries, pairs of a name
// and a thing, in name order. at(slot) reaches a thing by its slot without
// comparing names.
//
// - Entries live in a deque that only grows, so a reference to a thing stays
//   valid until that thing is erased, whatever else enters or leaves.
// - Erasing a thing leaves its slot empty; no other thing takes it, so a slot
//   kept after its thing was erased names nothing (contains(slot) is false).
// - A thing with a member `slot` of this map's slot type gets its slot written
//   there when it enters. Assigning a whole thing over an entry would replace
//   it, so the map offers no operator[]: insert_or_assign keeps the slot.
// - A thing is found by name through a hash table of slots, rebuilt when a
//   thing enters or leaves, so a lookup compares one name or two, where a
//   search in name order compared seven or eight. Name order serves only to
//   list the things and to place a new one.
// - Iterators are positions in name order: entering or erasing a thing moves
//   the positions after it, so neither may happen while iterating, except
//   erase(iterator), which returns the position of the next thing. Built with
//   GWRL_CHECK_SLOT_MAPS defined, an iterator used after its map gained or
//   lost a thing throws, which finds such loops in tests and random games.
template <class Kind, class Value>
class SlotMap {
  public:
    using key_type = std::string;
    using mapped_type = Value;
    using value_type = std::pair<const std::string, Value>;
    using size_type = std::size_t;
    using SlotType = Slot<Kind>;

    template <bool Const>
    class Iterator {
        using Map = std::conditional_t<Const, const SlotMap, SlotMap>;

      public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = SlotMap::value_type;
        using difference_type = std::ptrdiff_t;
        using pointer = std::conditional_t<Const, const value_type*, value_type*>;
        using reference = std::conditional_t<Const, const value_type&, value_type&>;

        Iterator() = default;
#ifdef GWRL_CHECK_SLOT_MAPS
        Iterator(Map* map, std::size_t at) : map_(map), at_(at), version_(map->version_) {}
#else
        Iterator(Map* map, std::size_t at) : map_(map), at_(at) {}
#endif
        // An iterator converts to a const_iterator, as std::map's does.
#ifdef GWRL_CHECK_SLOT_MAPS
        operator Iterator<true>() const { return Iterator<true>(map_, at_, version_); }
#else
        operator Iterator<true>() const { return Iterator<true>(map_, at_); }
#endif

        reference operator*() const { check(); return *map_->entries_[map_->byName_[at_]]; }
        pointer operator->() const { return &**this; }
        Iterator& operator++() { check(); ++at_; return *this; }
        Iterator operator++(int) { auto old = *this; ++*this; return old; }
        friend bool operator==(const Iterator& a, const Iterator& b) { return a.at_ == b.at_; }
        // The slot of the thing at this position.
        SlotType slot() const { check(); return SlotType::fromIndex(map_->byName_[at_]); }

      private:
        friend class SlotMap;
#ifdef GWRL_CHECK_SLOT_MAPS
        Iterator(Map* map, std::size_t at, std::uint64_t version) : map_(map), at_(at), version_(version) {}
        void check() const {
            if (map_ && version_ != map_->version_) throw std::logic_error("A SlotMap gained or lost a thing while iterating");
        }
        Map* map_ {nullptr};
        std::size_t at_ {0};
        std::uint64_t version_ {0};
#else
        void check() const {}
        Map* map_ {nullptr};
        std::size_t at_ {0};
#endif
    };
    using iterator = Iterator<false>;
    using const_iterator = Iterator<true>;

    SlotMap() = default;
    // Like std::map's, a repeated name keeps its first thing.
    SlotMap(std::initializer_list<value_type> entries) {
        for (const auto& [name, value] : entries) emplace(name, value);
    }
    SlotMap(const SlotMap&) = default;
    SlotMap(SlotMap&&) noexcept = default;
    // Entries hold a const name, so copying over a map rebuilds it.
    SlotMap& operator=(const SlotMap& other) {
        if (this != &other) {
            SlotMap copy(other);
            swap(copy);
        }
        return *this;
    }
    SlotMap& operator=(SlotMap&& other) noexcept {
        swap(other);
        return *this;
    }
    void swap(SlotMap& other) noexcept {
        entries_.swap(other.entries_);
        byName_.swap(other.byName_);
        positionOf_.swap(other.positionOf_);
        hash_.swap(other.hash_);
    }

    iterator begin() { return iterator(this, 0); }
    iterator end() { return iterator(this, byName_.size()); }
    const_iterator begin() const { return const_iterator(this, 0); }
    const_iterator end() const { return const_iterator(this, byName_.size()); }

    size_type size() const { return byName_.size(); }
    bool empty() const { return byName_.empty(); }
    void clear() {
        entries_.clear();
        byName_.clear();
        positionOf_.clear();
        hash_.clear();
        changed();
    }

    // By name, as std::map.
    iterator find(std::string_view name) { return iterator(this, position(name)); }
    const_iterator find(std::string_view name) const { return const_iterator(this, position(name)); }
    bool contains(std::string_view name) const { return lookup(name) != none; }
    size_type count(std::string_view name) const { return contains(name) ? 1 : 0; }
    Value& at(std::string_view name) { return named(name).second; }
    const Value& at(std::string_view name) const { return named(name).second; }
    // The first entry whose name sorts after this one.
    iterator upper_bound(std::string_view name) { return iterator(this, upperBound(name)); }
    const_iterator upper_bound(std::string_view name) const { return const_iterator(this, upperBound(name)); }

    template <class... Args>
    std::pair<iterator, bool> emplace(const std::string& name, Args&&... args) {
        if (const auto found = lookup(name); found != none) return {iterator(this, positionOf_[found]), false};
        const auto at = lowerBound(name);
        const auto slot = static_cast<std::uint32_t>(SlotType::fromIndex(entries_.size()).index());
        entries_.emplace_back(std::in_place, std::piecewise_construct, std::forward_as_tuple(name),
                              std::forward_as_tuple(std::forward<Args>(args)...));
        stamp(entries_.back()->second, SlotType::fromIndex(slot));
        byName_.insert(byName_.begin() + static_cast<std::ptrdiff_t>(at), slot);
        positionOf_.push_back(none);
        renumberFrom(at);
        enterInHash(slot);
        changed();
        return {iterator(this, at), true};
    }
    // Enters the thing, or replaces the thing of this name, which keeps its slot.
    std::pair<iterator, bool> insert_or_assign(const std::string& name, Value value) {
        if (const auto found = lookup(name); found != none) {
            auto& entry = entries_[found]->second;
            entry = std::move(value);
            stamp(entry, SlotType::fromIndex(found));
            return {iterator(this, positionOf_[found]), false};
        }
        return emplace(name, std::move(value));
    }

    size_type erase(std::string_view name) {
        const auto at = position(name);
        if (at == byName_.size()) return 0;
        erase(iterator(this, at));
        return 1;
    }
    iterator erase(const_iterator at) {
        at.check();
        const auto slot = byName_[at.at_];
        entries_[slot].reset();
        positionOf_[slot] = none;
        byName_.erase(byName_.begin() + static_cast<std::ptrdiff_t>(at.at_));
        renumberFrom(at.at_);
        rehash();
        changed();
        return iterator(this, at.at_);
    }

    // By slot.
    bool contains(SlotType slot) const { return slot.valid() && slot.index() < entries_.size() && entries_[slot.index()]; }
    Value& at(SlotType slot) { return checked(slot).second; }
    const Value& at(SlotType slot) const { return checked(slot).second; }
    const std::string& name(SlotType slot) const { return checked(slot).first; }
    // The slot of the thing of this name, or nothing.
    std::optional<SlotType> slotOf(std::string_view name) const {
        const auto found = lookup(name);
        if (found == none) return std::nullopt;
        return SlotType::fromIndex(found);
    }

  private:
    static constexpr std::uint32_t none = std::numeric_limits<std::uint32_t>::max();

    // The slot of the thing of this name, or none.
    std::uint32_t lookup(std::string_view name) const {
        if (hash_.empty()) return none;
        const auto mask = hash_.size() - 1;
        for (auto at = std::hash<std::string_view> {}(name) & mask;; at = (at + 1) & mask) {
            const auto slot = hash_[at];
            if (slot == none || entries_[slot]->first == name) return slot;
        }
    }
    // Enters a slot in the hash table, growing it to keep it at most half full.
    void enterInHash(std::uint32_t slot) {
        if (2 * byName_.size() > hash_.size()) {
            rehash();
            return;
        }
        const auto mask = hash_.size() - 1;
        auto at = std::hash<std::string_view> {}(entries_[slot]->first) & mask;
        while (hash_[at] != none) at = (at + 1) & mask;
        hash_[at] = slot;
    }
    void rehash() {
        std::size_t size = 16;
        while (size < 2 * byName_.size()) size *= 2;
        hash_.assign(size, none);
        const auto mask = size - 1;
        for (const auto slot : byName_) {
            auto at = std::hash<std::string_view> {}(entries_[slot]->first) & mask;
            while (hash_[at] != none) at = (at + 1) & mask;
            hash_[at] = slot;
        }
    }
    // Things at and after this position moved in name order.
    void renumberFrom(std::size_t at) {
        for (; at < byName_.size(); ++at) positionOf_[byName_[at]] = static_cast<std::uint32_t>(at);
    }
    std::size_t lowerBound(std::string_view name) const {
        return static_cast<std::size_t>(std::lower_bound(byName_.begin(), byName_.end(), name,
            [&](std::uint32_t at, std::string_view key) { return entries_[at]->first < key; }) - byName_.begin());
    }
    std::size_t upperBound(std::string_view name) const {
        return static_cast<std::size_t>(std::upper_bound(byName_.begin(), byName_.end(), name,
            [&](std::string_view key, std::uint32_t at) { return key < entries_[at]->first; }) - byName_.begin());
    }
    // The position of this name in name order, or size() for a name the map lacks.
    std::size_t position(std::string_view name) const {
        const auto found = lookup(name);
        return found == none ? byName_.size() : positionOf_[found];
    }
    value_type& named(std::string_view name) {
        const auto found = lookup(name);
        if (found == none) throw std::out_of_range("SlotMap::at: no entry of this name");
        return *entries_[found];
    }
    const value_type& named(std::string_view name) const {
        const auto found = lookup(name);
        if (found == none) throw std::out_of_range("SlotMap::at: no entry of this name");
        return *entries_[found];
    }
    const value_type& checked(SlotType slot) const {
        if (!contains(slot)) throw std::out_of_range("SlotMap::at: no entry in this slot");
        return *entries_[slot.index()];
    }
    value_type& checked(SlotType slot) {
        if (!contains(slot)) throw std::out_of_range("SlotMap::at: no entry in this slot");
        return *entries_[slot.index()];
    }
#ifdef GWRL_CHECK_SLOT_MAPS
    void changed() { ++version_; }
    std::uint64_t version_ {0};
#else
    void changed() {}
#endif
    static void stamp(Value& value, SlotType slot) {
        if constexpr (requires { value.slot = slot; }) value.slot = slot;
    }

    std::deque<std::optional<value_type>> entries_;  // By slot; an erased thing leaves its slot empty.
    std::vector<std::uint32_t> byName_;              // The slots of the things there are, in name order.
    std::vector<std::uint32_t> positionOf_;          // By slot: its place in byName_, or none once erased.
    std::vector<std::uint32_t> hash_;                // Slots by the hash of their names; none marks a free place.
};

}  // namespace game::campaign
