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
