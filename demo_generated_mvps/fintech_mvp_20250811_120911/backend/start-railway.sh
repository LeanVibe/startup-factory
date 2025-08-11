#!/bin/bash
# Railway startup script
export PORT=${PORT:-8000}
export DATABASE_URL=${DATABASE_URL:-postgresql://postgres:password@postgres:5432/mvp_db}

# Start the FastAPI application
uvicorn main:app --host 0.0.0.0 --port $PORT
