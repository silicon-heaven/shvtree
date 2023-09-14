"""Implementation of loading and validation of the SHV Tree."""
import collections.abc
import decimal
import json
import pathlib
import typing

import ruamel.yaml
import shv

from . import namedset
from .method import SHVMethod
from .node import SHVNode
from .shvtree import SHVTree
from .types import (
    SHVTypeAlias,
    SHVTypeBase,
    SHVTypeBitfield,
    SHVTypeBlob,
    SHVTypeConstant,
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
    shvAny,
    shvNull,
)
from .types_builtins import shvBuiltins


def load(path: str | pathlib.Path) -> SHVTree:
    """Construct SHVTree out of provided basic representation.

    :param path: Path to the file describing the SHV Tree.
    :returns: instace of SHVTree.
    """
    if isinstance(path, str):
        path = pathlib.Path(path)
    if path.suffix in (".yaml", ".yml"):
        return load_yaml(path)
    if path.suffix == ".json":
        with path.open("rb") as file:
            return load_json(file)
    raise RuntimeError(f"Unknown file suffix: {path}")


def load_yaml(stream: str | typing.TextIO | pathlib.Path) -> SHVTree:
    """Construct SHVTree out of provided basic representation in YAML.

    :param stream: Data or data stream with YAML or pathlib.Path to the file.
    :returns: instace of SHVTree.
    """
    yaml = ruamel.yaml.YAML(typ="safe")
    raw_tree = yaml.load(stream)
    return load_raw(raw_tree)


def load_json(stream: str | typing.IO) -> SHVTree:
    """Construct SHVTree out of provided basic representation in JSON.

    :param stream: Data or data stream with JSON.
    :returns: instace of SHVTree.
    """
    if isinstance(stream, str):
        raw_tree = json.loads(stream)
    else:
        raw_tree = json.load(stream)
    return load_raw(raw_tree)


def load_raw(data: collections.abc.Mapping[str, typing.Any]) -> SHVTree:
    """Construct SHVTree out of provided basic representation.

    :param data: SHV Tree representation in plain Python types.
    :returns: instace of SHVTree.
    """
    data = dict(data)  # copy so we can use pop

    # Load types
    dtypes = data.pop("types", {})
    shvtypes = load_types(dtypes if dtypes is not None else {})

    # Load nodes
    dnodes = data.pop("nodes", None)
    shvnodes = load_nodes(dnodes if dnodes is not None else {}, shvtypes)

    if data:
        keys = ", ".join(data.keys())
        raise ValueError(f"Unsupported keys: {keys}")

    return SHVTree(types=shvtypes, nodes=shvnodes)


def _get_type(types: namedset.NamedSet[SHVTypeBase], name: str | None) -> SHVTypeBase:
    if name is None:
        # Some formats such as YAML allow None to be loaded when Null or
        # other like that strings are used. We support this and consider it
        # to be shvNull type.
        return shvNull
    if name in shvBuiltins:
        return shvBuiltins[name]
    if name not in types:
        raise ValueError(f"Invalid type reference name: {name}")
    return types[name]


def _get_enum(types: namedset.NamedSet[SHVTypeBase], name: str | None) -> SHVTypeEnum:
    tp = _get_type(types, name)
    if not isinstance(tp, SHVTypeEnum):
        raise ValueError(f"Invalid type used as enum '{tp.name}'")
    return tp


def _load_types_int(name: str, attrs: collections.abc.MutableMapping) -> SHVTypeInt:
    minimum = attrs.pop("minimum", None)
    if minimum is not None:
        minimum = int(minimum)
    maximum = attrs.pop("maximum", None)
    if maximum is not None:
        maximum = int(maximum)
    multiple_of = attrs.pop("multipleOf", None)
    if multiple_of is not None:
        multiple_of = int(multiple_of)
    unsigned = attrs.pop("unsigned", None)
    if unsigned is not None:
        unsigned = bool(unsigned)
    return SHVTypeInt(name, minimum, maximum, multiple_of, unsigned)


