"""Tests for proto file generation."""

from pathlib import Path

import pytest
from pyramid.config import Configurator

from pyramid_grpc.cli.utils.introspection import ViewInfo
from pyramid_grpc.cli.utils.proto_generator import ProtoGenerator, ProtoMethod, ProtoService


# Test views for proto generation
def get_user_view(request):
    return {"user_id": request.matchdict["id"]}


def create_user_view(request):
    return {"user": "created"}


def list_orders_view(request):
    return {"orders": []}


TEST_VIEWS = [
    (get_user_view, "get_user", "/api/users/{id}", "GET"),
    (create_user_view, "create_user", "/api/users", "POST"),
    (list_orders_view, "list_orders", "/api/orders", "GET"),
]


@pytest.fixture
def simple_pyramid_app():
    """Create a lightweight Pyramid app with views for testing."""

    def _create(views):
        with Configurator() as config:
            for view_func, route_name, route_pattern, request_method in views:
                config.add_route(route_name, route_pattern)
                config.add_view(view_func, route_name=route_name, request_method=request_method, renderer="json")
            return config.make_wsgi_app()

    return _create


@pytest.mark.parametrize(
    "http_method,route_pattern,route_name,expected_method_name",
    [
        ("GET", "/api/users/{id}", "get_user", "GetUser"),
        ("GET", "/api/users", "list_users", "ListUsers"),
        ("POST", "/api/users", "create_user", "CreateUser"),
        ("PUT", "/api/users/{id}", "update_user", "UpdateUser"),
        ("DELETE", "/api/users/{id}", "delete_user", "DeleteUser"),
        ("GET", "/api/v1/products/{id}", "get_product", "GetProduct"),
        ("GET", "/api/orders", "list_orders", "ListOrders"),
    ],
)
def test_method_name_generation(http_method, route_pattern, route_name, expected_method_name):
    """Test gRPC method name generation from HTTP routes."""
    generator = ProtoGenerator()

    view = ViewInfo(
        name=f"{route_name}_view",
        route_name=route_name,
        request_method=http_method,
        view_callable=None,
        route_pattern=route_pattern,
    )

    method_name = generator._generate_method_name(view)
    assert (
        method_name == expected_method_name
    ), f"Expected {expected_method_name}, got {method_name} for {http_method} {route_pattern}"


@pytest.mark.parametrize(
    "plural,expected_singular",
    [
        ("users", "user"),
        ("orders", "order"),
        ("categories", "category"),
        ("companies", "company"),
        ("boxes", "box"),
        ("user", "user"),  # Already singular
        ("status", "status"),  # Ends with 's' but should not be singularized
    ],
)
def test_singularization(plural, expected_singular):
    """Test word singularization logic."""
    generator = ProtoGenerator()

    result = generator._singularize(plural)
    assert result == expected_singular, f"Expected {expected_singular}, got {result} for {plural}"


@pytest.mark.parametrize(
    "service_name,expected_filename",
    [
        ("UserService", "user_service.proto"),
        ("OrderService", "order_service.proto"),
        ("AdminDashboardService", "admin_dashboard_service.proto"),
        ("APIService", "api_service.proto"),  # Fixed: should be api_service.proto
    ],
)
def test_service_name_to_filename(service_name, expected_filename):
    """Test service name to filename conversion."""
    generator = ProtoGenerator()

    result = generator._service_name_to_filename(service_name)
    assert result == expected_filename, f"Expected {expected_filename}, got {result} for {service_name}"


def test_convert_view_to_method():
    """Test conversion of ViewInfo to ProtoMethod."""
    generator = ProtoGenerator()

    view = ViewInfo(
        name="get_user_view",
        route_name="get_user",
        request_method="GET",
        view_callable=get_user_view,
        route_pattern="/api/users/{id}",
    )

    method = generator._convert_view_to_method(view)

    assert method.name == "GetUser"
    assert method.request_type == "GenericRequest"
    assert method.response_type == "GenericResponse"
    assert method.http_method == "GET"
    assert method.route_pattern == "/api/users/{id}"


