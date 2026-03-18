"""Utilities for loading Pyramid applications from INI files."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyramid.paster import bootstrap, setup_logging
from pyramid.registry import Registry

logger = logging.getLogger(__name__)


@dataclass
class PyramidContext:
    """Context containing Pyramid application components."""

    pyramid_app: Any
    pyramid_request: Any
    registry: Registry
    root: Any
    closer: Any


def bootstrap_pyramid_app(ini_path: str | Path) -> PyramidContext:
    """Bootstrap a Pyramid application from an INI configuration file.

    This uses pyramid.paster.bootstrap to properly initialize the application
    with all its components, similar to how it would be done in production.

    Args:
        ini_path: Path to the Pyramid INI configuration file

    Returns:
        PyramidContext with all application components

    Raises:
        ValueError: If the INI file cannot be loaded or is invalid
        ImportError: If the application cannot be imported
    """
    try:
        # Convert to string if Path object
        ini_path_str = str(ini_path)

        logger.info(f"Bootstrapping Pyramid application from {ini_path_str}")

        # Set up logging from INI file
        setup_logging(ini_path_str)

        # Bootstrap the application
        env = bootstrap(ini_path_str)
    except Exception as e:
        raise ValueError(f"Failed to bootstrap Pyramid application from {ini_path}: {e}") from e
    else:
        registry = env["registry"]
        app = env["app"]
        root = env["root"]
        request = env["request"]
        closer = env["closer"]

        return PyramidContext(pyramid_app=app, pyramid_request=request, registry=registry, root=root, closer=closer)
