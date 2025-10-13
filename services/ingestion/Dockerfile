FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.2.1

# Copy files from project root context
COPY services/ingestion/pyproject.toml services/ingestion/poetry.lock* ./
COPY services/common ./common/

# Adjust common path
RUN sed -i 's|path = "../common"|path = "./common"|g' pyproject.toml || true

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

COPY services/ingestion/app/ ./app/

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
