from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_current_user
from app.db.session import get_db
from app.schemas.job import ProcessingJobCreatedResponse, ProcessingJobResponse, UrlCaptureJobRequest
from app.services.job_service import create_url_capture_job, get_processing_job, run_url_capture_job

router = APIRouter(tags=["jobs"])


@router.post("/captures/url", response_model=ProcessingJobCreatedResponse, status_code=202)
def create_url_job(
    payload: UrlCaptureJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> ProcessingJobCreatedResponse:
    response = create_url_capture_job(db=db, payload=payload, user_id=current_user.id)
    background_tasks.add_task(run_url_capture_job, response.job_id)
    return response


@router.get("/{job_id}", response_model=ProcessingJobResponse)
def job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> ProcessingJobResponse:
    job = get_processing_job(db=db, job_id=job_id, user_id=current_user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Processing job not found.")
    return job
