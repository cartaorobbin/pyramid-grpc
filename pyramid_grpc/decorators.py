from functools import wraps

import grpc
from pyramid.interfaces import (
    ISecurityPolicy,
)

services = []


def config_grpc_call(factory=None, permission=None):
    def decorator(function):
        @wraps(function)
        def wrapper(self, request, context):
            # If permission not set no need to perform any further check!
            if not permission:
                return function(self, request, context)

            pcontext = factory(context.pyramid_request) if factory else context.pyramid_request.context

            policy = context.pyramid_request.registry.queryUtility(ISecurityPolicy)
            if policy.permits(context.pyramid_request, pcontext, permission):
                return function(self, request, context)
            else:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Permission Denied")

        return wrapper

    return decorator


def config_grpc_service(function):
    services.append(function)

    def wrapper():
        pass

    return wrapper


def get_services():
    return services
