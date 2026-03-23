import numpy as np
import pandas as pd
import subprocess
from sqlalchemy import create_engine, text
import os

# Path to raw CSV — place it in the same etl/ folder as this script
etl_dir  = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(etl_dir, "nyc_311_requests.csv")


def get_docker_db_ip():
    """Get the Docker container IP for nyc311v2_db."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "nyc311v2_db",
             "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"],
            capture_output=True, text=True, timeout=5
        )
        ip = result.stdout.strip()
        if ip:
            print(f"Docker DB IP: {ip}")
            return ip
    except Exception:
        pass
    return None


def get_engine():
    """Connect using Docker internal hostname when running inside container,
    fall back to localhost for running outside."""
    import socket
    # check if we are inside Docker by resolving the 'db' hostname
    try:
        socket.gethostbyname('db')
        url = "postgresql+psycopg2://postgres:password@db:5432/nyc_311"
        print("Running inside Docker — connecting via internal hostname: db:5432/nyc_311")
    except socket.gaierror:
        url = "postgresql+psycopg2://postgres:password@localhost:5432/nyc_311"
        print("Running on host — connecting via: localhost:5432/nyc_311")
    return create_engine(url, echo=False)


# Load raw CSV
print(f"Loading CSV from: {csv_path}")
df = pd.read_csv(csv_path, low_memory=False)
print(f"Raw rows: {df.shape[0]:,}")

# Select only the 16 columns the table has
df = df[[
    'unique_key', 'created_date', 'closed_date', 'agency',
    'agency_name', 'complaint_type', 'descriptor', 'location_type',
    'incident_zip', 'city', 'borough', 'status',
    'resolution_description', 'latitude', 'longitude',
    'resolution_action_updated_date'
]]

# Drop duplicate unique_keys within the CSV
before = len(df)
df = df.drop_duplicates(subset=['unique_key'], keep='first')
if before - len(df):
    print(f"Dropped {before - len(df):,} duplicate unique_key rows in CSV")

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

engine = get_engine()

# Force clear the table before inserting
print("Truncating existing data...")
with engine.connect() as conn:
    conn.execute(text("TRUNCATE TABLE nyc_311_service_requests RESTART IDENTITY CASCADE"))
    conn.commit()
print("Table cleared.")

# Verify we're talking to the right DB
with engine.connect() as conn:
    count = conn.execute(text("SELECT COUNT(*) FROM nyc_311_service_requests")).scalar()
    print(f"Rows after truncate: {count} (should be 0)")

# Bulk insert in chunks of 5,000
chunk_size = 5_000
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

# Final verification
with engine.connect() as conn:
    final_count = conn.execute(text("SELECT COUNT(*) FROM nyc_311_service_requests")).scalar()
    print(f"Final row count in DB: {final_count:,}")

print("ETL complete ✅")