def test_convert_services_to_proto(simple_pyramid_app):
    """Test conversion of ServiceInfo to ProtoService."""
    app = simple_pyramid_app(TEST_VIEWS)

    # Create test services using introspector
    from pyramid_grpc.cli.utils.introspection import PyramidIntrospector

    introspector = PyramidIntrospector(app.registry)
    views = introspector.discover_views()
    services = introspector.group_views_by_service(views)

    # Convert to proto services
    generator = ProtoGenerator()
    proto_services = generator.convert_services_to_proto(services)

    assert len(proto_services) == 2  # UserService and OrderService

    # Check UserService
    user_service = next(s for s in proto_services if s.name == "UserService")
    assert len(user_service.methods) == 2  # GetUser and CreateUser

    method_names = {method.name for method in user_service.methods}
    assert "GetUser" in method_names
    assert "CreateUser" in method_names

    # Check OrderService
    order_service = next(s for s in proto_services if s.name == "OrderService")
    assert len(order_service.methods) == 1  # ListOrders
    assert order_service.methods[0].name == "ListOrders"


def test_generate_proto_file():
    """Test proto file content generation."""
    generator = ProtoGenerator()

    # Create a test service
    methods = [
        ProtoMethod(
            name="GetUser",
            request_type="GenericRequest",
            response_type="GenericResponse",
            http_method="GET",
            route_pattern="/api/users/{id}",
        ),
        ProtoMethod(
            name="CreateUser",
            request_type="GenericRequest",
            response_type="GenericResponse",
            http_method="POST",
            route_pattern="/api/users",
        ),
    ]

    service = ProtoService(name="UserService", methods=methods)

    # Generate proto content
    content = generator.generate_proto_file(service, package_name="test_package")

    # Check that content contains expected elements
    assert 'syntax = "proto3";' in content
    assert "package test_package;" in content
    assert 'import "messages.proto";' in content
    assert "service UserService" in content
    assert "rpc GetUser(GenericRequest) returns (GenericResponse);" in content
    assert "rpc CreateUser(GenericRequest) returns (GenericResponse);" in content
    assert "// GET /api/users/{id}" in content
    assert "// POST /api/users" in content

    # Should NOT contain message definitions (they're in messages.proto now)
    assert "message GenericRequest" not in content
    assert "message GenericResponse" not in content


def test_generate_messages_file():
    """Test messages proto file content generation."""
    generator = ProtoGenerator()

    # Generate messages content
    content = generator.generate_messages_file(package_name="test_package")

    # Check that content contains expected elements
    assert 'syntax = "proto3";' in content
    assert "package test_package;" in content
    assert 'import "google/protobuf/any.proto";' in content
    assert "message GenericRequest" in content
    assert "message GenericResponse" in content
    assert "google.protobuf.Any data = 1;" in content
    assert "map<string, string> metadata = 2;" in content
    assert "bool success = 3;" in content
    assert "string error_message = 4;" in content


def test_write_proto_files(tmp_path):
    """Test writing proto files to disk."""
    generator = ProtoGenerator()

    # Create test services
    user_methods = [
        ProtoMethod("GetUser", "GenericRequest", "GenericResponse", "GET", "/api/users/{id}"),
        ProtoMethod("CreateUser", "GenericRequest", "GenericResponse", "POST", "/api/users"),
    ]

    order_methods = [
        ProtoMethod("ListOrders", "GenericRequest", "GenericResponse", "GET", "/api/orders"),
    ]

    services = [
        ProtoService("UserService", user_methods),
        ProtoService("OrderService", order_methods),
    ]

    # Write proto files
    output_dir = tmp_path / "protos"
    generated_files = generator.write_proto_files(services, output_dir)

    # Check that files were created (should include messages.proto + 2 service files)
    assert len(generated_files) == 3
    assert output_dir.exists()

    # Check file names
    filenames = {f.name for f in generated_files}
    assert "messages.proto" in filenames
    assert "user_service.proto" in filenames
    assert "order_service.proto" in filenames

    # Check messages.proto content
    messages_proto = output_dir / "messages.proto"
    assert messages_proto.exists()
    messages_content = messages_proto.read_text()
    assert "message GenericRequest" in messages_content
    assert "message GenericResponse" in messages_content
    assert "google.protobuf.Any" in messages_content

    # Check service proto content
    user_proto = output_dir / "user_service.proto"
    assert user_proto.exists()

    content = user_proto.read_text()
    assert "service UserService" in content
    assert "rpc GetUser" in content
    assert "rpc CreateUser" in content
    assert 'import "messages.proto"' in content


def test_empty_services_handling():
    """Test handling of empty services list."""
    generator = ProtoGenerator()

    proto_services = generator.convert_services_to_proto([])
    assert proto_services == []

    generated_files = generator.write_proto_files([], Path("./tmp_test"))
    assert generated_files == []
