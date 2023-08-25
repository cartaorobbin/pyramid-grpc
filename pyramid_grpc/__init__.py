import inspect
from concurrent import futures
from functools import partial

import grpc
from grpc_interceptor import ServerInterceptor

from pyramid_grpc.decorators import get_services


def add_grpc_interceptors(config, interceptor: ServerInterceptor):
    def register():
        if inspect.isclass(interceptor):
            interceptor = interceptor(config.registry)

        config.registry.grpc_interceptors.append(interceptor)

    config.action("pgrcp_interseptors", register, order=90)


def configure_grpc(config, server: grpc.Server):
    def register(server: grpc.Server = None):
        max_workers = config.registry.settings.get("grpc.max_workers", 10)

        server = server or grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers),
            interceptors=config.registry.grpc_interceptors,
        )

        port = config.registry.settings.get("grpc.port", "50051")
        server.add_insecure_port(f"[::]:{port}")

        config.registry.grpc_server = server

        for func in get_services():
            func(server)

    config.action("pgrcp", partial(register, server), order=99)


def includeme(config):
    config.registry.grpc_server_interceptors = []

    config.add_directive("configure_grpc", configure_grpc)

    config.add_directive("configure_grpc_interceptors", add_grpc_interceptors)
