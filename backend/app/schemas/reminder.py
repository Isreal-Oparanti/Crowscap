from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReminderResponse(BaseModel):
    id: str
    content: str
    due_at: datetime
    status: str
    save_as_memory: bool
    memory_id: str | None = None
    conversation_id: str | None = None
    created_at: datetime


class ReminderSnoozeRequest(BaseModel):
    minutes: int = Field(default=60, ge=1, le=10_080)
