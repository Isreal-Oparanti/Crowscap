from __future__ import annotations

import re
import secrets
import datetime
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
import jwt
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import (
    User, Conversation, ChatMessage, Source, Capture, Memory, UserPreference, utc_now
)
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
    authorization: str | None = Header(default=None, alias="Authorization"),
    proxy_secret: str | None = Header(default=None, alias="X-Crowscap-Proxy-Secret"),
    user_id: str | None = Header(default=None, alias="X-Crowscap-User-Id"),
    user_email: str | None = Header(default=None, alias="X-Crowscap-User-Email"),
    user_name: str | None = Header(default=None, alias="X-Crowscap-User-Name"),
    user_image: str | None = Header(default=None, alias="X-Crowscap-User-Image"),
    user_provider: str | None = Header(default=None, alias="X-Crowscap-User-Provider"),
) -> CurrentUser:
    """Accept identity only from the trusted Next.js proxy.

    The browser never gets to choose its own Crowscap user. NextAuth verifies
    Google in the frontend, then the proxy forwards a signed internal identity.
    """

    settings = get_settings()

    mobile_user = _current_user_from_mobile_token(
        db=db,
        authorization=authorization,
        jwt_secret=settings.crowscap_jwt_secret,
    )
    if mobile_user is not None:
        return mobile_user

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
        provider=user_provider or "google",
    )

    return CurrentUser(id=user_id, email=user_email, name=user_name, image_url=user_image)


def normalize_google_user_id(value: str | None) -> str:
    safe = (value or "user").replace(" ", "")
    safe = re.sub(r"[^a-zA-Z0-9_.:-]", "", safe)[:34]
    return f"g_{safe or 'user'}"


def issue_mobile_session_token(
    *,
    user_id: str,
    email: str,
    name: str | None,
    image_url: str | None,
    provider: str,
    days: int = 30,
) -> tuple[str, datetime.datetime]:
    settings = get_settings()
    expires_at = utc_now() + datetime.timedelta(days=days)
    payload = {
        "aud": "crowscap-mobile",
        "iss": "crowscap-api",
        "sub": user_id,
        "email": email,
        "name": name,
        "picture": image_url,
        "provider": provider,
        "exp": expires_at,
        "iat": utc_now(),
    }
    token = jwt.encode(payload, settings.crowscap_jwt_secret, algorithm="HS256")
    return token, expires_at


def _current_user_from_mobile_token(
    *,
    db: Session,
    authorization: str | None,
    jwt_secret: str,
) -> CurrentUser | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None

    settings = get_settings()
    if (
        settings.crowscap_mobile_demo_enabled
        and secrets.compare_digest(token.strip(), settings.crowscap_mobile_demo_token)
    ):
        _upsert_user(
            db=db,
            user_id="demo_yc_user",
            email="yc@crowscap.xyz",
            name="YC Reviewer",
            image_url=None,
            provider="mobile_demo",
        )
        _seed_demo_user_data(db, "demo_yc_user")
        return CurrentUser(
            id="demo_yc_user",
            email="yc@crowscap.xyz",
            name="YC Reviewer",
            image_url=None,
        )

    try:
        payload = jwt.decode(
            token.strip(),
            jwt_secret,
            algorithms=["HS256"],
            audience="crowscap-mobile",
        )
    except InvalidTokenError:
        logger.warning("🔒 auth.rejected reason=bad_mobile_token")
        raise HTTPException(status_code=401, detail="Authentication required.")

    user_id = str(payload.get("sub") or "").strip()
    user_email = str(payload.get("email") or "").strip().lower()
    user_name = str(payload.get("name") or "").strip() or None
    user_image = str(payload.get("picture") or "").strip() or None
    provider = str(payload.get("provider") or "mobile").strip() or "mobile"

    if not _SAFE_USER_ID.fullmatch(user_id) or "@" not in user_email:
        logger.warning("🔒 auth.rejected reason=invalid_mobile_identity")
        raise HTTPException(status_code=401, detail="Authentication required.")

    _upsert_user(
        db=db,
        user_id=user_id,
        email=user_email,
        name=user_name,
        image_url=user_image,
        provider=provider,
    )
    return CurrentUser(id=user_id, email=user_email, name=user_name, image_url=user_image)


