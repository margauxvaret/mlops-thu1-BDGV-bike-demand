# Bike Demand: Week 1 starter

Teams of 3–4 use one private GitHub repository throughout the course. Lab 1 is
repository setup, Git workflow and quality checks. Lab 2 adds validated data,
chronological splitting, a baseline comparison and local MLflow tracking.
No Docker, cloud account or MLflow server is needed this week.

## Setup: Lab 1

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/)
(`>=0.12.19,<0.13`). Python **3.12** is required; uv can download it. From the
`bike-demand/` root:

```bash
uv python install 3.12
uv sync --locked
uv run --locked python -m bike_demand.preflight
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest -q -m infra
uv run --locked pytest -q -m lab1
```

First setup requires internet for Python and the locked dependencies, unless
these exact distributions are already cached. The frozen UCI CSV ships here;
preflight does not download/repair it. `uv.lock` is shared across platforms;
that is not evidence that every OS has been tested. macOS setup has been checked;
Windows and Linux remain unverified. Remote CI is unavailable until a permitted
repository is configured and a workflow actually runs on the checked revision.
Do not regenerate the lock just to bypass an installation failure.

## Expected failure and exercise: Lab 1

`pytest -m infra` must pass immediately. `pytest -m lab1` has **one intentional
behavior failure** in `src/bike_demand/team.py`: the helper
`normalize_team_slug` does not yet meet the contract in `tests/lab1/test_team.py`
(trim, lowercase, join whitespace with hyphens, reject blank names with
`ValueError`). Read the assertion, diagnose the cause, make a small repair and add
one useful test of your own. Do not weaken assertions, skip tests or disable
checks. Sync or import errors, or failures outside `lab1`, are setup problems:
diagnose them separately.

Fill in `WORKING-AGREEMENT.md`. Use a task branch, open a pull request, and get a
review from another member before merging. Rotate driver/reviewer roles and the
main PR author between labs. Keep actual evidence in `reports/lab-01.md` and
`reports/week-01-team.md`; templates contain no pre-filled results.

## Expected failures: Lab 2

The student export has bounded TODOs in `src/bike_demand/`:

| File | Your task |
| --- | --- |
| `validate.py` | Categorical domains, finite normalised ranges, nonnegative counts, date windows |
| `split.py` | Chronological nonempty/disjoint/complete partitions; sort `(dteday, hr, instant)` |
| `train.py` | Ordered predictors, train-mean comparator, RF fit and validation MAE |

`NotImplementedError("TODO(Week 1, Lab 2): ...")` and failing exercise tests are
**expected before implementation**, not environment failures. Infra must pass
immediately. Do not skip/mute exercise tests or fabricate metrics to get green.
Tracking, metadata/history, configuration and input parsing are already supplied.
Read the failing test, inspect the contract, implement one TODO, and rerun:

```bash
uv run --locked pytest -q -m exercise
uv run --locked python -m bike_demand.validate --data data/raw/hour.csv
uv run --locked python -m bike_demand.train --config configs/baseline.yaml
uv run --locked pytest -q
```

Keep `data/raw/hour.csv` unchanged; use copies and `tests/fixtures/` for deliberate
faults. `missing-temp.csv` is the worked Fault A; design your own Fault B by
breaking exactly one contract rule or split boundary on a tiny copy, with a valid
control and a test of your own. The supplied `hum-out-of-range.csv` is another
worked example, not your Fault B. Missing hours are valid. Features and splits are fixed in the config and
code. Fit only on 2011 training rows; compare both predictors on the same
2012 January–June validation rows. Hold July–December 2012 test rows throughout
Weeks 1–4; do not compute test metrics. MAE is rentals/hour, not accuracy, and
RF is not required to beat the comparator. The task uses supplied weather;
it does not forecast future weather or station-level demand.

## Outputs and readback

Each successful train execution creates two separate MLflow runs, a saved
`artifacts/model.joblib` and `model-metadata.json`, latest `reports/metrics.json`,
and one appended `reports/metrics-history.jsonl` line. Metadata records feature
order, data identity, model version and run ID. A commit is recorded when Git is
available; `working_tree_dirty` prevents uncommitted code being mistaken for a
committed revision. Train reloads the trusted local model and verifies validation
MAE/metadata and logged artifact bytes. Never load untrusted joblib files.
Optional stretch, only after the core is complete and reviewed: run train again
unchanged and compare both run IDs and observed MAEs/history. Do not promise
byte-identical models across systems/library versions.

