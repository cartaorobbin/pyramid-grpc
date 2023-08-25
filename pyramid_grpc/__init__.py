import inspect
import logging
from concurrent import futures
from functools import partial

import grpc
from grpc_interceptor import ServerInterceptor

from pyramid_grpc.decorators import get_services
from pyramid_grpc.interseptors.request import RequestInterseptor
from pyramid_grpc.interseptors.transaction import TransactionInterseptor

logger = logging.getLogger(__name__)

ACTION_DEFAUTL_ORDER = 100
ACTION_ADD_INSPECTOR_ORDER = 90
ACTION_CONFIGURE_SERVER_ORDER = 80


def register_interseptor(config, interceptor: ServerInterceptor, position: str = "bottom"):
    if inspect.isclass(interceptor):
        interceptor = interceptor(config.registry)

    if not hasattr(config.registry, "grpc_interceptors"):
        config.registry.grpc_interceptors = []

    for interseptor in config.registry.grpc_interceptors:
        if interseptor.__class__ == interceptor.__class__:
            logger.warning(f"Interseptor {interseptor.__class__} already registered. Keeping both instances.")

    if position == "top":
        config.registry.grpc_interceptors.insert(0, interceptor)
    else:
        config.registry.grpc_interceptors.append(interceptor)


def add_grpc_interceptors(config, interceptor: ServerInterceptor, position: str = "bottom"):
    id_ = id(interceptor)

    config.action(
        f"pgrcp_interseptors_{id_}",
        partial(register_interseptor, config=config, interceptor=interceptor, position=position),
        order=ACTION_ADD_INSPECTOR_ORDER,
    )


def register_server(config, server: grpc.Server = None):
    if hasattr(config.registry, "grpc_server"):
        return

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


def configure_grpc(config, server: grpc.Server = None):
    config.action(
        "pgrcp_server", partial(register_server, config=config, server=server), order=ACTION_CONFIGURE_SERVER_ORDER
    )


def default_config(config):
    register_interseptor(config, RequestInterseptor(config.registry), position="top")

    if config.registry.settings.get("tm.manager_hook"):
        register_interseptor(config, TransactionInterseptor(config.registry))
    register_server(config)


def includeme(config):
    config.registry.grpc_server_interceptors = []

    config.add_directive("configure_grpc", configure_grpc)

    config.add_directive("add_grpc_interceptors", add_grpc_interceptors)

    config.action("pgrcp_default", partial(default_config, config), order=ACTION_DEFAUTL_ORDER)
