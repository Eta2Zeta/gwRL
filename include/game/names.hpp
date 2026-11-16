#pragma once

#include <array>
#include <bit>
#include <compare>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <iterator>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>

// Names held as numbers.
//
// The scenario names its zones and other things with strings, such as
// "land_china_hopeh". Inside the engine such a name is held as a small number
// of a type of its own for each kind of name, such as ZoneId for a zone, so
// that comparing, copying and looking up names costs no more than for an
// integer. The numbers come from the definition's name tables (Names below):
// a kind's names sorted bytewise, each name's number being its place in that
// list, counted from 0. Numbers therefore compare as their names do, and a
// container keyed by numbers lists its entries in the order the same container
// keyed by the names would.
//
// The names remain what the engine reads and writes: saved positions, planning
// keys, observations, actions and the Python interface all carry names, and
// the engine converts them where it reads them. A number means nothing without
// its definition's table; tools/print_name_tables.py prints the tables of a
// scenario, and docs/engine/names.md says where each kind's names come from.

namespace game::campaign {

// The kinds of name held as numbers. `Rep` stores a number, `capacity` bounds
// how many names a kind's table may hold (a NumberSet holds that many bits)
// and `noun` names the kind in error messages.
struct ZoneKind {
    using Rep = std::uint16_t;
    static constexpr std::size_t capacity = 1024;  // The full world map has 539 zones.
    static constexpr std::string_view noun = "zone";
};

// A name of one kind, held as its number in the definition's table of that
// kind. There are no conversions to or from strings or integers, not even
// explicit ones: a table gives a name's number and a number's name, and only
// tables and the containers below make numbers from places (fromIndex). So a
// string or a character can never become a number by accident, as a list of
// two string literals would through std::vector's iterator-pair constructor.
// A default-constructed Number is no name at all; the tables give it no name
// and containers refuse it.
template <class KindTag>
class Number {
  public:
    using Kind = KindTag;
    using Rep = typename Kind::Rep;
    static_assert(Kind::capacity < std::numeric_limits<Rep>::max(), "Rep must leave room for no name");

    constexpr Number() = default;
    // The number at this place in its table.
    static constexpr Number fromIndex(std::size_t index) {
        Number number;
        number.value_ = checked(index);
        return number;
    }

    // The name's place in its table, from 0. Containers index by it.
    constexpr std::size_t index() const { return value_; }
    constexpr bool valid() const { return value_ != none; }

    friend constexpr bool operator==(Number, Number) = default;
    friend constexpr auto operator<=>(Number, Number) = default;

  private:
    static constexpr Rep none = std::numeric_limits<Rep>::max();
    static constexpr Rep checked(std::size_t index) {
        if (index >= Kind::capacity) throw std::out_of_range("Name number beyond its kind's capacity");
        return static_cast<Rep>(index);
    }
    Rep value_ {none};
};

using ZoneId = Number<ZoneKind>;

// Every number below a count, ascending: the numbers a table holds.
template <class Kind>
class NumberRange {
  public:
    class iterator {
      public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = Number<Kind>;
        using difference_type = std::ptrdiff_t;
        using pointer = const Number<Kind>*;
        using reference = Number<Kind>;
        iterator() = default;
        explicit iterator(std::size_t at) : at_(at) {}
        Number<Kind> operator*() const { return Number<Kind>::fromIndex(at_); }
        iterator& operator++() { ++at_; return *this; }
        iterator operator++(int) { auto old = *this; ++at_; return old; }
        friend bool operator==(const iterator&, const iterator&) = default;

      private:
        std::size_t at_ {0};
    };
    explicit NumberRange(std::size_t count) : count_(count) {}
    iterator begin() const { return iterator(0); }
    iterator end() const { return iterator(count_); }

  private:
    std::size_t count_;
};

// The names of one kind, sorted bytewise; a name's number is its place in
// that order. A table never changes after it is built.
template <class Kind>
class NameTable {
  public:
    using Id = Number<Kind>;

