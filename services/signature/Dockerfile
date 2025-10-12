FROM python:3.13-slim

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-dev --no-interaction --no-ansi

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
