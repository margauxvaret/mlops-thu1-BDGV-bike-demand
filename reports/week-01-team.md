# Week 1, Labs 1–2: team evidence

> Filled only with results that were actually observed. Items in _[brackets]_ are not known yet and must be completed by the team (names, review, Fault B). Nothing here was invented.

## Team and roles

| Member | GitHub username | Lab 1 role | Lab 2 role |
|---|---|---|---|
| _Margaux VARET_ | _margauxvaret_ | _[driver / reviewer / PR author]_ | _[rotated role]_ |
| _Gabrielle DOLBEAU_ | _gabrielleDol_ | _[ ]_ | _[ ]_ |
| _Pierre GUILLOIS_ | _PierreGuillois12_ | _[ ]_ | _[ ]_ |
| _Victor BOUGRO_ | _victorbgr_ | _[ ]_ | _[ ]_ |

_[Delete unused rows if the team has fewer than 4 members. Roles must rotate between labs.]_

## Repository and pull requests

- Team repository: `mlops-thu1-BDGV-bike-demand` (private, owner `margauxvaret`).
- Lab 1: branch `lab01/fix-team-slug`, merged through pull request #1 into `main`.
- Lab 2: branch `lab02/baseline`. _[PR number, reviewer, and merge status once opened and reviewed.]_

## Setup, preflight and quality checks (commands and actual results)

Platform: Windows (setup is only checked on macOS by the course; this run is a Windows data point, not a guarantee for other systems).

| Command | Result |
|---|---|
| `uv run --locked pytest -q -m infra` | passed |
| `uv run --locked pytest -q -m lab1` (before fix) | 1 failed, 2 passed: `test_joins_whitespace_with_hyphens` got `'team---blue\tnorth'`, expected `'team-blue-north'` |
| `uv run --locked pytest -q -m lab1` (after fix) | 3 passed |
| `uv run --locked pytest -q -m lab1` (after own test) | 4 passed |
| `uv run --locked ruff check .` | All checks passed (after `--fix` of one import-order error in `train.py`) |
| `uv run --locked ruff format --check .` | 10 files already formatted (after `ruff format .`) |
| `uv run --locked pytest -q` | 48 passed, 1 warning (SQLAlchemy `noload` deprecation inside MLflow, not from our code) |

_[preflight output and the revision it was run on.]_

## Data identity, validator checks and added test

- Command: `uv run --locked python -m bike_demand.validate --data data/raw/hour.csv`
- Result: `Validated 17379 rows; input bytes unchanged.`
- Data SHA-256: `e03de4ee4ef4dc376ac6e04bf829673c6269e8eba5c60fa121640fa2f829504f`
- `check_domains` checks: integer domains (season 1–4, yr 0–1, mnth 1–12, hr 0–23, holiday 0–1, weekday 0–6, workingday 0–1, weathersit 1–4), finite normalised values in [0, 1] for temp, atemp, hum, windspeed, nonnegative integer counts, dates within 2011-01-01 to 2012-12-31. Missing hours are valid.
- Lab 1 test of our own: _[test name and what it checks]_.

## Partition counts, boundaries and held test rows

| Partition | Rows | Date range |
|---|---|---|
| train | 8645 | 2011-01-01 to 2011-12-31 |
| validation | 4358 | 2012-01-01 to 2012-06-30 |
| test (held) | 4376 | 2012-07-01 to 2012-12-31 |

Rows are sorted by `(dteday, hr, instant)`; the three partitions are nonempty, disjoint and complete. No test metric was computed.

## Comparator and RF: run IDs, validation MAEs, metadata/readback

Command: `uv run --locked python -m bike_demand.train --config configs/baseline.yaml`

| Item | Value |
|---|---|
| Training commit recorded | `73270643359c15c469deadc2317f7bc3baeac464` |
| `working_tree_dirty` | `true` (training was run before the `reports/` files were committed) |
| Model version | `baseline-88de10aaec00` |
| Naive (train mean) run ID | `d7ddd6b04d214718be4b6e460e1c88b5` |
| RF run ID | `bbd0efb70ea544f1820f69eb5ed61769` |
| Train mean | 143.79 rentals/hour |
| Validation MAE, train-mean comparator | 154.23 rentals/hour |
| Validation MAE, random forest | 86.85 rentals/hour |
| Model SHA-256 | `fd98ceafc57a5babce61ce703cbf9cb8d1f83c6820b0b34fe30ad1a0fc49c304` |

