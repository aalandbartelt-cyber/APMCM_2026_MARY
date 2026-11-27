"""Compact P1 workflow, following the user's three-step revision."""
from pathlib import Path
import importlib.util
import json
import hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.colors import to_rgb
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent
TEMPLATE=Path('/home/mary/.codex/skills/mary-modeling-contest-pipeline-apmcm/assets/apmcm_d_plot_templates.py')
spec=importlib.util.spec_from_file_location('apmcm_templates',TEMPLATE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
base.apply_apmcm_style();base.use_times_new_roman()
plt.rcParams.update({'pdf.fonttype':42,'ps.fonttype':42,'savefig.bbox':None})
palette=json.loads((ROOT/'figures/palette_frozen.json').read_text())
blue=next(r['hex'] for r in palette['roles'] if r['key']=='surrogate')
ink,edge=palette['ink'],palette['outline']
def tint(amount):return tuple(1-amount*(1-c) for c in to_rgb(blue))
fig=plt.figure(figsize=(137.6/25.4,30/25.4),facecolor='white')
ax=fig.add_axes([0,0,1,1],xlim=(0,137.6),ylim=(0,30));ax.axis('off')
nodes=[(3,'Fit models','LightGBM',tint(.5)),
       (48.8,'Calibrate scores','L-BFGS-B',tint(.25)),
       (94.6,'Validate / select','RMSE · EF@20','white')]
bounded=[]
for x,title,detail,color in nodes:
    ax.add_patch(patches.FancyBboxPatch((x,10),40,15,boxstyle='round,pad=0,rounding_size=1',
                                      facecolor=color,edgecolor=edge,lw=.85))
    for yy,content,size,bold in [(20.3,title,9.3,True),(14.7,detail,9,False)]:
        t=ax.text(x+20,yy,content,ha='center',va='center',fontsize=size,color=ink,
                  fontweight='bold' if bold else 'normal')
        bounded.append((t,(x+1,10.5,x+39,24.5)))
for x0,x1 in [(43,48.8),(88.8,94.6)]:
    ax.add_patch(patches.FancyArrowPatch((x0,17.5),(x1,17.5),arrowstyle='-|>',
                                       mutation_scale=9,color=edge,lw=.9,shrinkA=0,shrinkB=0))
ax.plot([3,3,88.8,88.8],[8,6.8,6.8,8],color=edge,lw=.6)
ax.text(45.9,3.1,'Within fitting groups',ha='center',va='center',fontsize=8.5,color=ink)
ax.text(114.6,5.3,'Grouped folds / file 03',ha='center',va='center',fontsize=8.5,color=ink)
fig.canvas.draw();renderer=fig.canvas.get_renderer()
for t,b in bounded:
    r=t.get_window_extent(renderer).transformed(ax.transData.inverted())
    assert r.x0>=b[0] and r.x1<=b[2] and r.y0>=b[1] and r.y1<=b[3],t.get_text()
assert all(t.get_fontsize()>=8.5 for t in ax.texts)
stem=OUT/'F4_model_workflow_v2'
fig.savefig(stem.with_suffix('.pdf'),metadata={'Title':None,'Author':None,'Subject':None,'Keywords':None})
fig.savefig(stem.with_suffix('.png'),dpi=300)
Image.open(stem.with_suffix('.png')).convert('L').save(OUT/'F4_model_workflow_v2_grayscale.png',dpi=(300,300))
plt.close(fig)
(OUT/'F4_audit_v2.json').write_text(json.dumps({
    'purpose':'Replace the three prose steps with a compact three-node workflow.',
    'sources':['03_求解/D/p1_v2/models.py','03_求解/D/p1_v2/experiment.py'],
    'template':str(TEMPLATE),'template_sha256':hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
    'palette':'figures/palette_frozen.json','font':'Times New Roman','dpi':300,
    'width_mm':137.6,'height_mm':30,'minimum_font_pt':8.5,'node_count':3,
    'new_fits':0,'no_suptitle':True,'no_embedded_table':True,'direct_labels':True,
    'text_within_nodes':True,'english_only':True,
    'diagram_text':[t.get_text() for t in ax.texts],
    'review_status':'Revised after user rejected the large nested diagram; awaiting review.'
},ensure_ascii=False,indent=2)+'\n')
print(stem.with_suffix('.pdf'))
