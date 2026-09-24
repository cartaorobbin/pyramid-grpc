# Completed tasks

### 2026-09-23 Client RPC failure logging

**Status**: DONE

#### Plan
- [x] Add `rpc_status_line` and `RpcFailureLog` in `pyramid_grpc/interseptors/client.py`
- [x] Cover a failed unary call with a real server that aborts `PERMISSION_DENIED`
- [x] Document the client helper in the README

#### Decisions Made
- The helper is a `grpc.UnaryUnaryClientInterceptor`, placed next to the server interceptors.
- `source_prefix` is supplied by the caller. The library does not read Pyramid settings and does not hardcode an application path.
- The continuation returns a `grpc.RpcError`. Detect it with `isinstance` and return that same object.
- The application frame is taken from the live stack with `inspect.stack()`, skipping `site-packages` and this package.

#### Test results
`poetry run pytest tests/test_client.py -v` — 4 passed.
