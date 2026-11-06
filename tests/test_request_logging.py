"""Unit tests for src/bike_demand/request_logging.py (Lab 5, structured logs).

These run the module in-process on a tiny app. They do not replace the check
against the running container, which must go over the network.
"""

import io
import json

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from bike_demand.request_logging import (
    REQUEST_ID_HEADER,
    configure_logging,
    install_request_logging,
    log_event,
)


class Features(BaseModel):
    hr: int = Field(ge=0, le=23)
    temp: float = Field(ge=0, le=1)


def make_app(model_version: str | None) -> FastAPI:
    app = FastAPI()
    state = {"model_version": model_version}

    @app.post("/predict")
    def predict(features: Features):
        if state["model_version"] is None:
            raise HTTPException(503, "model not loaded")
        return {"prediction": 42.0, "model_version": state["model_version"]}

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret detail that must not reach the logs")

    install_request_logging(app, get_model_version=lambda: state["model_version"])
    return app


@pytest.fixture
def log_stream():
    stream = io.StringIO()
    configure_logging(level="INFO", stream=stream)
    return stream


def lines(stream: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


VALID = {"hr": 8, "temp": 0.5}


def test_valid_request_writes_one_served_line(log_stream):
    with TestClient(make_app("rf-v1")) as client:
        response = client.post("/predict", json=VALID)

    assert response.status_code == 200
    [line] = lines(log_stream)
    assert line["event"] == "served"
    assert line["status"] == 200
    assert line["method"] == "POST"
    assert line["path"] == "/predict"
    assert line["model_version"] == "rf-v1"
    assert line["ms"] >= 0
    assert line["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_invalid_request_logs_field_names_not_values(log_stream):
    bad = {"hr": 24, "temp": "PLEASE-DO-NOT-LOG-ME"}
    with TestClient(make_app("rf-v1")) as client:
        response = client.post("/predict", json=bad)

    assert response.status_code == 422
    # The 422 body is still FastAPI's default: the logging wrapper changes nothing.
    assert {tuple(e["loc"]) for e in response.json()["detail"]} == {
        ("body", "hr"),
        ("body", "temp"),
    }
    [line] = lines(log_stream)
    assert line["event"] == "rejected"
    assert line["status"] == 422
    assert line["invalid_fields"] == ["hr:less_than_equal", "temp:float_parsing"]
    assert "PLEASE-DO-NOT-LOG-ME" not in log_stream.getvalue()


def test_unreadable_body_is_named_body(log_stream):
    with TestClient(make_app("rf-v1")) as client:
        response = client.post(
            "/predict",
            content=b"{oops",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 422
    [line] = lines(log_stream)
    assert line["invalid_fields"] == ["body:json_invalid"]


def test_existing_validation_handler_is_kept(log_stream):
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.post("/predict")
    def predict(features: Features):
        return {"prediction": 1.0}

    @app.exception_handler(RequestValidationError)
    def team_handler(request, exc):  # sync on purpose: both kinds must work
        return JSONResponse({"error": "bad input"}, status_code=400)

    install_request_logging(app, get_model_version=lambda: "rf-v1")
    with TestClient(app) as client:
        response = client.post("/predict", json={"hr": 99, "temp": 0.5})

    assert response.status_code == 400
    assert response.json() == {"error": "bad input"}
    [line] = lines(log_stream)
    assert line["event"] == "rejected"
    assert line["invalid_fields"] == ["hr:less_than_equal"]


def test_missing_model_is_logged_as_unavailable(log_stream):
    with TestClient(make_app(None)) as client:
        response = client.post("/predict", json=VALID)

    assert response.status_code == 503
    [line] = lines(log_stream)
    assert line["event"] == "unavailable"
    assert line["level"] == "WARNING"
    assert line["model_version"] is None


def test_crash_is_logged_without_its_message(log_stream):
    with TestClient(make_app("rf-v1"), raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    [line] = lines(log_stream)
    assert line["event"] == "failed"
    assert line["error"] == "RuntimeError"
    assert line["error_at"].startswith("test_request_logging.py:")
    assert "secret detail" not in log_stream.getvalue()


def test_safe_request_id_is_kept_and_unsafe_one_replaced(log_stream):
    with TestClient(make_app("rf-v1")) as client:
        kept = client.post("/predict", json=VALID, headers={REQUEST_ID_HEADER: "r-17"})
        replaced = client.post(
            "/predict", json=VALID, headers={REQUEST_ID_HEADER: 'x" injected'}
        )

    assert kept.headers[REQUEST_ID_HEADER] == "r-17"
    assert replaced.headers[REQUEST_ID_HEADER] != 'x" injected'
    first, second = lines(log_stream)
    assert first["request_id"] == "r-17"
    assert second["request_id"] == replaced.headers[REQUEST_ID_HEADER]


def test_log_event_adds_fields_to_one_line(log_stream):
    log_event("model_loaded", model_version="rf-v1", model_sha256="abc")
    [line] = lines(log_stream)
    assert line["event"] == "model_loaded"
    assert line["model_sha256"] == "abc"


def test_unknown_log_level_fails_at_start_up():
    with pytest.raises(ValueError):
        configure_logging(level="LOUD", stream=io.StringIO())
