"""The implementation that creates dummy device out of any tree."""
# pylint: disable=C0103
import collections.abc
import datetime
import importlib.metadata
import logging
import random
import string
import typing

import shv

from .. import (
    SHVMethod,
    SHVTypeAlias,
    SHVTypeBase,
    SHVTypeBitfield,
    SHVTypeBlob,
    SHVTypeConstant,
    SHVTypeDateTime,
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
    shvIMap,
    shvInt,
    shvMap,
    shvNull,
    shvString,
    shvUInt,
)
from .device import SHVTreeDevice

logger = logging.getLogger(__name__)


class SHVTreeDummyDevice(SHVTreeDevice):
    """The dummy device that overrides not-implemented error based on requested type."""

    APP_NAME = "pyshvtree-dummy"
    try:
        APP_VERSION = importlib.metadata.version("pyshvtree")
    except importlib.metadata.PackageNotFoundError:
        APP_VERSION = "unknown"

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.dummy_time_offset: datetime.timedelta = datetime.timedelta()
        """Offset to the current time that is added to the current date and time."""

    def _get_method_impl(self, args: dict[str, typing.Any]) -> typing.Callable | None:
        res = super()._get_method_impl(args)
        if res is None and args.get("method", None) is not None:
            return self._default_method
        return res

    def _default_method(self, method: SHVMethod) -> shv.SHVType:
        return self._dummy_value(method.result)

    @classmethod
    def _dummy_value(cls, shvtp: SHVTypeBase) -> shv.SHVType:
        # TOOD support type nesting safely!!! to prevent infinite recursion
        if shvtp is shvNull:
            return None
        if shvtp is shvBool:
            return random.choice([True, False])
        if shvtp is shvDateTime:
            return datetime.datetime.now()
        if shvtp is shvDecimal:
            return random.randint(0, 100000)
        if shvtp in (shvMap, shvIMap):
            return typing.cast(collections.abc.Mapping[str, shv.SHVType], {})
        if isinstance(shvtp, SHVTypeInt):
            # TODO cover case when min is higher than 100 and max lower than 0
            minval = shvtp.minimum or (0 if shvtp.unsigned else -100)
            maxval = shvtp.maximum or 100
            if shvtp.multiple_of is not None:
                return shvtp.multiple_of * random.randrange(
                    minval // shvtp.multiple_of, maxval // shvtp.multiple_of
                )
            return random.randrange(minval, maxval)
        if shvtp is shvDouble:
            return random.random()
        if isinstance(shvtp, SHVTypeString) and shvtp.pattern is None:
            return "".join(
                random.choice(string.ascii_letters)
                for _ in range(
                    random.randrange(shvtp.min_length or 0, shvtp.max_length or 100)
                )
            )
        if isinstance(shvtp, SHVTypeBlob):
            return bytes(
                random.randrange(0, 255)
                for _ in range(
                    random.randrange(shvtp.min_length or 0, shvtp.max_length or 100)
                )
            )
        if isinstance(shvtp, SHVTypeEnum):
            return random.choice(list(shvtp.values()))
        if isinstance(shvtp, SHVTypeBitfield):
            val = 0
            for tp, pos, siz in shvtp.types():
                val |= int(cls._dummy_value(tp) & (2**siz - 1)) << pos
            return val
        if isinstance(shvtp, SHVTypeList):
            if shvtp.maxlen is None:
                return []
            return [
                cls._dummy_value(shvtp.allowed)
                for _ in range(random.randrange(shvtp.minlen, shvtp.maxlen))
            ]
        if isinstance(shvtp, SHVTypeTuple):
            return [cls._dummy_value(v) for v in shvtp]
        if isinstance(shvtp, SHVTypeMap):
            return {k: cls._dummy_value(v) for k, v in shvtp.items()}
        if isinstance(shvtp, SHVTypeIMap):
            return {
                k: cls._dummy_value(v) for k, v in shvtp.items() if isinstance(k, int)
            }
        if isinstance(shvtp, SHVTypeAlias):
            return cls._dummy_value(shvtp.type)
        if isinstance(shvtp, SHVTypeOneOf):
            return cls._dummy_value(random.choice(list(shvtp))) if shvtp else None
        if isinstance(shvtp, SHVTypeConstant):
            return shvtp.value
        raise shv.RpcMethodCallExceptionError(f"Can't generate value for type: {shvtp}")

    def _serialNumber_get(self, method: SHVMethod) -> shv.SHVType:
        value = 0xFF42
        if method.result.validate(value):
            return value
        return self._dummy_value(method.result)

    def _status_get(self, method: SHVMethod) -> shv.SHVType:
        if isinstance(method.result, SHVTypeEnum) and "ok" in method.result:
            return method.result["ok"]
        return self._dummy_value(method.result)

    def _utcTime_get(self, method: SHVMethod) -> shv.SHVType:
        if isinstance(method.result, SHVTypeDateTime):
            return datetime.datetime.utcnow() + self.dummy_time_offset
        return self._dummy_value(method.result)

    def _utcTime_set(self, method: SHVMethod, param: shv.SHVType) -> shv.SHVType:
        if isinstance(method.param, SHVTypeDateTime):
            assert isinstance(param, datetime.datetime)
            if param.tzinfo is not None and param.tzinfo != datetime.timezone.utc:
                raise shv.RpcInvalidParamsError("DateTime must be in UTC")
            self.dummy_time_offset = (
                param.replace(tzinfo=None) - datetime.datetime.utcnow()
            )
        return self._dummy_value(method.result)

    def _localTime_get(self, method: SHVMethod) -> shv.SHVType:
        if isinstance(method.result, SHVTypeDateTime):
            return datetime.datetime.now() + self.dummy_time_offset
        return self._dummy_value(method.result)