def _load_types_double(
    name: str, attrs: collections.abc.MutableMapping
) -> SHVTypeDouble:
    minimum = attrs.pop("minimum", None)
    if minimum is not None:
        minimum = float(minimum)
    exclusive_minimum = attrs.pop("exclusiveMinimum", None)
    if exclusive_minimum is not None:
        exclusive_minimum = float(exclusive_minimum)
    maximum = attrs.pop("maximum", None)
    if maximum is not None:
        maximum = float(maximum)
    exclusive_maximum = attrs.pop("exclusiveMaximum", None)
    if exclusive_maximum is not None:
        exclusive_maximum = float(exclusive_maximum)
    multiple_of = attrs.pop("multipleOf", None)
    if multiple_of is not None:
        multiple_of = float(multiple_of)
    return SHVTypeDouble(
        name, minimum, maximum, exclusive_minimum, exclusive_maximum, multiple_of
    )


def _load_types_decimal(
    name: str, attrs: collections.abc.MutableMapping
) -> SHVTypeDecimal:
    minimum = attrs.pop("minimum", None)
    if minimum is not None:
        minimum = decimal.Decimal(minimum)
    maximum = attrs.pop("maximum", None)
    if maximum is not None:
        maximum = decimal.Decimal(maximum)
    return SHVTypeDecimal(name, minimum, maximum)


def _load_types_string(
    name: str, attrs: collections.abc.MutableMapping
) -> SHVTypeString:
    min_length = attrs.pop("minLength", None)
    if min_length is not None:
        min_length = int(min_length)
    max_length = attrs.pop("maxLength", None)
    if max_length is not None:
        max_length = int(max_length)
    pattern = attrs.pop("pattern", None)
    if pattern is not None:
        pattern = str(pattern)
    return SHVTypeString(name, min_length, max_length, pattern)


def _load_types_blob(name: str, attrs: collections.abc.MutableMapping) -> SHVTypeBlob:
    length = attrs.pop("length", None)
    if length is not None:
        min_length = length
        max_length = length
    else:
        min_length = attrs.pop("minLength", None)
        if min_length is not None:
            min_length = int(min_length)
        max_length = attrs.pop("maxLength", None)
        if max_length is not None:
            max_length = int(max_length)
    return SHVTypeBlob(name, min_length, max_length)


def _load_types_enum_generic(
    obj: SHVTypeEnum, attrs: collections.abc.MutableMapping
) -> None:
    nexti = 0
    for dkey in attrs.pop("values", []):
        if isinstance(dkey, collections.abc.Mapping):
            for key, value in dkey.items():
                obj[key] = value
                nexti = value + 1
        elif isinstance(dkey, str):
            obj[dkey] = nexti
            nexti += 1
        else:
            raise ValueError(f"Invalid value specifier for enum: {dkey}")


def _load_types_enum(name: str, attrs: collections.abc.MutableMapping) -> SHVTypeEnum:
    res = SHVTypeEnum(name)
    _load_types_enum_generic(res, attrs)
    return res


def _load_types_bitfield(
    name: str, attrs: collections.abc.MutableMapping
) -> SHVTypeBitfield:
    res = SHVTypeBitfield(name)
    _load_types_enum_generic(res, attrs)
    return res


def _load_types_list_1(name: str, attrs: collections.abc.MutableMapping) -> SHVTypeList:
    attrs.pop("allowed", None)  # Loaded in second pass
    return SHVTypeList(name)


def _load_types_list_2(
    res: namedset.NamedSet[SHVTypeBase],
    obj: SHVTypeBase,
    attrs: collections.abc.Mapping,
) -> None:
    assert isinstance(obj, SHVTypeList)
    for tp in attrs.get("allowed", []):
        obj.add(_get_type(res, tp))


def _load_types_tuple_1(
    name: str, attrs: collections.abc.MutableMapping
) -> SHVTypeTuple:
    attrs.pop("fields", None)  # Loaded in second pass
    attrs.pop("enum", None)  # Loaded in second pass
    return SHVTypeTuple(name)


def _load_types_tuple_2(
    res: namedset.NamedSet[SHVTypeBase],
    obj: SHVTypeBase,
    attrs: collections.abc.Mapping,
) -> None:
    assert isinstance(obj, SHVTypeTuple)
    for tp in attrs.get("fields", []):
        obj.append(_get_type(res, tp))
    if (enum := attrs.get("enum", None)) is not None:
        obj.enum = _get_enum(res, enum)


