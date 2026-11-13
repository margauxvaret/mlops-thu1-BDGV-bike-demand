"""Preuve Lab 7 : une décision non-accept laisse l'état accepté inchangé.

Usage :
    uv run --locked python scripts/lab7_reject_evidence.py --candidate <dir> --decision <json>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bike_demand import promote as pr
from bike_demand.preflight import sha256


def snapshot(accepted: Path) -> dict:
    pointer = pr.read_pointer(accepted)
    model = accepted / "versions" / pointer["version_id"] / pr.MODEL_FILE
    return {
        "current": pointer["version_id"],
        "pointer_sha256": sha256(accepted / "CURRENT.json"),
        "model_sha256_on_disk": sha256(model),
        "versions": sorted(p.name for p in (accepted / "versions").iterdir()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--accepted", type=Path, default=pr.ACCEPTED)
    args = parser.parse_args()

    before = snapshot(args.accepted)
    print("BEFORE", json.dumps(before, sort_keys=True))
    print("DECISION", args.decision.read_text(encoding="utf-8").strip())

    try:
        pr.promote(args.candidate, args.decision, before["current"], args.accepted)
    except RuntimeError as exc:
        print("PROMOTION REFUSED:", exc)
    else:
        print("ERREUR : la promotion a réussi, la décision n'était pas un rejet")
        return 2

    after = snapshot(args.accepted)
    print("AFTER ", json.dumps(after, sort_keys=True))
    same = before == after
    print("STATE UNCHANGED" if same else "STATE CHANGED")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
