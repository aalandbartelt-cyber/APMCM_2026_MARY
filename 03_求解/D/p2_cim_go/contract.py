"""Frozen input verification and pure decoding; no SDK, fitting or network."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
RECEIPT = "codex/p2_cim_go/receipt.json"
INPUT = ROOT / "artifacts/p2_cim_go_20261128/input"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(anchor):
    if len(anchor) != 40 or any(c not in "0123456789abcdef" for c in anchor):
        raise ValueError("Full anchored commit SHA required")
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT)
    history = git("rev-list", "--reverse", "HEAD", "--", RECEIPT).decode().splitlines()
    if not history or anchor != history[0]:
        raise ValueError("Only the FIRST git-anchored receipt is accepted")
    raw = git("show", anchor + ":" + RECEIPT)
    if (ROOT / RECEIPT).read_bytes() != raw:
        raise ValueError("Receipt differs from external git anchor")
    receipt = json.loads(raw)
    failures = [name for name, digest in receipt["files"].items()
                if not (ROOT / name).is_file() or sha(ROOT / name) != digest]
    if failures:
        raise ValueError("Anchored input/code changed: " + ", ".join(failures))
    if receipt["certificate"]["G1"] != "CERTIFIED" or receipt["certificate"]["G2"] != "CERTIFIED":
        raise ValueError("Missing dual certificate")
    return receipt


def can_start(now):
    if now.tzinfo is None:
        raise ValueError("Timezone-aware time required")
    return now < datetime(2026, 11, 29, 18, tzinfo=ZoneInfo("Asia/Shanghai"))


def budget_decision(before, after, uncontaminated):
    """Keep distinct quota buckets; no assumption of fungibility."""
    if not uncontaminated or set(before) != set(after):
        return {"status": "PAUSE_UNVERIFIED_ATTRIBUTION"}
    differences = {k: before[k] - after[k] for k in before}
    used = [k for k, d in differences.items() if d != 0]
    if len(used) != 1 or differences[used[0]] <= 0:
        return {"status": "PAUSE_UNVERIFIED_DEDUCTION", "delta": differences}
    key = used[0]
    d, b = differences[key], before[key]
    n = 25 if 25*d <= .8*b else (15 if 15*d <= b else None)
    status = ("BUDGET_ONLY_PASS" if n else
              "STOP_FIVE_UNAFFORDABLE" if 5*d > b else "STOP_UNCOVERED_SCALE")
    return {"status": status, "bucket": key, "D": d, "B0": b,
            "operational_slots": n, "formal_slots": n-5 if n else None}


def load_input(path=INPUT):
    z = np.load(path / "matrix.npz", allow_pickle=False)
    return z["J"], z["q"], z["values"], json.loads((path / "blocks.json").read_text())


def decode(spins, K, q, values, blocks):
    a = np.asarray(spins)
    if a.ndim != 2 or a.shape[1] != len(K) or len(a) == 0:
        raise ValueError("Expected a nonempty m-by-490 spin array")
    if not np.isfinite(a).all() or not np.isin(a, [-1, 1]).all():
        raise ValueError("Spins must be exactly finite +/-1")
    a = a.astype(np.int64)
    rows = []
    chain_counts = np.zeros(len(blocks), dtype=np.int64)
    edge_counts = [np.zeros(b["stop"]-b["start"]-1, dtype=np.int64) for b in blocks]
    for index, s in enumerate(a):
        candidates, violations = [], []
        for k, b in enumerate(blocks):
            d = s[b["start"]:b["stop"]] * s[b["reference"]]
            broken = d[:-1] < d[1:]
            edge_counts[k] += broken
            violations.append(int(broken.sum()))
            if not broken.any():
                chain_counts[k] += 1
                candidates.append(b["mapping"][int((d == 1).sum())])
        candidate = min(candidates, key=lambda c: (q[c], c)) if candidates else None
        strict = len(candidates) == len(blocks)
        regret = float(values[candidate] - values.min()) if candidate is not None else None
        rows.append(dict(index=index, energy=int(-s @ K @ s),
                         strict_feasible=strict, partial_usable=bool(candidates),
                         valid_chains=len(candidates), chain_violations=violations,
                         candidate=candidate, regret=regret,
                         rank=int(1+np.count_nonzero(values < values[candidate])) if candidate is not None else None,
                         hit_strict=bool(strict and regret == 0),
                         hit_partial=bool(candidate is not None and regret == 0),
                         near_strict=bool(strict and regret <= .1)))
    strict_rows = [r for r in rows if r["strict_feasible"]]
    best_energy = min(strict_rows, key=lambda r: (r["energy"], r["index"])) if strict_rows else None
    return dict(rows=rows, returned_rows=len(rows),
                strict_count=sum(r["strict_feasible"] for r in rows),
                strict_hits=sum(r["hit_strict"] for r in rows),
                partial_count=sum(r["partial_usable"] for r in rows),
                partial_hits=sum(r["hit_partial"] for r in rows),
                chain_legal_counts=chain_counts.tolist(),
                edge_01_counts=[x.tolist() for x in edge_counts],
                best_strict_regret=min((r["regret"] for r in strict_rows), default=None),
                energy_selected_regret=best_energy["regret"] if best_energy else None,
                energy_selected_index=best_energy["index"] if best_energy else None,
                distribution_semantics="UNVERIFIED; diagnostics only until source contract verified")


def check_raw100_contract(report, documented_raw_sample_semantics):
    return report["returned_rows"] == 100 and documented_raw_sample_semantics is True


def check_provider_energy(report, energy, convention):
    if convention != "-sTKs":
        raise ValueError("Unknown provider energy convention; no fitted conversion")
    actual = np.array([r["energy"] for r in report["rows"]])
    provided = np.asarray(energy)
    if provided.shape != actual.shape or not np.array_equal(actual, provided):
        raise ValueError("Provider energies disagree with independent calculation")


def nested_counts(statuses, feasible, near):
    if not len(statuses) == len(feasible) == len(near):
        raise ValueError("Mismatched task lists")
    valid = [s == "VALID_COMPLETED" for s in statuses]
    if any(f and not v for f, v in zip(feasible, valid)) or any(h and not f for h, f in zip(near, feasible)):
        raise ValueError("Invalid numerator eligibility")
    na = sum(s != "NOT_STARTED" for s in statuses)
    nv, nf, ne = sum(valid), sum(feasible), sum(near)
    assert ne <= nf <= nv <= na <= len(statuses)
    return {"N": len(statuses), "N_A": na, "N_V": nv, "N_F": nf, "N_eps": ne}
