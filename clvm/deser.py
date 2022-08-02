from typing import List, Tuple



MAX_SINGLE_BYTE = 0x7F
CONS_BOX_MARKER = 0xFF


class InPlace:
    def __init__(self, blob, int_triples, index):
        self.blob = blob
        self.int_triples = int_triples
        self.index = index

    @property
    def atom(self):
        cursor, atom_offset, end = self.int_triples[self.index]
        if self.blob[cursor] == 0xff:
            return None
        return self.blob[cursor + atom_offset:end]

    @property
    def pair(self):
        cursor, right_index, end = self.int_triples[self.index]
        if self.blob[cursor] != 0xff:
            return None
        left = self.__class__(self.blob, self.int_triples, self.index + 1)
        right = self.__class__(self.blob, self.int_triples, right_index)
        return (left, right)

    def as_bin(self):
        cursor, _, end = self.int_triples[self.index]
        return self.blob[cursor:end]

    def __str__(self):
        return self.as_bin().hex()
        a = self.atom
        if a is not None:
            return a.hex()
        return f"({self.index+1}, {self.int_triples[self.index][1]})"

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self}>"


def _atom_size_from_cursor(blob, cursor) -> Tuple[int, int]:
    # return `(size_of_prefix, cursor)`
    b = blob[cursor]
    if b == 0x80:
        return 1, cursor + 1
    if b <= MAX_SINGLE_BYTE:
        return 0, cursor + 1
    bit_count = 0
    bit_mask = 0x80
    while b & bit_mask:
        bit_count += 1
        b &= 0xFF ^ bit_mask
        bit_mask >>= 1
    size_blob = bytes([b])
    if bit_count > 1:
        breakpoint()
        size_blob += blob[cursor+1:cursor+bit_count]
    size = int.from_bytes(size_blob, "big")
    if size >= 0x400000000:
        raise ValueError("blob too large")
    return bit_count, cursor + size + bit_count


# ATOM: serialize_offset, atom_offset, serialize_end
# PAIR: serialize_offset, right_index, serialize_end

def deserialized_in_place(blob: bytes, cursor: int = 0) -> List[Tuple[int, int, int]]:

    def save_cursor(index, blob, cursor, obj_list, op_stack):
        obj_list[index] = (obj_list[index][0], obj_list[index][1], cursor)
        return cursor

    def save_index(index, blob, cursor, obj_list, op_stack):
        obj_list[index][1] = len(obj_list)
        return cursor

    def parse_obj(blob, cursor, obj_list, op_stack):
        if cursor >= len(blob):
            raise ValueError("bad encoding")

        if blob[cursor] == CONS_BOX_MARKER:
            index = len(obj_list)
            obj_list.append([cursor, None, None])
            op_stack.append(lambda *args: save_cursor(index, *args))
            op_stack.append(parse_obj)
            op_stack.append(lambda *args: save_index(index, *args))
            op_stack.append(parse_obj)
            return cursor + 1
        atom_offset, new_cursor = _atom_size_from_cursor(blob, cursor)
        obj_list.append((cursor, atom_offset, new_cursor))
        return new_cursor

    obj_list = []
    op_stack = [parse_obj]
    while op_stack:
        f = op_stack.pop()
        cursor = f(blob, cursor, obj_list, op_stack)

    v = InPlace(blob, obj_list, 0)
    return v



def check(h):
    b = bytes.fromhex(h)
    t = deserialized_in_place(b)
    assert t.as_bin() == b
    print(repr(t))
    if t.pair:
        print(f"* {repr(t.pair[0])}, {repr(t.pair[1])}")

check("80")
check("64")
check("86666f6f626172")
check("ff8080")
check("ff83666f6f83626172")
check("ff83666f6fff8362617280")
check("ff83666f6fffff83626172ff8362617a80ff85717561636b80")
gen_hex = open("generator.hex", "r").read()
breakpoint()
check(gen_hex)