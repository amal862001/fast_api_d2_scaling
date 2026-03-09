from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.auth_service import decode_access_token, get_user_by_id
from models.user import PlatformUser
from repositories.complaint_repository import ComplaintRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token : str          = Depends(oauth2_scheme),
    db    : AsyncSession = Depends(get_db)
) -> PlatformUser:

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