"""Tests for proto file compilation."""

from pathlib import Path

from pyramid_grpc.cli.utils.proto_compiler import CompilationResult, ProtoCompiler


def test_find_proto_files(tmp_path):
    """Test finding proto files in a directory."""
    compiler = ProtoCompiler()

    # Create test proto files
    proto_dir = tmp_path / "protos"
    proto_dir.mkdir()

    (proto_dir / "service1.proto").write_text('syntax = "proto3";')
    (proto_dir / "service2.proto").write_text('syntax = "proto3";')
    (proto_dir / "not_proto.txt").write_text("not a proto file")

    # Find proto files
    proto_files = compiler.find_proto_files(proto_dir)

    assert len(proto_files) == 2
    filenames = {f.name for f in proto_files}
    assert filenames == {"service1.proto", "service2.proto"}


def test_find_proto_files_empty_directory(tmp_path):
    """Test finding proto files in empty directory."""
    compiler = ProtoCompiler()

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    proto_files = compiler.find_proto_files(empty_dir)
    assert proto_files == []


def test_find_proto_files_nonexistent_directory(tmp_path):
    """Test finding proto files in nonexistent directory."""
    compiler = ProtoCompiler()

    nonexistent_dir = tmp_path / "nonexistent"

    proto_files = compiler.find_proto_files(nonexistent_dir)
    assert proto_files == []


def test_validate_proto_files(tmp_path):
    """Test proto file validation."""
    compiler = ProtoCompiler()

    # Create test files
    proto_dir = tmp_path / "protos"
    proto_dir.mkdir()

    valid_proto = proto_dir / "valid.proto"
    valid_proto.write_text('syntax = "proto3";')

    invalid_file = proto_dir / "invalid.txt"
    invalid_file.write_text("not proto")

    # Test validation
    assert compiler.validate_proto_files([valid_proto]) is True
    assert compiler.validate_proto_files([invalid_file]) is False
    assert compiler.validate_proto_files([]) is False

    # Test nonexistent file
    nonexistent = proto_dir / "nonexistent.proto"
    assert compiler.validate_proto_files([nonexistent]) is False


def test_compile_proto_files_no_files():
    """Test compilation with no proto files."""
    compiler = ProtoCompiler()

    result = compiler.compile_proto_files([], Path("./tmp_output"))

    assert result.success is False
    assert "No proto files provided" in result.error_message
    assert result.generated_files == []


def test_compile_proto_files_invalid_files(tmp_path):
    """Test compilation with invalid proto files."""
    compiler = ProtoCompiler()

    invalid_file = tmp_path / "invalid.txt"
    invalid_file.write_text("not proto")

    result = compiler.compile_proto_files([invalid_file], tmp_path / "output")

    assert result.success is False
    assert "Invalid proto files provided" in result.error_message
    assert result.generated_files == []


def test_compile_proto_files_success(tmp_path):
    """Test successful proto compilation."""
    compiler = ProtoCompiler()

    # Create a simple proto file
    proto_dir = tmp_path / "protos"
    proto_dir.mkdir()
    output_dir = tmp_path / "output"

    proto_content = """syntax = "proto3";

package test;

message TestRequest {
  string name = 1;
}

message TestResponse {
  string message = 1;
}

service TestService {
  rpc SayHello(TestRequest) returns (TestResponse);
}
"""

    proto_file = proto_dir / "test_service.proto"
    proto_file.write_text(proto_content)

    # Compile proto file
    result = compiler.compile_proto_files([proto_file], output_dir, proto_dir)

    # Check compilation result
    assert result.success is True
    assert result.error_message is None
    assert len(result.generated_files) == 2  # _pb2.py and _pb2_grpc.py

    # Check generated files exist
    pb2_file = output_dir / "test_service_pb2.py"
    grpc_file = output_dir / "test_service_pb2_grpc.py"

    assert pb2_file.exists()
    assert grpc_file.exists()

    # Check files are in result
    generated_names = {f.name for f in result.generated_files}
    assert "test_service_pb2.py" in generated_names
    assert "test_service_pb2_grpc.py" in generated_names


def test_compile_directory_success(tmp_path):
    """Test successful directory compilation."""
    compiler = ProtoCompiler()

    # Create proto directory with multiple files
    proto_dir = tmp_path / "protos"
    proto_dir.mkdir()
    output_dir = tmp_path / "output"

    # Create simple proto files
    for i in range(2):
        proto_content = f"""syntax = "proto3";

package test{i};

message TestRequest{i} {{
  string name = 1;
}}

message TestResponse{i} {{
  string message = 1;
}}

service TestService{i} {{
  rpc SayHello(TestRequest{i}) returns (TestResponse{i});
}}
"""
        proto_file = proto_dir / f"service{i}.proto"
        proto_file.write_text(proto_content)

    # Compile directory
    result = compiler.compile_directory(proto_dir, output_dir)

    # Check compilation result
    assert result.success is True
    assert result.error_message is None
    assert len(result.generated_files) == 4  # 2 services x 2 files each

    # Check all expected files exist
    expected_files = ["service0_pb2.py", "service0_pb2_grpc.py", "service1_pb2.py", "service1_pb2_grpc.py"]

    generated_names = {f.name for f in result.generated_files}
    for expected in expected_files:
        assert expected in generated_names


def test_compile_directory_no_proto_files(tmp_path):
    """Test directory compilation with no proto files."""
    compiler = ProtoCompiler()

    # Create empty directory
    proto_dir = tmp_path / "empty"
    proto_dir.mkdir()
    output_dir = tmp_path / "output"

    result = compiler.compile_directory(proto_dir, output_dir)

    assert result.success is False
    assert "No .proto files found" in result.error_message
    assert result.generated_files == []


def test_get_import_statements():
    """Test generation of import statements."""
    compiler = ProtoCompiler()

    # Create mock generated files
    generated_files = [
        Path("output/service1_pb2.py"),
        Path("output/service1_pb2_grpc.py"),
        Path("output/service2_pb2.py"),
        Path("output/service2_pb2_grpc.py"),
    ]

    # Test without base package
    imports = compiler.get_import_statements(generated_files)
    expected = [
        "import service1_pb2",
        "import service1_pb2_grpc",
        "import service2_pb2",
        "import service2_pb2_grpc",
    ]
    assert imports == expected

    # Test with base package
    imports = compiler.get_import_statements(generated_files, "myproject.generated")
    expected = [
        "import myproject.generated.service1_pb2",
        "import myproject.generated.service1_pb2_grpc",
        "import myproject.generated.service2_pb2",
        "import myproject.generated.service2_pb2_grpc",
    ]
    assert imports == expected


def test_get_import_statements_empty():
    """Test generation of import statements with no files."""
    compiler = ProtoCompiler()

    imports = compiler.get_import_statements([])
    assert imports == []


def test_compilation_result_dataclass():
    """Test CompilationResult dataclass."""
    # Test success result
    result = CompilationResult(success=True, generated_files=[Path("test.py")])
    assert result.success is True
    assert len(result.generated_files) == 1
    assert result.error_message is None

    # Test failure result
    result = CompilationResult(success=False, generated_files=[], error_message="Test error")
    assert result.success is False
    assert result.generated_files == []
    assert result.error_message == "Test error"
