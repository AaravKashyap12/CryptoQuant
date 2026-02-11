#!/bin/bash
# start.sh
# Ensure PORT is set, default to 8000
PORT=${PORT:-8000}
echo "Starting Uvicorn on PORT: $PORT"
exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
