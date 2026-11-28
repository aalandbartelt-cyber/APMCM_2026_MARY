"""Offline adjudication of the frozen P3 optimization-service experiment.

Records are a mapping from F01..F09 to independently archived task facts:
status, task_id (if assigned), family, outcome (from judge_return for a return),
and billing {before: {"550": n, "1000": n}, after: {...}, attributable: bool}.
Original vector order is part of the return contract. No function creates a task.
"""

import csv
import hashlib
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from zoneinfo import ZoneInfo

import numpy as np


SLICES = ("O3", "NO2", "FO2")
ORDER = ("O3", "FO2", "NO2", "FO2", "NO2", "O3", "NO2", "O3", "FO2")
SLOTS = tuple(f"F{i:02d}" for i in range(1, 10))
FAMILY = MappingProxyType(dict(zip(SLOTS, ORDER)))
# P05, P95, certified ground energy, first possible illegal residual.
REFERENCES = MappingProxyType({
    "O3": (100, 444, -58496, 340),
    "NO2": (112, 584, -58722, 340),
    "FO2": (88, 408, -58150, 472),
})
MATRIX_SHA = MappingProxyType({
    "O3": "beb1d7e6715c5420782008b4f36982b9b6a5b5ccd793b469bf69cc7c0a3ee6a2",
    "NO2": "f72fbc9e425ebc1ff890d5f439878560f59d8fc62e62065b79062f30a922506f",
    "FO2": "3502da271cd352e795c1d27a0fa5df0a12f24dcf4c1c32a24b49cfe23389dcc9",
})
GLOBAL_WINNER_ID = 13153
STOP = datetime(2026, 11, 29, 18, tzinfo=ZoneInfo("Asia/Shanghai"))
SNAPSHOT = datetime(2026, 11, 29, 21, tzinfo=ZoneInfo("Asia/Shanghai"))
STATES = frozenset(("NOT_STARTED", "CREATED", "PENDING", "CREATE_FAILED",
                    "RUN_FAILED", "VALID_COMPLETED", "INVALID_RETURN",
                    "CONTRACT_ERROR", "DUPLICATE"))


def forecast(family, residual):
    if residual is None:
        return None
    floor, ceiling = REFERENCES[family][:2]
    if residual > ceiling:
        return "WORSE_THAN_SINGLE_SA"
    if residual < floor:
        return "BETTER_THAN_SINGLE_SA"
    return "WITHIN_REFERENCE"


def _invalid(family, reason, status="INVALID_RETURN"):
    return {"family": family, "status": status, "reason": reason, "primary": None}


def choose_strict(rows):
    """The only tie-break after integer energy is the original zero-based position."""
    strict = [row for row in rows if row["strict"]]
    primary = min(strict, key=lambda row: (row["energy"], row["return_index"]), default=None)
    secondary = {"exists_strict_hit": any(row["exact"] for row in strict),
                 "min_strict_regret": min((row["regret"] for row in strict), default=None)}
    return primary, secondary


