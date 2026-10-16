# Python 3.12, same as .python-version and requires-python
FROM python:3.12-slim-trixie

# uv pinned to the CI version (pyproject requires >=0.12.19,<0.13)
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

WORKDIR /app

# Lock first: this layer is reused until pyproject.toml or uv.lock change
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-install-project