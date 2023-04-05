"""Implementation of SHV and custom types."""
from __future__ import annotations

import abc
import collections
import collections.abc
import datetime
import decimal
import re
import typing

import shv

from . import namedset


def _chainpack_bytes(value) -> int:
    """Size of the value in chainpack."""
    pack = shv.ChainPackWriter()
    pack.write(value)
    return pack.bytes_cnt


class SHVTypeBase(abc.ABC, namedset.Named):
    """The generic SHV type.

    This is base class for all SHV types.
    """

    @abc.abstractmethod
    def validate(self, value: object) -> bool:
        """Check that given value matches the described Type.

        :param value: plain Python type to be checked
        :returns: True if it matches and False otherwise
        """

    def chainpack_bytes(self) -> int | None:
        """Calculate maximum number of bytes to represent this type in Chainpack.

        :return: Number of bytes or ``None`` in case this can't be determined
          (which commonly means unbound type).
        """
        return None


class SHVTypeAny(SHVTypeBase):
    """Type that matches any valid SHV RPC type."""

    __obj = None

    def __new__(cls):
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self):
        super().__init__("Any")

    def validate(self, value: object) -> bool:
        return (
            shv.is_shvnull(value)
            or shv.is_shvbool(value)
            or isinstance(
                value, (int, float, decimal.Decimal, bytes, str, datetime.datetime)
            )
            or (isinstance(value, list) and all(self.validate(v) for v in value))
            or (
                isinstance(value, dict) and all(self.validate(v) for v in value.items())
            )
        )


shvAny = SHVTypeAny()


class SHVTypeNull(SHVTypeBase):
    """SHV Null type.

    There is always only one instance of this type.
    """

    __obj = None

    def __new__(cls):
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self):
        super().__init__("Null")

    def validate(self, value: object) -> bool:
        return shv.is_shvnull(value)

    def chainpack_bytes(self) -> int | None:
        return 1


shvNull = SHVTypeNull()


class SHVTypeBool(SHVTypeBase):
    """SHV Boolean type.

    There is always only one instance of this type.
    """

    __obj = None

    def __new__(cls):
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self):
        super().__init__("Bool")

    def validate(self, value: object) -> bool:
        return shv.is_shvbool(value)

    def chainpack_bytes(self) -> int | None:
        return 1


shvBool = SHVTypeBool()


