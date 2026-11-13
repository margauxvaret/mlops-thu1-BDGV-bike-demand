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
CI now runs lock, lint, format, preflight and the full test suite on every PR: see "Lab 6: CI" below.

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


### Deployment identity and external check (Person 3)

Run the checker from the repository root while the container is running. It
uses HTTP only for observations; it never imports the application or uses
`TestClient`.

```bash
uv run --locked python scripts/check_deployment.py --model-dir artifacts
```

The expected model version comes from `artifacts/model-metadata.json`. The
expected model SHA256 is recomputed from `artifacts/model.joblib` and checked
against that metadata before making HTTP requests. The expected code revision
comes independently from `git rev-parse HEAD`. The checker compares these
values with `/health`, sends a valid `/predict` request, verifies that the
prediction is finite and nonnegative, and sends an invalid request (`hr=24`)
that must receive `422`. It prints a claim/expected/observed/result table and
returns exit code `1` if any check fails (exit code `2` means the local expected
identity could not be read).

PowerShell equivalent:

```powershell
uv run --locked python .\scripts\check_deployment.py --model-dir .\artifacts
if ($LASTEXITCODE -ne 0) { throw "Deployment check failed: $LASTEXITCODE" }
```

#### Identity: how can an operator tell which code and model are running?

- **Our choice:** inject the commit with Docker's `GIT_SHA` build argument;
  return it from `/health`. Report the loaded model version and the SHA256 of
  its bytes from `/health` too.
- **Rejected option:** infer identity from an image tag such as `latest` or
  trust only a version string.
- **Why:** tags can move, and a version label does not prove which file was
  loaded. The commit and model content hash identify the running inputs.

#### Expected: where do the checker’s expected values come from?

- **Our choice:** read `model_version` from the local artifact metadata, hash
  the local model file independently, and read the expected commit from
  `git rev-parse HEAD`.
- **Rejected option:** copy expected values from the service's `/health`
  response.
- **Why:** comparing the service with itself cannot reveal a stale image or
  wrong model mount.

#### Failure: how is a deployment failure demonstrated?

- **Our choice:** start the built image without its model volume, then run the
  same checker while keeping the expected model artifacts available locally.
  `/health` and prediction checks must fail, the checker must exit `1`, and
  `docker logs` must show `model_missing` plus the HTTP `503` request lines.
- **Rejected option:** simulate the outage by calling application functions or
  using an in-process test client.
- **Why:** the exercise is to observe the running container from outside. Keep
  the raw checker output and `docker logs` together under
  `reports/evidence/lab5/` after running this scenario.
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

## Lab 6: CI

### Workflow (Person 1)

`.github/workflows/ci.yml` runs one job, `checks`, on every pull request and
push targeting `integration` or `main`, and on manual dispatch. Steps, in order:

1. `uv lock --check`: `uv.lock` matches `pyproject.toml` (never regenerated).
2. `uv sync --locked`: install from the lock file only.
3. `uv run --locked ruff check .` and `uv run --locked ruff format --check .`
4. `uv run --locked python -m bike_demand.preflight`
5. `uv run --locked pytest -q -m infra`: fast plumbing tests.
6. `uv run --locked pytest -q -m "not infra"`: every other test (`lab1`,
   `exercise` and `tests/test_api.py`, which the starter never ran).

Safe settings kept from the starter: `permissions: contents: read`, no secrets,
`persist-credentials: false`, actions pinned by commit SHA, uv and Python
versions pinned, `timeout-minutes: 15`.

#### Machine: where do the checks run, and what do they not depend on?

- **Our choice:** a fresh GitHub-hosted `ubuntu-24.04` runner for every run,
  with uv `0.12.23` and Python `3.12` pinned, installing only from `uv.lock`
  (`uv sync --locked`, `uv run --locked`).
- **Rejected option:** `ubuntu-latest`, or trusting that tests pass on a team
  laptop.
- **Why:** `ubuntu-latest` changes under us without a commit. A laptop has a
  warm `.venv`, local `artifacts/` and `tracking/` (both gitignored) that a
  clean clone does not have; the runner starts from the repository alone.

#### Trigger: which events run the workflow?

- **Our choice:** `pull_request` and `push` on `integration` and `main`, plus
  `workflow_dispatch`. A `concurrency` group cancels an older run of the same
  pull request when a new commit is pushed; runs on `main` are never cancelled.
- **Rejected option:** run on every push to every branch, or only on `main`
  as in the starter.
- **Why:** every change reaches `integration` or `main` through a pull request,
  so it is checked before merge and again after merge, without duplicate runs
  on feature branches. Only `main` was covered before, so PRs into the
  integration branch were never checked.

#### Order: why are the steps in this order?

- **Our choice:** cheapest and most common failures first: lock check (seconds,
  no install), install, ruff lint and format (seconds), preflight, fast `infra`
  tests, then the rest of the suite (about 2 minutes).
