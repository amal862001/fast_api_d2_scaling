from sqlalchemy.ext.asyncio import AsyncSession
from models.audit_log import AuditLog


async def write_audit_log(
    db           : AsyncSession,
    user_id      : int,
    agency_code  : str,
    endpoint     : str,
    query_params : dict,
    result_count : int
):
    try:
        log = AuditLog(
            user_id      = user_id,
            agency_code  = agency_code,
            endpoint     = endpoint,
            query_params = query_params,
            result_count = result_count
        )
        db.add(log)
        await db.commit()
    except Exception as e:
        # never let audit logging break the main request
        print(f"Audit log failed: {e}")