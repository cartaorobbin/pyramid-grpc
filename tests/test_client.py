import logging
from concurrent import futures

import grpc
import pytest

from pyramid_grpc.interseptors.client import RpcFailureLog, rpc_status_line
from tests.services.greet_pb2 import HelloRequest
from tests.services.greet_pb2_grpc import GreeterServicer, GreeterStub, add_GreeterServicer_to_server

_CLIENT_LOGGER = "pyramid_grpc.interseptors.client"


class _DenyServicer(GreeterServicer):
    """Reject SayHello with PERMISSION_DENIED."""

    def SayHello(self, request, context):
        context.abort(grpc.StatusCode.PERMISSION_DENIED, "Permission Denied")


@pytest.fixture(scope="module")
def denied_target():
    """Address of a server whose SayHello aborts PERMISSION_DENIED."""
    pool = futures.ThreadPoolExecutor(max_workers=1)
    server = grpc.server(pool)
    add_GreeterServicer_to_server(_DenyServicer(), server)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    yield f"127.0.0.1:{port}"
    server.stop(grace=None)
    pool.shutdown(wait=False)


@pytest.fixture
def denied_channel(denied_target):
    """Intercepted channel that logs failed unary calls."""
    channel = grpc.intercept_channel(grpc.insecure_channel(denied_target), RpcFailureLog())
    yield channel
    channel.close()


@pytest.fixture
def prefixed_denied_channel(denied_target):
    """Intercepted channel that shortens caller paths at ``tests/``."""
    channel = grpc.intercept_channel(
        grpc.insecure_channel(denied_target),
        RpcFailureLog(source_prefix="tests/"),
    )
    yield channel
    channel.close()


def test_failed_unary_propagates_permission_denied(denied_channel):
    """The RPC error still reaches the caller."""
    stub = GreeterStub(denied_channel)

    with pytest.raises(grpc.RpcError) as exc_info:
        stub.SayHello(HelloRequest(name="Ada"))

    assert exc_info.value.code() == grpc.StatusCode.PERMISSION_DENIED


def test_failed_unary_logs_method_status_and_caller(denied_channel, caplog):
    """One warning names the method, the status, and this test."""
    stub = GreeterStub(denied_channel)

    with caplog.at_level(logging.WARNING, logger=_CLIENT_LOGGER), pytest.raises(grpc.RpcError) as exc_info:
        stub.SayHello(HelloRequest(name="Ada"))

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.name == _CLIENT_LOGGER
    assert record.levelno == logging.WARNING
    assert record.exc_info is None
    assert "\n" not in record.message
    assert "debug_error_string" not in record.message
    assert record.message.startswith("gRPC /greet.v1.Greeter/SayHello PERMISSION_DENIED: Permission Denied @")
    assert record.message.endswith("test_failed_unary_logs_method_status_and_caller")
    assert rpc_status_line(exc_info.value) == "PERMISSION_DENIED: Permission Denied"


def test_source_prefix_shortens_caller_path(prefixed_denied_channel, caplog):
    """A caller-supplied prefix replaces the recorded path."""
    stub = GreeterStub(prefixed_denied_channel)

    with caplog.at_level(logging.WARNING, logger=_CLIENT_LOGGER), pytest.raises(grpc.RpcError):
        stub.SayHello(HelloRequest(name="Ada"))

    assert len(caplog.records) == 1
    message = caplog.records[0].message
    assert " @ tests/test_client.py:" in message
    assert message.endswith("test_source_prefix_shortens_caller_path")


def test_rpc_status_line_returns_none_for_plain_exception():
    """Exceptions without a grpc status are left unformatted."""
    assert rpc_status_line(RuntimeError("nope")) is None
