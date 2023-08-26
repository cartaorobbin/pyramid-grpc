from pyramid.authorization import Allow

from pyramid_grpc.decorators import config_grpc_call, config_grpc_service
from tests.services import greet_pb2, greet_pb2_grpc


class Context:
    def __init__(self, request):
        self.request = request

    __acl__ = [
        (Allow, "say::hellow", ["view", "edit"]),
    ]


class GreetServicer(greet_pb2_grpc.GreeterServicer):
    @config_grpc_call()
    def SayHello(self, request, context):
        return greet_pb2.HelloReply(message=f"Hi {request.name}! I'm {context.pyramid_request.host}")

    @config_grpc_call(permission="view", factory=Context)
    def SecureSayHello(self, request, context):
        return greet_pb2.HelloReply(message=f"Hi {request.name}! I'm {context.pyramid_request.host}")

    @config_grpc_call()
    def TransactionSayHello(self, request, context):
        return greet_pb2.HelloReply(message=f"Hi {request.name}! I'm {id(context.pyramid_request.dbsession)}")

    @config_grpc_call()
    def PersistedSayHello(self, request, context):
        from tests.models.greet import Greet

        greeting = context.pyramid_request.dbsession.query(Greet).first()

        return greet_pb2.HelloReply(message=f"Hi {request.name}! I'm {greeting.message}")


@config_grpc_service
def configure(server):
    greet_pb2_grpc.add_GreeterServicer_to_server(GreetServicer(), server)
