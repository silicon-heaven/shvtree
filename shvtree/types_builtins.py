"""Definition of builtin types."""

from . import namedset
from .types import (
    SHVTypeAlias,
    SHVTypeAnyIMap,
    SHVTypeAnyMap,
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

shvInt = SHVTypeInt("Int")  # noqa N816
shvInt8 = SHVTypeInt("Int8", minimum=-(2**7), maximum=2**7 - 1)  # noqa N816
shvInt16 = SHVTypeInt("Int16", minimum=-(2**15), maximum=2**15 - 1)  # noqa N816
shvInt32 = SHVTypeInt("Int32", minimum=-(2**31), maximum=2**31 - 1)  # noqa N816
shvInt64 = SHVTypeInt("Int64", minimum=-(2**63), maximum=2**63 - 1)  # noqa N816
shvUInt = SHVTypeInt("UInt", minimum=0)  # noqa N816
shvUInt8 = SHVTypeInt("UInt8", minimum=0, maximum=2**8 - 1)  # noqa N816
shvUInt16 = SHVTypeInt("UInt16", minimum=0, maximum=2**16 - 1)  # noqa N816
shvUInt32 = SHVTypeInt("UInt32", minimum=0, maximum=2**32 - 1)  # noqa N816
shvUInt64 = SHVTypeInt("UInt64", minimum=0, maximum=2**64 - 1)  # noqa N816
shvDouble = SHVTypeDouble("Double")  # noqa N816
shvDecimal = SHVTypeDecimal("Decimal")  # noqa N816
shvString = SHVTypeString("String")  # noqa N816
shvBlob = SHVTypeBlob("Blob")  # noqa N816
shvDateTime = SHVTypeDateTime()  # noqa N816
shvList = SHVTypeList("List")  # noqa N816
shvMap = SHVTypeAnyMap()  # noqa N816
shvIMap = SHVTypeAnyIMap()  # noqa N816

shvOptionalString = SHVTypeOneOf("OptionalString", shvNull, shvString)  # noqa N816
shvGetParam = SHVTypeAlias("_getParam", shvOptionalString)  # noqa N816


shvBuiltins: namedset.NamedSet[SHVTypeBase] = namedset.NamedSet(  # noqa N816
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
    shvMap,
    shvIMap,
    shvOptionalString,
    shvGetParam,
)
