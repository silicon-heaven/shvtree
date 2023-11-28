"""The SHV node's method description."""
from __future__ import annotations

import shv

from . import namedset
from .types import SHVTypeBase, shvNull
from .types_builtins import shvGetParam


class SHVMethod(namedset.Named):
    """The SHV node's method description.

    :param name: name of the method.
    :param param: expected argument type for this method.
    :param result: expected return type from this method.
    :param flags: method flags and hints.
    :param access: minimal requires access level for this method
    :param description: optional method description.
    """

    def __init__(
        self,
        name: str,
        param: SHVTypeBase = shvNull,
        result: SHVTypeBase = shvNull,
        flags: shv.RpcMethodFlags = shv.RpcMethodFlags(0),
        access: shv.RpcMethodAccess = shv.RpcMethodAccess.COMMAND,
        description: str = "",
    ):
        if name in ("ls", "dir", "lschng"):
            raise ValueError(f"Defining standard method {name} is not allowed")
        super().__init__(name)
        self.param = param
        self.result = result
        self.flags = flags
        self.access = access
        self.description = description

    @classmethod
    def new_signal(
        cls,
        name: str,
        dtype: SHVTypeBase,
        flags: shv.RpcMethodFlags = shv.RpcMethodFlags(0),
        access: shv.RpcMethodAccess = shv.RpcMethodAccess.READ,
        description: str = "",
    ) -> SHVMethod:
        """Initialize new method that is signal."""
        nflags = flags | shv.RpcMethodFlags.SIGNAL
        return cls(name, shvNull, dtype, nflags, access, description)

    @classmethod
    def new_change(
        cls,
        dtype: SHVTypeBase,
        flags: shv.RpcMethodFlags = shv.RpcMethodFlags(0),
        access: shv.RpcMethodAccess = shv.RpcMethodAccess.READ,
        description: str = "",
    ) -> SHVMethod:
        """Initialize new method that is standard change signal."""
        return cls.new_signal("chng", dtype, flags, access, description)

    @classmethod
    def new_getter(
        cls,
        dtype: SHVTypeBase,
        flags: shv.RpcMethodFlags = shv.RpcMethodFlags(0),
        access: shv.RpcMethodAccess = shv.RpcMethodAccess.READ,
        description: str = "",
    ) -> SHVMethod:
        """Initialize new method that is standard getter."""
        nflags = flags | shv.RpcMethodFlags.GETTER
        return cls("get", shvGetParam, dtype, nflags, access, description)

    @classmethod
    def new_setter(
        cls,
        dtype: SHVTypeBase,
        flags: shv.RpcMethodFlags = shv.RpcMethodFlags(0),
        access: shv.RpcMethodAccess = shv.RpcMethodAccess.WRITE,
        description: str = "",
    ) -> SHVMethod:
        """Initialize new method that is standard setter."""
        nflags = flags | shv.RpcMethodFlags.SETTER
        return cls("set", dtype, shvNull, nflags, access, description)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SHVMethod)
            and self.name == other.name
            and self.param == other.param
            and self.result == other.result
            and self.flags == other.flags
            and self.description == other.description
        )

    @property
    def descriptor(self) -> shv.RpcMethodDesc:
        """SHV RPC method descriptor."""
        return shv.RpcMethodDesc(
            self.name,
            self.flags,
            self.param.name or "Null",
            self.result.name or "Null",
            self.access,
            self.description,
        )
