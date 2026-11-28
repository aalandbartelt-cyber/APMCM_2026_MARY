"""Create an evidence-only Git bundle and test both project and shared checkouts."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def git(*args,cwd=ROOT,out=True):
    return subprocess.check_output(['git',*map(str,args)],cwd=cwd,text=True).strip()

def run():
    share=Path(sys.argv[1]).resolve()
    share.mkdir(parents=True,exist_ok=True)
    bundle=share/'P2_evidence_20261128.bundle'
    commit=git('log','-1','--format=%H','--','evidence/p2')
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td)
        private=temp/'project';git('clone','-q','--no-local',ROOT,private)
        git('checkout','-q','--detach',commit,cwd=private)
        args=[sys.executable,'-I','-B','evidence/p2/verify.py']
        def verify(d):
            return subprocess.check_output(args,cwd=d,text=True,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'}).strip().splitlines()
        project_pass=verify(private)
        src=temp/'export';src.mkdir()
        shutil.copytree(private/'evidence/p2',src/'evidence/p2')
        git('init','-q','-b','p2-evidence',cwd=src)
        git('config','user.name','P2 evidence archive',cwd=src)
        git('config','user.email','evidence@localhost.invalid',cwd=src)
        git('config','core.autocrlf','false',cwd=src)
        (src/'.gitattributes').write_text('* -text\n')
        git('add','.',cwd=src)
        git('commit','-qm','Freeze evidence from project '+commit,cwd=src)
        temporary=temp/'share.bundle'
        git('bundle','create',temporary,'--all',cwd=src)
        if bundle.exists():raise FileExistsError(bundle)
        with bundle.open('xb') as f,temporary.open('rb') as i:shutil.copyfileobj(i,f)
        dst=temp/'shared-checkout';git('clone','-q',bundle,dst);shared_pass=verify(dst)
        assert project_pass==shared_pass and git('status','--porcelain',cwd=dst)==''
        receipt=dict(source_commit=commit,shared_bundle=bundle.name,sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),evidence_commit=git('rev-parse','HEAD',cwd=dst),branch='p2-evidence',shared_clone_verified=True,project_clone_verified=True,verify_output=shared_pass,tracked_files=len(git('ls-files',cwd=dst).splitlines()),scope='fresh local replay of D-drive distribution; third-party access or independent execution not asserted')
        (ROOT/'codex/p2_zero/distribution_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        shutil.copyfile(ROOT/'codex/p2_zero/distribution_receipt.json',share/'distribution_receipt.json')
        print(json.dumps(receipt))
if __name__=='__main__':run()
