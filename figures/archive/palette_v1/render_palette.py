"""Palette proof adapted from the mandatory APMCM D plotting template.

Uses apply_apmcm_style directly and its labelled small-multiple layout language.
All glyph geometry is synthetic design material, not an experimental result.
All writes, including the Matplotlib cache, are confined to figures/.
"""
from pathlib import Path
import os
import sys
import json
import hashlib
import importlib.util
import colorsys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
os.environ['MPLCONFIGDIR'] = str(HERE/'.cache/matplotlib')
os.environ['MPLBACKEND'] = 'Agg'
sys.dont_write_bytecode = True
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import patheffects
from matplotlib.text import Text
from matplotlib.font_manager import findfont, FontProperties, fontManager
from PIL import Image, ImageCms, PngImagePlugin

SOURCE = Path('/mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm')
TEMPLATE = SOURCE/'assets/apmcm_d_plot_templates.py'
spec = importlib.util.spec_from_file_location('apmcm_d_plot_templates', TEMPLATE)
template = importlib.util.module_from_spec(spec)
spec.loader.exec_module(template)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def linearise(rgb):
    a=np.asarray(rgb, dtype=float)
    return np.where(a<=.04045, a/12.92, ((a+.055)/1.055)**2.4)


def encode(linear):
    a=np.asarray(linear, dtype=float)
    return np.where(a<=.0031308, 12.92*a, 1.055*np.maximum(a,0)**(1/2.4)-.055)


def luminance(rgb):
    return linearise(rgb) @ np.array([.2126,.7152,.0722])


def lightness(y):
    d=6/29
    return np.where(np.asarray(y)>d**3, 116*np.cbrt(y)-16, (29/3)**3*np.asarray(y))


def colour_record(role):
    rgb=np.array([int(role['hex'][j:j+2],16) for j in (1,3,5)])
    y=float(luminance(rgb/255)); gray=int(round(float(encode(y))*255))
    xyz=linearise(rgb/255) @ np.array([[.4124564,.2126729,.0193339],
                                     [.3575761,.7151522,.1191920],
                                     [.1804375,.0721750,.9503041]])
    ratios=xyz/np.array([.95047,1.,1.08883]);d=6/29
    f=np.where(ratios>d**3,np.cbrt(ratios),ratios/(3*d*d)+4/29)
    a=500*(f[0]-f[1]);b=200*(f[1]-f[2])
    h,l,s=colorsys.rgb_to_hls(*(rgb/255))
    return dict(**role,rgb=rgb.tolist(),Y=y,L_star=float(lightness(y)),gray8=gray,
                gray_hex=f'#{gray:02X}{gray:02X}{gray:02X}',
                gray8_legacy601=int(round(float(rgb @ [.299,.587,.114]))),
                C_ab=float(np.hypot(a,b)),HSL_saturation=s,HSL_lightness=l,
                white_contrast=1.05/(y+.05),black_contrast=(y+.05)/.05)


