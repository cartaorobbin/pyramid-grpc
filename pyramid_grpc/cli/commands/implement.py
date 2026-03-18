"""Service implementation generation command."""

from pathlib import Path

import click

from pyramid_grpc.cli.utils.introspection import PyramidIntrospector
from pyramid_grpc.cli.utils.service_generator import ServiceGenerator


@click.command()
@click.option(
    "--proto-dir", required=True, type=click.Path(exists=True, path_type=Path), help="Directory containing .proto files"
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory to output service implementation files",
)
@click.pass_context
def implement(ctx: click.Context, proto_dir: Path, output_dir: Path) -> None:
    """Generate gRPC service implementation with Pyramid subrequest bridging.

    This command generates Python service classes that implement the gRPC
    services defined in .proto files. Each service method makes subrequests
    to the corresponding Pyramid view.

    Example:
        grpc-generate --ini development.ini implement --proto-dir ./protos --output-dir ./services
    """
    # Get Pyramid context (bootstrap on demand)
    from pyramid_grpc.cli.main import get_pyramid_context

    pyramid_context = get_pyramid_context(ctx)

    ini_path = ctx.obj["ini_path"]
    click.echo(f"🔍 Introspecting Pyramid application from: {ini_path}")
    click.echo(f"📄 Proto files directory: {proto_dir}")
    click.echo(f"📁 Output directory: {output_dir}")

    try:
        # Discover Pyramid views
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

        # Generate service implementations
        click.echo("🏗️  Generating service implementations...")
        generator = ServiceGenerator()
        implementations = generator.convert_services_to_implementations(services)

        # Write service files to disk
        generated_files = generator.write_service_files(implementations, output_dir)

        click.echo(f"✅ Generated {len(generated_files)} service implementation files:")
        for filepath in generated_files:
            click.echo(f"   🐍 {filepath}")

        click.echo("🎉 Service implementation generation complete!")
        click.echo("📋 Next steps:")
        click.echo("   1. Import the generated service classes in your application")
        click.echo("   2. Register them with your gRPC server")
        click.echo("   3. Configure authentication and middleware as needed")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        raise click.ClickException(str(e)) from e
