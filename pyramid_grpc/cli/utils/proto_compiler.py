"""Proto file compilation utilities."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class CompilationResult:
    """Result of proto compilation."""

    success: bool
    generated_files: List[Path]
    error_message: Optional[str] = None


class ProtoCompiler:
    """Compiles .proto files to Python stubs using grpc_tools.protoc."""

    def __init__(self):
        """Initialize the proto compiler."""
        pass

    def find_proto_files(self, proto_dir: Path) -> List[Path]:
        """Find all .proto files in a directory.

        Args:
            proto_dir: Directory containing .proto files

        Returns:
            List of .proto file paths
        """
        if not proto_dir.exists():
            return []

        proto_files = []
        for proto_file in proto_dir.glob("*.proto"):
            if proto_file.is_file():
                proto_files.append(proto_file)

        return sorted(proto_files)

    def validate_proto_files(self, proto_files: List[Path]) -> bool:
        """Validate that proto files exist and are readable.

        Args:
            proto_files: List of proto file paths

        Returns:
            True if all files are valid, False otherwise
        """
        if not proto_files:
            return False

        for proto_file in proto_files:
            if not proto_file.exists():
                return False
            if not proto_file.is_file():
                return False
            if proto_file.suffix != ".proto":
                return False

        return True

    def compile_proto_files(
        self, proto_files: List[Path], output_dir: Path, proto_path: Optional[Path] = None
    ) -> CompilationResult:
        """Compile proto files to Python stubs.

        Args:
            proto_files: List of .proto files to compile
            output_dir: Directory to output generated Python files
            proto_path: Base path for proto imports (defaults to parent of first proto file)

        Returns:
            CompilationResult with success status and generated files
        """
        if not proto_files:
            return CompilationResult(success=False, generated_files=[], error_message="No proto files provided")

        if not self.validate_proto_files(proto_files):
            return CompilationResult(success=False, generated_files=[], error_message="Invalid proto files provided")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine proto path (directory containing proto files)
        if proto_path is None:
            proto_path = proto_files[0].parent

        try:
            # Import grpc_tools.protoc
            import grpc_tools
            from grpc_tools import protoc

            # Get the path to grpc_tools proto files (includes google/protobuf/*.proto)
            grpc_tools_path = Path(grpc_tools.__file__).parent / "_proto"

            # Build protoc arguments
            args = [
                "grpc_tools.protoc",  # Program name
                f"--proto_path={proto_path}",  # Proto import path
                f"--proto_path={grpc_tools_path}",  # Standard protobuf files
                f"--python_out={output_dir}",  # Python message classes output
                f"--grpc_python_out={output_dir}",  # Python gRPC stubs output
            ]

            # Add proto files
            for proto_file in proto_files:
                # Use relative path from proto_path
                relative_path = proto_file.relative_to(proto_path)
                args.append(str(relative_path))

            # Run protoc
            result = protoc.main(args)

            # Find generated files
            generated_files = self._find_generated_files(proto_files, output_dir, proto_path)

            if result != 0:
                return CompilationResult(
                    success=False,
                    generated_files=[],
                    error_message=f"protoc compilation failed with exit code {result}",
                )
            else:
                return CompilationResult(success=True, generated_files=generated_files)

        except ImportError:
            return CompilationResult(
                success=False,
                generated_files=[],
                error_message="grpcio-tools not installed. Run: pip install grpcio-tools",
            )
        except Exception as e:
            return CompilationResult(success=False, generated_files=[], error_message=f"Compilation failed: {str(e)}")

    def _find_generated_files(self, proto_files: List[Path], output_dir: Path, proto_path: Path) -> List[Path]:
        """Find generated Python files after compilation.

        Args:
            proto_files: Original proto files
            output_dir: Output directory
            proto_path: Proto import path

        Returns:
            List of generated Python file paths
        """
        generated_files = []

        for proto_file in proto_files:
            # Get relative path and convert to Python module path
            relative_path = proto_file.relative_to(proto_path)
            stem = relative_path.stem  # filename without .proto extension

            # Expected generated files:
            # service.proto -> service_pb2.py (messages)
            # service.proto -> service_pb2_grpc.py (gRPC stubs)

            pb2_file = output_dir / f"{stem}_pb2.py"
            grpc_file = output_dir / f"{stem}_pb2_grpc.py"

            if pb2_file.exists():
                generated_files.append(pb2_file)
            if grpc_file.exists():
                generated_files.append(grpc_file)

        return generated_files

    def compile_directory(self, proto_dir: Path, output_dir: Path) -> CompilationResult:
        """Compile all proto files in a directory.

        Args:
            proto_dir: Directory containing .proto files
            output_dir: Directory to output generated Python files

        Returns:
            CompilationResult with success status and generated files
        """
        proto_files = self.find_proto_files(proto_dir)

        if not proto_files:
            return CompilationResult(
                success=False, generated_files=[], error_message=f"No .proto files found in {proto_dir}"
            )

        return self.compile_proto_files(proto_files, output_dir, proto_dir)

    def get_import_statements(self, generated_files: List[Path], base_package: str = "") -> List[str]:
        """Generate import statements for generated Python files.

        Args:
            generated_files: List of generated Python file paths
            base_package: Base package name for imports

        Returns:
            List of import statements
        """
        imports = []

        for file_path in generated_files:
            stem = file_path.stem  # filename without .py extension

            module_name = f"{base_package}.{stem}" if base_package else stem

            if stem.endswith("_pb2"):
                # Message classes
                imports.append(f"import {module_name}")
            elif stem.endswith("_pb2_grpc"):
                # gRPC service stubs
                imports.append(f"import {module_name}")

        return sorted(imports)
