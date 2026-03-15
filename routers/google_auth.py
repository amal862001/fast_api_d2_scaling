import httpx
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from database import get_db
from models.user import PlatformUser
from services.auth_service import create_access_token
from config import settings

router = APIRouter(prefix="/auth", tags=["Google OAuth"])

# OAuth client setup
oauth = OAuth()
oauth.register(
    name                 = "google",
    client_id            = settings.GOOGLE_CLIENT_ID,
    client_secret        = settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url  = "https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs        = {"scope": "openid email profile"},
)


# GET /auth/google — redirect to Google login

@router.get("/google")
async def google_login(request: Request):
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


# GET /auth/google/callback — handle Google response

@router.get("/google/callback")
async def google_callback(
    request : Request,
    db      : AsyncSession = Depends(get_db)
):
    try:
        token    = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")

    # extract user info from Google's ID token
    userinfo = token.get("userinfo")
    if not userinfo:
        async with httpx.AsyncClient() as client:
            resp     = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token['access_token']}"}
            )
            userinfo = resp.json()

    email = userinfo.get("email")
    name  = userinfo.get("name", email)

    if not email:
        raise HTTPException(status_code=400, detail="No email returned from Google")

    # Find existing user or auto-provision 
    result = await db.execute(
        select(PlatformUser).where(PlatformUser.email == email)
    )
    user = result.scalars().first()

    if not user:
        user = PlatformUser(
            email           = email,
            full_name       = name,
            agency_code     = "DOITT",
            role            = "staff",
            hashed_password = "",        # no password — OAuth only
            created_at      = datetime.now().replace(tzinfo=None),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Issue JWT like normal login 
    access_token = create_access_token(user)

    return {
        "access_token" : access_token,
        "token_type"   : "bearer",
        "email"        : user.email,
        "agency_code"  : user.agency_code,
        "role"         : user.role,
        "scopes"       : ["complaints:read"] if user.role == "staff" else []
    }