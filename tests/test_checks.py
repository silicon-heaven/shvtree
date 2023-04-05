"""Test that our checker works as epxected."""
from shvtree.check import check

from . import trees


def test_tree1():
    """The tree1 should be without any issues."""
    assert not check(trees.tree1)
