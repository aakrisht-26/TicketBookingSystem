"""The published API contract.

The frontend client is generated from this schema, so what it documents is what
the frontend can see. A missing error model or an undocumented status is a
frontend that cannot handle the case.
"""

from typing import Any

from fastapi import FastAPI


def _schema(app: FastAPI) -> dict[str, Any]:
    return app.openapi()


def test_schema_is_served_under_the_api_prefix(app: FastAPI) -> None:
    assert app.openapi_url == "/api/openapi.json"
    assert app.docs_url == "/api/docs"


def test_the_error_envelope_is_a_documented_component(app: FastAPI) -> None:
    components = _schema(app)["components"]["schemas"]

    assert "ErrorResponse" in components
    assert set(components["ErrorDetail"]["properties"]) == {"code", "message", "request_id"}


def test_error_codes_are_enumerated_for_clients(app: FastAPI) -> None:
    """A generated client gets the codes as a union type, not as bare strings."""
    components = _schema(app)["components"]["schemas"]

    assert set(components["ErrorCode"]["enum"]) == {
        "DATABASE_UNAVAILABLE",
        "INTERNAL_ERROR",
        "METHOD_NOT_ALLOWED",
        "NOT_FOUND",
        "VALIDATION_ERROR",
    }


def test_health_is_documented_with_a_summary_and_a_response_model(app: FastAPI) -> None:
    operation = _schema(app)["paths"]["/api/health"]["get"]

    assert operation["summary"] == "Liveness probe"
    assert operation["tags"] == ["health"]
    assert operation["description"]
    assert "500" in operation["responses"]
    assert "404" in operation["responses"]
