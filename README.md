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


## Lab 5 — Déploiement

### 1. SHA du commit

```
f47c1151446891b3e6912862db352bb971fed261
```

(fichier brut : `reports/evidence/lab5/commit-sha.txt`)

### 2. Image et commande utilisée

ID de l'image : `sha256:5ac5fe4f2a563e19b86dfae700060a2a8d380850cefb4753fecb355f22f49c87` (`bdgv-api:lab5`)

Build :

```powershell
docker build --progress=plain --build-arg GIT_COMMIT=$FULL -t bdgv-api:lab5 .
```

Run :

```powershell
docker run -d --name bike-api -e MODEL_DIR=/models -p 127.0.0.1:8000:8000 -v "${PWD}/artifacts:/models:ro" bdgv-api:lab5
```

Le label `org.opencontainers.image.revision` de l'image vaut `f47c1151446891b3e6912862db352bb971fed261`, identique au SHA du commit.

### 3. Requêtes envoyées et logs obtenus

| Requête | Attendu | Observé | Ligne de log |
|---|---|---|---|
| `GET /health` | 200 | 200, `{"status":"ok","model_version":"baseline-3231526734d2"}` | `INFO: 172.17.0.1:38998 - "GET /health HTTP/1.1" 200 OK` |
| `POST /predict` valide | 200 | 200, `{"prediction":437.861105705694,"model_version":"baseline-3231526734d2"}` | `INFO: 172.17.0.1:39006 - "POST /predict HTTP/1.1" 200 OK` |
| `POST /predict` avec `hr=24` | 422 | 422, `Input should be less than or equal to 23` | `INFO: 172.17.0.1:39016 - "POST /predict HTTP/1.1" 422 Unprocessable Entity` |

Fichiers bruts : `reports/evidence/lab5/` (`health.txt`, `predict-valid.txt`, `predict-hr24.txt`, `docker-logs.txt`, `docker-build.txt`, `image-id.txt`, `commit-sha.txt`).

### 4. Panne provoquée

- **Panne** : lancement du conteneur sans monter le modèle (pas de `-v`).
- **Statut HTTP** : 503 sur `/health`.
- **Corps** : `{"status":"unavailable","reason":"FileNotFoundError: [Errno 2] No such file or directory: '/models/model-metadata.json'"}`
- **Logs** : `No usable model in /models (FileNotFoundError: ... '/models/model-metadata.json')` puis `GET /health ... 503 Service Unavailable`
- **Script** : non lancé (script absent, voir blocages).

Fichiers : `failure-health.txt`, `failure-docker-logs.txt`.

### 5. Blocages

1. **Script de vérification absent**
   - Étape : `uv run python scripts/check_deployment.py`
   - Message : `can't open file '...\scripts\check_deployment.py': [Errno 2] No such file or directory` (exit code 2)
   - Qui doit agir : personne 3 (script), puis merge dans la branche d'intégration.
2. **`/health` ne contient pas l'identité du service**
   - Constat : seulement `status` et `model_version`, pas de `git_sha` ni `model_sha256`.
   - Qui doit agir : personne 1 (ajout des champs).
3. **Logs non structurés**
   - Constat : logs texte uvicorn, pas de ligne JSON avec id de requête, durée et `model_version`.
   - Qui doit agir : personne 2.
4. **Port 8000 déjà occupé** (résolu)
   - Message : `Bind for 0.0.0.0:8000 failed: port is already allocated`
   - Cause : un ancien conteneur du Lab 4 (`funny_williams`) tournait. Résolu par `docker stop funny_williams`.


### 6. Les 10 questions

| Question | Notre choix | Option écartée | Pourquoi |
|---|---|---|---|
| **settings** | Config par variables d'environnement (`-e MODEL_DIR=/models`) | Valeurs en dur dans l'image | Une même image sert pour plusieurs configurations sans rebuild |
| **model** | Modèle monté depuis `./artifacts` avec `-v ...:ro` | Modèle copié dans l'image | L'image reste indépendante du modèle, on change de modèle sans rebuild (à confirmer avec P1) |
| **ready** | Prêt = `/health` répond 200 (modèle chargé) | Considérer prêt dès que le conteneur tourne | Un conteneur « Up » sans modèle ne peut pas prédire |
| **broken** | 503 sur `/health` et sur `/predict` avec un message sur le modèle introuvable | Plantage au démarrage | Le service reste joignable et dit clairement ce qui manque |
| **log line** | Une ligne JSON par requête sur stdout : événement, id de requête, route, statut, durée en ms, `model_version` | Logs texte libres d'uvicorn | Quelqu'un qui lit seulement `docker logs` comprend ce qui s'est passé, et les 422 et 503 sont aussi loggés |
| **secrets** | Jamais de secrets, de variables d'environnement sensibles ni de corps de requête complet dans les logs | Tout loguer pour faciliter le débogage | Les logs sont lus par d'autres personnes et conservés : une fuite y serait durable |
| **identity** | `/health` expose `model_version`, `model_sha256` (calculé au chargement du modèle) et `git_sha` (injecté au build) | Un numéro de version écrit à la main | Ces valeurs viennent des artefacts réels et peuvent être vérifiées de l'extérieur |
| **expected** | Valeurs attendues lues dans les métadonnées de l'artefact modèle et avec `git rev-parse HEAD` | Lire les valeurs dans `/health` lui-même | Comparer le service à ce qu'il dit de lui-même ne prouve rien |
| **failure** | Lancement sans modèle (503) | Image construite sur un ancien commit | Panne simple à provoquer, visible dans `/health` et dans les logs |
| **promise** | Un service déployé promet de dire la vérité sur lui-même : quel code (`git_sha`), quel modèle (`model_version`, `model_sha256`), s'il est prêt (200) ou non (503 avec un message clair), et de laisser des logs qui expliquent chaque requête | Promettre seulement « le conteneur tourne » | Un conteneur qui tourne sans modèle ou avec le mauvais code est en panne sans que ça se voie |

**Définition de « déployé »** : le conteneur tourne depuis une image construite à partir d'un commit connu, `/health` répond 200, et une vérification faite de l'extérieur (HTTP sur `127.0.0.1:8000`) confirme que `git_sha`, `model_version` et `model_sha256` sont ceux attendus, qu'un `/predict` valide répond 200 et qu'une entrée invalide répond 422. Un conteneur « Up » qui n'a pas passé cette vérification n'est pas considéré comme déployé.