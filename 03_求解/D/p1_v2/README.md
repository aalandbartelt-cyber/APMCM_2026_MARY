# P1 v2.1 reproducible experiment

**P1 training is closed (2026-11-27).** The ledger remains at 914 tree-fit
attempts. All 86 remaining attempts are reserved for the frozen P23 refit;
no new model routes, losses, searches, Ridge fits or scalar calibration fits
are authorized by the hardening task. The historical training commands below
document the completed run; do not execute them again.

The original pre-training plan is archived byte-for-byte as
`codex/P1_PLANv2.1_FROZEN.md`. Section 6 of `codex/P1_PLANv2.md` freezes the
postprocessing definitions and the future P23 construction. Original training
code, freeze records, fitted models and P1 prediction tables remain unchanged.

## Postprocessing-only hardening

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3.10 03_求解/D/p1_v2/test_hardening.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3.10 03_求解/D/p1_v2/report.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3.10 03_求解/D/p1_v2/decision_stability.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3.10 03_求解/D/p1_v2/hardening_report.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3.10 03_求解/D/p1_v2/hardening_audit.py
```

These commands require the original frozen artifacts and the pre-analysis
`hardening/protocol.json` / `protected_before.json`. They must not recreate or
relax missing freeze records. `report.py` now reuses the already-fitted
calibration diagnostic CSV without refitting. The paired bootstrap resamples
AB clusters separately inside each outer fold and averages the five fold
Top-20 EFs. An undefined fold invalidates the entire replicate. Original
pooled intervals are retained in a separate diagnostic file and columns.

The main table includes eight candidates, three existing baselines and two
nested selection procedures. `results/P1_main_per_fold.csv` records N/M/h
and selected identities for all 65 row/fold combinations. Decision diagnostics
for pools 07/08/11/12 and the fixed split-half comparison are in `hardening/`.
They use only twenty existing prediction tables and contain no truth-based
accuracy comparison. The frozen P23 choice is `bagged_mean_20`; P23 training
has **not** been executed. See `codex/P1_HARDENING_REPORT.md` for the costs,
limitations, old/new endpoint distinction and audit receipt.

This implementation follows `codex/P1_PLANv2.md`. It trains on official 02 only,
selects from at most three frozen candidates on the historically used 03
development set, and predicts the composition-only 04 holdout. The screening
event is `V<=2`, never `V=0`. No Kaiwu import, QUBO solve or hardware request is
made by these scripts.

Use `/usr/bin/python3.10` and the existing environment. The local source paths
and interpreter are intentionally pinned to the current WSL workspace. Do not
upgrade or replace the installed packages. Run from the repository root.

## Sources and isolated LightGBM

`prepare_sources.py` downloads only the eight Magpie elemental tables pinned to
matminer v0.9.3 and the LightGBM 3.3.5 source distribution. Source URLs and SHA-256
digests are preserved. The only C++ modification changes the maximum query
length from 10,000 to 20,000. The Python wrapper is copied into an isolated
artifact directory. Existing installations are unchanged.

```bash
/usr/bin/python3.10 03_求解/D/p1_v2/prepare_sources.py
cmake -S artifacts/p1_v21/sources/lightgbm-3.3.5/compile -B artifacts/p1_v21/lgbm_build -DUSE_GPU=OFF -DUSE_CUDA=OFF -DBUILD_CLI=OFF
cmake --build artifacts/p1_v21/lgbm_build -j 4
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 /usr/bin/python3.10 03_求解/D/p1_v2/preflight.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 /usr/bin/python3.10 03_求解/D/p1_v2/test_contracts.py
```

Preflight checks official hashes, AB separation, composition-only feature
construction, zero/missing handling, invalid geometry and batch/order
invariance. Two synthetic library parity fits are counted. Existing preflight
records are verified without changing their freeze timestamp.

## Historical registered execution and recovery (closed)

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 /usr/bin/python3.10 03_求解/D/p1_v2/run_registered.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 /usr/bin/python3.10 03_求解/D/p1_v2/report.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 /usr/bin/python3.10 03_求解/D/p1_v2/interface.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 /usr/bin/python3.10 03_求解/D/p1_v2/audit.py
```