Viewer is optional; training does not depend on it:

```bash
uv run --locked mlflow server --backend-store-uri sqlite:///tracking/mlflow.db --default-artifact-root tracking/artifacts --no-serve-artifacts --host 127.0.0.1 --port 5000 --workers 1
```

`artifacts/`, `tracking/` and `.venv/` are ignored by Git. Team metrics may be
committed as evidence; never commit credentials or individual private reports.
CI currently checks only infrastructure/quality; expand it in Week 3.

## Support and individual reports

If setup remains blocked after five minutes, contact the instructor using the
support route recorded in your working agreement. Do not spend the whole lab
repairing a laptop. Ask for an approved recovery function only if coding remains
blocked; acknowledge the supplied code and assistance in your report. Recovery
is instructor-controlled, not bundled here.

## Names, reports and screenshots

Repository names (lowercase, hyphens, the same for the whole course):

- Team repository: `mlops-<session>-<team-name>-bike-demand`, for example
  `mlops-thu1-sparrows-bike-demand`. Sessions: `thu1`, `thu2`, `fri1`, `fri2`
  (1 = morning, 2 = afternoon).
- Your private report repository: `mlops-<session>-<github-username>`, for example
  `mlops-thu1-minhtc`. You create it and invite the instructor (`minhtc-uca`). Start from the
  [report template](../report-template/README.md) and commit to `main`; no report
  pull request or CI is used.

Reports mix writing and images. Save screenshots in `reports/images/` and embed
them in the report (see the template). A screenshot supports, but does not replace,
the command, revision and your explanation. Never show tokens, passwords or
personal data. Team evidence goes in `reports/lab-01.md` and
`reports/week-01-team.md`, with team screenshots in `reports/images/`.
Each weekly report is due Sunday 23:59 of the same week (published time zone).
Assessment policy comes from the instructor, not this repository.
See `BACKLOG.md` for later labs.

## Lab 3: dependency lock

`uv.lock` is the source of truth: install and run only with `--locked`
(`uv sync --locked`, `uv run --locked ...`, and inside the Docker image).

If `pyproject.toml` changes without `uv lock`, then `uv lock --check`, CI and
`docker build` all fail. Fix it with `uv lock` in a reviewed PR that commits
`pyproject.toml` and `uv.lock` together. Never use `--frozen` to get green: it
skips the check.

Evidence: `reports/lab3/logs/stale-lock.log`.

## Lab 3: Build & rerun

Same code, clean environment: the Lab 2 baseline runs from a Docker image built
from the committed `uv.lock`, with no `.venv`, cache or secret from any laptop.

### Prerequisites

- On Windows, run the commands below in Git Bash. The repository currently tracks
  both `DockerFile` and `Dockerfile`, which can collide on a case-insensitive
  Windows checkout: for a reliable rerun, use a Linux/WSL checkout (see
  "Lab 3: clean Docker rerun" below).

### Build

```bash
git clone https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand.git
cd mlops-thu1-BDGV-bike-demand
git checkout <SHA>
docker build --build-arg GIT_COMMIT=$(git rev-parse HEAD) -t bdgv-baseline:lab3 .
```

### Run the baseline and the tests

```bash
docker run --name lab3-run --network none bdgv-baseline:lab3
docker run --rm --network none bdgv-baseline:lab3 uv run --locked pytest -q
```

### Collect the outputs and check the lock

```bash
mkdir -p ../evidence
docker cp lab3-run:/app/artifacts ../evidence/artifacts
docker cp lab3-run:/app/reports/metrics.json ../evidence/metrics.json
docker rm lab3-run
uv lock --check
```

### Expected results

Same data snapshot, config and split as Lab 2: validation MAE (rentals/hour)
should match the Lab 2 values in `reports/metrics.json`.

