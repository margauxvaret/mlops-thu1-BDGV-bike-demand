"""Check actual rejection leaves pointer, model and API responses unchanged."""

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from bike_demand.api import app
from bike_demand.preflight import sha256

candidate = Path(sys.argv[1])
decision = Path(sys.argv[2])
request = {
    "season": 1,
    "yr": 0,
    "mnth": 1,
    "hr": 12,
    "holiday": 0,
    "weekday": 1,
    "workingday": 1,
    "weathersit": 1,
    "temp": 0.24,
    "atemp": 0.2879,
    "hum": 0.81,
    "windspeed": 0.0,
}


def status():
    return json.loads(
        subprocess.check_output(
            [sys.executable, "-m", "bike_demand.promote", "status"], text=True
        )
    )


def state(client):
    return {
        "status": status(),
        "accepted_model_sha256": sha256(
            Path("artifacts/accepted/versions/model-001/model.joblib")
        ),
        "served_model_sha256": sha256(Path("artifacts/model.joblib")),
        "health": client.get("/health").json(),
        "prediction": client.post("/predict", json=request).json(),
    }


with TestClient(app) as client:
    before = state(client)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bike_demand.promote",
            "promote",
            "--candidate",
            str(candidate),
            "--decision",
            str(decision),
            "--expected-incumbent",
            "model-001",
        ],
        capture_output=True,
        text=True,
    )
    after = state(client)
    print(
        json.dumps(
            {
                "before": before,
                "promotion_exit": result.returncode,
                "promotion_error": result.stderr,
                "after": after,
                "unchanged": before == after,
            },
            indent=2,
        )
    )
    if (
        result.returncode == 0
        or before != after
        or before["health"].get("status") != "ok"
        or "prediction" not in before["prediction"]
    ):
        raise SystemExit(1)
