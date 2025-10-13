FROM python:3.13-slim

WORKDIR /app/services/gateway

RUN pip install --no-cache-dir poetry==2.2.1

# Copy common package to ../common (as expected by pyproject.toml)
COPY services/common ../common/

# Copy poetry files (pyproject.toml expects ../common)
COPY services/gateway/pyproject.toml services/gateway/poetry.lock* ./

# Install dependencies (no sed needed, paths match)
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-root --no-interaction --no-ansi

# Copy application code
COPY services/gateway/app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
