"""Service implementation generation utilities."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import DictLoader, Environment

from .introspection import ServiceInfo, ViewInfo


@dataclass
class ServiceImplementation:
    """Represents a generated gRPC service implementation."""

    name: str
    class_name: str
    methods: List[Dict[str, Any]]
    imports: List[str]


class ServiceGenerator:
    """Generates gRPC service implementation code."""

    # Service implementation template
    SERVICE_TEMPLATE = """\"\"\"Generated gRPC service implementation for {{ service.name }}.

This file was automatically generated from Pyramid views.
It bridges gRPC calls to Pyramid subrequests.
\"\"\"

import json
import grpc
from google.protobuf import any_pb2
from pyramid.httpexceptions import HTTPException

# Import generated gRPC stubs
{% for import_stmt in service.imports %}
{{ import_stmt }}
{% endfor %}

# Import pyramid-grpc decorators
from pyramid_grpc.decorators import grpc_service


@grpc_service
class {{ service.class_name }}:
    \"\"\"{{ service.name }} gRPC service implementation.
    
    This service bridges gRPC calls to Pyramid views using subrequests.
    Each gRPC method corresponds to a Pyramid view.
    \"\"\"
    
    def __init__(self, request):
        \"\"\"Initialize the service with Pyramid request context.
        
        Args:
            request: Pyramid request object with authentication, registry, etc.
        \"\"\"
        self.request = request
{% for method in service.methods %}

    def {{ method.name }}(self, request, context):
        \"\"\"{{ method.description }}
        
        Bridges to Pyramid view: {{ method.pyramid_view_name }}
        Original route: {{ method.http_method }} {{ method.route_pattern }}
        
        Args:
            request: {{ method.request_type }} gRPC request
            context: gRPC service context
            
        Returns:
            {{ method.response_type }} gRPC response
        \"\"\"
        try:
            # Extract data from gRPC request
            request_data = self._extract_request_data(request)
            
            # Extract metadata (authentication, etc.)
            metadata = self._extract_metadata(context)
            
            # Create Pyramid subrequest
            subrequest = self._create_subrequest(
                method='{{ method.http_method }}',
                path='{{ method.route_pattern }}',
                data=request_data,
                metadata=metadata,
                matchdict={{ method.matchdict }}
            )
            
            # Execute Pyramid view via subrequest
            response = self.request.invoke_subrequest(subrequest)
            
            # Convert Pyramid response to gRPC response
            return self._create_grpc_response(response, context)
            
        except HTTPException as e:
            # Handle Pyramid HTTP exceptions
            return self._handle_http_exception(e, context)
        except Exception as e:
            # Handle unexpected errors
            return self._handle_error(e, context)
{% endfor %}

    def _extract_request_data(self, grpc_request):
        \"\"\"Extract data from gRPC request.
        
        Args:
            grpc_request: gRPC request message
            
        Returns:
            dict: Extracted request data
        \"\"\"
        try:
            if hasattr(grpc_request, 'data') and grpc_request.data:
                # Unpack Any message
                data = {}
                grpc_request.data.Unpack(data)
                return data
            return {}
        except Exception:
            return {}
    
    def _extract_metadata(self, context):
        \"\"\"Extract metadata from gRPC context.
        
        Args:
            context: gRPC service context
            
        Returns:
            dict: Extracted metadata
        \"\"\"
        metadata = {}
        
        # Extract authentication headers
        invocation_metadata = context.invocation_metadata()
        for key, value in invocation_metadata:
            if key.lower() in ['authorization', 'x-user-id', 'x-auth-token']:
                metadata[key] = value
        
        return metadata
    
    def _create_subrequest(self, method, path, data, metadata, matchdict):
        \"\"\"Create Pyramid subrequest.
        
        Args:
            method: HTTP method
            path: Request path
            data: Request data
            metadata: Request metadata
            matchdict: Route matchdict parameters
            
        Returns:
            Pyramid subrequest
        \"\"\"
        # Create subrequest with proper path and method
        subrequest = self.request.copy()
        subrequest.method = method
        subrequest.path = path
        
        # Set request data
        if method in ['POST', 'PUT', 'PATCH'] and data:
            subrequest.json_body = data
        
        # Set query parameters for GET requests
        if method == 'GET' and data:
            subrequest.GET = data
        
        # Set matchdict for path parameters
        if matchdict:
            subrequest.matchdict.update(matchdict)
        
        # Add authentication headers
        for key, value in metadata.items():
            subrequest.headers[key] = value
        
        return subrequest
    
    def _create_grpc_response(self, pyramid_response, context):
        \"\"\"Create gRPC response from Pyramid response.
        
        Args:
            pyramid_response: Pyramid response object
            context: gRPC service context
            
        Returns:
            gRPC response message
        \"\"\"
        # Import the response message class
        from messages_pb2 import GenericResponse
        
        response = GenericResponse()
        response.success = True
        
        # Pack response data
        if hasattr(pyramid_response, 'json') and pyramid_response.json:
            response_data = any_pb2.Any()
            response_data.Pack(json.dumps(pyramid_response.json).encode())
            response.data.CopyFrom(response_data)
        elif hasattr(pyramid_response, 'text') and pyramid_response.text:
            response_data = any_pb2.Any()
            response_data.Pack(pyramid_response.text.encode())
            response.data.CopyFrom(response_data)
        
        # Add response metadata
        if hasattr(pyramid_response, 'headers'):
            for key, value in pyramid_response.headers.items():
                response.metadata[key] = str(value)
        
        return response
    
    def _handle_http_exception(self, exc, context):
        \"\"\"Handle Pyramid HTTP exceptions.
        
        Args:
            exc: HTTPException
            context: gRPC service context
            
        Returns:
            gRPC error response
        \"\"\"
        from messages_pb2 import GenericResponse
        
        # Map HTTP status codes to gRPC status codes
        status_map = {
            400: grpc.StatusCode.INVALID_ARGUMENT,
            401: grpc.StatusCode.UNAUTHENTICATED,
            403: grpc.StatusCode.PERMISSION_DENIED,
            404: grpc.StatusCode.NOT_FOUND,
            409: grpc.StatusCode.ALREADY_EXISTS,
            500: grpc.StatusCode.INTERNAL,
        }
        
        grpc_status = status_map.get(exc.status_code, grpc.StatusCode.UNKNOWN)
        context.set_code(grpc_status)
        context.set_details(str(exc))
        
        response = GenericResponse()
        response.success = False
        response.error_message = str(exc)
        
        return response
    
    def _handle_error(self, exc, context):
        \"\"\"Handle unexpected errors.
        
        Args:
            exc: Exception
            context: gRPC service context
            
        Returns:
            gRPC error response
        \"\"\"
        from messages_pb2 import GenericResponse
        
        context.set_code(grpc.StatusCode.INTERNAL)
        context.set_details(f"Internal error: {str(exc)}")
        
        response = GenericResponse()
        response.success = False
        response.error_message = f"Internal error: {str(exc)}"
        
        return response
