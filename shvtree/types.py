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


def _chainpack_bytes(value: shv.SHVType) -> int:
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

    def __new__(cls) -> "SHVTypeAny":
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self) -> None:
        super().__init__("Any")

    def validate(self, value: object) -> bool:
        return (
            shv.is_shvnull(value)
            or shv.is_shvbool(value)
            or isinstance(
                value, (int, float, decimal.Decimal, bytes, str, datetime.datetime)
            )
            or (
                isinstance(value, collections.abc.Sequence)
                and all(self.validate(v) for v in value)
            )
            or (
                isinstance(value, collections.abc.Mapping)
                and (
                    all(isinstance(k, int) for k in value)
                    or all(isinstance(k, str) for k in value)
                )
                and all(self.validate(v) for v in value.values())
            )
        )


shvAny = SHVTypeAny()  # Must be defined here for reuse not in types_builtins.py


class SHVTypeAlias(SHVTypeBase):
    """Type that provide a way to name type with multiple names."""

    def __init__(self, name: str, shvtp: SHVTypeBase = shvAny):
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

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SHVTypeOneOf) and self._types == other._types

    def __contains__(self, value: object) -> bool:
        return value in self._types

    def __iter__(self) -> typing.Iterator[SHVTypeBase]:
        return iter(self._types)

    def __len__(self) -> int:
        return len(self._types)

    def add(self, value: object) -> None:
        if not isinstance(value, SHVTypeBase):
            raise TypeError("Only instances of SHVTypeBase can be included")
        self._types.append(value)

    def discard(self, value: object) -> None:
        if not isinstance(value, SHVTypeBase):
            raise TypeError("Only instances of SHVTypeBase can be included")
        self._types.remove(value)

    def update(self, values: typing.Iterable[SHVTypeBase]) -> None:
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


class SHVTypeNull(SHVTypeBase):
    """SHV Null type.

    There is always only one instance of this type.
    """

    __obj = None

    def __new__(cls) -> "SHVTypeNull":
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self) -> None:
        super().__init__("Null")

    def validate(self, value: object) -> bool:
        return shv.is_shvnull(value)

    def chainpack_bytes(self) -> int | None:
        return 1


shvNull = SHVTypeNull()  # Must be defined here for reuse not in types_builtins.py


class SHVTypeBool(SHVTypeBase):
    """SHV Boolean type.

    There is always only one instance of this type.
    """

    __obj = None

    def __new__(cls) -> "SHVTypeBool":
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self) -> None:
        super().__init__("Bool")

    def validate(self, value: object) -> bool:
        return shv.is_shvbool(value)

    def chainpack_bytes(self) -> int | None:
        return 1


shvBool = SHVTypeBool()  # Must be defined here for reuse not in types_builtins.py


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
    ) -> "SHVTypeInt":
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
    ) -> None:
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
    def maximum(self, value: int | None) -> None:
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
    ) -> "SHVTypeDouble":
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
    ) -> None:
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


class SHVTypeDecimal(SHVTypeBase):
    """SHV Decimal type."""

    __obj = None

    def __new__(
        cls,
        name: str,
        minimum: decimal.Decimal | None = None,
        maximum: decimal.Decimal | None = None,
    ) -> "SHVTypeDecimal":
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
    ) -> None:
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


class SHVTypeString(SHVTypeBase):
    """SHV String type."""

    __obj = None

    def __new__(
        cls,
        name: str,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
    ) -> "SHVTypeString":
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
    ) -> None:
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


class SHVTypeBlob(SHVTypeBase):
    """SHV Blob type."""

    __obj = None

    def __new__(
        cls,
        name: str,
        min_length: int | None = None,
        max_length: int | None = None,
    ) -> "SHVTypeBlob":
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
    ) -> None:
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


class SHVTypeDateTime(SHVTypeBase):
    """SHV date and time type."""

    __obj = None

    def __new__(cls) -> "SHVTypeDateTime":
        if cls.__obj is None:
            cls.__obj = object.__new__(cls)
        return cls.__obj

    def __init__(self) -> None:
        super().__init__("DateTime")

    def validate(self, value: object) -> bool:
        return isinstance(value, datetime.datetime)

    def chainpack_bytes(self) -> int | None:
        # signed 62 bit int and one byte for schema
        return 9


class SHVTypeEnum(SHVTypeBase, dict[str, int]):
    """The type based on unsigned integer that has only predefined values.

    It is mapping of string keys to numeric representation. Note that it is
    allowed to have multiple names for the same number to support aliases.
    """

    def __init__(self, name: str, *values: str, **kvalues: int) -> None:
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


SHVTypeBitfieldCompatible = SHVTypeNull | SHVTypeBool | SHVTypeEnum | SHVTypeInt
SHVBitfieldCompatible = None | bool | int


