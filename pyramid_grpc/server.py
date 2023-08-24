import logging
from concurrent import futures

import sys
import click
import grpc
from pyramid.paster import bootstrap

from pyramid_grpc.main import build_interceptors, serve

logger = logging.getLogger(__name__)


@click.command()
@click.argument("ini_location")
def run(ini_location):
    """Simple program that greets NAME for a total of COUNT times."""

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    logger.addHandler(handler)

    logger.info("Starting Server ...")

    env = bootstrap(ini_location)

    env["registry"]
    app = env["app"]
    env["root"]
    env["request"]
    env["closer"]

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=build_interceptors(app),
    )

    serve(app, server)


if __name__ == "__main__":
    run()
