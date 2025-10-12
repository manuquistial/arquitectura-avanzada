FROM python:3.13-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

WORKDIR /app

# Copy dependency files (context is project root)
COPY services/sharing/pyproject.toml services/sharing/poetry.lock* ./
COPY services/common ./common/

# Adjust path in pyproject.toml for Docker build
RUN sed -i 's|path = "../common"|path = "./common"|g' pyproject.toml

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# Final stage
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (context is project root)
COPY services/sharing/app ./app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8011

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8011/health')" || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
