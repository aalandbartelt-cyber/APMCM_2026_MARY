"""Read-only arithmetic audit of sealed P2 inputs/returns; no solver or SDK.

Prints JSON to stdout. Does not import any project modeling/decoding code.
Run from any directory with /usr/bin/python3; redirect to a NEW review file.
"""
from pathlib import Path
import hashlib
import io
import json
import pickle
import zlib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "artifacts/p2_cim_go_20261128/input"
BASE = ROOT / "artifacts/p2_cim_go_20261128/service_audit"
sources = {}


def read(path):
    raw = path.read_bytes()
    sources[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    return raw


class PrimitiveOnly(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError("Global objects are prohibited")


def returns(path):
    p = PrimitiveOnly(io.BytesIO(read(path))).load()
    assert p["format"] == "ndarray-zlib-v1" and tuple(p["shape"]) == (10, 490)
    dtype = np.dtype(p["dtype"])
    assert dtype.kind in "fiu"
    size = 10 * 490 * dtype.itemsize
    dec = zlib.decompressobj()
    data = dec.decompress(p["data"], size + 1)
    assert len(data) == size and dec.eof and not dec.unused_data and not dec.unconsumed_tail
    a = np.frombuffer(data, dtype=dtype).reshape(10, 490)
    assert np.isin(a, [-1, 1]).all()
    return a.astype(np.int64)


z = np.load(io.BytesIO(read(INPUT / "matrix.npz")), allow_pickle=False)
K, q, values = (z[k] for k in ("J", "q", "values"))
blocks = json.loads(read(INPUT / "blocks.json"))
assert np.array_equal(K, K.T) and K.dtype.kind in "iu" and not np.diag(K).any()
assert np.max(np.abs(K)) <= 127
source = np.load(io.BytesIO(read(ROOT / "artifacts/p23_v2/pool_11.npz")))
assert np.array_equal(values, source["vhat"][:, :, 0][source["allowed"][:, :, 0]])
r = values - values.min()
expected_q = np.rint(63 * np.where(r <= 2, .375 * r, .75 + .25 * (r - 2)/(r.max() - 2)))
assert np.array_equal(q, expected_q)
star = int(values.argmin())
assert np.flatnonzero(q == q.min()).tolist() == [star]
critical = next(i for i, b in enumerate(blocks) if star in b["mapping"])
coverage, spin_coverage, legal_minima, illegal_minima, constants = [], [], [], [], []
edge_mask = np.zeros(K.shape, dtype=bool)
local_min_q = np.array([q[b["mapping"]].min() for b in blocks])
for b in blocks:
    ids = list(range(b["start"], b["stop"]))
    spin_coverage.extend(ids)
    coverage.extend(b["mapping"])
    assert b["reference"] == 489 and len(b["mapping"]) == len(ids) + 1
    for a, c in zip(ids[:-1], ids[1:]):
        edge_mask[a, c] = edge_mask[c, a] = True
    edge_mask[ids, 489] = edge_mask[489, ids] = True
    sub = K[np.ix_(ids + [489], ids + [489])]
    # Exhaust all at most 2^13 states of each fixed-reference chain.
    n = len(ids)
    bits = ((np.arange(1 << n)[:, None] >> np.arange(n)) & 1)
    spins = np.column_stack((2 * bits - 1, np.ones(1 << n, dtype=np.int64)))
    energies = -np.einsum("ni,ij,nj->n", spins, sub, spins)
    bad = np.any(np.diff(bits, axis=1) > 0, axis=1)
    legal_minima.append(int(energies[~bad].min()))
    illegal_minima.append(int(energies[bad].min()))
    legal_costs = q[np.array(b["mapping"])[bits[~bad].sum(1)]]
    offsets = np.unique(energies[~bad] - 4 * legal_costs)
    assert len(offsets) == 1
    constants.append(int(offsets[0]))
assert spin_coverage == list(range(489)) and coverage == list(range(529))
assert not K[~edge_mask].any()
ground = sum(legal_minima)
illegal_gap = min(b - a for a, b in zip(legal_minima, illegal_minima))
assert illegal_gap > 0
critical_other = [c for c in blocks[critical]["mapping"] if c != star]
wrong_gap = 4 * int(q[critical_other].min() - q[star])
failure_gap = min(illegal_gap, wrong_gap)


def inspect(s):
    chosen = []
    for b in blocks:
        d = (s[b["start"]:b["stop"]] * s[489] + 1) // 2
        assert (np.diff(d) <= 0).all()
        chosen.append(b["mapping"][int(d.sum())])
    excess = q[chosen] - local_min_q
    e = int(-s @ K @ s)
    ii, jj = np.triu_indices(len(K), 1)
    assert e == int(-2 * np.sum(s[ii] * s[jj] * K[ii, jj]))
    assert e - ground == 4 * int(excess.sum())
    c = min(chosen, key=lambda a: (q[a], a))
    return {"energy": e, "gap": e - ground,
            "locally_optimal_chains": int((excess == 0).sum()),
            "critical_chain_candidate": int(chosen[critical]),
            "decoded_candidate": int(c), "regret": float(r[c])}


# A mathematical witness, not an experimental return: 39 locally optimal
# chains are insufficient if the only nonoptimal chain contains the optimum.
witness = np.ones(490, dtype=np.int64)
for i, b in enumerate(blocks):
    candidates = critical_other if i == critical else b["mapping"]
    c = min(candidates, key=lambda a: (q[a], a))
    t = b["mapping"].index(c)
    witness[b["start"]:b["stop"]] = -1
    witness[b["start"]:b["start"]+t] = 1
witness_info = inspect(witness)
assert witness_info["gap"] == wrong_gap and witness_info["regret"] > 0
assert witness_info["locally_optimal_chains"] == 39

task_rows = []
all_rows = []
for number in range(1, 21):
    slot = f"F{number:02}"
    raw = returns(BASE / slot / "result.pkl")
    saved = json.loads(read(BASE / slot / "result.json"))
    assert saved["status"] == "VALID_COMPLETED"
    assert sources[str((BASE / slot / "result.pkl").relative_to(ROOT))] == saved["source_sha256"]
    rows = [inspect(s) for s in raw]
    best_i = min(range(10), key=lambda i: (rows[i]["energy"], i))
    best = rows[best_i]
    assert best["energy"] == saved["min_integer_energy"]
    assert best["regret"] == saved["energy_selected_regret_strict"] == 0
    assert all(x["gap"] < failure_gap and x["regret"] == 0 for x in rows)
    task_rows.append({"slot": slot, "energy_selected_index": best_i, **best,
                      "maximum_return_gap": max(x["gap"] for x in rows),
                      "local_optimal_chain_count_min": min(x["locally_optimal_chains"] for x in rows),
                      "local_optimal_chain_count_max": max(x["locally_optimal_chains"] for x in rows)})
    all_rows.extend(rows)

prior_controls = {}
for name in ("blind_permutation_real", "blind_permutation_zero", "blind_linear"):
    path = ROOT / "artifacts/p2_research_20261128/validation_H07_H08" / name / "raw.jsonl"
    rows = [json.loads(line) for line in read(path).splitlines()]
    prior_controls[name] = {
        "attempts": len(rows),
        "strict_feasible": sum(bool(x.get("all_chains_feasible")) for x in rows),
        "strict_hits": sum(bool(x.get("all_chains_feasible")) and x.get("regret") == 0 for x in rows),
        "partial_hits": sum(x.get("regret") == 0 for x in rows)}

pools = {}
for name in ("07", "08", "11", "12"):
    pools[name] = np.load(io.BytesIO(read(ROOT / f"artifacts/p23_v2/pool_{name}.npz")))
p3_metadata = {}
for large, small in (("08", "07"), ("12", "11")):
    a, b = pools[large], pools[small]
    k = a["X"].tolist().index("NO2")
    assert np.array_equal(a["A"], b["A"]) and np.array_equal(a["B"], b["B"])
    # Forbidden cells are NaN in both blind-pool arrays, not unequal values.
    assert np.array_equal(a["vhat"][:, :, k], b["vhat"][:, :, 0], equal_nan=True)
    mask = a["allowed"][:, :, k]
    assert np.array_equal(a["vhat"][:, :, k][mask], b["vhat"][:, :, 0][mask])
    assert np.array_equal(a["allowed"][:, :, k], b["allowed"][:, :, 0])
    p3_metadata[large] = {"X": a["X"].tolist(), "allowed_per_X": a["allowed"].sum(axis=(0,1)).tolist(),
                          "NO2_source_table_equals_P2": True}

seal_path = ROOT / "codex/p2_cim_service/final_seal.json"
seal = json.loads(read(seal_path))
seal_failures = [p for p,h in seal["files"].items()
                 if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != h]
assert not seal_failures
result = {
    "scope": "Post-hoc read-only self-review, not a changed acceptance rule or new experiment",
    "new_fits": 0, "new_SA_calls": 0, "new_hardware_tasks": 0,
    "matrix_shape": list(K.shape), "max_abs_K": int(abs(K).max()),
    "candidates": len(values), "groups": len(blocks), "quantized_distinct_cost_levels": len(np.unique(q)),
    "ground": ground, "legal_energy_constant": sum(constants), "sum_chain_min_q": int(local_min_q.sum()),
    "illegal_gap": illegal_gap, "unique_optimum_index": star,
    "critical_chain_zero_based": critical, "critical_chain_mapping": blocks[critical]["mapping"],
    "critical_chain_costs": q[blocks[critical]["mapping"]].tolist(),
    "minimum_legal_wrong_decision_gap": wrong_gap, "strict_failure_gap": failure_gap,
    "wrong_decision_witness": witness_info, "original_vmin": float(values.min()), "original_range_R": float(r.max()),
    "original_second_gap": float(np.sort(r)[1]), "formal_tasks": task_rows,
    "formal_all_return_gap_range": [min(x["gap"] for x in all_rows), max(x["gap"] for x in all_rows)],
    "formal_local_optimal_chain_count_range": [min(x["locally_optimal_chains"] for x in all_rows), max(x["locally_optimal_chains"] for x in all_rows)],
    "all_formal_returns_below_strict_failure_gap": True,
    "prior_control_recounts": prior_controls, "P3_metadata_only": p3_metadata,
    "final_seal_files_verified": len(seal["files"]), "sealed_file_failures": seal_failures,
    "source_sha256": sources}
print(json.dumps(result, ensure_ascii=False, indent=2))
