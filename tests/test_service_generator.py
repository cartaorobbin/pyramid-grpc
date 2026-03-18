"""Tests for service implementation generation."""

from pathlib import Path

import pytest
from pyramid.config import Configurator

from pyramid_grpc.cli.utils.introspection import ViewInfo
from pyramid_grpc.cli.utils.service_generator import ServiceGenerator, ServiceImplementation


# Test views for service generation
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
    generator = ServiceGenerator()

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
    generator = ServiceGenerator()

    result = generator._singularize(plural)
    assert result == expected_singular, f"Expected {expected_singular}, got {result} for {plural}"


@pytest.mark.parametrize(
    "service_name,expected_filename",
    [
        ("UserService", "user_service_impl.py"),
        ("OrderService", "order_service_impl.py"),
        ("AdminDashboardService", "admin_dashboard_service_impl.py"),
        ("APIService", "api_service_impl.py"),
    ],
)
def test_implementation_name_to_filename(service_name, expected_filename):
    """Test service implementation name to filename conversion."""
    generator = ServiceGenerator()

    result = generator._implementation_name_to_filename(service_name)
    assert result == expected_filename, f"Expected {expected_filename}, got {result} for {service_name}"


@pytest.mark.parametrize(
    "route_pattern,expected_matchdict",
    [
        ("/api/users/{id}", {"id": "data.get('id', '')"}),
        ("/api/users/{id}/posts/{post_id}", {"id": "data.get('id', '')", "post_id": "data.get('post_id', '')"}),
        ("/api/users", {}),
        (
            "/api/categories/{category}/items/{item_id}",
            {"category": "data.get('category', '')", "item_id": "data.get('item_id', '')"},
        ),
    ],
)
def test_extract_path_parameters(route_pattern, expected_matchdict):
    """Test path parameter extraction from route patterns."""
    generator = ServiceGenerator()

    result = generator._extract_path_parameters(route_pattern)
    assert result == expected_matchdict, f"Expected {expected_matchdict}, got {result} for {route_pattern}"


def test_convert_view_to_method():
    """Test conversion of ViewInfo to method definition."""
    generator = ServiceGenerator()

    view = ViewInfo(
        name="get_user_view",
        route_name="get_user",
        request_method="GET",
        view_callable=get_user_view,
        route_pattern="/api/users/{id}",
    )

    method = generator._convert_view_to_method(view)

    assert method["name"] == "GetUser"
    assert method["description"] == "GET /api/users/{id}"
    assert method["pyramid_view_name"] == "get_user_view"
    assert method["http_method"] == "GET"
    assert method["route_pattern"] == "/api/users/{id}"
    assert method["request_type"] == "GenericRequest"
    assert method["response_type"] == "GenericResponse"
    assert method["matchdict"] == {"id": "data.get('id', '')"}


def test_generate_imports():
    """Test import statement generation."""
    generator = ServiceGenerator()

    imports = generator._generate_imports("UserService")
    expected = [
        "import user_service_pb2",
        "import user_service_pb2_grpc",
        "import messages_pb2",
        "import messages_pb2_grpc",
    ]

    assert imports == expected


def test_convert_services_to_implementations(simple_pyramid_app):
    """Test conversion of ServiceInfo to ServiceImplementation."""
    app = simple_pyramid_app(TEST_VIEWS)

    # Create test services using introspector
    from pyramid_grpc.cli.utils.introspection import PyramidIntrospector

    introspector = PyramidIntrospector(app.registry)
    views = introspector.discover_views()
    services = introspector.group_views_by_service(views)

    # Convert to service implementations
    generator = ServiceGenerator()
    implementations = generator.convert_services_to_implementations(services)

    assert len(implementations) == 2  # UserService and OrderService

    # Check UserService implementation
    user_impl = next(impl for impl in implementations if impl.name == "UserService")
    assert user_impl.class_name == "UserServiceImpl"
    assert len(user_impl.methods) == 2  # GetUser and CreateUser

    method_names = {method["name"] for method in user_impl.methods}
    assert "GetUser" in method_names
    assert "CreateUser" in method_names

    # Check imports
    assert len(user_impl.imports) == 4
    assert "import user_service_pb2" in user_impl.imports
    assert "import messages_pb2" in user_impl.imports

    # Check OrderService implementation
    order_impl = next(impl for impl in implementations if impl.name == "OrderService")
    assert order_impl.class_name == "OrderServiceImpl"
    assert len(order_impl.methods) == 1  # ListOrders
    assert order_impl.methods[0]["name"] == "ListOrders"


