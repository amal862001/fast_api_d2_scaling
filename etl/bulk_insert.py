import pandas as pd
from sqlalchemy import create_engine

# load cleaned dataframe
df = pd.read_csv("nyc_311_requests.csv", low_memory=False)

# database connection
engine = create_engine("postgresql+psycopg2://postgres:password@localhost:5432/nyc_311")

# insert in chunks
chunk_size = 10000
total = len(df)

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