"""Proto file generation utilities."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from jinja2 import DictLoader, Environment

from .introspection import ServiceInfo, ViewInfo


@dataclass
class ProtoMethod:
    """Represents a gRPC method in a proto file."""

    name: str
    request_type: str
    response_type: str
    http_method: str
    route_pattern: str


@dataclass
class ProtoService:
    """Represents a gRPC service in a proto file."""

    name: str
    methods: List[ProtoMethod]


class ProtoGenerator:
    """Generates .proto files from Pyramid services."""

    # Proto file template for services (without messages)
    PROTO_TEMPLATE = """syntax = "proto3";

package {{ package_name }};

import "messages.proto";

// {{ service.name }} service
service {{ service.name }} {
{%- for method in service.methods %}
  // {{ method.http_method }} {{ method.route_pattern }}
  rpc {{ method.name }}(GenericRequest) returns (GenericResponse);
{%- endfor %}
}
"""

    # Proto file template for shared messages
    MESSAGES_TEMPLATE = """syntax = "proto3";

package {{ package_name }};

import "google/protobuf/any.proto";

// Generic request message for all methods
message GenericRequest {
  google.protobuf.Any data = 1;
  map<string, string> metadata = 2;
}

// Generic response message for all methods
message GenericResponse {
  google.protobuf.Any data = 1;
  map<string, string> metadata = 2;
  bool success = 3;
  string error_message = 4;
}
"""

    def __init__(self):
        """Initialize the proto generator."""
        self.env = Environment(
            loader=DictLoader({"service.proto": self.PROTO_TEMPLATE, "messages.proto": self.MESSAGES_TEMPLATE}),
            autoescape=True,
        )

    def convert_services_to_proto(self, services: List[ServiceInfo]) -> List[ProtoService]:
        """Convert ServiceInfo objects to ProtoService objects.

        Args:
            services: List of ServiceInfo objects from introspection

        Returns:
            List of ProtoService objects ready for proto generation
        """
        proto_services = []

        for service in services:
            methods = []
            for view in service.views:
                method = self._convert_view_to_method(view)
                methods.append(method)

            proto_service = ProtoService(name=service.name, methods=methods)
            proto_services.append(proto_service)

        return proto_services

    def _convert_view_to_method(self, view: ViewInfo) -> ProtoMethod:
        """Convert a ViewInfo to a ProtoMethod.

        Args:
            view: ViewInfo object from introspection

        Returns:
            ProtoMethod with gRPC-appropriate naming
        """
        # Convert HTTP method + route to gRPC method name
        method_name = self._generate_method_name(view)

        return ProtoMethod(
            name=method_name,
            request_type="GenericRequest",
            response_type="GenericResponse",
            http_method=view.request_method,
            route_pattern=view.route_pattern,
        )

    def _generate_method_name(self, view: ViewInfo) -> str:
        """Generate a gRPC method name from a Pyramid view.

        Args:
            view: ViewInfo object

        Returns:
            PascalCase gRPC method name

        Examples:
            GET /users/{id} -> GetUser
            POST /users -> CreateUser
            PUT /users/{id} -> UpdateUser
            DELETE /users/{id} -> DeleteUser
            GET /users -> ListUsers
        """
        http_method = (view.request_method or "GET").upper()
        route_pattern = view.route_pattern

        # Extract resource name from route pattern
        # /api/users/{id} -> users
        # /api/v1/products -> products
        parts = [p for p in route_pattern.split("/") if p and not p.startswith("{")]

        # Get the last meaningful part (usually the resource)
        resource = None
        for part in reversed(parts):
            if not part.startswith("api") and not part.startswith("v"):
                resource = part
                break

        if not resource:
            # Fallback to route name
            resource = view.route_name.split("_")[-1]

        # Convert to singular form for most operations
        singular_resource = self._singularize(resource)

        # Generate method name based on HTTP method
        if http_method == "GET":
            if "{" in route_pattern:  # GET /users/{id}
                return f"Get{singular_resource.title()}"
            else:  # GET /users
                return f"List{resource.title()}"
        elif http_method == "POST":
            return f"Create{singular_resource.title()}"
        elif http_method == "PUT" or http_method == "PATCH":
            return f"Update{singular_resource.title()}"
        elif http_method == "DELETE":
            return f"Delete{singular_resource.title()}"
        else:
            # Fallback for other methods
            return f"{http_method.title()}{singular_resource.title()}"

    def _singularize(self, word: str) -> str:
        """Simple singularization of English words.

        Args:
            word: Plural word

        Returns:
            Singular form (best effort)
        """
        if word.endswith("ies"):
            return word[:-3] + "y"
        elif word.endswith("es") and not word.endswith("ses"):
            return word[:-2]
        elif word.endswith("s") and not word.endswith("ss") and not word.endswith("us"):
            return word[:-1]
        else:
            return word

    def generate_proto_file(self, service: ProtoService, package_name: str = "pyramid_grpc") -> str:
        """Generate proto file content for a service.

        Args:
            service: ProtoService to generate proto for
            package_name: Proto package name

        Returns:
            Generated proto file content as string
        """
        template = self.env.get_template("service.proto")
        return template.render(service=service, package_name=package_name)

    def generate_messages_file(self, package_name: str = "pyramid_grpc") -> str:
        """Generate messages proto file content.

        Args:
            package_name: Proto package name

        Returns:
            Generated messages proto file content as string
        """
        template = self.env.get_template("messages.proto")
        return template.render(package_name=package_name)

    def write_proto_files(
        self, services: List[ProtoService], output_dir: Path, package_name: str = "pyramid_grpc"
    ) -> List[Path]:
        """Write proto files to disk.

        Args:
            services: List of ProtoService objects
            output_dir: Directory to write proto files
            package_name: Proto package name

        Returns:
            List of generated file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_files = []

        # Create package directory if needed
        if "/" in package_name:
            package_dir = output_dir / package_name.replace(".", "/")
            package_dir.mkdir(parents=True, exist_ok=True)
        else:
            package_dir = output_dir

        # Generate messages.proto file first (shared messages)
        if services:  # Only generate if we have services
            messages_file = package_dir / "messages.proto"
            messages_content = self.generate_messages_file(package_name)
            with open(messages_file, "w") as f:
                f.write(messages_content)
            generated_files.append(messages_file)

        # Generate service proto files
        for service in services:
            # Generate filename: UserService -> user_service.proto
            filename = self._service_name_to_filename(service.name)
            filepath = package_dir / filename

            # Generate proto content
            content = self.generate_proto_file(service, package_name)

            # Write to file
            with open(filepath, "w") as f:
                f.write(content)

            generated_files.append(filepath)

        return generated_files

    def _service_name_to_filename(self, service_name: str) -> str:
        """Convert service name to proto filename.

        Args:
            service_name: Service name (e.g., "UserService")

        Returns:
            Proto filename (e.g., "user_service.proto")
        """
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", service_name)
        filename = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
        return f"{filename}.proto"
