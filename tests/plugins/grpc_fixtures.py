# grpc fixtures
import copy
from concurrent import futures
from contextlib import suppress
from unittest.mock import PropertyMock

import grpc
import pytest
from pytest_grpc.plugin import FakeChannel, FakeServer


@pytest.fixture(scope="module")
def grpc_add_to_server():
    def lala(*args, **kwargs):
        pass

    return lala


@pytest.fixture(scope="module")
def grpc_servicer():
    return


@pytest.fixture(scope="module")
def grpc_is_fake(request):
    return request.config.getoption("grpc-fake")


@pytest.fixture(scope="module")
def _pyramid_grpc_server(request, grpc_is_fake, grpc_addr, grpc_interceptors):
    max_workers = request.config.getoption("grpc-max-workers")

    with suppress(AttributeError):
        max_workers = max(request.module.grpc_max_workers, max_workers)

    pool = futures.ThreadPoolExecutor(max_workers=max_workers)
    if grpc_is_fake:
        server = FakeServer(pool)
        yield server
    else:
        server = grpc.server(pool, interceptors=grpc_interceptors)
        yield server
    pool.shutdown(wait=False)


@pytest.fixture(scope="module")
def pyramid_grpc_create_channel(grpc_is_fake, grpc_addr, pyramid_grpc_server):
    def _create_channel(credentials=None, options=None):
        if grpc_is_fake:
            return FakeChannel(pyramid_grpc_server, credentials)
        if credentials is not None:
            return grpc.secure_channel(grpc_addr, credentials, options)
        return grpc.insecure_channel(grpc_addr, options)

    return _create_channel


@pytest.fixture(scope="module")
def pyramid_grpc_channel(pyramid_grpc_create_channel):
    with pyramid_grpc_create_channel() as channel:
        yield channel


@pytest.fixture(scope="module")
def pyramid_grpc_server(grpc_addr, app):
    server = app.registry.grpc_server

    server.add_insecure_port(grpc_addr)
    server.start()
    yield server
    server.stop(grace=None)


@pytest.fixture()
def transaction_interseptor_extra_environ_mock(mocker):
    def _mock(value):
        mocker.patch(
            "pyramid_grpc.interseptors.request.RequestInterseptor.extra_environ",
            new_callable=PropertyMock(return_value=value),
        )

    return _mock


class GrpcTestApp:
    def __init__(self, app, server, channel, extra_environ=None):
        self.app = app
        self.server = server
        self.channel = channel
        self.extra_environ = extra_environ or {}

    def metadata(self, **kwargs):
        data = copy.copy(self.extra_environ)
        data.update(kwargs)
        return tuple((k, v) for k, v in data.items())

    def __call__(self, stub, method, request, **kwargs):
        callable_ = getattr(stub(self.channel), method)
        return callable_(request, metadata=self.metadata(**kwargs))
