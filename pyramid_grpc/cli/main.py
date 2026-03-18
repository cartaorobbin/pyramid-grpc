"""Main CLI entry point for grpc-generate command."""

import logging

import click

from pyramid_grpc.cli.commands.compile import compile_cmd
from pyramid_grpc.cli.commands.implement import implement
from pyramid_grpc.cli.commands.proto import proto
from pyramid_grpc.cli.utils.pyramid_loader import PyramidContext, bootstrap_pyramid_app

logger = logging.getLogger(__name__)


def get_pyramid_context(ctx: click.Context) -> PyramidContext:
    """Get or bootstrap Pyramid context on demand.

    Args:
        ctx: Click context

    Returns:
        PyramidContext object

    Raises:
        click.ClickException: If INI file not provided or bootstrap fails
    """
    # Check if already bootstrapped
    if ctx.obj.get("pyramid_context"):
        return ctx.obj["pyramid_context"]

    # Check if INI file provided
    ini_path = ctx.obj.get("ini_path")
    if not ini_path:
        raise click.ClickException("Pyramid INI file required for this command. Use --ini option.")

    # Bootstrap Pyramid application
    try:
        logger.info(f"Bootstrapping Pyramid application from {ini_path}")
        pyramid_context = bootstrap_pyramid_app(ini_path)
    except Exception as e:
        raise click.ClickException(f"Failed to bootstrap Pyramid application from {ini_path}: {e}") from e
    else:
        ctx.obj["pyramid_context"] = pyramid_context
        return pyramid_context


@click.group()
@click.option(
    "--ini",
    required=False,
    type=click.Path(exists=True, readable=True),
    help="Path to Pyramid INI configuration file (required for proto and implement commands)",
)
@click.pass_context
def main(ctx: click.Context, ini: str) -> None:
    """Generate gRPC services from Pyramid applications.

    This tool introspects Pyramid applications and generates:
    1. Protocol buffer (.proto) files
    2. Compiled gRPC Python stubs
    3. Service implementation code with subrequest bridging

    Example usage:
        grpc-generate --ini development.ini proto --dir ./protos
        grpc-generate compile --proto-dir ./protos --output-dir ./generated
        grpc-generate --ini development.ini implement --proto-dir ./protos --output-dir ./services
    """
    # Ensure context object exists and store INI path
    ctx.ensure_object(dict)
    ctx.obj["ini_path"] = ini
    ctx.obj["pyramid_context"] = None  # Will be bootstrapped on demand


# Add subcommands
main.add_command(proto)
main.add_command(compile_cmd)
main.add_command(implement)


def cli_main() -> None:
    """Entry point for grpc-generate console script."""
    main()


if __name__ == "__main__":
    cli_main()
