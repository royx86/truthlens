FROM python:3.12-slim

# Prevent .pyc files and enable unbuffered stdout/stderr (better Docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# pytesseract calls the system Tesseract binary for image text extraction.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifests first to leverage Docker layer caching.
COPY requirements.txt ./

# Install runtime dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
COPY app/ ./app/

# Expose the FastAPI port.
EXPOSE 8000

# Railway provides PORT at runtime; retain 8000 for local Docker runs.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
