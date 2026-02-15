FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Shared Library
COPY shared /app/shared

# Copy Worker Service
COPY services/worker /app/services/worker

# Run Worker (Scheduler or Just Keep Alive)
# For now, we can run a simple loop or just the training task if invoked
CMD ["python", "-m", "services.worker.main"]
