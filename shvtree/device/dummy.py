"""The implementation that creates dummy device out of any tree."""
# pylint: disable=C0103
import datetime
import importlib.metadata
import random
import typing

import shv

from .. import (
    SHVMethod,
    SHVTypeAlias,
    SHVTypeBase,
    SHVTypeConstant,
    SHVTypeEnum,
    SHVTypeIMap,
    SHVTypeList,
    SHVTypeMap,
    SHVTypeOneOf,
    SHVTypeTuple,
    shvBlob,
    shvBool,
    shvDateTime,
    shvDecimal,
    shvDouble,
    shvInt,
    shvNull,
    shvString,
    shvUInt,
)
from .device import SHVTreeDevice


class SHVTreeDummyDevice(SHVTreeDevice):
    """The dummy device that overrides not-implemented error based on requested type."""

    APP_NAME = "pyshvtree-dummy"
    try:
        APP_VERSION = importlib.metadata.version("pyshvtree")
    except importlib.metadata.PackageNotFoundError:
        APP_VERSION = "unknown"

    def _get_method_impl(self, args: dict[str, typing.Any]) -> typing.Callable | None:
        res = super()._get_method_impl(args)
        if res is None and args.get("method", None) is not None:
            return self._default_method
        return res

    def _default_method(self, param: shv.SHVType, method: SHVMethod) -> shv.SHVType:
        return self._dummy_value(method.result)

    @classmethod
    def _dummy_value(cls, shvtp: SHVTypeBase) -> shv.SHVType:
        if shvtp is shvNull:
            return None
        if shvtp is shvBool:
            return random.choice([True, False])
        if shvtp is shvInt:
            return random.randint(-100, 100)
        if shvtp is shvUInt:
            return random.randint(0, 100)
        if shvtp is shvDouble:
            return random.random()
        if shvtp is shvBlob:
            return b""
        if shvtp is shvString:
            return ""
        if shvtp is shvDateTime:
            return datetime.datetime.now()
        if shvtp is shvDecimal:
            return random.randint(0, 100000)
        if isinstance(shvtp, SHVTypeEnum):
            # Note: this handles SHVTypeBitfield as well
            return random.choice(list(shvtp.values()))
        if isinstance(shvtp, SHVTypeList):
            return []
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
            return cls._dummy_value(next(iter(shvtp))) if shvtp else None
        if isinstance(shvtp, SHVTypeConstant):
            return shvtp.value
        raise shv.RpcMethodCallExceptionError(f"Can't generate value for type: {shvtp}")

    def _serialNumber_get(self):
        return 0xFF42

    def _status_get(self, method: SHVMethod):
        assert isinstance(method.result, SHVTypeEnum)
        return method.result["ok"]

    def _errors_get(self):
        return 0