class SHVTypeInt(SHVTypeBase):
    """SHV Integer type."""

    __obj_int = None
    __obj_uint = None

    def __new__(
        cls,
        name: str,
        minimum: decimal.Decimal | None = None,
        maximum: decimal.Decimal | None = None,
        multiple_of: decimal.Decimal | None = None,
        unsigned: bool | None = None,
    ):
        if maximum is None and multiple_of is None:
            if minimum is None:
                if name == "Int":
                    if cls.__obj_int is None:
                        cls.__obj_int = super().__new__(cls)
                    return cls.__obj_int
                raise ValueError("Please use shvInt instead")
            if minimum == 0 and unsigned is not False:
                if name == "UInt":
                    if cls.__obj_uint is None:
                        cls.__obj_uint = super().__new__(cls)
                    return cls.__obj_uint
                raise ValueError("Please use shvUInt instead")
        return super().__new__(cls)

    def __init__(
        self,
        name: str,
        minimum: int | None = None,
        maximum: int | None = None,
        multiple_of: int | None = None,
        unsigned: bool | None = None,
    ):
        super().__init__(name)
        self._minimum = minimum
        self._maximum = maximum
        self.multiple_of = multiple_of
        self._unsigned = (
            unsigned if unsigned is not None else minimum is not None and minimum >= 0
        )
        if self._unsigned and (
            self._minimum is not None
            and self._minimum < 0
            or self._maximum is not None
            and self._maximum < 0
        ):
            raise ValueError("Boundaries can't be less than zero for unsigned number")

    @property
    def minimum(self) -> int | None:
        return self._minimum

    @minimum.setter
    def minimum(self, value: int | None) -> None:
        if self._unsigned and value is not None and value < 0:
            raise ValueError("Can't be less than zero for unsigned number")
        self._maximum = value

    @property
    def maximum(self) -> int | None:
        return self._maximum

    @maximum.setter
    def maximum(self, value: int | None):
        if self._unsigned and value is not None and value < 0:
            raise ValueError("Can't be less than zero for unsigned number")
        self._maximum = value

    @property
    def unsigned(self) -> bool:
        return self._unsigned

    @unsigned.setter
    def unsigned(self, value: bool) -> None:
        if value:
            if self.minimum is not None and self.minimum < 0:
                raise ValueError("Minimum can't be negative number")
            if self.maximum is not None and self.maximum < 0:
                raise ValueError("Maximum can't be negative number")
        self._unsigned = value

    def validate(self, value: object) -> bool:
        return (
            isinstance(value, int)
            and (self._minimum is None or self._minimum <= value)
            and (self._maximum is None or self._maximum >= value)
            and (self.multiple_of is None or value % self.multiple_of == 0)
        )

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, SHVTypeInt)
            and value.minimum == self._minimum
            and value.maximum == self._maximum
            and value.multiple_of == self.multiple_of
        )

    def bytes_size(self) -> int | None:
        """Number of bytes to be used to cover whole range."""
        if (
            self._maximum is None
            or self._minimum is None
            or self._maximum == self._minimum
        ):
            return None
        return ((abs(self._maximum - self._minimum).bit_length() - 1) // 8) + 1

    def chainpack_bytes(self) -> int | None:
        if self._minimum is not None and self._maximum is not None:
            if self._minimum >= 0 and self._maximum < 64:
                return 1  # packed in schema
            bits = max(abs(self._minimum), abs(self._maximum)).bit_length() - 1
            if not self._unsigned:
                bits += 1  # sign bit
            if bits <= 7:
                return 2
            if bits <= 14:
                return 3
            if bits <= 21:
                return 4
            if bits <= 28:
                return 5
            bts = (bits // 8) + 1
            if bts <= 17:
                return 2 + bts
        return None


shvInt = SHVTypeInt("Int")
shvInt8 = SHVTypeInt("Int8", minimum=-(2**7), maximum=2**7 - 1)
shvInt16 = SHVTypeInt("Int16", minimum=-(2**15), maximum=2**15 - 1)
shvInt32 = SHVTypeInt("Int32", minimum=-(2**31), maximum=2**31 - 1)
shvInt64 = SHVTypeInt("Int64", minimum=-(2**63), maximum=2**63 - 1)
shvUInt = SHVTypeInt("UInt", minimum=0)
shvUInt8 = SHVTypeInt("UInt8", minimum=0, maximum=2**8 - 1)
shvUInt16 = SHVTypeInt("UInt16", minimum=0, maximum=2**16 - 1)
shvUInt32 = SHVTypeInt("UInt32", minimum=0, maximum=2**32 - 1)
shvUInt64 = SHVTypeInt("UInt64", minimum=0, maximum=2**64 - 1)


class SHVTypeDouble(SHVTypeBase):
    """SHV Double type."""

    __obj = None

    def __new__(
        cls,
        name: str,
        minimum: decimal.Decimal | None = None,
        maximum: decimal.Decimal | None = None,
        exclusive_minimum: decimal.Decimal | None = None,
        exclusive_maximum: decimal.Decimal | None = None,
        multiple_of: decimal.Decimal | None = None,
    ):
        if (
            minimum is None
            and maximum is None
            and exclusive_minimum is None
            and exclusive_maximum is None
            and multiple_of is None
        ):
            if name == "Double":
                if cls.__obj is None:
                    cls.__obj = super().__new__(cls)
                return cls.__obj
            raise ValueError("Please use shvDouble instead")
        return super().__new__(cls)

    def __init__(
        self,
        name: str,
        minimum: float | None = None,
        maximum: float | None = None,
        exclusive_minimum: float | None = None,
        exclusive_maximum: float | None = None,
        multiple_of: float | None = None,
    ):
        super().__init__(name)
        self.minimum = minimum
        self.maximum = maximum
        self.exclusive_minimum = exclusive_minimum
        self.exclusive_maximum = exclusive_maximum
        self.multiple_of = multiple_of

    def validate(self, value: object) -> bool:
        return (
            isinstance(value, float)
            and (self.minimum is None or self.minimum <= value)
            and (self.maximum is None or self.maximum >= value)
            and (self.exclusive_minimum is None or self.exclusive_minimum < value)
            and (self.exclusive_maximum is None or self.exclusive_maximum > value)
            and (self.multiple_of is None or value % self.multiple_of == 0)
        )

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, SHVTypeDouble)
            and value.minimum == self.minimum
            and value.maximum == self.maximum
            and value.exclusive_minimum == self.exclusive_minimum
            and value.exclusive_maximum == self.exclusive_maximum
            and value.multiple_of == self.multiple_of
        )

    def chainpack_bytes(self) -> int | None:
        return 65