def _load_types_map_1(name: str, attrs: collections.abc.MutableMapping) -> SHVTypeMap:
    attrs.pop("fields", None)  # Loaded in second pass
    return SHVTypeMap(name)


def _load_types_map_2(
    res: namedset.NamedSet[SHVTypeBase],
    obj: SHVTypeBase,
    attrs: collections.abc.Mapping,
) -> None:
    assert isinstance(obj, SHVTypeMap)
    obj.update(
        {key: _get_type(res, value) for key, value in attrs.get("fields", {}).items()}
    )


def _load_types_imap_1(name: str, attrs: collections.abc.MutableMapping) -> SHVTypeIMap:
    attrs.pop("fields", None)  # Loaded in second pass
    attrs.pop("enum", None)  # Loaded in second pass
    return SHVTypeIMap(name)


def _load_types_imap_2(
    res: namedset.NamedSet[SHVTypeBase],
    obj: SHVTypeBase,
    attrs: collections.abc.Mapping,
) -> None:
    assert isinstance(obj, SHVTypeIMap)
    nexti = 0
    for dkey in attrs.get("fields", []):
        if isinstance(dkey, collections.abc.Mapping):
            for key, value in dkey.items():
                obj[value] = _get_type(res, key)
                nexti = value + 1
        elif isinstance(dkey, str):
            obj[nexti] = _get_type(res, dkey)
            nexti += 1
        else:
            raise ValueError(f"Invalid fields specifier for imap: {dkey}")
    if (denum := attrs.get("enum", None)) is not None:
        obj.enum = _get_enum(res, denum)


def _load_types_constant(
    name: str, attrs: collections.abc.MutableMapping
) -> SHVTypeConstant:
    # TODO support some type conversion
    value = attrs.pop("value", None)
    if value is None:
        raise ValueError("Use shvNull instead.")
    if not shvAny.validate(value):
        raise ValueError(f"Invalid value: {value}")
    return SHVTypeConstant(name, value)


_load_types: dict[
    str, typing.Callable[[str, collections.abc.MutableMapping], SHVTypeBase]
] = {
    "Int": _load_types_int,
    "Double": _load_types_double,
    "Decimal": _load_types_decimal,
    "String": _load_types_string,
    "Blob": _load_types_blob,
    "Enum": _load_types_enum,
    "Bitfield": _load_types_bitfield,
    "List": _load_types_list_1,
    "Tuple": _load_types_tuple_1,
    "Map": _load_types_map_1,
    "IMap": _load_types_imap_1,
    "Constant": _load_types_constant,
}


_load_types_sec: dict[
    str,
    typing.Callable[
        [namedset.NamedSet[SHVTypeBase], SHVTypeBase, collections.abc.Mapping],
        None,
    ],
] = {
    "List": _load_types_list_2,
    "Tuple": _load_types_tuple_2,
    "Map": _load_types_map_2,
    "IMap": _load_types_imap_2,
}


def _load_types_invalid(name: str, attrs: collections.abc.MutableMapping):
    raise ValueError(f"Invalid 'type' of the {name} type.")


def _load_types_alias(
    res: namedset.NamedSet[SHVTypeBase], obj: SHVTypeAlias, tp: str
) -> None:
    obj.type = _get_type(res, tp)


def _load_types_oneof(
    res: namedset.NamedSet[SHVTypeBase],
    obj: SHVTypeOneOf,
    types: collections.abc.Sequence,
) -> None:
    obj.update(_get_type(res, dtype) for dtype in types)