| Predictor | Expected MAE |
| --- | --- |
| Train-mean comparator | 154.23 |
| Random forest | 86.85 |
- Any other failure: write down the failing step, the exact message and who
  owns the next action.

### Lab 3: clean Docker rerun

After the Lab 3 changes are merged, a teammate can rebuild and rerun the baseline
from a fresh clone. Replace `<SHA>` with the reviewed integration commit to
reproduce.

The repository currently contains both `DockerFile` and `Dockerfile`. On a
case-insensitive Windows checkout, use a case-sensitive Linux/WSL checkout for
this procedure so Git can materialize both tracked paths independently.

```sh
git clone <url-team-repo> lab3-rerun
cd lab3-rerun
git checkout <SHA>
mkdir -p ../evidence
{ git rev-parse HEAD; sha256sum uv.lock; } | tee ../evidence/revision.txt
docker build --no-cache --progress=plain \
  --build-arg GIT_COMMIT="$(git rev-parse HEAD)" \
  -t bdgv-baseline:lab3 . 2>&1 | tee ../evidence/build.log
docker image inspect bdgv-baseline:lab3 \
  --format '{{.Id}} {{.Os}}/{{.Architecture}}' | tee ../evidence/image.txt
docker run --name lab3-rerun --network none bdgv-baseline:lab3 \
  2>&1 | tee ../evidence/run.log
docker run --rm --network none bdgv-baseline:lab3 \
  uv run --locked pytest -q 2>&1 | tee ../evidence/tests.log
docker cp lab3-rerun:/app/artifacts ../evidence/artifacts
docker rm lab3-rerun
```

The model file is retained with the rerun evidence, not committed; record its
SHA-256 in the team report. The rerun logs and metrics are in
`reports/lab3/logs/`.

# Lab 5: 

### Logs (Gabrielle)

The service writes **one JSON line per request** to stdout, plus one line at
start-up saying whether the model loaded. Read them from outside the container:

```bash
docker logs <container>
docker logs --since 5m <container>
docker logs <container> > reports/evidence/lab5/<git-sha>.jsonl  
```

Set the level with `-e LOG_LEVEL=DEBUG|INFO|WARNING` (default `INFO`). An unknown
level stops the service at start-up instead of silently logging nothing.
Uvicorn's own access log is turned off (`--no-access-log` in the Dockerfile `CMD`)
so a request never writes two lines.

| Field | Meaning |
| --- | --- |
| `event` | `served` (2xx), `rejected` (4xx), `unavailable` (503), `failed` (500); at start-up `model_loaded` or `model_missing` |
| `request_id` | Request id, also returned in the `X-Request-ID` response header. A client may send its own (letters, digits, `.` `_` `-`, max 64), otherwise one is generated |
| `method`, `path` | HTTP method and route, without the query string |
| `status` | HTTP status returned |
| `ms` | Time spent in the service, in milliseconds |
| `model_version` | Version of the loaded model; `null` when no model is loaded |
| `invalid_fields` | Rejected input only: `field:reason`, e.g. `hr:less_than_equal`, `cnt:extra_forbidden` |
| `error`, `error_at` | Crash only: exception class and `file:line` where it was raised |

The start-up line `model_loaded` also carries `model_dir`, `model_sha256` and
`git_sha`, so the logs alone tell which model file and which code revision were
running. `model_missing` carries `model_dir`, `git_sha` and the `reason` the
model could not be used (missing file, SHA256 mismatch, different features).

#### Log line: what must one request tell an operator?

- **Our choice:** what happened (`event`, `status`), to which request
  (`request_id`, `method`, `path`), how long it took (`ms`) and which model
  answered (`model_version`). A rejected request also says which fields were
  wrong and why, without their values.
- **Rejected option:** keep Uvicorn's default access line
  (`"POST /predict HTTP/1.1" 422`).
- **Why:** it says neither which model answered nor why a request was refused,
  it is plain text that is hard to filter, and it contains the client's IP
  address. With `request_id` echoed in the response header, the check script can
  send a known id and find its exact line in `docker logs`.

#### Secrets: what must never appear in a log?

