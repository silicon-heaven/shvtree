"""Check our genericc implementation for set of named objects."""
import pytest

from shvtree.namedset import Named, NamedSet


class Foo(Named):
    """Just some generic named type."""

    def __init__(self, name):
        super().__init__(name)


def test_named():
    """Just check that child class with __name has name property."""
    assert Foo("foo").name == "foo"


foos = [Foo("foo1"), Foo("foo2"), Foo("foo3")]
foo4 = Foo("foo4")


@pytest.fixture(name="namedset")
def fixture_namedset():
    """Instance of NamedSet."""
    return NamedSet[Foo](*foos)


def test_len(namedset):
    assert len(namedset) == 3


@pytest.mark.parametrize("foo", foos)
def test_in(namedset, foo):
    assert foo in namedset


@pytest.mark.parametrize("foo", foos)
def test_in_name(namedset, foo):
    assert foo.name in namedset


def test_not_in(namedset):
    assert foo4 not in namedset


def test_invalid_in(namedset):
    assert False not in namedset


def test_del(namedset):
    assert foos[2] in namedset
    del namedset[foos[2].name]
    assert set((foo.name for foo in foos if foo is not foos[2])) == set(namedset)


def test_update(namedset):
    newset = NamedSet()
    assert set(newset) == set()
    newset.update(namedset)
    assert set((foo.name for foo in foos)) == set(newset)


@pytest.mark.parametrize("foo", foos)
def test_get(namedset, foo):
    assert namedset[foo.name] == foo


def test_get_missing(namedset):
    with pytest.raises(KeyError):
        namedset["missing"]


@pytest.fixture(name="namedset4")
def fixture_namedset4(namedset):
    """Namedset with foo4 added."""
    namedset.add(foo4)
    return namedset


def test_add(namedset4):
    """Check that add works as expected."""
    assert foo4 in namedset4


def test_add_duplicate(namedset):
    """See if we fail when duplicate item is being added."""
    with pytest.raises(ValueError):
        namedset.add(foos[1])
