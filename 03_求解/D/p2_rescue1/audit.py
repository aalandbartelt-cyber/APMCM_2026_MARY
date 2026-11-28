"""One bounded, post-hoc registered penalty revision. Never calls a solver."""
import sys
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '03_求解/D/p2_v2'))
from p2_common import read, sha, write_new, now
from representation import construct, quantize, legal_energies, metrics
from checker import direct, certify

REG = ROOT / 'codex/p2_rescue1'
OUT = ROOT / 'artifacts/p2_rescue1'

def main():
    frozen = read(REG / 'freeze.json')
    assert sha(ROOT / 'codex/P2_RESCUE_AMENDMENT_20261128.md') == frozen['declaration_sha256']
    for name, value in frozen['protected'].items():
        assert sha(ROOT / name) == value, name
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    for name in ['codex/p2_rescue1/freeze.json', 'codex/P2_RESCUE_AMENDMENT_20261128.md']:
        assert subprocess.check_output(['git', 'show', f'{commit}:{name}']) == (ROOT / name).read_bytes()
    assert not (REG / 'selection_receipt.json').exists()
    dest = OUT / 'representations'
    dest.mkdir()
    z = np.load(ROOT / 'artifacts/p23_v2/pool_11.npz')
    W, mask = z['vhat'][:, :, 0], z['allowed'][:, :, 0]
    keys = np.array([[f'{a}|{b}|NO2' for b in z['B']] for a in z['A']])
    t = frozen['theta'][1]
    assert t['pool'] == '11'
    lam = t['lambda_rescue']
    rows = []
    for encoding in ['raw', 'rc']:
        ident = f'11-{encoding}-N8-rescue1'
        J, meta, Q = construct(W, mask, encoding, ratio=lam / (t['R'] or 1.))
        assert abs(meta['lam'] - lam) < 1e-13
        target = np.where(mask, W - meta['m'], meta['encoding_scale'])
        ferror = float(np.max(np.abs(legal_energies(J, *mask.shape) + meta['offset'] - target)))
        assert ferror < 1e-8 * max(1., t['R'])
        K, factor = quantize(J)
        p = dest / f'{ident}.npz'
        with p.open('xb') as stream:
            np.savez_compressed(stream, J=K, W=W, allowed=mask, keys=keys)
        na, nb = mask.shape
        X = np.zeros((na * nb, na + nb), np.int64)
        for i in range(na):
            for j in range(nb):
                X[i * nb + j, i] = X[i * nb + j, na + j] = 1
        E = direct(K, X).reshape(mask.shape)
        np.testing.assert_array_equal(E, legal_energies(K, na, nb))
        cert = certify(K, mask, node_limit=1000000, seconds=600)
        write_new(dest / f'{ident}.certificate.json', cert)
        stat = metrics(W, mask, E, keys)
        row = dict(id=ident, encoding=encoding, meta=meta, quant_scale=factor,
                   float_equivalence_max_abs=ferror, onehot_checked=int(E.size),
                   allowed_count=int(mask.sum()), certificate=cert['status'],
                   certificate_reason=cert['reason'], matrix_file=str(p.relative_to(ROOT)),
                   matrix_sha256=sha(p), **stat)
        # Fixed-scale zero-business negative control; mask and penalty unchanged.
        C0 = np.where(mask, 0., meta['encoding_scale'])
        u = C0.min(axis=1) if encoding == 'rc' else np.zeros(na)
        v = (C0-u[:, None]).min(axis=0) if encoding == 'rc' else np.zeros(nb)
        Q0 = Q.copy(); Q0[:na, na:] = C0-u[:, None]-v[None, :]
        Q0[np.arange(na), np.arange(na)] = u-lam
        Q0[na+np.arange(nb), na+np.arange(nb)] = v-lam
        off = Q0.copy(); np.fill_diagonal(off, 0)
        J0 = np.zeros_like(J); J0[:-1, :-1] = -(off+off.T)/8
        J0[:-1, -1] = J0[-1, :-1] = -(np.diag(Q0)/4+(off+off.T).sum(axis=1)/8)
        K0 = np.rint(J0*factor).astype(np.int64)
        neg = dict(scale_fixed=factor, matrix_equal=bool(np.array_equal(K, K0)),
                   changed_entries=int(np.count_nonzero(K-K0)),
                   onehot_energy_equal=bool(np.array_equal(E, direct(K0, X).reshape(mask.shape))))
        write_new(dest / f'{ident}.negative_control.json', neg)
        pd.DataFrame(dict(key=keys.ravel(), allowed=mask.ravel(), vhat=W.ravel(), energy=E.ravel())).to_csv(dest/f'{ident}.energies.csv', index=False, float_format='%.17g')
        write_new(dest / f'{ident}.json', row)
        rows.append(row)
        print(ident, cert['status'], 'worst regret', row['worst_ground_regret'], flush=True)
    eligible = sorted([r for r in rows if r['certificate']=='CERTIFIED' and r['worst_ground_regret']<=.1],
                      key=lambda r: (r['worst_ground_regret'], -r['top20_min'], r['id']))
    selected = eligible[0] if eligible else None
    obj = dict(time=now(), preregistration_type='POST_HOC_AUDIT_DRIVEN_AMENDMENT',
               amendment_commit=commit, old_receipt_sha256=frozen['old_receipt_sha256'],
               status='SELECTED' if selected else 'NO_ELIGIBLE_CONFIGURATION',
               selected=selected['id'] if selected else None,
               selected_matrix_sha256=selected['matrix_sha256'] if selected else None,
               configurations=rows, new_fit_count=0, new_sa_count=0, cim_submissions=0,
               selection_order=['CERTIFIED', 'worst_original_regret<=0.1', 'min_worst_regret', 'max_top20_lower_retention', 'id'],
               code_hashes={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__), ROOT/'03_求解/D/p2_v2/representation.py', ROOT/'03_求解/D/p2_v2/checker.py', ROOT/'03_求解/D/p2_v2/p2_common.py']},
               input_hashes={str(p.relative_to(ROOT)):sha(p) for p in [REG/'freeze.json', ROOT/'codex/P2_RESCUE_AMENDMENT_20261128.md', ROOT/'artifacts/p23_v2/pool_11.npz']})
    write_new(REG/'selection_receipt.json', obj)
    print('selection', obj['selected'], 'receipt SHA256', sha(REG/'selection_receipt.json'), flush=True)

if __name__ == '__main__':
    main()