"""

    def __init__(self):
        """Initialize the service generator."""
        self.env = Environment(loader=DictLoader({"service.py": self.SERVICE_TEMPLATE}), autoescape=True)

    def convert_services_to_implementations(self, services: List[ServiceInfo]) -> List[ServiceImplementation]:
        """Convert ServiceInfo objects to ServiceImplementation objects.

        Args:
            services: List of ServiceInfo objects from introspection

        Returns:
            List of ServiceImplementation objects ready for code generation
        """
        implementations = []

        for service in services:
            methods = []
            for view in service.views:
                method = self._convert_view_to_method(view)
                methods.append(method)

            implementation = ServiceImplementation(
                name=service.name,
                class_name=f"{service.name}Impl",
                methods=methods,
                imports=self._generate_imports(service.name),
            )
            implementations.append(implementation)

        return implementations

    def _convert_view_to_method(self, view: ViewInfo) -> Dict[str, Any]:
        """Convert a ViewInfo to a method definition.

        Args:
            view: ViewInfo object from introspection

        Returns:
            Method definition dictionary
        """
        # Generate gRPC method name (same logic as proto generator)
        method_name = self._generate_method_name(view)

        # Extract path parameters for matchdict
        matchdict = self._extract_path_parameters(view.route_pattern)

        return {
            "name": method_name,
            "description": f"{view.request_method or 'ANY'} {view.route_pattern}",
            "pyramid_view_name": view.name,
            "http_method": view.request_method or "GET",
            "route_pattern": view.route_pattern,
            "request_type": "GenericRequest",
            "response_type": "GenericResponse",
            "matchdict": matchdict,
        }

    def _generate_method_name(self, view: ViewInfo) -> str:
        """Generate a gRPC method name from a Pyramid view.

        This uses the same logic as the proto generator to ensure consistency.
        """
        http_method = (view.request_method or "GET").upper()
        route_pattern = view.route_pattern

        # Extract resource name from route pattern
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
        """Simple singularization of English words."""
        if word.endswith("ies"):
            return word[:-3] + "y"
        elif word.endswith("es") and not word.endswith("ses"):
            return word[:-2]
        elif word.endswith("s") and not word.endswith("ss") and not word.endswith("us"):
            return word[:-1]
        else:
            return word

    def _extract_path_parameters(self, route_pattern: str) -> Dict[str, str]:
        """Extract path parameters from route pattern.

        Args:
            route_pattern: Route pattern like '/users/{id}'

        Returns:
            Dict of parameter names to placeholder values
        """
        params = re.findall(r"\{(\w+)\}", route_pattern)

        # Create matchdict with placeholder values
        matchdict = {}
        for param in params:
            # Use request data to populate actual values
            matchdict[param] = f"data.get('{param}', '')"

        return matchdict

    def _generate_imports(self, service_name: str) -> List[str]:
        """Generate import statements for a service.

        Args:
            service_name: Name of the service

        Returns:
            List of import statements
        """
        service_module = service_name.lower().replace("service", "_service")

        return [
            f"import {service_module}_pb2",
            f"import {service_module}_pb2_grpc",
            "import messages_pb2",
            "import messages_pb2_grpc",
        ]

    def generate_service_file(self, implementation: ServiceImplementation) -> str:
        """Generate service implementation file content.

        Args:
            implementation: ServiceImplementation to generate code for

        Returns:
            Generated Python code as string
        """
        template = self.env.get_template("service.py")
        return template.render(service=implementation)

    def write_service_files(self, implementations: List[ServiceImplementation], output_dir: Path) -> List[Path]:
        """Write service implementation files to disk.

        Args:
            implementations: List of ServiceImplementation objects
            output_dir: Directory to write service files

        Returns:
            List of generated file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_files = []

        for implementation in implementations:
            # Generate filename: UserService -> user_service_impl.py
            filename = self._implementation_name_to_filename(implementation.name)
            filepath = output_dir / filename

            # Generate service content
            content = self.generate_service_file(implementation)

            # Write to file
            with open(filepath, "w") as f:
                f.write(content)

            generated_files.append(filepath)

        return generated_files

    def _implementation_name_to_filename(self, service_name: str) -> str:
        """Convert service name to implementation filename.

        Args:
            service_name: Service name (e.g., "UserService")

        Returns:
            Implementation filename (e.g., "user_service_impl.py")
        """
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", service_name)
        filename = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
        return f"{filename}_impl.py"
