"""Read-only P1 plotting helpers, adapted from the required APMCM D template.

The user's batch-render authorization changes the review cadence, not the
data/model boundary. All derived files and caches stay in figures/.
"""
from pathlib import Path
import csv
import gzip
import hashlib
import importlib.util
import json
import os
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / 'artifacts/p1_v21'
os.environ['MPLCONFIGDIR'] = str(HERE / '.cache/matplotlib')
os.environ['MPLBACKEND'] = 'Agg'
sys.dont_write_bytecode = True

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patheffects
from matplotlib.font_manager import findfont, FontProperties
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.text import Text
from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
from PIL import Image, ImageCms, PngImagePlugin
import pymupdf

TEMPLATE = Path('/mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm/assets/apmcm_d_plot_templates.py')
spec = importlib.util.spec_from_file_location('apmcm_d_plot_templates', TEMPLATE)
template = importlib.util.module_from_spec(spec)
spec.loader.exec_module(template)
CFG = json.loads((HERE / 'palette_frozen.json').read_text())
COLORS = {r['id']: r['hex'] for r in CFG['roles']}
INK, EDGE = CFG['ink'], CFG['outline']
SOURCES = json.loads((HERE / 'figure_inventory_sources.json').read_text())['sources_and_filters']
INVENTORY = {r['figure_id']: r for r in csv.DictReader((HERE / 'figure_inventory.csv').open())}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read_csv(rel):
    p = DATA / rel
    opener = gzip.open if p.suffix == '.gz' else open
    with opener(p, 'rt', newline='') as f:
        return list(csv.DictReader(f))


def fnum(row, key):
    value = float(row[key])
    assert np.isfinite(value), (key, row)
    return value


def verify_sources(fid):
    auth = json.loads((HERE / 'batch_rendering_authorization.json').read_text())
    assert auth['status'] == 'approved_for_remaining_batch_rendering' and fid in auth['figures']
    assert sha(HERE / 'palette_frozen.json') == '8cd969d67c966c78ad1b41fc5f7859f98e04acfb37850039d13a98c9e66a64d1'
    for source in SOURCES[fid]['sources']:
        assert sha(ROOT / source['path']) == source['sha256'], source['path']


def style():
    # The template is the actual style foundation, then the approved palette,
    # minimum size and mandatory font override its demonstration defaults.
    template.apply_apmcm_style()
    assert template.use_times_new_roman()
    plt.rcParams.update({
        'font.size': 9, 'axes.titlesize': 10, 'axes.labelsize': 9,
        'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5, 'legend.fontsize': 8.5,
        'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': EDGE,
        'xtick.color': INK, 'ytick.color': INK, 'axes.linewidth': .6,
        'axes.grid': False, 'axes.unicode_minus': False, 'hatch.linewidth': .35,
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'savefig.bbox': None,
        'savefig.dpi': 300, 'axes.formatter.use_mathtext': False,
    })


def figure(height):
    style()
    return plt.figure(figsize=(170/25.4, height/25.4), facecolor='white')


def panel(fig, box, title, **kwargs):
    ax = fig.add_axes(box, **kwargs)
    ax.set_title(title, loc='left', pad=8)
    ax.tick_params(length=3, pad=3)
    return ax


def outlined(line, width=1.5):
    line.set_linewidth(width)
    line.set_path_effects([patheffects.Stroke(linewidth=width+.6, foreground=EDGE), patheffects.Normal()])
    return line


def line(ax, x, y, *, role='S', marker='o', ls='-', label=None, fill=True, zorder=3, **kwargs):
    obj, = ax.plot(x, y, color=COLORS[role], marker=marker, ls=ls,
        markersize=4.5, markeredgewidth=.55, markeredgecolor=EDGE,
        markerfacecolor=COLORS[role] if fill else 'white', label=label,
        zorder=zorder, **kwargs)
    return outlined(obj) if role in ('S', 'P', 'N', 'W') else obj


def key(label, *, role='S', marker='o', ls='-', fill=True):
    k = Line2D([], [], color=COLORS[role], lw=1.5, marker=marker, ls=ls,
        markersize=4.5, markeredgecolor=EDGE, markeredgewidth=.55,
        markerfacecolor=COLORS[role] if fill else 'white', label=label)
    return outlined(k) if role in ('S', 'P', 'N', 'W') else k


def reference(ax, value, axis='y', label=None, ls=':'):
    fn = ax.axhline if axis == 'y' else ax.axvline
    return outlined(fn(value, color=COLORS['W'], ls=ls, lw=1.5, label=label, zorder=1))


def note(fig, y, text, x=.5, size=8.5, ha='center'):
    return fig.text(x, y, text, ha=ha, va='center', fontsize=size, linespacing=1.35)


