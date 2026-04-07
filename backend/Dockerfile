FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for runtime
RUN groupadd -g 10001 app && useradd -u 10001 -g app -m app

# Copy backend code
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir --upgrade "pip>=26.0" "wheel>=0.46.2"
RUN pip install --no-cache-dir -e .

COPY backend/ .

# Ensure app user owns runtime files
RUN chown -R app:app /app

USER app

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
