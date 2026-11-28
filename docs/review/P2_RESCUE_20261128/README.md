# P2 bounded rescue: closed after two counterexamples

The user approved one post hoc registered penalty revision, restricted to blind-pool raw-N8 and rc-N8. Both failed. No new fit, SA restart, hardware submission or broader parameter search followed.

- Declaration and input snapshot were committed before matrix generation: `dfb2c89`.
- New rejection receipt: `codex/p2_rescue1/selection_receipt.json`, SHA256 `937b799a97ad3947af1577dae7fc7f995b1089253ffc9f7561ca76f92e498ea7`.
- Original rejection remains anchored at `5528cae132206a30b6f921905da6f30704ad15c5`; its files are unchanged.
- Results: `codex/P2_RESCUE_RESULTS_20261128.md` and `codex/P2_RESCUE_COMPARISON_20261128.csv`.
- Matrices, all one-hot energies and exact witnesses: `artifacts/p2_rescue1/representations/`.
- Read-only channel check: `ACCOUNT_CHANNEL_CHECK.md`. Query reachability does not establish quota, billing, queue or returned-sample contracts.

The user subsequently instructed that manuscript writing requires separate explicit permission. All manuscript changes made during this turn were withdrawn. The original source and PDF match all eight files in the before snapshot; new P2 manuscript files and preview images were removed. `MANUSCRIPT_ROLLBACK.json` records hashes, without retaining an active unauthorized draft. Compiler auxiliary files were rebuilt from restored sources, then the original PDF bytes were restored. No further manuscript work is authorized by this rescue.

Read-only verification:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 docs/review/P2_RESCUE_20261128/verify.py
```

This checks 4,701 protected files, the unchanged fit ledger, 32 exhaustive synthetic tests, 5,408 one-hot energies and both rescue witnesses. The audit entrypoint has already run; do not rerun it or delete its receipt. A different representation requires a separately approved amendment.
