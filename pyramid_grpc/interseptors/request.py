from typing import Any, Callable

from grpc import ServicerContext
from grpc_interceptor import ServerInterceptor


def _get_authorization(meta, auth_header):
    for item in meta:
        if item.key.lower() == auth_header:
            return item.value


def _make_request(registry):
    from pyramid.scripting import prepare

    return prepare(registry=registry)["request"]


class RequestInterseptor(ServerInterceptor):
    extra_environ: dict | None = None

    def __init__(self, registry):
        self.pyramid_regsitry = registry

    def intercept(
        self,
        method: Callable,
        request: Any,
        context: ServicerContext,
        method_name: str,
    ) -> Any:
        pyramid_request = _make_request(self.pyramid_regsitry)

        pyramid_request.environ.update(self.extra_environ or {})

        auth = _get_authorization(
            context.invocation_metadata(), self.pyramid_regsitry.settings.get("grpc.auth_header", "authorization")
        )
        if auth:
            pyramid_request.environ.update({"HTTP_AUTHORIZATION": auth})

        context.pyramid_request = pyramid_request

        return method(request, context)
