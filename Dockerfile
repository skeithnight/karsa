FROM python:3.9-slim

WORKDIR /app
COPY pyproject.toml /app/
RUN pip install "psycopg[binary]"
RUN pip install pytest

COPY src/ /app/src/
COPY tests/ /app/tests/

ENV PYTHONPATH=/app/src
CMD ["python", "-m", "pytest", "tests"]
RUN pip install cryptography testcontainers psycopg_pool
