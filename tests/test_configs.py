from pyramid.config import Configurator
from pyramid_grpc.interseptors.request import RequestInterseptor
from pyramid_grpc.interseptors.transaction import TransactionInterseptor


def test_config_with_tm(private_key, public_key):
    with Configurator() as config:
        config.get_settings()["jwt.private_key"] = private_key
        config.get_settings()["jwt.public_key"] = public_key
        config.get_settings()["sqlalchemy.url"] = "sqlite:////tmp/testing.sqlite"
        config.get_settings()["tm.manager_hook"] = "pyramid_tm.explicit_manager"
        config.include("pyramid_tm")
        config.include("pyramid_grpc")
        # config.configure_grpc_interceptors(RequestInterseptor(config.registry))

    app = config.make_wsgi_app()
    assert app.registry.grpc_interceptors[0].__class__ == RequestInterseptor
    assert app.registry.grpc_interceptors[1].__class__ == TransactionInterseptor


def test_config_without_tm(private_key, public_key):
    with Configurator() as config:
        config.get_settings()["jwt.private_key"] = private_key
        config.get_settings()["jwt.public_key"] = public_key
        config.get_settings()["sqlalchemy.url"] = "sqlite:////tmp/testing.sqlite"
        # config.get_settings()["tm.manager_hook"] = "pyramid_tm.explicit_manager"
        # config.include("pyramid_tm")
        config.include("pyramid_grpc")
        # config.configure_grpc_interceptors(RequestInterseptor(config.registry))

    app = config.make_wsgi_app()
    assert app.registry.grpc_interceptors[0].__class__ == RequestInterseptor
    assert len(app.registry.grpc_interceptors) == 1


def test_config_with_add_interceptor(private_key, public_key):
    with Configurator() as config:
        config.get_settings()["jwt.private_key"] = private_key
        config.get_settings()["jwt.public_key"] = public_key
        config.get_settings()["sqlalchemy.url"] = "sqlite:////tmp/testing.sqlite"
        # config.get_settings()["tm.manager_hook"] = "pyramid_tm.explicit_manager"
        # config.include("pyramid_tm")
        config.include("pyramid_grpc")
        config.add_grpc_interceptors(TransactionInterseptor(config.registry))

    app = config.make_wsgi_app()
    assert len(app.registry.grpc_interceptors) == 2
    assert app.registry.grpc_interceptors[0].__class__ == RequestInterseptor
    assert app.registry.grpc_interceptors[1].__class__ == TransactionInterseptor


def test_config_with_add_interceptor_twice(private_key, public_key):
    with Configurator() as config:
        config.get_settings()["jwt.private_key"] = private_key
        config.get_settings()["jwt.public_key"] = public_key
        config.get_settings()["sqlalchemy.url"] = "sqlite:////tmp/testing.sqlite"
        # config.get_settings()["tm.manager_hook"] = "pyramid_tm.explicit_manager"
        # config.include("pyramid_tm")
        config.include("pyramid_grpc")
        config.add_grpc_interceptors(TransactionInterseptor(config.registry))
        config.add_grpc_interceptors(TransactionInterseptor(config.registry))

    app = config.make_wsgi_app()
    assert len(app.registry.grpc_interceptors) == 3
    assert app.registry.grpc_interceptors[0].__class__ == RequestInterseptor
    assert app.registry.grpc_interceptors[1].__class__ == TransactionInterseptor
    assert app.registry.grpc_interceptors[2].__class__ == TransactionInterseptor
