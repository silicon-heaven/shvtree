"""The SHV node's method description."""
from __future__ import annotations

import shv

from . import namedset
from .types import SHVTypeBase, shvNull
from .types_builtins import shvGetParam


class SHVMethod(namedset.Named):
    """The SHV node's method description.

    :param name: name of the method.
    :param args: expected argument type for this method.
    :param returns: expected return type from this method.
    :param flags: method flags and hints.
    :param access_level: minimal requires access level for this method
    :param description: optional method description.
    """

    def __init__(
        self,
        name: str,
        args: SHVTypeBase = shvNull,
        returns: SHVTypeBase = shvNull,
        flags: shv.RpcMethodFlags = shv.RpcMethodFlags(0),
        access_level: shv.RpcMethodAccess = shv.RpcMethodAccess.COMMAND,
        description: str = "",
    ):
        # TODO prevent from creation of ls and dir!!!!
        super().__init__(name)
        self.args = args
        self.returns = returns
        self.flags = flags
        self.access_level = access_level
        self.description = description

    @classmethod
    def new_change(
        cls,
        dtype: SHVTypeBase,
        flags: shv.RpcMethodFlags = shv.RpcMethodFlags(0),
        access_level: shv.RpcMethodAccess = shv.RpcMethodAccess.READ,
        description: str = "",
    ) -> SHVMethod:
        """Initialize new method that is standard signal."""
        nflags = flags | shv.RpcMethodFlags.SIGNAL
        return cls("chng", shvNull, dtype, nflags, access_level, description)

    @classmethod
    def new_getter(
        cls,
        dtype: SHVTypeBase,
        flags: shv.RpcMethodFlags = shv.RpcMethodFlags(0),
        access_level: shv.RpcMethodAccess = shv.RpcMethodAccess.READ,
        description: str = "",
    ) -> SHVMethod:
        """Initialize new method that is standard getter."""
        nflags = flags | shv.RpcMethodFlags.GETTER
        return cls("get", shvGetParam, dtype, nflags, access_level, description)

    @classmethod
    def new_setter(
        cls,
        dtype: SHVTypeBase,
        flags: shv.RpcMethodFlags = shv.RpcMethodFlags(0),
        access_level: shv.RpcMethodAccess = shv.RpcMethodAccess.WRITE,
        description: str = "",
    ) -> SHVMethod:
        """Initialize new method that is standard setter."""
        nflags = flags | shv.RpcMethodFlags.SETTER
        return cls("set", dtype, shvNull, nflags, access_level, description)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SHVMethod)
            and self.name == other.name
            and self.args == other.args
            and self.returns == other.returns
            and self.flags == other.flags
            and self.description == other.description
        )

    __method_signature_map = {
        (False, False): shv.RpcMethodSignature.VOID_VOID,
        (True, False): shv.RpcMethodSignature.VOID_PARAM,
        (False, True): shv.RpcMethodSignature.RET_VOID,
        (True, True): shv.RpcMethodSignature.RET_PARAM,
    }

    @property
    def signature(self) -> shv.RpcMethodSignature:
        """SHV RPC signature for this method."""
        return self.__method_signature_map[
            (self.args not in (None, shvNull), self.returns not in (None, shvNull))
        ]

    @property
    def descriptor(self) -> shv.RpcMethodDesc:
        """SHV RPC method descriptor."""
        return shv.RpcMethodDesc(
            self.name, self.signature, self.flags, self.access_level, self.description
        )
