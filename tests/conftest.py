from pyramid.config import Configurator
import pytest

from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from pyramid_grpc.interseptors.request import RequestInterseptor
from pyramid_grpc.interseptors.transaction import TransactionInterseptor
import transaction
import zope.sqlalchemy

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
def dbsession(app, tm):

    engine = get_engine(app.registry.settings)

    factory = sessionmaker()
    factory.configure(bind=engine)
    app.registry["dbsession_factory"] = factory

    session_factory = app.registry["dbsession_factory"]

    _session = session_factory()

    zope.sqlalchemy.register(_session, transaction_manager=tm)
    return dbsession

    return # models.get_tm_session(session_factory, tm)

@pytest.fixture(scope="module")
def app(private_key, public_key):
    with Configurator() as config:
        config.get_settings()['jwt.private_key'] = private_key
        config.get_settings()['jwt.public_key'] = public_key
        config.get_settings()['sqlalchemy.url'] = "sqlite:////tmp/testing.sqlite"
        config.get_settings()['tm.manager_hook'] = 'pyramid_tm.explicit_manager'
        config.include("pyramid_tm")
        config.include("pyramid_grpc")
        config.include(".services")
        config.include('pyramid_jwt')
        config.set_security_policy(SecurityPolicy(config.get_settings()))
        app = config.make_wsgi_app()

    return app


@pytest.fixture(scope="module")
def grpc_interceptors(app, dbsession):
    request_intersector = RequestInterseptor(
        app,
        extra_environ={"HTTP_HOST": "example.com"},
    )

    transaction_intersector = TransactionInterseptor(
        app
    )

    return [
        request_intersector, transaction_intersector
    ]


@pytest.fixture(scope="module")
def grpc_server(_grpc_server, grpc_addr, app):
    from pyramid_grpc.main import configure_server

    configure_server(pyramid_app=app, grpc_server=_grpc_server)

    _grpc_server.add_insecure_port(grpc_addr)
    _grpc_server.start()
    yield _grpc_server
    _grpc_server.stop(grace=None)


@pytest.fixture
def greet_stub(grpc_channel):
    from tests.services.greet_pb2_grpc import GreeterStub

    return GreeterStub(grpc_channel)