- **Rejected option:** run a single `pytest` first and style checks last.
- **Why:** a stale lock or a style error is reported in seconds instead of
  after the slow tests. On our first run with this order, `ruff check` failed
  on `scripts/check_deployment.py` (unsorted imports, merged in PR #14) before
  any test ran; the fix was one commit and the next run was green.

### Reproduce a CI failure locally (Person 4)

Run the same commands as CI, in the same order. Stop at the first failure.

**bash (Linux, macOS, Git Bash)**
```bash
uv lock --check
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python -m bike_demand.preflight
uv run --locked pytest -q -m infra
uv run --locked pytest -q -m "not infra"
```

**PowerShell (Windows)**
```powershell
uv lock --check
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python -m bike_demand.preflight
uv run --locked pytest -q -m infra
uv run --locked pytest -q -m "not infra"
```

Run one test: `uv run --locked pytest tests/test_api.py -v` (same in both shells).

Replay our real CI failure (PR #16): `git switch --detach 12b519d`, then
`uv run --locked ruff check .` reports `I001 Import block is un-sorted` in
`scripts/check_deployment.py`. Go back with `git switch -`.

Never run `uv lock` or drop `--locked` to make a failure disappear: a stale lock
is a real failure, fixed by committing `pyproject.toml` and `uv.lock` together.

#### Coverage: what does CI check, and what does it not see?

- **Our choice:** coverage is a list of named defects, each tied to a test that
  we made fail on purpose (test map in the team report, Lab 6 section). CI does
  not see: the training run, our local MLflow runs in `tracking/`, local model
  files in `artifacts/` (both gitignored) or the live Cloud Run service (only the
  deploy job on `main` checks it).
- **Rejected option:** a line-coverage percentage (`pytest-cov`) as our coverage claim.
- **Why:** a percentage says which lines ran, not which defect would turn the run
  red. A test only counts once we have seen it fail for its defect.

#### Evidence: where is the proof, and why there?

- **Our choice:** raw run logs saved as text in `reports/evidence/lab6/`, with
  `INDEX.md` giving the run link, commit SHA, PR and result for each file.
- **Rejected option:** links to GitHub Actions runs, or screenshots only.
- **Why:** run logs expire after the retention period and screenshots cannot be
  searched or compared. Text plus a commit SHA lets anyone check the log
  against the exact code.

#### Repair: show one real red-to-green.

- **Our choice:** PR #16. Commit `12b519d` added the ruff steps; run
  [43183335657](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/actions/runs/43183335657)
  failed at `Lint (ruff)` after 19 s with `I001 Import block is un-sorted` in
  `scripts/check_deployment.py`. Commit `973ba53` sorted and reformatted the file;
  run [43184757992](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/actions/runs/43184757992)
  was green. Logs: `reports/evidence/lab6/01-pr16-rouge*.txt`, `02-pr16-vert.txt`.
- **Rejected option:** pressing "Re-run jobs", or breaking code artificially just to show red.
- **Why:** a re-run without a change proves nothing. Here a real defect (from the
  Lab 5 code) was caught by a new check and fixed by a new commit on the same PR.

#### Records: what do we keep, and how do we find it later?

- **Our choice:** in the repository: raw logs and `INDEX.md`, commit SHAs, the
  Cloud Run revision name and the identity output (`git_sha`, `model_version`,
  `model_sha256`), and the annotated tag `m3` on the submitted commit.
- **Rejected option:** relying on the GitHub Actions history and the Cloud Run console.
- **Why:** both live outside the repository and change or expire. The tag plus
  the committed files freeze what was checked and when.

### Lab 6 — Tests (Person 2)

#### Defects: which faults do the tests target?
- **Choice:** test named observable faults: `hr=24` is accepted, `/health` loses an identity field, a model with an incorrect SHA is loaded, the API prediction changes relative to the saved model, and non-finite inputs produce 500 instead of 422. Existing boundary tests cover further invalid values.
- **Rejected:** checking only successful HTTP responses.
- **Why:** each assertion identifies a contract violation. The non-finite regression required fixing validation-error serialization; the old expected-failure markers have been removed.

#### Failing: how do we know the tests can fail?
- **Choice:** temporarily introduce one defect at a time, run its targeted test, restore the source, and retain the output under `reports/evidence/lab6/personne2/`.
- **Rejected:** assume a green test would catch the defect.
- **Why:** the five `*.log` files named after mutations show the exact mutation, test, nonzero exit and assertion failure. These are local mutation experiments, not CI run or pull-request evidence.

#### Tolerance: where does the threshold come from?
- **Choice:** compare the API prediction with a fresh prediction from the earlier serialized `DummyRegressor` using zero absolute and relative tolerance. Five repeated readbacks and API calls measured 42.0 on both sides and a maximum difference of 0.0; see `measurement.log` and `measure_prediction.py`.
- **Rejected:** a generous arbitrary tolerance or comparing two newly trained models.
- **Why:** the fixture returns a deterministic constant; exact equality detects a changed response. This local measurement is specific to this fixture and environment, not evidence of numerical stability of a real model on every platform.

To reproduce, from the repository root after `uv sync --locked`:

```powershell
uv run --locked pytest -q tests/test_api.py
uv run --locked python reports/evidence/lab6/personne2/measure_prediction.py
```

```bash
uv run --locked pytest -q tests/test_api.py
uv run --locked python reports/evidence/lab6/personne2/measure_prediction.py
```
