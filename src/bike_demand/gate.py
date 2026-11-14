"""Evaluate a trusted local candidate against the precommitted Lab 7 policy."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error

from bike_demand.pipeline import ROOT, load_contract_splits
from bike_demand.preflight import check_snapshot, sha256
from bike_demand.train import select_features
from bike_demand.validate import FEATURES

INCUMBENT_SHA = "fd98ceafc57a5babce61ce703cbf9cb8d1f83c6820b0b34fe30ad1a0fc49c304"
MAX_BYTES = 50 * 1024 * 1024
CODES = {"accept": 0, "invalid": 2, "missing": 3, "rejected": 4, "blocked": 5}


def decide(checks):
    """Checks map names to (status, reason); absent mandatory checks fail closed."""
    required = ("integrity", "operation", "naive", "incumbent")
    items = dict(checks)
    for name in required:
        if name not in items:
            items[name] = ("missing", f"{name}: contrôle non exécuté")
    for name, result in items.items():
        if (
            not isinstance(result, (tuple, list))
            or len(result) != 2
            or result[0] not in CODES
        ):
            return "invalid", [f"{name}: résultat malformé"]
    for status in ("invalid", "blocked", "missing", "rejected"):
        reasons = [
            f"{name}: {reason}" for name, (s, reason) in items.items() if s == status
        ]
        if reasons:
            return status, reasons
    return "accept", ["Tous les contrôles obligatoires sont satisfaits."]


def quality(candidate, naive, incumbent, equivalent):
    values = (candidate, naive, incumbent)
    if any(
        isinstance(v, bool)
        or not isinstance(v, (int, float))
        or not math.isfinite(v)
        or v < 0
        for v in values
    ):
        raise ValueError("MAE invalides")
    return candidate < naive, equivalent or candidate <= incumbent - 1.0


def evaluate(candidate_dir):
    checks, evidence = {}, {}
    digest = None
    manifest = None
    model_path = candidate_dir / "model.joblib"
    try:
        manifest = json.loads(
            (candidate_dir / "manifest.json").read_text(encoding="utf-8")
        )
        digest = sha256(model_path)
        if not isinstance(manifest, dict) or digest != manifest.get("model_sha256"):
            raise ValueError("SHA-256 du candidat différent du manifest")
        if manifest.get("identity", {}).get("features") != list(FEATURES):
            raise ValueError("features du manifest incorrectes ou désordonnées")
        snapshot = check_snapshot(ROOT)
        if manifest["identity"].get("data_sha256") != snapshot["sha256"]:
            raise ValueError("SHA-256 des données différent du snapshot")
        parts = load_contract_splits()
        model = joblib.load(model_path)  # Only trusted local pipeline artifacts.
        if (
            list(getattr(model, "feature_names_in_", [])) != list(FEATURES)
            or getattr(model, "n_features_in_", None) != 12
        ):
            raise ValueError("features du modèle incorrectes ou désordonnées")
        checks["integrity"] = (
            "accept",
            "snapshot, données, features et modèle vérifiés",
        )
        validation = parts["validation"]
        rows = (
            validation[["instant", "cnt"]]
            .to_csv(index=False, lineterminator="\n")
            .encode()
        )
        evidence.update(
            data_sha256=snapshot["sha256"],
            validation_rows=len(validation),
            validation_rows_labels_sha256=hashlib.sha256(rows).hexdigest(),
        )
    except (FileNotFoundError, PermissionError) as exc:
        checks["integrity"] = ("blocked", str(exc))
    except Exception as exc:
        checks["integrity"] = ("invalid", f"{type(exc).__name__}: {exc}")

    if model_path.is_file():
        size = model_path.stat().st_size
        evidence["model_bytes"] = size
        checks["operation"] = (
            "accept" if size <= MAX_BYTES else "rejected",
            f"taille {size} / {MAX_BYTES} octets",
        )

    if checks["integrity"][0] == "accept":
        try:
            x = select_features(validation, FEATURES)
            y = validation["cnt"]
            preds = model.predict(x)
            if not np.isfinite(preds).all():
                raise ValueError("prédictions non finies")
            cand = float(mean_absolute_error(y, preds))
            mean = float(parts["train"]["cnt"].mean())
            naive = float(np.abs(y - mean).mean())
            evidence.update(candidate_mae=cand, naive_mae=naive, train_mean=mean)
            checks["naive"] = (
                "accept" if cand < naive else "rejected",
                f"MAE {cand} contre naïve {naive}",
            )
        except Exception as exc:
            checks["naive"] = (
                "invalid",
                f"évaluation candidat: {type(exc).__name__}: {exc}",
            )
        try:
            pointer = json.loads(
                (ROOT / "artifacts/accepted/CURRENT.json").read_text(encoding="utf-8")
            )
            ipath = ROOT / "artifacts/accepted/versions/model-001/model.joblib"
            if (
                pointer.get("version_id") != "model-001"
                or pointer.get("model_sha256") != INCUMBENT_SHA
                or sha256(ipath) != INCUMBENT_SHA
            ):
                raise RuntimeError(
                    "incumbent courant ou octets différents de model-001"
                )
            incumbent = joblib.load(ipath)
            if list(getattr(incumbent, "feature_names_in_", [])) != list(FEATURES):
                raise RuntimeError("features de l'incumbent incorrectes")
            pred = incumbent.predict(x)
            if not np.isfinite(pred).all():
                raise RuntimeError("prédictions incumbent non finies")
            incumbent_mae = float(mean_absolute_error(y, pred))
            evidence.update(
                incumbent_mae=incumbent_mae,
                incumbent_sha256=INCUMBENT_SHA,
                equivalent=digest == INCUMBENT_SHA,
            )
            _, passed = quality(cand, naive, incumbent_mae, digest == INCUMBENT_SHA)
            checks["incumbent"] = (
                "accept" if passed else "rejected",
                f"MAE {cand} contre incumbent {incumbent_mae}, marge 1",
            )
        except FileNotFoundError as exc:
            checks["incumbent"] = ("blocked", f"incumbent indisponible : {exc}")
        except Exception as exc:
            checks["incumbent"] = (
                "blocked",
                f"incumbent à réparer : {type(exc).__name__}: {exc}",
            )
    status, reasons = decide(checks)
    return {
        "status": status,
        "model_sha256": digest,
        "expected_incumbent": "model-001",
        "candidate": candidate_dir.name,
        "policy": "reports/lab7-policy.md",
        "checks": {k: {"status": v[0], "reason": v[1]} for k, v in checks.items()},
        "reasons": reasons,
        "evidence": evidence,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = evaluate(args.candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return CODES[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
