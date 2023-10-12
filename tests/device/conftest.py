import asyncio

import pytest
from shv import RpcLoginType, RpcMethodAccess, RpcUrl, ValueClient
from shv.broker import RpcBroker, RpcBrokerConfig


@pytest.fixture(name="port", scope="module")
def fixture_port(unused_tcp_port_factory):
    """Override for port for shvbroker."""
    return unused_tcp_port_factory()


@pytest.fixture(name="url", scope="module")
def fixture_url(port):
    """Provides RpcUrl for connecting to the broker."""
    return RpcUrl(
        location="localhost",
        port=port,
        username="admin",
        password="admin!123",
        login_type=RpcLoginType.PLAIN,
    )


@pytest.fixture(name="broker_config", scope="module")
def fixture_broker_config(url):
    """Configuration for the broker."""
    config = RpcBrokerConfig()
    config.listen = {"test": url}
    role_admin = RpcBrokerConfig.Role(
        "admin", RpcMethodAccess.DEVEL, frozenset({RpcBrokerConfig.Method()})
    )
    config.add_role(role_admin)
    user_admin = RpcBrokerConfig.User(
        "admin", "admin!123", RpcLoginType.PLAIN, frozenset({role_admin})
    )
    config.add_user(user_admin)
    return config


@pytest.fixture(name="broker")
async def fixture_broker(broker_config):
    """Provide running RpcBroker."""
    broker = RpcBroker(broker_config)
    await broker.start_serving()
    yield broker
    await broker.terminate()


@pytest.fixture(name="client")
async def fixture_client(broker, url):
    client = await ValueClient.connect(url)
    yield client
    await client.disconnect()
