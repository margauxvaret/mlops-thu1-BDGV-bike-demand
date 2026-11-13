"""Pipeline d'entraînement Lab 7 : produit un candidat, jamais l'état accepté.

Usage :
    uv run --locked python -m bike_demand.pipeline --settings configs/candidates/rf-default.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from bike_demand.preflight import sha256
from bike_demand.settings import validate_settings
from bike_demand.split import split_data
from bike_demand.tracking import training_commit, working_tree_dirty
from bike_demand.train import select_features
from bike_demand.validate import FEATURES, load_data

ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = ROOT / "data" / "raw" / "hour.csv"
LOCK_FILE = ROOT / "uv.lock"
CANDIDATES = ROOT / "artifacts" / "candidates"
CODE_DIR = "src/bike_demand"
TARGET = "cnt"

EXPECTED_ROWS = {"train": 8645, "validation": 4358, "test": 4376}
EXPECTED_FEATURE_COUNT = 12


def load_contract_splits() -> dict[str, pd.DataFrame]:
    """Charge et découpe les données, vérifie le contrat.

    Renvoie uniquement train et validation : la partition test
    ne sort jamais de cette fonction.
    """
    df = load_data(DATA_CSV)
    splits = split_data(df)
    train = splits["train"]
    validation = splits["validation"]

    for name, expected in EXPECTED_ROWS.items():
        actual = len(splits[name])
        if actual != expected:
            raise ValueError(
                f"contrat de données violé : {name} a {actual} lignes, attendu {expected}"
            )

    if len(FEATURES) != EXPECTED_FEATURE_COUNT:
        raise ValueError(
            f"contrat de features violé : {len(FEATURES)} features, "
            f"attendu {EXPECTED_FEATURE_COUNT}"
        )

    missing = [f for f in FEATURES if f not in train.columns]
    if missing:
        raise ValueError(f"features absentes des données : {missing}")

    return {"train": train, "validation": validation}


def code_tree_sha(root: Path = ROOT) -> str:
    """Empreinte Git du code du paquet : ne change que si le code change."""
    result = subprocess.run(
        ["git", "rev-parse", f"HEAD:{CODE_DIR}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def build_identity(settings: dict, root: Path = ROOT) -> dict:
    """Les entrées qui déterminent un run. Refuse un arbre git sale."""
    dirty = working_tree_dirty(root)
    if dirty is not False:
        raise RuntimeError(
            "arbre git sale ou état inconnu : commite avant de lancer le pipeline"
        )
    return {
        "data_sha256": sha256(DATA_CSV),
        "lock_sha256": sha256(LOCK_FILE),
        "code_tree_sha": code_tree_sha(root),
        "settings": settings,
        "features": list(FEATURES),
    }


def run_id_of(identity: dict) -> str:
    """Identifiant stable : même identité, même run_id."""
    blob = json.dumps(identity, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def existing_candidate_is_valid(candidate_dir: Path) -> bool:
    """Un candidat déjà publié est valide si ses octets correspondent au manifest."""
    manifest_path = candidate_dir / "manifest.json"
    model_path = candidate_dir / "model.joblib"
    if not (manifest_path.is_file() and model_path.is_file()):
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest.get("model_sha256") == sha256(model_path)


def run_pipeline(settings_path: Path, candidates_dir: Path = CANDIDATES) -> Path:
    """Produit un candidat dans candidates_dir/<run_id>/ et renvoie son chemin."""
    raw = json.loads(settings_path.read_text(encoding="utf-8"))
    settings = validate_settings(raw)
    identity = build_identity(settings)
    run_id = run_id_of(identity)
    final_dir = candidates_dir / run_id

    # Retry sûr : même identité, même candidat, rien n'est réécrit.
    if final_dir.exists():
        if existing_candidate_is_valid(final_dir):
            print(f"[pipeline] candidat {run_id} déjà présent et valide (idempotent)")
            return final_dir
        raise RuntimeError(
            f"{final_dir} existe mais est invalide : inspecte-le, ne l'écrase pas"
        )

    candidates_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = candidates_dir / f".tmp-{run_id}-{uuid.uuid4().hex[:8]}"
    tmp_dir.mkdir()
    try:
        splits = load_contract_splits()
        train = splits["train"]

        # Ajuster UNIQUEMENT sur le train.
        model = RandomForestRegressor(**settings)
        model.fit(select_features(train, FEATURES), train[TARGET])

        model_path = tmp_dir / "model.joblib"
        joblib.dump(model, model_path)

        manifest = {
            "run_id": run_id,
            "identity": identity,
            "git_sha": training_commit(ROOT),
            "model_sha256": sha256(model_path),
            "rows": {name: len(df) for name, df in splits.items()},
            "status": "candidate",
        }
        (tmp_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )

        # Publication atomique : le dossier final apparaît complet, ou pas du tout.
        os.replace(tmp_dir, final_dir)
    except BaseException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    print(f"[pipeline] candidat {run_id} publié, sha256={manifest['model_sha256']}")
    return final_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Produit un candidat Lab 7.")
    parser.add_argument("--settings", required=True, type=Path)
    args = parser.parse_args(argv)
    print(run_pipeline(args.settings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
