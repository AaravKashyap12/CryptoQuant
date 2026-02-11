# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from root requirements.txt (cleaned)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy only the BACKEND source code into the container root
# This effectively ignores the root app.py (Streamlit)
COPY backend/ .

# Expose port (railway/fly dynamic port binding usually handles this, but 8000 is standard)
# CMD ["python", "main.py"]
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
