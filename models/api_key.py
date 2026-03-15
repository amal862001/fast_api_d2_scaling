from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from models.user import Base

class ApiKey(Base):
    __tablename__ = "api_keys"

    id           : Mapped[int]            = mapped_column(Integer, primary_key=True, index=True)
    key_prefix   : Mapped[str]            = mapped_column(String(8),  nullable=False)
    key_hash     : Mapped[str]            = mapped_column(String(64), nullable=False, unique=True, index=True)
    owner_id     : Mapped[int]            = mapped_column(Integer, ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False, index=True)
    scopes       : Mapped[list[str]]      = mapped_column(ARRAY(String), nullable=False, default=[])
    created_at   : Mapped[datetime]       = mapped_column(DateTime, nullable=False, default=datetime.now)
    expires_at   : Mapped[datetime | None]= mapped_column(DateTime, nullable=True)
    last_used_at : Mapped[datetime | None]= mapped_column(DateTime, nullable=True)