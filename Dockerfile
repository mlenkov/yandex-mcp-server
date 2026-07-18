FROM ghcr.io/astral-sh/uv:python3.11-slim

WORKDIR /app

RUN useradd -m appuser

COPY pyproject.toml ./
COPY uv.lock ./

RUN uv sync --no-dev --frozen

COPY . .
RUN chown -R appuser:appuser /app && chmod 755 /app

RUN mkdir -p /app/data && chown appuser:appuser /app/data

ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "app.main"]
