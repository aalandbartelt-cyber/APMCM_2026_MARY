"""Package the reference-matched A5 colour revision only."""
from pathlib import Path
import csv, hashlib, json, shutil
from PIL import Image
import pymupdf

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent

def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def tree_hash(path):
    files = sorted(p for p in path.rglob('*') if p.is_file())
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(ROOT)).encode()+b'\0'+bytes.fromhex(sha(p)))
    return dict(files=len(files), bytes=sum(p.stat().st_size for p in files), sha256=h.hexdigest())


def inspect_pdf(path):
    with pymupdf.open(path) as doc:
        info = []
        for page in doc:
            fonts = page.get_fonts(full=True)
            spans = [s for b in page.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]
            assert fonts and spans and not page.get_images()
            assert all('TimesNewRoman' in f[3] and doc.extract_font(f[0])[3] for f in fonts)
            assert page.get_text().isascii() and min(s['size'] for s in spans)>=8.49
            info.append(dict(width_mm=page.rect.width*25.4/72, height_mm=page.rect.height*25.4/72,
                minimum_font_pt=min(s['size'] for s in spans), all_fonts_embedded=True,
                Times_New_Roman_only=True, all_text_ascii=True, raster_images=0))
        assert not doc.metadata.get('author')
        return dict(page_count=len(doc), pages=info, personal_metadata_absent=True)


auth=read_json(HERE/'A5_color_revision_v4_authorization.json')
old=read_json(HERE/'P1_redesign_delivery_receipt_v3.json')
assert sha(HERE/'P1_redesign_delivery_receipt_v3.json')==auth['previous_delivery_receipt_sha256']
for group in ['other_figure_files','previous_A5_v3_files']:
    assert all(sha(HERE/p)==h for p,h in auth[group].items()),group
protected={name:tree_hash(ROOT/p) for name,p in {
    'p1_artifacts':'artifacts/p1_v21','p1_code':'03_求解/D/p1_v2',
    'official_D_data':'00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date'}.items()}
protected['fit_ledger_sha256']=sha(ROOT/'artifacts/p1_v21/fit_ledger.jsonl')
assert protected==old['protected_groups']
a=read_json(HERE/'A5/A5_audit_v4.json')
for p,h in a['files'].items():assert sha(HERE/'A5'/p)==h
for src in a['source_files']:assert sha(ROOT/src['path'])==src['sha256']
assert a['renderer_sha256']==sha(HERE/'render_A5_palette_v4.py')
assert a['common_helper_sha256']==sha(HERE/'p1_revision_v4_common.py')
assert a['palette_sha256']==sha(HERE/'palette_A5_reference_v4.json')
assert read_json(HERE/'palette_A5_reference_v4.json')['diverging']==read_json(HERE/'palette_redesign_v2.json')['diverging']
assert a['diagnostics']['minimum_cell_text_contrast']>=4.5
prior=read_json(HERE/'archive/before_A5_color_v4/A5/A5_audit.json')
assert all(sha(HERE/'A5'/p)==h for p,h in prior['files'].items() if p.endswith('.csv'))
checkpoint=read_json(HERE/'visual_review_checkpoint_v4.json')
for name,digest in checkpoint['reviewed_color_and_grayscale_pixels'].items():
    with Image.open(HERE/'A5'/name) as im:
        assert hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()==digest
        assert all(abs(x-300)<.1 for x in im.info['dpi'])
with pymupdf.open(HERE/'A5/A5_stress_protocols_v3.pdf') as before, pymupdf.open(HERE/'A5/A5_stress_protocols_v4.pdf') as after:
    def text_geometry(page):
        return [(s['text'],s['bbox'],s['size'],s['font']) for b in page.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]
    assert before[0].rect==after[0].rect and text_geometry(before[0])==text_geometry(after[0])
    assert [d['rect'] for d in before[0].get_drawings()]==[d['rect'] for d in after[0].get_drawings()]
