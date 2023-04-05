"""Check dummy device."""
import dataclasses
import datetime

import pytest

from shvtree.device import SHVTreeDummyDevice

from ..trees import tree1


class TreeDevice(SHVTreeDummyDevice):
    tree = tree1


@pytest.fixture(name="device")
async def fixture_device(broker, url):
    nurl = dataclasses.replace(url, device_mount_point="test")
    client = await TreeDevice.connect(nurl)
    yield client
    await client.disconnect()


async def test_prop_boolean(device, client):
    res = await client.prop_get("test/properties/boolean")
    assert res in (True, False)


async def test_prop_int(device, client):
    res = await client.prop_get("test/properties/integer")
    assert isinstance(res, int)
    assert -100 <= res <= 100


async def test_prop_uint(device, client):
    res = await client.prop_get("test/properties/uinteger")
    assert isinstance(res, int)
    assert 0 <= res <= 100


async def test_prop_string(device, client):
    res = await client.prop_get("test/properties/string")
    assert res == ""


async def test_prop_datetime(device, client):
    res = await client.prop_get("test/properties/dateTime")
    assert isinstance(res, datetime.datetime)


async def test_prop_tuple(device, client):
    res = await client.prop_get("test/properties/tuple")
    assert isinstance(res, list)
    assert len(res) == 5
    assert res[0] in (True, False)
    assert -100 <= res[1] <= 100
    assert 0 <= res[2] <= 100
    assert res[3] == ""
    assert isinstance(res[4], datetime.datetime)


async def test_prop_map(device, client):
    res = await client.prop_get("test/properties/map")
    assert isinstance(res, dict)
    assert len(res) == 5
    assert res["boolean"] in (True, False)
    assert -100 <= res["integer"] <= 100
    assert 0 <= res["uinteger"] <= 100
    assert res["string"] == ""
    assert isinstance(res["dateTime"], datetime.datetime)


async def test_prop_imap(device, client):
    res = await client.prop_get("test/properties/imap")
    assert isinstance(res, dict)
    assert len(res) == 5
    assert res[0] in (True, False)
    assert -100 <= res[1] <= 100
    assert 0 <= res[2] <= 100
    assert res[3] == ""
    assert isinstance(res[4], datetime.datetime)


@pytest.mark.parametrize(
    "path,expected",
    (
        ("serialNumber", 0xFF42),
        ("status", 0),
        ("errors", 0),
    ),
)
async def test_common_props_get(device, client, path, expected):
    """Some static mappings."""
    assert await client.prop_get(f"test/{path}") == expected
