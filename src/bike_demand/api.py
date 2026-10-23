"""Prediction service: load the trusted saved model at startup; never train here."""

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
from fastapi import FastAPI, Response

logger = logging.getLogger(__name__)

# The single model-availability state, read by every route.
STATE: dict = {"model": None, "metadata": None, "reason": "not loaded yet"}


def model_dir() -> Path:
    """Folder with model.joblib and model-metadata.json (MODEL_DIR, default artifacts)."""
    return Path(os.environ.get("MODEL_DIR", "artifacts"))


def load_model(directory: Path) -> None:
    """Fill STATE from directory; on any problem keep serving, without a model."""
    STATE.update(model=None, metadata=None, reason=None)
    try:
        metadata = json.loads((directory / "model-metadata.json").read_text())
        # joblib can run code from the file: only load our own, locally trained model.
        model = joblib.load(directory / "model.joblib")
    except Exception as error:
        # Absent or unreadable model: the service still starts, without a model.
        STATE["reason"] = f"{type(error).__name__}: {error}"
        logger.warning("No usable model in %s (%s)", directory, STATE["reason"])
        return
    STATE.update(model=model, metadata=metadata)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model(model_dir())
    yield
    STATE.update(model=None, metadata=None, reason="service stopped")


app = FastAPI(title="Bike demand prediction", lifespan=lifespan)


@app.get("/health")
def health(response: Response) -> dict:
    if STATE["model"] is None:
        response.status_code = 503
        return {"status": "unavailable", "reason": STATE["reason"]}
    return {"status": "ok", "model_version": STATE["metadata"]["model_version"]}
