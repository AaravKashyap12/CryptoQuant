# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set WORKDIR to /app/backend so the 'app' package is always on the Python path
WORKDIR /app/backend

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full project into /app  (so backend/ lands at /app/backend/)
COPY . /app

# Expose port
EXPOSE 8080

# uvicorn starts from WORKDIR (/app/backend), so 'from app.api import ...' works
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
