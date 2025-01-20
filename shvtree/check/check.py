"""Checker and suggester for the SHVTree."""

import enum
import itertools

from shvtree import SHVTree, SHVTypeAlias, SHVTypeOneOf


class Checks(enum.Flag):
    """Handles for every single check that can be performed."""

    EMPTY_ONEOF = enum.auto()
    """Empty shvOneOf is not allowed. SHVTree does not support 'no type'."""
    ALIAS_INSTEAD_ONEOF = enum.auto()
    """It is prefered to use shvAlias instead of shvOneOf for a single type."""
    DUPLICATE_TYPE = enum.auto()
    """Detect type duplicates and suggest using aliases."""


def check(tree: SHVTree, disable: Checks | None = None) -> list[str]:
    """Perform checking operations of the provided tree.

    This is intended to discover issues that are not of syntax or definition but
    rather of style. The point is to not polute the loader with side chcecks
    such as duplications but still perform them on demand to ensure that we do
    not have some anti-patterns in the SVH tree.

    :param tree: The SHV tree to check.
    :param disable: Set of checks to disable. The default is to perform all
        checks.
    :returns:
    """
    if disable is None:
        disable = Checks(0)
    res = []
    for shvtp in tree.types.values():
        if isinstance(shvtp, SHVTypeOneOf):
            if Checks.EMPTY_ONEOF not in disable and len(shvtp) == 0:
                res.append(
                    f"SHV type OneOf '{shvtp.name}' has no field. "
                    + "Use SHV type Alias instead."
                )
            if Checks.ALIAS_INSTEAD_ONEOF not in disable and len(shvtp) == 1:
                res.append(
                    f"SHV type OneOf '{shvtp.name}' has only one field. "
                    + "Use SHV type Alias instead."
                )
    for shvtp1, shvtp2 in itertools.combinations(tree.types.values(), 2):
        if (
            not isinstance(shvtp1, SHVTypeAlias)
            and not isinstance(shvtp2, SHVTypeAlias)
            and shvtp1 == shvtp2
        ):
            res.append(
                f"Type '{shvtp1.name}' is same as '{shvtp2.name}'. "
                + "It is highly suggested to use Alias type instead."
            )

    return res
