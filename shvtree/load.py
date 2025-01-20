"""Implementation of loading and validation of the SHV Tree."""

import collections
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
    SHVTypeBitfieldCompatible,
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
    if path.suffix in {".yaml", ".yml"}:
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
    return load_raw(
        json.loads(stream) if isinstance(stream, str) else json.load(stream)
    )


def load_raw(data: typing.Any) -> SHVTree:  # noqa ANN401
    """Construct SHVTree out of provided basic representation.

    :param data: SHV Tree representation in plain Python types.
    :returns: instace of SHVTree.
    """
    if not isinstance(data, collections.abc.Mapping):
        raise SHVTreeValueError([], "Invalid format")
    data = dict(data)  # copy so we can use pop

    # Load types
    shvtypes = load_types(data.pop("types", {}))

    # Load nodes
    shvnodes = load_nodes(data.pop("nodes", {}), shvtypes)

    if data:
        keys = ", ".join(data.keys())
        raise SHVTreeValueError(tuple(), f"Unsupported keys: {keys}")

    return SHVTree(types=shvtypes, nodes=shvnodes)


class _TypesLoader:
    def __init__(self, data: collections.abc.Mapping[str, typing.Any]) -> None:
        self.types: namedset.NamedSet[SHVTypeBase] = namedset.NamedSet()
        self.to_load = collections.deque(data.keys())
        self.data = data

    def load_all(self) -> namedset.NamedSet[SHVTypeBase]:
        while self.to_load:
            self.load(self.to_load.popleft())
        return self.types

    def get_type(
        self,
        location: list[str],
        name: str,
        value: typing.Any,  # noqa ANN401
    ) -> SHVTypeBase:
        # Some formats such as YAML allow None to be loaded when Null or
        # other like that strings are used. We support this and consider it
        # to be shvNull type. Otherwise we would have to use `"Null"` instead of
        # just plain `Null`.
        if value is None:
            return shvNull
        if isinstance(value, str):
            if value in shvBuiltins:
                return shvBuiltins[value]
            if value in self.types:
                return self.types[value]
            if value in self.to_load:
                self.to_load.remove(value)
                self.load(value)
                return self.types[value]
        elif isinstance(value, collections.abc.Sequence):
            oneof = SHVTypeOneOf(f"{name}OneOf")
            self.types.add(oneof)
            oneof.update(self.get_type(location, oneof.name, v) for v in value)
            return oneof
        # Note: This can also be due to the implementation error. Type loaders
        # shnould always add them self to ``self.types`` before they call this
        # method to prevent from this confusing error showing up.
        raise SHVTreeValueError(location, f"Invalid type '{value}' referenced.")

    def load(self, name: str) -> None:
        location = ["types", name]
        if name in shvBuiltins:
            raise SHVTreeValueError(location, "Redefining builtin types is not allowed")
        value = self.data[name]
        if isinstance(value, str):
            alias = SHVTypeAlias(name)
            self.types.add(alias)
            alias.type = self.get_type(location, alias.name, value)
        elif isinstance(value, collections.abc.Sequence):
            oneof = SHVTypeOneOf(name)
            self.types.add(oneof)
            oneof.update(self.get_type(location, name, v) for v in value)
        elif isinstance(value, collections.abc.Mapping):
            attrs = {**value}
            if "type" not in attrs:
                raise SHVTreeValueError(location, "Missing 'type'")
            self.loaders.get(attrs.pop("type"), type(self)._load_invalid)(
                self, location, name, attrs
            )
            if attrs:
                raise SHVTreeValueError(
                    location, f"Invalid keys: {', '.join(attrs.keys())}"
                )
        else:
            raise SHVTreeValueError(
                location, f"Invalid type description format: {value}"
            )
        assert name in self.types

    def _load_invalid(self, location: list[str], name: str, attrs: dict) -> None:  # noqa PLR6301 TODO
        raise SHVTreeValueError(location, f"Invalid type of the '{name}' type.")

    def _load_int(self, location: list[str], name: str, attrs: dict) -> None:
        minimum = attrs.pop("minimum", None)
        if minimum is not None and not isinstance(minimum, int):
            raise SHVTreeValueError([*location, "minimum"], "Expected integer")
        maximum = attrs.pop("maximum", None)
        if maximum is not None and not isinstance(maximum, int):
            raise SHVTreeValueError([*location, "maximum"], "Expected integer")
        multiple_of = attrs.pop("multipleOf", None)
        if multiple_of is not None and not isinstance(multiple_of, int):
            raise SHVTreeValueError([*location, "multiple_of"], "Expected integer")
        unsigned = attrs.pop("unsigned", None)
        if unsigned is not None and not isinstance(multiple_of, bool):
            raise SHVTreeValueError([*location, "unsigned"], "Expected bool")
        self.types.add(SHVTypeInt(name, minimum, maximum, multiple_of, unsigned))

    def _load_double(self, location: list[str], name: str, attrs: dict) -> None:
        minimum = attrs.pop("minimum", None)
        if minimum is not None and not isinstance(minimum, int | float):
            raise SHVTreeValueError([*location, "minimum"], "Expected float")
        exclusive_minimum = attrs.pop("exclusiveMinimum", None)
        if exclusive_minimum is not None and not isinstance(
            exclusive_minimum, int | float
        ):
            raise SHVTreeValueError([*location, "exclusive_minimum"], "Expected float")
        maximum = attrs.pop("maximum", None)
        if maximum is not None and not isinstance(maximum, int | float):
            raise SHVTreeValueError([*location, "maximum"], "Expected float")
        exclusive_maximum = attrs.pop("exclusiveMaximum", None)
        if exclusive_maximum is not None and not isinstance(
            exclusive_maximum, int | float
        ):
            raise SHVTreeValueError([*location, "exclusive_maximum"], "Expected float")
        multiple_of = attrs.pop("multipleOf", None)
        if multiple_of is not None and not isinstance(multiple_of, int | float):
            raise SHVTreeValueError([*location, "multiple_of"], "Expected float")
        self.types.add(
            SHVTypeDouble(
                name,
                minimum,
                maximum,
                exclusive_minimum,
                exclusive_maximum,
                multiple_of,
            )
        )

    def _load_decimal(self, location: list[str], name: str, attrs: dict) -> None:
        minimum = attrs.pop("minimum", None)
        if minimum is not None:
            if not isinstance(minimum, int | float | str):
                raise SHVTreeValueError([*location, "minimum"], "Expected decimal")
            minimum = decimal.Decimal(minimum)
        maximum = attrs.pop("maximum", None)
        if maximum is not None:
            if not isinstance(maximum, int | float | str):
                raise SHVTreeValueError([*location, "maximum"], "Expected decimal")
            maximum = decimal.Decimal(maximum)
        self.types.add(SHVTypeDecimal(name, minimum, maximum))

    def _load_string(self, location: list[str], name: str, attrs: dict) -> None:
        length = attrs.pop("length", None)
        if length is not None and not isinstance(length, int):
            raise SHVTreeValueError([*location, "length"], "Expected integer")
        min_length = attrs.pop("minLength", length)
        if min_length is not None and not isinstance(min_length, int):
            raise SHVTreeValueError([*location, "min_length"], "Expected integer")
        max_length = attrs.pop("maxLength", length)
        if max_length is not None and not isinstance(max_length, int):
            raise SHVTreeValueError([*location, "max_length"], "Expected integer")
        pattern = attrs.pop("pattern", None)
        if pattern is not None and not isinstance(pattern, str):
            raise SHVTreeValueError([*location, "pattern"], "Expected string")
        self.types.add(SHVTypeString(name, min_length, max_length, pattern))

    def _load_blob(self, location: list[str], name: str, attrs: dict) -> None:
        length = attrs.pop("length", None)
        if length is not None and not isinstance(length, int):
            raise SHVTreeValueError([*location, "length"], "Expected integer")
        min_length = attrs.pop("minLength", length)
        if min_length is not None and not isinstance(min_length, int):
            raise SHVTreeValueError([*location, "min_length"], "Expected integer")
        max_length = attrs.pop("maxLength", length)
        if max_length is not None and not isinstance(max_length, int):
            raise SHVTreeValueError([*location, "max_length"], "Expected integer")
        self.types.add(SHVTypeBlob(name, min_length, max_length))

    def _load_enum(self, location: list[str], name: str, attrs: dict) -> None:
        res = SHVTypeEnum(name)
        for dkey, i in self._load_enumlike(
            [*location, "values"], attrs.pop("values", [])
        ):
            res[dkey] = i
        self.types.add(res)

    def _load_subenum(
        self,
        location: list[str],
        name: str,
        enum: typing.Any,  # noqa ANN401
    ) -> SHVTypeEnum:
        if isinstance(enum, str):
            tp = self.get_type(location, name, enum)
            if not isinstance(tp, SHVTypeEnum):
                raise SHVTreeValueError(location, f"Type '{enum}' is not Enum")
            return tp
        res = SHVTypeEnum(f"{name}Enum")
        for dkey, i in self._load_enumlike(location, enum):
            res[dkey] = i
        self.types.add(res)
        return res

    @staticmethod
    def _load_enumlike(
        location: list[str],
        values: typing.Any,  # noqa ANN401
    ) -> collections.abc.Iterator[tuple[str, int]]:
        """Interpret value as a enum value like list.

        This includes common interpretation of integers and nulls as holes and
        thus such values are skipped.
        """
        if not isinstance(values, collections.abc.Sequence):
            raise SHVTreeValueError(location, "Invalid type, list expected.")
        nexti = 0
        for val in values:
            if val is None:
                nexti += 1
            elif isinstance(val, int):
                nexti += val
            elif isinstance(val, str):
                yield val, nexti
                nexti += 1
            elif isinstance(val, collections.abc.Mapping):
                for key, kv in val.items():
                    if not isinstance(kv, int):
                        raise SHVTreeValueError([*location, key], "Expected int!")
                    yield key, kv
                    nexti = kv + 1
            else:
                raise SHVTreeValueError(location, f"Invalid value specifier: {val!r}")

    def _load_bitfield(self, location: list[str], name: str, attrs: dict) -> None:
        res = SHVTypeBitfield(name)
        self.types.add(res)
        rtypes = attrs.pop("types", None)
        if rtypes is not None:
            for tp, i in self._load_enumlike([*location, "types"], rtypes):
                rtp = self.get_type([*location, "types"], name, tp)
                if SHVTypeBitfield.type_span(rtp) is None:
                    raise SHVTreeValueError(
                        [*location, "types"], f"Type {tp} can't be included in bitfield"
                    )
                res.set(i, typing.cast(SHVTypeBitfieldCompatible, rtp))
        if (renum := attrs.pop("enum", None)) is not None:
            enum = self._load_subenum([*location, "enum"], name, renum)
            if rtypes is None:
                res = SHVTypeBitfield.from_enum(name, enum)
                del self.types[name]
                self.types.add(res)

    def _load_list(self, location: list[str], name: str, attrs: dict) -> None:
        minlen = attrs.pop("minlen", 0)
        if not isinstance(minlen, int):
            raise SHVTreeValueError([*location, "minlen"], "Expected integer")
        maxlen = attrs.pop("maxlen", None)
        if maxlen is not None and not isinstance(maxlen, int):
            raise SHVTreeValueError([*location, "maxlen"], "Expected integer")
        res = SHVTypeList(name, minlen=minlen, maxlen=maxlen)
        self.types.add(res)

        res.allowed = self.get_type(
            [*location, "allowed"], name, attrs.pop("allowed", None)
        )

    def _load_tuple(self, location: list[str], name: str, attrs: dict) -> None:
        res = SHVTypeTuple(name)
        self.types.add(res)
        items = attrs.pop("items", [])
        if not isinstance(items, collections.abc.Sequence):
            raise SHVTreeValueError([*location, "items"], "Invalid format")
        for i, tp in enumerate(items):
            res.append(self.get_type([*location, f"items[{i}]"], f"{name}{i}", tp))
        if (enum := attrs.pop("enum", None)) is not None:
            res.enum = self._load_subenum([*location, "enum"], name, enum)

    def _load_map(self, location: list[str], name: str, attrs: dict) -> None:
        res = SHVTypeMap(name)
        self.types.add(res)
        fields = attrs.pop("fields", {})
        if not isinstance(fields, collections.abc.Mapping):
            raise SHVTreeValueError([*location, "fields"], "Expected mapping")
        for key, value in fields.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise SHVTreeValueError(
                    [*location, "fields", str(key)], "Expected string"
                )
            res[key] = self.get_type([*location, "fields"], name, value)

    def _load_imap(self, location: list[str], name: str, attrs: dict) -> None:
        res = SHVTypeIMap(name)
        self.types.add(res)
        if (enum := attrs.pop("enum", None)) is not None:
            res.enum = self._load_subenum([*location, "enum"], name, enum)
        fields = attrs.pop("fields", [])
        if isinstance(fields, collections.abc.Mapping):
            for dkey, dvalue in fields.items():
                if not isinstance(dkey, str):
                    raise SHVTreeValueError(
                        [*location, "fields"], f"Key must be string: {dkey!r}"
                    )
                res[dkey] = self.get_type(
                    [*location, "fields"], f"{name}{dkey}", dvalue
                )
        elif isinstance(fields, collections.abc.Sequence):
            nexti = 0
            for i, dkey in enumerate(fields):
                if isinstance(dkey, str):
                    res[nexti] = self.get_type(
                        [*location, "fields"], f"{name}{nexti}", dkey
                    )
                    nexti += 1
                elif isinstance(dkey, collections.abc.Mapping):
                    for key, value in dkey.items():
                        res[value] = self.get_type(
                            [*location, f"fields[{i}]", key], f"{name}{value}", key
                        )
                        nexti = value + 1
                else:
                    raise SHVTreeValueError(
                        [*location, "fields"], "Invalid fields format"
                    )
        else:
            raise SHVTreeValueError([*location, "fields"], "Invalid format")

    def _load_constant(self, location: list[str], name: str, attrs: dict) -> None:
        value = attrs.pop("value", None)
        if value is None:
            raise SHVTreeValueError([*location, "value"], "Use shvNull instead.")
        if isinstance(value, str):
            try:
                value = shv.Cpon.unpack(value)
            except (ValueError, EOFError):
                pass
        if not shvAny.validate(value):
            raise SHVTreeValueError([*location, "value"], f"Invalid value: {value}")
        self.types.add(SHVTypeConstant(name, value))

    loaders: collections.abc.Mapping[str, collections.abc.Callable] = {
        "Int": _load_int,
        "Double": _load_double,
        "Decimal": _load_decimal,
        "String": _load_string,
        "Blob": _load_blob,
        "Enum": _load_enum,
        "Bitfield": _load_bitfield,
        "List": _load_list,
        "Tuple": _load_tuple,
        "Map": _load_map,
        "IMap": _load_imap,
        "Constant": _load_constant,
    }


