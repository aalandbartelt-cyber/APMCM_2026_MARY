"""Copy already frozen research inputs and independently recheck; no new solve."""
from pathlib import Path
import json
import sys
from contract import ROOT, INPUT, sha


def main():
    source = ROOT / "artifacts/p2_research_20261128/short_H05/40_real"
    INPUT.mkdir(parents=True, exist_ok=False)
    for name in ["matrix.npz", "blocks.json"]:
        with (INPUT / name).open("xb") as f:
            f.write((source / name).read_bytes())
        assert sha(INPUT / name) == sha(source / name)
    sys.path.insert(0, str(ROOT / "03_求解/D/p2_research"))
    from validation_checker import certify
    cert = certify(INPUT)
    assert cert["G1"] == cert["G2"] == "CERTIFIED"
    assert cert["batch_ground_worst_regret"] == 0 and cert["spins"] == 490
    cert["purpose"] = "Read-only independent recheck of unchanged research matrix before P01"
    cert["original_matrix"] = str((source / "matrix.npz").relative_to(ROOT))
    with (ROOT / "codex/p2_cim_go/certificate.json").open("x") as f:
        json.dump(cert, f, indent=2)
        f.write("\n")
    print(json.dumps({k: cert[k] for k in ["G1", "G2", "spins", "max_J", "illegal_gap", "batch_ground_worst_regret"]}))


if __name__ == "__main__":
    main()
