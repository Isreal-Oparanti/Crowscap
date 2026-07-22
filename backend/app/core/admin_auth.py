import jwt
from fastapi import Request, HTTPException
from app.core.config import get_settings

def require_admin(request: Request):
    """
    Dependency to verify the admin_token cookie.
    Raises HTTPException if missing or invalid.
    """
    settings = get_settings()
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    try:
        payload = jwt.decode(token, settings.crowscap_jwt_secret, algorithms=["HS256"])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Forbidden.")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")
