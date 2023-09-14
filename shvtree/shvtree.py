"""Implementation of the top level SHV tree class."""
from . import namedset
from .node import SHVNode
from .types import SHVTypeBase
from .types_builtins import shvBuiltins


class SHVTree(SHVNode):
    """The top level of the SHV tree.

    Note that top level is node as well but with its name always set to empty
    string.

    :param nodes: Nodes that are part of the tree.
    :param types: Custom types used in nodes.
    """

    def __init__(
        self,
        nodes: namedset.NamedSet[SHVNode] | None = None,
        types: namedset.NamedSet[SHVTypeBase] | None = None,
    ) -> None:
        super().__init__(name="", nodes=nodes)
        self.types: namedset.NamedSet[SHVTypeBase] = (
            types if types is not None else namedset.NamedSet()
        )
        """Access to the types used in the nodes of this tree."""

    def get_type(self, name: str) -> None | SHVTypeBase:
        """Getter of type.

        You should use this instead of directly using self.types because those
        are only custom types while this can provide you with builtin types as
        well.

        :param name: Name of the required type.
        :returns: Instance of SHVTypeBase or None in case type can't be located.
        """
        if name in shvBuiltins:
            return shvBuiltins[name]
        return self.types[name]

    def __str__(self):
        return super().__str__() + str(
            {
                "types": str(self.types),
                "nodes": str(self.nodes),
            }
        )

    def __eq__(self, other: object):
        return super().__eq__(other) and (
            isinstance(other, SHVTree) and self.types == other.types
        )
