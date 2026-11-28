"""Compact method figure using the accepted P1 workflow's geometry and frozen palette."""
import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.colors import to_rgb

out = Path(__file__).resolve().parent
template = Path.home()/'.codex/skills/mary-modeling-contest-pipeline-apmcm/assets/apmcm_d_plot_templates.py'
spec = importlib.util.spec_from_file_location('apmcm_templates', template)
style = importlib.util.module_from_spec(spec)
spec.loader.exec_module(style)
style.apply_apmcm_style()
style.use_times_new_roman()
plt.rcParams.update({'pdf.fonttype': 42, 'savefig.bbox': None})
palette = json.loads((out.parents[1]/'palette_frozen.json').read_text())
color = next(r['hex'] for r in palette['roles'] if r['key']=='surrogate')
ink, edge = palette['ink'], palette['outline']
def tint(weight):
    return tuple(1-weight*(1-c) for c in to_rgb(color))

fig = plt.figure(figsize=(137.6/25.4, 21/25.4), facecolor='white')
ax = fig.add_axes([0,0,1,1], xlim=(0,137.6), ylim=(0,21))
ax.axis('off')
labels = [(3,'Enumerate','Exact reference',tint(.5)),
          (48.8,'Solve in Kaiwu','SA / cloud optimizer',tint(.25)),
          (94.6,'Check returns','Legality and regret','white')]
bounds = []
for x, title, detail, fill in labels:
    ax.add_patch(patches.FancyBboxPatch((x,3),40,15,boxstyle='round,pad=0,rounding_size=1',
                                         facecolor=fill,edgecolor=edge,lw=.85))
    for y, line, size, bold in [(13.3,title,9.3,True),(7.7,detail,9,False)]:
        txt = ax.text(x+20,y,line,ha='center',va='center',fontsize=size,color=ink,
                      fontweight='bold' if bold else 'normal')
        bounds.append((txt,x))
for x,y in [(43,48.8),(88.8,94.6)]:
    ax.add_patch(patches.FancyArrowPatch((x,10.5),(y,10.5),arrowstyle='-|>',mutation_scale=9,
                                         color=edge,lw=.9,shrinkA=0,shrinkB=0))
fig.canvas.draw()
for label,x in bounds:
    box = label.get_window_extent(fig.canvas.get_renderer()).transformed(ax.transData.inverted())
    assert x+1 <= box.x0 and box.x1 <= x+39 and box.y0>3 and box.y1<18, label.get_text()
fig.savefig(out/'kaiwu_solver_workflow.pdf',metadata={'Title':None,'Author':None,'Subject':None})
fig.savefig(out/'kaiwu_solver_workflow.png',dpi=450)
plt.close(fig)
