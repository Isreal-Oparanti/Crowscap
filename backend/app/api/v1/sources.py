from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Source
from app.db.session import get_db
from app.schemas.source import SourceContentResponse

router = APIRouter(tags=["sources"])


@router.get("/{source_id}", response_model=SourceContentResponse)
def get_source_content(
    source_id: str,
    db: Session = Depends(get_db),
) -> SourceContentResponse:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")

    return SourceContentResponse(
        source_id=source.id,
        source_type=source.source_type,
        title=source.title,
        original_url=source.original_url,
        original_content=source.raw_text,
    )
