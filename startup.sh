#!/bin/sh

echo "Running Alembic migrations..."
alembic upgrade head

# echo "Seeding users..."
# PYTHONPATH=/app python /app/etl/seed_users.py

echo "Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 8000