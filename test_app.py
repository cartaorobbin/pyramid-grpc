"""Test Pyramid app for demonstrating generated code."""

from pyramid.config import Configurator


def get_user(request):
    """Get a specific user."""
    user_id = request.matchdict["id"]
    return {"user_id": user_id, "name": "John Doe", "email": "john@example.com"}


def create_user(request):
    """Create a new user."""
    data = request.json_body
    return {"user": "created", "id": 123, "name": data.get("name")}


def update_user(request):
    """Update a user."""
    user_id = request.matchdict["id"]
    data = request.json_body
    return {"user_id": user_id, "updated": True, "name": data.get("name")}


def list_orders(request):
    """Get all orders for a user."""
    return {"orders": [{"id": 1, "total": 100}, {"id": 2, "total": 250}]}


def create_order(request):
    """Create a new order."""
    data = request.json_body
    return {"order": "created", "id": 456, "total": data.get("total")}


def main(global_config, **settings):
    """Create and configure the Pyramid application."""
    config = Configurator(settings=settings)
    config.include("pyramid_grpc")

    # Add routes
    config.add_route("get_user", "/api/users/{id}")
    config.add_route("create_user", "/api/users")
    config.add_route("update_user", "/api/users/{id}")
    config.add_route("list_orders", "/api/orders")
    config.add_route("create_order", "/api/orders")

    # Add views
    config.add_view(get_user, route_name="get_user", request_method="GET", renderer="json")
    config.add_view(create_user, route_name="create_user", request_method="POST", renderer="json")
    config.add_view(update_user, route_name="update_user", request_method="PUT", renderer="json")
    config.add_view(list_orders, route_name="list_orders", request_method="GET", renderer="json")
    config.add_view(create_order, route_name="create_order", request_method="POST", renderer="json")

    return config.make_wsgi_app()
