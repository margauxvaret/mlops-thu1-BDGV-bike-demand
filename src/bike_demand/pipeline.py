"""Pipeline d'entraînement Lab 7 : produit un candidat, jamais l'état accepté."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from bike_demand.preflight import sha256
from bike_demand.split import split_data
from bike_demand.tracking import training_commit, working_tree_dirty
from bike_demand.validate import FEATURES, load_data

ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = ROOT / "data" / "raw" / "hour.csv"
LOCK_FILE = ROOT / "uv.lock"

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
        "git_sha": training_commit(root),
        "settings": settings,
        "features": list(FEATURES),
    }


def run_id_of(identity: dict) -> str:
    """Identifiant stable : même identité, même run_id."""
    blob = json.dumps(identity, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]
