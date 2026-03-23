import os
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from database import get_db
from models.api_key import ApiKey
from dependencies import get_current_user, require_scope
from models.user import PlatformUser


router = APIRouter(prefix="/auth/api-keys", tags=["API Keys"])


# Schemas

class ApiKeyCreate(BaseModel):
    scopes      : list[str]       = ["complaints:read"]
    expires_at  : Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    id          : int
    key_prefix  : str
    scopes      : list[str]
    created_at  : datetime
    expires_at  : Optional[datetime]
    last_used_at: Optional[datetime]


class ApiKeyCreated(ApiKeyResponse):
    plain_key   : str    # returned ONCE only on creation


# Helpers 

def _hash_key(plain_key: str) -> str:
    return hashlib.sha256(plain_key.encode()).hexdigest()


def _generate_key() -> tuple[str, str, str]:
    # 32 cryptographically random bytes → hex string
    plain_key  = "nyc311_" + os.urandom(32).hex()
    prefix     = plain_key[:8]           # "nyc311_x" — shown to user
    key_hash   = _hash_key(plain_key)    # stored in DB
    return plain_key, prefix, key_hash


# POST /auth/api-keys — generate new key

@router.post("", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    body         : ApiKeyCreate,
    db           : AsyncSession  = Depends(get_db),
    current_user : PlatformUser  = Depends(require_scope("admin"))
):
    plain_key, prefix, key_hash = _generate_key()

    expires_at = body.expires_at.replace(tzinfo=None) if body.expires_at else None

    api_key = ApiKey(
        key_prefix   = prefix,
        key_hash     = key_hash,
        owner_id     = current_user.id,
        scopes       = body.scopes,
        created_at   = datetime.utcnow(),
        expires_at   = expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyCreated(
        id           = api_key.id,
        key_prefix   = api_key.key_prefix,
        scopes       = api_key.scopes,
        created_at   = api_key.created_at,
        expires_at   = api_key.expires_at,
        last_used_at = api_key.last_used_at,
        plain_key    = plain_key       # ← only time it is ever returned
    )


# GET /auth/api-keys — list user's keys 
@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    db           : AsyncSession = Depends(get_db),
    current_user : PlatformUser = Depends(get_current_user)
):
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.owner_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
    )
    return [
        ApiKeyResponse(
            id           = k.id,
            key_prefix   = k.key_prefix,
            scopes       = k.scopes,
            created_at   = k.created_at,
            expires_at   = k.expires_at,
            last_used_at = k.last_used_at,
        )
        for k in result.scalars().all()
    ]


# DELETE /auth/api-keys/{id} — revoke key

@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id       : int,
    db           : AsyncSession = Depends(get_db),
    current_user : PlatformUser = Depends(get_current_user)
):
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id       == key_id,
            ApiKey.owner_id == current_user.id   # owner check — can't delete others' keys
        )
    )
    key = result.scalars().first()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.execute(delete(ApiKey).where(ApiKey.id == key_id))
    await db.commit()