shvDouble = SHVTypeDouble("Double")


class SHVTypeDecimal(SHVTypeBase):
    """SHV Decimal type."""

    __obj = None

    def __new__(
        cls,
        name: str,
        minimum: decimal.Decimal | None = None,
        maximum: decimal.Decimal | None = None,
    ):
        if minimum is None and maximum is None:
            if name == "Decimal":
                if cls.__obj is None:
                    cls.__obj = super().__new__(cls)
                return cls.__obj
            raise ValueError("Please use shvDecimal instead")
        return super().__new__(cls)

    def __init__(
        self,
        name: str,
        minimum: decimal.Decimal | None = None,
        maximum: decimal.Decimal | None = None,
    ):
        super().__init__(name)
        self.minimum = minimum
        self.maximum = maximum

    def validate(self, value: object) -> bool:
        return (
            isinstance(value, decimal.Decimal)
            and (self.minimum is None or self.minimum <= value)
            and (self.maximum is None or self.maximum >= value)
        )

    def mantisa(self) -> SHVTypeInt:
        """Deduce type for mantisa of this decimal type."""
        minimum = None
        if self.minimum is not None:
            decmin = self.minimum.as_tuple()
            # TODO
        maximum = None
        if self.maximum is not None:
            decmax = self.maximum.as_tuple()
            # TODO
        return SHVTypeInt(self.name + "-mantisa", minimum, maximum)

    def exponent(self) -> SHVTypeInt:
        """Deduce type for exponent of this decimal type."""
        minimum = None if self.minimum is None else self.minimum.as_tuple().exponent
        if not isinstance(minimum, int):
            minimum = None
        maximum = None if self.maximum is None else self.maximum.as_tuple().exponent
        if not isinstance(maximum, int):
            maximum = None
        return SHVTypeInt(self.name + "-exponent", minimum, maximum)

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, SHVTypeDecimal)
            and value.minimum == self.minimum
            and value.maximum == self.maximum
        )

    def chainpack_bytes(self) -> int | None:
        mantisa = self.mantisa().chainpack_bytes()
        exponent = self.exponent().chainpack_bytes()
        if mantisa is not None and exponent is not None:
            return 1 + mantisa + exponent
        return None


shvDecimal = SHVTypeDecimal("Decimal")


class SHVTypeString(SHVTypeBase):
    """SHV String type."""

    __obj = None

    def __new__(
        cls,
        name: str,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
    ):
        if min_length is None and max_length is None and pattern is None:
            if name == "String":
                if cls.__obj is None:
                    cls.__obj = super().__new__(cls)
                return cls.__obj
            raise ValueError("Please use shvString instead")
        return super().__new__(cls)

    def __init__(
        self,
        name: str,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
    ):
        super().__init__(name)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        if self.pattern is not None:
            self._pattern = re.compile(self.pattern)

    def validate(self, value: object) -> bool:
        return (
            isinstance(value, str)
            and (self.min_length is None or len(value) >= self.min_length)
            and (self.max_length is None or len(value) <= self.max_length)
            and (self.pattern is None or self._pattern.match(value) is not None)
        )

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, SHVTypeString)
            and value.min_length == self.min_length
            and value.max_length == self.max_length
            and value.pattern == self.pattern
        )

    def length(self) -> SHVTypeInt:
        return SHVTypeInt(
            self.name + "-length", minimum=self.min_length, maximum=self.max_length
        )

    def chainpack_bytes(self) -> int | None:
        # Note: we do not investigate pattern so we consider only maximum length
        # to calculate required bytes.
        length = self.length().chainpack_bytes()
        if length is not None:
            assert self.max_length is not None  # couldn't calculate length otherwise
            return 1 + length + self.max_length
        return None