- **Our choice:** no request or response bodies (input values, predictions), no
  headers (they can carry tokens or cookies), no query strings, no client IP
  addresses (personal data), no environment variables, no exception messages
  while handling a request. For invalid input we log only the field name and the
  error type; for a crash only the exception class and `file:line`. The one
  message we do log is the start-up `reason` a model could not be loaded: it is
  about our own files in `MODEL_DIR`, never about what a client sent.
- **Rejected option:** log the full request body of rejected requests, or the
  full traceback, which would make debugging faster.
- **Why:** a log is copied, shipped and read by more people than the service
  itself; anything a client sends may one day be personal or secret, and an
  exception message can quote it. Field name + reason is enough to diagnose a
  422; `error_at` points to the line to read for a 500. Unit tests check that a
  submitted value and an exception message never reach the log.

## Lab 4: API container and deployment (Person D)

### Model delivery decision

We supply the trained model with a **read-only bind mount at run time**. The image contains the API and its locked Python dependencies, not a model binary. `MODEL_DIR` still defaults to `artifacts/` in the application; the container command explicitly sets it to `/models` to match the mount.

- **Chosen:** mount `artifacts/` at `/models` with read-only access and pass `MODEL_DIR=/models`.
- **Rejected — train during image build:** every build would execute training, take longer, and make an image build depend on training inputs and behavior.
- **Rejected — commit the model:** the binary would be coupled to source changes, enlarge Git history, and make artifact replacement harder to review.

The service never trains at startup. Without a model, it stays up and returns `503` for `/health` and for a valid `/predict` request.

### Build the image

From the repository root, on the reviewed commit that contains the API routes and request schema:

```bash
set -o pipefail
mkdir -p reports/lab4/logs
docker build --no-cache --progress=plain -f Dockerfile \
  --build-arg GIT_SHA="$(git rev-parse HEAD)" \
  -t bdgv-api:lab4 . 2>&1 | tee reports/lab4/logs/docker-build.log
docker image inspect bdgv-api:lab4 \
  --format '{{.Id}} {{.Os}}/{{.Architecture}}' \
  | tee reports/lab4/logs/image.txt
```

PowerShell equivalent:

```powershell
New-Item -ItemType Directory -Force .\reports\lab4\logs | Out-Null
$commit = (git rev-parse HEAD).Trim()
docker build --no-cache --progress=plain -f Dockerfile `
  --build-arg "GIT_SHA=$commit" -t bdgv-api:lab4 . 2>&1 `
  | Tee-Object .\reports\lab4\logs\docker-build.log
if ($LASTEXITCODE -ne 0) { throw "Docker build failed: $LASTEXITCODE" }
docker image inspect bdgv-api:lab4 `
  --format '{{.Id}} {{.Os}}/{{.Architecture}}' `
  | Tee-Object .\reports\lab4\logs\image.txt
```

### Run with the model mounted

The local `artifacts/` directory must already contain `model.joblib` and `model-metadata.json`. Do not retrain for this deployment exercise. If those files are not available yet, do not invent or retrain an artifact: build the image and run the no-model check below, then request the existing Lab 4 artifact from the teammate who trained it before attempting the successful prediction check.

```bash
docker rm -f bdgv-api-lab4 2>/dev/null || true
docker run -d --name bdgv-api-lab4 \
  -p 127.0.0.1:8000:8000 \
  -e MODEL_DIR=/models \
  --mount type=bind,source="$(pwd)/artifacts",target=/models,readonly \
  bdgv-api:lab4
```

PowerShell:

```powershell
$ModelPath = (Resolve-Path .\artifacts).Path
docker rm -f bdgv-api-lab4 2>$null
docker run -d --name bdgv-api-lab4 `
  -p 127.0.0.1:8000:8000 -e MODEL_DIR=/models `
  --mount "type=bind,source=$ModelPath,target=/models,readonly" `
  bdgv-api:lab4
```

Send requests from outside the container and preserve the observed status and body:

```bash
curl -sS -i http://127.0.0.1:8000/health \
  | tee reports/lab4/logs/health-with-model.log
