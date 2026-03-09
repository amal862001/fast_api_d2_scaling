from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum
import re


# Borough Enum

class BoroughEnum(str, Enum):
    MANHATTAN     = "MANHATTAN"
    BROOKLYN      = "BROOKLYN"
    QUEENS        = "QUEENS"
    BRONX         = "BRONX"
    STATEN_ISLAND = "STATEN ISLAND"


# Complaint Summary (list view - 8 fields)

class ComplaintSummary(BaseModel):
    unique_key     : int
    created_date   : datetime
    complaint_type : str
    descriptor     : Optional[str]
    borough        : str
    status         : str
    agency         : str
    incident_zip   : Optional[str]

    class Config:
        from_attributes = True      # Pydantic will read data from ORM objects using attribute access


# Complaint Detail (full record - all 16 fields)

class ComplaintDetail(BaseModel):
    unique_key                     : int
    created_date                   : datetime
    closed_date                    : Optional[datetime]
    agency                         : str
    agency_name                    : str
    complaint_type                 : str
    descriptor                     : Optional[str]
    location_type                  : Optional[str]
    incident_zip                   : Optional[str]
    city                           : Optional[str]
    borough                        : str
    status                         : str
    resolution_description         : Optional[str]
    latitude                       : Optional[float]
    longitude                      : Optional[float]
    resolution_action_updated_date : Optional[datetime]

    class Config:
        from_attributes = True 


# Complaint Create 

class ComplaintCreate(BaseModel):
    complaint_type : str
    borough        : str
    descriptor     : Optional[str]   = None
    incident_zip   : Optional[str]   = None
    city           : Optional[str]   = None
    location_type  : Optional[str]   = None
    latitude       : Optional[float] = None
    longitude      : Optional[float] = None

    # Borough validator
    @field_validator("borough", mode="before")
    @classmethod
    def normalize_borough(cls, value):
        if value is None:
            raise ValueError("Borough is required")

        # normalize to uppercase and strip whitespace
        normalized = str(value).strip().upper()

        # map common variations
        valid = {
            "MANHATTAN"    : "MANHATTAN",
            "BROOKLYN"     : "BROOKLYN",
            "QUEENS"       : "QUEENS",
            "BRONX"        : "BRONX",
            "THE BRONX"    : "BRONX",
            "STATEN ISLAND": "STATEN ISLAND",
            "STATEN"       : "STATEN ISLAND",
            "SI"           : "STATEN ISLAND",
        }

        if normalized not in valid:
            raise ValueError(
                f"Invalid borough '{value}'. Must be one of: MANHATTAN, BROOKLYN, QUEENS, BRONX, STATEN ISLAND"
            )

        return valid[normalized]

    # ZIP validator
    @field_validator("incident_zip", mode="before")
    @classmethod
    def normalize_zip(cls, value):
        if value is None:
            return None

        # clean the value
        cleaned = str(value).strip()

        # return None for known invalid values
        invalid_values = {"", "N/A", "n/a", "00000", "NA", "NONE", "NULL"}
        if cleaned in invalid_values:
            return None

        # validate 5 digit format
        if not re.match(r"^\d{5}$", cleaned):
            return None

        return cleaned


# Complaint Update

class ComplaintUpdate(BaseModel):
    status                 : Optional[str] = None
    resolution_description : Optional[str] = None