def load_types(
    data: typing.Any,  # noqa ANN401
) -> namedset.NamedSet[SHVTypeBase]:
    """Load set of types from generic representation."""
    if not isinstance(data, collections.abc.Mapping):
        raise SHVTreeValueError(["types"], "Invalid format")
    return _TypesLoader(data).load_all()


def _get_type(
    location: list[str], types: namedset.NamedSet[SHVTypeBase], name: str | None
) -> SHVTypeBase:
    if name is None:
        return shvNull
    if name in shvBuiltins:
        return shvBuiltins[name]
    if name not in types:
        raise SHVTreeValueError(location, f"Invalid type reference name: {name}")
    return types[name]


def load_nodes(
    data: typing.Any,  # noqa ANN401
    types: namedset.NamedSet[SHVTypeBase],
) -> namedset.NamedSet[SHVNode]:
    """Load nodes set from generic representation."""
    location = ["nodes"]
    if not isinstance(data, collections.abc.Mapping):
        raise SHVTreeValueError(location, "Invalid format")

    res: namedset.NamedSet[SHVNode] = namedset.NamedSet()

    for name, dnode in data.items():
        # Note: the None here supports empty node definition
        dnode = dict(dnode) if dnode is not None else {}  # noqa PLW2901

        dnodes = dnode.pop("nodes", None)
        shvnodes = load_nodes(dnodes if dnodes is not None else {}, types)

        dmethods = dnode.pop("methods", None)
        shvmethods = _load_methods(
            [*location, name, "methods"],
            dmethods if dmethods is not None else {},
            types,
        )

        description = dnode.pop("description", "") or ""

        node = SHVNode(
            name, nodes=shvnodes, methods=shvmethods, description=description
        )

        # Note: pop can also return None if `Null` is used as value but Null
        # property is the same as no property for us and thus same here.
        prop = dnode.pop("property", None)
        if prop is not None:
            readonly = bool(dnode.pop("readonly", False))
            if not isinstance(readonly, bool):
                raise SHVTreeValueError([*location, name, "property"], "Invalid format")
            signal = dnode.pop("signal", not readonly)
            shvtype = _get_type([*location, name, "property"], types, prop)
            node.make_property(shvtype, readonly, signal)

        if dnode:
            keys = ", ".join(dnode.keys())
            raise SHVTreeValueError([*location, name], f"Unsupported keys: {keys}")

        res.add(node)

    return res


