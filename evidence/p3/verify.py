"""Read-only P3 certificate replay. This file imports neither builder nor service decoder."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
from collections import Counter

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACK = Path("evidence/p3")
RECEIPT = PACK / "receipt.json"
# Matrix SHA-256 is over C-order little-endian int64 bytes, not ZIP framing.
MATRIX_SHA = {
    "O3": "beb1d7e6715c5420782008b4f36982b9b6a5b5ccd793b469bf69cc7c0a3ee6a2",
    "NO2": "f72fbc9e425ebc1ff890d5f439878560f59d8fc62e62065b79062f30a922506f",
    "FO2": "3502da271cd352e795c1d27a0fa5df0a12f24dcf4c1c32a24b49cfe23389dcc9",
    "tie08": "2c0a58ecff62eda029b2e3314410cdffff7dfb8590f6adb5c67e5f7b11e2a627",
}
# Independently extracted from pool_{08,12}.npz and the corresponding ID CSV.
# Format per candidate: official_id,A,B,float64.hex() followed by LF.
DICTIONARY_SHA = {
    "O3": "d6abd90a50900e772aca25c029a0e014bc5b0343aebf3288a17c36cb53081908",
    "NO2": "3a78b6dc2285f15af2b9e475a84ae849410411d6c95cc0a4ea25a3845e7cacab",
    "FO2": "8852bb832257dceb960a7786dcb3877b41d609ef2d2e32732846a7e2d63ce342",
    "tie08": "5e49309d4c031b633d26e9544fe837906a508b764d7aff0dcc4f2cbc86ae2da8",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spectra(fields, bonds):
    """Check the full two-sector transfer histogram against exhaustive local states."""
    dp = {(s, False, -2 * int(fields[0]) * s): 1 for s in (-1, 1)}
    for field, bond in zip(fields[1:], bonds):
        following = Counter()
        for (last, broken, energy), count in dp.items():
            for s in (-1, 1):
                next_energy = energy - 2 * s * (int(field) + int(bond) * last)
                following[s, broken or last < s, next_energy] += count
        dp = following
    hist = [Counter(), Counter()]
    for (_, broken, energy), count in dp.items():
        hist[int(broken)][energy] += count
    n = len(fields)
    patterns = 2 * ((np.arange(2**n)[:, None] >> np.arange(n)) & 1) - 1
    energy = -2 * ((patterns * fields).sum(1)
                   + (patterns[:, 1:] * patterns[:, :-1] * bonds).sum(1))
    legal = (np.diff(patterns, axis=1) <= 0).all(1)
    require(hist[0] == Counter(energy[legal]) and hist[1] == Counter(energy[~legal]),
            "transfer histogram differs from exhaustive spectrum")
    # Map one legal prefix per wall position to candidate order.
    legal_cost = np.empty(n + 1, dtype=np.int64)
    legal_cost[(patterns[legal] == 1).sum(1)] = energy[legal]
    return legal_cost, min(hist[1])


def replay_witnesses(data, q, blocks, residual, ground):
    """Decode domain-wall transitions and evaluate the full matrix edge expression."""
    matrix, spins = data["J"], data["witnesses"]
    indices = np.flatnonzero(residual >= 0)
    wi = data["witness_index"]
    require(wi.dtype.kind in "iu" and np.array_equal(wi, indices),
            "wrong witness index, duplicate or missing finite witness")
    require(spins.dtype.kind == "i" and spins.shape == (len(indices), len(matrix))
            and np.isin(spins, (-1, 1)).all(), "invalid witness spin array")
    winners = np.empty((len(indices), len(blocks)), dtype=int)
    for j, (lo, hi, axes) in enumerate(blocks):
        relative = spins[:, axes] * spins[:, -1:]
        boundary = np.ones((len(indices), 1), dtype=np.int8)
        changes = np.diff(np.column_stack((boundary, relative, -boundary)), axis=1)
        require((changes <= 0).all() and ((changes == -2).sum(1) == 1).all(),
                "illegal spin transition in witness")
        winners[:, j] = lo + np.argmax(changes == -2, axis=1)
    decoded = [min(row, key=lambda idx: (q[idx], idx)) for row in winners]
    require(np.array_equal(decoded, indices), "witness decoded to wrong candidate")
    i, j = np.nonzero(np.triu(matrix, 1))
    energies = -2 * (matrix[i, j] * spins[:, i] * spins[:, j]).sum(1)
    require(np.array_equal(energies - ground, residual[indices]), "nonminimal witness energy")


def independent_residual(q, blocks, legal_costs):
    """At each winning-key cutoff search each OTHER chain for its lowest legal energy."""
    count = len(q)
    # rank[c] is the position in the total (integer q, row-index) order.
    rank = np.empty(count, dtype=int)
    rank[np.lexsort((np.arange(count), q))] = np.arange(count)
    # Keep impossibility as integer counts; never add an infinite energy.
    penalties = np.zeros((len(blocks), count), dtype=np.int64)
    blocked = np.zeros((len(blocks), count), dtype=bool)
    for g, ((lo, hi, _), cost) in enumerate(zip(blocks, legal_costs)):
        ranked = np.argsort(rank[lo:hi])
        keys = rank[lo:hi][ranked]
        suffix_minimum = np.minimum.accumulate(cost[ranked][::-1])[::-1]
        ix = keys.searchsorted(rank)
        blocked[g] = ix == len(keys)
        ok = ~blocked[g]
        penalties[g, ok] = suffix_minimum[ix[ok]] - cost.min()
        # Winning chain must choose exactly c, even when a cheaper later key is eligible.
        penalties[g, lo:hi] = cost - cost.min()
        blocked[g, lo:hi] = False
    result = penalties.sum(0)
    result[blocked.any(0)] = -1
    return result


def audit_batch(data, name):
    """Certify one NPZ batch; D=-1 denotes an unreachable final decoder winner."""
    require(name in MATRIX_SHA, "unregistered batch")
    n = 541 if name == "tie08" else 529
    m = n - 40 + 1
    J, q, v = data["J"], data["q"], data["values"]
    ids, aa, bb = data["ids"], data["A"], data["B"]
    require(J.dtype.kind == "i" and J.dtype.itemsize == 8 and J.shape == (m, m)
            and (J >= -127).all() and (J <= 127).all() and np.array_equal(J.T, J)
            and not J.diagonal().any(), "8-bit integer matrix contract")
    jsha = hashlib.sha256(J.astype("<i8").tobytes()).hexdigest()
    require(jsha == MATRIX_SHA[name], "registered matrix hash mismatch")
    require(q.shape == v.shape == ids.shape == aa.shape == bb.shape == (n,)
            and q.dtype.kind in "iu" and ids.dtype.kind in "iu"
            and aa.dtype.kind == bb.dtype.kind == "U" and len(set(ids)) == n
            and len(set(zip(aa, bb))) == n and v.dtype.kind == "f" and v.dtype.itemsize == 8
            and np.isfinite(v).all(), "candidate dictionary contract")
    raw = "".join(f"{int(cid)},{a},{b},{float(value).hex()}\n"
                  for cid, a, b, value in zip(ids, aa, bb, v))
    require(hashlib.sha256(raw.encode("ascii")).hexdigest() == DICTIONARY_SHA[name],
            "candidate mapping differs from frozen source")
    regret = v - v.min()
    fraction = np.where(regret <= 2, .375*regret, .75+.25*(regret-2)/(regret.max()-2))
    require(np.array_equal(np.rint(63*fraction), q), "q and source shaping disagree")
    offsets = data["offsets"]
    reference, mapping = data["reference"], data["mapping"]
    require(reference.shape == () and reference.dtype.kind in "iu" and int(reference) == m-1,
            "incorrect shared reference index")
    require(mapping.dtype.kind in "iu" and np.array_equal(mapping, np.arange(n)),
            "candidate mapping is not the frozen ordered bijection")
    sizes = np.full(40, n//40)
    sizes[:n%40] += 1
    require(offsets.dtype.kind in "iu" and np.array_equal(offsets, np.r_[0, sizes.cumsum()]),
            "invalid segmentation or reference index")

    blocks, costs, illegal_gaps = [], [], []
    edge_mask = np.zeros_like(J, dtype=bool)
    for g, (lo, hi) in enumerate(zip(offsets[:-1], offsets[1:])):
        lo, hi = int(lo), int(hi)
        axes = np.arange(lo-g, hi-g-1)
        edge_mask[axes, -1] = True
        edge_mask[axes[:-1], axes[1:]] = True
        legal, bad = spectra(J[axes, -1], J[axes[:-1], axes[1:]])
        require(np.ptp(legal - 4*q[lo:hi]) == 0, "legal energies disagree with integer q")
        blocks.append((lo, hi, axes))
        costs.append(legal)
        illegal_gaps.append(bad - int(legal.min()))
    require(not np.any(np.triu(J, 1)[~edge_mask]), "undeclared cross-chain edge")
    ground = int(sum(c.min() for c in costs))
    require(min(illegal_gaps) > 0, "G1 has an illegal ground-state witness")
    d = independent_residual(q, blocks, costs)
    require(data["D"].dtype.kind == "i" and np.array_equal(data["D"], d),
            "stored D differs from independent lower bound or blocking constraint")
    replay_witnesses(data, q, blocks, d, ground)
    reachable = d >= 0
    candidates_at_ground = np.flatnonzero(d == 0)
    worst = float(regret[candidates_at_ground].max())
    wrong = reachable & (regret > 0)
    rwrong = int(d[wrong].min())
    require(worst <= .1, "G2_0.1 failed")
    if name == "tie08":
        require(q[288] == q[303] == 0 and d[288] == 0 and d[303] == 196
                and np.array_equal(candidates_at_ground, [288]) and v.argmin() == 303
                and (aa[288], bb[288], aa[303], bb[303]) == ("Ba","Nb","Ba","Ta"),
                "08 NO2 tie rule regression")
    else:
        require(worst == 0 and len(candidates_at_ground) == 1
                and np.array_equal(regret <= .1, regret == 0), "blind exact-hit contract")
    rank_order = np.lexsort((ids, v))
    unreachable_ranks = np.flatnonzero(~reachable[rank_order]) + 1
    envelope = []
    previous = -1.
    for threshold in np.unique(d[reachable]):
        height = float(regret[d == threshold].max())
        if height > previous:
            envelope.append([int(threshold), height])
            previous = height
    return dict(matrix_sha256=jsha, candidate_count=n, ground_energy=ground,
                illegal_gap=int(min(illegal_gaps)), strict_wrong_gap=rwrong,
                G1="CERTIFIED", **{"G2_0.1": "CERTIFIED"},
                exact_argmin_preserved=(worst == 0), worst_ground_regret=worst,
                max_abs_J=int(abs(J).max()), reachable=int(reachable.sum()),
                blocked=int((~reachable).sum()), top100_reachable=int(reachable[rank_order[:100]].sum()),
                first_unreachable_rank=int(unreachable_ranks[0]) if len(unreachable_ranks) else None,
                envelope=envelope)


def compare_p2(root, data):
    folder = root / "evidence/p2"
    with np.load(folder / "matrix.npz", allow_pickle=False) as reference:
        for key in ("J", "q", "values"):
            require(np.array_equal(reference[key], data[key]), f"P2 positive control: {key}")
    with (folder / "candidates.csv").open(encoding="utf-8", newline="") as f:
        original = list(csv.DictReader(f))
    require(len(original) == len(data["ids"]), "P2 candidate count")
    for i, row in enumerate(original):
        require(int(row["id"]) == data["ids"][i] and (row["A"], row["B"], row["X"])
                == (data["A"][i], data["B"][i], "NO2"), "P2 candidate ID/order")
    blocks = json.loads((folder / "blocks.json").read_text())
    offsets = data["offsets"]
    require(len(blocks) == len(offsets)-1, "P2 group count")
    for g, b in enumerate(blocks):
        a, z = int(offsets[g]), int(offsets[g+1])
        require(b == dict(reference=len(data["J"])-1, start=a-g, stop=z-g-1,
                          mapping=list(range(a, z))), "P2 reference or dictionary mismatch")


def audit_exports(folder, batches):
    """Match both readable exports to the checked integer witnesses and staircase."""
    with (folder / "candidates.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        require(reader.fieldnames == ["batch", "index", "id", "A", "B", "vhat", "q", "D"],
                "invalid candidate CSV header")
        for name in batches:
            with np.load(folder/f"{name}.npz", allow_pickle=False) as data:
                columns = (data[key] for key in ("ids", "A", "B", "values", "q", "D"))
                for i, (cid, a, b, value, q, d) in enumerate(zip(*columns)):
                    row = next(reader, None)
                    require(row is not None and None not in row and
                            (row["batch"], int(row["index"]), int(row["id"]), row["A"], row["B"],
                             float(row["vhat"]).hex(), int(row["q"]), row["D"]) ==
                            (name, i, cid, a, b, float(value).hex(), q, "INF" if d < 0 else str(d)),
                            f"dictionary CSV disagrees with certified candidate {name}/{i}")
        require(next(reader, None) is None, "extra candidate CSV rows")
    with (folder / "envelopes.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        require(reader.fieldnames == ["batch", "residual", "max_regret"], "invalid envelope CSV header")
        for name, result in batches.items():
            for threshold, height in result["envelope"]:
                row = next(reader, None)
                require(row is not None and None not in row and row["batch"] == name
                        and int(row["residual"]) == threshold and float(row["max_regret"]).hex() == height.hex(),
                        f"envelope CSV disagrees with exact bound for {name}/{threshold}")
        require(next(reader, None) is None, "extra envelope CSV rows")


def safe_path(root, rel):
    rel = Path(rel)
    require(not rel.is_absolute() and ".." not in rel.parts, "unsafe inventory path")
    resolved = (root / rel).resolve()
    require(resolved.is_relative_to(root.resolve()), "inventory path outside package")
    return resolved


def verify_hashes(root, mapping):
    require(isinstance(mapping, dict) and mapping, "empty receipt inventory")
    for rel, expected in mapping.items():
        require(isinstance(expected, str) and re.fullmatch("[0-9a-f]{64}", expected),
                f"invalid registered digest: {rel}")
        require(file_sha(safe_path(root, rel)) == expected, f"hash mismatch: {rel}")


def verify_anchor(root, repo, supplied_anchor=None):
    """Bind receipt to first commit containing this path, then verify its entire inventory."""
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args])
    rel = RECEIPT.as_posix()
    history = git("rev-list", "--reverse", "HEAD", "--", rel).decode().splitlines()
    require(history, "receipt has no anchor in this git history")
    anchor = history[0]
    if supplied_anchor is not None:
        require(supplied_anchor == anchor, "expected anchor must equal the full first commit SHA")
    sealed = git("show", f"{anchor}:{rel}")
    require((root/RECEIPT).read_bytes() == sealed, "receipt differs from first Git anchor")
    receipt = json.loads(sealed)
    required = {str(PACK / (name + ".npz")) for name in MATRIX_SHA}
    required.update(str(PACK / name) for name in (
        "verify.py", "protocol.py", "test_protocol.py", "candidates.csv", "envelopes.csv"))
    required.add("codex/P3_FINAL.md")
    require(required <= set(receipt["files"]), "missing required evidence from receipt")
    verify_hashes(root, receipt["files"])
    return anchor, receipt


def main():
    require(__debug__, "optimized Python is disabled for certificate replay")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchor", help="expected full SHA of first receipt commit")
    parser.add_argument("--anchor-repo", type=Path, default=ROOT, help="Git history used to verify a mirror")
    parser.add_argument("--sources", action="store_true", help="also verify registered original source files")
    parser.add_argument("--preseal", action="store_true", help="first-time mathematics only; never a sealed receipt")
    args = parser.parse_args()
    if args.preseal:
        require(not (ROOT/RECEIPT).exists(), "preseal disabled after receipt is written")
        require(not args.anchor and not args.sources, "preseal cannot verify an anchor or receipt sources")
        anchor = None
    else:
        anchor, receipt = verify_anchor(ROOT, args.anchor_repo, args.anchor)
        if args.sources:
            verify_hashes(ROOT, receipt["sources"])
    batches = {}
    for name in MATRIX_SHA:
        with np.load(ROOT/PACK/f"{name}.npz", allow_pickle=False) as data:
            batches[name] = audit_batch(data, name)
            if name == "NO2":
                compare_p2(ROOT, data)
    audit_exports(ROOT/PACK, batches)
    print(json.dumps(dict(status="PRESEAL_MATH_ONLY" if args.preseal else "SEALED_VERIFIED",
                          anchor=anchor, sources_checked=args.sources,
                          p2_no2_regression=True, batches=batches), indent=2))


if __name__ == "__main__":
    main()