Readback: reloaded MAE equals measured MAE (delta 0.0), metadata matches, logged model bytes match the saved model, max prediction delta 0.0.

Interpretation: MAE is in rentals per hour. On the same validation rows, the RF error is lower than the comparator's. This is one split and one run, not a claim about future demand.

## Optional stretch, after the core: unchanged-config repeat (new run IDs, history, differences)

Not attempted (core not yet reviewed).

## Fault diagnosis and your own Fault B

Fault A (`missing-temp.csv`, supplied): _[what the validator reported]_.

Fault B:

- **Choice:** _not attempted yet_
- **Reason:** _not attempted yet_
- **Result:** _not attempted yet_

## Review observation and author's response

_[Reviewer's observation on the pull request and the author's response. Leave blank until a real review happens.]_

## Contribution and assistance/recovery acknowledgement

- Contributions per member: _[to fill by each member]_.
- Assistance: an AI assistant (Claude) was used for guidance and code suggestions on `validate.py`, `split.py` and `train.py`, and for wording the Lab 1 screenshot comments. The team ran, checked and committed the code itself. _[Add any instructor recovery function used; none recorded here.]_

## Blockers and next action

- Lab 2 commits were first made on local `main` instead of `lab02/baseline`; they were moved to the task branch before the PR. _[confirm once done]_
- Next: design and test Fault B, open the Lab 2 PR, get a review from another member, then re-run training on a clean tree and update the commit/run IDs above.

## Lab 3 Results — clean container rerun

The rerun used a fresh clone at integration commit `968306c8c7558d303dbffb94258071af27b579ed`.
The committed `uv.lock` SHA-256 is `8d84120008104540172043b5dc103a83a3827f42dc8f0f369f0367e32e8c7462`.
The image was built without cache from that commit and ran with `--network none`.
Its image ID is `sha256:cd4f8f623ed434beb976be57eb36a2086f6f0f863cb67c84d66b6b65e0e0f0b0`
(`linux/amd64`). The image label `org.opencontainers.image.revision` matches the
commit above. The training metadata reports `training_commit: unavailable` because
the image does not contain `.git`; the image label records the source revision.

| Validation MAE (rentals/hour) | Lab 2 | Lab 3 | Écart (Lab 3 − Lab 2) | Explication |
|---|---:|---:|---:|---|
| Train-mean comparator | 154.231793 | 154.231793 | 0.000000 | Same train mean, unchanged data (`e03de4ee…`), features and validation rows. |
| Random forest | 86.846857 | 86.846857 | 0.000000 | Same locked baseline configuration, seed, input snapshot and validation split; the observed validation MAE is unchanged. |

The run held out July–December 2012 and did not calculate test-set metrics. The
validation readback matched exactly (`reload_mae_delta: 0.0`). The rerun model
SHA-256 is `d24c050e3631d5b4c2feb8cb571bef6382d8c975c42a5c11edd28de78a0b8c07`;
the model binary is not committed.

`uv run --locked pytest -q` in a second network-disabled container: **48 passed**
with one SQLAlchemy deprecation warning emitted through MLflow. Run IDs, metrics,
model hash, and raw evidence are in `reports/lab3/logs/metrics.json`,
`reports/lab3/logs/run.log`, `reports/lab3/logs/tests.log`,
`reports/lab3/logs/build.log`, `reports/lab3/logs/image.txt`, and
`reports/lab3/logs/revision.txt`.

## Screenshots

![Lab 1: failing test before the fix (`pytest -m lab1`)](images/lab01-screenshot-1.png)
Caption: failing `test_joins_whitespace_with_hyphens`, revision _[commit]_.

![Lab 1: 3 tests passing after the fix](images/lab01-screenshot-2.png)
Caption: `pytest -m lab1` after the repair, revision _[commit]_.

![Lab 1: 4 tests passing after our own test](images/lab01-screenshot-3.png)
Caption: `pytest -m lab1` with the added test, revision _[commit]_.

![Lab 1: branch pushed, Compare & pull request banner](images/lab01-screenshot-4.png)
Caption: push of `lab01/fix-team-slug`, before PR #1.

_[Lab 2: add screenshots of the validator output, MLflow runs (RF `bbd0efb7…`, naive `d7ddd6b0…`) and the PR checks, each with its commit or run ID.]_