def main():
    cfg=json.loads((HERE/'palette_candidate.json').read_text())
    assert cfg['status']=='awaiting_user_approval'
    roles=[colour_record(r) for r in cfg['roles']]
    min_pair_L=min(abs(a['L_star']-b['L_star']) for i,a in enumerate(roles) for b in roles[i+1:])
    min_pair_gray=min(abs(a['gray8']-b['gray8']) for i,a in enumerate(roles) for b in roles[i+1:])
    ink=cfg['ink'];minimum=cfg['minimum_font_pt']
    template.apply_apmcm_style()
    # Explicit user override: actual Times New Roman, including math text.
    for filename in ('times.ttf','timesbd.ttf','timesi.ttf','timesbi.ttf'):
        fontManager.addfont('/mnt/c/Windows/Fonts/'+filename)
    plt.rcParams.update({'font.family':cfg['font_family'],
        'mathtext.fontset':'custom','mathtext.rm':'Times New Roman',
        'mathtext.it':'Times New Roman:italic','mathtext.bf':'Times New Roman:bold',
        'mathtext.bfit':'Times New Roman:italic:bold','mathtext.fallback':None,
        'font.size':9,'axes.labelsize':9,'axes.titlesize':10,
        'xtick.labelsize':minimum,'ytick.labelsize':minimum,'legend.fontsize':minimum,
        'text.color':ink,'axes.labelcolor':ink,'xtick.color':ink,'ytick.color':ink,
        'axes.grid':False,'savefig.bbox':None,'savefig.dpi':cfg['dpi']})
    fig=plt.figure(figsize=(7.,9.8),facecolor='white')
    gs=fig.add_gridspec(3,1,height_ratios=[2.1,5.25,1.2],left=.075,right=.985,
                        bottom=.065,top=.89,hspace=.36)
    fig.text(.075,.978,'P1/P2/P3 palette proposal',fontsize=12,weight='bold',va='top')
    fig.text(.075,.954,'Eight fixed roles | Muted colours | Approval pending',fontsize=9,va='top')

    # (a) One row of semantic colours and its linear-luminance grayscale match.
    ax=fig.add_subplot(gs[0]);ax.set(xlim=(-.05,8.05),ylim=(0,2.5));ax.axis('off')
    ax.set_title('(a) Semantic colours and their grayscale equivalents',loc='left',pad=10)
    for i,r in enumerate(roles):
        x=i+.075;w=.85
        ax.text(i+.5,2.43,r['id']+'\n'+r['label'],ha='center',va='top',fontsize=minimum,linespacing=1.15)
        for y,color in [(1.10,r['hex']),(.35,r['gray_hex'])]:
            ax.add_patch(Rectangle((x,y),w,.40,facecolor=color,edgecolor=ink,lw=.5))
            textcolor='white' if r['white_contrast']>=r['black_contrast'] else 'black'
            label=r['hex'] if y==1.10 else f"g = {r['gray8']}"
            ax.text(i+.5,y+.20,label,ha='center',va='center',fontsize=minimum,color=textcolor)
        ax.text(i+.5,.925,','.join(map(str,r['rgb'])),ha='center',va='center',fontsize=minimum)
        ax.text(i+.5,.18,f"L* = {r['L_star']:.1f}",ha='center',va='center',fontsize=minimum)

    # (b) Upper triangle: colour, lower triangle: the same pair in grayscale.
    ax=fig.add_subplot(gs[1]);ax.set(xlim=(0,8),ylim=(8,0))
    ax.set_xticks(np.arange(8)+.5,[r['id'] for r in roles]);ax.xaxis.tick_top()
    ax.set_yticks(np.arange(8)+.5,[r['id'] for r in roles])
    ax.tick_params(length=0,pad=4)
    ax.set_title('(b) All 28 pairs: colour above, grayscale below',loc='left',pad=19)
    for line in np.arange(9):
        ax.axhline(line,color='#E1E1E1',lw=.45,zorder=0)
        ax.axvline(line,color='#E1E1E1',lw=.45,zorder=0)
    for spine in ax.spines.values():spine.set_visible(False)
    for row in range(8):
        for col in range(8):
            if row==col:
                r=roles[row]
                ax.text(col+.5,row+.5,r['id'],ha='center',va='center',color=ink,fontsize=10,weight='bold')
                continue
            i,j=sorted((row,col))
            for which,index in enumerate((i,j)):
                r=roles[index];color=r['hex'] if row<col else r['gray_hex']
                x=np.array([.14,.36,.64,.86])+col
                y=(np.array([.75,.60,.40,.25]) if which==0 else np.array([.25,.40,.60,.75]))+row
                line,=ax.plot(x,y,color=color,lw=1.5,ls=r['linestyle'],marker=r['marker'],
                    markevery=[1 if which==0 else 2],ms=5.7 if r['marker']=='*' else 4.4,
                    markeredgecolor=ink,markeredgewidth=.45,markerfacecolor=color,
                    solid_capstyle='round',zorder=2+which)
                if r['key'] in ('baseline','metal'):
                    line.set_path_effects([patheffects.Stroke(linewidth=2.15,foreground=ink),patheffects.Normal()])
    ax.text(0,-.045,f'Min dL* = {min_pair_L:.2f} | Min gray gap = {min_pair_gray}/255 | Identity also uses markers and dashes.',
            transform=ax.transAxes,fontsize=minimum,ha='left',va='top')

    # (c) Continuous maps retain their original order and lightness direction.
    ax=fig.add_subplot(gs[2]);ax.axis('off')
    ax.set_title('(c) Continuous values: native maps, bright endpoints trimmed',loc='left',pad=7)
    cmap_proofs=[]
    for index,definition in enumerate(cfg['continuous_maps']):
        name=definition['name'];positions=np.linspace(definition['start'],definition['end'],256)
        colours=matplotlib.colormaps[name](positions)[:,:3]
        yy=luminance(colours);Ls=lightness(yy)
        assert np.all(np.diff(Ls)>=-1e-9)
        left=.21;bottom=.60-index*.55
        bar=ax.inset_axes([left,bottom,.77,.29]);bar.imshow(colours[np.newaxis,:,:],aspect='auto',extent=[0,1,0,1])
        bar.set_xticks([0,.5,1],['0','0.5','1']);bar.set_yticks([]);bar.tick_params(length=2,pad=1,labelsize=minimum)
        bar.spines[['top','right','left']].set_visible(False)
        ax.text(0,bottom+.16,f"{name}\n{definition['start']:.2f}-{definition['end']:.2f}",va='center',fontsize=minimum)
        cmap_proofs.append(dict(**definition,L_star_min=float(Ls.min()),L_star_max=float(Ls.max()),
                               nondecreasing_lightness=bool(np.all(np.diff(Ls)>=-1e-9))))
    fig.text(.075,.028,'Design proof only. Pair lines and map values are synthetic, not P1 experimental results.',
             fontsize=minimum,va='bottom')
    fig.canvas.draw()
    visible_texts=[t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
    assert min(t.get_fontsize() for t in visible_texts)>=minimum
    assert all(t.get_text().isascii() for t in visible_texts), 'Figure text must be ASCII English'
    used_fonts={Path(findfont(t.get_fontproperties(),fallback_to_default=False)) for t in visible_texts}
    assert all(FontProperties(fname=p).get_name()=='Times New Roman' for p in used_fonts)
    # Check bounds of actual glyphs, rather than trusting figure tight-layout heuristics.
    renderer=fig.canvas.get_renderer();fw,fh=fig.canvas.get_width_height()
    outside=[]
    for t in visible_texts:
        bb=t.get_window_extent(renderer)
        if bb.x0<0 or bb.y0<0 or bb.x1>fw or bb.y1>fh:outside.append(t.get_text())
    assert not outside,outside
    colour_path=HERE/'palette_strip.png'
    fig.savefig(colour_path,dpi=cfg['dpi'],facecolor='white',metadata={
        'Title':'Muted semantic palette proposal','Description':'Synthetic design proof; approval pending',
        'Software':'Matplotlib; APMCM template adaptation'})
    plt.close(fig)
    # Matched grayscale proof uses linear-light luminance, then sRGB encoding.
    rgb_image=Image.open(colour_path).convert('RGB')
    arr=np.asarray(rgb_image,dtype=np.float32)/255
    gray=np.round(np.clip(encode(luminance(arr)),0,1)*255).astype(np.uint8)
    gray_image=Image.fromarray(np.repeat(gray[:,:,None],3,axis=2),'RGB')
    icc=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    meta=PngImagePlugin.PngInfo();meta.add_text('Title','Muted semantic palette proposal')
    meta.add_text('Description','Synthetic design proof; approval pending; no experimental data')
    rgb_image.save(colour_path,dpi=(300,300),icc_profile=icc,pnginfo=meta)
    gray_path=HERE/'palette_strip_grayscale.png'
    gray_image.save(gray_path,dpi=(300,300),icc_profile=icc,pnginfo=meta)
    L=np.array([r['L_star'] for r in roles]);G=np.array([r['gray8'] for r in roles])
    pairs=[]
    for i in range(8):
        for j in range(i+1,8):
            pairs.append(dict(first=roles[i]['id'],second=roles[j]['id'],
                delta_L_star=float(abs(L[i]-L[j])),delta_gray8=int(abs(G[i]-G[j])),
                delta_gray8_legacy601=abs(roles[i]['gray8_legacy601']-roles[j]['gray8_legacy601'])))
    assert len(pairs)==28 and len(set(G))==8 and max(r['C_ab'] for r in roles)<23
    with Image.open(colour_path) as im:
        assert im.size==(2100,2940)
        assert all(abs(dpi-300)<.1 for dpi in im.info['dpi'])
    check=dict(status='awaiting_user_palette_approval',date='2026-11-27',
        template_sha256=sha(TEMPLATE),template_function='apply_apmcm_style',
        candidate_sha256=sha(HERE/'palette_candidate.json'),
        source_hashes={str(p.relative_to(SOURCE)):sha(p) for p in [SOURCE/'SKILL.md',
            SOURCE/'assets/apmcm_figure_playbook.md',TEMPLATE,SOURCE/'references/25_D题量子优化优秀论文解剖.md']},
        reading_order=['SKILL.md sections 2.5 and 7','complete figure playbook','complete D plotting template',
                       'reference 25 sections 25.9-25.12; 25.13 read for the actual 2025B material'],
        roles=roles,all_28_pairs=pairs,minimum_delta_L_star=min(p['delta_L_star'] for p in pairs),
        minimum_delta_gray8=min(p['delta_gray8'] for p in pairs),
        minimum_delta_gray8_legacy601=min(p['delta_gray8_legacy601'] for p in pairs),
        continuous_maps=cmap_proofs,dpi=300,width_inches=7.,height_inches=9.8,
        pixels=[2100,2940],font_family=cfg['font_family'],minimum_text_pt=min(t.get_fontsize() for t in visible_texts),
        font_files={p.name:sha(p) for p in sorted(used_fonts)},all_text_actual_times_new_roman=True,
        mathtext_family='Times New Roman',font_fallback_allowed=False,
        all_figure_text_ascii=True,all_text_within_canvas=True,
        min_swatch_text_contrast=min(max(r['white_contrast'],r['black_contrast']) for r in roles),
        no_experimental_data_used=True,models_loaded=False,fits=0,
        formal_figures_generated=False,figure_inventory_generated=False,
        outputs={p.name:sha(p) for p in [colour_path,gray_path]})
    (HERE/'palette_audit.json').write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:check[k] for k in ['dpi','pixels','minimum_text_pt','minimum_delta_L_star',
        'minimum_delta_gray8','minimum_delta_gray8_legacy601','min_swatch_text_contrast','fits']},indent=2))


if __name__=='__main__':
    main()
