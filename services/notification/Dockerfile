FROM python:3.13-slim

WORKDIR /app/services/notification

RUN pip install --no-cache-dir poetry==2.2.1

# Copy common package to ../common (as expected by pyproject.toml)
COPY services/common ../common/

# Copy poetry files (pyproject.toml expects ../common)
COPY services/notification/pyproject.toml services/notification/poetry.lock* ./

# Install dependencies (no sed needed, paths match)
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-root --no-interaction --no-ansi

# Copy application code
COPY services/notification/app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (varies by service)
EXPOSE 8010

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