shvString = SHVTypeString("String")


class SHVTypeBlob(SHVTypeBase):
    """SHV Blob type."""

    __obj = None

    def __new__(
        cls,
        name: str,
        min_length: int | None = None,
        max_length: int | None = None,
    ):
        if min_length is None and max_length is None:
            if name == "Blob":
                if cls.__obj is None:
                    cls.__obj = super().__new__(cls)
                return cls.__obj
            raise ValueError("Please use shvBlob instead")
        return super().__new__(cls)

    def __init__(
        self,
        name: str,
        min_length: int | None = None,
        max_length: int | None = None,
    ):
        super().__init__(name)
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: object) -> bool:
        return (
            isinstance(value, (bytes, bytearray))
            and (self.min_length is None or len(value) >= self.min_length)
            and (self.max_length is None or len(value) <= self.max_length)
        )

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, SHVTypeString)
            and value.min_length == self.min_length
            and value.max_length == self.max_length
        )

    def length(self) -> SHVTypeInt:
        return SHVTypeInt(
            self.name + "-length", minimum=self.min_length, maximum=self.max_length
        )

    def chainpack_bytes(self) -> int | None:
        length = self.length().chainpack_bytes()
        if length is not None:
            assert self.max_length is not None  # couldn't calculate length otherwise
            return 1 + length + self.max_length
        return None


shvBlob = SHVTypeBlob("Blob")


class SHVTypeDateTime(SHVTypeBase):
    """SHV date and time type."""

    __obj = None

    def __new__(cls):
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self):
        super().__init__("DateTime")

    def validate(self, value: object) -> bool:
        return isinstance(value, datetime.datetime)

    def chainpack_bytes(self) -> int | None:
        # signed 62 bit int and one byte for schema
        return 9


shvDateTime = SHVTypeDateTime()


class SHVTypeEnum(SHVTypeBase, dict[str, int]):
    """The type based on unsigned integer that has only predefined values.

    It is mapping of string keys to numeric representation. Note that it is
    allowed to have multiple names for the same number to support aliases.
    """

    def __init__(self, name: str, *values: str, **kvalues: int):
        """Initialize new Enum type.

        :param name: Name of the new type.
        :param values: Position arguments have to be strings and they get
            assigned values from 0 onward.
        :param kvalues: Keyword arguments allow you to set custom numeric value
        for the specific values.
        """
        super().__init__(name)
        self.update({value: i for i, value in enumerate(values)})
        self.update(kvalues)

    def validate(self, value: object) -> bool:
        if isinstance(value, str):
            return value in self.keys()
        if isinstance(value, int):
            return value in self.values()
        return False

    def integer(self) -> SHVTypeInt:
        """Integer representing this enum."""
        return SHVTypeInt(self.name + "-integer", 0, max(self.values()))

    def chainpack_bytes(self) -> int | None:
        return self.integer().chainpack_bytes()


class SHVTypeBitfield(SHVTypeEnum):
    """Type that combines multiple boolean values to one integer.

    The type is based on Enum and transmitted using builtin usigned integer.

    The intended usage of this type is to pass multiple booleans at once with
    little overhead.
    """

    def validate(self, value: object) -> bool:
        if not isinstance(value, int):
            return False
        i = 0
        while value:
            if (value >> i) & 0x1:
                if i not in self.values():
                    return False
                value -= 0x1 << i
            i += 1
        return True


