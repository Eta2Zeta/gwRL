"""Shared read-only Metal views of the lossless native state record format.

Pointers address one lane; child and end indices are local to that lane. Helpers
never decode through float, allocate on the host or inspect execution values on
CPU. A failed lookup remains distinct from an absent optional/map entry.
"""

METAL_STATE_SOURCE = r"""
struct PackedStateView {
    device const long* records;
    long length;
    long capacity;
    device const uchar* prefix_bytes;
    device const long* prefix_offsets;
    long prefix_count;
    long prefix_bytes_length;
    device const uchar* suffix_bytes;
    device const long* suffix_offsets;
    long suffix_count;
    long suffix_bytes_length;
};

inline bool state_node(thread const PackedStateView& view, long index) {
    return index >= 0 && index < view.length && index < view.capacity;
}

inline device const long* state_record(thread const PackedStateView& view, long index) {
    return view.records + ulong(index) * 5;
}

inline long state_end(thread const PackedStateView& view, long index, thread bool& valid) {
    if (!state_node(view, index)) { valid = false; return -1; }
    const long end = state_record(view, index)[4];
    if (end <= index || end > view.length || end > view.capacity) { valid = false; return -1; }
    return end;
}

inline ulong state_raw_bits(thread const PackedStateView& view, long index, int tag, thread bool& valid) {
    if (!state_node(view, index)) { valid = false; return 0; }
    device const long* row = state_record(view, index);
    if (row[0] != tag || row[1] != 0 || row[2] < 0 || row[2] > 0xffffffffL ||
        row[3] < 0 || row[3] > 0xffffffffL || row[4] != index + 1) {
        valid = false; return 0;
    }
    return ulong(row[2]) | (ulong(row[3]) << 32);
}

inline long state_signed_value(thread const PackedStateView& view, long index, thread bool& valid) {
    return as_type<long>(state_raw_bits(view, index, 2, valid));
}

inline ulong state_unsigned_value(thread const PackedStateView& view, long index, thread bool& valid) {
    return state_raw_bits(view, index, 3, valid);
}

inline bool state_boolean_value(thread const PackedStateView& view, long index, thread bool& valid) {
    if (!state_node(view, index)) { valid = false; return false; }
    device const long* row = state_record(view, index);
    if (row[0] != 1 || row[1] < 0 || row[1] > 1 || row[2] || row[3] || row[4] != index + 1) {
        valid = false; return false;
    }
    return row[1] == 1;
}

inline long state_child(thread const PackedStateView& view, long parent, long child, thread bool& valid) {
    const long end = state_end(view, parent, valid);
    if (!valid) return -1;
    device const long* row = state_record(view, parent);
    const long tag = row[0], count = row[1];
    // Map/JSON-object counts are pairs; their lookup helpers handle those.
    if ((tag != 6 && tag != 8 && tag != 9 && tag != 10 && tag != 11 && tag != 12) ||
        count < 0 || child < 0 || child >= count || row[2] || row[3]) {
        valid = false; return -1;
    }
    long cursor = parent + 1;
    for (long field = 0; field < child; ++field) {
        cursor = state_end(view, cursor, valid);
        if (!valid || cursor >= end) { valid = false; return -1; }
    }
    if (cursor >= end || state_end(view, cursor, valid) > end) { valid = false; return -1; }
    return cursor;
}

inline long state_optional(thread const PackedStateView& view, long parent, thread bool& present, thread bool& valid) {
    if (!state_node(view, parent)) { valid = false; present = false; return -1; }
    device const long* row = state_record(view, parent);
    if (row[0] != 9 || row[1] < 0 || row[1] > 1 || row[2] || row[3]) {
        valid = false; present = false; return -1;
    }
    present = row[1] == 1;
    if (!present) {
        if (row[4] != parent + 1) valid = false;
        return -1;
    }
    const long child = state_child(view, parent, 0, valid);
    if (valid && state_end(view, child, valid) != row[4]) valid = false;
    return child;
}

inline long state_string_id(thread const PackedStateView& view, long index, thread bool& valid) {
    if (!state_node(view, index)) { valid = false; return -1; }
    device const long* row = state_record(view, index);
    if (row[0] != 5 || row[1] < 0 || row[1] >= view.prefix_count + view.suffix_count ||
        row[2] || row[3] || row[4] != index + 1) {
        valid = false; return -1;
    }
    return row[1];
}

inline bool state_string_id_equals(thread const PackedStateView& view, long id,
                                   constant char* text, long length, thread bool& valid) {
    if (id < 0 || id >= view.prefix_count + view.suffix_count) { valid = false; return false; }
    const bool prefix = id < view.prefix_count;
    const long local = prefix ? id : id - view.prefix_count;
    device const long* offsets = prefix ? view.prefix_offsets : view.suffix_offsets;
    device const uchar* bytes = prefix ? view.prefix_bytes : view.suffix_bytes;
    const long start = offsets[local], end = offsets[local + 1];
    if (start < 0 || end < start || end > (prefix ? view.prefix_bytes_length : view.suffix_bytes_length)) {
        valid = false; return false;
    }
    if (end - start != length) return false;
    for (long i = 0; i < length; ++i) if (bytes[start + i] != uchar(text[i])) return false;
    return true;
}

inline bool state_string_equals(thread const PackedStateView& view, long index,
                                constant char* text, long length, thread bool& valid) {
    const long id = state_string_id(view, index, valid);
    return valid && state_string_id_equals(view, id, text, length, valid);
}

inline long state_map_find_id(thread const PackedStateView& view, long parent, long key, thread bool& valid) {
    const long end = state_end(view, parent, valid);
    if (!valid) return -1;
    device const long* row = state_record(view, parent);
    if ((row[0] != 7 && row[0] != 13) || row[1] < 0 || row[1] > (end - parent - 1) / 2 || row[2] || row[3]) {
        valid = false; return -1;
    }
    long cursor = parent + 1;
    for (long entry = 0; entry < row[1]; ++entry) {
        const long found = state_string_id(view, cursor, valid);
        const long value = state_end(view, cursor, valid);
        if (!valid || value >= end) { valid = false; return -1; }
        const long next = state_end(view, value, valid);
        if (!valid || next > end) { valid = false; return -1; }
        if (found == key) return value;
        cursor = next;
    }
    if (cursor != end) valid = false;
    return -1;
}

inline long state_map_find_literal(thread const PackedStateView& view, long parent,
                                   constant char* key, long length, thread bool& valid) {
    const long end = state_end(view, parent, valid);
    if (!valid) return -1;
    device const long* row = state_record(view, parent);
    if ((row[0] != 7 && row[0] != 13) || row[1] < 0 || row[1] > (end - parent - 1) / 2 || row[2] || row[3]) {
        valid = false; return -1;
    }
    long cursor = parent + 1;
    for (long entry = 0; entry < row[1]; ++entry) {
        const bool found = state_string_equals(view, cursor, key, length, valid);
        const long value = state_end(view, cursor, valid);
        if (!valid || value >= end) { valid = false; return -1; }
        const long next = state_end(view, value, valid);
        if (!valid || next > end) { valid = false; return -1; }
        if (found) return value;
        cursor = next;
    }
    if (cursor != end) valid = false;
    return -1;
}
"""
