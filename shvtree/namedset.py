"""Implementation of special set of named objects."""

from __future__ import annotations

import collections.abc
import typing


class Named:
    """Any class that has read only name attribute."""

    def __init__(self, name: str) -> None:
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

    def __init__(self, *values: NamedT) -> None:
        """Initialize new set of named objects.

        :param nset: iterable with objects to be initially added to the set.
        """
        self.__namedset: list[NamedT] = list(values)

    def add(self, obj: NamedT) -> None:
        """Add given object to the set."""
        if obj.name in self:
            raise ValueError(
                f"Object with name '{obj.name}' is already present in the set."
            )
        self.__namedset.append(obj)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, Named):
            return item in self.__namedset
        if isinstance(item, str):
            return any(item == named.name for named in self.__namedset)
        return False

    def __iter__(self) -> typing.Iterator[str]:
        return (value.name for value in self.__namedset)

    def __len__(self) -> int:
        return len(self.__namedset)

    def __getitem__(self, key: str) -> NamedT:
        try:
            return next(named for named in self.__namedset if named.name == key)
        except StopIteration as exc:
            raise KeyError(f"No item for key: {key}") from exc

    def __delitem__(self, key: str) -> None:
        self.discard(self[key])

    def discard(self, value: NamedT) -> None:
        """Remove ``value`` from self."""
        self.__namedset.remove(value)

    def update(self, nset: NamedSet) -> None:
        """Add all of ``nset`` into the self."""
        for obj in nset.values():
            self.add(obj)

    def __repr__(self) -> str:
        return str({value.name: str(value) for value in self.__namedset})
