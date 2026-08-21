# 4. Middleware is written against raw ASGI, not BaseHTTPMiddleware

- Status: accepted
- Date: 2026-08-21

## Context

Starlette offers two ways to write middleware. `BaseHTTPMiddleware` is the
documented, comfortable one: subclass it, write `async def dispatch(request,
call_next)`, work with `Request` and `Response` objects. The alternative is to
implement the ASGI callable directly and work with raw `scope`, `receive` and
`send`.

`BaseHTTPMiddleware` runs the downstream application in a separate task and
pipes the response through an anyio memory object stream. For a normal
request-and-response that is invisible. For a long-lived streaming response it
is not: the stream couples the producing task's lifetime to the middleware's,
background tasks and client disconnects are handled differently, and a
response that never ends behaves differently from one that does.

Step 10 adds `GET /api/shows/{id}/stream`, a server-sent event stream that is
open for the whole time a customer is looking at a seat map. Every middleware
in the stack sits between that stream and the client.

Discovering this at step 10 would mean rewriting middleware written at step 1,
after eight steps of endpoints have been built and tested against its
behaviour.

## Decision

All middleware in this application implements the ASGI interface directly:

```python
class SomeMiddleware:
    def __init__(self, app: ASGIApp) -> None: ...
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...
```

Non-HTTP scopes are passed through untouched. Response headers are set by
wrapping `send` and mutating the `http.response.start` message, rather than by
constructing a `Response` object.

`CorrelationIdMiddleware` and `AccessLogMiddleware` are both written this way.

## Consequences

The middleware is a little more verbose and a little less obvious to a reader
who knows `BaseHTTPMiddleware` and not the ASGI spec. Each one needs its own
`if scope["type"] != "http"` guard, and setting a response header takes five
lines instead of one.

In exchange, the SSE endpoint at step 10 needs no middleware changes, and
nothing in the stack buffers a response that is not supposed to be buffered.

One consequence worth naming: because these middlewares wrap `send`, they only
see responses that pass through them. An unhandled exception is turned into a
response by Starlette's `ServerErrorMiddleware`, which sits above everything
and writes to the original `send`. The correlation ID would therefore be
missing from the header of exactly the response most likely to be reported by a
user. `app/errors.py` sets the header on the error response itself rather than
relying on the middleware, and `test_error_body_request_id_matches_the_header`
covers the 500 path specifically.