a.update(status='revision_4_reference_matched_awaiting_user_review',manual_color_review=True,
    manual_grayscale_review=True,legend_matches_actual_marks=True,nine_self_checks_passed=True,
    manual_no_explanatory_sentences=True,manual_no_clipping_or_label_overlap=True,
    reference_A1_palette_exact_match=True,existing_display_data_unchanged=True,
    all_text_geometry_unchanged=True,all_graphic_rectangles_unchanged=True,
    final_pdf_inspection=inspect_pdf(HERE/'A5/A5_stress_protocols_v4.pdf'))
for name in ['A5_audit.json','A5_audit_v4.json']:write_json(HERE/'A5'/name,a)

review=(HERE/'A5/A5_review_v3.md').read_text().replace('A5 v3','A5 v4').replace('_v3.','_v4.').replace('_v3_grayscale','_v4_grayscale')
review=review.replace('2026-11-27。本轮只修订合并审阅 PDF 的第 2、4、8 页；其他六图已获用户认可并原件保留。本图 v3 待用户验收。',
    '2026-11-27。本轮仅更新合并 PDF 第八页的配色和格内文字颜色；其他八图原件保留。本图 v4 待用户验收。')
review=review.replace('本次修改：改为 150 × 150 mm 方形画布和等宽高网格；蓝端提亮为 #93BED7，琥珀端采用 #E7BF8E，零点、归一化范围和数值不变。',
    '本次修改：按用户提供的 A1(a) 参考图，复用钢蓝 #587AA4—白—琥珀 #DC9848 连续色图。格内数字使用深色 #080808，最低文字/底色对比度为 4.65:1。150 × 150 mm 方形布局、±80% 色标、字体字号和全部数值保持不变。')
review=review.replace('负变化浅蓝、零白、正变化浅琥珀','负变化钢蓝、零白、正变化琥珀')
review=review.replace('配色与本图登记一致；F2/A1 沿用 v2，A5 按用户本轮意见登记浅色修订。',
    '配色与用户所附 A1(a) 参考图一致，见 ../palette_A5_reference_v4.json；格内深色数字另经对比度核验。')
for name in ['A5_review.md','A5_review_v4.md']:(HERE/'A5'/name).write_text(review)

with pymupdf.open(HERE/'P1_figures_review_v3.pdf') as before, pymupdf.open(HERE/'A5/A5_stress_protocols_v4.pdf') as single, pymupdf.open() as merged:
    merged.insert_pdf(before,from_page=0,to_page=6)
    merged.insert_pdf(single)
    merged.insert_pdf(before,from_page=8,to_page=8)
    toc=before.get_toc();toc[7][1]='A5 v4 - reference-matched colours; revised for review'
    merged.set_toc(toc)
    merged.set_metadata(dict(title='P1 figures - A5 colour revision v4',author='',
        subject='Page 8 matches the supplied A1 palette reference; other pages unchanged',
        creator='P1 figure packaging',producer='PyMuPDF',keywords='',creationDate='',modDate=''))
    merged.save(HERE/'P1_figures_review_v4.pdf',garbage=4,deflate=True)
shutil.copyfile(HERE/'P1_figures_review_v4.pdf',HERE/'P1_figures_review.pdf')
with pymupdf.open(HERE/'P1_figures_review_v3.pdf') as before, pymupdf.open(HERE/'P1_figures_review_v4.pdf') as after:
    for i in range(9):
        assert before[i].rect==after[i].rect and before[i].get_text()==after[i].get_text()
        if i!=7:assert before[i].get_pixmap().samples==after[i].get_pixmap().samples
pdf_check=inspect_pdf(HERE/'P1_figures_review_v4.pdf')

with (HERE/'figure_inventory.csv').open(newline='') as f:
    reader=csv.DictReader(f);fields=reader.fieldnames;inventory=list(reader)
