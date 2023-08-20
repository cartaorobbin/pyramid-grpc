import re
from typing import Any, Callable
from grpc import ServicerContext, HandlerCallDetails

from grpc_interceptor import ServerInterceptor


def _get_authorization(meta):
    for item in meta:
        if item.key.lower() == 'authorization':
            return item.value

def _make_request(registry):
    from pyramid.scripting import prepare, _make_request as mk
    return prepare(registry=registry)['request']


class RequestInterseptor(ServerInterceptor):
    def __init__(self, pyramid_app, extra_environ=None):
        self.pyramid_app = pyramid_app
        self.extra_environ = extra_environ or {}

    def intercept(
        self,
        method: Callable,
        request: Any,
        context: ServicerContext,
        method_name: str,
    ) -> Any:
        
        pyramid_request = _make_request(self.pyramid_app.registry)
        pyramid_request.environ.update(self.extra_environ)
        auth = _get_authorization(context.invocation_metadata())
        if auth:
            pyramid_request.environ.update({'HTTP_AUTHORIZATION': auth})
        
        context.pyramid_request = pyramid_request

        return method(request, context)
