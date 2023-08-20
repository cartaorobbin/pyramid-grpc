from pyramid_grpc.decorators import get_services
from pyramid_grpc.interseptors.request import RequestInterseptor


def build_interceptors(pyramid_app):
    return [RequestInterseptor(pyramid_app)]


def configure_server(pyramid_app, grpc_server):
    for func in get_services():
        func(grpc_server, pyramid_app)


def serve(pyramid_app, grpc_server):
    configure_server(pyramid_app, grpc_server)
    port = pyramid_app.registry.settings.get("grpc.port", "50051")
    grpc_server.add_insecure_port(f"[::]:{port}")

    grpc_server.start()
    grpc_server.wait_for_termination()
