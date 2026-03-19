import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.cache_service import get_redis
from services.metrics_service import active_ws_connections
import asyncio


router = APIRouter(tags=["WebSocket"])

BOROUGHS = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]


# Build payload from Redis keys

async def build_live_payload() -> dict:
    redis = await get_redis()

    # open counts per borough
    by_borough = {}
    for borough in BOROUGHS:
        key   = f"borough_stats:{borough}:open_count"
        value = await redis.get(key)
        by_borough[borough] = int(value) if value else 0

    # global stats
    last_hour = await redis.get("global:complaints_last_hour")
    top_type  = await redis.get("global:top_complaint_type")

    return {
        "timestamp"              : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_open_complaints"  : sum(by_borough.values()),
        "complaints_last_hour"   : int(last_hour) if last_hour else 0,
        "by_borough"             : by_borough,
        "top_complaint_type"     : top_type or "N/A"
    }


# WebSocket endpoint

@router.websocket("/ws/live")
async def live_dashboard(websocket: WebSocket):
    await websocket.accept()
    active_ws_connections.inc()          # ← increment on connect
    client = websocket.client.host
    print(f"WebSocket connected: {client}")

    try:
        while True:
            payload = await build_live_payload()
            await websocket.send_json(payload)
            await asyncio.sleep(3)

    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {client}")

    finally:
        active_ws_connections.dec()      # ← decrement on disconnect
        print(f"WebSocket closed: {client}")
