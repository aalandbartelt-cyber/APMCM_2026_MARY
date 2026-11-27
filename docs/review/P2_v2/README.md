# P2 v2 execution and review

The approved plan is `codex/P2_PLAN.md`. The result report and complete experiment table are `codex/P2_RESULTS_v2.md` and `codex/P2_FINAL_RESULTS_v2.csv`.

Execution completed the 65-fit deterministic P23 refit and 32,000 registered executable SA restarts. The four-candidate hardware decision is **NO_ELIGIBLE_CONFIGURATION**. No CIM task was submitted. Missing M8 generation control is UNKNOWN, not a negative result for the mutate method.

The selection anchor is **5528cae132206a30b6f921905da6f30704ad15c5**. Keep that exact commit and its receipt; do not amend it or replace the receipt. All SA ran after this anchor. Hardware remains gated off.

Read-only checks (no fitting or remote submission):

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B 03_求解/D/p2_v2/tests.py
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3.10 -B docs/review/P2_v2/test_anchor.py
```

The training, representation and SA entrypoints have already run; do not restart them to change outcomes. `produce_report.py` independently checks every SA return and every repair and creates derived tables. `auxiliary_bootstrap.py` provides descriptive task-block summaries only. Existing output files are preserved; an intentional fresh report reproduction requires a new output location or preserving the previous derived directory first. Neither script fits models or calls hardware.

Evidence locations:

- `artifacts/p23_v2/manifest.json`: model/table hashes and 65 fit attempts; the live stdout-log suffix is reconciled separately.
- `artifacts/p2_v2/training_validation.json`: all model lineages, bootstrap multiplicities, independent prediction reconstruction and pool equality.
- `artifacts/p2_v2/representations/`: submitted-format integer matrices, candidate energies, exact witnesses and certificate statuses.
- `artifacts/p2_v2/sa/`: all 320 blocks with raw spins, times, seeds, original and repaired decisions.
- `artifacts/p2_v2/results/verification.json`: independent full-return and protection audit.
- `artifacts/p2_v2/results/cim_current_status.json`: 20 NOT_STARTED formal slots, no fabricated hardware metrics; not the future T_snap.
- `figures/P2/figure_inventory.csv`: complete A–G mapping and user-approved placement rules; figures not yet rendered.

`PROCESSING_NOTES.md` records two postprocessing issues and the preserved intermediate files. No retraining, solver rerun, matrix reselection or parameter change was used to correct them.

The official manuscript, existing figures, P1 outputs and P3 solver remain unchanged. No cloud balance or queue observation is claimed. The current contest's shared D-drive folder contains the scout status and result documents; the available message bus belongs to the previous contest and was deliberately not used for delivery.
