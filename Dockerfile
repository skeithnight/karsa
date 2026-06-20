FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install system dependencies if necessary (e.g. libpq for psycopg)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY uv.lock pyproject.toml README.md /app/
RUN uv sync --frozen --no-install-project

COPY src /app/src
COPY tests /app/tests
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini

RUN uv sync --frozen

CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn karsa.app:app --host 0.0.0.0 --port 8000"]