def load_types(
    data: collections.abc.Mapping[str, typing.Any]
) -> namedset.NamedSet[SHVTypeBase]:
    """Load set of types from generic representation."""
    if not isinstance(data, collections.abc.Mapping):
        raise TypeError(f"Invalid type of 'types': {type(data)}")
    res: namedset.NamedSet[SHVTypeBase] = namedset.NamedSet()
    # To solve any inter-type dependency we do two passes
    for key, value in data.items():
        if key in shvBuiltins:
            raise RuntimeError(f"Redefining builtin types is not allowed: {key}")
        if isinstance(value, str):
            res.add(SHVTypeAlias(key))
        elif isinstance(value, collections.abc.Sequence):
            res.add(SHVTypeOneOf(key))
        elif isinstance(value, collections.abc.Mapping):
            attrs = {**value}
            tp = _load_types.get(attrs.pop("type"), _load_types_invalid)(key, attrs)
            if attrs:
                raise ValueError(f"Invalid keys for type '{key}': {attrs.keys()}")
            res.add(tp)
        else:
            raise TypeError(f"Invalid type description: {value}")
    for key, value in data.items():
        obj = res[key]
        if isinstance(value, str):
            assert isinstance(obj, SHVTypeAlias)
            _load_types_alias(res, obj, value)
        elif isinstance(value, collections.abc.Sequence):
            assert isinstance(obj, SHVTypeOneOf)
            _load_types_oneof(res, obj, value)
        elif isinstance(value, collections.abc.Mapping):
            _load_types_sec.get(value["type"], lambda *_: None)(res, obj, value)
    return res


def load_nodes(
    data: collections.abc.Mapping[str, typing.Any],
    types: namedset.NamedSet[SHVTypeBase],
) -> namedset.NamedSet[SHVNode]:
    """Load nodes set from generic representation."""
    if not isinstance(data, collections.abc.Mapping):
        raise TypeError(f"Invalid type of 'nodes': {type(data)}")

    res: namedset.NamedSet[SHVNode] = namedset.NamedSet()

    for name, dnode in data.items():
        # Note: the None here supports empty node definition
        dnode = dict(dnode) if dnode is not None else {}

        dnodes = dnode.pop("nodes", None)
        shvnodes = load_nodes(dnodes if dnodes is not None else {}, types)

        dmethods = dnode.pop("methods", None)
        shvmethods = load_methods(dmethods if dmethods is not None else {}, types)

        description = dnode.pop("description", "") or ""

        node = SHVNode(
            name, nodes=shvnodes, methods=shvmethods, description=description
        )

        # Note: pop can also return None if `Null` is used as value but Null
        # property is the same as no property for us and thus same here.
        prop = dnode.pop("property", None)
        if prop is not None:
            readonly = bool(dnode.pop("readonly", False))
            signal = bool(dnode.pop("signal", not readonly))
            shvtype = _get_type(types, prop)
            node.make_property(shvtype, readonly, signal)

        if dnode:
            keys = ", ".join(dnode.keys())
            raise ValueError(f"Unsupported keys for node '{name}': {keys}")

        res.add(node)

    return res


def load_methods(
    data: collections.abc.Mapping[str, typing.Any],
    types: namedset.NamedSet[SHVTypeBase],
) -> namedset.NamedSet[SHVMethod]:
    """Load methods from generic representation."""
    if not isinstance(data, collections.abc.Mapping):
        raise TypeError(f"Invalid type of 'methods': {type(data)}")
    res: namedset.NamedSet[SHVMethod] = namedset.NamedSet()

    for name, dmethod in data.items():
        # Note: the None here supports empty node definition
        dmethod = dict(dmethod) if dmethod is not None else {}

        args = _get_type(types, dmethod.pop("args", None))
        returns = _get_type(types, dmethod.pop("returns", None))
        access = shv.RpcMethodAccess.fromstr(dmethod.pop("access", "cmd"))
        description = dmethod.pop("description", "")

        flags = shv.RpcMethodFlags(0)
        dflags = dmethod.pop("flags", None)
        fmap = {flag.name: flag for flag in shv.RpcMethodFlags}
        for dflag in dflags if dflags is not None else []:
            dflag = dflag.upper()
            if dflag not in fmap:
                raise ValueError(f"Invalid flag for method '{name}': {dflag}")
            flags |= fmap[dflag]

        if dmethod:
            keys = ", ".join(dmethod.keys())
            raise ValueError(f"Unsupported keys for method '{name}': {keys}")

        res.add(SHVMethod(name, args, returns, flags, access, description))

    return res
