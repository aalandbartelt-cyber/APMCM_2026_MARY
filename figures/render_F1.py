"""F1 data audit, adapted from the mandatory APMCM D plotting template.

Only frozen artifacts are read; no model is loaded or fitted. All generated
files, including caches and display aggregates, remain under figures/.
"""
from pathlib import Path
import os
import sys
import json
import csv
import gzip
import hashlib
import importlib.util
import shutil
from collections import Counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'F1'
os.environ['MPLCONFIGDIR'] = str(HERE / '.cache/matplotlib')
os.environ['MPLBACKEND'] = 'Agg'
sys.dont_write_bytecode = True

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib import patheffects
from matplotlib.text import Text
from matplotlib.font_manager import findfont, FontProperties
from PIL import Image, ImageCms, PngImagePlugin

SOURCE = Path('/mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm')
TEMPLATE = SOURCE / 'assets/apmcm_d_plot_templates.py'
spec = importlib.util.spec_from_file_location('apmcm_d_plot_templates', TEMPLATE)
template = importlib.util.module_from_spec(spec)
spec.loader.exec_module(template)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def load_audit_data():
    approved = json.loads((HERE/'figure_inventory_approval.json').read_text())
    assert approved['status'] == 'approved_for_sequential_rendering'
    assert sha(HERE/'palette_frozen.json') == approved['palette_frozen_sha256']
    source_record = json.loads((HERE/'figure_inventory_sources.json').read_text())['sources_and_filters']['F1']
    for item in source_record['sources']:
        assert sha(ROOT/item['path']) == item['sha256'], item['path']
    records = []
    for fold in range(5):
        with gzip.open(ROOT/f'artifacts/p1_v21/domains/main_outer_{fold}.csv.gz', 'rt') as stream:
            records.extend(row for row in csv.DictReader(stream) if row['route'] == 'H-soft')
    # splits.json stores persistent sample IDs, while row_index is the local
    # position inside the 02 table. Check both identities; never equate them.
    rows = {int(row['id']): row for row in records}
    assert len(records) == len(rows) == 11256
    assert {int(row['row_index']) for row in records} == set(range(11256))
    assert len({row['key'] for row in records}) == 11256
    ab_counts = Counter(row['ab'] for row in records)
    assert len(ab_counts) == 1608 and set(ab_counts.values()) == {7}
    splits = json.loads((ROOT/'artifacts/p1_v21/splits.json').read_text())
    all_indices = set(rows); outer_tests = []; fold_records = []
    for fold in range(5):
        split = splits[f'main_outer_{fold}']
        train, test = set(split['train']), set(split['test'])
        assert train.isdisjoint(test) and train | test == all_indices
        train_ab = {rows[i]['ab'] for i in train}; test_ab = {rows[i]['ab'] for i in test}
        assert train_ab.isdisjoint(test_ab)
        assert test == {i for i, row in rows.items() if row['domain'] == f'main_outer_{fold}'}
        inner_tests = []
        for inner in range(3):
            ss = splits[f'main_inner_{fold}_{inner}']
            tr, ev = set(ss['train']), set(ss['test'])
            assert tr | ev == train and tr.isdisjoint(ev)
            assert {rows[i]['ab'] for i in tr}.isdisjoint({rows[i]['ab'] for i in ev})
            inner_tests.extend(ev)
        assert len(inner_tests) == len(set(inner_tests)) == len(train)
        outer_tests.extend(test)
        fold_records.append(dict(fold=fold+1, train_rows=len(train), test_rows=len(test),
            train_AB=len(train_ab), test_AB=len(test_ab), AB_overlap=0, inner_splits_checked=3))
    assert len(outer_tests) == len(set(outer_tests)) == 11256
    v = np.array([float(row['V']) for row in records])
    gap = np.array([float(row['gap']) for row in records])
    assert np.isfinite(v).all() and np.isfinite(gap).all() and (gap >= 0).all()
    eps = json.loads((ROOT/'artifacts/p1_v21/experiment_freeze.json').read_text())['eps']
    assert eps == 2 and np.sum(v <= eps) == 128 and np.sum(v == 0) == 0
    assert np.sum(gap == 0) == 10824 and np.sum(gap > 0) == 432
    assert np.all(gap[v <= eps] > 0)
    return v, gap, fold_records, source_record


