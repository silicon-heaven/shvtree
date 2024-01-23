"""Check that we have correctly implemented types descriptions."""
import datetime
import decimal

import pytest

from shvtree import (
    SHVTypeBitfield,
    SHVTypeBlob,
    SHVTypeDecimal,
    SHVTypeDouble,
    SHVTypeEnum,
    SHVTypeIMap,
    SHVTypeInt,
    SHVTypeList,
    SHVTypeMap,
    SHVTypeOneOf,
    SHVTypeString,
    shvAny,
    shvBlob,
    shvBool,
    shvDateTime,
    shvDecimal,
    shvDouble,
    shvInt,
    shvInt8,
    shvInt16,
    shvInt32,
    shvInt64,
    shvList,
    shvNull,
    shvString,
    shvUInt,
    shvUInt8,
    shvUInt16,
    shvUInt32,
    shvUInt64,
    types,
)


@pytest.mark.parametrize(
    "obj1,obj2",
    [
        (shvAny, types.SHVTypeAny()),
        (shvNull, types.SHVTypeNull()),
        (shvBool, types.SHVTypeBool()),
        (shvInt, types.SHVTypeInt("Int")),
        (shvUInt, types.SHVTypeInt("UInt", minimum=0)),
        (shvDouble, types.SHVTypeDouble("Double")),
        (shvDecimal, types.SHVTypeDecimal("Decimal")),
        (shvBlob, types.SHVTypeBlob("Blob")),
        (shvString, types.SHVTypeString("String")),
        (shvDateTime, types.SHVTypeDateTime()),
        (shvList, types.SHVTypeList("List")),
    ],
)
def test_signletons(obj1, obj2):
    """Check that our signleton types can't be recreated."""
    assert obj1 is obj2


@pytest.mark.parametrize(
    "shvtype,value",
    (
        (shvAny, "foo"),
        (shvAny, 1),
        (shvAny, True),
        (shvAny, None),
        (shvAny, b"foo"),
        (shvNull, None),
        (shvBool, True),
        (shvBool, False),
        (shvInt, 4),
        (shvInt, 0),
        (shvInt, -9),
        (shvUInt, 4),
        (shvUInt, 0),
        (shvDouble, 4.0),
        (shvDouble, -9.5),
        (shvDouble, 0.0),
        (shvBlob, b"foo"),
        (shvString, "foo"),
        (shvDateTime, datetime.datetime.now()),
        (shvDecimal, decimal.Decimal("5e2")),
        (shvDecimal, decimal.Decimal("0")),
        (SHVTypeDouble("foo", minimum=0.0, maximum=1.0), 0.5),
        (
            SHVTypeDecimal(
                "foo", minimum=decimal.Decimal("0"), maximum=decimal.Decimal("1")
            ),
            decimal.Decimal("0.5"),
        ),
        (SHVTypeString("foo", max_length=2), "f"),
        (SHVTypeString("foo", pattern=r"^o*$"), "oo"),
        (SHVTypeBlob("foo", max_length=2), b"f"),
        (SHVTypeList("foo", shvString, minlen=1, maxlen=2), ["foo"]),
    ),
)
def test_valid(shvtype, value):
    assert shvtype.validate(value) is True


@pytest.mark.parametrize(
    "shvtype,value",
    (
        (shvAny, complex(1, 1)),
        (shvNull, "foo"),
        (shvNull, 5),
        (shvNull, False),
        (shvBool, None),
        (shvBool, "false"),
        (shvInt, None),
        (shvInt, "foo"),
        (shvUInt, -1),
        (shvUInt, None),
        (shvUInt, "foo"),
        (shvDouble, 4),
        (shvDouble, None),
        (shvBlob, "foo"),
        (shvBlob, None),
        (shvString, b"foo"),
        (shvString, None),
        (shvDateTime, None),
        (shvDecimal, 0),
        (shvDecimal, 0.0),
        (shvDecimal, None),
        (SHVTypeDouble("foo", minimum=0.0, maximum=1.0), 1.1),
        (SHVTypeString("foo", max_length=2), "foo"),
        (SHVTypeString("foo", pattern=r"^o*$"), "foo"),
        (SHVTypeBlob("foo", max_length=2), b"foo"),
        (SHVTypeList("foo", shvString, minlen=1, maxlen=2), []),
        (SHVTypeList("foo", shvString, minlen=1, maxlen=2), ["1", "2", "3"]),
    ),
)
def test_invalid(shvtype, value):
    assert shvtype.validate(value) is False


