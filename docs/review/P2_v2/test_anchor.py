"""Independent regression test: deleting/recreating a receipt cannot replace its anchor."""
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'03_求解/D/p2_v2'))
import p2_common

with tempfile.TemporaryDirectory(prefix='p2-anchor-contract-') as directory:
    root=Path(directory)
    def git(*args):return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.DEVNULL,text=True).strip()
    git('init','-q');matrix=root/'matrix.bin';matrix.write_bytes(b'original matrix')
    receipt=root/p2_common.RECEIPT;receipt.parent.mkdir(parents=True)
    data=dict(code_hashes={},input_hashes={'matrix.bin':hashlib.sha256(matrix.read_bytes()).hexdigest()},configurations=[],sa_matrices=[],selected=None)
    receipt.write_text(json.dumps(data));git('add','.');git('-c','user.name=Contract Test','-c','user.email=test@example.invalid','commit','-qm','toy anchor')
    original=git('rev-parse','HEAD')
    with patch.object(p2_common,'ROOT',root):
        assert p2_common.anchor(original)['selected'] is None
        old=receipt.read_bytes();receipt.unlink();receipt.write_text(json.dumps(dict(data,selected='forged')))
        git('add','.');git('-c','user.name=Contract Test','-c','user.email=test@example.invalid','commit','-qm','later toy receipt')
        try:p2_common.anchor(original)
        except AssertionError:pass
        else:raise AssertionError('Later receipt replaced old anchor')
        receipt.write_bytes(old);matrix.write_bytes(b'changed matrix')
        try:p2_common.anchor(original)
        except AssertionError:pass
        else:raise AssertionError('Changed matrix was accepted')
        try:p2_common.anchor('HEAD')
        except AssertionError:pass
        else:raise AssertionError('Mutable symbolic anchor was accepted')
print('PASS: exact committed receipt only; delete/recreate, later receipt, changed matrix, symbolic HEAD rejected.')
