"""Rebuild the offline witness bundle from the frozen tables into an empty directory."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "artifacts/p23_v2"
OFFICIAL = ROOT / "00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date"
FAMILIES = ("O3", "NO2", "FO2")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_out(path, columns, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def read_pool(pool, manifest):
    path = FROZEN / f"pool_{pool}.npz"
    if sha(path) != manifest[pool]:
        raise ValueError(f"input digest mismatch: {pool}")
    with np.load(path, allow_pickle=False) as archive:
        z = {k: archive[k] for k in archive.files}
    with next(OFFICIAL.glob(pool + "_*.csv")).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    by_key = {(row["A"], row["B"], row["X"]): int(row["id"]) for row in rows}
    if len(rows) != len(set(by_key.values())) or len(by_key) != int(z["allowed"].sum()):
        raise ValueError(f"non-bijective pool {pool}")
    if not np.array_equal(np.isfinite(z["vhat"]), z["allowed"]):
        raise ValueError(f"mask mismatch: {pool}")
    data = {}
    for x in FAMILIES:
        col = list(z["X"]).index(x)
        mask = z["allowed"][:, :, col]
        ia, ib = np.nonzero(mask)
        a, b = z["A"][ia], z["B"][ib]
        ids = np.array([by_key[(u, v, x)] for u, v in zip(a, b)], dtype="<i8")
        members = z["members"][:, :, col, :][mask]
        values = z["vhat"][:, :, col][mask]
        if not np.array_equal(values.view("u8"), members.mean(1).view("u8")):
            raise ValueError("frozen member mean mismatch")
        data[x] = (ids, a, b, values, members)
    return data


def build_batch(out, name, data):
    ids, a, b, values, _ = data
    n = len(values)
    original = values - values.min()
    span = original.max()
    if span <= 2:
        raise ValueError("unexpected input to the frozen piecewise map")
    q = np.rint(63 * np.where(original <= 2, .375 * original,
                              .75 + .25 * (original - 2) / (span - 2))).astype("<i8")
    groups = np.array_split(np.arange(n), 40)
    offsets = np.array([0] + [int(g[-1]) + 1 for g in groups], dtype="<i8")
    ns = n - 40 + 1
    matrix = np.zeros((ns, ns), dtype="<i8")
    axes = []
    for k, group in enumerate(groups):
        axes_g = np.arange(offsets[k] - k, offsets[k+1] - k - 1)
        field = -np.diff(q[group])
        field[0] += 64
        field[-1] -= 64
        matrix[axes_g, -1] = matrix[-1, axes_g] = field
        matrix[axes_g[1:], axes_g[:-1]] = matrix[axes_g[:-1], axes_g[1:]] = 64
        axes.append(axes_g)

    # On a legal chain each slot costs 4q plus a group constant. Restrict every
    # competing chain to keys no smaller than c; never consult values to break ties.
    order_key = q * n + np.arange(n)
    distance = np.full(n, -1, dtype="<i8")
    vectors = []
    for c in range(n):
        choices = []
        for group in groups:
            if group[0] <= c <= group[-1]:
                choices.append(c)
                continue
            options = group[order_key[group] >= order_key[c]]
            if not len(options):
                break
            choices.append(options[order_key[options].argmin()])
        if len(choices) != len(groups):
            continue
        s = np.full(ns, -1, dtype="i1")
        s[-1] = 1
        total = 0
        for i, group, axis in zip(choices, groups, axes):
            s[axis[:i-group[0]]] = 1
            total += 4 * int(q[i] - q[group].min())
        distance[c] = total
        vectors.append(s)
    with (out / (name + ".npz")).open("xb") as stream:
        np.savez_compressed(stream, J=matrix, q=q, values=values, ids=ids, A=a, B=b,
                            offsets=offsets, mapping=np.arange(n), reference=np.int64(ns-1),
                            D=distance, witness_index=np.flatnonzero(distance >= 0),
                            witnesses=np.stack(vectors))
    rows = [(name, i, int(ids[i]), a[i], b[i], repr(float(values[i])), int(q[i]),
             int(distance[i]) if distance[i] >= 0 else "INF") for i in range(n)]
    reachable = distance >= 0
    best = -1.
    staircase = []
    for d in np.unique(distance[reachable]):
        new = float(original[distance == d].max())
        if new > best:
            best = new
            staircase.append((name, int(d), repr(best)))
    return rows, staircase


def member_rows(pool, data):
    regions = dict(data)
    regions["ALL"] = tuple(np.concatenate(items) for items in zip(*data.values()))
    family_by_id = {int(i): x for x, pack in data.items() for i in pack[0]}
    member_seeds = [json.loads((FROZEN / "members" / f"member_{j:02d}.json").read_text())["seed"]
                    for j in range(20)]
    rows = []
    for region, (ids, a, b, values, members) in regions.items():
        nominal = int(values.argmin())
        for j in range(members.shape[1]):
            m = members[:, j]
            winner = int(m.argmin())
            if (m == m[winner]).sum() != 1:
                raise ValueError("non-unique member winner")
            rows.append((pool, region, j, member_seeds[j], int(ids[winner]), a[winner], b[winner],
                         family_by_id[int(ids[winner])],
                         int(ids[nominal]), 1 + int((m < m[nominal]).sum()),
                         repr(float(m[nominal]-m[winner]))))
    return rows


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit("Use a new or empty output directory; frozen files are never replaced.")
    manifest = {v["pool"]: v["sha256"] for v in json.loads(
        (FROZEN / "interface_manifest.json").read_text())["tables"]}
    blind, full = (read_pool(p, manifest) for p in ("12", "08"))
    batches = {**blind, "tie08": tuple(v[:541] for v in full["NO2"])}
    dictionary, steps = [], []
    for name, data in batches.items():
        rows, env = build_batch(out, name, data)
        dictionary.extend(rows)
        steps.extend(env)
    csv_out(out / "candidates.csv", ["batch","index","id","A","B","vhat","q","D"], dictionary)
    csv_out(out / "envelopes.csv", ["batch","residual","max_regret"], steps)
    csv_out(out / "member_scenarios.csv",
            ["pool","region","member","seed","winner_id","winner_A","winner_B","winner_X","nominal_id",
             "nominal_rank","nominal_regret"], member_rows("08", full)+member_rows("12", blind))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