@pytest.mark.parametrize(
    "inttype,cnt",
    (
        (shvInt, None),
        (shvInt8, 1),
        (shvInt16, 2),
        (shvInt32, 4),
        (shvInt64, 8),
        (shvUInt, None),
        (shvUInt8, 1),
        (shvUInt16, 2),
        (shvUInt32, 4),
        (shvUInt64, 8),
        (SHVTypeInt("foo", minimum=1), None),
        (SHVTypeInt("foo", minimum=0, maximum=0), None),
        (SHVTypeInt("foo", minimum=0, maximum=1), 1),
        (SHVTypeInt("foo", minimum=-1, maximum=0), 1),
        (SHVTypeInt("foo", minimum=-1, maximum=255), 2),
    ),
)
def test_int_bytes_size(inttype, cnt):
    assert inttype.bytes_size() == cnt


@pytest.mark.parametrize(
    "inttype,is_unsigned",
    (
        (shvInt, False),
        (shvInt8, False),
        (shvInt16, False),
        (shvInt32, False),
        (shvInt64, False),
        (shvUInt, True),
        (shvUInt8, True),
        (shvUInt16, True),
        (shvUInt32, True),
        (shvUInt64, True),
        (SHVTypeInt("foo", minimum=0, maximum=0), True),
        (SHVTypeInt("foo", minimum=0, maximum=1), True),
        (SHVTypeInt("foo", minimum=-1, maximum=0), False),
        (SHVTypeInt("foo", minimum=-1, maximum=255), False),
    ),
)
def test_int_is_unsigned(inttype, is_unsigned):
    assert inttype.unsigned is is_unsigned


def test_int_duplicate():
    with pytest.raises(ValueError, match=r"^Please use shvInt instead$"):
        SHVTypeInt("foo")


def test_uint_duplicate():
    with pytest.raises(ValueError, match=r"^Please use shvUInt instead$"):
        SHVTypeInt("foo", minimum=0)


def test_double_duplicate():
    with pytest.raises(ValueError, match=r"^Please use shvDouble instead$"):
        SHVTypeDouble("foo")


def test_decimal_duplicate():
    with pytest.raises(ValueError, match=r"^Please use shvDecimal instead$"):
        SHVTypeDecimal("foo")


def test_string_duplicate():
    with pytest.raises(ValueError, match=r"^Please use shvString instead$"):
        SHVTypeString("foo")


def test_blob_duplicate():
    with pytest.raises(ValueError, match=r"^Please use shvBlob instead$"):
        SHVTypeBlob("foo")


def test_enum():
    """Check if we have correct implementation of enum."""
    enum = SHVTypeEnum("foo", "one", "two", three=5)
    assert enum.name == "foo"
    assert enum["one"] == 0
    assert enum["two"] == 1
    assert enum["three"] == 5
    with pytest.raises(KeyError):
        _ = enum["none"]


def test_enum_modify():
    """Check if we can modify enum."""
    enum = SHVTypeEnum("foo")
    with pytest.raises(KeyError):
        _ = enum["one"]
    enum["one"] = 3
    assert enum["one"] == 3
    del enum["one"]
    with pytest.raises(KeyError):
        _ = enum["one"]


@pytest.mark.parametrize(
    "value,res",
    (
        ("one", True),
        ("two", True),
        ("three", False),
        ("four", True),
        ("foo", False),
        (0, True),
        (1, True),
        (2, False),
        (4, True),
        (5, False),
        (None, False),
    ),
)
def test_enum_validate(value, res):
    enum = SHVTypeEnum("foo", "one", "two", four=4)
    assert enum.validate(value) == res


@pytest.mark.parametrize(
    "tp,span",
    (
        (shvBool, 1),
        (shvNull, 1),
        (SHVTypeEnum("foo", "one", "two"), 1),
        (shvUInt8, 8),
        (SHVTypeInt("foo", minimum=4, maximum=17), 5),
        (SHVTypeInt("foo", maximum=17), None),
        (shvString, None),
    ),
)
def test_bitfield_type_span(tp, span):
    """Check our implementation of bitfield."""
    assert SHVTypeBitfield.type_span(tp) == span


