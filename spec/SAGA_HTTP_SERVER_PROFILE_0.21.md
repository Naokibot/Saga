# Saga HTTP Server Profile 0.21

**Status:** Native Hosted profile implemented and validated on Linux x86-64 in Saga 0.21.0.

`use http` adds a synchronous ownership-safe server surface:

- `listen(host,port)`; port 0 selects an ephemeral port
- `server_port(server)`
- `accept(server)`
- request method/path/body/header/query accessors
- `respond(request,status,content_type,body)`
- `server_close(server)`

The reference backend enforces an 8 MiB request-body ceiling, a read-header timeout, one response per request, and unblocks an outstanding `accept` when the server closes. The response writer remains owned by its server goroutine; Saga code communicates through a response channel instead of using the host response object across goroutines.

This is a server baseline, not yet a production framework with HTTP/2 tuning, TLS certificate automation, middleware composition, websocket routing, template hot reload, or distributed tracing.