class SHVTypeList(SHVTypeBase, collections.abc.MutableSet[SHVTypeBase]):
    """The native SHV type that contains ordered values."""

    def __init__(self, name: str, *types: SHVTypeBase):
        """Initialize new List type.

        :param name: Name of the new type.
        :param types: Allowed types in the list.
        """
        super().__init__(name)
        self._types: list[SHVTypeBase] = []
        self.update(types)

    def __contains__(self, value: object) -> bool:
        return value in self._types

    def __iter__(self):
        return iter(self._types)

    def __len__(self):
        return len(self._types)

    def add(self, value: SHVTypeBase):
        if value is shvAny:
            raise ValueError("To specify list with shvAny please use shvList")
        self._types.append(value)

    def discard(self, value: SHVTypeBase):
        self._types.remove(value)

    def update(self, values: typing.Iterable[SHVTypeBase]):
        for value in values:
            self.add(value)

    def validate(self, value: object) -> bool:
        return isinstance(value, collections.abc.Sequence) and all(
            any(tp.validate(item) for tp in self._types) for item in value
        )


class SHVTypeListAny(SHVTypeList):
    """The native SHV type that can contain any other types."""

    __obj = None

    def __new__(cls):
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self):
        super().__init__("List")
        self._types.append(shvAny)

    def add(self, value: object):
        raise RuntimeError("Modification disabled for shvList")

    def discard(self, value: object):
        raise RuntimeError("Modification disabled for shvList")


shvList = SHVTypeListAny()


class SHVTypeTuple(SHVTypeBase, list[SHVTypeBase]):
    """The List type that expects specific types on specific indexes.

    Compared with Enum or IMap the empty indexes are not allowed here. You can
    use Enum to assign aliases to the indexes.
    """

    def __init__(
        self, name: str, *fields: SHVTypeBase, enum: None | SHVTypeEnum = None
    ):
        """Initialize new Tuple type.

        :param fields: Keywords declaring name and type of the field in the
            tuple.
        :param enum: Enum used to assign aliases to the fields in the tuple.
        """
        super().__init__(name)
        self.extend(fields)
        self.enum: SHVTypeEnum | None = enum

    def __eq__(self, other: object):
        return (
            hasattr(other, "enum") and other.enum == self.enum and super().__eq__(other)
        )

    # TODO allow access trough enum names

    def validate(self, value: object) -> bool:
        return isinstance(value, collections.abc.Sequence) and all(
            i < len(self) and self[i].validate(item) for i, item in enumerate(value)
        )

    def chainpack_bytes(self) -> int | None:
        res = 2
        for tp in self:
            tpsize = tp.chainpack_bytes()
            if tpsize is None:
                return None
            res += tpsize
        return res


class SHVTypeMap(SHVTypeBase, dict[str, SHVTypeBase]):
    """The native SHV type where there is value assigned per string key."""

    def __init__(self, name: str, **fields: SHVTypeBase):
        """Initialize new List type.

        :param name: Name of the new type.
        :param types: Allowed types in the list.
        """
        super().__init__(name)
        self.update(fields)

    def validate(self, value: object) -> bool:
        return isinstance(value, collections.abc.Mapping) and all(
            key in self and self[key].validate(item) for key, item in value.items()
        )

    # TODO implement chainpack_bytes


