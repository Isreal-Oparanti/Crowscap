from __future__ import annotations

import hashlib
import hmac
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import issue_mobile_session_token, normalize_google_user_id, _upsert_user
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import EmailLoginCode, utc_now
from app.db.session import get_db

router = APIRouter(tags=["auth"])
logger = get_logger("api.auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class MobileSessionRequest(BaseModel):
    id_token: str = Field(min_length=20)
    platform: Literal["ios", "android"]


class DemoSessionRequest(BaseModel):
    platform: Literal["ios", "android"] | None = None


class EmailCodeStartRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    mode: Literal["signup", "login"] = "signup"


class EmailCodeStartResponse(BaseModel):
    status: Literal["code_sent"]
    email: str
    expires_in_seconds: int
    resend_after_seconds: int


class EmailCodeVerifyRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    code: str = Field(min_length=4, max_length=12)
    mode: Literal["signup", "login"] = "signup"


class MobileSessionResponse(BaseModel):
    token: str
    user_id: str
    email: str
    name: str | None
    image_url: str | None
    expires_at: str


@router.post("/mobile-session", response_model=MobileSessionResponse)
def create_mobile_session(
    payload: MobileSessionRequest,
    db: Session = Depends(get_db),
) -> MobileSessionResponse:
    profile = _verify_google_id_token(payload.id_token)
    sub = str(profile.get("sub") or "").strip()
    email = str(profile.get("email") or "").strip().lower()
    name = str(profile.get("name") or "").strip() or None
    image_url = str(profile.get("picture") or "").strip() or None

    if not sub or "@" not in email:
        raise HTTPException(status_code=401, detail="Google sign in could not be verified.")

    email_verified = profile.get("email_verified")
    if email_verified not in (True, "true", "True", "1", 1):
        raise HTTPException(status_code=401, detail="Google email is not verified.")

    user_id = normalize_google_user_id(sub)
    return _create_session_response(
        db=db,
        user_id=user_id,
        email=email,
        name=name,
        image_url=image_url,
        provider="google",
    )


@router.post("/demo-session", response_model=MobileSessionResponse)
def create_demo_session(
    _payload: DemoSessionRequest | None = None,
    db: Session = Depends(get_db),
) -> MobileSessionResponse:
    settings = get_settings()
    if not settings.crowscap_mobile_demo_enabled:
        raise HTTPException(status_code=404, detail="Demo workspace is not available.")

    return _create_session_response(
        db=db,
        user_id="demo_yc_user",
        email="yc@crowscap.xyz",
        name="YC Reviewer",
        image_url=None,
        provider="demo",
    )


@router.post("/email/start", response_model=EmailCodeStartResponse)
def start_email_session(
    payload: EmailCodeStartRequest,
    db: Session = Depends(get_db),
) -> EmailCodeStartResponse:
    email = _normalize_email(payload.email)
    settings = get_settings()
    code = f"{random.SystemRandom().randint(0, 999999):06d}"
    expires_at = utc_now() + timedelta(minutes=max(2, settings.crowscap_email_code_ttl_minutes))

    db.query(EmailLoginCode).filter(
        EmailLoginCode.email == email,
        EmailLoginCode.consumed_at.is_(None),
    ).update({"consumed_at": utc_now()})

    db.add(
        EmailLoginCode(
            email=email,
            code_hash=_hash_email_code(email=email, code=code),
            purpose=payload.mode,
            expires_at=expires_at,
        )
    )
    db.commit()

    _send_login_code(email=email, code=code)
    return EmailCodeStartResponse(
        status="code_sent",
        email=email,
        expires_in_seconds=int((expires_at - utc_now()).total_seconds()),
        resend_after_seconds=60,
    )


@router.post("/email/verify", response_model=MobileSessionResponse)
def verify_email_session(
    payload: EmailCodeVerifyRequest,
    db: Session = Depends(get_db),
) -> MobileSessionResponse:
    email = _normalize_email(payload.email)
    code = re.sub(r"\D", "", payload.code)
    if len(code) != 6:
        raise HTTPException(status_code=400, detail="Enter the 6-digit code from your inbox.")

    row = db.scalar(
        select(EmailLoginCode)
        .where(
            EmailLoginCode.email == email,
            EmailLoginCode.consumed_at.is_(None),
        )
        .order_by(EmailLoginCode.created_at.desc())
    )
    if row is None:
        raise HTTPException(status_code=400, detail="Request a fresh code and try again.")

    now = utc_now()
    expires_at = _ensure_aware_utc(row.expires_at)
    if expires_at < now:
        row.consumed_at = now
        db.commit()
        raise HTTPException(status_code=400, detail="That code expired. Request a new one.")

    if row.attempt_count >= 5:
        row.consumed_at = now
        db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts. Request a fresh code.")

    row.attempt_count += 1
    if not hmac.compare_digest(row.code_hash, _hash_email_code(email=email, code=code)):
        db.commit()
        raise HTTPException(status_code=400, detail="That code is not correct.")

    row.consumed_at = now
    db.commit()
    return _create_session_response(
        db=db,
        user_id=_normalize_email_user_id(email),
        email=email,
        name=email.split("@")[0],
        image_url=None,
        provider="email",
    )


def _create_session_response(
    *,
    db: Session,
    user_id: str,
    email: str,
    name: str | None,
    image_url: str | None,
    provider: str,
) -> MobileSessionResponse:
    _upsert_user(
        db=db,
        user_id=user_id,
        email=email,
        name=name,
        image_url=image_url,
        provider=provider,
    )
    token, expires_at = issue_mobile_session_token(
        user_id=user_id,
        email=email,
        name=name,
        image_url=image_url,
        provider=provider,
    )
    return MobileSessionResponse(
        token=token,
        user_id=user_id,
        email=email,
        name=name,
        image_url=image_url,
        expires_at=expires_at.isoformat(),
    )


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not _EMAIL_RE.fullmatch(normalized):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    return normalized


def _normalize_email_user_id(email: str) -> str:
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]
    return f"e_{digest}"


