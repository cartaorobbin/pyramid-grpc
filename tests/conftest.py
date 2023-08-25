import pytest
import transaction
import zope.sqlalchemy
from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker

from tests.a10n import SecurityPolicy

pytest_plugins = [
    "tests.plugins.jwt_fixtures",
]


def get_engine(settings, prefix="sqlalchemy."):
    return engine_from_config(settings, prefix)


@pytest.fixture(scope="module")
def tm():
    tm = transaction.TransactionManager(explicit=True)
    tm.begin()
    tm.doom()

    yield tm

    tm.abort()


@pytest.fixture(scope="module")
def dbsession(app_config, tm):
    engine = get_engine(app_config.registry.settings)

    factory = sessionmaker()
    factory.configure(bind=engine)
    app_config.registry["dbsession_factory"] = factory

    session_factory = app_config.registry["dbsession_factory"]

    _session = session_factory()

    zope.sqlalchemy.register(_session, transaction_manager=tm)
    return dbsession


@pytest.fixture(scope="module")
def app_config(private_key, public_key):
    with Configurator() as config:
        config.get_settings()["jwt.private_key"] = private_key
        config.get_settings()["jwt.public_key"] = public_key
        config.get_settings()["sqlalchemy.url"] = "sqlite:////tmp/testing.sqlite"
        config.get_settings()["tm.manager_hook"] = "pyramid_tm.explicit_manager"
        config.include("pyramid_tm")
        config.include(".services")
        config.include("pyramid_jwt")
        config.set_security_policy(SecurityPolicy(config.get_settings()))
        config.include("pyramid_grpc")
    return config


@pytest.fixture(scope="module")
def app(app_config, _grpc_server):
    app_config.configure_grpc(_grpc_server)
    app = app_config.make_wsgi_app()

    return app


@pytest.fixture(scope="module")
def grpc_server(grpc_addr, app):
    server = app.registry.grpc_server

    server.add_insecure_port(grpc_addr)
    server.start()
    yield server
    server.stop(grace=None)


# @pytest.fixture(scope="module")
# def grpc_interceptors(app_config, dbsession):
#     request_intersector = RequestInterseptor(
#         app_config.registry,
#         extra_environ={"HTTP_HOST": "example.com"},
#     )

#     transaction_intersector = TransactionInterseptor(app_config.registry)

#     return [request_intersector, transaction_intersector]


@pytest.fixture
def greet_stub(grpc_channel):
    from tests.services.greet_pb2_grpc import GreeterStub

    return GreeterStub(grpc_channel)
