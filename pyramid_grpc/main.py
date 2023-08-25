import logging

import click
from pyramid.paster import bootstrap, setup_logging

logger = logging.getLogger(__name__)


def main(ini_location):
    """Simple program that greets NAME for a total of COUNT times."""

    logger.info("Setting up pyramid")
    setup_logging(ini_location)
    env = bootstrap(ini_location)

    logger.info("Starting Server ...")

    env["registry"]
    app = env["app"]
    env["root"]
    env["request"]
    env["closer"]

    return app


@click.command()
@click.argument("ini_location")
def run(ini_location):
    app = main(ini_location)
    grpc_server = app.registry.grpc_server
    grpc_server.start()
    grpc_server.wait_for_termination()


if __name__ == "__main__":
    run()
