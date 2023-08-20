from typing import Any, Callable
from grpc import ServicerContext, HandlerCallDetails
from pyramid.scripting import prepare
from grpc_interceptor import ServerInterceptor


class TransactionInterseptor(ServerInterceptor):
    def __init__(self, pyramid_app, extra_environ=None):
        self.pyramid_app = pyramid_app
        # self.session = pyramid_app.registry["dbsession_factory"]()

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