for row in inventory:
    if row['figure_id']=='A5':
        row['status']=a['status']
        row['grayscale_ok']='visually checked; signed values; minimum cell text contrast 4.65:1'
        row['notes']=(f"title={a['title']}; tier=appendix; model_chain=Model validation; revision=4; "
            f"design={a['design']}; palette=figures/palette_A5_reference_v4.json; "
            'output=figures/A5/A5_stress_protocols_v4.pdf; review=figures/A5/A5_review_v4.md; '
            'height_mm=150; nine_checks=passed; new_fits=0; new_bootstrap_draws=0; '
            'colour_map=exact_A1_reference; dark_cell_text=080808; data_and_geometry_unchanged=1')
with (HERE/'figure_inventory.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(inventory)
approval=read_json(HERE/'figure_inventory_approval.json')
approval.update(rendering_mode='A5_reference_matched_colour_revision_only',current_figure='A5',
    current_figure_revision=4,current_figure_status=a['status'],
    superseding_authorization='figures/A5_color_revision_v4_authorization.json',
    gate='Acceptance of other figures remains as recorded previously; A5 v4 is submitted for review. No manuscript embedding.')
write_json(HERE/'figure_inventory_approval.json',approval)

index=(HERE/'archive/before_A5_color_v4/P1_FIGURES_REVIEW.md').read_text()
index=index.replace('# P1 图件审阅：三处修订 v3','# P1 图件审阅：第八页配色 v4')
lines=index.splitlines()
for i,line in enumerate(lines):
    if line.startswith('2026-11-27。'):
        lines[i]='2026-11-27。本轮只更新第 **8 页（A5 v4）**：按用户提供的 A1(a) 图片匹配钢蓝—白—琥珀色图，数字改用清晰深色。其余八张图及原审计文件保持字节不变，既有验收状态沿用上轮记录。'
    elif line.startswith('| 8 |'):
        lines[i]='| 8 | A5 v4：本轮配色修订，待验收 | 复用参考图的钢蓝—白—琥珀渐变；150 × 150 mm 方形布局、全部数据不变。 | [PNG](A5/A5_stress_protocols_v4.png) / [PDF](A5/A5_stress_protocols_v4.pdf) / [灰度](A5/A5_stress_protocols_v4_grayscale.png) | [审图单](A5/A5_review_v4.md) |'
    elif line.startswith('A5 的浅色调整'):
        lines[i]='A5 直接复用用户所附 A1(a) 参考图的连续色图，见 [当前配色记录](palette_A5_reference_v4.json)。负蓝/零白/正琥珀及 ±80% 归一化范围未变。格内数字最低对比度为 4.65:1，灰度已检查；protocol-level evidence, not final-model 边界保留在 caption。完整数字继续使用 [伴随材料](P1_FIGURE_COMPANION_TABLES_v2.md)。'
    elif line.startswith('仅重现本次三图'):
        lines[i]='仅重现本次第八页：`PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_A5_palette_v4.py`。重新渲染后需更新目检像素记录，再运行 finalize_A5_palette_v4.py；不要运行旧版批量生成器覆盖其余图。'
index='\n'.join(lines)+'\n'
index=index.replace('合并审阅 PDF v3','合并审阅 PDF v4').replace('P1_figures_review_v3.pdf','P1_figures_review_v4.pdf')
index=index.replace('P1_redesign_delivery_receipt_v3.json','P1_redesign_delivery_receipt_v4.json').replace('visual_review_checkpoint_v3.json','visual_review_checkpoint_v4.json').replace('P1_repository_checks_v3.json','P1_repository_checks_v4.json')
index=index.replace('targeted_revision_v3_authorization.json','A5_color_revision_v4_authorization.json').replace('archive/before_targeted_v3/P1_FIGURES_REVIEW.md','archive/before_A5_color_v4/P1_FIGURES_REVIEW.md')
index=index.replace('三张新版均为','当前 F2/A1/A5 均为').replace('修订前索引及三图审计存档','上一轮索引存档')
index=index.replace('F2 v3：本轮修订','F2 v3：上轮修订').replace('A1 v3：本轮修订','A1 v3：上轮修订')
(HERE/'P1_FIGURES_REVIEW.md').write_text(index)
proposal=(HERE/'archive/before_A5_color_v4/figure_inventory_proposal.md').read_text()
proposal+='\n2026-11-27 更新：A5 现为 v4，按用户提供的 A1(a) 图匹配钢蓝—白—琥珀配色；方形比例、数据与其余八图不变。当前入口见审阅索引。\n'
(HERE/'figure_inventory_proposal.md').write_text(proposal)
(HERE/'P1_BATCH_HANDOFF.md').write_text('''# P1 figure handoff — A5 reference colours v4

2026-11-27. Only A5 (review page 8) changed in this revision. The user supplied the existing A1(a) bias panel as the colour reference. A5 now uses exactly the same steel-blue #587AA4 / white / amber #DC9848 map, with dark #080808 cell text. The minimum cell-text contrast is 4.65:1. Square geometry, signed normalization, all numbers, source CSVs and the other eight figure folders are unchanged. Existing acceptance states are preserved; A5 v4 awaits review.

Current entries: P1_FIGURES_REVIEW.md, P1_figures_review_v4.pdf and the stable PDF alias. Renderer: render_A5_palette_v4.py; exporter: p1_revision_v4_common.py; package: finalize_A5_palette_v4.py. Active colour file: palette_A5_reference_v4.json. Earlier v4 palette trials are explicitly superseded drafts. Do not run historical batch generators over current originals.

All colour and grayscale outputs have been opened for visual inspection. Font and metadata checks, preserved-source hashes and unchanged-page checks are in the v4 receipt. All writes remain in figures/; no new models, fits, calibrations, bootstrap draws, manuscript embedding, P2 or P3 work. Shared handoff documents remain untouched under the figures-only boundary.
''')

checks=read_json(HERE/'P1_repository_checks_v4.json');assert all(x['exit_code']==0 for x in checks.values())
for group in ['other_figure_files','previous_A5_v3_files']:
    assert all(sha(HERE/p)==h for p,h in auth[group].items())
paths=[HERE/n for n in ['P1_FIGURES_REVIEW.md','P1_figures_review_v4.pdf','P1_figures_review.pdf',
    'P1_BATCH_HANDOFF.md','figure_inventory.csv','figure_inventory_proposal.md','figure_inventory_approval.json',
    'palette_A5_reference_v4.json','A5_color_revision_v4_authorization.json','P1_repository_checks_v4.json',
    'visual_review_checkpoint_v4.json','render_A5_palette_v4.py','p1_revision_v4_common.py','finalize_A5_palette_v4.py']]
paths.extend(p for p in (HERE/'A5').iterdir() if p.is_file())
receipt=dict(date='2026-11-27',revision=4,status='A5_reference_matched_colours_submitted_for_review',
    revised_figures=['A5'],other_figure_files_unchanged=True,verified_other_figure_files=auth['other_figure_files'],
    prior_A5_v3_files_unchanged=True,protected_inputs_unchanged=True,protected_groups=protected,
    layout_and_all_text_positions_unchanged=True,source_CSVs_unchanged=True,
    reference_colour_map_exact_match=True,cell_text_minimum_contrast=a['diagnostics']['minimum_cell_text_contrast'],
    all_nine_self_checks_passed=True,manual_colour_and_grayscale_review=True,actual_paper_print_test=False,
    other_eight_merged_pages_render_identically=True,review_collection_pdf=pdf_check,
    writes_limited_to='figures/',new_fits=0,new_bootstrap_draws=0,models_loaded=False,
    checks=checks,user_figure_approval=False,manuscript_embedding_performed=False,
    files={str(p.relative_to(HERE)):sha(p) for p in sorted(set(paths))})
write_json(HERE/'P1_redesign_delivery_receipt_v4.json',receipt)
write_json(HERE/'P1_batch_delivery_receipt.json',receipt)
print(json.dumps(dict(revised='A5',other_files_unchanged=len(auth['other_figure_files']),
    pages=pdf_check['page_count'],minimum_cell_text_contrast=a['diagnostics']['minimum_cell_text_contrast'],new_fits=0)))

