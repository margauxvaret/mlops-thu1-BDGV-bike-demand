"""État accepté Lab 7.

artifacts/accepted/
    versions/<version_id>/   model.joblib, model-metadata.json, manifest.json (immuables)
    CURRENT.json             pointeur vers la version servie (remplacé atomiquement)
    HISTORY.jsonl            journal en ajout seul
    .lock                    verrou pendant une modification

Usage :
    uv run --locked python -m bike_demand.promote status
    uv run --locked python -m bike_demand.promote adopt
    uv run --locked python -m bike_demand.promote promote --candidate <dir> --decision <json> --expected-incumbent <id|none>
    uv run --locked python -m bike_demand.promote restore --version <id> --expected-incumbent <id>
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

DECISION_STATUS_FIELD = "status"
DECISION_DIGEST_FIELD = "model_sha256"


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


def _current_id(accepted: Path) -> str:
    current = read_pointer(accepted)
    return current["version_id"] if current else "none"


def _check_incumbent(accepted: Path, expected_incumbent: str) -> str:
    """Compare-and-swap : l'état courant doit être celui vu au moment de décider."""
    current_id = _current_id(accepted)
    if current_id != expected_incumbent:
        raise RuntimeError(
            f"incumbent changé : attendu {expected_incumbent}, "
            f"trouvé {current_id}. Refaire la décision."
        )
    return current_id


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


def _api_metadata(manifest: dict, version_id: str) -> dict:
    """Métadonnées compatibles avec api.py (model_sha256, model_version, features)."""
    identity = manifest["identity"]
    return {
        "model_version": f"rf-{manifest['run_id']}",
        "model_sha256": manifest["model_sha256"],
        "features": identity["features"],
        "data_sha256": identity["data_sha256"],
        "training_commit": manifest.get("git_sha"),
        "config": {"model": identity["settings"]},
        "run_id": manifest["run_id"],
        "accepted_version_id": version_id,
    }


def promote(
    candidate_dir: Path,
    decision_path: Path,
    expected_incumbent: str,
    accepted: Path = ACCEPTED,
) -> dict:
    """Promeut un candidat décidé. Tout contrôle raté lève AVANT de modifier l'état."""
    # 1) La décision doit être un accept.
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    status = decision.get(DECISION_STATUS_FIELD)
    if status != "accept":
        raise RuntimeError(f"promotion refusée : décision {status!r}, pas 'accept'")

    # 2) Les octets du candidat sont exactement ceux décidés.
    manifest = json.loads((candidate_dir / MANIFEST_FILE).read_text(encoding="utf-8"))
    candidate_sha = sha256(candidate_dir / MODEL_FILE)
    decided_sha = decision.get(DECISION_DIGEST_FIELD)
    if not candidate_sha == manifest["model_sha256"] == decided_sha:
        raise RuntimeError(
            f"octets différents : fichier {candidate_sha}, manifest "
            f"{manifest['model_sha256']}, décision {decided_sha}. Échec fermé."
        )

    with accepted_lock(accepted):
        # 3) L'incumbent n'a pas changé depuis la décision.
        current_id = _check_incumbent(accepted, expected_incumbent)

        # 4) Installer la nouvelle version, immuable, avant de toucher au pointeur.
        version_id = _next_version_id(accepted)
        metadata = _api_metadata(manifest, version_id)
        record = {
            "version_id": version_id,
            "source": f"promoted from candidate {manifest['run_id']}",
            "model_sha256": candidate_sha,
            "model_version": metadata["model_version"],
            "decision_file": str(decision_path),
            "decision_sha256": sha256(decision_path),
        }
        _install_version(
            accepted, version_id, candidate_dir / MODEL_FILE, metadata, record
        )

        # 5) Basculer le pointeur atomiquement, en gardant la version remplacée.
        pointer = {
            "version_id": version_id,
            "model_sha256": candidate_sha,
            "model_version": metadata["model_version"],
            "previous": current_id,
            "decision_sha256": record["decision_sha256"],
            "updated_at": _now(),
        }
        _write_json_atomic(accepted / "CURRENT.json", pointer)
        _append_history(accepted, {"event": "promote", **pointer})
        return pointer


def restore(
    version_id: str, expected_incumbent: str, accepted: Path = ACCEPTED
) -> dict:
    """Remet une version déjà acceptée comme courante, sans réentraîner."""
    target = accepted / "versions" / version_id
    if not target.is_dir():
        raise RuntimeError(f"version inconnue : {version_id} ({target} absent)")

    with accepted_lock(accepted):
        current_id = _check_incumbent(accepted, expected_incumbent)
        if current_id == version_id:
            raise RuntimeError(f"{version_id} est déjà la version courante")

        # Vérifier les octets AVANT de basculer : un checksum faux échoue fermé.
        metadata = verify_bundle(target)

        pointer = {
            "version_id": version_id,
            "model_sha256": metadata["model_sha256"],
            "model_version": metadata.get("model_version"),
            "previous": current_id,
            "updated_at": _now(),
        }
        _write_json_atomic(accepted / "CURRENT.json", pointer)
        _append_history(accepted, {"event": "restore", **pointer})
        return pointer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="État accepté Lab 7.")
    parser.add_argument(
        "--accepted", type=Path, default=ACCEPTED, help="dossier d'état accepté"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="affiche la version acceptée courante")
    sub.add_parser("adopt", help="adopte le modèle servi comme model-001")

    p = sub.add_parser("promote", help="promeut un candidat décidé 'accept'")
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--decision", required=True, type=Path)
    p.add_argument(
        "--expected-incumbent",
        required=True,
        help="version_id vu au moment de la décision, ou 'none'",
    )

    r = sub.add_parser("restore", help="remet une version acceptée, sans réentraîner")
    r.add_argument("--version", required=True)
    r.add_argument(
        "--expected-incumbent", required=True, help="version_id courant attendu"
    )

    args = parser.parse_args(argv)

    if args.command == "status":
        result = read_pointer(args.accepted)
    elif args.command == "adopt":
        result = adopt(args.accepted)
    elif args.command == "promote":
        result = promote(
            args.candidate, args.decision, args.expected_incumbent, args.accepted
        )
    else:
        result = restore(args.version, args.expected_incumbent, args.accepted)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
