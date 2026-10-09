from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_current_user
from app.db.models import Source
from app.db.session import get_db
from app.schemas.source import SourceContentResponse

router = APIRouter(tags=["sources"])


@router.get("/{source_id}", response_model=SourceContentResponse)
def get_source_content(
    source_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> SourceContentResponse:
    source = db.get(Source, source_id)
    if source is None or source.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Source not found.")

    return SourceContentResponse(
        source_id=source.id,
        source_type=source.source_type,
        title=source.title,
        original_url=source.original_url,
        # Prefer the organized markdown overview; fall back to raw_text
        # when extraction hasn't produced one yet (e.g. a reference-link
        # stub still waiting on its background enrichment job).
        original_content=source.summary_markdown or source.raw_text,
        raw_text=source.raw_text,
    )
