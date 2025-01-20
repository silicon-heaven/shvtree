"""The SHV node description."""

from __future__ import annotations

import typing

from . import namedset
from .method import SHVMethod
from .types import SHVTypeBase


class SHVNode(namedset.Named):
    """The SHV node description."""

    def __init__(
        self,
        name: str,
        nodes: namedset.NamedSet[SHVNode] | None = None,
        methods: namedset.NamedSet[SHVMethod] | None = None,
        description: str = "",
    ) -> None:
        """Initialize new SHV node.

        :param name: Name of the node.
        :param nodes: NamedSet of child nodes.
        :param methods: NamedSet of methods associated with this node.
        :param description: Short text describing the node.
        """
        super().__init__(name)
        self.nodes = nodes if nodes is not None else namedset.NamedSet()
        """Access to the child nodes."""
        self.methods = methods if methods is not None else namedset.NamedSet()
        """Access to the methods associated with this node."""
        self.description = description
        """String describing node."""

    @classmethod
    def new_property(
        cls,
        name: str,
        dtype: SHVTypeBase,
        readonly: bool = False,
        signal: bool | str | None = None,
        description: str = "",
    ) -> SHVNode:
        """Initialize new SHV node that has property value assigned to it.

        :param name: Name of the node.
        :param dtype: Type of the property.
        :param readonly: Sets that property is read-only.
        :param signal: Sets that property change is signaled. If ``None`` is
          passed then change is signaled only for non-readonly property. If
          string is passed then given name of the signal is used.
        :param description: Short text describing the node.
        :returns: SHVNode instance
        """
        res = cls(name, description=description)
        res.make_property(dtype, readonly, signal)
        return res

    def make_property(
        self,
        dtype: SHVTypeBase,
        readonly: bool = False,
        signal: bool | str | None = None,
    ) -> None:
        """Add methods for making this node a property node with given type.

        This method can be called only once per object because there has to be
        none of the get/set/chng methods. To call it again you have to remove
        those methods first.

        :param dtype: Type of the property.
        :param readonly: Sets that property is read-only.
        :param signal: Sets that property change is signaled. If ``None`` is
          passed then change is signaled only for non-readonly property. You can
          pass string to specify different signal name over ``chng``.
        :raises SHVPropError: there is one of the property method already
            present.
        """
        self.methods.add(SHVMethod.new_getter(dtype))
        if not readonly:
            self.methods.add(SHVMethod.new_setter(dtype))
        if signal or (signal is None and not readonly):
            self.methods.add(
                SHVMethod.new_signal(
                    signal if isinstance(signal, str) else "chng", dtype
                )
            )

    def is_property(
        self,
        readonly: bool | None = None,
        signal: bool | None = None,
    ) -> bool:
        """Check if this node has associated value.

        It effectivelly checks if it provides get method but wrapping that to
        this method name makes it more clear.
        It also allows you to check if property is read-only and/or signal.

        :param readonly: if node provides 'set' methods. The default None means
            "do not check".
        :param signal: if node provides 'chng' method. The default None means
            "do not check".
        """
        res = "get" in self.methods
        if readonly is not None:
            res = res and (("set" not in self.methods) is readonly)
        if signal is not None:
            res = res and (("chng" in self.methods) is signal)
        return res

    def get_node(self, path: str) -> SHVNode | None:
        """Getter of the node from the tree using its path.

        :param path: Slash separated path to the node.
        :returns: Located node or None when there is no such node.
        """
        node = None
        nodes = self.nodes
        if not path:
            return self
        for name in path.split("/"):
            if name not in nodes:
                return None
            node = nodes[name]
            nodes = node.nodes
        return node

    def __iter__(self) -> typing.Iterator[tuple[str, SHVNode]]:
        """Recursive iterate over children (DFS).

        :returns: Iterator that provides tuples with two values. The first value
            is full path relative to this node and second is the node.
        """
        # Note on implementation. Nodes have to be instances of this object and
        # thus we have to yield only our children and recursion can be delegated
        # to the iterator of the children.
        for node_name, node in self.nodes.items():
            yield node_name, node
            for sname, snode in node:
                yield f"{node_name}/{sname}", snode

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SHVNode)
            and self.name == other.name
            and self.nodes == other.nodes
            and self.methods == other.methods
            and self.description == other.description
        )


class SHVPropError(RuntimeError):
    """The node can't be set to be property."""

    def __init__(self, existing: str) -> None:
        super().__init__(f"Node already has the following method: {existing}")
