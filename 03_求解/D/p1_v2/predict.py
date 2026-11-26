"""Composition-only inference from frozen artifacts; no labels and no fitting."""
import argparse
import json
import numpy as np
import pandas as pd
from common import OUT,REG
from models import Bundle,Tree,Calibrated,lgb


def frozen_bundle():
    final=json.loads((OUT/'final_selection.json').read_text())
    b=Bundle.__new__(Bundle);b.routes=list(dict.fromkeys([final['numeric'],final['screen']]));b.models={}
    for name,entry in final['models'].items():
        key=entry['tree_key'];meta=json.loads((OUT/'models'/(key+'.json')).read_text())
        tree=Tree(meta,lgb.Booster(model_file=str(OUT/'models'/(key+'.txt'))) if meta['constant'] is None else None)
        b.models[name]=Calibrated(tree,entry['calibration']['mapping'],entry['calibration']) if 'calibration' in entry else tree
    return final,b


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();d=pd.read_csv(args.input,usecols=['id','A','B','X'])
    d['key']=d.A+'|'+d.B+'|'+d.X
    if not d.key.is_unique:raise ValueError('Duplicate compositions')
    bank=pd.read_pickle(OUT/'features/F4.pkl')
    if not d.key.isin(bank.index).all():raise ValueError('Composition outside registered 52 x 52 x 7 universe')
    final,b=frozen_bundle();p=b.predict(bank.loc[d.key]);r=p[final['numeric']];s=p[final['screen']]
    d['vhat_raw']=r['vhat_raw'];d['vhat']=r['vhat'];d['screen_score']=s['score'];d['screen_event']='V<=2'
    d['regression_model_id']=final['numeric'];d['screen_model_id']=final['screen'];d['model_scope']='P1_train02'
    d.to_csv(args.output,index=False,float_format='%.17g')
    print(json.dumps(dict(rows=len(d),fitting=False,physical_labels_read=False)))


if __name__=='__main__':main()
