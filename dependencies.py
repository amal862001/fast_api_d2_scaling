from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.auth_service import decode_access_token, get_user_by_id
from models.user import PlatformUser
from repositories.complaint_repository import ComplaintRepository

import hashlib
from datetime import datetime
from fastapi import Header, HTTPException
from sqlalchemy import select
from models.api_key import ApiKey
from fastapi.security import SecurityScopes
from config import settings
from jose import jwt, JWTError


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    request : Request,
    token   : str          = Depends(oauth2_scheme),
    db      : AsyncSession = Depends(get_db)
) -> PlatformUser:

    # Accept X-API-Key header as an alternative to Bearer token
    api_key_value = request.headers.get("X-API-Key")
    if api_key_value:
        key_hash = hashlib.sha256(api_key_value.encode()).hexdigest()
        result   = await db.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        )
        api_key = result.scalars().first()
        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        if api_key.expires_at and api_key.expires_at < datetime.now().replace(tzinfo=None):
            raise HTTPException(status_code=401, detail="API key expired")
        user_result = await db.execute(
            select(PlatformUser).where(PlatformUser.id == api_key.owner_id)
        )
        user = user_result.scalars().first()
        if not user:
            raise HTTPException(status_code=401, detail="API key owner not found")
        return user

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid or expired token"
        )

    user_id = int(payload.get("sub"))
    user    = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "User not found"
        )

    return user


async def get_complaint_repo(
    db: AsyncSession = Depends(get_db)
) -> ComplaintRepository:
    return ComplaintRepository(db)



async def get_api_key_user(
    x_api_key : str         = Header(...),
    db        : AsyncSession = Depends(get_db)
) -> PlatformUser:

    # hash the incoming key
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()

    # look up hash in DB
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    )
    api_key = result.scalars().first()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # check expiry
    if api_key.expires_at and api_key.expires_at < datetime.now().replace(tzinfo=None):
        raise HTTPException(status_code=401, detail="API key expired")

    # update last_used_at — fire and forget
    api_key.last_used_at = datetime.now().replace(tzinfo=None)
    await db.commit()

    # load and return the  user
    user_result = await db.execute(
        select(PlatformUser).where(PlatformUser.id == api_key.owner_id)
    )
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="API key owner not found")

    return user



    # require scope dependency for routes

def require_scope(required_scope: str):
    async def _check(
        current_user : PlatformUser = Depends(get_current_user),
        token        : str          = Depends(oauth2_scheme)
    ):
        # decode token to read scopes
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            token_scopes: list[str] = payload.get("scopes", [])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        if required_scope not in token_scopes:
            raise HTTPException(
                status_code  = 403,
                detail       = f"Scope '{required_scope}' required",
                headers      = {"WWW-Authenticate": f'Bearer scope="{required_scope}"'}
            )
        return current_user
    return _check