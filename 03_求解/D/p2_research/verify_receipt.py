"""Read-only hash verification of the research archive; never invokes a solver."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3]
receipt=json.loads((ROOT/'codex/p2_research_receipt/receipt.json').read_text())
bad=[]
for name,digest in receipt['files'].items():
    p=ROOT/name
    if not p.is_file():bad.append([name,'missing'])
    elif hashlib.sha256(p.read_bytes()).hexdigest()!=digest:bad.append([name,'changed'])
print(json.dumps(dict(checked=len(receipt['files']),failures=bad,
    hardware_authorized=receipt['hardware_authorized'],fit_authorized=receipt['fit_authorized']),indent=2))
raise SystemExit(bool(bad))
