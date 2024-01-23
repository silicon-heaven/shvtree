"""Validate loading types from basic type representation."""
import decimal

import pytest
import ruamel.yaml

from shvtree import (
    SHVTypeAlias,
    SHVTypeBitfield,
    SHVTypeDecimal,
    SHVTypeDouble,
    SHVTypeEnum,
    SHVTypeIMap,
    SHVTypeInt,
    SHVTypeList,
    SHVTypeMap,
    SHVTypeOneOf,
    SHVTypeString,
    SHVTypeTuple,
    shvBlob,
    shvBool,
    shvDateTime,
    shvDecimal,
    shvDouble,
    shvInt,
    shvList,
    shvNull,
    shvString,
    shvUInt,
    shvUInt8,
)
from shvtree.load import SHVTreeValueError, load_types
from shvtree.namedset import NamedSet

from . import trees

_nullAlias = SHVTypeAlias("nullAlias", shvNull)

_myIMapEnum = SHVTypeEnum("myimapEnum", "one", "two")
_myIMapEnum["seven"] = 7

_myIMap = SHVTypeIMap("myimap", enum=_myIMapEnum)
_myIMap[0] = shvString
_myIMap[1] = shvDateTime
_myIMap[7] = shvBlob

_sometupleEnum = SHVTypeEnum("sometupleEnum", "name", "surname")

_simpleListOneOf = SHVTypeOneOf("simplelistOneOf", _nullAlias, shvString)
_someListOneOf = SHVTypeOneOf("somelistOneOf", shvInt, shvString)

_somebitEnum = SHVTypeEnum("somebitEnum", "one", "two", five=4, last=63)


