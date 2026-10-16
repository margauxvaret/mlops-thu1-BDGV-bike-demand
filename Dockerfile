# Python 3.12, same as .python-version and requires-python
FROM python:3.12-slim-trixie

# tracking.training_commit() calls git: without it the baseline crashes
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# uv pinned to the CI version (pyproject requires >=0.12.19,<0.13)
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

WORKDIR /app

# Lock first: this layer is reused until pyproject.toml or uv.lock change
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-install-project

# Data snapshot, config and code, then install the project from the lock
COPY data ./data
COPY configs ./configs
# Files preflight (and so the infra tests) requires
COPY README.md ./
COPY reports/week-01-team.md ./reports/week-01-team.md
COPY .github/workflows/ci.yml ./.github/workflows/ci.yml
COPY src ./src
RUN uv sync --locked
COPY tests ./tests

# Use the locked venv directly at run time
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "bike_demand.train", "--config", "configs/baseline.yaml"]