def judge_return(family, batch, raw_vectors):
    """Judge an ordered complete return against a previously anchor-verified NPZ."""
    _, _, ground, illegal_gap = REFERENCES[family]
    matrix = np.asarray(batch["J"])
    if (matrix.dtype.kind not in "iu" or matrix.shape != (490, 490)
            or hashlib.sha256(matrix.astype("<i8", copy=False).tobytes()).hexdigest() != MATRIX_SHA[family]):
        return _invalid(family, "MATRIX_FAMILY_MISMATCH", "CONTRACT_ERROR")
    matrix = matrix.astype(np.int64, copy=False)
    offsets, q, values, ids, minimum_d = (batch[k] for k in ("offsets", "q", "values", "ids", "D"))
    try:
        vectors = np.asarray(raw_vectors)
    except (ValueError, TypeError):
        return _invalid(family, "RAGGED_OR_NONNUMERIC_RETURN")
    if (vectors.ndim != 2 or not len(vectors) or vectors.shape[1] != len(matrix)
            or vectors.dtype.kind not in "iuf" or not np.isin(vectors, (-1, 1)).all()):
        return _invalid(family, "EXPECTED_NONEMPTY_ORDERED_SIGN_VECTORS")

    spins = vectors.astype(np.int64)
    energies = -np.sum((spins @ matrix) * spins, axis=1)
    winner = int(np.argmin(values))
    rows = []
    for index, (s, energy) in enumerate(zip(spins, energies)):
        residual = int(energy) - ground
        relative = s[:-1] * s[-1]
        choices = []
        invalid_groups = []
        for group, (lo, hi) in enumerate(zip(offsets[:-1], offsets[1:])):
            chain = relative[int(lo) - group:int(hi) - group - 1]
            if np.any(chain[1:] > chain[:-1]):
                invalid_groups.append(group + 1)
            else:
                choices.append(int(lo) + int(np.count_nonzero(chain == 1)))
        strict = not invalid_groups
        row = {"return_index": index, "energy": int(energy), "residual": residual,
               "strict": strict, "invalid_groups": invalid_groups}
        if residual < 0 or (not strict and residual < illegal_gap):
            return _invalid(family, f"ENERGY_CERTIFICATE_AT_ROW_{index}", "CONTRACT_ERROR")
        if choices:
            candidate = min(choices, key=lambda c: (q[c], c))
            value = float(values[candidate])
            regret = value - float(values[winner])
            decoded = {"candidate_index": candidate, "id": int(ids[candidate]), "vhat": value,
                       "regret": regret, "exact": bool(ids[candidate] == ids[winner])}
            if strict:
                row.update(decoded)
                row["regret_le_0.1"] = regret <= 0.1
                if (minimum_d[candidate] < 0 or residual < minimum_d[candidate]
                        or row["exact"] != row["regret_le_0.1"]):
                    return _invalid(family, f"DECODER_CERTIFICATE_AT_ROW_{index}", "CONTRACT_ERROR")
            else:
                row["partial_only"] = decoded
        rows.append(row)
    primary, secondary = choose_strict(rows)
    return {"family": family, "status": "VALID_COMPLETED", "rows": rows, "primary": primary,
            "secondary": secondary, "strict_count": sum(row["strict"] for row in rows),
            "forecast": forecast(family, primary["residual"] if primary else None)}


def _history_ids():
    path = Path(__file__).resolve().parents[1] / "p2/tasks.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        return {row["result_id"] for row in csv.DictReader(stream) if row["result_id"]}


def slot_records(records):
    """Place received records in planned order; the first distinct server ID owns its slot."""
    unexpected = set(records) - set(SLOTS)
    if unexpected:
        raise ValueError(f"Unknown formal slots: {sorted(unexpected)}")
    seen = _history_ids()
    rows = []
    for slot in SLOTS:
        rec = records.get(slot, {})
        family = FAMILY[slot]
        status = rec.get("status", "NOT_STARTED")
        if status not in STATES or rec.get("family", family) != family:
            raise ValueError(f"Incorrect slot identity or lifecycle status at {slot}")
        tid = rec.get("task_id")
        if tid is not None and (not isinstance(tid, str) or not tid.strip()):
            raise ValueError(f"Malformed server ID at {slot}")
        if tid:
            if tid in seen:
                status = "DUPLICATE"
            seen.add(tid)
        outcome = rec.get("outcome")
        if status == "VALID_COMPLETED":
            if not tid or not isinstance(outcome, dict) or outcome.get("family") != family:
                status = "INVALID_RETURN"
            elif outcome.get("status") in {"INVALID_RETURN", "CONTRACT_ERROR"}:
                status = outcome["status"]
            elif outcome.get("status") != status or not outcome.get("rows"):
                status = "INVALID_RETURN"
        primary = outcome["primary"] if status == "VALID_COMPLETED" else None
        rows.append({"slot": slot, "family": family, "status": status, "task_id": tid,
                     "primary": primary, "secondary": outcome["secondary"] if status == "VALID_COMPLETED" else None,
                     "forecast": forecast(family, primary["residual"] if primary else None)})
    return rows


