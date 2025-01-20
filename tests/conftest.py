import pathlib

import pytest


@pytest.fixture(name="path_tree1")
def fixture_path_tree1():
    """Path to the testing tree1.yaml."""
    return pathlib.Path(__file__).parent / "tree1.yaml"


@pytest.fixture(name="path_tree2")
def fixture_path_tree2():
    """Path to the testing tree2.json."""
    return pathlib.Path(__file__).parent / "tree2.json"


@pytest.fixture(name="path_tree3")
def fixture_path_tree3():
    """Path to the testing tree3.yaml."""
    return pathlib.Path(__file__).parent / "tree3.yaml"
