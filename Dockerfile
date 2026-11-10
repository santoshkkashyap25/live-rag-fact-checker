# =============================================================
# Stage 1: Build Next.js Static Export
# =============================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

# Empty NEXT_PUBLIC_API_URL so the UI calls /api/* relative to the same host
ENV NEXT_PUBLIC_API_URL=""
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# =============================================================
# Stage 2: Python Backend Runtime with Static Frontend
# =============================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_XET=1 \
    HF_HUB_ENABLE_HF_TRANSFER=0 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies (curl for container health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download and cache SpaCy linguistic model
RUN python -c "import spacy; spacy.load('en_core_web_sm')"

# Copy backend application source code
COPY backend/ /app/

# Copy compiled static frontend from Stage 1 into /app/static
COPY --from=frontend-builder /app/frontend/out /app/static

# Ensure runtime data directory exists
RUN mkdir -p /app/data

EXPOSE 8000

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start unified FastAPI application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

