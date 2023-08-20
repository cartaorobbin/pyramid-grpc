import re
import click
import grpc
from pyramid.paster import bootstrap, setup_logging
from pyramid_grpc.main import serve, build_interceptors

from concurrent import futures

import logging

logger = logging.getLogger(__name__)


@click.command()
@click.argument("ini_location")
def run(ini_location):
    """Simple program that greets NAME for a total of COUNT times."""

    logger.info("Starting server")
    env = bootstrap(ini_location)

    registry = env["registry"]
    app = env["app"]
    root = env["root"]
    request = env["request"]
    closer = env["closer"]

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=build_interceptors(app),
    )

    serve(app, server)


if __name__ == "__main__":
    run()