    NameTable() = default;
    // Takes the names in any order. Throws on an empty or repeated name, or
    // on more names than the kind's capacity.
    explicit NameTable(std::vector<std::string> names) : names_(std::move(names)) {
        std::sort(names_.begin(), names_.end());
        if (names_.size() > Kind::capacity)
            throw std::runtime_error("Too many " + std::string(Kind::noun) + " names");
        for (std::size_t at = 0; at < names_.size(); ++at) {
            if (names_[at].empty()) throw std::runtime_error("Empty " + std::string(Kind::noun) + " name");
            if (at > 0 && names_[at] == names_[at - 1])
                throw std::runtime_error("Repeated " + std::string(Kind::noun) + " name: " + names_[at]);
        }
    }

    std::size_t size() const { return names_.size(); }
    bool empty() const { return names_.empty(); }
    // The names in number order: names()[n.index()] is n's name.
    const std::vector<std::string>& names() const { return names_; }
    // Every number in the table, ascending, which is name order.
    NumberRange<Kind> numbers() const { return NumberRange<Kind>(names_.size()); }

    const std::string& name(Id id) const {
        if (!id.valid() || id.index() >= names_.size())
            throw std::out_of_range("No " + std::string(Kind::noun) + " has this number");
        return names_[id.index()];
    }
    std::optional<Id> find(std::string_view name) const {
        const auto at = std::lower_bound(names_.begin(), names_.end(), name,
                                         [](const std::string& entry, std::string_view key) { return entry < key; });
        if (at == names_.end() || *at != name) return std::nullopt;
        return Id::fromIndex(static_cast<std::size_t>(at - names_.begin()));
    }
    bool contains(std::string_view name) const { return find(name).has_value(); }
    // Throws "Unknown zone: <name>" (with the kind's noun) for a name not in the table.
    Id number(std::string_view name) const {
        if (const auto found = find(name)) return *found;
        throw std::runtime_error("Unknown " + std::string(Kind::noun) + ": " + std::string(name));
    }

  private:
    std::vector<std::string> names_;
};

// A map keyed by numbers of one kind, kept in a vector with one slot per
// number. It offers the parts of std::map's interface the engine uses, lists
// its entries in number order (which is name order) and copies without
// allocating a node per entry. Iterators stay valid until the map gains a
// slot it lacked or is copied over.
template <class Key, class Value>
class NumberMap {
  public:
    using key_type = Key;
    using mapped_type = Value;
    using value_type = std::pair<const Key, Value>;
    using size_type = std::size_t;

    template <bool Const>
    class Iterator {
        using Slots = std::conditional_t<Const, const std::vector<std::optional<value_type>>,
                                         std::vector<std::optional<value_type>>>;

      public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = NumberMap::value_type;
        using difference_type = std::ptrdiff_t;
        using pointer = std::conditional_t<Const, const value_type*, value_type*>;
        using reference = std::conditional_t<Const, const value_type&, value_type&>;

        Iterator() = default;
        Iterator(Slots* slots, std::size_t at) : slots_(slots), at_(at) { skip(); }
        // An iterator converts to a const_iterator, as std::map's does.
        operator Iterator<true>() const { return Iterator<true>(slots_, at_); }

        reference operator*() const { return *(*slots_)[at_]; }
        pointer operator->() const { return &*(*slots_)[at_]; }
        Iterator& operator++() { ++at_; skip(); return *this; }
        Iterator operator++(int) { auto old = *this; ++*this; return old; }
        friend bool operator==(const Iterator& a, const Iterator& b) { return a.at_ == b.at_; }

      private:
        friend class NumberMap;
        void skip() { while (slots_ && at_ < slots_->size() && !(*slots_)[at_]) ++at_; }
        Slots* slots_ {nullptr};
        std::size_t at_ {0};
    };
    using iterator = Iterator<false>;
    using const_iterator = Iterator<true>;

