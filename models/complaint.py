from sqlalchemy import Column, BigInteger, String, DateTime, Float, Text, Index, Identity
from sqlalchemy.orm import declarative_base
from models.user import Base

class Complaint(Base):
    __tablename__ = "nyc_311_service_requests"

    # Primary Key
    unique_key                     = Column(BigInteger, primary_key=True)

    # Required Fields
    created_date                   = Column(DateTime, nullable=False)
    agency                         = Column(String(10), nullable=False)
    agency_name                    = Column(String(255), nullable=False)
    complaint_type                 = Column(String(255), nullable=False)
    borough                        = Column(String(50), nullable=False)
    status                         = Column(String(50), nullable=False)

    # Optional Fields
    closed_date                    = Column(DateTime, nullable=True)
    descriptor                     = Column(String(255), nullable=True)
    location_type                  = Column(String(255), nullable=True)
    incident_zip                   = Column(String(10), nullable=True)
    city                           = Column(String(100), nullable=True)
    resolution_description         = Column(Text, nullable=True)
    latitude                       = Column(Float, nullable=True)
    longitude                      = Column(Float, nullable=True)
    resolution_action_updated_date = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_agency_borough_date", "agency", "borough", "created_date"),
    )