def _hash_email_code(*, email: str, code: str) -> str:
    settings = get_settings()
    material = f"{email}:{code}".encode("utf-8")
    return hmac.new(settings.crowscap_jwt_secret.encode("utf-8"), material, hashlib.sha256).hexdigest()


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _send_login_code(*, email: str, code: str) -> None:
    settings = get_settings()
    api_key = settings.resend_api_key_value
    if not api_key:
        if settings.app_env == "production":
            raise HTTPException(
                status_code=503,
                detail="Email sign in is not configured yet.",
            )
        logger.warning("email.code.dev email=%s code=%s", email, code)
        return

    html = (
        "<div style='font-family:Inter,Arial,sans-serif;color:#111;line-height:1.5'>"
        "<h2>Your Crowscap code</h2>"
        f"<p>Use this code to continue:</p><p style='font-size:28px;font-weight:800;letter-spacing:6px'>{code}</p>"
        "<p>This code expires in 10 minutes. If you did not request it, you can ignore this email.</p>"
        "</div>"
    )
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": settings.crowscap_email_from,
                "to": [email],
                "subject": "Your Crowscap sign in code",
                "html": html,
            },
            timeout=8.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("email.code.resend_failed email=%s error=%s", email, str(exc))
        raise HTTPException(
            status_code=503,
            detail="Crowscap could not send the email code right now. Try again shortly.",
        ) from None


def _verify_google_id_token(id_token: str) -> dict[str, Any]:
    settings = get_settings()
    allowed_audiences = {
        value.strip()
        for value in (
            settings.auth_google_id,
            settings.google_client_id,
            settings.google_mobile_ios_client_id,
            settings.google_mobile_android_client_id,
        )
        if value and value.strip()
    }

    if not allowed_audiences and settings.app_env != "development":
        raise HTTPException(status_code=503, detail="Mobile Google sign in is not configured.")

    try:
        response = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=8.0,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Crowscap could not reach Google sign in. Check your connection and try again.",
        ) from None

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Google sign in could not be verified.")

    profile = response.json()
    audience = str(profile.get("aud") or "").strip()
    if allowed_audiences and audience not in allowed_audiences:
        raise HTTPException(status_code=401, detail="Google sign in was issued for another app.")

    return profile
