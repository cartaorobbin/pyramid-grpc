"""Client-channel helpers for failed unary RPCs."""

import inspect
import logging
from pathlib import Path

import grpc

logger = logging.getLogger(__name__)

_PACKAGE_ROOT = str(Path(__file__).resolve().parents[1]).replace("\\", "/")


def rpc_status_line(error: BaseException) -> str | None:
    """Format a failed RPC as ``STATUS: details``.

    The grpc debug dump stays out of the result so the line can be logged
    or stored on a failure row.

    Args:
        error: Exception from a failed RPC.

    Returns:
        A single-line status, or None when ``error`` has no grpc status.
    """
    code = getattr(error, "code", None)
    details = getattr(error, "details", None)
    if not callable(code) or not callable(details):
        return None
    status = code()
    name = getattr(status, "name", None)
    if not name:
        return None
    detail = details() or ""
    return " ".join(f"{name}: {detail}".split())


def _caller_frame(source_prefix: str | None) -> str | None:
    """Return ``path:line function`` for the first application frame.

    Args:
        source_prefix: When set and present in the path, the path is shortened
            to start at this marker.

    Returns:
        The caller description, or None when every frame is skipped.
    """
    for frame_info in inspect.stack():
        filename = frame_info.filename.replace("\\", "/")
        if "site-packages" in filename or filename.startswith(f"{_PACKAGE_ROOT}/"):
            continue
        path = filename
        if source_prefix:
            index = filename.rfind(source_prefix)
            if index >= 0:
                path = filename[index:]
        return f"{path}:{frame_info.lineno} {frame_info.function}"
    return None


def _log_rpc_failure(method: str, error: grpc.RpcError, source_prefix: str | None) -> None:
    status = rpc_status_line(error) or error.__class__.__name__
    frame = _caller_frame(source_prefix)
    where = f" @ {frame}" if frame else ""
    logger.warning("gRPC %s %s%s", method, status, where)


class RpcFailureLog(grpc.UnaryUnaryClientInterceptor):
    """Log one warning for each failed unary RPC.

    Pass an instance to ``grpc.intercept_channel``. The warning names the
    method, the status, and the application frame that made the call.

    Args:
        source_prefix: Path prefix used to shorten the caller frame. When
            omitted, the path is kept as ``inspect`` recorded it.
    """

    def __init__(self, source_prefix: str | None = None) -> None:
        self.source_prefix = source_prefix

    def intercept_unary_unary(self, continuation, client_call_details, request):
        """Log a returned RPC error, then return that same error."""
        outcome = continuation(client_call_details, request)
        if isinstance(outcome, grpc.RpcError):
            _log_rpc_failure(str(client_call_details.method), outcome, self.source_prefix)
        return outcome