VALID='{"season":1,"yr":1,"mnth":3,"hr":8,"holiday":0,"weekday":2,"workingday":1,"weathersit":1,"temp":0.34,"atemp":0.33,"hum":0.55,"windspeed":0.19}'
curl -sS -i -H 'Content-Type: application/json' \
  -d "$VALID" http://127.0.0.1:8000/predict \
  | tee reports/lab4/logs/predict-with-model.log
curl -sS -i -H 'Content-Type: application/json' \
  -d '{"season":1,"yr":1,"mnth":3,"hr":24,"holiday":0,"weekday":2,"workingday":1,"weathersit":1,"temp":0.34,"atemp":0.33,"hum":0.55,"windspeed":0.19}' \
  http://127.0.0.1:8000/predict \
  | tee reports/lab4/logs/predict-invalid.log
docker logs bdgv-api-lab4 2>&1 | tee reports/lab4/logs/container-with-model.log
```

Expected: `/health` and valid `/predict` return `200`; the prediction response has `prediction` and `model_version`; `hr=24` returns `422`. The API test suite also checks that `cnt`, `casual`, `registered`, and unknown fields return `422`.

### Deliberate no-model check

Stop the mounted-model container, then start the same image with no volume. This proves the service reports missing-model status instead of training or crashing:

```bash
docker rm -f bdgv-api-lab4
docker run -d --name bdgv-api-lab4 -p 127.0.0.1:8000:8000 \
  -e MODEL_DIR=/models bdgv-api:lab4
curl -sS -i http://127.0.0.1:8000/health \
  | tee reports/lab4/logs/health-no-model.log
curl -sS -i -H 'Content-Type: application/json' -d "$VALID" \
  http://127.0.0.1:8000/predict \
  | tee reports/lab4/logs/predict-no-model.log
docker logs bdgv-api-lab4 2>&1 | tee reports/lab4/logs/container-no-model.log
docker rm -f bdgv-api-lab4
```

Expected: `/health` and a **valid** `/predict` request return `503`; invalid input still returns `422`. Keep the raw build output, image ID, HTTP responses, and container logs under `reports/lab4/logs/`. Do not commit the model binary.

PowerShell request checks:

```powershell
$valid = '{"season":1,"yr":1,"mnth":3,"hr":8,"holiday":0,"weekday":2,"workingday":1,"weathersit":1,"temp":0.34,"atemp":0.33,"hum":0.55,"windspeed":0.19}'
curl.exe -sS -i http://127.0.0.1:8000/health `
  | Tee-Object .\reports\lab4\logs\health-with-model.log
curl.exe -sS -i -H "Content-Type: application/json" `
  --data-raw $valid http://127.0.0.1:8000/predict `
  | Tee-Object .\reports\lab4\logs\predict-with-model.log
$invalid = '{"season":1,"yr":1,"mnth":3,"hr":24,"holiday":0,"weekday":2,"workingday":1,"weathersit":1,"temp":0.34,"atemp":0.33,"hum":0.55,"windspeed":0.19}'
curl.exe -sS -i -H "Content-Type: application/json" `
  --data-raw $invalid http://127.0.0.1:8000/predict `
  | Tee-Object .\reports\lab4\logs\predict-invalid.log
docker logs bdgv-api-lab4 2>&1 `
  | Tee-Object .\reports\lab4\logs\container-with-model.log
```

PowerShell no-model check:

```powershell
docker rm -f bdgv-api-lab4 2>$null
docker run -d --name bdgv-api-lab4 `
  -p 127.0.0.1:8000:8000 -e MODEL_DIR=/models bdgv-api:lab4
curl.exe -sS -i http://127.0.0.1:8000/health `
  | Tee-Object .\reports\lab4\logs\health-no-model.log
$valid = '{"season":1,"yr":1,"mnth":3,"hr":8,"holiday":0,"weekday":2,"workingday":1,"weathersit":1,"temp":0.34,"atemp":0.33,"hum":0.55,"windspeed":0.19}'
curl.exe -sS -i -H "Content-Type: application/json" `
  --data-raw $valid http://127.0.0.1:8000/predict `
  | Tee-Object .\reports\lab4\logs\predict-no-model.log
docker logs bdgv-api-lab4 2>&1 `
  | Tee-Object .\reports\lab4\logs\container-no-model.log
docker rm -f bdgv-api-lab4
```
