# Auth Service Dockerfile
# OIDC Provider + Session Management

FROM python:3.13-slim

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 auth && chown -R auth:auth /app
USER auth

# Expose port
EXPOSE 8011

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8011/health', timeout=2)"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]