    NumberMap() = default;
    NumberMap(const NumberMap&) = default;
    NumberMap(NumberMap&&) noexcept = default;
    // Entries hold a const key, so copying over a map rebuilds its slots.
    NumberMap& operator=(const NumberMap& other) {
        if (this != &other) {
            NumberMap copy(other);
            swap(copy);
        }
        return *this;
    }
    NumberMap& operator=(NumberMap&&) noexcept = default;
    void swap(NumberMap& other) noexcept {
        slots_.swap(other.slots_);
        std::swap(size_, other.size_);
    }

    iterator begin() { return iterator(&slots_, 0); }
    iterator end() { return iterator(&slots_, slots_.size()); }
    const_iterator begin() const { return const_iterator(&slots_, 0); }
    const_iterator end() const { return const_iterator(&slots_, slots_.size()); }
    const_iterator cbegin() const { return begin(); }
    const_iterator cend() const { return end(); }

    size_type size() const { return size_; }
    bool empty() const { return size_ == 0; }
    void clear() {
        slots_.clear();
        size_ = 0;
    }

    bool contains(Key key) const { return key.valid() && key.index() < slots_.size() && slots_[key.index()]; }
    size_type count(Key key) const { return contains(key) ? 1 : 0; }
    iterator find(Key key) { return contains(key) ? iterator(&slots_, key.index()) : end(); }
    const_iterator find(Key key) const { return contains(key) ? const_iterator(&slots_, key.index()) : end(); }

    Value& at(Key key) {
        if (!contains(key)) throw std::out_of_range("NumberMap::at: no entry");
        return slots_[key.index()]->second;
    }
    const Value& at(Key key) const {
        if (!contains(key)) throw std::out_of_range("NumberMap::at: no entry");
        return slots_[key.index()]->second;
    }
    Value& operator[](Key key) { return try_emplace(key).first->second; }

    template <class... Args>
    std::pair<iterator, bool> try_emplace(Key key, Args&&... args) {
        if (!key.valid()) throw std::out_of_range("NumberMap: a key with no name");
        if (key.index() >= slots_.size()) slots_.resize(key.index() + 1);
        auto& slot = slots_[key.index()];
        if (slot) return {iterator(&slots_, key.index()), false};
        slot.emplace(std::piecewise_construct, std::forward_as_tuple(key),
                     std::forward_as_tuple(std::forward<Args>(args)...));
        ++size_;
        return {iterator(&slots_, key.index()), true};
    }
    template <class... Args>
    std::pair<iterator, bool> emplace(Key key, Args&&... args) {
        return try_emplace(key, std::forward<Args>(args)...);
    }
    std::pair<iterator, bool> insert(const value_type& entry) { return try_emplace(entry.first, entry.second); }
    template <class V>
    std::pair<iterator, bool> insert_or_assign(Key key, V&& value) {
        auto [at, inserted] = try_emplace(key, std::forward<V>(value));
        if (!inserted) at->second = std::forward<V>(value);
        return {at, inserted};
    }

    size_type erase(Key key) {
        if (!contains(key)) return 0;
        slots_[key.index()].reset();
        --size_;
        return 1;
    }
    iterator erase(const_iterator at) {
        const auto index = at.at_;
        slots_[index].reset();
        --size_;
        return iterator(&slots_, index + 1);
    }

    friend bool operator==(const NumberMap& a, const NumberMap& b) {
        if (a.size_ != b.size_) return false;
        for (const auto& [key, value] : a) {
            const auto other = b.find(key);
            if (other == b.end() || !(other->second == value)) return false;
        }
        return true;
    }

