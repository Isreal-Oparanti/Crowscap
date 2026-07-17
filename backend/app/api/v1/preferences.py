from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_current_user
from app.db.session import get_db
from app.schemas.preference import UserPreferenceLearningResponse, UserPreferenceResponse
from app.services.preference_service import (
    autonomously_update_preferences,
    get_or_create_user_preferences,
    preference_response,
)

router = APIRouter(tags=["preferences"])


@router.get("/me", response_model=UserPreferenceResponse)
def my_preferences(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> UserPreferenceResponse:
    profile = get_or_create_user_preferences(db=db, user_id=current_user.id)
    return preference_response(profile)


@router.post("/learn-now", response_model=UserPreferenceLearningResponse)
def learn_now(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> UserPreferenceLearningResponse:
    learning = autonomously_update_preferences(db=db, user_id=current_user.id, force=True)
    db.commit()
    return UserPreferenceLearningResponse(
        preferences=preference_response(learning.profile),
        updates=learning.updates,
    )
