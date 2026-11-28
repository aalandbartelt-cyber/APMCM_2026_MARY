# P3 offline seal

Run the independent checker from a full repository checkout with Python 3.10+ and NumPy. Supply the 40-character commit recorded in the handoff or delivery message.

```bash
/usr/bin/python3.10 -B evidence/p3/verify.py --anchor "$P3_ANCHOR"
/usr/bin/python3.10 -B -m unittest discover -s evidence/p3 -p 'test_*.py'
```

Use `--sources` to hash the locally held frozen inputs, including the original competition tables. In a D-drive mirror use `--anchor-repo /home/mary/apmcm2026` to read the Git history of the source repository. File verification and mathematical replay still read the mirror's own bytes. The D sibling file p3-final-anchor.bundle is incremental from the P3-2 baseline commit d770fa06011db1d72ec7791aeb58cbfa9a1db565; a repository containing that baseline can import and check the seal independently. All of these operations are offline.

## Evidence and interpretation

- `O3.npz`, `NO2.npz`, `FO2.npz` are the three formal matrices. `tie08.npz` is the 541-candidate first batch of the full NO2 slice, reserved for the tie regression. Each file contains the integer matrix J, its final reference index, a complete index mapping, group offsets, row-major site dictionary, official IDs, q, original values, D, finite witness indices and the corresponding signed vectors in original spin order. A stored D of -1 denotes an unreachable aggregate output.
- `candidates.csv` contains the four dictionaries with D in integer-energy units (INF for unreachable). `envelopes.csv` contains exact staircase breakpoints. At a query d, take the last row for the batch with residual at most d. `certificates.json` preserves the independent per-batch audits, including G1, the 0.1 engineering check, exact preservation and the attainable worst regret.
- `member_scenarios.csv` records nominal and member-optimal IDs, member seed, winning family, nominal rank and regret under the same member. The ALL rows use the entire named pool. IDs and continuous scores come from frozen outputs, without fitting. `source_members.json` records the ordered member descriptors and their digests.
- `slots.csv` is the immutable allocation. `receipt.json` binds the rules, figures, source inventory and forecast provenance to the first Git commit containing the receipt. Original per-restart vectors behind the historical SA percentiles were not located. These percentiles are registered as a historical summary; the seal makes no claim of raw SA replay.
- `protocol.py` computes primary and secondary outcomes, round denominators, and the offline creation gate. A later executor must preserve raw response order and supply the full externally recorded anchor to `creation_gate` **before each creation**. Use a separate append-only execution ledger for server IDs, ordered raw returns, timestamps, billing snapshots and integrity outcomes. Never write observations back into the registered slot table or receipt.
- `build_inputs.py NEW_EMPTY_DIRECTORY` reconstructs the seal inputs from the frozen source tables. The independent checker never imports the builder. It recomputes minimum attainable residuals from the stored integer matrix and decodes every supplied finite witness.

The stage represented by this package ends before creation of any P3 service task.
