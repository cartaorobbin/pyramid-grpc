"""Pyramid application introspection utilities.

Uses pyramid-introspector for robust route/view discovery, then adds
gRPC-specific service grouping logic on top.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pyramid.registry import Registry
from pyramid_introspector import PyramidIntrospector as LibIntrospector
from pyramid_introspector import RouteInfo
from pyramid_introspector import ViewInfo as LibViewInfo


@dataclass
class ViewInfo:
    """Flattened view information for gRPC service generation.

    Combines route-level and view-level data from pyramid-introspector
    into a single object suitable for proto/service generation.
    """

    name: str
    route_name: str
    request_method: str
    view_callable: Any
    route_pattern: str
    permission: Optional[str] = None
    grpc_service: Optional[str] = None


@dataclass
class ServiceInfo:
    """Information about a gRPC service to be generated."""

    name: str
    views: List[ViewInfo]
    package_name: str = "grpc_services"


class PyramidIntrospector:
    """Introspects Pyramid applications to discover views and routes.

    Delegates route/view discovery to pyramid-introspector and adds
    gRPC service grouping logic.
    """

    def __init__(self, registry: Registry, security_parameter: str = "mcp_security"):
        """Initialize the introspector.

        Args:
            registry: Pyramid registry with introspection data
            security_parameter: Name of the security parameter to look for
        """
        self.registry = registry
        self.security_parameter = security_parameter
        self._introspector = LibIntrospector(registry)

    def discover_views(self) -> List[ViewInfo]:
        """Discover all views in the Pyramid application.

        Returns:
            List of ViewInfo objects representing discovered views
        """
        routes = self._introspector.introspect()
        views = []

        for route in routes:
            for lib_view in route.views:
                view = self._convert_view(route, lib_view)
                views.append(view)

        return views

    def group_views_by_service(self, views: List[ViewInfo]) -> List[ServiceInfo]:
        """Group views by gRPC service based on resource names.

        Args:
            views: List of discovered views

        Returns:
            List of ServiceInfo objects representing gRPC services to generate
        """
        service_groups: Dict[str, List[ViewInfo]] = {}

        for view in views:
            service_name = self._determine_service_name(view)

            if service_name not in service_groups:
                service_groups[service_name] = []

            service_groups[service_name].append(view)

        return [ServiceInfo(name=name, views=group_views) for name, group_views in service_groups.items()]

    def _convert_view(self, route: RouteInfo, lib_view: LibViewInfo) -> ViewInfo:
        """Convert pyramid-introspector models to our ViewInfo.

        Args:
            route: RouteInfo from pyramid-introspector
            lib_view: ViewInfo from pyramid-introspector

        Returns:
            Our ViewInfo with flattened route + view data
        """
        view_name = self._extract_view_name(lib_view)

        return ViewInfo(
            name=view_name,
            route_name=route.name,
            request_method=lib_view.method,
            view_callable=lib_view.callable,
            route_pattern=route.pattern,
            permission=lib_view.permission,
        )

    def _extract_view_name(self, lib_view: LibViewInfo) -> str:
        """Extract a human-readable view name from the library's ViewInfo."""
        if lib_view.callable is not None:
            callable_obj = lib_view.callable
            if hasattr(callable_obj, "__name__"):
                return callable_obj.__name__
            if hasattr(callable_obj, "__class__"):
                return callable_obj.__class__.__name__
        return "unknown"

    def _determine_service_name(self, view: ViewInfo) -> str:
        """Determine the gRPC service name for a view.

        Args:
            view: ViewInfo object

        Returns:
            Service name (e.g., "UserService")
        """
        if view.grpc_service:
            return self._format_service_name(view.grpc_service)

        if view.route_name:
            resource_name = self._extract_resource_from_route_name(view.route_name)
            return self._format_service_name(resource_name)

        if view.name:
            resource_name = self._extract_resource_from_route_name(view.name)
            return self._format_service_name(resource_name)

        return "ApiService"

    def _extract_resource_from_route_name(self, route_name: str) -> str:
        """Extract resource name from route name.

        Examples:
            get_user -> User
            create_order -> Order
            api_v1_products -> Product

        Args:
            route_name: Route name to parse

        Returns:
            Resource name
        """
        cleaned = route_name

        # Remove action prefixes
        cleaned = re.sub(r"^(get_|create_|update_|delete_|list_)", "", cleaned)

        # Remove API version prefixes
        cleaned = re.sub(r"^(api_|v\d+_)", "", cleaned)

        parts = cleaned.split("_")
        if parts:
            resource = parts[-1]

            if resource in ("stats", "info", "data", "list") and len(parts) > 1:
                resource = parts[-2]

            # Basic singularization
            if resource.endswith("s") and len(resource) > 3:
                resource = resource[:-1]
            return resource

        return "Api"

    def _format_service_name(self, resource_name: str) -> str:
        """Format resource name as a proper gRPC service name.

        Args:
            resource_name: Raw resource name

        Returns:
            Formatted service name (e.g., "UserService")
        """
        formatted = resource_name.capitalize()
        if not formatted.endswith("Service"):
            formatted += "Service"
        return formatted
