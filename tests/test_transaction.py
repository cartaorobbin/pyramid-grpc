from tests.services.greet_pb2_grpc import GreeterStub
from tests.services.greet_pb2 import HelloRequest

from tests.models.greet import Greet


def test_service_tm(grpc_testapp, tm, dbsession):

    resp = grpc_testapp(GreeterStub, 'TransactionSayHello', HelloRequest(name="Tomas"))
    assert resp.message == f"Hi Tomas! I'm {id(dbsession)}"

def test_service_with_persistent_1(grpc_testapp, tm, dbsession):

    greet = Greet(message="Hello World!")
    dbsession.add(greet)
    dbsession.flush()

    resp = grpc_testapp(GreeterStub, 'PersistedSayHello', HelloRequest(name="Tomas"))
    assert resp.message == f"Hi Tomas! I'm Hello World!"


def test_service_with_persistent_2(grpc_testapp, tm, dbsession):

    greet = Greet(message="Hello World 2!")
    dbsession.add(greet)
    dbsession.flush()

    resp = grpc_testapp(GreeterStub, 'PersistedSayHello', HelloRequest(name="Tomas"))
    assert resp.message == f"Hi Tomas! I'm Hello World 2!"


    