def summarize(records):
    rows = slot_records(records)
    rounds = []
    prior_high = {}
    for row in rows:
        high = row["forecast"] == "WORSE_THAN_SINGLE_SA"
        row["prediction_mismatch"] = bool(high and prior_high.get(row["family"], False))
        prior_high[row["family"]] = high
    for start in range(0, 9, 3):
        group = rows[start:start + 3]
        complete = all(row["status"] == "VALID_COMPLETED" for row in group)
        strict = complete and all(row["primary"] is not None for row in group)
        joint = strict and all(row["primary"]["exact"] for row in group)
        agg = min((row["primary"] for row in group), key=lambda p: (p["vhat"], p["id"])) if strict else None
        rounds.append({"round": start // 3 + 1, "complete": complete, "strict_coverage": strict,
                       "joint_exact": joint, "observed_quality_failure": complete and not joint,
                       "max_slice_regret": max(row["primary"]["regret"] for row in group) if strict else None,
                       "aggregate_id": agg["id"] if agg else None,
                       "aggregate_exact": agg["id"] == GLOBAL_WINNER_ID if agg else None,
                       "aggregate_regret": agg["vhat"] - 1.839047051618571 if agg else None})
    k = sum(r["joint_exact"] for r in rounds)
    completed = sum(r["complete"] for r in rounds)
    return {"slots": rows, "rounds": rounds, "achieved": k, "planned_rounds": 3,
            "completed_rounds": completed, "achieved_per_planned": k / 3,
            "achieved_per_completed": k / completed if completed else None,
            "max_observed_regret_by_family": {
                f: max((row["primary"]["regret"] for row in rows if row["family"] == f and row["primary"]),
                       default=None) for f in SLICES}}


def _billing_status(bill):
    if not isinstance(bill, dict):
        return "PAUSE_UNVERIFIED_BILLING"
    before, after = bill.get("before"), bill.get("after")
    for snapshot in (before, after):
        if (not isinstance(snapshot, dict) or set(snapshot) != {"550", "1000"}
                or any(type(n) is not int or n < 0 for n in snapshot.values())):
            return "PAUSE_UNVERIFIED_BILLING"
    if after["1000"] < before["1000"]:
        return "PAUSE_1000_DEBIT"
    if (bill.get("attributable") is not True or before["550"] - after["550"] != 1
            or before["1000"] != after["1000"]):
        return "PAUSE_UNVERIFIED_BILLING"
    return "OK"


def ledger_gate(next_slot, records, now):
    """Pure gate for an already verified experiment. Freeze begins before F01."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timezone-aware observation time required")
    if now >= STOP:
        return "STOP_DEADLINE"
    if next_slot not in SLOTS:
        return "STOP_NONFORMAL_SLOT"
    rows = slot_records(records)
    i = SLOTS.index(next_slot)
    if any(row["status"] != "NOT_STARTED" or row["task_id"] for row in rows[i:]):
        return "STOP_RETRY_OR_OUT_OF_ORDER"
    for row in rows[:i]:
        slot = row["slot"]
        bill = _billing_status(records.get(slot, {}).get("billing"))
        if bill != "OK":
            return bill
        if not row["task_id"] or row["status"] not in {"CREATED", "PENDING", "RUN_FAILED", "VALID_COMPLETED"}:
            return "PAUSE_TECHNICAL"
        if slot == "F01" and row["status"] != "VALID_COMPLETED":
            return "WAIT_FIRST_RETURN_INTEGRITY"
    return "READY_OFFLINE"


def creation_gate(anchor, next_slot, records, now, anchor_repo=None):
    """Read-only preflight. Always verifies the original Git receipt before the ledger."""
    if not isinstance(anchor, str) or not re.fullmatch("[0-9a-f]{40}", anchor):
        raise ValueError("Provide the first externally recorded full Git anchor")
    verify = Path(__file__).resolve().with_name("verify.py")
    args = [sys.executable, "-B", str(verify), "--anchor", anchor]
    if anchor_repo is not None:
        args.extend(["--anchor-repo", str(anchor_repo)])
    subprocess.run(args, check=True)
    return ledger_gate(next_slot, records, now)
