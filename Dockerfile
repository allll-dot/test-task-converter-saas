FROM python:3.12-slim

WORKDIR /app
ENV PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10

COPY pyproject.toml ./
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
RUN pip install --no-cache-dir '.[local-ai]'

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
