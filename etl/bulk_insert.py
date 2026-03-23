import pandas as pd
from sqlalchemy import create_engine
import os

# Path to cleaned CSV — lives in the same etl/ folder as this script
etl_dir      = os.path.dirname(os.path.abspath(__file__))
cleaned_csv  = os.path.join(etl_dir, "nyc_311_requests_cleaned.csv")

print(f"Reading: {cleaned_csv}")
df = pd.read_csv(cleaned_csv, low_memory=False)
print(f"Loaded: {len(df)} rows, {len(df.columns)} columns")
print(f"Columns: {list(df.columns)}")

# database connection — fixed project Postgres on port 5432
engine = create_engine("postgresql+psycopg2://postgres:password@localhost:5432/nyc_311")

# insert in chunks of 10,000 rows
chunk_size = 10000
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
    print(f"Inserted rows {i} to {i + len(chunk)} of {total}")

print("Done ✅")