The stage names are `main`, `stress`, `final`, `diagnostics`, and `export`.
Individual stages are available through `experiment.py`; the end-to-end wrapper
also freezes the actual tree-file hashes before formal 04 export.
Domain checkpoints and content-addressed model files resume interrupted work
without repeating completed fits. Every tree-fit attempt is reserved in
`fit_ledger.jsonl` before training; failures consume the 1,000-attempt hard limit.
The registered upper bound is 992, plus at most eight repair/verification
attempts. Scalar calibrators, Ridge baselines and diagnostic statistics are
separate from tree-fit accounting.

Core code, sources, feature matrices and splits are frozen before real training.
Changing frozen core code or inputs makes the runner refuse to continue. Do not
delete manifests or ledgers to bypass that check or to reset the budget.

## Files and definitions

- `experiment_freeze.json`, `splits.json`: initial policy, code and split lineage.
- `models/`, `calibration/`, `domains/`: fitted trees, training-domain calibration
  records and complete fold-level predictions. Calibration fitting diagnostics
  are explicitly apparent; independent reliability uses held-out predictions.
- `03_candidate_freeze.json`, `03_results.json`, `final_selection.json`: single
  frozen development comparison and locked final choices.
- `weights_freeze_pre04.json`, `prediction_freeze.json`: final prediction lineage.
- `results/P1_final_experiment_table.csv`: original-scale OOF RMSE and per-fold
  mean `EF_{V<=2}@20`. Five fold Top-20 lists use a total budget of 100.
- `results/pooled_oof_diagnostic.csv`: a different, single pooled Top-20 budget.
- `results/paired_AB_bootstrap_5000.csv`: conditional percentile intervals on
  fixed OOF predictions, with per-fold Top-20 followed by macro averaging.
  These do not include all model-selection uncertainty.
- `results/paired_AB_bootstrap_pooled_diagnostic_legacy.csv`: unchanged original
  pooled intervals. `paired_AB_bootstrap_endpoint_comparison.csv` keeps their
  values in diagnostic columns beside the corrected primary intervals.
- `bootstrap/`: twenty genuinely resampled AB datasets, with all seven X rows
  and multiplicities retained. The final numeric gate calibrator is fixed.
- `predictions/04_P1_train02_predictions.csv`: final P1 numerical and screening
  outputs, plus conditional bootstrap dispersion.

Forward feature controls and reverse ablations do not trigger additional
selection. The three feature blocks overlap through declared dependencies;
ablation effects are conditional, not exclusive causal contributions.

The geometry proxy uses formal oxidation-state assignments and mixed-anion
mean radii. Strict CN12/CN6 coverage is limited. Nitride CN4 and A-site fallback
radii are separately flagged. Zunger source-native radii are electronic
descriptors and never inserted into Shannon geometric formulas.

## Label-free inference

`predict.py` reads only `id,A,B,X`, checks the registered composition universe,
loads frozen trees/calibrators, and performs no fitting:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 /usr/bin/python3.10 03_求解/D/p1_v2/predict.py --input INPUT.csv --output OUTPUT.csv
```

The output Vhat is always in the original V scale. A regression screening score
is `-Vhat`; a classifier score is an estimated `P(V<=2)`. These meanings are
recorded separately. Model dispersion is not a guaranteed prediction interval.

All P2/P3 preparation tables in this run are explicitly scoped `P1_train02`.
`interface/*_vhat_and_membership.npz` stores dense Vhat arrays with boolean
membership masks. Disallowed entries are NaN, never zero. These are input tables,
not QUBO matrices. No optimization or solver is executed.
The future 02+03 refit and the 3x104-bit / 208-bit / HOBO comparisons are deferred
to those stages. Missing blind-pool combinations must not be assigned zero cost.

No result in this experiment establishes holdout `V=0` recall, real physical
optimality, synthesizability or a restored historical blind evaluation.
