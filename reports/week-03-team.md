# Week 3 team report

## Lab 6: CI and deployment

### What CI proves, and what it does not

CI proves that each PR into `integration` or `main` installs from `uv.lock` on a clean
runner and passes lint, format, preflight and tests that each target a named defect.
It proves nothing about our local MLflow runs or the model files on our laptops:
CI never sees `tracking/` or `artifacts/`.
It does not prove the model is good on new data: the readback test uses a small test
model (`test-0.0.1`) and only proves the API returns exactly the prediction recorded
for the saved model (tolerance 0, measured over 5 runs).

### Test map

| Defect | Test | How we broke it locally | Red output |
|---|---|---|---|
| `hr=24` accepted (valid range is 0–23) | `test_out_of_bounds[hr-24]` | bound widened to accept 24 | `assert 200 == 422`, 1 failed (`personne2/hr-24-accepted.log`) |
| NaN/inf input crashes the API (500) instead of a clean 422 | `test_non_finite` | validation handler bound to `RuntimeError` instead of `RequestValidationError` | `assert 500 == 422` (`personne2/nonfinite-500.log`) |
| `/health` does not report the exact identity of the loaded model | `test_health_reports_exact_loaded_model_identity` | identity field altered in `/health` | dict mismatch on `git_sha` (`...t-commit-123` vs `...cd638dead411`), 1 failed (`personne2/health-missing-field.log`) |
| model file with a wrong SHA-256 is still served | `test_wrong_model_sha_is_rejected` | SHA check disabled | `assert 200 == 503`, 1 failed (`personne2/wrong-sha-accepted.log`) |
| prediction drifts from the recorded saved-model prediction | `test_prediction_matches_saved_model_readback` | recorded value shifted by 1 | `assert 43.0 == 42.0 ± 0.0`, 1 failed (`personne2/prediction-shift.log`); tolerance `abs=0` measured: 5 runs, saved=42.0, api=42.0, abs_delta=0.0 every run (`personne2/measurement.log`); test fixture model `test-0.0.1`, not the trained RF |

Each test was broken on purpose locally, the red output was saved, then the code was
restored. Raw logs: `reports/evidence/lab6/personne2/` (P2).

### Red to green (PR #16)

| Step | Commit | Run | Result |
|---|---|---|---|
| Change that caused it: ruff steps added | `12b519d` | [43183335657](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/actions/runs/43183335657) | ❌ `Lint (ruff)` after 19 s: `I001 Import block is un-sorted` in `scripts/check_deployment.py` |
| Fix: imports sorted, file reformatted | `973ba53` | [43184757992](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/actions/runs/43184757992) | ✅ all steps green |

The defect already existed in the Lab 5 code; the new ruff check caught it, and a new
commit on the same PR fixed it (no re-run). Raw logs: `reports/evidence/lab6/`
(see `INDEX.md`).

### Deployment trace

### Deployment trace

- Commit deployed: `8144cad` (merge of PR #20 on `main`)
- Deploy run: [43433382970](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/actions/runs/43433382970), green in 2 min 41 s; full log `reports/evidence/lab6/03-deploy-run.txt`
- Image (deployed by digest): `bdgv-api@sha256:ec187fb59e1bae856d3f3a4b9b99bbc859be103144be044e26832b609db0def6`
- Cloud Run revision: `mlops-thu1-bdgv-bike-demand-00018-jm6`, 100 % of traffic; previous revision `00017-rw6` kept as rollback target
- Identity check on the live URL: 7/7 PASS, including `git_sha` = `8144cad…`, `model_version` = `baseline-3231526734d2`, `model_sha256` = `fd98ceaf…c304`, valid `/predict` = 200 (68.88), `hr=24` = 422
- Raw records: `reports/evidence/lab6/deploy/deploy-evidence-8144cad…/deploy-record.txt` and `live-check.txt`
- Undo: on any failure after the deploy, the job runs `gcloud run services update-traffic --to-revisions <previous>=100`. It was not exercised: every deploy so far passed the live check, so no `rollback.txt` exists.

### Process gaps (honest)

- PRs #18 and #20 were merged directly into `main` instead of `integration`; `integration` was then synced from `main`. Future PRs target `integration`.
- `main` was red after PR #14 (run 42598577985, ruff failure) until PR #16 fixed it.