def _load_methods(
    location: list[str],
    data: collections.abc.Mapping[str, typing.Any],
    types: namedset.NamedSet[SHVTypeBase],
) -> namedset.NamedSet[SHVMethod]:
    """Load methods from generic representation."""
    if not isinstance(data, collections.abc.Mapping):
        raise SHVTreeValueError(location, "Invalid format")
    res: namedset.NamedSet[SHVMethod] = namedset.NamedSet()

    for name, dmethod in data.items():
        # Note: the None here supports empty node definition
        dmethod = dict(dmethod) if dmethod is not None else {}  # noqa PLW2901

        param = _get_type([*location, name], types, dmethod.pop("param", None))
        result = _get_type([*location, name], types, dmethod.pop("result", None))
        access = shv.RpcMethodAccess.fromstr(dmethod.pop("access", "cmd"))
        description = dmethod.pop("description", "")

        flags = shv.RpcMethodFlags(0)
        dflags = dmethod.pop("flags", None)
        fmap = {flag.name: flag for flag in shv.RpcMethodFlags}
        for dflag in dflags if dflags is not None else []:
            dflag = dflag.upper()  # noqa PLW2901
            if dflag not in fmap:
                raise SHVTreeValueError(
                    [*location, name, "flags"],
                    f"Invalid flag: {dflag}",
                )
            flags |= fmap[dflag]

        if dmethod:
            keys = ", ".join(dmethod.keys())
            raise SHVTreeValueError([*location, name], f"Unsupported keys: {keys}")

        res.add(SHVMethod(name, param, result, flags, access, description))

    return res


class SHVTreeValueError(ValueError):
    """:class:`ValueError` raised from SHVTree loading functions."""

    def __init__(self, location: collections.abc.Sequence[str], msg: str) -> None:
        self.args = (f"{'.'.join(location)}: {msg}" if location else msg,)