class SHVTypeIMap(SHVTypeBase, collections.abc.MutableMapping[int | str, SHVTypeBase]):
    """The native SHV type where keys are integers.

    It is possible to assign with :class:`SHVTypeEnum`.
    """

    def __init__(
        self, name: str, *fields: SHVTypeBase, enum: SHVTypeEnum | None = None
    ):
        """Initialize new List type.

        :param name: Name of the new type.
        :param types: Allowed types in the list.
        """
        super().__init__(name)
        self._fields: dict[int, SHVTypeBase] = dict(enumerate(fields))
        self.enum = enum

    def __getitem__(self, key: int | str) -> SHVTypeBase:
        if isinstance(key, str):
            if self.enum is None:
                raise KeyError("Can't use name unless you set enum attribute.")
            key = self.enum[key]
        return self._fields[key]

    def __setitem__(self, key: int | str, value: SHVTypeBase):
        if not isinstance(key, int):
            raise KeyError("Only integer key types can be assigned")
        self._fields[key] = value

    def __delitem__(self, key: int | str):
        if isinstance(key, str):
            if self.enum is None:
                raise KeyError("Can't use name unless you set enum attribute.")
            key = self.enum[key]
        del self._fields[key]

    def __iter__(self):
        return iter(self._fields)

    def __len__(self):
        return len(self._fields)

    def validate(self, value: object) -> bool:
        if not isinstance(value, collections.abc.Mapping):
            return False
        for key, item in value.items():
            if self.enum is not None and key in self.enum:
                key = self.enum[key]
            if key not in self._fields or not self._fields[key].validate(item):
                return False
        return True

    def chainpack_bytes(self) -> int | None:
        # TODO
        return None


class SHVTypeAlias(SHVTypeBase):
    """Type that provide a way to name type with multiple names."""

    def __init__(self, name: str, shvtp: SHVTypeBase = shvNull):
        """Initialize new combination of types and name it as such."""
        super().__init__(name)
        self.type = shvtp

    def __eq__(self, other: object) -> bool:
        return self.type == other or (
            isinstance(other, SHVTypeAlias) and self.type == other.type
        )

    def validate(self, value: object) -> bool:
        return self.type.validate(value)

    def chainpack_bytes(self) -> int | None:
        return self.type.chainpack_bytes()


class SHVTypeOneOf(SHVTypeBase, collections.abc.MutableSet[SHVTypeBase]):
    """Type that allows one of the selected types to be returned."""

    def __init__(self, name: str, *types: SHVTypeBase):
        """Initialize new combination of types and name it as such.

        :param name: Name of the new type.
        :param types: Allowed types to be used when this type is used.
        """
        super().__init__(name)
        self._types: list[SHVTypeBase] = []
        self.update(types)

    def __contains__(self, value: object) -> bool:
        return value in self._types

    def __iter__(self):
        return iter(self._types)

    def __len__(self):
        return len(self._types)

    def add(self, value: object):
        if not isinstance(value, SHVTypeBase):
            raise TypeError("Only instances of SHVTypeBase can be included")
        self._types.append(value)

    def discard(self, value: object):
        if not isinstance(value, SHVTypeBase):
            raise TypeError("Only instances of SHVTypeBase can be included")
        self._types.remove(value)

    def update(self, values: typing.Iterable[SHVTypeBase]):
        for value in values:
            self.add(value)

    def validate(self, value: object) -> bool:
        return any(tp.validate(value) for tp in self)

    def chainpack_bytes(self) -> int | None:
        res = -1
        for tp in self._types:
            size = tp.chainpack_bytes()
            if size is None:
                return None
            res = max(res, size)
        if res < 0:
            return None
        return res


class SHVTypeConstant(SHVTypeBase):
    """Type that allows you to specify expected constant."""

    def __init__(self, name: str, value: shv.SHVType = None):
        """Initialize new constant type.

        :param name: Name of the new constant.
        :param value: Value for the constant.
        """
        super().__init__(name)
        self.value: shv.SHVType = value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SHVTypeConstant) and self.value == other.value

    def validate(self, value: object) -> bool:
        return value == self.value

    def chainpack_bytes(self) -> int | None:
        return _chainpack_bytes(self.value)


shvBuiltins: namedset.NamedSet[SHVTypeBase] = namedset.NamedSet(
    shvAny,
    shvNull,
    shvBool,
    shvInt,
    shvInt8,
    shvInt16,
    shvInt32,
    shvInt64,
    shvUInt,
    shvUInt8,
    shvUInt16,
    shvUInt32,
    shvUInt64,
    shvDouble,
    shvDecimal,
    shvString,
    shvBlob,
    shvDateTime,
    shvList,
)