def table(fig, box, headers, rows, widths=None):
    ax = fig.add_axes(box); ax.axis('off')
    tab = ax.table(cellText=rows, colLabels=headers, colWidths=widths,
        cellLoc='center', colLoc='center', bbox=[0, 0, 1, 1])
    tab.auto_set_font_size(False); tab.set_fontsize(8.5)
    for (r, c), cell in tab.get_celld().items():
        cell.set_facecolor('white'); cell.set_edgecolor(EDGE); cell.set_linewidth(.45)
        cell.visible_edges = 'TB' if r == 0 else ('B' if r == len(rows) else '')
        cell.PAD = .04
        if c == 0:
            cell.get_text().set_ha('left')
    return tab


def save_rows(fid, name, rows):
    folder = HERE / fid; folder.mkdir(exist_ok=True)
    path = folder / name
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return path


def export(fid, basename, fig, caption, diagnostics, adaptations, renderer_path):
    folder = HERE / fid; folder.mkdir(exist_ok=True)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer(); w, h = fig.canvas.get_width_height()
    texts = [t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
    assert texts and all(t.get_text().isascii() for t in texts), [t.get_text() for t in texts if not t.get_text().isascii()]
    assert min(t.get_fontsize() for t in texts) >= 8.5
    fonts = {Path(findfont(t.get_fontproperties(), fallback_to_default=False)) for t in texts}
    assert all(FontProperties(fname=p).get_name() == 'Times New Roman' for p in fonts)
    outside = []
    for t in texts:
        bb = t.get_window_extent(renderer)
        if bb.x0 < -.5 or bb.y0 < -.5 or bb.x1 > w+.5 or bb.y1 > h+.5:
            outside.append((t.get_text(), [round(x, 1) for x in bb.bounds]))
    assert not outside, (fid, 'text outside canvas', outside)
    png = folder / (basename+'.png'); pdf = folder / (basename+'.pdf')
    fig.savefig(png, dpi=300, facecolor='white', metadata={'Title': SOURCES[fid]['title'], 'Software': 'Matplotlib'})
    fig.savefig(pdf, facecolor='white', metadata={
        'Title': SOURCES[fid]['title'], 'Author': '', 'Subject': 'P1 existing artifact visualization',
        'Keywords': '', 'Creator': 'Matplotlib', 'CreationDate': None, 'ModDate': None})
    width, height = fig.get_size_inches()*25.4
    plt.close(fig)
    rgb = Image.open(png).convert('RGB'); a = np.asarray(rgb, dtype=float)/255
    lin = np.where(a <= .04045, a/12.92, ((a+.055)/1.055)**2.4)
    y = lin @ [.2126729, .7151522, .0721750]
    gray = np.where(y <= .0031308, 12.92*y, 1.055*np.maximum(y,0)**(1/2.4)-.055)
    gray = np.rint(np.clip(gray,0,1)*255).astype(np.uint8)
    gray_im = Image.fromarray(np.repeat(gray[:,:,None], 3, axis=2))
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    meta = PngImagePlugin.PngInfo(); meta.add_text('Title', SOURCES[fid]['title'])
    rgb.save(png, dpi=(300,300), icc_profile=icc, pnginfo=meta)
    gray_path = folder / (basename+'_grayscale.png')
    gray_im.save(gray_path, dpi=(300,300), icc_profile=icc, pnginfo=meta)
    with Image.open(png) as im:
        assert all(abs(v-300)<.1 for v in im.info['dpi'])
        pixels = list(im.size)
    with pymupdf.open(pdf) as doc:
        pg = doc[0]; pf = pg.get_fonts(full=True)
        assert len(doc) == 1 and not pg.get_images()
        assert pf and all('TimesNewRoman' in font[3] and doc.extract_font(font[0])[3] for font in pf)
        spans = [s for b in pg.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]
        assert pg.get_text().isascii() and min(s['size'] for s in spans) >= 8.49
        assert not doc.metadata['author']
    audit = dict(figure=fid, revision=1, status='rendered_awaiting_visual_check',
        date='2026-11-27', title=SOURCES[fid]['title'], source_files=SOURCES[fid]['sources'],
        palette_sha256=sha(HERE/'palette_frozen.json'),
        template_sha256=sha(TEMPLATE), template_functions=['apply_apmcm_style','use_times_new_roman'],
        template_adaptations=adaptations, renderer_sha256=sha(renderer_path),
        common_helper_sha256=sha(Path(__file__)),
        width_mm=round(float(width),3), height_mm=round(float(height),3), dpi=300,
        pixels=pixels, minimum_font_pt=min(t.get_fontsize() for t in texts),
        all_text_ascii=True, all_actual_fonts_Times_New_Roman=True,
        font_files={p.name:sha(p) for p in sorted(fonts)},
        pdf_fonts_embedded=True, pdf_vector_only=True, personal_metadata_absent=True,
        all_text_within_canvas=True, models_loaded=False, new_fits=0,
        new_bootstrap_draws=0, diagnostics=diagnostics, caption=caption,
        manual_color_review=False, manual_grayscale_review=False,
        files={p.name:sha(p) for p in sorted(folder.iterdir()) if p.suffix in ('.csv','.png','.pdf')})
    (folder/(fid+'_audit.json')).write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(figure=fid, pixels=pixels, height_mm=round(float(height),1), min_font_pt=audit['minimum_font_pt'], fits=0)))
    return audit
