"""Check device with shvtree."""

import dataclasses

import pytest
import shv
from shv import RpcMethodDesc, RpcMethodNotFoundError

from shvtree.device import SHVTreeDevice

from ..trees import tree1


class TreeDevice(SHVTreeDevice):
    tree = tree1
    APP_NAME = "pyshvtree-test-device"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prop_boolean = False

    def _serialNumber_get(self):  # noqa N816
        return 42

    async def _hwVersion_get(self):  # noqa N816
        return "unknown"

    def _properties_boolean_get(self) -> bool:
        return bool(self.prop_boolean)

    async def _properties_boolean_set(
        self, params: bool, signals: SHVTreeDevice.Signals
    ) -> None:
        if self.prop_boolean != params:
            await signals.chng(params)
        self.prop_boolean = params


class TreeDeviceInvalid(SHVTreeDevice):
    tree = tree1
    APP_NAME = "pyshvtree-test-device-invalid"

    def _properties_boolean_get(self):
        return 42


class EmptyDevice(SHVTreeDevice):
    APP_NAME = "pyshvtree-test-empty-device"


@pytest.fixture(name="device")
async def fixture_device(broker, url):
    nurl = dataclasses.replace(
        url,
        login=dataclasses.replace(
            url.login, options={"device": {"deviceId": "example", "mountPoint": "test"}}
        ),
    )
    client = await TreeDevice.connect(nurl)
    yield client
    await client.disconnect()


@pytest.fixture(name="invalid_device")
async def fixture_invalid_device(broker, url):
    nurl = dataclasses.replace(
        url,
        login=dataclasses.replace(
            url.login, options={"device": {"deviceId": "example", "mountPoint": "test"}}
        ),
    )
    client = await TreeDeviceInvalid.connect(nurl)
    yield client
    await client.disconnect()


@pytest.fixture(name="empty_device")
async def fixture_empty_device(broker, url):
    nurl = dataclasses.replace(
        url,
        login=dataclasses.replace(
            url.login,
            options={"device": {"deviceId": "example", "mountPoint": "empty"}},
        ),
    )
    client = await EmptyDevice.connect(nurl)
    yield client
    await client.disconnect()


@pytest.mark.parametrize(
    "path,expected",
    list(
        (f"test/{path}", list(n.name for n in node.nodes.values()))
        for path, node in iter(tree1)
    ),
)
async def test_ls(device, client, path, expected):
    """Check that we can list all nodes in the tree."""
    assert await client.ls(path) == expected


async def test_ls_invalid(device, client):
    """Check that we correctly handle ls of invalid path."""
    with pytest.raises(shv.RpcMethodNotFoundError):
        await client.ls("/test/properties/missing")


async def test_empty_ls(empty_device, client):
    assert await client.ls("empty") == [".app"]


async def test_empty_ls_invalid(empty_device, client):
    with pytest.raises(shv.RpcMethodNotFoundError):
        await client.ls("empty/missing")


@pytest.mark.parametrize(
    "path,expected",
    [
        [
            f"test/{path}",
            [RpcMethodDesc.stddir(), RpcMethodDesc.stdls()]
            + (
                [
                    RpcMethodDesc.getter("shvVersionMajor", param="n", result="i"),
                    RpcMethodDesc.getter("shvVersionMinor", param="n", result="i"),
                    RpcMethodDesc.getter("name", param="n", result="s"),
                    RpcMethodDesc.getter("version", param="n", result="s"),
                    RpcMethodDesc.getter("date", "n", "t"),
                    RpcMethodDesc("ping"),
                ]
                if path == ".app"
                else []
            )
            + [m.descriptor for m in node.methods.values()]
            + (
                [
                    RpcMethodDesc.getter(
                        "desc",
                        param="n",
                        result="s",
                        access=shv.RpcMethodAccess.BROWSE,
                    )
                ]
                if node.description
                else []
            ),
        ]
        for path, node in iter(tree1)
    ],
)
async def test_dir(device, client, path, expected):
    """Check that we can list all methods with details in the tree."""
    assert await client.dir(path) == expected


async def test_dir_invalid(device, client):
    """Check that we correctly handle ls of invalid path."""
    with pytest.raises(shv.RpcMethodNotFoundError):
        await client.dir("/test/properties/missing")


async def test_empty_dir(empty_device, client):
    assert await client.dir("empty") == [
        RpcMethodDesc.stddir(),
        RpcMethodDesc.stdls(),
    ]


@pytest.mark.parametrize(
    "path,method,expected",
    (("test/serialNumber", "desc", "Serial number of the board"),),
)
async def test_call(device, client, path, method, expected):
    assert await client.call(path, method) == expected


@pytest.mark.parametrize(
    "path,expected",
    (
        ("test/serialNumber", 42),
        ("test/hwVersion", "unknown"),
    ),
)
async def test_prop_get(device, client, path, expected):
    assert await client.prop_get(path) == expected


async def test_invalid_path(device, client):
    with pytest.raises(RpcMethodNotFoundError):
        await client.call("test/invalid", "get")


async def test_invalid_param(device, client):
    with pytest.raises(shv.RpcInvalidParamError):
        await client.call("test/properties/boolean", "set", 42)


async def test_invalid_result(invalid_device, client):
    with pytest.raises(shv.RpcMethodCallExceptionError):
        await client.prop_get("test/properties/boolean")
