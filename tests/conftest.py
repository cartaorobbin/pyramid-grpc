import pytest
import transaction
from pyramid.config import Configurator

import tests.models as models
from tests.a10n import SecurityPolicy


pytest_plugins = [
    "tests.plugins.jwt_fixtures",
    "tests.plugins.grpc_fixtures",
]


@pytest.fixture(scope="session")
def dbengine():
    engine = models.get_engine({"sqlalchemy.url": "sqlite:////tmp/testing.sqlite"})

    models.meta.Base.metadata.drop_all(bind=engine)

    # run migrations to initialize the database
    # depending on how we want to initialize the database from scratch
    # we could alternatively call:
    models.meta.Base.metadata.create_all(bind=engine)

    # alembic.command.upgrade(alembic_cfg, "head")

    yield engine

    models.meta.Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def tm():
    tm = transaction.TransactionManager(explicit=True)
    tm.begin()
    tm.doom()

    yield tm

    tm.abort()


@pytest.fixture
def dbsession(app, tm):
    from tests.models import get_tm_session

    session_factory = app.registry["dbsession_factory"]
    session = get_tm_session(session_factory, tm)
    yield session
    session.close()


@pytest.fixture(scope="module")
def app_config(private_key, public_key):
    with Configurator() as config:
        config.get_settings()["jwt.private_key"] = private_key
        config.get_settings()["jwt.public_key"] = public_key
        config.get_settings()["sqlalchemy.url"] = "sqlite:////tmp/testing.sqlite"
        config.get_settings()["tm.manager_hook"] = "pyramid_tm.explicit_manager"
        config.include("pyramid_tm")
        config.include(".services")
        config.include(".models")
        config.include("pyramid_jwt")
        config.set_security_policy(SecurityPolicy(config.get_settings()))
        config.include("pyramid_grpc")
    return config


@pytest.fixture(scope="module")
def app(dbengine, app_config, _grpc_server):
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


@pytest.fixture
def greet_stub(grpc_channel):
    from tests.services.greet_pb2_grpc import GreeterStub

    return GreeterStub(grpc_channel)


@pytest.fixture
def grpc_testapp(
    app, pyramid_grpc_server, pyramid_grpc_channel, transaction_interseptor_extra_environ_mock, tm, dbsession
):
    # override request.dbsession and request.tm with our own
    # externally-controlled values that are shared across requests but aborted
    # at the end

    extra_environ = {
        "http_host": "example.com",
        "tm.active": "True",
        "tm.manager": tm,
        "app.dbsession": dbsession,
    }

    from tests.plugins.grpc_fixtures import GrpcTestApp

    testapp = GrpcTestApp(
        app,
        server=pyramid_grpc_server,
        channel=pyramid_grpc_channel,
    )

    transaction_interseptor_extra_environ_mock(extra_environ)

    return testapp
