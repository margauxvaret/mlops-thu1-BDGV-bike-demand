"""État accepté Lab 7.

artifacts/accepted/
    versions/<version_id>/   model.joblib, model-metadata.json, manifest.json (immuables)
    CURRENT.json             pointeur vers la version servie (remplacé atomiquement)
    HISTORY.jsonl            journal en ajout seul
    .lock                    verrou pendant une modification

Usage :
    uv run --locked python -m bike_demand.promote status
    uv run --locked python -m bike_demand.promote adopt
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from bike_demand.pipeline import ROOT
from bike_demand.preflight import sha256

ACCEPTED = ROOT / "artifacts" / "accepted"
SERVED = ROOT / "artifacts"

MODEL_FILE = "model.joblib"
METADATA_FILE = "model-metadata.json"
MANIFEST_FILE = "manifest.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_pointer(accepted: Path = ACCEPTED) -> dict | None:
    pointer = accepted / "CURRENT.json"
    if not pointer.exists():
        return None
    return json.loads(pointer.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, data: dict) -> None:
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _append_history(accepted: Path, event: dict) -> None:
    with open(accepted / "HISTORY.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _now(), **event}, sort_keys=True) + "\n")


@contextmanager
def accepted_lock(accepted: Path = ACCEPTED):
    """Un seul processus modifie l'état accepté à la fois."""
    accepted.mkdir(parents=True, exist_ok=True)
    lock = accepted / ".lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError(
            f"verrou présent ({lock}) : une autre opération est en cours, "
            "ou un processus a été tué. Vérifie, puis supprime le fichier à la main."
        ) from None
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def verify_bundle(version_dir: Path) -> dict:
    """Vérifie les octets du modèle contre ses métadonnées. Échec fermé."""
    metadata = json.loads((version_dir / METADATA_FILE).read_text(encoding="utf-8"))
    actual = sha256(version_dir / MODEL_FILE)
    if actual != metadata.get("model_sha256"):
        raise RuntimeError(
            f"checksum différent dans {version_dir} : attendu "
            f"{metadata.get('model_sha256')}, trouvé {actual}. Ne pas charger."
        )
    return metadata


def _next_version_id(accepted: Path) -> str:
    versions = accepted / "versions"
    existing = [
        p for p in versions.iterdir() if p.is_dir() and not p.name.startswith(".")
    ]
    return f"model-{len(existing) + 1:03d}"


def _install_version(
    accepted: Path, version_id: str, model: Path, metadata: dict, manifest: dict
) -> Path:
    """Copie un bundle dans versions/<id> de façon atomique, puis le rend lecture seule."""
    versions = accepted / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    final = versions / version_id
    if final.exists():
        raise RuntimeError(f"{final} existe déjà : une version n'est jamais réécrite")
    tmp = versions / f".tmp-{version_id}-{uuid.uuid4().hex[:8]}"
    tmp.mkdir()
    try:
        shutil.copy2(model, tmp / MODEL_FILE)
        (tmp / METADATA_FILE).write_text(
            json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
        )
        (tmp / MANIFEST_FILE).write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        verify_bundle(tmp)
        os.replace(tmp, final)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    for f in final.iterdir():
        f.chmod(stat.S_IREAD)
    return final


def adopt(accepted: Path = ACCEPTED, served: Path = SERVED) -> dict:
    """Enregistre le modèle actuellement servi comme première version acceptée."""
    with accepted_lock(accepted):
        if read_pointer(accepted) is not None:
            raise RuntimeError(
                "état accepté déjà initialisé : adopt ne sert qu'une fois"
            )

        metadata = verify_bundle(served)
        (accepted / "versions").mkdir(parents=True, exist_ok=True)
        version_id = _next_version_id(accepted)
        manifest = {
            "version_id": version_id,
            "source": "adopted from the model served in Lab 5 (artifacts/)",
            "model_sha256": metadata["model_sha256"],
            "model_version": metadata.get("model_version"),
        }
        _install_version(accepted, version_id, served / MODEL_FILE, metadata, manifest)

        pointer = {
            "version_id": version_id,
            "model_sha256": metadata["model_sha256"],
            "model_version": metadata.get("model_version"),
            "previous": None,
            "updated_at": _now(),
        }
        _write_json_atomic(accepted / "CURRENT.json", pointer)
        _append_history(accepted, {"event": "adopt", **pointer})
        return pointer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="État accepté Lab 7.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="affiche la version acceptée courante")
    sub.add_parser("adopt", help="adopte le modèle servi comme model-001")
    args = parser.parse_args(argv)

    if args.command == "status":
        print(json.dumps(read_pointer(), indent=2, sort_keys=True))
    elif args.command == "adopt":
        print(json.dumps(adopt(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
