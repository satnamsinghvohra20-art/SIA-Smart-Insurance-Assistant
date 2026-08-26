# ==============================================================================
# ClaimPilot — Multi-Agent Health Insurance Reimbursement Pipeline
# Production Container for Google Cloud Run / Docker Deployment
# ==============================================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy entire application (backend, frontend, data, sample files)
COPY backend /app/backend
COPY frontend /app/frontend

# Pre-generate sample files on build
WORKDIR /app/backend
RUN python services/sample_pdf_generator.py

# Expose port
EXPOSE 8000

# Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
