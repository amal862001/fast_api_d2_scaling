from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models.user import PlatformUser
from config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.user import PlatformUser

# password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Password helpers 

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)   # checks if plain password matches the hashed password, returns True or False


# JWT helpers 

def create_access_token(user: PlatformUser) -> str:
    payload = {
        "sub"         : str(user.id),
        "agency_code" : user.agency_code,
        "role"        : user.role,
        "exp"         : datetime.now(timezone.utc) + timedelta(minutes=30)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


# User helpers

async def get_user_by_email(db: AsyncSession, email: str) -> PlatformUser:
    result = await db.execute(
        select(PlatformUser).where(PlatformUser.email == email)
    )
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> PlatformUser:
    result = await db.execute(
        select(PlatformUser).where(PlatformUser.id == user_id)
    )
    return result.scalars().first()


async def create_user(db: AsyncSession, full_name: str, email: str, password: str, agency_code: str, role: str) -> PlatformUser:
    existing = await get_user_by_email(db, email)
    if existing:
        return None

    user = PlatformUser(
        full_name       = full_name,
        email           = email,
        hashed_password = hash_password(password),
        agency_code     = agency_code,
        role            = role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> PlatformUser:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
