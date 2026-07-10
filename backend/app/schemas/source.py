from pydantic import BaseModel


class SourceContentResponse(BaseModel):
    source_id: str
    source_type: str
    title: str | None
    original_url: str | None
    original_content: str | None
