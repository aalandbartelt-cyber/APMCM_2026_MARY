"""End-to-end orchestration, preserving an actual weight freeze before 04 export."""
import json
from common import OUT,dump,sha,now
from experiment import Experiment


def freeze_weights():
    dest=OUT/'weights_freeze_pre04.json'
    if dest.exists():
        record=json.loads(dest.read_text())
        assert record['04_export_already_exists'] is False
        for name,digest in record['weights'].items():assert sha(OUT/'models'/name)==digest
        return
    assert not (OUT/'predictions/04_P1_train02_predictions.csv').exists()
    final=json.loads((OUT/'final_selection.json').read_text());weights={}
    for m in final['models'].values():
        for ext in ('.json','.txt'):
            path=OUT/'models'/(m['tree_key']+ext)
            if path.exists():weights[path.name]=sha(path)
    dump(dest,{'time':now(),'04_export_already_exists':False,'weights':weights})


def main():
    e=Experiment();e.main();e.stress();e.choose_final();freeze_weights()
    e.diagnostics();e.export_predictions()


if __name__=='__main__':main()
