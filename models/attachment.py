from sqlalchemy import Column, Integer, String, DateTime, BigInteger
from models.user import Base
from datetime import datetime, timezone


class Attachment(Base):
    __tablename__ = "complaint_attachments"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    complaint_key  = Column(BigInteger, nullable=False)
    uploaded_by    = Column(Integer, nullable=False)     # user id
    agency_code    = Column(String, nullable=False)
    filename       = Column(String, nullable=False)      # original filename
    stored_name    = Column(String, nullable=False)      # uuid filename on disk
    file_type      = Column(String, nullable=False)      # image/pdf
    file_size      = Column(Integer, nullable=False)     # bytes
    uploaded_at    = Column(DateTime, default=lambda: datetime.now().replace(tzinfo=None))