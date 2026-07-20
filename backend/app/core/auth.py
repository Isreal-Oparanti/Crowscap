from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import User, utc_now
from app.db.session import get_db

logger = get_logger("core.auth")

_SAFE_USER_ID = re.compile(r"^[a-zA-Z0-9_.:-]{1,36}$")


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    name: str | None = None
    image_url: str | None = None


def require_current_user(
    db: Session = Depends(get_db),
    proxy_secret: str | None = Header(default=None, alias="X-Crowscap-Proxy-Secret"),
    user_id: str | None = Header(default=None, alias="X-Crowscap-User-Id"),
    user_email: str | None = Header(default=None, alias="X-Crowscap-User-Email"),
    user_name: str | None = Header(default=None, alias="X-Crowscap-User-Name"),
    user_image: str | None = Header(default=None, alias="X-Crowscap-User-Image"),
) -> CurrentUser:
    """Accept identity only from the trusted Next.js proxy.

    The browser never gets to choose its own Crowscap user. NextAuth verifies
    Google in the frontend, then the proxy forwards a signed internal identity.
    """

    settings = get_settings()
    expected_secret = settings.crowscap_proxy_secret_value

    if expected_secret:
        if not proxy_secret or not secrets.compare_digest(proxy_secret, expected_secret):
            logger.warning("🔒 auth.rejected reason=bad_proxy_secret")
            raise HTTPException(status_code=401, detail="Authentication required.")
        if not user_id or not user_email:
            logger.warning("🔒 auth.rejected reason=missing_user_headers")
            raise HTTPException(status_code=401, detail="Authentication required.")
    elif settings.crowscap_auth_required and settings.app_env != "development":
        logger.error("🔒 auth.misconfigured reason=missing_proxy_secret env=%s", settings.app_env)
        raise HTTPException(status_code=503, detail="Authentication is not configured.")
    elif not user_id or not user_email:
        user_id = settings.crowscap_dev_user_id
        user_email = settings.crowscap_dev_user_email
        user_name = "Local developer"

    # Explicit guards instead of assert — assert is stripped with -O (PYTHONOPTIMIZE)
    if user_id is None or user_email is None:
        logger.warning("🔒 auth.rejected reason=missing_identity_after_dev_fallback")
        raise HTTPException(status_code=401, detail="Authentication required.")

    user_id = user_id.strip()
    user_email = user_email.strip().lower()
    user_name = user_name.strip() if user_name else None
    user_image = user_image.strip() if user_image else None

    if not _SAFE_USER_ID.fullmatch(user_id) or "@" not in user_email:
        logger.warning("🔒 auth.rejected reason=invalid_identity user_id=%r email=%r", user_id, user_email)
        raise HTTPException(status_code=401, detail="Authentication required.")

    _upsert_user(
        db=db,
        user_id=user_id,
        email=user_email,
        name=user_name,
        image_url=user_image,
    )

    return CurrentUser(id=user_id, email=user_email, name=user_name, image_url=user_image)


def _upsert_user(
    *,
    db: Session,
    user_id: str,
    email: str,
    name: str | None,
    image_url: str | None,
) -> None:
    user = db.get(User, user_id)
    if user is None:
        existing_by_email = db.scalar(select(User).where(User.email == email))
        if existing_by_email is not None:
            user = existing_by_email
            user.id = user_id
        else:
            user = User(id=user_id, email=email, provider="google")
            db.add(user)

    user.email = email
    user.name = name
    user.image_url = image_url
    user.last_seen_at = utc_now()
    db.commit()
