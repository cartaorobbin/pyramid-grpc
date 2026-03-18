"""Proto compilation command."""

from pathlib import Path

import click

from pyramid_grpc.cli.utils.proto_compiler import ProtoCompiler


@click.command("compile")
@click.option(
    "--proto-dir",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Directory containing .proto files to compile",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory to output compiled Python gRPC stubs",
)
@click.pass_context
def compile_cmd(ctx: click.Context, proto_dir: Path, output_dir: Path) -> None:
    """Compile .proto files to Python gRPC stubs.

    This command uses grpc_tools.protoc to compile Protocol Buffer
    files into Python gRPC stubs (*_pb2.py and *_pb2_grpc.py files).

    Example:
        grpc-generate --ini development.ini compile --proto-dir ./protos --output-dir ./generated
    """
    click.echo(f"📄 Proto files directory: {proto_dir}")
    click.echo(f"📁 Output directory: {output_dir}")

    try:
        # Initialize compiler
        compiler = ProtoCompiler()

        # Find proto files
        click.echo("🔍 Finding .proto files...")
        proto_files = compiler.find_proto_files(proto_dir)

        if not proto_files:
            click.echo(f"❌ No .proto files found in {proto_dir}")
            raise click.ClickException(f"No .proto files found in {proto_dir}")

        click.echo(f"✅ Found {len(proto_files)} proto files:")
        for proto_file in proto_files:
            click.echo(f"   📄 {proto_file.name}")

        # Compile proto files
        click.echo("⚙️  Compiling proto files...")
        result = compiler.compile_directory(proto_dir, output_dir)

        if not result.success:
            click.echo(f"❌ Compilation failed: {result.error_message}")
            raise click.ClickException(result.error_message)

        # Show results
        click.echo(f"✅ Compilation successful! Generated {len(result.generated_files)} files:")
        for generated_file in result.generated_files:
            click.echo(f"   🐍 {generated_file}")

        # Show import statements
        if result.generated_files:
            click.echo("📋 Import statements for generated files:")
            imports = compiler.get_import_statements(result.generated_files)
            for import_stmt in imports:
                click.echo(f"   {import_stmt}")

        click.echo("🎉 Proto compilation complete!")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.ClickException(str(e)) from e