class SHVTypeBitfield(SHVTypeBase, list[SHVTypeBitfieldCompatible]):
    """Type that combines multiple integer based values to one integer.

    The value is transmitted using usigned integer.

    This type is pretty close to the :class:`SHVTypeTuple` with exception that
    it allows only limited types and that integer is more compact way to
    transmit data over list.

    The suggested but not enforced maximum size of the Bitfield is 64 bits. SHV
    can potentially work even with bigger values but working with them is harder
    on multiple platforms and for bigger values you should rather split it to
    multiple bitfields.
    """

    def __init__(
        self,
        name: str,
        *items: SHVTypeBitfieldCompatible,
        enum: None | SHVTypeEnum = None,
        strict: bool = True,
    ) -> None:
        """Initialize new Bitfield type.

        :param fields: Declaration of types of the field in the tuple. You can
          use :param:`shvNull` to insert holes (one null for one bit).
        :param enum: Enum used to assign aliases to the bits. Note that this
          does not directly map to field but rather to their indexes.
        :param strict: Interpret ``shvNull`` and upper bits as "must be zero"
          instead of ignoring such bits.
        """
        super().__init__(name)
        self.extend(items)
        self.enum: SHVTypeEnum | None = enum
        self.strict: bool = strict

    def __eq__(self, other: object) -> bool:
        return (
            hasattr(other, "enum") and other.enum == self.enum and super().__eq__(other)
        )

    def types(
        self,
    ) -> collections.abc.Iterator[tuple[SHVTypeBitfieldCompatible, int, int]]:
        """Iterate over types with their start bit and bit size.

        This skips Nulls because they are considered as holes in bitfield.

        :return: Iterator over all types in bitfield. Every type is yielded as
          tuple of the type, starting bit and bit span of the type.
        """
        i = 0
        for tp in self:
            if tp is shvNull:
                i += 1
                continue
            siz = self.type_span(tp)
            assert siz is not None
            yield tp, i, siz
            i += siz

    def get(self, bit: int | str) -> SHVTypeBitfieldCompatible:
        """Get type that starts on given bit in the bitfield.

        :param bit: Bit index (where 0 is the first bit) or alias from enum.
        :return: Type on the given bit.
        :raise ValueError: if there is no type starting on that bit.
        :raise KeyError: in case ``bit`` is string that is not in enum.
        """
        if isinstance(bit, str):
            if self.enum is None:
                raise KeyError("No enum provided")
            bit = self.enum[bit]
        for tp, pos, _ in self.types():
            if pos == bit:
                return tp
            if pos > bit:
                break
        raise ValueError(f"No type starts on bit {bit}")

    def set(self, bit: int | str, value: SHVTypeBitfieldCompatible) -> None:
        """Insert type to start at given bit.

        This will fail if there is overlap with existing type that is not
        ``shvNull``.

        :param bit: Bit index (where 0 is the first bit) or alias from enum.
        :param value: Type to be inserted to that type.
        :raise ValueError: if this would replace or overlap some other existing
          type.
        """
        if isinstance(bit, str):
            if self.enum is None:
                raise KeyError("No enum provided")
            bit = self.enum[bit]
        valsiz = self.type_span(value)
        if valsiz is None:
            raise ValueError(f"Type {valsiz!r} can't be included in bitfield.")
        old = list(self)
        self.clear()
        offset = 0
        for item in old:
            if offset == bit:
                if item is not shvNull:
                    raise ValueError("Replacement is not allowed")
                self.append(value)
            elif bit < offset < (bit + valsiz):
                if item is not shvNull:
                    raise ValueError("Replacement is not allowed")
            else:
                self.append(item)
            offset += self.type_span(item) or 0
        if offset <= bit:
            self.extend([shvNull] * (bit - offset))
            self.append(value)

    def bitsize(self) -> int:
        """Calculate number of bits needed for this bitfield.

        :result: Number of bits.
        """
        return sum(self.type_span(tp) or 0 for tp in self)

    def validate(self, value: object) -> bool:
        if not isinstance(value, int):
            return False
        try:
            self.interpret(value)
        except ValueError:
            return False
        return True

    def interpret(
        self,
        value: int,
    ) -> collections.abc.Sequence[SHVBitfieldCompatible]:
        """Interpret the given integer value by this bitfield.

        :param value: Integer to be interpreted.
        :return: List of values interpreted from integer based on this type.
        """
        res: list[SHVBitfieldCompatible] = []
        pos = siz = 0
        for tp, pos, siz in self.types():
            v = (value >> pos) & (2**siz - 1)
            value &= ~((2**siz - 1) << pos)
            assert tp is not shvNull
            if tp is shvBool:
                res.append(v != 0)
            elif isinstance(tp, SHVTypeEnum):
                if not tp.validate(v):
                    raise ValueError(
                        f"Bits from {pos} to {pos + siz} doesn't match enum values"
                    )
                res.append(v)
            elif isinstance(tp, SHVTypeInt):
                if not tp.validate(v):
                    raise ValueError(
                        f"Bits from {pos} to {pos + siz} doesn't match integer limits"
                        + " required by the type"
                    )
                res.append(v)
            else:
                raise ValueError(f"Can't interpret type: {tp!r}")
        if self.strict and value != 0:
            raise ValueError(f"These unsued bits were set: {bin(value)}")
        return res

    @staticmethod
    def type_span(tp: SHVTypeBase) -> int | None:
        """Calculate the bits span needed for this type.

        :return: Number of bits needed to carry this type in bitfield or
          ``None`` if that is not supported for this type.
        """
        if tp in (shvNull, shvBool):
            return 1
        if isinstance(tp, SHVTypeEnum):
            tp = tp.integer()
        if isinstance(tp, SHVTypeInt):
            if tp.unsigned and tp.maximum is not None:
                return tp.maximum.bit_length()
        return None

    @classmethod
    def from_enum(cls, name: str, enum: SHVTypeEnum) -> typing.Self:
        """Generate bitfield from given enum.

        It is common to create bitfields just with booleans and in such case the
        regular initialization can get pretty complex for not reason. This
        simplifies this use case and allows instead bitfield to be generated
        directly from enum.

        :param name: Name of the new bitfield type.
        :param enum: The enum bitfield should be generated for.
        :return: New bitfield type.
        """
        res = cls(name, enum=enum)
        for i in set(enum.values()):
            res.set(i, shvBool)
        return res