def save_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True)
    v, gap, folds, source_record = load_audit_data()
    cfg = json.loads((HERE/'palette_frozen.json').read_text())
    colors = {r['id']: r['hex'] for r in cfg['roles']}
    ink, edge = cfg['ink'], cfg['outline']
    bins = np.arange(0, 111, 5, dtype=float)
    metal = np.histogram(v[gap == 0], bins)[0]
    nonmetal = np.histogram(v[gap > 0], bins)[0]
    near_bins = np.linspace(0, 2, 9)
    near = np.histogram(v[v <= 2], near_bins)[0]
    assert int(metal.sum() + nonmetal.sum()) == len(v) and int(near.sum()) == 128
    save_csv(OUT/'F1_histogram_counts.csv', [dict(left=float(bins[i]), right=float(bins[i+1]),
        metal=int(metal[i]), nonmetal=int(nonmetal[i])) for i in range(len(metal))])
    save_csv(OUT/'F1_near_positive_histogram_counts.csv', [dict(left=float(near_bins[i]),
        right=float(near_bins[i+1]), count=int(near[i])) for i in range(len(near))])
    save_csv(OUT/'F1_split_counts.csv', folds)

    template.apply_apmcm_style()
    assert template.use_times_new_roman()
    plt.rcParams.update({'font.size':9, 'axes.titlesize':10, 'axes.labelsize':9,
        'xtick.labelsize':8.5, 'ytick.labelsize':8.5, 'legend.fontsize':8.5,
        'text.color':ink, 'axes.labelcolor':ink, 'axes.edgecolor':edge,
        'xtick.color':ink, 'ytick.color':ink, 'axes.linewidth':.6,
        'axes.grid':False, 'hatch.linewidth':.35, 'pdf.fonttype':42, 'ps.fonttype':42,
        'savefig.bbox':None, 'savefig.dpi':300})
    fig = plt.figure(figsize=(170/25.4, 136/25.4), facecolor='white')

    # (a) Full original-scale distribution with a clearly scoped low-V inset.
    ax = fig.add_axes([.095, .55, .52, .36])
    ax.set_title('(a) V distribution', loc='left', pad=9)
    ax.bar(bins[:-1], metal, width=5, align='edge', color=colors['M'],
           edgecolor=edge, linewidth=.35, hatch='//', label='Metal')
    ax.bar(bins[:-1], nonmetal, bottom=metal, width=5, align='edge', color=colors['N'],
           edgecolor=edge, linewidth=.35, hatch='..', label='Nonmetal')
    ax.set(xlim=(0,110), ylim=(0,3050), xticks=[0,25,50,75,100], yticks=[0,1000,2000,3000],
           xlabel='V', ylabel='Samples')
    ax.tick_params(length=3, pad=3)
    # Each visual encoding has an explicit local key; the inset is a subset,
    # not a third mutually exclusive sample class.
    inset = ax.inset_axes([.59, .60, .38, .32])
    inset.bar(near_bins[:-1], near, width=.25, align='edge', color=colors['P'],
              edgecolor=edge, linewidth=.45)
    threshold = inset.axvline(2, color=colors['W'], ls=':', lw=1.5)
    threshold.set_path_effects([patheffects.Stroke(linewidth=2.1, foreground=edge), patheffects.Normal()])
    inset.set(xlim=(0,2.13), ylim=(0,32), xticks=[0,1,2], yticks=[0,15,30])
    inset.set_title('Near-positive subset\n128 nonmetal samples', fontsize=8.5,
                    loc='center', pad=5, linespacing=1.2)
    inset.set_xlabel('V', fontsize=8.5, labelpad=1)
    inset.set_ylabel('Samples', fontsize=8.5, labelpad=1)
    inset.tick_params(length=2, pad=1.5, labelsize=8.5)
    sample_legend = ax.legend(handles=[
        Patch(facecolor=colors['M'],edgecolor=edge,linewidth=.45,hatch='//',label='Metal: gap = 0'),
        Patch(facecolor=colors['N'],edgecolor=edge,linewidth=.45,hatch='..',label='Nonmetal: gap > 0'),
        Patch(facecolor=colors['P'],edgecolor=edge,linewidth=.45,label='Near-positive: V <= 2'),
        plt.Line2D([],[],color=colors['W'],ls=':',lw=1.5,label='Inset cutoff: V = 2')],
        loc='lower right',bbox_to_anchor=(1,.07),frameon=False,fontsize=8.5,
        handlelength=1.8,handletextpad=.6,labelspacing=.30,borderaxespad=0)
    for line in sample_legend.get_lines():
        line.set_path_effects([patheffects.Stroke(linewidth=2.1,foreground=edge),patheffects.Normal()])

    # (b) Direct counts prevent the narrow nonmetal segment from disappearing.
    comp = fig.add_axes([.72, .55, .26, .36]); comp.set(xlim=(0,1), ylim=(0,1)); comp.axis('off')
    comp.set_title('(b) Composition', loc='left', pad=9)
    comp.text(0,.95,'Training samples: 11,256', fontsize=9, va='top')
    mfrac = np.sum(gap==0) / len(gap)
    comp.add_patch(Rectangle((0,.72),mfrac,.12,facecolor=colors['M'],edgecolor=edge,lw=.6,hatch='//'))
    comp.add_patch(Rectangle((mfrac,.72),1-mfrac,.12,facecolor=colors['N'],edgecolor=edge,lw=.6,hatch='..'))
    for y,c,label,value,hatch in [(.57,colors['M'],'Metal','10,824 (96.16%)','//'),
                                  (.34,colors['N'],'Nonmetal','432 (3.84%)','..')]:
        comp.add_patch(Rectangle((0,y-.02),.14,.07,facecolor=c,edgecolor=edge,lw=.45,hatch=hatch))
        comp.text(.18,y+.015,label,fontsize=9,va='center')
        comp.text(.18,y-.085,value,fontsize=9,va='center')
    comp.text(0,.07,'Zero-V cases: 0',fontsize=9,va='center')

    # (c) Schematic blocks are encoded by pattern and label, not new role colours.
    cv = fig.add_axes([.06,.05,.92,.34]);cv.set(xlim=(0,1),ylim=(0,1));cv.axis('off')
    cv.set_title('(c) Five-fold split of 1,608 A-B pairs',loc='left',pad=11)
    cv.text(.13,.995,'Keep each (A, B) pair in one block.',fontsize=9,va='top')
    # One full-width matrix replaces the separate route-selection flowchart.
    # The three inner folds remain documented in the caption and audit.
    start_x,cell_w,top,cell_h=.13,.169,.72,.125
    for col,fold in enumerate(folds):
        cv.text(start_x+(col+.5)*cell_w,.835,f"Block {col+1}\n{fold['test_AB']} pairs",
                fontsize=8.5,ha='center',va='center',linespacing=1.2)
    for row in range(5):
        cy=top-(row+1)*cell_h
        cv.text(start_x-.015,cy+cell_h/2,f'Fold {row+1}',fontsize=8.5,ha='right',va='center')
        for col in range(5):
            test=row==col
            cv.add_patch(Rectangle((start_x+col*cell_w,cy),cell_w-.004,cell_h-.008,
                facecolor=edge if test else 'white',edgecolor=edge,lw=.45,hatch=None if test else '/'))
            if test:
                cv.text(start_x+(col+.5)*cell_w-.002,cy+cell_h/2-.004,'Evaluate',fontsize=8.5,color='white',ha='center',va='center')
    cv.legend(handles=[
        Patch(facecolor='white',edgecolor=edge,linewidth=.45,hatch='/',label='Training blocks'),
        Patch(facecolor=edge,edgecolor=edge,linewidth=.45,label='Held-out evaluation')],
        loc='upper right',bbox_to_anchor=(.995,1.015),ncol=2,frameon=False,fontsize=8.5,
        handlelength=1.8,handletextpad=.5,columnspacing=1,borderaxespad=0)

    # Inspect real resolved fonts and glyph bounds, then export without cropping.
    fig.canvas.draw(); renderer=fig.canvas.get_renderer(); fw,fh=fig.canvas.get_width_height()
    texts=[t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
    assert all(t.get_text().isascii() for t in texts)
    assert min(t.get_fontsize() for t in texts)>=cfg['minimum_font_pt']
    font_paths={Path(findfont(t.get_fontproperties(),fallback_to_default=False)) for t in texts}
    assert all(FontProperties(fname=p).get_name()=='Times New Roman' for p in font_paths)
    outside=[]
    for t in texts:
        bb=t.get_window_extent(renderer)
        if bb.x0<0 or bb.y0<0 or bb.x1>fw or bb.y1>fh:outside.append(t.get_text())
    assert not outside,outside
    legend_box = sample_legend.get_window_extent(renderer)
    inset_label_box = inset.xaxis.label.get_window_extent(renderer)
    assert legend_box.y1 < inset_label_box.y0, (tuple(legend_box.bounds), tuple(inset_label_box.bounds))
    png=OUT/'F1_data_audit_v3.png';pdf=OUT/'F1_data_audit_v3.pdf'
    fig.savefig(png,dpi=300,facecolor='white',metadata={'Title':'Data audit and AB-blocked validation','Software':'Matplotlib'})
    fig.savefig(pdf,facecolor='white',metadata={'Title':'Data audit and AB-blocked validation','Author':'',
        'Subject':'Observed development data and fixed grouped validation','Keywords':'',
        'Creator':'Matplotlib','CreationDate':None,'ModDate':None})
    plt.close(fig)
    rgb=Image.open(png).convert('RGB');arr=np.asarray(rgb,dtype=float)/255
    linear=np.where(arr<=.04045,arr/12.92,((arr+.055)/1.055)**2.4)
    yy=linear @ [.2126729,.7151522,.0721750]
    gray=np.where(yy<=.0031308,12.92*yy,1.055*np.maximum(yy,0)**(1/2.4)-.055)
    gray=np.rint(np.clip(gray,0,1)*255).astype(np.uint8)
    gray_im=Image.fromarray(np.repeat(gray[:,:,None],3,axis=2))
    icc=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    meta=PngImagePlugin.PngInfo();meta.add_text('Title','Data audit and AB-blocked validation')
    rgb.save(png,dpi=(300,300),icc_profile=icc,pnginfo=meta)
    gray_path=OUT/'F1_data_audit_v3_grayscale.png';gray_im.save(gray_path,dpi=(300,300),icc_profile=icc,pnginfo=meta)
    # Stable links point to the current revision; the rejected revision is archived.
    for source, name in [(png,'F1_data_audit.png'),(pdf,'F1_data_audit.pdf'),
                         (gray_path,'F1_data_audit_grayscale.png')]:
        shutil.copyfile(source, OUT/name)
    with Image.open(png) as im:
        assert all(abs(d-300)<.1 for d in im.info['dpi']); pixels=list(im.size)
    audit=dict(figure='F1',revision=3,status='awaiting_user_figure_review',date='2026-11-27',
        source_files=source_record['sources'],palette_sha256=sha(HERE/'palette_frozen.json'),
        template_sha256=sha(TEMPLATE),template_functions=['apply_apmcm_style','use_times_new_roman'],
        renderer_sha256=sha(Path(__file__)),N=len(v),metal_count=int(np.sum(gap==0)),
        nonmetal_count=int(np.sum(gap>0)),near_positive_count=int(np.sum(v<=2)),
        observed_zero_V_count=int(np.sum(v==0)),V_min=float(v.min()),V_max=float(v.max()),
        directed_AB_groups=1608,outer_AB_disjoint_checks=5,inner_AB_disjoint_checks=15,
        unique_rows_checked=True,no_route_duplication=True,all_rows_accounted_for_in_histogram=True,
        split_index_semantics='Persistent id, not local row_index; both verified unique',
        near_positive_bin_rule='[left,right), final bin includes V=2; selection V<=2',
        outer_histogram_bin_width_V=5,near_positive_bin_width_V=.25,
        scope='02 training observations only; no 03/04 data displayed and no hidden labels read',
        visible_split_diagram='Five outer folds; inner three-fold protocol retained in caption and audit',
        revisions=['Added local class, near-positive subset and threshold keys to panel a',
                   'Defined near-positive inset as 128 nonmetal samples, not an independent third class',
                   'Matched legend hatches and outlined dotted line to the actual plotted marks',
                   'Added paired training and held-out-evaluation legend to panel c',
                   'Shortened panel b labels to avoid repeating the gap definitions'],
        width_mm=170,height_mm=136,dpi=300,pixels=pixels,
        min_font_pt=min(t.get_fontsize() for t in texts),all_text_ascii=True,
        all_actual_text_Times_New_Roman=True,font_files={p.name:sha(p) for p in sorted(font_paths)},
        all_text_within_canvas=True,models_loaded=False,new_fits=0,
        files={p.name:sha(p) for p in [png,pdf,gray_path,OUT/'F1_histogram_counts.csv',
            OUT/'F1_near_positive_histogram_counts.csv',OUT/'F1_split_counts.csv']})
    (OUT/'F1_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:audit[k] for k in ['N','metal_count','nonmetal_count','near_positive_count',
        'directed_AB_groups','outer_AB_disjoint_checks','inner_AB_disjoint_checks','pixels','min_font_pt','new_fits']},indent=2))


if __name__=='__main__':
    main()
