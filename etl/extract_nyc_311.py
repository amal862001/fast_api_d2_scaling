"""
NYC 311 Service Requests Data Extractor
Source: https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9
API: Socrata Open Data API (SODA)
"""

import requests
import pandas as pd
import os
import time
from datetime import datetime


# ── Configuration ────────────────────────────────────────────────────────────

DATASET_ID = "erm2-nwe9"
BASE_URL = f"https://data.cityofnewyork.us/resource/{DATASET_ID}.json"

# Optional: register for a free app token at https://data.cityofnewyork.us/login
# to get higher rate limits (unauthenticated requests are throttled).
APP_TOKEN = os.getenv("NYC_OPEN_DATA_TOKEN", "")  # set env var or paste token here

PAGE_SIZE = 50_000     # rows per request (max allowed by SODA)
MAX_ROWS  = 500_000   # cap at 500,000 rows

OUTPUT_FILE = "nyc_311_requests.csv"

# Optional server-side filters (SoQL WHERE clause). Set to "" to fetch everything.
# Examples:
#   "created_date >= '2024-01-01'"
#   "complaint_type = 'Noise - Residential'"
WHERE_CLAUSE = ""      # e.g. "created_date >= '2024-01-01'"

# ── Helpers ──────────────────────────────────────────────────────────────────

def build_headers() -> dict:
    headers = {"Accept": "application/json"}
    if APP_TOKEN:
        headers["X-App-Token"] = APP_TOKEN
    return headers


def fetch_page(offset: int, limit: int) -> list[dict]:
    params = {
        "$limit":  limit,
        "$offset": offset,
        "$order":  "unique_key ASC",   # stable ordering required for reliable pagination
    }
    if WHERE_CLAUSE:
        params["$where"] = WHERE_CLAUSE

    resp = requests.get(BASE_URL, headers=build_headers(), params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def get_total_row_count() -> int:
    """Return the total number of rows matching the filter (uses $select=count(*))."""
    params = {"$select": "count(*) as total"}
    if WHERE_CLAUSE:
        params["$where"] = WHERE_CLAUSE
    resp = requests.get(BASE_URL, headers=build_headers(), params=params, timeout=30)
    print("******************************")
    print(resp.json())
    print("*******************************")
    resp.raise_for_status()
    return int(resp.json()[0]["total"])


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("NYC 311 Service Requests – Data Extractor")
    print(f"Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Get total row count
    print("\n[1/3] Fetching total row count …")
    total_available = get_total_row_count()
    total_to_fetch  = total_available if MAX_ROWS is None else min(MAX_ROWS, total_available)
    print(f"      Rows available : {total_available:,}")
    print(f"      Rows to fetch  : {total_to_fetch:,}")
    print(f"      Pages (~{PAGE_SIZE:,}/page): {-(-total_to_fetch // PAGE_SIZE):,}")

    # 2. Paginate through the API
    print("\n[2/3] Downloading data …")
    all_frames = []
    offset     = 0
    page_num   = 0

    while offset < total_to_fetch:
        limit    = min(PAGE_SIZE, total_to_fetch - offset)
        page_num += 1
        print(f"      Page {page_num:>4} | offset={offset:>10,} | limit={limit:,}", end="", flush=True)

        try:
            rows = fetch_page(offset, limit)
        except requests.HTTPError as e:
            print(f"  ✗  HTTP error: {e}")
            break

        if not rows:
            print("  – empty response, stopping.")
            break

        all_frames.append(pd.DataFrame(rows))
        print(f"  ✓  ({len(rows):,} rows received)")

        offset += len(rows)

        # Avoid hammering the API without a token
        if not APP_TOKEN:
            time.sleep(0.25)

    # 3. Combine & save
    print("\n[3/3] Saving …")
    if not all_frames:
        print("      No data retrieved. Exiting.")
        return

    df = pd.concat(all_frames, ignore_index=True)
    print(f"      Total rows : {len(df):,}")
    print(f"      Columns    : {df.columns.tolist()}")

    df.to_csv(OUTPUT_FILE, index=False)
    size_mb = os.path.getsize(OUTPUT_FILE) / 1_048_576
    print(f"\n✅  Saved → {OUTPUT_FILE}  ({size_mb:.1f} MB)")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(df.head(2))


if __name__ == "__main__":
    main()
