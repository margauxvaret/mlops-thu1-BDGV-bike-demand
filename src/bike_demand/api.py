"""Prediction service: load the trusted saved model at startup; never train here."""

import hashlib
import json
import logging
import math
import os
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Response

from bike_demand.request_logging import (
    configure_logging,
    install_request_logging,
    log_event,
)
from bike_demand.schemas import PredictRequest
from bike_demand.validate import FEATURES

# The single model-availability state, read by every route.
STATE: dict = {
    "model": None,
    "metadata": None,
    "sha256": None,
    "reason": "not loaded yet",
}


def git_sha() -> str:
    """Commit the image was built from (injected with --build-arg GIT_SHA)."""
    return os.environ.get("GIT_SHA", "unknown")


def model_dir() -> Path:
    """Folder with model.joblib and model-metadata.json (MODEL_DIR, default artifacts)."""
    return Path(os.environ.get("MODEL_DIR", "artifacts"))


def current_model_version() -> str | None:
    """Version of the loaded model, None when no model is loaded (used in logs)."""
    metadata = STATE["metadata"]
    return metadata["model_version"] if metadata else None


def load_model(directory: Path) -> None:
    """Fill STATE from directory; on any problem keep serving, without a model."""
    STATE.update(model=None, metadata=None, sha256=None, reason=None)
    try:
        metadata = json.loads((directory / "model-metadata.json").read_text())
        model_path = directory / "model.joblib"
        digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if digest != metadata["model_sha256"]:
            raise ValueError("model.joblib does not match model_sha256 in the metadata")
        if metadata["features"] != list(FEATURES):
            raise ValueError("metadata features differ from the request contract")
        # joblib can run code from the file: only load our own, locally trained model.
        model = joblib.load(model_path)
    except Exception as error:
        # Absent, unreadable or inconsistent model: the service still starts.
        STATE["reason"] = f"{type(error).__name__}: {error}"
        log_event(
            "model_missing",
            logging.WARNING,
            model_dir=str(directory),
            reason=STATE["reason"],
            git_sha=git_sha(),
        )
        return
    STATE.update(model=model, metadata=metadata, sha256=digest)
    log_event(
        "model_loaded",
        model_dir=str(directory),
        model_version=metadata["model_version"],
        model_sha256=digest,
        git_sha=git_sha(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model(model_dir())
    yield
    STATE.update(model=None, metadata=None, sha256=None, reason="service stopped")


# JSON log lines on stdout (level from LOG_LEVEL); read them with docker logs.
configure_logging()
app = FastAPI(title="Bike demand prediction", lifespan=lifespan)


@app.get("/health")
def health(response: Response) -> dict:
    if STATE["model"] is None:
        response.status_code = 503
        return {
            "status": "unavailable",
            "reason": STATE["reason"],
            "message": "No model loaded: mount the model folder (MODEL_DIR)",
            "git_sha": git_sha(),
        }
    return {
        "status": "ok",
        "model_version": STATE["metadata"]["model_version"],
        "model_sha256": STATE["sha256"],
        "git_sha": git_sha(),
    }


@app.post("/predict")
def predict(request: PredictRequest) -> dict:
    # Invalid input never reaches this line: FastAPI answers 422 first.
    model, metadata = STATE["model"], STATE["metadata"]
    if model is None:
        raise HTTPException(status_code=503, detail="no usable model loaded")
    features = metadata["features"]
    values = request.model_dump()
    row = pd.DataFrame([[values[name] for name in features]], columns=features)
    prediction = float(model.predict(row)[0])
    if not math.isfinite(prediction) or prediction < 0:
        raise HTTPException(
            status_code=500, detail="model returned an invalid prediction"
        )
    return {"prediction": prediction, "model_version": metadata["model_version"]}


# One structured log line per request (Lab 5). Keep this after the routes.
install_request_logging(app, get_model_version=current_model_version)