@pytest.mark.parametrize(
    "repre,expected",
    (
        (
            {"foo": {"type": "Int", "minimum": 8, "maximum": 12}},
            NamedSet(SHVTypeInt("foo", 8, 12)),
        ),
        (
            {"foo": {"type": "Int", "multipleOf": 2}},
            NamedSet(SHVTypeInt("foo", multiple_of=2)),
        ),
        (
            {
                "foo": {
                    "type": "Double",
                    "minimum": -1.0,
                    "maximum": 1.0,
                    "multipleOf": 0.02,
                }
            },
            NamedSet(SHVTypeDouble("foo", minimum=-1.0, maximum=1.0, multiple_of=0.02)),
        ),
        (
            {"foo": {"type": "Double", "exclusiveMinimum": 0, "exclusiveMaximum": 1}},
            NamedSet(
                SHVTypeDouble("foo", exclusive_minimum=0.0, exclusive_maximum=1.0)
            ),
        ),
        (
            {
                "foo": {
                    "type": "Decimal",
                    "minimum": "-1",
                }
            },
            NamedSet(SHVTypeDecimal("foo", minimum=-decimal.Decimal("1"))),
        ),
        (
            {
                "foo": {
                    "type": "Decimal",
                    "maximum": "1e1000",
                }
            },
            NamedSet(SHVTypeDecimal("foo", maximum=decimal.Decimal("1e1000"))),
        ),
        (
            {"foo": {"type": "String", "minLength": 6, "maxLength": 80}},
            NamedSet(SHVTypeString("foo", 6, 80)),
        ),
        (
            {"foo": {"type": "String", "pattern": r"[a-z0-9]+"}},
            NamedSet(SHVTypeString("foo", pattern=r"[a-z0-9]+")),
        ),
        (
            {"foo": {"type": "Blob", "minLength": 64}},
            NamedSet(SHVTypeString("foo", 64)),
        ),
        (
            {"foo": {"type": "Blob", "maxLength": 64}},
            NamedSet(SHVTypeString("foo", max_length=64)),
        ),
        ({"foo": "Null"}, NamedSet(SHVTypeAlias("foo", shvNull))),
        (
            {"one": "List", "two": "Bool"},
            NamedSet(SHVTypeAlias("two", shvBool), SHVTypeAlias("one", shvList)),
        ),
        (
            {"some": ["Null", "String"]},
            NamedSet(SHVTypeOneOf("some", shvNull, shvString)),
        ),
        (
            {
                "foo": {
                    "type": "Enum",
                    "values": [
                        "one",
                        "two",
                        {"four": 4, "six": 6},
                        "seven",
                        None,
                        "nine",
                        6,
                        "sixteen",
                    ],
                }
            },
            NamedSet(
                SHVTypeEnum(
                    "foo", "one", "two", four=4, six=6, seven=7, nine=9, sixteen=16
                )
            ),
        ),
        (
            {
                "nullAlias": "Null",
                "simplelist": {
                    "type": "List",
                    "allowed": ["nullAlias", "String"],
                },
            },
            NamedSet(
                SHVTypeList("simplelist", _simpleListOneOf),
                _simpleListOneOf,
                _nullAlias,
            ),
        ),
        (
            {
                "somelistOneOf": ["Int", "String"],
                "somelist": {
                    "type": "List",
                    "allowed": "somelistOneOf",
                    "minlen": 1,
                    "maxlen": 8,
                },
            },
            NamedSet(
                _someListOneOf,
                SHVTypeList("somelist", _someListOneOf, minlen=1, maxlen=8),
            ),
        ),
        (
            {
                "footuple": {"type": "Tuple", "items": ["Decimal", "UInt"]},
            },
            NamedSet(
                SHVTypeTuple("footuple", shvDecimal, shvUInt),
            ),
        ),
        (
            {
                "sometupleEnum": {
                    "type": "Enum",
                    "values": ["name", "surname"],
                },
                "sometuple": {
                    "type": "Tuple",
                    "items": ["String", "String"],
                    "enum": "sometupleEnum",
                },
            },
            NamedSet(
                _sometupleEnum,
                SHVTypeTuple("sometuple", shvString, shvString, enum=_sometupleEnum),
            ),
        ),
        (
            {
                "sometuple": {
                    "type": "Tuple",
                    "items": ["String", "String"],
                    "enum": ["name", "surname"],
                },
            },
            NamedSet(
                _sometupleEnum,
                SHVTypeTuple("sometuple", shvString, shvString, enum=_sometupleEnum),
            ),
        ),
        (
            {
                "somebit": {
                    "type": "Bitfield",
                    "enum": ["one", "two", 2, "five", {"last": 63}],
                },
            },
            NamedSet(_somebitEnum, SHVTypeBitfield.from_enum("somebit", _somebitEnum)),
        ),
        (
            {
                "unknownbit": {
                    "type": "Bitfield",
                    "types": ["Bool", 2, "UInt8", {"Bool": 12}],
                },
            },
            NamedSet(
                SHVTypeBitfield(
                    "unknownbit", shvBool, shvNull, shvNull, shvUInt8, shvNull, shvBool
                )
            ),
        ),
        (
            {
                "mymap": {
                    "type": "Map",
                    "fields": {"one": "String", "two": "DateTime"},
                }
            },
            NamedSet(SHVTypeMap("mymap", one=shvString, two=shvDateTime)),
        ),
        (
            {
                "myimap": {
                    "type": "IMap",
                    "enum": "myimapEnum",
                    "fields": ["String", "DateTime", {"Blob": 7}],
                },
                "myimapEnum": {
                    "type": "Enum",
                    "values": ["one", "two", {"seven": 7}],
                },
            },
            NamedSet(_myIMap, _myIMapEnum),
        ),
        (
            {
                "myimap": {
                    "type": "IMap",
                    "enum": ["one", "two", {"seven": 7}],
                    "fields": {"one": "String", "two": "DateTime", "seven": "Blob"},
                },
            },
            NamedSet(_myIMap, _myIMapEnum),
        ),
    ),
)
def test_load_types(repre, expected):
    res = load_types(repre)
    assert res == expected


def test_load_type_invalid_builtin():
    with pytest.raises(SHVTreeValueError):
        load_types({"Double": shvDouble})


def test_load_type_invalid_repre():
    with pytest.raises(SHVTreeValueError):
        load_types({"invalid": set()})


def test_load_type_invalid_no_type():
    with pytest.raises(SHVTreeValueError):
        load_types({"notype": {}})


def test_load_type_invalid_key():
    with pytest.raises(SHVTreeValueError):
        load_types({"toomuch": {"type": "List", "invalid": None}})


def test_load_type_invalid_missing():
    with pytest.raises(SHVTreeValueError):
        load_types({"toomuch": "nosuchtype"})


def test_load_type_invalid_enum():
    with pytest.raises(SHVTreeValueError):
        load_types({"foo": {"type": "Enum", "values": [0.0]}})


def test_load_type_invalid_tuple_enum():
    with pytest.raises(SHVTreeValueError):
        load_types({"foo": {"type": "Tuple", "enum": "Int"}})


def test_load_type_invalid_imap_fields():
    with pytest.raises(ValueError):
        load_types({"foo": {"type": "IMap", "fields": [3]}})


def test_load_type_tree1(path_tree1):
    """Check tree1 types."""
    yaml = ruamel.yaml.YAML(typ="safe")
    raw_tree = yaml.load(path_tree1)
    res = load_types(raw_tree["types"])
    assert res == trees.tree1_types