  private:
    std::vector<std::optional<value_type>> slots_;
    size_type size_ {0};
};

// A set of numbers of one kind, held as one bit per number with no
// allocation. It offers the parts of std::set's interface the engine uses and
// lists its members in number order (which is name order).
template <class Key>
class NumberSet {
    static constexpr std::size_t bitsPerWord = 64;
    static constexpr std::size_t wordCount = (Key::Kind::capacity + bitsPerWord - 1) / bitsPerWord;

  public:
    using key_type = Key;
    using value_type = Key;
    using size_type = std::size_t;

    class const_iterator {
      public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = Key;
        using difference_type = std::ptrdiff_t;
        using pointer = const Key*;
        using reference = Key;

        const_iterator() = default;
        const_iterator(const NumberSet* set, std::size_t at) : set_(set), at_(at) { skip(); }
        Key operator*() const { return Key::fromIndex(at_); }
        const_iterator& operator++() { ++at_; skip(); return *this; }
        const_iterator operator++(int) { auto old = *this; ++*this; return old; }
        friend bool operator==(const const_iterator& a, const const_iterator& b) { return a.at_ == b.at_; }

      private:
        void skip() {
            while (at_ < Key::Kind::capacity) {
                const auto word = set_->bits_[at_ / bitsPerWord] >> (at_ % bitsPerWord);
                if (word) {
                    at_ += static_cast<std::size_t>(std::countr_zero(word));
                    return;
                }
                at_ = (at_ / bitsPerWord + 1) * bitsPerWord;
            }
            at_ = Key::Kind::capacity;
        }
        const NumberSet* set_ {nullptr};
        std::size_t at_ {Key::Kind::capacity};
    };
    using iterator = const_iterator;

    NumberSet() = default;
    NumberSet(std::initializer_list<Key> keys) {
        for (const auto key : keys) insert(key);
    }
    template <class It>
    NumberSet(It first, It last) {
        for (; first != last; ++first) insert(*first);
    }

    const_iterator begin() const { return const_iterator(this, 0); }
    const_iterator end() const { return const_iterator(this, Key::Kind::capacity); }

    bool contains(Key key) const {
        return key.valid() && (bits_[key.index() / bitsPerWord] >> (key.index() % bitsPerWord) & 1u);
    }
    size_type count(Key key) const { return contains(key) ? 1 : 0; }
    size_type size() const {
        size_type total = 0;
        for (const auto word : bits_) total += static_cast<size_type>(std::popcount(word));
        return total;
    }
    bool empty() const {
        for (const auto word : bits_)
            if (word) return false;
        return true;
    }
    void clear() { bits_ = {}; }

    std::pair<const_iterator, bool> insert(Key key) {
        if (!key.valid()) throw std::out_of_range("NumberSet: a key with no name");
        auto& word = bits_[key.index() / bitsPerWord];
        const auto bit = std::uint64_t {1} << (key.index() % bitsPerWord);
        const bool inserted = !(word & bit);
        word |= bit;
        return {const_iterator(this, key.index()), inserted};
    }
    template <class It>
    void insert(It first, It last) {
        for (; first != last; ++first) insert(*first);
    }
    std::pair<const_iterator, bool> emplace(Key key) { return insert(key); }
    size_type erase(Key key) {
        if (!contains(key)) return 0;
        bits_[key.index() / bitsPerWord] &= ~(std::uint64_t {1} << (key.index() % bitsPerWord));
        return 1;
    }

    // Keeps only the members the other set also holds.
    NumberSet& operator&=(const NumberSet& other) {
        for (std::size_t word = 0; word < wordCount; ++word) bits_[word] &= other.bits_[word];
        return *this;
    }

    friend bool operator==(const NumberSet&, const NumberSet&) = default;

  private:
    std::array<std::uint64_t, wordCount> bits_ {};
};

}  // namespace game::campaign

template <class Kind>
struct std::hash<game::campaign::Number<Kind>> {
    std::size_t operator()(game::campaign::Number<Kind> number) const noexcept {
        return std::hash<std::size_t> {}(number.index());
    }
};
