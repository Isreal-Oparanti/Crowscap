from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.preference import UserPreferenceResponse
from app.services.preference_service import get_or_create_user_preferences, preference_response

router = APIRouter(tags=["preferences"])


@router.get("/me", response_model=UserPreferenceResponse)
def my_preferences(db: Session = Depends(get_db)) -> UserPreferenceResponse:
    profile = get_or_create_user_preferences(db=db)
    return preference_response(profile)
