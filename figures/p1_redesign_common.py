"""APMCM D-template foundation for the user's P1 visual redesign.

Source access remains read-only. All exports and graphics caches stay in figures/.
"""
import json
import re
import shutil
from pathlib import Path

from p1_plot_common import (HERE, ROOT, DATA, TEMPLATE, template, read_csv, fnum,
                            sha, SOURCES, save_rows, verify_sources)
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patheffects
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.font_manager import findfont, FontProperties
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.table import Table
from matplotlib.text import Text
from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
from matplotlib.collections import LineCollection
from PIL import Image, ImageCms, PngImagePlugin
import pymupdf

CFG = json.loads((HERE/'palette_redesign_v2.json').read_text())
INK, EDGE = CFG['ink'], CFG['edge']
CMAP = LinearSegmentedColormap.from_list('steel_white_amber', CFG['diverging'], N=257)
POOLS = CFG['pool_order']
POOL_COLORS = dict(zip(POOLS, CFG['pool_colours']))
POOL_MARKERS = dict(zip(POOLS, ['o', 's', '^', 'D']))
OUT = {
    'F2': 'F2_enrichment', 'F3': 'F3_error_tradeoff', 'A1': 'A1_residual_structure',
    'A2': 'A2_calibration', 'A3': 'A3_decision_stability', 'A4': 'A4_split_half',
    'A5': 'A5_stress_protocols', 'A6': 'A6_ablation',
}


def figure(height_mm):
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
    return plt.figure(figsize=(170/25.4, height_mm/25.4), facecolor='white')


def panel(fig, box, title):
    ax = fig.add_axes(box)
    ax.set_title(title, loc='left', pad=8)
    ax.tick_params(length=3, pad=3)
    return ax


def line(ax, x, y, color, marker='o', ls='-', label=None, main=False):
    obj, = ax.plot(x, y, color=color, marker=marker, linestyle=ls,
                   lw=2 if main else 1.25, ms=4.5 if main else 4,
                   markeredgecolor=EDGE, markeredgewidth=.45,
                   markerfacecolor=color, label=label, zorder=3 if main else 2)
    if main:
        obj.set_path_effects([patheffects.Stroke(linewidth=2.5, foreground=EDGE), patheffects.Normal()])
    return obj


def signed_color(value, bound):
    return CMAP(TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound)(value))


def colorbar(fig, box, norm, label, ticks):
    from matplotlib.cm import ScalarMappable
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap=CMAP), cax=fig.add_axes(box),
                      orientation='horizontal', ticks=ticks)
    cb.set_label(label, fontsize=8.5, labelpad=2)
    cb.ax.tick_params(labelsize=8.5, length=2, pad=2)
    cb.outline.set_linewidth(.45)
    cb.solids.set_rasterized(False)
    return cb


def sources_for(fid):
    found = list(SOURCES[fid]['sources'])
    if fid == 'A5':
        # A display-only matched-reference colour transformation needs the
        # already approved main-result source, not any additional experiment.
        src = next(s for s in SOURCES['F3']['sources'] if s['path'].endswith('P1_final_experiment_table.csv'))
        found.append(src)
    return found


