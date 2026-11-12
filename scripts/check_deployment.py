#!/usr/bin/env python3
"""Check a running bike-demand deployment using HTTP only.

Expected identity comes from the local model artifact and the checked-out Git
revision. Observed identity comes only from HTTP responses from the container.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

VALID_REQUEST = {
    "season": 1,
    "yr": 0,
    "mnth": 1,
    "hr": 12,
    "holiday": 0,
    "weekday": 1,
    "workingday": 1,
    "weathersit": 1,
    "temp": 0.24,
    "atemp": 0.2879,
    "hum": 0.81,
    "windspeed": 0.0,
}


def _http(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: Any = None,
    timeout: float,
) -> tuple[int | None, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return None, f"{type(error).__name__}: {error}"
    try:
        return status, json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, body.decode("utf-8", errors="replace")[:300]


def _git_sha(repo_root: Path) -> str:
    top_level = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if Path(top_level).resolve() != repo_root.resolve():
        raise ValueError(f"{repo_root} is not the root of a Git checkout")
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _load_expected(model_dir: Path, repo_root: Path, supplied_git_sha: str | None):
    metadata_path = model_dir / "model-metadata.json"
    model_path = model_dir / "model.joblib"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if metadata.get("model_sha256") != model_sha:
        raise ValueError(
            f"{metadata_path} model_sha256 does not match {model_path} bytes"
        )
    version = metadata.get("model_version")
    if not isinstance(version, str) or not version:
        raise ValueError(f"{metadata_path} has no non-empty model_version")
    return version, model_sha, supplied_git_sha or _git_sha(repo_root)


def _display(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="HTTP address of the running container",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("artifacts"),
        help="independent local directory containing model.joblib and model-metadata.json",
    )
    parser.add_argument(
        "--git-sha",
        help="expected checked-out commit (default: git rev-parse HEAD in the repository)",
    )
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    try:
        expected_version, expected_model_sha, expected_git_sha = _load_expected(
            args.model_dir, repo_root, args.git_sha
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as error:
        parser.exit(2, f"Cannot load independent expected identity: {error}\n")

    rows: list[tuple[str, str, str, bool]] = []

    def add(claim: str, expected: Any, observed: Any, passed: bool) -> None:
        rows.append((claim, _display(expected), _display(observed), passed))

    health_status, health = _http(args.base_url, "/health", timeout=args.timeout)
    add("/health HTTP status", 200, health_status, health_status == 200)
    if isinstance(health, dict):
        observed_version = health.get("model_version")
        observed_sha = health.get("model_sha256")
        observed_git = health.get("git_sha")
    else:
        observed_version = observed_sha = observed_git = None
    add(
        "model_version",
        expected_version,
        observed_version,
        observed_version == expected_version,
    )
    add(
        "model_sha256",
        expected_model_sha,
        observed_sha,
        observed_sha == expected_model_sha,
    )
    add("git_sha", expected_git_sha, observed_git, observed_git == expected_git_sha)

    predict_status, prediction_body = _http(
        args.base_url,
        "/predict",
        method="POST",
        payload=VALID_REQUEST,
        timeout=args.timeout,
    )
    prediction = (
        prediction_body.get("prediction") if isinstance(prediction_body, dict) else None
    )
    if isinstance(prediction, (int, float)) and not isinstance(prediction, bool):
        finite_nonnegative = math.isfinite(prediction) and prediction >= 0
    else:
        finite_nonnegative = False
    add("valid /predict status", 200, predict_status, predict_status == 200)
    add(
        "valid prediction finite and >= 0",
        "finite number >= 0",
        prediction,
        predict_status == 200 and finite_nonnegative,
    )

    invalid_request = {**VALID_REQUEST, "hr": 24}
    invalid_status, _ = _http(
        args.base_url,
        "/predict",
        method="POST",
        payload=invalid_request,
        timeout=args.timeout,
    )
    add("invalid /predict status (hr=24)", 422, invalid_status, invalid_status == 422)

    headers = ("claim", "expected", "observed", "result")
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(3)]
    print(" | ".join(headers[i].ljust(widths[i]) for i in range(3)) + " | result")
    print("-+-".join("-" * width for width in widths) + "-+--------")
    for claim, expected, observed, passed in rows:
        print(
            f"{claim.ljust(widths[0])} | {expected.ljust(widths[1])} | "
            f"{observed.ljust(widths[2])} | {'PASS' if passed else 'FAIL'}"
        )
    failures = sum(not passed for _, _, _, passed in rows)
    print(f"\n{len(rows) - failures}/{len(rows)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