def test_bitfield():
    """Check our implementation of bitfield."""
    uint = SHVTypeInt("bitvarInt", minimum=1, maximum=6)
    bitfield = SHVTypeBitfield("bitvar", shvBool, shvNull, uint, shvUInt8)
    assert bitfield.name == "bitvar"
    assert bitfield.bitsize() == 13
    assert bitfield.get(0) == shvBool
    assert bitfield.get(2) == uint
    with pytest.raises(ValueError):
        _ = bitfield.get(3)
    assert bitfield.get(5) == shvUInt8


def test_bitfield_from_enum():
    """Check our implementation of bitfield initialzied from enum."""
    enum = SHVTypeEnum("bitfooEnum", "one", "two", four=4, last=63)
    bitfield = SHVTypeBitfield.from_enum("bitfoo", enum)
    assert bitfield.name == "bitfoo"
    assert bitfield.bitsize() == 64
    assert bitfield.get("one") == shvBool
    assert bitfield.get("two") == shvBool
    assert bitfield.get(1) == shvBool
    assert bitfield.get("four") == shvBool
    assert bitfield.get("last") == shvBool
    assert bitfield.get("last") == shvBool
    with pytest.raises(KeyError):
        _ = bitfield.get("none")
    with pytest.raises(ValueError):
        _ = bitfield.get(64)
    with pytest.raises(ValueError):
        _ = bitfield.get(-1)


@pytest.mark.parametrize(
    "value,res",
    (
        (0x2, [False, 1, False, False]),
        (0x3, [True, 1, False, False]),
        (0x4, [False, 2, False, False]),
        (0xD, [True, 6, False, False]),
        (0x800000000000000C, [False, 6, False, True]),
    ),
)
def test_bitfield_interpret(value, res):
    bitfield = SHVTypeBitfield(
        "bitfield", shvBool, SHVTypeInt("foo", minimum=1, maximum=6), shvNull, shvBool
    )
    bitfield.set(63, shvBool)
    assert bitfield.interpret(value) == res


@pytest.mark.parametrize(
    "value,res",
    (
        (0x0, True),
        (0x1, True),
        (0x3, True),
        (0x11, False),
        (0x21, True),
        (0x8000000000000000, True),
        ("one", False),
    ),
)
def test_bitfield_value(value, res):
    bitfield = SHVTypeBitfield(
        "foo", shvBool, SHVTypeInt("foo", minimum=0, maximum=6), shvNull, shvBool
    )
    bitfield.set(63, shvBool)
    print(list(bitfield.types()))
    assert bitfield.validate(value) == res


def test_list():
    """Check that we have correct implementation for list."""
    lst = SHVTypeList("listfoo", shvUInt)
    assert lst.name == "listfoo"
    assert lst.allowed is shvUInt


def test_list_modify():
    """Check that we can modify list."""
    lst = SHVTypeList("foo", shvInt)
    assert lst.allowed is shvInt
    lst.allowed = shvString
    assert lst.allowed is shvString


# TODO check SHVTypeTuple


def test_map():
    """Check our implementation of map type representation."""
    mp = SHVTypeMap("foomap", null=shvNull, string=shvString)
    assert mp.name == "foomap"
    assert mp["null"] is shvNull
    assert mp["string"] is shvString
    with pytest.raises(KeyError):
        _ = mp["none"]


def test_map_modify():
    """Check that we can modify the map type content."""
    mp = SHVTypeMap("foo")
    assert "double" not in mp
    mp["double"] = shvDouble
    assert "double" in mp
    del mp["double"]
    assert "double" not in mp


# TODO test SHVTypeImap


def test_one_of():
    oneof = SHVTypeOneOf("fooof", shvNull, shvBlob)
    assert oneof.name == "fooof"
    assert shvNull in oneof
    assert shvBlob in oneof
    assert len(oneof) == 2
    assert shvNull in oneof
    assert shvBlob in oneof


def test_one_of_modify():
    oneof = SHVTypeOneOf("foo")
    assert shvNull not in oneof
    oneof.add(shvNull)
    assert shvNull in oneof
    oneof.discard(shvNull)
    assert shvNull not in oneof
