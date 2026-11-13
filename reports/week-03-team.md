# Week 3 team report

## Lab 6: CI and deployment

### What CI proves, and what it does not

CI proves that each PR into `integration` or `main` installs from `uv.lock` on a clean
runner and passes lint, format, preflight and tests that each target a named defect.
It proves nothing about our local MLflow runs or the model files on our laptops:
CI never sees `tracking/` or `artifacts/`.
It does not prove the model is good on new data, only that it reproduces a recorded
result within a measured tolerance.

### Test map

| Defect | Test | How we broke it locally | Red output |
|---|---|---|---|
| TODO (P2) | | | |
| TODO (P2) | | | |
| TODO (P2) | | | |

### Red to green (PR #16)

| Step | Commit | Run | Result |
|---|---|---|---|
| Change that caused it: ruff steps added | `12b519d` | [43183335657](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/actions/runs/43183335657) | ❌ `Lint (ruff)`: `I001 Import block is un-sorted` in `scripts/check_deployment.py` |
| Fix: imports sorted, file reformatted | `973ba53` | [43184757992](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/actions/runs/43184757992) | ✅ all steps green |

Raw logs: `reports/evidence/lab6/` (see `INDEX.md`).

### Deployment trace

- Commit deployed: TODO (P3)
- Deploy run: TODO (link + `reports/evidence/lab6/03-deploy.txt`)
- Cloud Run revision: TODO
- Identity check (`git_sha`, `model_version`, `model_sha256`): TODO (`04-identite.txt`)
- Undo: TODO (command that sends traffic back to the previous revision)