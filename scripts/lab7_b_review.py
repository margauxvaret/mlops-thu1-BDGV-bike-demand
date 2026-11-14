"""Vérifie le refus et les réponses du service dans un clone propre."""

import contextlib
import io
import json
import sys
from pathlib import Path

from fastapi import Response

from bike_demand import api, promote
from bike_demand.preflight import sha256
from bike_demand.schemas import PredictRequest

candidate, decision = map(Path, sys.argv[1:3])
request = PredictRequest(
    season=1,
    yr=0,
    mnth=1,
    hr=12,
    holiday=0,
    weekday=1,
    workingday=1,
    weathersit=1,
    temp=0.24,
    atemp=0.2879,
    hum=0.81,
    windspeed=0.0,
)


def status():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert promote.main(["status"]) == 0
    return json.loads(output.getvalue())


def state():
    api.load_model(Path("artifacts"))
    response = Response()
    health = api.health(response)
    return {
        "status": status(),
        "accepted_model_sha256": sha256(
            Path("artifacts/accepted/versions/model-001/model.joblib")
        ),
        "served_model_sha256": sha256(Path("artifacts/model.joblib")),
        "health": health,
        "health_code": response.status_code,
        "prediction": api.predict(request),
    }


before = state()
try:
    promote.main(
        [
            "promote",
            "--candidate",
            str(candidate),
            "--decision",
            str(decision),
            "--expected-incumbent",
            "model-001",
        ]
    )
except RuntimeError as exc:
    error = str(exc)
else:
    raise SystemExit("promotion unexpectedly succeeded")
after = state()
print(
    json.dumps(
        {
            "before": before,
            "promotion_error": error,
            "after": after,
            "unchanged": before == after,
        },
        indent=2,
    )
)
if before != after or before["health"]["status"] != "ok":
    raise SystemExit(1)
