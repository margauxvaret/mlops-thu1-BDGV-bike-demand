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

from bike_demand.schemas import PredictRequest
from bike_demand.validate import FEATURES

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
