from typing import Any, Callable

from grpc import ServicerContext
from grpc_interceptor import ServerInterceptor


class TransactionInterseptor(ServerInterceptor):
    def __init__(self, registry, extra_environ=None):
        self.registry = registry
        self.extra_environ = extra_environ or {}

    def intercept(
        self,
        method: Callable,
        request: Any,
        context: ServicerContext,
        method_name: str,
    ) -> Any:
        context.pyramid_request.tm.begin()
        try:
            response = method(request, context)
            context.pyramid_request.tm.commit()
        except Exception as e:
            context.pyramid_request.tm.abort()
            raise e
        return response
