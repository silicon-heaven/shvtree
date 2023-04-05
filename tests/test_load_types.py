"""Validate loading types from basic type representation."""
import decimal

import pytest
import ruamel.yaml

from shvtree import (
    SHVTypeAlias,
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
    shvList,
    shvNull,
    shvString,
    shvUInt,
)
from shvtree.load import load_types
from shvtree.namedset import NamedSet

from . import trees

_nullAlias = SHVTypeAlias("nullAlias", shvNull)

_myIMap = SHVTypeIMap("myimap")
_myIMap[0] = shvString
_myIMap[1] = shvDateTime
_myIMap[7] = shvBlob

_someEnum = SHVTypeEnum("someenum", "name", "surname")


@pytest.mark.parametrize(
    "repre,expected",
    (
        ({"foo": "Null"}, NamedSet(SHVTypeAlias("foo", shvNull))),
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
                    "values": ["one", "two", {"four": 4, "six": 6}, "seven"],
                }
            },
            NamedSet(SHVTypeEnum("foo", "one", "two", four=4, six=6, seven=7)),
        ),
        (
            {
                "nullAlias": "Null",
                "somelist": {
                    "type": "List",
                    "allowed": ["nullAlias", "String"],
                },
            },
            NamedSet(_nullAlias, SHVTypeList("somelist", _nullAlias, shvString)),
        ),
        (
            {
                "footuple": {"type": "Tuple", "fields": ["Decimal", "UInt"]},
            },
            NamedSet(
                SHVTypeTuple("footuple", shvDecimal, shvUInt),
            ),
        ),
        (
            {
                "someenum": {
                    "type": "Enum",
                    "values": ["name", "surname"],
                },
                "sometuple": {
                    "type": "Tuple",
                    "fields": ["String", "String"],
                    "enum": "someenum",
                },
            },
            NamedSet(
                _someEnum,
                SHVTypeTuple("sometuple", shvString, shvString, enum=_someEnum),
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
                    "fields": ["String", "DateTime", {"Blob": 7}],
                }
            },
            NamedSet(_myIMap),
        ),
    ),
)
def test_load_types(repre, expected):
    res = load_types(repre)
    assert res == expected


def test_load_type_invalid_builtin():
    with pytest.raises(RuntimeError):
        load_types({"Double": shvDouble})


def test_load_type_invalid_repre():
    with pytest.raises(TypeError):
        load_types({"invalid": set()})


def test_load_type_invalid_no_type():
    with pytest.raises(KeyError):
        load_types({"notype": {}})


def test_load_type_invalid_key():
    with pytest.raises(ValueError):
        load_types({"toomuch": {"type": "List", "invalid": None}})


def test_load_type_invalid_missing():
    with pytest.raises(ValueError):
        load_types({"toomuch": "nosuchtype"})


def test_load_type_invalid_enum():
    with pytest.raises(ValueError):
        load_types({"foo": {"type": "Enum", "values": [None]}})


def test_load_type_invalid_tuple_enum():
    with pytest.raises(ValueError):
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
