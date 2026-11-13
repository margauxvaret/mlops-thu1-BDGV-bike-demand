# Lab 6: preuves brutes

Les liens de runs GitHub Actions expirent : les logs bruts sont copiés ici, en texte.

| Fichier | Run | Commit | PR | Résultat | Ce que ça prouve |
|---|---|---|---|---|---|
| `01-pr16-rouge.txt` / `01-pr16-rouge-failed.txt` | [43183335657](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/actions/runs/43183335657) | `12b519d` | [#16](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/pull/16) | ❌ failure (19 s) | l'étape `Lint (ruff)` attrape `I001` dans `scripts/check_deployment.py` |
| `02-pr16-vert.txt` | [43184757992](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/actions/runs/43184757992) | `973ba53` | [#16](https://github.com/margauxvaret/mlops-thu1-BDGV-bike-demand/pull/16) | ✅ success (36 s) | la correction passe toutes les étapes : lock, lint, format, preflight, tests |
| `03-deploy.txt` | à compléter (P3) | | | | déploiement d'une nouvelle révision Cloud Run |
| `04-identite.txt` | à compléter (P3) | | | | `git_sha`, `model_version`, `model_sha256` de l'URL en ligne |

## Rouge vers vert (PR #16)

1. **Changement** : le commit `12b519d` ajoute à la CI les étapes `ruff check` et `ruff format --check`.
2. **Check qui a attrapé** : `Lint (ruff)`, run 43183335657, ligne de cause dans le log :
   `I001 [*] Import block is un-sorted or un-formatted` puis `16 | | import urllib.error`, puis `Found 1 error.` et `exit code 1`.
3. **Cause** : l'ordre des imports et le formatage de `scripts/check_deployment.py` (code du Lab 5) n'avaient jamais été vérifiés. Le défaut existait déjà, et le nouveau check l'a révélé.
4. **Correction** : le commit `973ba53` réordonne les imports et reformate le fichier (14 insertions, 10 suppressions).
5. **Vert** : run 43184757992, sur la même PR, avec un nouveau commit. Ce n'est pas une relance.
