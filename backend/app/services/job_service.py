from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai.qwen_client import QwenClientError
from app.core.logging import get_logger
from app.db.models import ProcessingJob, utc_now
from app.db.session import SessionLocal
from app.schemas.capture import UrlCaptureRequest
from app.schemas.job import ProcessingJobCreatedResponse, ProcessingJobResponse
from app.services.embedding_service import EmbeddingError, get_memory_embedder
from app.services.extraction_service import ExtractionError, get_memory_extractor
from app.services.ingestion_service import IngestionError, create_url_capture
from app.services.relationship_service import get_memory_relation_detector

logger = get_logger("services.jobs")


def create_url_capture_job(
    *,
    db: Session,
    payload: UrlCaptureRequest,
    user_id: str | None = None,
) -> ProcessingJobCreatedResponse:
    job = ProcessingJob(
        user_id=user_id,
        job_type="url_capture",
        status="queued",
        step="queued",
        attempts=0,
        payload_json=payload.model_dump(mode="json"),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("📬 job.created id=%s type=%s", job.id, job.job_type)
    return ProcessingJobCreatedResponse(
        job_id=job.id,
        status=job.status,
        status_url=f"/api/v1/jobs/{job.id}",
    )


def get_processing_job(
    *,
    db: Session,
    job_id: str,
    user_id: str | None = None,
) -> ProcessingJobResponse | None:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        return None
    if user_id is not None and job.user_id != user_id:
        return None
    return _job_response(job)


def run_url_capture_job(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            logger.warning("⚠️ job.missing id=%s", job_id)
            return
        if job.status not in {"queued", "retrying"}:
            logger.info("ℹ️ job.skipped id=%s status=%s", job.id, job.status)
            return

        _mark_running(db=db, job=job, step="validating_url")

        try:
            payload = UrlCaptureRequest.model_validate(job.payload_json or {})
            _mark_step(db=db, job=job, step="extracting_source")
            capture = create_url_capture(
                db=db,
                payload=payload,
                extractor=get_memory_extractor(),
                embedder=get_memory_embedder(),
                relation_detector=get_memory_relation_detector(),
                user_id=job.user_id,
            )
            job.status = "succeeded"
            job.step = "ready"
            job.capture_id = capture.capture_id
            job.source_id = capture.source_id
            job.result_json = capture.model_dump(mode="json")
            job.error_code = None
            job.error_message_safe = None
            job.finished_at = utc_now()
            db.commit()
            logger.info(
                "✅ job.succeeded id=%s type=%s capture_id=%s memories=%s",
                job.id,
                job.job_type,
                capture.capture_id,
                len(capture.memories),
            )
        except (QwenClientError, ExtractionError, EmbeddingError, IngestionError, ValueError) as exc:
            _mark_failed(db=db, job=job, code=exc.__class__.__name__, message=str(exc))
        except Exception as exc:
            logger.exception("❌ job.unexpected id=%s", job.id)
            _mark_failed(
                db=db,
                job=job,
                code=exc.__class__.__name__,
                message="Crowscap could not process this capture job. Please try again.",
            )


def _mark_running(*, db: Session, job: ProcessingJob, step: str) -> None:
    job.status = "running"
    job.step = step
    job.attempts += 1
    job.started_at = utc_now()
    db.commit()
    logger.info("🏃 job.running id=%s step=%s attempts=%s", job.id, step, job.attempts)


def _mark_step(*, db: Session, job: ProcessingJob, step: str) -> None:
    job.step = step
    db.commit()
    logger.info("🔄 job.step id=%s step=%s", job.id, step)


def _mark_failed(*, db: Session, job: ProcessingJob, code: str, message: str) -> None:
    job.status = "failed"
    job.step = "failed"
    job.error_code = code
    job.error_message_safe = message[:1000]
    job.finished_at = utc_now()
    db.commit()
    logger.warning("⚠️ job.failed id=%s code=%s reason=%s", job.id, code, job.error_message_safe)


def _job_response(job: ProcessingJob) -> ProcessingJobResponse:
    result = None
    if job.result_json:
        result = job.result_json
    return ProcessingJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        step=job.step,
        attempts=job.attempts,
        capture_id=job.capture_id,
        source_id=job.source_id,
        error_code=job.error_code,
        error_message_safe=job.error_message_safe,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        result=result,
    )
