"""Lab 7 : chaque test nomme le défaut que la garde doit attraper."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from bike_demand import promote as pr
from bike_demand.preflight import sha256
from bike_demand.settings import validate_settings
from bike_demand.validate import FEATURES

pytestmark = pytest.mark.lab7

VALID = {"n_estimators": 50, "max_depth": 10, "min_samples_leaf": 1, "random_state": 42}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def state(tmp_path):
    """État accepté avec model-001, plus un candidat aux octets différents."""
    served = tmp_path / "served"
    served.mkdir()
    (served / "model.joblib").write_bytes(b"incumbent-bytes")
    _write_json(
        served / "model-metadata.json",
        {
            "model_sha256": sha256(served / "model.joblib"),
            "model_version": "baseline-test",
            "features": list(FEATURES),
        },
    )
    accepted = tmp_path / "accepted"
    pr.adopt(accepted, served)

    cand = tmp_path / "candidate"
    cand.mkdir()
    (cand / "model.joblib").write_bytes(b"candidate-bytes")
    cand_sha = sha256(cand / "model.joblib")
    _write_json(
        cand / "manifest.json",
        {
            "run_id": "testrun",
            "model_sha256": cand_sha,
            "git_sha": "test",
            "identity": {
                "features": list(FEATURES),
                "data_sha256": "test",
                "settings": VALID,
            },
        },
    )
    return accepted, cand, cand_sha, tmp_path


def _decision(tmp_path: Path, status: str, sha: str) -> Path:
    path = tmp_path / f"decision-{status}-{sha[:6]}.json"
    _write_json(path, {"status": status, "model_sha256": sha})
    return path


def _snapshot(accepted: Path) -> dict:
    return {
        "pointer": (accepted / "CURRENT.json").read_bytes(),
        "versions": sorted(p.name for p in (accepted / "versions").iterdir()),
        "lock": (accepted / ".lock").exists(),
    }


# --- Réglages ---------------------------------------------------------------


def test_unknown_setting_rejected():
    """Défaut : un réglage hors contrat (ex. retirer une feature) est accepté."""
    with pytest.raises(ValueError, match="non autorisés"):
        validate_settings({**VALID, "drop_feature": "hr"})


def test_bool_setting_rejected():
    """Défaut : True passe pour un entier (bool est une sous-classe de int)."""
    with pytest.raises(ValueError, match="entier"):
        validate_settings({**VALID, "max_depth": True})


def test_out_of_bounds_setting_rejected():
    """Défaut : une valeur hors bornes est acceptée."""
    with pytest.raises(ValueError, match="hors bornes"):
        validate_settings({**VALID, "n_estimators": 5})


# --- Séparation pipeline / état accepté -------------------------------------


def test_pipeline_never_references_accepted_state():
    """Défaut : le pipeline écrit dans l'état accepté."""
    source = Path(pr.__file__).with_name("pipeline.py").read_text(encoding="utf-8")
    assert "accepted" not in source


# --- Promotion --------------------------------------------------------------


def test_reject_decision_leaves_state_unchanged(state):
    """Défaut : une décision 'reject' modifie l'état accepté."""
    accepted, cand, cand_sha, tmp = state
    before = _snapshot(accepted)
    with pytest.raises(RuntimeError, match="promotion refusée"):
        pr.promote(cand, _decision(tmp, "reject", cand_sha), "model-001", accepted)
    assert _snapshot(accepted) == before


def test_digest_mismatch_leaves_state_unchanged(state):
    """Défaut : on promeut des octets différents de ceux décidés."""
    accepted, cand, _, tmp = state
    before = _snapshot(accepted)
    with pytest.raises(RuntimeError, match="octets différents"):
        pr.promote(cand, _decision(tmp, "accept", "0" * 64), "model-001", accepted)
    assert _snapshot(accepted) == before


def test_stale_incumbent_leaves_state_unchanged(state):
    """Défaut : on promeut alors que l'incumbent a changé depuis la décision."""
    accepted, cand, cand_sha, tmp = state
    before = _snapshot(accepted)
    with pytest.raises(RuntimeError, match="incumbent changé"):
        pr.promote(cand, _decision(tmp, "accept", cand_sha), "model-999", accepted)
    assert _snapshot(accepted) == before


def test_accept_keeps_previous_version(state):
    """Défaut : la promotion perd la version acceptée qu'elle remplace."""
    accepted, cand, cand_sha, tmp = state
    pointer = pr.promote(
        cand, _decision(tmp, "accept", cand_sha), "model-001", accepted
    )
    assert pointer["version_id"] == "model-002"
    assert pointer["previous"] == "model-001"
    pr.verify_bundle(accepted / "versions" / "model-001")
    assert not (accepted / ".lock").exists()


# --- Restauration -----------------------------------------------------------


def test_restore_corrupted_checksum_fails_closed(state):
    """Défaut : un modèle aux octets corrompus est restauré."""
    accepted, cand, cand_sha, tmp = state
    pr.promote(cand, _decision(tmp, "accept", cand_sha), "model-001", accepted)
    model = accepted / "versions" / "model-001" / "model.joblib"
    os.chmod(model, stat.S_IREAD | stat.S_IWRITE)
    with open(model, "ab") as f:
        f.write(b"x")
    before = _snapshot(accepted)
    with pytest.raises(RuntimeError, match="checksum différent"):
        pr.restore("model-001", "model-002", accepted)
    assert _snapshot(accepted) == before


def test_restore_without_retraining(state):
    """Défaut : la version remplacée n'est pas récupérable sans réentraîner."""
    accepted, cand, cand_sha, tmp = state
    pr.promote(cand, _decision(tmp, "accept", cand_sha), "model-001", accepted)
    pointer = pr.restore("model-001", "model-002", accepted)
    assert pointer["version_id"] == "model-001"
    assert pointer["previous"] == "model-002"
