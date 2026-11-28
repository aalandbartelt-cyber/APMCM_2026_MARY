"""Read-only replay of an atomic lane-A state revision. No SDK or network imports."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
from datetime import datetime
import zlib

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SEAL = ROOT / "evidence/p3"
LANE = ROOT / "artifacts/p3_run/A"
OUT = ROOT / "artifacts/p3_run/verify"
ANCHOR = "2e1dab8d3312ad01bac1d71c7edd6ac5fddb7d37"
sys.path.insert(0, str(SEAL))
import protocol


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


class PrimitiveReturn(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError("External objects in return")


def ordered_spins(raw):
    cap = 64 * 1024 * 1024
    check(len(raw) <= cap, "oversized packet")
    src = io.BytesIO(raw)
    d = PrimitiveReturn(src).load()
    check(not src.read(1) and isinstance(d, dict) and d.get("format") == "ndarray-zlib-v1", "return format")
    shape, dtype = d["shape"], np.dtype(d["dtype"])
    check(isinstance(shape, (tuple, list)) and len(shape) == 2 and all(type(k) is int for k in shape)
          and 0 < shape[0] <= 100000 and shape[1] == 490 and dtype.kind in "fiu", "array dimensions")
    size = shape[0] * shape[1] * dtype.itemsize
    check(size <= cap and isinstance(d["data"], bytes), "return bounds")
    dec = zlib.decompressobj()
    content = dec.decompress(d["data"], size + 1)
    check(len(content) == size and dec.eof and not dec.unused_data and not dec.unconsumed_tail, "zlib frame")
    spins = np.frombuffer(content, dtype=dtype).reshape(shape)
    check(np.isin(spins, [-1, 1]).all(), "non-binary return")
    return spins


def evaluate(batch, spin_rows, cert):
    # Each legal wall position has an explicit binary-string lookup, independent
    # of the protocol's transition test / count of +1 entries.
    J = batch["J"]
    left, right = np.nonzero(np.triu(J, 1))
    edge_weights = -2 * J[left, right].astype(np.int64)
    q, values, ids = batch["q"], batch["values"], batch["ids"]
    reference = int(batch["reference"])
    reference_id = int(ids[np.argmin(values)])
    ground = cert["ground_energy"]
    legal_words = []
    for start, stop in zip(batch["offsets"][:-1], batch["offsets"][1:]):
        size = int(stop - start - 1)
        words = {bytes([1] * k + [0] * (size - k)): int(start + k) for k in range(size + 1)}
        legal_words.append((size, words))
    rows = []
    for index, vector in enumerate(spin_rows):
        s = vector.astype(np.int64)
        energy = int(edge_weights @ (s[left] * s[right]))
        residue = energy - ground
        same = np.delete((s == s[reference]).astype(np.uint8), reference)
        bad, candidates, pos = [], [], 0
        for group, (width, words) in enumerate(legal_words, start=1):
            match = words.get(same[pos:pos+width].tobytes())
            if match is None:
                bad.append(group)
            else:
                candidates.append(match)
            pos += width
        check(pos == len(same), "unused spin")
        check(residue >= 0 and (not bad or residue >= cert["illegal_gap"]), f"ground/legality certificate {index}")
        row = dict(return_index=index, energy=energy, residual=residue, strict=not bad, invalid_groups=bad)
        if candidates:
            best = sorted((int(q[c]), c) for c in candidates)[0][1]
            value = float(values[best])
            regret = value - float(np.min(values))
            win = int(ids[best]) == reference_id
            decoded = dict(candidate_index=best, id=int(ids[best]), vhat=value, regret=regret, exact=win)
            if bad:
                row["partial_only"] = decoded
            else:
                row.update(decoded)
                row["regret_le_0.1"] = regret <= .1
                check(0 <= batch["D"][best] <= residue and win == (regret <= .1), f"decoder certificate {index}")
        rows.append(row)
    eligible = [r for r in rows if r["strict"]]
    min_energy = min((r["energy"] for r in eligible), default=None)
    primary = next((r for r in eligible if r["energy"] == min_energy), None)
    secondary = {"exists_strict_hit": any(r["exact"] for r in eligible),
                 "min_strict_regret": min((r["regret"] for r in eligible), default=None)}
    return {"rows": rows, "primary": primary, "secondary": secondary, "strict_count": len(eligible)}


def read_history(state, raw_state):
    snapshots = []
    for rev in range(1, state["revision"] + 1):
        raw = (LANE / "history" / f"{rev:05d}.json").read_bytes()
        h = json.loads(raw)
        check(h["revision"] == rev and h["anchor"] == ANCHOR, f"history revision {rev}")
        snapshots.append(h)
    check(raw == raw_state, "state/history mismatch")
    return snapshots


def check_gate(snapshots, slot):
    found = [i for i, s in enumerate(snapshots) if s["event"] == slot + "_RESERVED"]
    if not found:
        return None
    check(len(found) == 1 and found[0] > 0, f"duplicate/missing reservation {slot}")
    i = found[0]
    cur, prev = snapshots[i], snapshots[i-1]
    mark = cur["attempts"][slot]
    when = datetime.fromisoformat(mark["intent_at"])
    check(mark["gate"] == protocol.ledger_gate(slot, prev["records"], when) == "READY_OFFLINE",
          f"rejected gate replay for {slot}")
    check(not prev.get("stop_reason") and when < protocol.STOP, f"paused or cutoff {slot}")
    prior_slots = protocol.SLOTS[:protocol.SLOTS.index(slot)]
    balance = prev["baseline_balance"]
    for prev_slot in prior_slots:
        old = prev["records"][prev_slot]
        bill = old["billing"]
        check(bill["before"] == balance and bill["attributable"] is True and bill["after"]["550"] == balance["550"]-1
              and bill["after"]["1000"] == balance["1000"] and datetime.fromisoformat(bill["recorded_at"]) <= when,
              f"billing did not precede {slot}")
        check(old.get("task_id") and (prev_slot != "F01" or old["status"] == "VALID_COMPLETED"), f"technical gate {slot}")
        balance = bill["after"]
    check(mark["before"] == balance and balance["550"] > 0, f"balance before {slot}")
    return cur["revision"]


def event_sources(snapshots, slot, folder):
    seen, accepts, terminal, evidence = set(), [], [], []
    for h in snapshots:
        call = h["records"].get(slot, {}).get("last_transport")
        if not call or call["request_dir"] in seen:
            continue
        seen.add(call["request_dir"])
        folder_name = Path(call["request_dir"]).name
        report = folder / folder_name / "summary.json"
        check(read(report) == call, f"transport/ledger mismatch {slot}")
        for e in call["events"]:
            if not e.get("path"):
                continue  # An attempted request can fail before any HTTP reply arrives.
            path = folder / folder_name / Path(e["path"]).name
            raw = path.read_bytes()
            check(sha(raw) == e["sha256"], f"HTTP hash {slot}")
            payload = json.loads(raw)
            code = str(payload.get("code"))
            check(code == e["response_code"], f"HTTP response code {slot}")
            check(datetime.fromisoformat(e["started_at"]) <= datetime.fromisoformat(e["ended_at"]), f"HTTP time {slot}")
            evidence.append({"path":str(path.relative_to(LANE)), "sha256":e["sha256"], "kind":e["kind"],
                             "started_at":e["started_at"], "ended_at":e["ended_at"], "http_status":e["http_status"]})
            d = payload.get("data") or {}
            if code == "0" and e["kind"] == "create" and isinstance(d, dict) and d.get("result_id"):
                accepts.append((str(d["result_id"]), e["sha256"]))
            if code == "0" and e["kind"] == "query" and isinstance(d, dict) and str(d.get("code")) == "1000":
                terminal.append(e["sha256"])
    return accepts, terminal, evidence


def audit(revision=None):
    raw_state = (LANE / "state.json").read_bytes()
    if revision is not None:
        current = json.loads(raw_state)["revision"]
        check(1 <= revision <= current, "Unknown state revision")
        raw_state = (LANE / "history" / f"{revision:05d}.json").read_bytes()
    state = json.loads(raw_state)
    sealed = (SEAL / "receipt.json").read_bytes()
    anchor_copy = subprocess.check_output(["git", "-C", str(ROOT), "show", ANCHOR+":evidence/p3/receipt.json"])
    check(sealed == anchor_copy and state["receipt_sha256"] == sha(sealed) and state["anchor"] == ANCHOR, "anchor receipt")
    names = json.loads(sealed)["files"]
    for rel in ("evidence/p3/protocol.py","evidence/p3/certificates.json","evidence/p2/tasks.csv",
                *(f"evidence/p3/{fam}.npz" for fam in protocol.SLICES)):
        check(sha((ROOT/rel).read_bytes()) == names[rel], f"sealed asset mismatch {rel}")
    certs = read(SEAL/"certificates.json")["batches"]
    snapshots = read_history(state, raw_state)
    previous_ids = {row["result_id"] for row in csv.DictReader((ROOT/"evidence/p2/tasks.csv").read_text().splitlines())}
    results = []
    for slot in protocol.SLOTS:
        row = state["records"].get(slot, {})
        family = protocol.FAMILY[slot]
        status = row.get("status", "NOT_STARTED")
        gate = check_gate(snapshots, slot)
        result = {"slot":slot, "family":family, "status":status, "gate_revision":gate,
                  "vector_replay":"NOT_AVAILABLE", "billing":"AWAITING_READBACK" if row.get("task_id") else "NO_CONFIRMED_CREATE"}
        results.append(result)
        if gate is None:
            check(not row and slot not in state["attempts"], f"unreserved slot {slot}")
            continue
        out = LANE / slot
        accepts, terminal, events = event_sources(snapshots, slot, out)
        result["events"] = events
        check(len(accepts) <= 1 and sum(e["kind"] == "create" for e in events) <= 1, f"multiple creates {slot}")
        if row.get("task_id"):
            task = row["task_id"]
            check(len(accepts) == 1 and accepts[0][0] == task, f"server ID source {slot}")
            check((task not in previous_ids) == (status != "DUPLICATE"), f"ID collision {slot}")
            previous_ids.add(task)
            created, intent = read(out/"created.json"), read(out/"create_intent.json")
            check(created["result_id"] == task and created["sha256"] == accepts[0][1], f"creation receipt {slot}")
            check(created["matrix_sha256"] == intent["matrix_sha256"] == certs[family]["matrix_sha256"]
                  and intent["bit_num"] == 490 and intent["task_mode"] == "optimization" and intent["sample_number"] == 100
                  and intent["anchor"] == ANCHOR and intent["slot"] == slot and intent["family"] == family,
                  f"matrix / mode contract {slot}")
            result["task_id"] = task
        if row.get("billing"):
            bill = row["billing"]
            result["billing"] = protocol._billing_status(bill)
            check(bill["before"] == state["attempts"][slot]["before"] and bill in row["balance_observations"], f"billing evidence {slot}")
        if status != "VALID_COMPLETED":
            if status == "INVALID_RETURN":
                result["vector_replay"] = "DECLARED_INVALID"
            continue
        check(bool(terminal), f"no server terminal query {slot}")
        query = (out/"terminal_query.bin").read_bytes()
        a = row["return_archive"]
        check(sha(query) == terminal[0] == a["terminal_query_sha256"], f"first terminal query {slot}")
        raw = (out/"result.pkl").read_bytes()
        check(sha(raw) == a["sha256"] and result["task_id"] == a["result_id"], f"raw result binding {slot}")
        spins = ordered_spins(raw)
        npy = (out/"vectors.npy").read_bytes()
        saved = np.load(io.BytesIO(npy), allow_pickle=False)
        check(sha(npy) == a["vectors_sha256"] and len(spins) == a["count"]
              and saved.dtype == spins.dtype and np.array_equal(saved, spins), f"ordered vector archive {slot}")
        with np.load(SEAL/f"{family}.npz", allow_pickle=False) as batch:
            independent = evaluate(batch, spins, certs[family])
            official = protocol.judge_return(family, batch, spins)
        check(official == row["outcome"] and all(official.get(k) == v for k,v in independent.items()), f"vector judgments {slot}")
        result.update(vector_replay="VERIFIED", verified_vector_count=len(spins), **independent,
                      raw_sha256=sha(raw), vectors_sha256=sha(npy), terminal_sha256=sha(query))
    check(protocol.summarize(state["records"]) == state["summary"], "state summary")
    return {"anchor":ANCHOR, "state_revision":state["revision"], "state_sha256":sha(raw_state),
            "as_of":state["updated_at"], "verified_slots":sum(r["vector_replay"] == "VERIFIED" for r in results),
            "verified_vectors":sum(r.get("verified_vector_count",0) for r in results), "slots":results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--revision", type=int, help="replay exactly this immutable state revision (e.g., snapshot source)")
    args = parser.parse_args()
    report = audit(args.revision)
    if not args.check_only:
        OUT.mkdir(exist_ok=True, parents=True)
        dest = OUT / f"cloud_replay_rev{report['state_revision']:05d}.json"
        raw = (json.dumps(report, indent=2, allow_nan=False)+"\n").encode()
        # The exact state bytes identify a replay. Never supersede a previous run.
        with tempfile.NamedTemporaryFile(dir=OUT) as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
            try:
                os.link(f.name, dest)
            except FileExistsError:
                check(dest.read_bytes() == raw, "existing report differs for the same revision")
    print(json.dumps({k:v for k,v in report.items() if k != "slots"}))


if __name__ == "__main__":
    main()
