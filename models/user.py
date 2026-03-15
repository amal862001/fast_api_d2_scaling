from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone 
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class PlatformUser(Base):
    __tablename__ = "platform_users"

    id              = Column(Integer, primary_key=True, autoincrement=True, index=True)
    email           = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name       = Column(String, nullable=False)
    agency_code     = Column(String, nullable=False)
    role            = Column(String, nullable=False, default="staff")
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))

