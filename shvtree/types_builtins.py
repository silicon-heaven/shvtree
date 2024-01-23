"""Definition of builtin types."""

from . import namedset
from .types import (
    SHVTypeBase,
    SHVTypeBlob,
    SHVTypeDateTime,
    SHVTypeDecimal,
    SHVTypeDouble,
    SHVTypeInt,
    SHVTypeList,
    SHVTypeOneOf,
    SHVTypeString,
    shvAny,
    shvBool,
    shvNull,
)

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
shvDouble = SHVTypeDouble("Double")
shvDecimal = SHVTypeDecimal("Decimal")
shvString = SHVTypeString("String")
shvBlob = SHVTypeBlob("Blob")
shvDateTime = SHVTypeDateTime()
shvList = SHVTypeList("List")

shvGetParam = SHVTypeOneOf("_getParam", shvNull, shvString)


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
    shvGetParam,
)
