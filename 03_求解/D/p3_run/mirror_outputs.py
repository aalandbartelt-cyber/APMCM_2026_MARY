"""Mirror local analysis and raw spin payloads, keeping signed transport responses private."""
from pathlib import Path
import subprocess
import shutil

import lane_a as lane

DEST = Path("/mnt/d/上海大学__/26亚太杯英文赛")

def rsync(source, target, *args):
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rsync","-rt","--omit-dir-times",*args,str(source)+"/",str(target)+"/"],check=True)

def sync():
    if not (DEST/"codex").is_dir():
        raise FileNotFoundError("Competition D mirror is unavailable")
    rel = Path("artifacts/p3_run")
    src,dst = lane.ROOT/rel,DEST/rel
    src_a,dst_a=src/"A",dst/"A"
    for folder in ("B","verify","completed_comparison","snapshot_comparison"):
        if (src/folder).is_dir():
            rsync(src/folder,dst/folder)
    for folder in ("current","history","snapshot_20261129T2100"):
        if (src_a/folder).is_dir():
            rsync(src_a/folder,dst_a/folder)
    shutil.copy2(src_a/"state.json",dst_a/"state.json")
    for slot in lane.protocol.SLOTS:
        folder=src_a/slot
        if folder.is_dir():
            rsync(folder,dst_a/slot,"--include=/result.pkl","--include=/vectors.npy","--include=/created.json",
                  "--include=/create_intent.json","--include=/slot_intent.json","--exclude=*")
    code = Path("03_求解/D/p3_run")
    rsync(lane.ROOT/code,DEST/code,"--exclude=__pycache__")
    for name in ("P3_SOLVE_RESULTS.md","P3_SA_BASELINE_RESULTS.md"):
        report=lane.ROOT/"codex"/name
        if report.exists():
            shutil.copy2(report,DEST/"codex"/name)

if __name__ == "__main__":
    sync()
