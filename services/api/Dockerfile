FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Shared Library
COPY shared /app/shared

# Copy API Service
COPY services/api /app/services/api

# Expose port
EXPOSE 8000

# Run FastAPI
# Note: we run from /app root so "services.api.main" is importable
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
