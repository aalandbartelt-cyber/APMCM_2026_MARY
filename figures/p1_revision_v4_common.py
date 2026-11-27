"""Targeted revision exporter; reuse the unchanged, template-based v2 styling."""
from p1_redesign_common import *


def finish(fid, fig, caption, reading_guide, diagnostics, design):
    authorization = json.loads((HERE/'A5_color_revision_v4_authorization.json').read_text())
    assert fid in authorization['revise_only']
    verify_sources(fid)
    for source in sources_for(fid):
        assert sha(ROOT/source['path']) == source['sha256']
    assert not fig._suptitle and not fig.findobj(Table)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    width_px, height_px = fig.canvas.get_width_height()
    texts = [t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
    strings = [t.get_text() for t in texts]
    assert all(s.isascii() and len(re.findall(r'\S+', s)) <= 9 for s in strings)
    assert min(t.get_fontsize() for t in texts) >= 8.5
    fonts = {Path(findfont(t.get_fontproperties(), fallback_to_default=False)) for t in texts}
    assert all(FontProperties(fname=p).get_name() == 'Times New Roman' for p in fonts)
    outside = []
    for t in texts:
        b = t.get_window_extent(renderer)
        if b.x0 < -.5 or b.y0 < -.5 or b.x1 > width_px+.5 or b.y1 > height_px+.5:
            outside.append((t.get_text(), list(b.bounds)))
    assert not outside, (fid, outside)
    folder = HERE/fid
    base = OUT[fid]+'_v4'
    png, pdf, gray = [folder/(base+s) for s in ['.png','.pdf','_grayscale.png']]
    fig.savefig(png, dpi=300, facecolor='white', metadata={'Title':SOURCES[fid]['title'],'Software':'Matplotlib'})
    fig.savefig(pdf, facecolor='white', metadata={'Title':SOURCES[fid]['title'],'Author':'',
        'Subject':'P1 targeted visual revision; existing artifacts only','Keywords':'',
        'Creator':'Matplotlib','CreationDate':None,'ModDate':None})
    size_mm = (fig.get_size_inches()*25.4).tolist()
    plt.close(fig)
    rgb = Image.open(png).convert('RGB')
    a = np.asarray(rgb,dtype=float)/255
    lin = np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
    lum = lin@[.2126729,.7151522,.0721750]
    g = np.where(lum<=.0031308,12.92*lum,1.055*np.maximum(lum,0)**(1/2.4)-.055)
    g = np.rint(np.clip(g,0,1)*255).astype(np.uint8)
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    meta = PngImagePlugin.PngInfo(); meta.add_text('Title',SOURCES[fid]['title'])
    rgb.save(png,dpi=(300,300),icc_profile=icc,pnginfo=meta)
    Image.fromarray(np.repeat(g[:,:,None],3,axis=2)).save(gray,dpi=(300,300),icc_profile=icc,pnginfo=meta)
    for src in [png,pdf,gray]:
        shutil.copyfile(src,folder/src.name.replace('_v4',''))
    with pymupdf.open(pdf) as doc:
        page=doc[0]; pf=page.get_fonts(full=True)
        spans=[s for b in page.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]
        assert len(doc)==1 and not page.get_images() and not doc.metadata['author']
        assert pf and all('TimesNewRoman' in f[3] and doc.extract_font(f[0])[3] for f in pf)
        assert page.get_text().isascii() and min(s['size'] for s in spans)>=8.49
        word_count=len(page.get_text('words'))
    previous=json.loads((HERE/'archive/before_A5_color_v4'/fid/(fid+'_audit.json')).read_text())
    palette='palette_A5_reference_v4.json' if fid=='A5' else 'palette_redesign_v2.json'
    audit=dict(figure=fid,revision=4,date='2026-11-27',status='rendered_awaiting_visual_check',
        title=SOURCES[fid]['title'],width_mm=round(size_mm[0],3),height_mm=round(size_mm[1],3),
        dpi=300,pixels=list(rgb.size),minimum_font_pt=min(t.get_fontsize() for t in texts),
        all_text_ascii=True,all_actual_fonts_Times_New_Roman=True,
        font_files={p.name:sha(p) for p in sorted(fonts)},pdf_fonts_embedded=True,pdf_vector_only=True,
        personal_metadata_absent=True,all_text_within_canvas=True,no_suptitle=True,no_embedded_table=True,
        annotation_only_text=True,text_strings=strings,text_word_count=word_count,
        previous_v3_text_word_count=previous['text_word_count'],no_lollipop=True,
        design=design,source_files=sources_for(fid),template=str(TEMPLATE),template_sha256=sha(TEMPLATE),
        template_functions=['apply_apmcm_style','use_times_new_roman'],
        renderer_file='figures/render_A5_palette_v4.py',renderer_sha256=sha(HERE/'render_A5_palette_v4.py'),
        common_helper_file='figures/p1_revision_v4_common.py',common_helper_sha256=sha(Path(__file__)),
        foundation_helper_sha256=sha(HERE/'p1_redesign_common.py'),
        palette_file='figures/'+palette,palette_sha256=sha(HERE/palette),
        models_loaded=False,new_fits=0,new_bootstrap_draws=0,caption=caption,reading_guide=reading_guide,
        diagnostics=diagnostics,manual_color_review=False,manual_grayscale_review=False,
        user_figure_approval=False,actual_paper_print_test_performed=False,
        files={p.name:sha(p) for p in sorted(folder.iterdir()) if p.suffix in ('.csv','.png','.pdf')})
    for name in [fid+'_audit.json',fid+'_audit_v4.json']:
        (folder/name).write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(figure=fid,size_mm=size_mm,words=word_count,new_fits=0)))
    return audit
