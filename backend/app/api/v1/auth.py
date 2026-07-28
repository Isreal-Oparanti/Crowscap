from __future__ import annotations

from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import issue_mobile_session_token, normalize_google_user_id, _upsert_user
from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["auth"])


class MobileSessionRequest(BaseModel):
    id_token: str = Field(min_length=20)
    platform: Literal["ios", "android"]


class DemoSessionRequest(BaseModel):
    platform: Literal["ios", "android"] | None = None


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
