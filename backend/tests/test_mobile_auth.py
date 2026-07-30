from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import User
from app.db.session import get_db
from app.main import app
from app.api.v1.auth import _resend_from_header, _resend_user_error



def build_auth_db_override():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    return override_db


def test_mobile_demo_session_can_access_protected_api() -> None:
    app.dependency_overrides[get_db] = build_auth_db_override()

    try:
        client = TestClient(app)
        session_response = client.post("/api/v1/auth/demo-session", json={"platform": "android"})

        assert session_response.status_code == 200
        session = session_response.json()
        assert session["user_id"] == "demo_yc_user"
        assert session["email"] == "yc@crowscap.xyz"
        assert session["token"]

        protected_response = client.get(
            "/api/v1/notifications/push/public-key",
            headers={"Authorization": f"Bearer {session['token']}"},
        )

        assert protected_response.status_code == 200
        assert isinstance(protected_response.json()["configured"], bool)
    finally:
        app.dependency_overrides.clear()


def test_mobile_static_demo_token_can_access_protected_api() -> None:
    app.dependency_overrides[get_db] = build_auth_db_override()

    try:
        client = TestClient(app)
        protected_response = client.get(
            "/api/v1/notifications/push/public-key",
            headers={"Authorization": "Bearer crowscap-demo-workspace"},
        )

        assert protected_response.status_code == 200
        assert isinstance(protected_response.json()["configured"], bool)
    finally:
        app.dependency_overrides.clear()


def test_mobile_demo_session_seeds_demo_workspace_once() -> None:
    override_db = build_auth_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        first = client.post("/api/v1/auth/demo-session", json={"platform": "android"})
        second = client.post("/api/v1/auth/demo-session", json={"platform": "ios"})

        assert first.status_code == 200
        assert second.status_code == 200

        db = next(override_db())
        try:
            users = db.query(User).all()
            assert len(users) == 1
            assert users[0].id == "demo_yc_user"
        finally:
            db.close()
    finally:
        app.dependency_overrides.clear()


def test_mobile_email_code_session_can_access_protected_api(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = build_auth_db_override()
    monkeypatch.setattr("random.SystemRandom.randint", lambda _self, _start, _end: 123456)

    class DummyResponse:
        status_code = 200
        text = '{"id":"mock_msg_123"}'
        def raise_for_status(self): pass
        def json(self): return {"id": "mock_msg_123"}

    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: DummyResponse())


    try:
        client = TestClient(app)
        start = client.post(
            "/api/v1/auth/email/start",
            json={"email": "founder@example.com", "mode": "signup"},
        )


        assert start.status_code == 200
        assert start.json()["status"] == "code_sent"
        assert start.json()["email"] == "founder@example.com"

        verified = client.post(
            "/api/v1/auth/email/verify",
            json={"email": "founder@example.com", "code": "123456", "mode": "signup"},
        )

        assert verified.status_code == 200
        session = verified.json()
        assert session["email"] == "founder@example.com"
        assert session["user_id"].startswith("e_")
        assert session["token"]

        protected_response = client.get(
            "/api/v1/notifications/push/public-key",
            headers={"Authorization": f"Bearer {session['token']}"},
        )

        assert protected_response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_email_signup_rejects_existing_account() -> None:
    override_db = build_auth_db_override()
    app.dependency_overrides[get_db] = override_db

    try:
        db = next(override_db())
        try:
            db.add(User(id="existing_user", email="founder@example.com", provider="email"))
            db.commit()
        finally:
            db.close()

        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/email/start",
            json={"email": "founder@example.com", "mode": "signup"},
        )

        assert response.status_code == 409
        assert "already has a Crowscap account" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_email_login_rejects_missing_account() -> None:
    app.dependency_overrides[get_db] = build_auth_db_override()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/email/start",
            json={"email": "new@example.com", "mode": "login"},
        )

        assert response.status_code == 404
        assert "Sign up first" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_resend_errors_identify_invalid_api_key() -> None:
    detail = _resend_user_error(
        status_code=401,
        provider_message="API key is invalid",
    )

    assert "Resend API key" in detail
    assert "invalid" in detail


def test_resend_errors_identify_unverified_sender() -> None:
    detail = _resend_user_error(
        status_code=403,
        provider_message="The from domain is not verified",
    )

    assert "sender" in detail.lower()
    assert "verified" in detail.lower()


def test_resend_errors_identify_test_mode_recipient_limit() -> None:
    detail = _resend_user_error(
        status_code=403,
        provider_message="You can only send testing emails to your own email address.",
    )

    assert "test mode" in detail.lower()
    assert "verify crowscap.xyz" in detail.lower()


def test_resend_from_header_always_formats_crowscap_sender() -> None:
    assert _resend_from_header("auth <auth@crowscap.xyz>") == "Crowscap <auth@crowscap.xyz>"
    assert _resend_from_header("auth@crowscap.xyz") == "Crowscap <auth@crowscap.xyz>"
    assert _resend_from_header("Crowscap <support@crowscap.xyz>") == "Crowscap <support@crowscap.xyz>"
    assert _resend_from_header("") == "Crowscap <support@crowscap.xyz>"

