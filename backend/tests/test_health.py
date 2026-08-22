"""Liveness endpoint."""

from fastapi.testclient import TestClient

from app import __version__
from app.request_context import REQUEST_ID_HEADER


def test_health_reports_ok_and_version(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_health_performs_no_io(client: TestClient) -> None:
    """Liveness must not depend on anything but this process.

    No database is configured or reachable in the test environment. If the
    endpoint ever grows a dependency call, this stops passing, which is the
    point: a liveness probe that fails when a dependency is slow causes the
    platform to restart a healthy process.
    """
    assert client.get("/api/health").status_code == 200


def test_health_response_carries_a_correlation_id(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.headers[REQUEST_ID_HEADER]
