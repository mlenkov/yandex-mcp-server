FROM python:3.11-slim AS builder

RUN apt-get update -qq && apt-get install -y -qq git && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .
RUN uv run python -m py_compile app/main.py app/config.py app/crypto.py \
    app/database.py app/context_parser.py app/models.py app/apiforge_async.py \
    app/services/account_service.py \
    app/tools/accounts.py app/tools/direct.py app/tools/metrika.py \
    app/tools/webmaster.py app/tools/audience.py app/tools/admetrica.py

FROM python:3.11-slim

RUN useradd -m appuser

COPY --from=builder /app /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser
WORKDIR /app

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "app.main"]
