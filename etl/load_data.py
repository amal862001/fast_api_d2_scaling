import numpy as np
import pandas as pd
from sqlalchemy import create_engine
import os

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:your_password@db:5432/nyc_311"
).replace("asyncpg", "psycopg2")  # ETL uses sync driver

engine = create_engine(DATABASE_URL)

# Load raw CSV
print("Loading CSV...")
df = pd.read_csv("nyc_311_requests.csv", low_memory=False)  # fix DtypeWarning
print(f"Raw rows: {df.shape[0]:,}")

# Select 16 columns
df = df[[
    'unique_key', 'created_date', 'closed_date', 'agency',
    'agency_name', 'complaint_type', 'descriptor', 'location_type',
    'incident_zip', 'city', 'borough', 'status',
    'resolution_description', 'latitude', 'longitude',
    'resolution_action_updated_date'
]]

# Clean borough
df['borough'] = df['borough'].replace({"Unspecified": np.nan})
df['borough'] = df['borough'].str.upper().str.strip()
df = df.dropna(subset=['borough'])

# Clean city
df['city'] = df['city'].str.upper().str.strip()

# Fix dates
df['created_date']                   = pd.to_datetime(df['created_date'], errors='coerce')
df['closed_date']                    = pd.to_datetime(df['closed_date'], errors='coerce')
df['resolution_action_updated_date'] = pd.to_datetime(df['resolution_action_updated_date'], errors='coerce')

# Fix ZIP
df['incident_zip'] = df['incident_zip'].apply(
    lambda x: str(int(x)).zfill(5) if pd.notnull(x) else None
)

print(f"Clean rows: {df.shape[0]:,}")

# Bulk insert 
chunk_size = 10_000
total      = len(df)

for i in range(0, total, chunk_size):
    chunk = df.iloc[i:i + chunk_size]
    chunk.to_sql(
        name      = "nyc_311_service_requests",
        con       = engine,
        if_exists = "append",
        index     = False,
        method    = "multi"
    )
    print(f"Inserted {min(i + chunk_size, total):,} / {total:,} rows")

print("ETL complete ✅")