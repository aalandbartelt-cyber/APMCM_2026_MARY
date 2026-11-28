"""Resume H04 unstarted blocks in fresh OS processes; never rerun completed samples."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import negative_control as base

OUT = base.OUT / 'initialization_recovery'
SPECS = [(s, b) for b in range(2, 5) for s in ['real', 'zero']]

def prepare():
    OUT.mkdir(exist_ok=False)
    for name in ['matrices.npz', 'blocks.json']:
        (OUT / name).symlink_to(base.OUT / name)
    for s, b in SPECS:
        assert not (base.OUT / f'{s}_{b:02d}' / 'raw.jsonl').exists()
    receipt = dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        reason='Reused worker attempted license initialization after its requests transport had been disabled. Six blocks failed before SA initialization; four completed blocks are retained without rerun.',
        specs=SPECS, completed_original_samples=400, remaining_samples=600,
        change='One fresh OS process per block; unchanged original job function, matrices, seeds, temperature, decoder.',
        original_code_sha256=hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest(),
        recovery_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        hardware_calls=0, fits=0)
    (OUT / 'recovery_registration.json').write_text(json.dumps(receipt, indent=2))

def child(spec):
    s, b = spec
    with (OUT / f'{s}_{b:02d}.log').open('x') as stream:
        r = subprocess.run([sys.executable, __file__, 'child', s, str(b)], stdout=stream, stderr=subprocess.STDOUT)
    return dict(setting=s, block=b, exit_code=r.returncode)

if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'child':
        base.OUT = OUT
        print(json.dumps(base.job((sys.argv[2], int(sys.argv[3])))), flush=True)
    elif sys.argv[1] == 'run':
        with ThreadPoolExecutor(4) as ex:
            rows = list(ex.map(child, SPECS))
        (OUT / 'process_outcomes.json').write_text(json.dumps(rows, indent=2))
        print(json.dumps(rows))
