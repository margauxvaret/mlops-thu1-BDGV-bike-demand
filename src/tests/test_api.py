"""Tests de l'API (Lab 4) : etat normal, entrees invalides, modele absent."""

import hashlib
import json
import math

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.dummy import DummyRegressor

from bike_demand.api import app

PRED_KEY = "prediction"
VERSION_KEY = "model_version"
MODEL_DIR_ENV = "MODEL_DIR"
TEST_VERSION = "test-0.0.1"

FEATURES = [
    "season",
    "yr",
    "mnth",
    "hr",
    "holiday",
    "weekday",
    "workingday",
    "weathersit",
    "temp",
    "atemp",
    "hum",
    "windspeed",
]


METADATA = {"model_version": TEST_VERSION, "features": FEATURES}

VALID = {
    "season": 1,
    "yr": 0,
    "mnth": 6,
    "hr": 12,
    "holiday": 0,
    "weekday": 3,
    "workingday": 1,
    "weathersit": 1,
    "temp": 0.5,
    "atemp": 0.5,
    "hum": 0.5,
    "windspeed": 0.2,
}


# --------------------------- fixtures ---------------------------
@pytest.fixture
def model_dir(tmp_path):
    """Petit modele bidon dans un dossier temporaire (pas de artifacts/ requis)."""
    d = tmp_path / "model"
    d.mkdir()
    X = pd.DataFrame([VALID, VALID], columns=FEATURES)
    model = DummyRegressor(strategy="constant", constant=42.0).fit(X, [42.0, 42.0])
    joblib.dump(model, d / "model.joblib")
    digest = hashlib.sha256((d / "model.joblib").read_bytes()).hexdigest()
    meta = {**METADATA, "model_sha256": digest}
    (d / "model-metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    return d


@pytest.fixture
def client(model_dir, monkeypatch):
    monkeypatch.setenv(MODEL_DIR_ENV, str(model_dir))
    with TestClient(
        app, raise_server_exceptions=False
    ) as c:  # execute le demarrage (lifespan)
        yield c


@pytest.fixture
def client_no_model(tmp_path, monkeypatch):
    monkeypatch.setenv(MODEL_DIR_ENV, str(tmp_path / "dossier_absent"))
    with TestClient(app) as c:
        yield c


def post_raw(c, payload):
    """Envoie du JSON brut (permet NaN/Infinity, que httpx refuse avec json=)."""
    return c.post(
        "/predict",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )


# ------------------------ cas 1 : normal ------------------------
def test_health_ok(client):
    assert client.get("/health").status_code == 200


def test_predict_ok(client):
    r = client.post("/predict", json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert body[VERSION_KEY] == TEST_VERSION  # vient des metadonnees
    pred = body[PRED_KEY]
    assert isinstance(pred, (int, float))
    assert math.isfinite(pred)
    assert pred >= 0


# ------------------------ cas 2 : invalide ------------------------
@pytest.mark.parametrize("field", FEATURES)
def test_missing_field(client, field):
    payload = {k: v for k, v in VALID.items() if k != field}
    assert client.post("/predict", json=payload).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("season", "3"),
        ("hr", "abc"),
        ("hr", 12.5),
        ("yr", None),
        ("temp", "0.5"),
        ("hum", [0.5]),
    ],
)
def test_wrong_type(client, field, value):
    payload = {**VALID, field: value}
    assert client.post("/predict", json=payload).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("season", 0),
        ("season", 5),
        ("yr", -1),
        ("yr", 2),
        ("mnth", 0),
        ("mnth", 13),
        ("hr", -1),
        ("hr", 24),
        ("holiday", 2),
        ("weekday", 7),
        ("workingday", 2),
        ("weathersit", 0),
        ("weathersit", 5),
        ("temp", -0.1),
        ("temp", 1.1),
        ("atemp", -0.1),
        ("atemp", 1.1),
        ("hum", -0.1),
        ("hum", 1.1),
        ("windspeed", -0.1),
        ("windspeed", 1.1),
    ],
)
def test_out_of_bounds(client, field, value):
    payload = {**VALID, field: value}
    assert client.post("/predict", json=payload).status_code == 422


@pytest.mark.parametrize("field", ["temp", "atemp", "hum", "windspeed"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite(client, field, value):
    assert post_raw(client, {**VALID, field: value}).status_code == 422


@pytest.mark.parametrize("extra", ["cnt", "casual", "registered", "champ_inconnu"])
def test_extra_field_rejected(client, extra):
    payload = {**VALID, extra: 1}
    assert client.post("/predict", json=payload).status_code == 422


# ------------------------ cas 3 : modele absent ------------------------
def test_health_without_model(client_no_model):
    assert client_no_model.get("/health").status_code == 503


def test_predict_valid_without_model(client_no_model):
    assert client_no_model.post("/predict", json=VALID).status_code == 503


def test_predict_invalid_without_model(client_no_model):
    payload = {k: v for k, v in VALID.items() if k != "hr"}
    assert client_no_model.post("/predict", json=payload).status_code == 422


def test_health_reports_exact_loaded_model_identity(client, model_dir, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "test-commit-123")
    body = client.get("/health").json()
    assert body == {
        "status": "ok",
        "git_sha": "test-commit-123",
        "model_version": TEST_VERSION,
        "model_sha256": hashlib.sha256(
            (model_dir / "model.joblib").read_bytes()
        ).hexdigest(),
    }


def test_wrong_model_sha_is_rejected(model_dir, monkeypatch):
    metadata_path = model_dir / "model-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["model_sha256"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setenv(MODEL_DIR_ENV, str(model_dir))
    with TestClient(app) as c:
        health = c.get("/health")
        assert health.status_code == 503
        assert "model_sha256" in health.json()["reason"]
        assert c.post("/predict", json=VALID).status_code == 503


def test_prediction_matches_saved_model_readback(client, model_dir):
    # Recompute from the earlier serialized fixture, not from a second training run.
    model = joblib.load(model_dir / "model.joblib")
    recorded = float(model.predict(pd.DataFrame([VALID], columns=FEATURES))[0])
    response = client.post("/predict", json=VALID)
    assert response.status_code == 200
    assert response.json()["prediction"] == pytest.approx(recorded, rel=0, abs=0)
