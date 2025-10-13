FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==2.2.1

# Copy files from project root context
COPY services/auth/pyproject.toml services/auth/poetry.lock* ./
COPY services/common ./common/

# Adjust common path
RUN sed -i 's|path = "../common"|path = "./common"|g' pyproject.toml || true

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# Copy application code
COPY services/auth/app/ ./app/

# Expose port
EXPOSE 8008

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008"]
