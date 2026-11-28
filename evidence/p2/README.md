# P2 · offline replay

From the checkout root, run **python3 -I -B evidence/p2/verify.py**. Python 3.8+ with its standard library suffices. The verifier reads only this directory and exits zero after two PASS lines. The data represent an optimization service returning ten curated vectors per task. The five pilot tasks have their own labels. Formal inference uses twenty service tasks.

| File | Reproduction input |
|---|---|
| matrix.npz, blocks.json | Signed-integer symmetric coupling matrix, original floating values, integer costs and 40 disjoint chains with one common reference |
| candidates.csv | Row-major blind-pool identity, original surrogate value and integer cost for each of the 529 allowed candidates |
| returns/P01.pkl … returns/F20.pkl | Byte-exact terminal payloads. P01 comes from the initial completion archive. Each file contains a compressed primitive byte object with ten 490-spin vectors |
| tasks.csv | Unique server result ID, stage, raw payload digest and sealed task endpoints |
| matrix_certificate.json, return_certificate.json | Independent design certificate and historical per-task checks for comparison |
| timeline.csv | Original project commit IDs and commit times for selection, pilot validation, formal freeze and final results |
| sha256.json | Input and verifier digests. The Git revision or the separately delivered bundle digest anchors this manifest |

With reference spin fixed, the independent dynamic program tracks the last spin and whether a forbidden transition has appeared. It checks all block energies, reconstructs the global minimum and the gap to illegality, and explicitly realizes the first possible wrong business decision. The verifier also recomputes every returned energy directly from matrix edges and checks each aggregate decision against the original values. Coordinates in the matrix and in the dictionary start at zero.

Expected values are integer ground energy −58722, first wrong strictly legal output at excess 196 and first illegal output at excess 340. Every formal task achieves original regret zero even under minimum-energy selection. The raw files authenticate correspondence to the sealed local record. They contain no provider signature attesting to optical dynamics or independent sampling. A reviewer can verify the arithmetic offline without an account.
