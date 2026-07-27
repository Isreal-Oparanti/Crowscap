from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_current_user
from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.schemas.notifications import (
    NotificationEventResponse,
    PushPublicKeyResponse,
    PushSubscriptionRequest,
    PushSubscriptionResponse,
    PushUnsubscribeRequest,
)
from app.services.notification_service import (
    deactivate_push_subscription,
    get_current_notification_event,
    get_push_public_key,
    upsert_push_subscription,
)

router = APIRouter(tags=["notifications"])


@router.get("/push/public-key", response_model=PushPublicKeyResponse)
def push_public_key(
    _current_user: CurrentUser = Depends(require_current_user),
) -> PushPublicKeyResponse:
    configured, public_key = get_push_public_key()
    return PushPublicKeyResponse(configured=configured, public_key=public_key)


@router.post("/push/subscribe", response_model=PushSubscriptionResponse)
def subscribe_push(
    payload: PushSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> PushSubscriptionResponse:
    configured, _public_key = get_push_public_key()
    upsert_push_subscription(
        db=db,
        user_id=current_user.id,
        payload=payload.subscription,
        user_agent=payload.user_agent,
    )
    return PushSubscriptionResponse(status="active", configured=configured)


@router.post("/push/unsubscribe", response_model=PushSubscriptionResponse)
def unsubscribe_push(
    payload: PushUnsubscribeRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> PushSubscriptionResponse:
    configured, _public_key = get_push_public_key()
    deactivate_push_subscription(
        db=db,
        user_id=current_user.id,
        endpoint=payload.endpoint,
    )
    return PushSubscriptionResponse(status="disabled", configured=configured)


@router.get("/current", response_model=NotificationEventResponse)
def current_notification(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> NotificationEventResponse:
    event = get_current_notification_event(db=db, user_id=current_user.id)
    return NotificationEventResponse(event=event)


@router.get("/stream")
async def notification_stream(
    request: Request,
    current_user: CurrentUser = Depends(require_current_user),
) -> StreamingResponse:
    settings = get_settings()
    interval = max(10.0, settings.crowscap_notification_stream_interval_seconds)

    async def events() -> AsyncIterator[str]:
        last_event_key: str | None = None
        yield "event: connected\ndata: {\"status\":\"ok\"}\n\n"

        while not await request.is_disconnected():
            with SessionLocal() as db:
                event = get_current_notification_event(db=db, user_id=current_user.id)
            if event.event_type == "heartbeat":
                yield f"event: heartbeat\ndata: {event.model_dump_json()}\n\n"
            elif event.event_key != last_event_key:
                last_event_key = event.event_key
                yield f"event: {event.event_type}\ndata: {event.model_dump_json()}\n\n"

            await asyncio.sleep(interval)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
