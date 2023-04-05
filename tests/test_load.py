"""Validate loading from basic representation."""
import pytest

from shvtree import NamedSet, SHVNode, SHVTree
from shvtree.load import load, load_json, load_raw

from . import trees


def test_tree1(path_tree1):
    assert load(path_tree1) == trees.tree1


def test_tree2(path_tree2):
    assert load(str(path_tree2)) == trees.tree2


def test_load_invalid():
    with pytest.raises(RuntimeError):
        load("foo.txt")


def test_load_json():
    assert load_json('{"nodes": {"one":{}}}') == SHVTree(nodes=NamedSet(SHVNode("one")))


def test_empty_tree():
    assert load_raw({}) == SHVTree()


def test_invalid_type_types():
    with pytest.raises(TypeError, match=r"^Invalid type of 'types': <class 'bool'>$"):
        load_raw({"types": True})


def test_invalid_type_nodes():
    with pytest.raises(TypeError, match=r"^Invalid type of 'nodes': <class 'bool'>$"):
        load_raw({"nodes": False})


def test_invalid_type_node_methods():
    with pytest.raises(TypeError, match=r"^Invalid type of 'methods': <class 'bool'>$"):
        load_raw({"nodes": {"foo": {"methods": False}}})


def test_invalid_key():
    with pytest.raises(ValueError, match=r"^Unsupported keys: invalid$"):
        load_raw({"invalid": None})


def test_invalid_prop_type():
    with pytest.raises(ValueError, match=r"^Invalid type reference name: invalid$"):
        load_raw({"nodes": {"foo": {"property": "invalid"}}})


def test_invalid_node_key():
    with pytest.raises(ValueError, match=r"^Unsupported keys for node 'foo': invalid$"):
        load_raw({"nodes": {"foo": {"invalid": "foo"}}})


def test_invalid_node_method_key():
    with pytest.raises(
        ValueError, match=r"^Unsupported keys for method 'foo': invalid$"
    ):
        load_raw({"nodes": {"foo": {"methods": {"foo": {"invalid": "foo"}}}}})


def test_invalid_node_method_flag():
    with pytest.raises(ValueError, match=r"^Invalid flag for method 'get': INVALID$"):
        load_raw({"nodes": {"foo": {"methods": {"get": {"flags": ["invalid"]}}}}})
