"""Proto file generation command."""

from pathlib import Path

import click

from pyramid_grpc.cli.utils.introspection import PyramidIntrospector
from pyramid_grpc.cli.utils.proto_generator import ProtoGenerator


@click.command()
@click.option(
    "--dir",
    "output_dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory to output generated .proto files",
)
@click.pass_context
def proto(ctx: click.Context, output_dir: Path) -> None:
    """Generate .proto files from Pyramid application views.

    This command introspects the Pyramid application and generates
    Protocol Buffer (.proto) files with gRPC service definitions.
    Services are organized by resource (e.g., UserService, OrderService).

    Example:
        grpc-generate --ini development.ini proto --dir ./protos
    """
    # Get Pyramid context (bootstrap on demand)
    from pyramid_grpc.cli.main import get_pyramid_context

    pyramid_context = get_pyramid_context(ctx)

    ini_path = ctx.obj["ini_path"]
    click.echo(f"🔍 Introspecting Pyramid application from: {ini_path}")
    click.echo(f"📁 Output directory: {output_dir}")

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Use the bootstrapped Pyramid application
        click.echo("🔎 Discovering views and routes...")
        introspector = PyramidIntrospector(pyramid_context.registry)
        views = introspector.discover_views()

        click.echo(f"✅ Found {len(views)} views")

        # Group views by service
        click.echo("🗂️  Grouping views by service...")
        services = introspector.group_views_by_service(views)

        click.echo(f"✅ Organized into {len(services)} services:")
        for service in services:
            click.echo(f"   📦 {service.name} ({len(service.views)} methods)")
            for view in service.views:
                method_name = view.request_method or "ANY"
                click.echo(f"      - {method_name} {view.route_name}")

        # Generate proto files
        click.echo("🏗️  Generating proto files...")
        generator = ProtoGenerator()
        proto_services = generator.convert_services_to_proto(services)

        # Write proto files to disk
        generated_files = generator.write_proto_files(proto_services, output_dir)

        click.echo(f"✅ Generated {len(generated_files)} proto files:")
        for filepath in generated_files:
            click.echo(f"   📄 {filepath}")

        click.echo("🎉 Proto file generation complete!")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.ClickException(str(e)) from e