def test_generate_service_file():
    """Test service implementation file content generation."""
    generator = ServiceGenerator()

    # Create a test implementation
    methods = [
        {
            "name": "GetUser",
            "description": "GET /api/users/{id}",
            "pyramid_view_name": "get_user_view",
            "http_method": "GET",
            "route_pattern": "/api/users/{id}",
            "request_type": "GenericRequest",
            "response_type": "GenericResponse",
            "matchdict": {"id": "data.get('id', '')"},
        },
        {
            "name": "CreateUser",
            "description": "POST /api/users",
            "pyramid_view_name": "create_user_view",
            "http_method": "POST",
            "route_pattern": "/api/users",
            "request_type": "GenericRequest",
            "response_type": "GenericResponse",
            "matchdict": {},
        },
    ]

    implementation = ServiceImplementation(
        name="UserService",
        class_name="UserServiceImpl",
        methods=methods,
        imports=["import user_service_pb2", "import messages_pb2"],
    )

    # Generate service content
    content = generator.generate_service_file(implementation)

    # Check that content contains expected elements
    assert "class UserServiceImpl:" in content
    assert "@grpc_service" in content
    assert "def GetUser(self, request, context):" in content
    assert "def CreateUser(self, request, context):" in content
    assert "import user_service_pb2" in content
    assert "import messages_pb2" in content
    assert "self.request.invoke_subrequest(subrequest)" in content
    assert "_extract_request_data" in content
    assert "_create_grpc_response" in content
    assert "_handle_http_exception" in content


def test_write_service_files(tmp_path):
    """Test writing service implementation files to disk."""
    generator = ServiceGenerator()

    # Create test implementations
    user_methods = [
        {
            "name": "GetUser",
            "description": "GET /api/users/{id}",
            "pyramid_view_name": "get_user_view",
            "http_method": "GET",
            "route_pattern": "/api/users/{id}",
            "request_type": "GenericRequest",
            "response_type": "GenericResponse",
            "matchdict": {"id": "data.get('id', '')"},
        },
    ]

    order_methods = [
        {
            "name": "ListOrders",
            "description": "GET /api/orders",
            "pyramid_view_name": "list_orders_view",
            "http_method": "GET",
            "route_pattern": "/api/orders",
            "request_type": "GenericRequest",
            "response_type": "GenericResponse",
            "matchdict": {},
        },
    ]

    implementations = [
        ServiceImplementation("UserService", "UserServiceImpl", user_methods, ["import user_service_pb2"]),
        ServiceImplementation("OrderService", "OrderServiceImpl", order_methods, ["import order_service_pb2"]),
    ]

    # Write service files
    output_dir = tmp_path / "services"
    generated_files = generator.write_service_files(implementations, output_dir)

    # Check that files were created
    assert len(generated_files) == 2
    assert output_dir.exists()

    # Check file names
    filenames = {f.name for f in generated_files}
    assert "user_service_impl.py" in filenames
    assert "order_service_impl.py" in filenames

    # Check file content
    user_service = output_dir / "user_service_impl.py"
    assert user_service.exists()

    content = user_service.read_text()
    assert "class UserServiceImpl:" in content
    assert "def GetUser(self, request, context):" in content
    assert "@grpc_service" in content


def test_empty_services_handling():
    """Test handling of empty services list."""
    generator = ServiceGenerator()

    implementations = generator.convert_services_to_implementations([])
    assert implementations == []

    generated_files = generator.write_service_files([], Path("./tmp_test"))
    assert generated_files == []


def test_service_implementation_dataclass():
    """Test ServiceImplementation dataclass."""
    implementation = ServiceImplementation(
        name="TestService", class_name="TestServiceImpl", methods=[{"name": "TestMethod"}], imports=["import test_pb2"]
    )

    assert implementation.name == "TestService"
    assert implementation.class_name == "TestServiceImpl"
    assert len(implementation.methods) == 1
    assert implementation.methods[0]["name"] == "TestMethod"
    assert implementation.imports == ["import test_pb2"]
