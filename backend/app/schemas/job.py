from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.capture import TextCaptureResponse, UrlCaptureRequest

ProcessingJobStatus = Literal["queued", "running", "succeeded", "failed", "retrying"]
ProcessingJobType = Literal["url_capture"]


class UrlCaptureJobRequest(UrlCaptureRequest):
    pass


class ProcessingJobResponse(BaseModel):
    id: str
    job_type: ProcessingJobType | str
    status: ProcessingJobStatus | str
    step: str
    attempts: int
    capture_id: str | None = None
    source_id: str | None = None
    error_code: str | None = None
    error_message_safe: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: TextCaptureResponse | None = None


class ProcessingJobCreatedResponse(BaseModel):
    job_id: str
    status: ProcessingJobStatus | str = "queued"
    status_url: str = Field(description="API path the frontend can poll for status.")
