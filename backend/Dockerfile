# Python 3.11 slim image for fast and lightweight builds
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_XET=1 \
    HF_HUB_ENABLE_HF_TRANSFER=0 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies (curl for container health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only first for 3x smaller image and reliable fast downloads
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download and cache NLP models during build to ensure instant container boot
RUN python -c "import spacy; spacy.load('en_core_web_md')"
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L6-v2', max_length=512)"

# Copy application source code
COPY . .

# Ensure runtime directories exist
RUN mkdir -p /app/data

# Expose default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=5s --timeout=5s --start-period=3s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/ || exit 1

# Start FastAPI application using dynamic PORT provided by Render
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
