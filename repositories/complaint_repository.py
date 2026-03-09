from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.future import select
from models.complaint import Complaint
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func, distinct, Integer


class ComplaintRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # Get single complaint by ID 

    async def get_by_id(self, unique_key: int, agency_code: str) -> Complaint | None:
        result = await self.db.execute(
            select(Complaint).where(
                Complaint.unique_key == unique_key,
                Complaint.agency     == agency_code
            )
        )
        return result.scalars().first()   # returns single complaint or None if not found

    # List complaints with filters

    async def list_paginated(
        self,
        agency_code    : str,
        borough        : Optional[str]      = None,
        complaint_type : Optional[str]      = None,
        status         : Optional[str]      = None,
        start_date     : Optional[datetime] = None,
        end_date       : Optional[datetime] = None,
        page           : int                = 1,
        limit          : int                = 50
    ) -> list[Complaint]:

        query = select(Complaint).where(
            Complaint.agency == agency_code
        )

        if borough:
            query = query.where(Complaint.borough == borough.upper())

        if complaint_type:
            query = query.where(Complaint.complaint_type == complaint_type)

        if status:
            query = query.where(Complaint.status == status)

        if start_date:
            query = query.where(Complaint.created_date >= start_date)

        if end_date:
            query = query.where(Complaint.created_date <= end_date)

        # pagination
        offset = (page - 1) * limit
        query  = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    # ── List complaints by agency ─────────────────────────────

    async def list_by_agency(self, agency_code: str, limit: int = 50) -> list[Complaint]:
        result = await self.db.execute(
            select(Complaint)
            .where(Complaint.agency == agency_code)
            .limit(limit)
        )
        return result.scalars().all()

    # Create complaint 

    async def create(
        self,
        agency_code    : str,
        complaint_type : str,
        borough        : str,
        descriptor     : Optional[str]   = None,
        incident_zip   : Optional[str]   = None,
        city           : Optional[str]   = None,
        location_type  : Optional[str]   = None,
        latitude       : Optional[float] = None,
        longitude      : Optional[float] = None,
    ) -> Complaint:

        complaint = Complaint(
            complaint_type = complaint_type,
            descriptor     = descriptor,
            incident_zip   = incident_zip,
            city           = city,
            borough        = borough.upper(),
            location_type  = location_type,
            latitude       = latitude,
            longitude      = longitude,
            agency         = agency_code,
            agency_name    = agency_code,
            status         = "Open",
            created_date   = datetime.now().replace(tzinfo=None)
        )

        self.db.add(complaint)
        await self.db.commit()
        await self.db.refresh(complaint)
        return complaint
    


    # Get distinct complaint types

    async def get_complaint_types(self, agency_code: str) -> list[str]:
        result = await self.db.execute(
            select(distinct(Complaint.complaint_type))
            .where(Complaint.agency == agency_code)
            .order_by(Complaint.complaint_type)
        )
        return [row[0] for row in result.fetchall()]   # extract complaint_type from each row which is a tuple like (complaint_type,)


    # Get complaint count per borough

    async def get_borough_stats(self, agency_code: str) -> list[dict]:
        result = await self.db.execute(
            select(
                Complaint.borough,
                func.count(Complaint.unique_key).label("total"),
                func.sum(
                    func.cast(Complaint.status == "Open", Integer)
                ).label("open"),
                func.sum(
                    func.cast(Complaint.status == "Closed", Integer)
                ).label("closed")
            )
            .where(Complaint.agency == agency_code)
            .group_by(Complaint.borough)
            .order_by(func.count(Complaint.unique_key).desc())
        )

        return [
            {
                "borough" : row.borough,
                "total"   : row.total,
                "open"    : row.open or 0,
                "closed"  : row.closed or 0
            }
            for row in result.fetchall()
        ]


    
    