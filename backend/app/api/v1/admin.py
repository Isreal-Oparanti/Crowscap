import datetime
import jwt
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.admin_auth import require_admin
from app.db.models import User, utc_now
from app.db.session import get_db

router = APIRouter(tags=["admin"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(request: LoginRequest, response: Response) -> dict[str, Any]:
    settings = get_settings()
    
    if request.username != settings.crowscap_admin_username or request.password != settings.crowscap_admin_password:
        return {"success": False, "message": "Invalid username or password"}

    # Generate JWT
    expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    payload = {
        "role": "admin",
        "exp": expiration
    }
    token = jwt.encode(payload, settings.crowscap_jwt_secret, algorithm="HS256")
    
    response.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=86400,
    )
    
    return {"success": True}

@router.post("/logout")
def logout(response: Response) -> dict[str, Any]:
    response.delete_cookie("admin_token")
    return {"success": True}

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    _=Depends(require_admin)
) -> dict[str, Any]:
    total_users = db.scalar(select(func.count(User.id))) or 0
    
    # Calculate today's users
    today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_users = db.scalar(select(func.count(User.id)).where(User.created_at >= today_start)) or 0
    
    return {
        "data": {
            "totalUsers": total_users,
            "todayUsers": today_users,
            "totalProjects": 0,
            "featuredProjects": 0,
            "verifiedUsers": 0,
        }
    }

@router.get("/users")
def get_users(
    page: int = 1,
    limit: int = 30,
    search: str = "",
    db: Session = Depends(get_db),
    _=Depends(require_admin)
) -> dict[str, Any]:
    query = select(User)
    
    if search:
        search_filter = f"%{search}%"
        query = query.where(User.email.ilike(search_filter) | User.name.ilike(search_filter))
    
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    
    query = query.order_by(desc(User.created_at)).offset((page - 1) * limit).limit(limit)
    users = db.scalars(query).all()
    
    pages = (total + limit - 1) // limit
    
    return {
        "data": {
            "users": [
                {
                    "_id": u.id,
                    "email": u.email,
                    "fullName": u.name,
                    "username": u.email.split("@")[0],
                    "googleId": u.provider == "google",
                    "createdAt": u.created_at.isoformat() if u.created_at else None,
                    "lastLogin": u.last_seen_at.isoformat() if u.last_seen_at else None,
                    "profilePicture": u.image_url,
                    "isEmailVerified": True, # Hardcoded for now as provider=google handles it
                }
                for u in users
            ],
            "total": total,
            "pages": pages
        }
    }

@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_admin)
) -> dict[str, Any]:
    user = db.get(User, user_id)
    if not user:
        return {"success": False, "message": "User not found"}
        
    db.delete(user)
    db.commit()
    return {"success": True}
