"""Measure prediction/readback variation using the same synthetic API fixture."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

import joblib
import pandas as pd
from fastapi.testclient import TestClient
from sklearn.dummy import DummyRegressor

from bike_demand.api import app
from bike_demand.validate import FEATURES

values = dict(zip(FEATURES, [1, 0, 6, 12, 0, 3, 1, 1, 0.5, 0.5, 0.5, 0.2]))
with tempfile.TemporaryDirectory() as directory:
    model_dir = Path(directory)
    model = DummyRegressor(strategy="constant", constant=42.0).fit(
        pd.DataFrame([values, values], columns=FEATURES), [42.0, 42.0]
    )
    joblib.dump(model, model_dir / "model.joblib")
    digest = hashlib.sha256((model_dir / "model.joblib").read_bytes()).hexdigest()
    (model_dir / "model-metadata.json").write_text(
        json.dumps(
            {
                "model_version": "test-0.0.1",
                "features": list(FEATURES),
                "model_sha256": digest,
            }
        )
    )
    os.environ["MODEL_DIR"] = directory
    with TestClient(app) as client:
        for i in range(1, 6):
            recorded = float(
                joblib.load(model_dir / "model.joblib").predict(
                    pd.DataFrame([values], columns=FEATURES)
                )[0]
            )
            actual = client.post("/predict", json=values).json()["prediction"]
            print(
                f"run={i} saved={recorded!r} api={actual!r} abs_delta={abs(actual - recorded)!r}"
            )
