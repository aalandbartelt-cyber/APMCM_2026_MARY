"""Draw the existing P1 fitting protocol; no data fitting or model imports."""
from pathlib import Path
import importlib.util
import json
import hashlib

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.path import Path as MplPath
from matplotlib.colors import to_rgb
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
TEMPLATE = Path('/home/mary/.codex/skills/mary-modeling-contest-pipeline-apmcm/assets/apmcm_d_plot_templates.py')
spec = importlib.util.spec_from_file_location('apmcm_templates', TEMPLATE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.apply_apmcm_style()
base.use_times_new_roman()
plt.rcParams.update({'font.size': 9, 'pdf.fonttype': 42, 'ps.fonttype': 42,
                     'savefig.bbox': None, 'savefig.dpi': 300})
palette = json.loads((ROOT/'figures/palette_frozen.json').read_text())
colors = {r['key']: r['hex'] for r in palette['roles']}
ink, outline = palette['ink'], palette['outline']

def tint(c, amount):
    return tuple(1 - amount * (1-x) for x in to_rgb(c))

fig = plt.figure(figsize=(146.4/25.4, 109/25.4), facecolor='white')
ax = fig.add_axes([0, 0, 1, 1], xlim=(0,146.4), ylim=(0,109))
ax.axis('off')
boxes = []

def text(x,y,s,size=9,weight='normal',ha='center',va='center'):
    return ax.text(x,y,s,fontsize=size,fontweight=weight,ha=ha,va=va,
                   color=ink,linespacing=1.22,zorder=5)

def node(x,y,w,h,lines,kind='process',fill='white',bold=False):
    if kind == 'data':
        pad=2
        shape=patches.Polygon([(x+pad,y),(x+w,y),(x+w-pad,y+h),(x,y+h)],
                              facecolor=fill,edgecolor=outline,lw=.85,zorder=3)
    else:
        shape=patches.FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=1',
                                    facecolor=fill,edgecolor=outline,lw=.85,zorder=3)
    ax.add_patch(shape)
    label=text(x+w/2,y+h/2,lines,weight='bold' if bold else 'normal')
    boxes.append((label,(x+1,y+.5,x+w-1,y+h-.5)))

def arrow(points, dashed=False):
    path=MplPath(points,[MplPath.MOVETO]+[MplPath.LINETO]*(len(points)-1))
    ax.add_patch(patches.FancyArrowPatch(path=path,arrowstyle='-|>',mutation_scale=9,
                                       linewidth=.9,color=outline,linestyle='--' if dashed else '-',
                                       zorder=2))

# (a) A held-out outer fold receives predictions only after training is complete.
text(2,106,'(a) Nested grouped assessment',weight='bold',ha='left',size=10)
node(39,92.5,68.4,9,'File 02: labeled compositions',kind='data')
ax.add_patch(patches.FancyBboxPatch((1.7,38.8),143,50.8,
    boxstyle='round,pad=0,rounding_size=1.3',facecolor='white',edgecolor=outline,
    linewidth=.8,linestyle=(0,(4,2)),zorder=0))
text(4,87.1,'Five outer A–B folds',ha='left',size=8.5)

ax.add_patch(patches.FancyBboxPatch((5,42),93,41.2,
    boxstyle='round,pad=0,rounding_size=1',facecolor=tint(colors['surrogate'],.08),
    edgecolor=outline,linewidth=.75,zorder=0))
text(51.5,79.6,'Outer training groups',weight='bold')
arrow([(63,92.5),(63,90.8),(51.5,90.8),(51.5,83.2)])
arrow([(84,92.5),(84,90.8),(123.2,90.8),(123.2,82)])

ax.add_patch(patches.FancyBboxPatch((9,56.8),85,18.4,
    boxstyle='round,pad=0,rounding_size=.6',facecolor='white',edgecolor=outline,
    linewidth=.65,linestyle=(0,(2,2)),zorder=1))
text(51.5,72.4,'Three-fold route selection',size=8.5)
node(12,59,33,10,'LightGBM\nfitting',fill=tint(colors['surrogate'],.55))
node(57,59,33,10,'Two-fold OOF\ncalibration',fill=tint(colors['surrogate'],.25))
arrow([(45,64),(57,64)])
node(27,44,49,9,'Select and refit',fill=tint(colors['surrogate'],.4))
arrow([(73.5,56.8),(73.5,55.1),(51.5,55.1),(51.5,53)])

node(104,70,38.5,12,'Held-out\nA–B groups',kind='data')
node(104,43.5,38.5,13,'Evaluate\nRMSE · EF@20')
arrow([(123.25,70),(123.25,56.5)])
arrow([(76,48.5),(104,48.5)])
text(88.7,53.5,'Predict',size=8.5)

# (b) Development responses select between fixed candidates; 04 has no labels.
text(2,32.6,'(b) Development selection and test prediction',weight='bold',ha='left',size=10)
node(3,12.4,40,13,'Fit candidates\nFile 02 only',fill=tint(colors['surrogate'],.28))
node(53.2,12.4,40,13,'Select H-soft\nFile 03',fill=tint(colors['surrogate'],.55),bold=True)
node(103.4,12.4,40,13,'Predict V\nFile 04',kind='data')
arrow([(43,18.9),(53.2,18.9)])
arrow([(93.2,18.9),(103.4,18.9)])
text(23,8,'Fixed candidates',size=8.5)
text(73.2,8,'RMSE / EF@20',size=8.5)
text(73.2,3.4,'NDCG tie-break',size=8.5)
text(123.4,8,'3,703 compositions',size=8.5)

fig.canvas.draw()
renderer=fig.canvas.get_renderer()
bad=[]
for label,bound in boxes:
    box=label.get_window_extent(renderer).transformed(ax.transData.inverted())
    if box.x0<bound[0] or box.y0<bound[1] or box.x1>bound[2] or box.y1>bound[3]:
        bad.append(label.get_text())
if bad:
    raise RuntimeError('Node text exceeds its box: '+repr(bad))
texts=[t.get_text() for t in ax.texts]
assert not any('\u3400'<=c<='\u9fff' for s in texts for c in s)
assert min(t.get_fontsize() for t in ax.texts)>=8.5
assert fig._suptitle is None
stem=OUT/'F4_model_workflow_v1'
fig.savefig(stem.with_suffix('.pdf'),metadata={'Title':None,'Author':None,'Subject':None,'Keywords':None})
fig.savefig(stem.with_suffix('.png'),dpi=300)
Image.open(stem.with_suffix('.png')).convert('L').save(OUT/'F4_model_workflow_v1_grayscale.png',dpi=(300,300))
plt.close(fig)
(OUT/'F4_audit.json').write_text(json.dumps({
    'purpose':'Show the existing fitting, grouped assessment and development-selection protocol.',
    'sources':['03_求解/D/p1_v2/experiment.py','03_求解/D/p1_v2/models.py',
               'artifacts/p1_v21/model_card.json','artifacts/p1_v21/results/03_development_results.csv'],
    'template':str(TEMPLATE),'template_sha256':hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
    'palette':'figures/palette_frozen.json','font':'Times New Roman',
    'width_mm':146.4,'height_mm':109,'minimum_font_pt':8.5,'dpi':300,
    'new_fits':0,'node_text_within_bounds':True,'english_only':True,'no_suptitle':True,
    'no_embedded_table':True,'direct_labels':True,'figure_text':texts,
    'review_status':'Rendered for manuscript review; user approval pending.'
},ensure_ascii=False,indent=2)+'\n')
print(stem.with_suffix('.pdf'))
