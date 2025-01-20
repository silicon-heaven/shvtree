import pytest
from shv import RpcLogin, RpcLoginType, RpcMethodAccess, RpcUrl, ValueClient
from shv.broker import RpcBroker, RpcBrokerConfig


@pytest.fixture(name="port", scope="module")
def fixture_port(unused_tcp_port_factory):
    """Override for port for shvbroker."""
    return unused_tcp_port_factory()


@pytest.fixture(name="url", scope="module")
def fixture_url(port):
    """Provide RpcUrl for connecting to the broker."""
    return RpcUrl(
        location="localhost",
        port=3755,
        login=RpcLogin(
            username="admin",
            password="admin!123",
            login_type=RpcLoginType.PLAIN,
        ),
    )


@pytest.fixture(name="broker_config", scope="module")
def fixture_broker_config(url):
    """Provide configuration for the broker."""
    role_admin = RpcBrokerConfig.Role(
        name="admin",
        mount_points={"**"},
        access={RpcMethodAccess.DEVEL: {"**:*"}},
    )
    user_admin = RpcBrokerConfig.User(
        name="admin",
        password="admin!123",
        roles=["admin"],
        login_type=RpcLoginType.PLAIN,
    )
    config = RpcBrokerConfig(
        name="testbroker",
        listen=[url],
        roles=[role_admin],
        users=[user_admin],
    )
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
