# Contributing

## Quick Start

```bash
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run python -m app.main
```

## Project Structure

```
app/                    # MCP server (FastMCP + tools)
admin/                  # Admin panel (FastAPI + UI)
docs/                   # Documentation + JSON dumps
```

## Code Style

- Python 3.11+, async throughout
- Follow existing patterns in `app/tools/` for new tools
- Use `ctx.info/warning/error` for structured logging
- Use `@rate_limiter.check()` for rate limiting
- All tools need rich LLM docstrings (КОГДА ИСПОЛЬЗОВАТЬ / ПАРАМЕТРЫ / ВОЗВРАЩАЕТ)
- All tools need Tool Annotations (readOnlyHint, etc.)

## Testing

```bash
uv run pytest
```

## Pull Request Process

1. Fork the repo, create a feature branch
2. Add your changes
3. Run lint: `uv run ruff check .`
4. Open a PR against `main`