def _seed_demo_user_data(db: Session, user_id: str) -> None:
    """Pre-populate a demo workspace with rich sample memories, sources, and conversation."""
    existing_source = db.scalar(select(Source).where(Source.user_id == user_id))
    if existing_source is not None:
        return

    # Create Sources
    src1 = Source(
        id=f"src_pg_{user_id[:8]}",
        user_id=user_id,
        source_type="web",
        title="Do Things That Don't Scale - Paul Graham",
        original_url="https://paulgraham.com/ds.html",
        author="Paul Graham",
        publisher="Y Combinator",
    )
    src2 = Source(
        id=f"src_pmf_{user_id[:8]}",
        user_id=user_id,
        source_type="youtube",
        title="How to Find Product Market Fit & Retention",
        original_url="https://youtube.com/watch?v=demo_pmf",
        author="YC Startup School",
        publisher="Y Combinator",
    )
    src3 = Source(
        id=f"src_qwen_{user_id[:8]}",
        user_id=user_id,
        source_type="pdf",
        title="Qwen Cloud Agent Memory Architecture Paper",
        original_url="https://arxiv.org/abs/2401.memory",
        author="Alibaba Qwen Research",
    )
    db.add_all([src1, src2, src3])

    # Create Captures
    cap1 = Capture(id=f"cap_pg_{user_id[:8]}", user_id=user_id, source_id=src1.id, status="completed")
    cap2 = Capture(id=f"cap_pmf_{user_id[:8]}", user_id=user_id, source_id=src2.id, status="completed")
    cap3 = Capture(id=f"cap_qwen_{user_id[:8]}", user_id=user_id, source_id=src3.id, status="completed")
    db.add_all([cap1, cap2, cap3])

    # Create Memory Atoms
    m1 = Memory(
        id=f"mem_1_{user_id[:8]}",
        user_id=user_id,
        source_id=src1.id,
        capture_id=cap1.id,
        memory_type="principle",
        epistemic_label="framework",
        content="Unscalable manual recruitment of initial users builds the early feedback loop that defines product-market fit.",
        summary="Recruit your first 100 users manually before attempting automated distribution.",
        confidence="high",
        importance_score=0.95,
        status="active",
    )
    m2 = Memory(
        id=f"mem_2_{user_id[:8]}",
        user_id=user_id,
        source_id=src2.id,
        capture_id=cap2.id,
        memory_type="principle",
        epistemic_label="factual_claim",
        content="Retention curves must flatten horizontally. If cohort retention keeps dropping to zero, growth cannot compound.",
        summary="Flattening cohort retention curves prove real product-market fit.",
        confidence="high",
        importance_score=0.92,
        status="active",
    )
    m3 = Memory(
        id=f"mem_3_{user_id[:8]}",
        user_id=user_id,
        source_id=src3.id,
        capture_id=cap3.id,
        memory_type="claim",
        epistemic_label="factual_claim",
        content="Retrieving small source-aware atomic memories outperforms full-document retrieval within tight LLM context windows.",
        summary="Atomic memory extraction keeps AI context lean and prevents hallucinated facts.",
        confidence="high",
        importance_score=0.98,
        status="active",
    )
    db.add_all([m1, m2, m3])

    # Create Demo Conversation
    conv = Conversation(
        id=f"conv_demo_{user_id[:8]}",
        user_id=user_id,
        title="YC Demo Memory Audit & Strategy",
        status="active",
    )
    db.add(conv)

    msg1 = ChatMessage(
        conversation_id=conv.id,
        user_id=user_id,
        role="user",
        content="What do I know about early user acquisition and product retention?",
    )
    msg2 = ChatMessage(
        conversation_id=conv.id,
        user_id=user_id,
        role="assistant",
        content="Based on your saved sources (**Paul Graham Essay** & **YC PMF Guide**):\n\n1. **Manual Acquisition**: Recruit your first 100 users manually. Do things that don't scale to establish a tight feedback loop.\n2. **Retention Criterion**: Ensure your cohort retention curve flattens horizontally. Compound growth is impossible if retention drops to zero.\n\nYour memory engine has indexed 3 atomic memories across 3 sources.",
    )
    db.add_all([msg1, msg2])

    # Create User Preference
    pref = UserPreference(
        id=f"pref_{user_id[:8]}",
        user_id=user_id,
        profile_key=f"profile_{user_id}",
        evidence_strictness="high",
        topics_of_interest=["startups", "product-market fit", "memory agents", "distribution"],
    )
    db.add(pref)
    db.commit()


def _upsert_user(
    *,
    db: Session,
    user_id: str,
    email: str,
    name: str | None,
    image_url: str | None,
    provider: str = "google",
) -> None:
    user = db.get(User, user_id)
    is_new = False
    if user is None:
        existing_by_email = db.scalar(select(User).where(User.email == email))
        if existing_by_email is not None:
            user = existing_by_email
        else:
            user = User(id=user_id, email=email, provider=provider)
            db.add(user)
            is_new = True

    user.email = email
    user.name = name
    user.image_url = image_url
    user.last_seen_at = utc_now()
    db.commit()

    if provider in {"demo", "mobile_demo"}:
        _seed_demo_user_data(db, user_id)
