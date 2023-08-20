from os import name
from tests.services.greet_pb2 import HelloRequest


def test_service(app, greet_stub):

    metadata=(
                ("initial-metadata-1", "The value should be str"),
                (
                    "binary-metadata-bin",
                    b"With -bin surffix, the value can be bytes",
                ),
                ("accesstoken", "gRPC Python is great"),
            )
    request = HelloRequest(name="Tomas")
    response = greet_stub.SayHello(request, metadata=metadata)
    assert response.message == "Hi Tomas! I'm example.com"


def test_service_with_permissions(app, greet_stub, auth_token):

    metadata=(
                ("initial-metadata-1", "The value should be str"),
                (
                    "binary-metadata-bin",
                    b"With -bin surffix, the value can be bytes",
                ),
                ("authorization", auth_token({'scope': ['say::hellow']})),
            )

    request = HelloRequest(name="Tomas")
    response = greet_stub.SecureSayHello(request, metadata=metadata)
    assert response.message == "Hi Tomas! I'm example.com"
