"""The error registry and the handlers that render it.

Every assertion here is about the contract a client sees: one envelope shape,
a code from the registry, a correlation ID, and never an internal detail.
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors import ERROR_REGISTRY, AppError, ErrorCode
from app.request_context import REQUEST_ID_HEADER

_INTERNAL_DETAIL = "connection to db-primary.internal refused"


class _Payload(BaseModel):
    quantity: int


@pytest.fixture
def faulty_app(app: FastAPI) -> FastAPI:
    """The application plus routes that fail in each way the handlers cover.

    Step 1 has no endpoint that can fail on purpose yet, so the failures are
    injected here rather than left untested until a later step happens to
    produce one.
    """

    @app.get("/api/_faults/app-error")
    async def _app_error() -> None:
        raise AppError(ErrorCode.NOT_FOUND, "No show with that id.")

    @app.get("/api/_faults/unhandled")
    async def _unhandled() -> None:
        raise RuntimeError(_INTERNAL_DETAIL)

    @app.get("/api/_faults/teapot")
    async def _teapot() -> None:
        raise HTTPException(status_code=418, detail="short and stout")

    @app.post("/api/_faults/validated")
    async def _validated(payload: _Payload) -> dict[str, int]:
        return {"quantity": payload.quantity}

    return app


@pytest.fixture
def faulty_client(faulty_app: FastAPI) -> TestClient:
    return TestClient(faulty_app, raise_server_exceptions=False)


def test_registry_covers_every_code() -> None:
    """A code without a spec would raise KeyError inside an error handler."""
    assert set(ERROR_REGISTRY) == set(ErrorCode)


def test_unknown_route_returns_the_envelope(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == ErrorCode.NOT_FOUND
    assert body["error"]["message"]
    assert body["error"]["request_id"]
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id"}


def test_wrong_method_returns_the_envelope(client: TestClient) -> None:
    response = client.post("/api/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == ErrorCode.METHOD_NOT_ALLOWED


def test_app_error_renders_its_registered_status_and_own_message(
    faulty_client: TestClient,
) -> None:
    response = faulty_client.get("/api/_faults/app-error")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": ErrorCode.NOT_FOUND,
        "message": "No show with that id.",
        "request_id": response.headers[REQUEST_ID_HEADER],
    }


def test_validation_failure_names_the_offending_field(faulty_client: TestClient) -> None:
    response = faulty_client.post("/api/_faults/validated", json={"quantity": "three"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == ErrorCode.VALIDATION_ERROR
    assert "body.quantity" in body["error"]["message"]


def test_unhandled_exception_becomes_internal_error(faulty_client: TestClient) -> None:
    response = faulty_client.get("/api/_faults/unhandled")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == ErrorCode.INTERNAL_ERROR


def test_unhandled_exception_leaks_nothing(faulty_client: TestClient) -> None:
    """No exception type, no message, no traceback, no file path."""
    response = faulty_client.get("/api/_faults/unhandled")

    raw = response.text
    assert _INTERNAL_DETAIL not in raw
    assert "RuntimeError" not in raw
    assert "Traceback" not in raw
    assert "app/errors.py" not in raw


def test_unregistered_http_status_is_not_leaked(faulty_client: TestClient) -> None:
    """A status outside the registry is a bug here, not a contract for clients.

    Rendering it verbatim would put an unregistered code into the API surface
    that no frontend can switch on. It is reported as INTERNAL_ERROR instead,
    which is what it is.
    """
    response = faulty_client.get("/api/_faults/teapot")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == ErrorCode.INTERNAL_ERROR
    assert "short and stout" not in response.text


def test_error_body_request_id_matches_the_header(faulty_client: TestClient) -> None:
    """Including the 500 path, which is handled above the correlation middleware."""
    response = faulty_client.get("/api/_faults/unhandled")

    assert response.json()["error"]["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert response.headers[REQUEST_ID_HEADER] != ""
