# Python 3.12, same as .python-version and requires-python; digest pins the exact base
FROM python:3.12-slim-trixie@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

# tracking.training_commit() calls git: without it the baseline crashes
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# uv pinned to the CI version (pyproject requires >=0.12.19,<0.13)
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

WORKDIR /app

# Image Python only, no uv cache in layers; MLflow 3 telemetry is an outbound call
ENV UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    MLFLOW_DISABLE_TELEMETRY=true \
    DO_NOT_TRACK=true \
    PYTHONUNBUFFERED=1

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

# Port the service listens on inside the container (publish it with docker run -p)
ENV PORT=8000
EXPOSE 8000

# Run-time settings: override any of them with docker run -e NAME=value
ENV MODEL_DIR=/models \
    LOG_LEVEL=info

# Link the image to the commit it was built from (docker build --build-arg GIT_SHA=...)
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
LABEL org.opencontainers.image.revision=$GIT_SHA

CMD ["sh", "-c", "uvicorn bike_demand.api:app --host 0.0.0.0 --port ${PORT}"]
