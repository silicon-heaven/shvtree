"""Implementation of special set of named objects."""
from __future__ import annotations

import collections.abc
import typing


class Named:
    """Any class that has read only name attribute."""

    def __init__(self, name: str):
        """Initialize object and set its name.

        :param name: name assigned to the object.
        """
        self.__name = name

    @property
    def name(self) -> str:
        """Name of the object."""
        return self.__name


NamedT = typing.TypeVar("NamedT", bound=Named)


class NamedSet(collections.abc.Mapping[str, NamedT]):
    """The set of objects that are based on Named class."""

    def __init__(self, *values: NamedT):
        """Initialize new set of named objects.

        :param nset: iterable with objects to be initially added to the set.
        """
        self.__namedset: list[NamedT] = list(values)

    def add(self, obj: NamedT):
        """Add given object to the set."""
        if obj.name in self:
            raise ValueError("Object of this name is already present in the set.")
        self.__namedset.append(obj)

    def __contains__(self, item: object):
        if isinstance(item, Named):
            return item in self.__namedset
        if isinstance(item, str):
            return any(item == named.name for named in self.__namedset)
        return False

    def __iter__(self):
        return (value.name for value in self.__namedset)

    def __len__(self):
        return len(self.__namedset)

    def __getitem__(self, key: str) -> NamedT:
        try:
            return next(named for named in self.__namedset if named.name == key)
        except StopIteration as exc:
            raise KeyError(f"No item for key: {key}") from exc

    def __delitem__(self, key: str):
        self.discard(self[key])

    def discard(self, value: NamedT):
        self.__namedset.remove(value)

    def update(self, nset: NamedSet):
        for obj in nset.values():
            self.add(obj)

    def __str__(self):
        return str({value.name: str(value) for value in self.__namedset})
