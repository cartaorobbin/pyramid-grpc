from pyramid_grpc.decorators import config_grpc_service, config_grpc_call
from tests.services import greet_pb2_grpc
from tests.services import greet_pb2
from pyramid.authorization import Allow


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
    
    @config_grpc_call(permission='view', factory=Context)
    def SecureSayHello(self, request, context):
        return greet_pb2.HelloReply(message=f"Hi {request.name}! I'm {context.pyramid_request.host}")


@config_grpc_service
def configure(server, pyramid_app):
    greet_pb2_grpc.add_GreeterServicer_to_server(GreetServicer(), server)
