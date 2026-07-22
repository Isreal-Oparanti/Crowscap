import socket

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.auth import CurrentUser, require_current_user
from app.db.session import get_db
from app.main import app


def test_database_dns_failure_returns_retryable_json() -> None:
    def broken_db():
        raise OperationalError(
            "SELECT 1",
            {},
            socket.gaierror(11001, "getaddrinfo failed"),
        )

    app.dependency_overrides[get_db] = broken_db
    app.dependency_overrides[require_current_user] = lambda: CurrentUser(
        id="test-user",
        email="test@example.com",
        name="Test User",
    )

    try:
        client = TestClient(app)
        response = client.get("/api/v1/recalls/due?limit=1")

        assert response.status_code == 503
        payload = response.json()
        assert payload["error_code"] == "database_unavailable"
        assert payload["retryable"] is True
        assert "memory database" in payload["detail"]
    finally:
        app.dependency_overrides.clear()
