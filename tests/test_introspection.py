"""Tests for Pyramid application introspection."""

import pytest
from pyramid.config import Configurator

from pyramid_grpc.cli.utils.introspection import PyramidIntrospector, ViewInfo


def get_user_view(request):
    """Get a user by ID."""
    user_id = request.matchdict.get("id", "1")
    return {"id": user_id, "name": "John Doe", "email": "john@example.com"}


def create_user_view(request):
    """Create a new user."""
    return {"id": "123", "name": "New User", "created": True}


def update_user_view(request):
    """Update an existing user."""
    user_id = request.matchdict.get("id", "1")
    return {"id": user_id, "name": "Updated User", "updated": True}


def list_orders_view(request):
    """List all orders."""
    return [{"id": "1", "total": 100.00, "status": "pending"}, {"id": "2", "total": 250.50, "status": "completed"}]


def create_order_view(request):
    """Create a new order."""
    return {"id": "456", "total": 75.25, "status": "pending", "created": True}


def admin_stats_view(request):
    """Get admin statistics (override service name)."""
    return {"users": 1000, "orders": 2500, "revenue": 125000.00}


# Test views list: (view_func, route_name, route_pattern, request_method)
TEST_VIEWS = [
    (get_user_view, "get_user", "/api/users/{id}", "GET"),
    (create_user_view, "create_user", "/api/users", "POST"),
    (update_user_view, "update_user", "/api/users/{id}", "PUT"),
    (list_orders_view, "list_orders", "/api/orders", "GET"),
    (create_order_view, "create_order", "/api/orders", "POST"),
    (admin_stats_view, "admin_stats", "/api/admin/stats", "GET"),
]


@pytest.fixture
def simple_pyramid_app():
    """Create a lightweight Pyramid app with views for introspection testing."""

    def _create(views):
        with Configurator() as config:
            for view_func, route_name, route_pattern, request_method in views:
                config.add_route(route_name, route_pattern)
                config.add_view(view_func, route_name=route_name, request_method=request_method, renderer="json")
            return config.make_wsgi_app()

    return _create


def test_discover_views(simple_pyramid_app):
    """Test that views are discovered correctly."""
    app = simple_pyramid_app(TEST_VIEWS)
    introspector = PyramidIntrospector(app.registry)
    views = introspector.discover_views()

    assert len(views) == 6

    route_names = {view.route_name for view in views}
    expected_routes = {"get_user", "create_user", "update_user", "list_orders", "create_order", "admin_stats"}
    assert route_names == expected_routes

    user_view = next(view for view in views if view.route_name == "get_user")
    assert user_view.route_pattern == "/api/users/{id}"

    create_view = next(view for view in views if view.route_name == "create_user")
    assert create_view.route_pattern == "/api/users"


def test_discover_views_extracts_http_methods(simple_pyramid_app):
    """Test that HTTP methods are correctly extracted from view registrations."""
    app = simple_pyramid_app(TEST_VIEWS)
    introspector = PyramidIntrospector(app.registry)
    views = introspector.discover_views()

    get_user = next(view for view in views if view.route_name == "get_user")
    assert get_user.request_method == "GET"

    create_user = next(view for view in views if view.route_name == "create_user")
    assert create_user.request_method == "POST"

    update_user = next(view for view in views if view.route_name == "update_user")
    assert update_user.request_method == "PUT"


def test_discover_views_extracts_view_names(simple_pyramid_app):
    """Test that view callable names are correctly extracted."""
    app = simple_pyramid_app(TEST_VIEWS)
    introspector = PyramidIntrospector(app.registry)
    views = introspector.discover_views()

    get_user = next(view for view in views if view.route_name == "get_user")
    assert get_user.name == "get_user_view"

    list_orders = next(view for view in views if view.route_name == "list_orders")
    assert list_orders.name == "list_orders_view"


def test_discover_views_extracts_view_callables(simple_pyramid_app):
    """Test that view callables are preserved from introspection."""
    app = simple_pyramid_app(TEST_VIEWS)
    introspector = PyramidIntrospector(app.registry)
    views = introspector.discover_views()

    user_view = next(view for view in views if view.route_name == "get_user")
    assert user_view.view_callable is not None


def test_group_views_by_service(simple_pyramid_app):
    """Test that views are grouped into services correctly."""
    app = simple_pyramid_app(TEST_VIEWS)
    introspector = PyramidIntrospector(app.registry)
    views = introspector.discover_views()
    services = introspector.group_views_by_service(views)

    assert len(services) == 3

    service_names = {service.name for service in services}
    expected_services = {"UserService", "OrderService", "AdminService"}
    assert service_names == expected_services

    user_service = next(service for service in services if service.name == "UserService")
    assert len(user_service.views) == 3
    user_routes = {view.route_name for view in user_service.views}
    assert user_routes == {"get_user", "create_user", "update_user"}

    order_service = next(service for service in services if service.name == "OrderService")
    assert len(order_service.views) == 2
    order_routes = {view.route_name for view in order_service.views}
    assert order_routes == {"list_orders", "create_order"}

    admin_service = next(service for service in services if service.name == "AdminService")
    assert len(admin_service.views) == 1
    assert admin_service.views[0].route_name == "admin_stats"


def test_resource_name_extraction():
    """Test that resource names are correctly extracted from route names."""
    test_cases = [
        ("get_user", "UserService"),
        ("create_user", "UserService"),
        ("list_users", "UserService"),
        ("update_order", "OrderService"),
        ("admin_dashboard", "DashboardService"),
        ("api_v1_products", "ProductService"),
    ]

    with Configurator() as config:
        dummy_app = config.make_wsgi_app()
    introspector = PyramidIntrospector(dummy_app.registry)

    for route_name, expected_service in test_cases:
        view = ViewInfo(
            name="test_view",
            route_name=route_name,
            request_method="GET",
            view_callable=None,
            route_pattern="/test",
        )

        service_name = introspector._determine_service_name(view)
        assert (
            service_name == expected_service
        ), f"Route '{route_name}' should map to '{expected_service}', got '{service_name}'"


def test_view_info_extraction(simple_pyramid_app):
    """Test that ViewInfo objects are created correctly."""
    app = simple_pyramid_app(TEST_VIEWS)
    introspector = PyramidIntrospector(app.registry)
    views = introspector.discover_views()

    get_user = next(view for view in views if view.route_name == "get_user")

    assert get_user.name == "get_user_view"
    assert get_user.route_name == "get_user"
    assert get_user.route_pattern == "/api/users/{id}"
    assert get_user.request_method == "GET"


def test_empty_views_handling():
    """Test handling of applications with no custom views."""
    with Configurator() as config:
        empty_app = config.make_wsgi_app()

    introspector = PyramidIntrospector(empty_app.registry)
    views = introspector.discover_views()
    services = introspector.group_views_by_service(views)

    assert len(views) == 0
    assert len(services) == 0
