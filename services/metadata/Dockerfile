FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app/services/metadata

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

# Copy common package to ../common (as expected by pyproject.toml)
# Copy pyproject.toml and poetry.lock first, then the package
COPY services/common/pyproject.toml ../common/
COPY services/common/poetry.lock ../common/
COPY services/common/carpeta_common ../common/carpeta_common/

# Copy poetry files
COPY services/metadata/pyproject.toml services/metadata/poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-root --no-interaction --no-ansi

# Copy application code
COPY services/metadata/app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]

