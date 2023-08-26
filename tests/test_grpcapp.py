from tests.services.greet_pb2 import HelloRequest
from tests.services.greet_pb2_grpc import GreeterStub


def test_service(grpc_testapp, tm):
    resp = grpc_testapp(GreeterStub, "SayHello", HelloRequest(name="Tomas"))
    assert resp.message == "Hi Tomas! I'm localhost:80"
