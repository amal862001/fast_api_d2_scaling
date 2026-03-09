from sqlalchemy import Column, Integer, String, DateTime, JSON
from models.user import Base
from datetime import datetime, timezone

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(Integer, nullable=False)
    agency_code  = Column(String, nullable=False)
    endpoint     = Column(String, nullable=False)
    query_params = Column(JSON, nullable=True)
    result_count = Column(Integer, nullable=True)
    timestamp    = Column(DateTime, default=lambda: datetime.now().replace(tzinfo=None))