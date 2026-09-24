# Architecture

pyramid-grpc is a Pyramid add-on that runs gRPC services inside a Pyramid app. `includeme` registers the server, a per-RPC Pyramid request, and an optional transaction wrapper. Application code registers servicers with `config_grpc_service` and can require a Pyramid permission with `config_grpc_call`. Outbound unary calls are logged by a separate client interceptor the caller attaches to its own channel.

## Package Structure

```
pyramid_grpc/
├── __init__.py              # includeme, interceptor directives, grpc.server registration
├── main.py                  # Click CLI: bootstrap a Paste ini file and start the server
├── decorators.py            # config_grpc_service registry and config_grpc_call permission check
└── interseptors/
    ├── request.py           # Build a Pyramid request per RPC and copy the auth metadata
    ├── transaction.py       # Begin, commit, or abort pyramid-tm around the RPC
    └── client.py            # RpcFailureLog and rpc_status_line for failed outbound unary calls
tests/                       # pytest-grpc fixtures and a sample Greeter service
```

## Core Design Decisions

The gRPC server is stored on the Pyramid registry as `grpc_server`. Interceptors live on `registry.grpc_interceptors` and are passed into `grpc.server` when that server is created. The listen port comes from `grpc.port` (default `50051`) and the worker count from `grpc.max_workers` (default 10). The port is insecure.

`config_grpc_service` appends the decorated callable to a process-global list. When the server is registered, each callable receives the `grpc.Server` and adds its servicer.

`config_grpc_call` wraps a method. With no permission it calls through. With a permission it asks the Pyramid `ISecurityPolicy` and aborts `PERMISSION_DENIED` when the policy denies the call. An optional factory builds the security context from `context.pyramid_request`.

`RequestInterseptor` runs first. It builds a Pyramid request with `pyramid.scripting.prepare`, copies gRPC metadata into `HTTP_AUTHORIZATION` when present, and stores the request on `context.pyramid_request`. The metadata key is `grpc.auth_header`, defaulting to `authorization`.

`TransactionInterseptor` is registered only when `tm.manager_hook` is set. If `tm.active` is already in the request environ it does nothing. Otherwise it begins a transaction, commits on success, and aborts on any exception.

Outbound logging is not part of the server stack. The caller wraps a channel with `grpc.intercept_channel` and `RpcFailureLog`. `rpc_status_line` formats a failed call as `STATUS: details` and leaves out the grpc debug dump.

## Component Relationships

A Paste ini file is bootstrapped into a Pyramid app. `includeme` installs the default interceptors and the server. Inbound RPCs pass through `RequestInterseptor`, then `TransactionInterseptor` when transactions are enabled, then the servicer method. Methods decorated with `config_grpc_call` check the Pyramid security policy before the method body runs.

Outbound calls stay on the caller's channel. `RpcFailureLog` logs the method, the status line, and the first application frame outside this package and `site-packages`.

## Key Learnings / Gotchas

The interceptor package is spelled `interseptors`. Imports and config action names use that spelling.

`pyproject.toml` declares the console script `grpc-server` as `pyramid_grpc.server:run`. There is no `server` module. The Click command is `run` in `pyramid_grpc.main`.

`configure_grpc` schedules server creation at Pyramid action order 80. `includeme` schedules `default_config` at order 100, and extra interceptors added with `add_grpc_interceptors` run at order 90. Lower orders run first, so an explicit `configure_grpc` creates the server before those later actions. `register_server` keeps the first server and does not rebuild it, so interceptors registered afterward are not attached to that server. `default_config` alone registers the request interceptor and then the server in one function, which does attach them.

`RequestInterseptor` stores the registry on the attribute `pyramid_regsitry`.

`RpcFailureLog` implements `grpc.UnaryUnaryClientInterceptor` only. Streaming calls are not logged.

Servicers registered with `config_grpc_service` stay in a module-level list for the life of the process.
