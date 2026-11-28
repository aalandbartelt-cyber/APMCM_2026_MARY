"""Join actual service tasks and independent 100-restart blocks by family and round."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import os

import lane_a as lane


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(snapshot):
    a = lane.A / ("snapshot_20261129T2100" if snapshot else "current")
    b = lane.ROOT / "artifacts/p3_run/B/formal"
    out = lane.A.parent / ("snapshot_comparison" if snapshot else "completed_comparison")
    files = [a/"summary.json", a/"slots.csv", a/"rounds.csv", b/"budget_prefixes.csv",b/"vectors.sha256"]
    fingerprints = {str(f.relative_to(lane.ROOT)):sha(f) for f in files}
    if out.exists():
        sources = json.loads((out/"sources.json").read_text())
        if sources["sources_sha256"] != fingerprints:
            raise RuntimeError("Existing comparison uses different source revisions")
        if sha(out/"main.csv") != sources["hash_main"]:
            raise RuntimeError("Existing main table differs from its recorded hash")
        return out
    summary = json.loads(files[0].read_text())
    with files[1].open() as f:
        slots = list(csv.DictReader(f))
    with files[3].open() as f:
        blocks = {(r["family"],int(r["block"])):r for r in csv.DictReader(f) if int(r["budget"]) == 100}
    if len(slots) != 9 or len(blocks) != 9:
        raise RuntimeError("Expected nine planned slots and nine observed SA blocks")
    if not snapshot and any(r["status"] in {"CREATED","PENDING","NOT_STARTED"} for r in slots):
        raise RuntimeError("Use an actual cutoff snapshot for incomplete observation")
    cols = ("status","task_id","strict_count","return_index","energy","residual","id","regret","exact",
            "forecast","prediction_mismatch","exists_strict_hit","min_strict_regret")
    rows = []
    for i,r in enumerate(slots):
        n = i//3+1
        block = blocks[r["family"],n]
        row = {"round":n,"family":r["family"],"slot":r["slot"]}
        row.update({"service_"+k:r[k] for k in cols})
        row.update({"sa_"+k:v for k,v in block.items() if k not in {"family","block"}})
        rows.append(row)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        draft = Path(tmp)/"deliverable"
        draft.mkdir()
        with (draft/"main.csv").open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        lane.write_json(draft/"sources.json",dict(sources_sha256=fingerprints,
             state_revision=summary["state_revision"],cutoff=lane.protocol.SNAPSHOT.isoformat() if snapshot else None,
             service_unit="one optimization-service task; platform-filtered return set",
             sa_unit="one independently registered block of 100 local restarts",
             selection="minimum strict integer energy; preserve original order on ties",
             joint_primary="exact primary in each of the three slices within the same service round",
             sample_rate_comparison=False,hash_main=sha(draft/"main.csv")),immutable=True)
        os.rename(draft,out)
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",action="store_true")
    print(build(p.parse_args().snapshot))