def finish(fid, fig, caption, reading_guide, diagnostics, design):
    verify_sources(fid)
    assert json.loads((HERE/'redesign_authorization.json').read_text())['status']=='user_authorized_rework_batch'
    for s in sources_for(fid):
        assert sha(ROOT/s['path']) == s['sha256']
    assert not fig._suptitle
    assert not fig.findobj(Table)
    fig.canvas.draw()
    render = fig.canvas.get_renderer()
    width_px, height_px = fig.canvas.get_width_height()
    texts = [t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
    assert all(t.get_text().isascii() for t in texts)
    assert min(t.get_fontsize() for t in texts) >= 8.5
    fonts = {Path(findfont(t.get_fontproperties(), fallback_to_default=False)) for t in texts}
    assert all(FontProperties(fname=p).get_name() == 'Times New Roman' for p in fonts)
    bad = []
    for t in texts:
        b = t.get_window_extent(render)
        if b.x0 < -.5 or b.y0 < -.5 or b.x1 > width_px+.5 or b.y1 > height_px+.5:
            bad.append((t.get_text(), [round(v,1) for v in b.bounds]))
    assert not bad, (fid, 'text outside canvas', bad)
    all_strings = [t.get_text() for t in texts]
    # Labels/keys/values only. Sentence-like free text is separately reviewed.
    assert all(len(re.findall(r'\S+', s)) <= 9 for s in all_strings), all_strings
    folder=HERE/fid
    base=OUT[fid]+'_v2'
    png=folder/(base+'.png'); pdf=folder/(base+'.pdf'); gray=folder/(base+'_grayscale.png')
    fig.savefig(png, dpi=300, facecolor='white', metadata={'Title':SOURCES[fid]['title'],'Software':'Matplotlib'})
    fig.savefig(pdf, facecolor='white', metadata={'Title':SOURCES[fid]['title'], 'Author':'',
        'Subject':'P1 visual redesign, existing artifacts only', 'Keywords':'',
        'Creator':'Matplotlib', 'CreationDate':None, 'ModDate':None})
    size_mm = (fig.get_size_inches()*25.4).tolist()
    plt.close(fig)
    rgb=Image.open(png).convert('RGB'); a=np.asarray(rgb, dtype=float)/255
    lin=np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
    lum=lin@[.2126729,.7151522,.0721750]
    g=np.where(lum<=.0031308,12.92*lum,1.055*np.maximum(lum,0)**(1/2.4)-.055)
    g=np.rint(np.clip(g,0,1)*255).astype(np.uint8)
    gray_im=Image.fromarray(np.repeat(g[:,:,None],3,axis=2))
    icc=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    meta=PngImagePlugin.PngInfo(); meta.add_text('Title',SOURCES[fid]['title'])
    rgb.save(png,dpi=(300,300),icc_profile=icc,pnginfo=meta)
    gray_im.save(gray,dpi=(300,300),icc_profile=icc,pnginfo=meta)
    for src in [png,pdf,gray]:
        shutil.copyfile(src, folder/src.name.replace('_v2',''))
    with pymupdf.open(pdf) as doc:
        pg=doc[0]; pdf_fonts=pg.get_fonts(full=True)
        assert len(doc)==1 and not pg.get_images()
        assert pdf_fonts and all('TimesNewRoman' in f[3] and doc.extract_font(f[0])[3] for f in pdf_fonts)
        spans=[s for b in pg.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]
        assert pg.get_text().isascii() and min(s['size'] for s in spans)>=8.49
        assert not doc.metadata['author']
    old=json.loads((HERE/'archive/rejected_batch_v1'/fid/(fid+'_audit.json')).read_text())
    with pymupdf.open(HERE/'archive/rejected_batch_v1'/fid/(OUT[fid]+'.pdf')) as d:
        old_words=len(d[0].get_text('words'))
    with pymupdf.open(pdf) as d:
        word_count=len(d[0].get_text('words'))
    audit=dict(figure=fid,revision=2,date='2026-11-27',status='rendered_awaiting_visual_check',
        title=SOURCES[fid]['title'],width_mm=round(size_mm[0],3),height_mm=round(size_mm[1],3),
        dpi=300,pixels=list(rgb.size),minimum_font_pt=min(t.get_fontsize() for t in texts),
        all_text_ascii=True,all_actual_fonts_Times_New_Roman=True,
        font_files={p.name:sha(p) for p in sorted(fonts)},
        pdf_fonts_embedded=True,pdf_vector_only=True,personal_metadata_absent=True,
        all_text_within_canvas=True,no_suptitle=True,no_embedded_table=True,
        annotation_only_text=True,text_strings=all_strings,text_word_count=word_count,
        rejected_v1_text_word_count=old_words,text_reduction_fraction=1-word_count/old_words,
        no_lollipop=True,design=design,source_files=sources_for(fid),
        template=str(TEMPLATE),template_sha256=sha(TEMPLATE),
        template_functions=['apply_apmcm_style','use_times_new_roman'],
        renderer_sha256=sha(HERE/'render_p1_redesign.py'),common_helper_sha256=sha(Path(__file__)),
        palette_file='figures/palette_redesign_v2.json',palette_sha256=sha(HERE/'palette_redesign_v2.json'),
        prior_frozen_palette_unchanged=sha(HERE/'palette_frozen.json')==old['palette_sha256'],
        models_loaded=False,new_fits=0,new_bootstrap_draws=0,
        caption=caption,reading_guide=reading_guide,diagnostics=diagnostics,
        manual_color_review=False,manual_grayscale_review=False,user_figure_approval=False,
        actual_paper_print_test_performed=False,
        files={p.name:sha(p) for p in sorted(folder.iterdir()) if p.suffix in ('.csv','.png','.pdf')})
    (folder/(fid+'_audit.json')).write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(figure=fid,height_mm=audit['height_mm'],words=word_count,
        previous_words=old_words,new_fits=0)))
    return audit
