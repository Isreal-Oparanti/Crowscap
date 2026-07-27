from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PushPublicKeyResponse(BaseModel):
    configured: bool
    public_key: str | None = None


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=20)
    auth: str = Field(min_length=8)


class PushSubscriptionPayload(BaseModel):
    endpoint: str = Field(min_length=20)
    keys: PushSubscriptionKeys


class PushSubscriptionRequest(BaseModel):
    subscription: PushSubscriptionPayload
    user_agent: str | None = Field(default=None, max_length=1000)


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=20)


class PushSubscriptionResponse(BaseModel):
    status: Literal["active", "disabled"]
    configured: bool


class NotificationEvent(BaseModel):
    event_id: str
    event_key: str
    event_type: Literal["heartbeat", "reminder_due", "recall_due"]
    due_count: int = 0
    title: str
    body: str
    url: str
    reminder_id: str | None = None
    memory_id: str | None = None
    created_at: datetime


class NotificationEventResponse(BaseModel):
    event: NotificationEvent
