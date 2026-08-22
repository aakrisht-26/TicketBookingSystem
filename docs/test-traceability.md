# Test traceability

Every invariant this system claims, and the test that proves it. A claim
without a row here is a claim nobody checks.

Filled in as steps land. The Definition of Done in `CLAUDE.md` requires a new
row for every new invariant, in the same step that introduces it.

## How to read a row

- **Invariant** - the guarantee, stated so it can be false.
- **Enforced by** - the mechanism that makes it true. A database constraint, a
  lock ordering, a transaction boundary. Not a code comment.
- **Proven by** - the test that fails if the mechanism is removed. Removal, not
  reformulation: a test that passes against a gutted implementation proves
  nothing.
- **Step** - the roadmap step that introduced it.

The eight data invariants named in `docs/DATA-MODEL.md` are added as their
steps land, alongside the concurrency guarantees from steps 7 and 9 and the
offer cascade from step 13.

## Invariants

| # | Invariant | Enforced by | Proven by | Step |
|---|---|---|---|---|
| TC1 | The backend package installed in the environment is the one in this tree, at the version declared in `backend/pyproject.toml`, so the version has one source of truth. | Editable install of `backend/pyproject.toml`; `app.__version__` read from installed distribution metadata rather than duplicated in source. | `backend/tests/test_toolchain.py::test_package_version_matches_pyproject` | 0 |
| TC2 | The backend runs on Python 3.11, the version `CLAUDE.md` commits to. A runner on any other version fails the build rather than passing quietly on untested behaviour. | `requires-python = ">=3.11,<3.12"` in `backend/pyproject.toml`; `python-version: "3.11"` in the CI workflow. | `backend/tests/test_toolchain.py::test_runs_on_python_311` | 0 |
| E1 | Every error a client sees uses one envelope, `{"error": {"code", "message", "request_id"}}`, with a code from the registry. | `app/errors.py`: one `ErrorCode` enum, one `ERROR_REGISTRY`, and handlers registered for `AppError`, `HTTPException`, `RequestValidationError` and bare `Exception`. | `backend/tests/test_errors.py::test_unknown_route_returns_the_envelope`, `::test_registry_covers_every_code` | 1 |
| E2 | No exception type, message, traceback or file path reaches a client. | The `Exception` handler discards the exception and returns a fixed `INTERNAL_ERROR` body; the detail goes to the log only. | `backend/tests/test_errors.py::test_unhandled_exception_leaks_nothing` | 1 |
| E3 | An HTTP status outside the registry is never rendered as a client-facing code. | `_ROUTING_STATUS_CODES` maps only 404 and 405; anything else is logged and reported as `INTERNAL_ERROR`. | `backend/tests/test_errors.py::test_unregistered_http_status_is_not_leaked` | 1 |
| C1 | Every request has a correlation ID, present in the response header, in every log line for that request, and in the body of any error it produces. | `CorrelationIdMiddleware` sets a context variable before anything else runs; a structlog processor stamps it onto every event; `error_response` reads it. | `backend/tests/test_correlation.py::test_every_log_line_for_a_request_carries_the_id`, `backend/tests/test_errors.py::test_error_body_request_id_matches_the_header` | 1 |
| C2 | A client-supplied correlation ID is honoured only if it is well formed, since it is echoed into responses and logs. | `_SAFE_REQUEST_ID` accepts 8 to 64 characters of `[A-Za-z0-9._-]` and nothing else. | `backend/tests/test_correlation.py::test_a_malformed_client_id_is_replaced` | 1 |
| C3 | Two requests in flight at the same time never share a correlation ID, including across an `await`. | The ID lives in a `contextvars.ContextVar`, so each request task gets its own copy. Deliberately the only mechanism: structlog's `merge_contextvars` was removed because with two mechanisms, removing either left every test passing. | `backend/tests/test_correlation.py::test_concurrent_requests_never_share_a_correlation_id` | 1 |
| L1 | Exactly one access log line per request, carrying the status the client actually received. | `AccessLogMiddleware` captures the status from `http.response.start`; uvicorn's own access logger is silenced so it cannot emit a second. | `backend/tests/test_logging.py::test_exactly_one_access_line_per_request`, `::test_uvicorn_access_log_is_silenced` | 1 |
| L2 | Production logs are JSON, so an aggregator can parse them; development logs are not. | `Settings.log_json` derives from `environment`; `configure_logging` selects the renderer from it. | `backend/tests/test_logging.py::test_production_renders_json`, `::test_development_renders_for_humans` | 1 |
| M1 | No database connection string is committed, and Alembic resolves its URL from application settings rather than from `alembic.ini`. | `sqlalchemy.url` is absent from `alembic.ini`; `migrations/env.py` sets it from `get_settings()`. | `backend/tests/test_migrations.py::test_no_connection_string_is_committed`, `::test_offline_mode_resolves_the_url_from_settings`, `::test_alembic_will_not_run_without_the_settings_url` | 1 |