class SHVTypeList(SHVTypeBase):
    """The native SHV type that contains ordered values."""

    __anylist: SHVTypeList | None = None

    def __new__(
        cls,
        name: str,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> SHVTypeList:
        if name == "List":
            if cls.__anylist is None:
                cls.__anylist = object.__new__(cls)
            return cls.__anylist
        return object.__new__(cls)

    def __init__(
        self,
        name: str,
        allowed: SHVTypeBase = shvAny,
        minlen: int = 0,
        maxlen: int | None = None,
    ):
        """Initialize new List type.

        :param name: Name of the new type.
        :param allowed: Allowed type in the list.
        """
        super().__init__(name)
        self._types: list[SHVTypeBase] = []
        self._allowed: SHVTypeBase
        self.allowed = allowed
        self.minlen: int = minlen
        self.maxlen: int | None = maxlen

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SHVTypeList)
            and other.allowed == self.allowed
            and other.minlen == self.minlen
            and other.maxlen == self.maxlen
        )

    @property
    def allowed(self) -> SHVTypeBase:
        """The type that is allowed to be in the list.

        You can use :class:`SHVTypeOneOf` if you want to allow multiple types.
        """
        return self._allowed

    @allowed.setter
    def allowed(self, value: SHVTypeBase) -> None:
        """Set and validate the allowed type."""
        if self.name == "List" and value is not shvAny:
            raise ValueError("List type can't be modified")
        self._allowed = value

    def validate(self, value: object) -> bool:
        return (
            isinstance(value, collections.abc.Sequence)
            and self.minlen <= len(value)
            and (self.maxlen is None or len(value) <= self.maxlen)
            and all(self.allowed.validate(item) for item in value)
        )


class SHVTypeTuple(SHVTypeBase, list[SHVTypeBase]):
    """The List type that expects specific types on specific indexes.

    Tuples are always at most of the given size. The only exception are tuples
    with *Null*s at the end of list. Such nulls can be left out.  This type
    doesn't allow holes but you can use *Null* as a hole.

    You can use Enum to assign aliases to the indexes.
    """

    def __init__(
        self, name: str, *items: SHVTypeBase, enum: None | SHVTypeEnum = None
    ) -> None:
        """Initialize new Tuple type.

        :param items: Declaration of types of the field in the tuple.
        :param enum: Enum used to assign aliases to the fields in the tuple.
        """
        super().__init__(name)
        self.extend(items)
        self.enum: SHVTypeEnum | None = enum

    def __eq__(self, other: object) -> bool:
        return (
            hasattr(other, "enum") and other.enum == self.enum and super().__eq__(other)
        )

    # TODO allow access through enum names

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
        self,
        name: str,
        *fields: SHVTypeBase,
        enum: SHVTypeEnum | None = None,
        **kwfields: SHVTypeBase,
    ):
        """Initialize new List type.

        :param name: Name of the new type.
        :param enum: Optional mapping for index fields to string keys.
        """
        super().__init__(name)
        self.enum = enum
        self._fields: dict[int, SHVTypeBase] = dict(enumerate(fields))
        for key, value in kwfields.items():
            self.__setitem__(key, value)

    def __getitem__(self, key: int | str) -> SHVTypeBase:
        if isinstance(key, str):
            if self.enum is None:
                raise KeyError("Can't use name unless you set enum attribute.")
            key = self.enum[key]
        return self._fields[key]

    def __setitem__(self, key: int | str, value: SHVTypeBase) -> None:
        if isinstance(key, str):
            if self.enum is None:
                raise KeyError("Can't use name unless you set enum attribute.")
            key = self.enum[key]
        self._fields[key] = value

    def __delitem__(self, key: int | str) -> None:
        if isinstance(key, str):
            if self.enum is None:
                raise KeyError("Can't use name unless you set enum attribute.")
            key = self.enum[key]
        del self._fields[key]

    def __iter__(self) -> typing.Iterator[int]:
        return iter(self._fields)

    def __len__(self) -> int:
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
