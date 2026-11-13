"""Liste blanche des réglages autorisés pour un candidat (Lab 7)."""

from __future__ import annotations

ALLOWED: dict[str, tuple[int, int]] = {
    "n_estimators": (10, 500),
    "max_depth": (2, 30),
    "min_samples_leaf": (1, 50),
    "random_state": (0, 2**31 - 1),
}

FIXED = {"n_jobs": 1}


def validate_settings(raw: dict) -> dict:
    """Renvoie des réglages validés, ou lève ValueError."""
    unknown = set(raw) - set(ALLOWED)
    if unknown:
        raise ValueError(f"réglages non autorisés : {sorted(unknown)}")

    missing = set(ALLOWED) - set(raw)
    if missing:
        raise ValueError(f"réglages manquants : {sorted(missing)}")

    for key, (low, high) in ALLOWED.items():
        value = raw[key]
        if type(value) is not int:
            raise ValueError(f"{key} doit être un entier, reçu {value!r}")
        if not low <= value <= high:
            raise ValueError(f"{key}={value} hors bornes [{low}, {high}]")

    return {**dict(sorted(raw.items())), **FIXED}
