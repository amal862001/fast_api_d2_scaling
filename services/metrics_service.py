from prometheus_client import Counter, Gauge

# ── Custom metrics ────────────────────────────────────────────

cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["endpoint"]
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["endpoint"]
)

active_ws_connections = Gauge(
    "active_ws_connections",
    "Currently active WebSocket connections"
)

report_jobs_total = Counter(
    "report_jobs_total",
    "Total report jobs submitted",
    ["status"]   # queued, complete, failed
)