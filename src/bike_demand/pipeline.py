"""Pipeline d'entraînement Lab 7 : produit un candidat, jamais l'état accepté."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bike_demand.split import split_data
from bike_demand.validate import FEATURES, load_data

ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = ROOT / "data" / "raw" / "hour.csv"

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
