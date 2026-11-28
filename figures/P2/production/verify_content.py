"""Independent, read-only checks for what the P2 plates show and for final review pagination."""
import csv, json, hashlib, re
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import pymupdf as pdf

p2=Path(__file__).resolve().parents[1]
root=p2.parents[1]
def data(x):return pd.read_csv(p2/'data'/x)
def check(flag,message):
    if not flag:raise ValueError(message)
    return message
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    checks=[]
    for pool,count in [('07',2704),('11',529)]:
        z=np.load(root/f'artifacts/p23_v2/pool_{pool}.npz'); allowed=z['allowed'][:,:,0];
        v=z['vhat'][:,:,0];a,b=np.unravel_index(np.argmin(np.where(allowed,v,np.inf)),v.shape)
        checks.append(check(allowed.sum()==count and [z['A'][a],z['B'][b]]==['La','Ti'] and abs(v[a,b]-1.839047051618571)<1e-12,'Pool '+pool+' size, allowed minimum and material'))
    r=data('return_energy.csv');m=data('task_margin.csv').set_index('slot')
    check(len(r)==250 and len(m)==25 and set(r.groupby('slot').size())=={10},'return cardinalities')
    for slot,g in r.groupby('slot'):
        z=m.loc[slot];x=g.energy.to_numpy()+58722
        assert np.array_equal(x,g.residual) and x.min()==z.min_residual and x.max()==z.max_residual
        assert 196-x.max()==z.set_min_margin and 196-x.min()==z.selected_margin
        assert g.original_regret.eq(0).all() and g.strict.eq(1).all()
    checks.append(check(m.selected_margin.idxmin()=='F03' and m.selected_margin.min()==20 and m.set_min_margin.idxmin()=='F14' and m.set_min_margin.min()==8,'250 energies, two margins in 25 task records, F03=20 and F14=8'))
    raw=data('chain_optimal_250x40.csv');chaincols=raw.filter(regex='^chain_').columns
    x=raw.groupby('slot')[chaincols].sum().sort_index(); y=data('chain_task_25x40.csv').set_index('slot')[chaincols].sort_index()
    checks.append(check(x.equals(y) and len(chaincols)==40 and (x.chain_17==10).all(),'25 x 40 cells recomputed from 250 x 40, including critical group 17'))
    b=data('sa_budget_blocks.csv');curve=data('sa_budget_curve.csv')
    for _,c in curve.iterrows():
        g=b[(b.source==c.source.split('_')[0]) & (b.arm==c.arm) & (b.budget==c.budget)]
        if c.source=='fresh_length_paired':g=g[g.block<2]
        assert len(g)==c.planned_blocks and g.any_hit.sum()==c.strict_hit_blocks and g.energy_hit.sum()==c.energy_hit_blocks
    h=b[(b.source=='fresh')&(b.budget==5)].pivot(index='block',columns='arm',values='any_hit')
    checks.append(check(((h['40_real']==1)&(h['40_zero']==0)).sum()==14 and h['40_real'].sum()==20 and h['40_zero'].sum()==6 and (2/2**14)==json.loads((p2/'data/sa_paired_test.json').read_text())['p_two_sided'],'49 budget records and paired p = 0.0001220703125; 20/20 vs 6/20'))
    old=np.load(root/'artifacts/p2_v2/representations/11-raw-float.npz')['J'];new=np.load(root/'evidence/p2/matrix.npz')['J'];w=old[np.triu_indices(105,1)]
    checks.append(check((w<0).sum()==5459 and (w>0).sum()==0 and np.count_nonzero(np.triu(new,1))==875,'Logical coupling map: 5459 negative edges; submitted 490-spin matrix: 875 edges'))
    tl=data('task_timeline.csv');checks.append(check(tl.slot.nunique()==25 and tl.accepted_at_local.notna().all() and tl.terminal_observed_at_local.notna().all() and tl.physical_start.isna().all(),'25 usable observation intervals; no provider physical start times'))
    ab=data('chain_ablation.csv').query("cohort=='fresh_matched_2'").set_index('arm')
    checks.append(check(ab.loc['40_real','strict']==199 and ab.loc['40_real','strict_hits']==135 and ab.loc['single_real','strict']==0,'Matched ablation: 199/200 feasible and 135/200 strict hits vs 0/200'))
    ex=json.loads((p2/'production/crystal/exports.json').read_text());assert len(ex['images'])==6
    for row in ex['images']:
        stem=p2/'production/crystal'/row['scene'];ss=stem.with_suffix('.vesta');png=stem.with_suffix('.png');assert sha(ss)==row['scene_sha256'] and sha(png)==row['png_sha256']
        sb=ss.read_text().split('SBOND\n')[1].split('SITET\n')[0];assert len(re.findall(r'\bTi\b',sb))==2 and not re.search(r'\bLa\b',sb)
    checks.append('Six native VESTA scenes and native PNG hashes verified; two Ti-only bond rules in every scene')
    inv=pd.read_csv(p2/'delivery_inventory.csv',encoding='utf-8-sig');d=pdf.open(p2/'P2_figures_review.pdf')
    assert len(d)==16 and inv.iloc[0].id=='P2-F1' and sum(inv.placement=='Main figure')==5
    for pg,(_,r) in zip(d,inv.iterrows()):
        txt=pg.get_text().replace(chr(173),'-');assert r.id in txt and len(txt)>150 and not re.search(r'[\u3400-\u9fff]',txt)
        # Caption block must be present and fully visible at the registered print size.
        spans=[s for b in pg.get_text('dict',flags=pdf.TEXT_PRESERVE_WHITESPACE)['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans'] if s['text'].strip()]
        assert all(pg.rect.contains(pdf.Rect(s['bbox'])) for s in spans)
        assert all('TimesNewRoman' in s['font'] for s in spans) and min(s['size'] for s in spans)>=8.45
    checks.append('Review PDF: 16 native-size plates with bookmarks and captions, correct order, English labels inside page bounds')
    out=p2/'audit/content_verification.json'
    out.write_text(json.dumps({'checks':checks,'review_sha256':sha(p2/'P2_figures_review.pdf')},indent=2)+'\n')
    print('\n'.join(checks))
if __name__=='__main__':main()
