"""Package only F2/A1/A5 revisions; preserve every accepted figure file."""
from pathlib import Path
import csv
import hashlib
import json
import shutil
from PIL import Image
import pymupdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TARGETS = ['F2', 'A1', 'A5']
ORDER = ['F1', 'F2', 'F3', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6']
BASES = dict(zip(ORDER, ['F1_data_audit', 'F2_enrichment', 'F3_error_tradeoff',
    'A1_residual_structure', 'A2_calibration', 'A3_decision_stability',
    'A4_split_half', 'A5_stress_protocols', 'A6_ablation']))
VERSIONS = {f: 3 if f in TARGETS+['F1'] else 2 for f in ORDER}
PURPOSE = {
    'F2': '比较固定逐折预算下的近正例命中与富集，清晰展示低 EF 基线。',
    'A1': '按明确标注的 X 族，对照有符号偏差、RMSE 与绝对误差 q95。',
    'A5': '用方形矩阵展示压力协议结果及相对同路线 OOF 的变化。',
}
CHANGE = {
    'F2': '低 EF 放大区改为贴近主图的共享横轴窄带；统一左右边界，采用短竖直连接线，保留来源框及相同坐标含义。',
    'A1': '(b) 改成成对横条；每行重新标明 X 族，14 个值直接标在条末。RMSE 用实色，q95 用斜纹，避免灰度下依赖颜色辨认。',
    'A5': '改为 150 × 150 mm 方形画布和等宽高网格；蓝端提亮为 #93BED7，琥珀端采用 #E7BF8E，零点、归一化范围和数值不变。',
}
LEGEND = {
    'F2': 'H-soft=浅钢蓝实线圆点；Additive Ridge=琥珀虚线方块；Mean=灰绿点线倒三角；Random (fixed)=灰粉点划线叉号。砖红点线为 k=20；中性虚线为 EF=1。下带显示 EF=0–1.5，使用与主图相同的 log-k 横轴范围和系列样式。',
    'A1': '左色条：负偏差蓝、零白、正偏差琥珀；右图：实色灰绿横条=RMSE，斜纹灰粉横条=q95 absolute error。每组两条共用零起点，不堆叠。两面板的纵向分类均明确为 X family。',
    'A5': '底部连续色条：负变化浅蓝、零白、正变化浅琥珀。每格上方大数值为原始指标，下方带符号百分数为相对同路线 AB-blocked OOF 的变化；行标协议，列标模型路线与指标。',
}
TYPES = {
    'F2': ('Enrichment curves with integrated magnification', '2 main panels; compact shared-x low-EF strip'),
    'A1': ('Diverging bias heat strip + paired horizontal bars', '2: signed bias; explicitly labelled X-family error pairs'),
    'A5': ('Square diverging heatmap', '3-by-3 equal-aspect matrix; horizontal colourbar'),
}


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


auth = read_json(HERE/'targeted_revision_v3_authorization.json')
old = read_json(HERE/'P1_redesign_delivery_receipt_v2.json')
assert sha(HERE/'P1_redesign_delivery_receipt_v2.json') == auth['prior_receipt_sha256']
for group in ['accepted_folder_hashes', 'prior_target_v2_hashes', 'prior_source_hashes']:
    assert all(sha(HERE/p)==h for p,h in auth[group].items()), group
protected = {name:tree_hash(ROOT/p) for name,p in {
    'p1_artifacts':'artifacts/p1_v21', 'p1_code':'03_求解/D/p1_v2',
    'official_D_data':'00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date'}.items()}
protected['fit_ledger_sha256'] = sha(ROOT/'artifacts/p1_v21/fit_ledger.jsonl')
assert protected == old['protected_groups']
checkpoint = read_json(HERE/'visual_review_checkpoint_v3.json')
checks = read_json(HERE/'P1_repository_checks_v3.json')
assert all(c['exit_code']==0 for c in checks.values())
audits = {}
for fid in TARGETS:
    a = read_json(HERE/fid/(fid+'_audit_v3.json'))
    assert a['renderer_sha256']==sha(HERE/'render_p1_revision_v3.py')
    assert a['common_helper_sha256']==sha(HERE/'p1_revision_v3_common.py')
    assert a['palette_sha256']==sha(ROOT/a['palette_file'])
    for source in a['source_files']:
        assert sha(ROOT/source['path']) == source['sha256']
    for name,digest in a['files'].items():
        assert sha(HERE/fid/name)==digest
    for name,digest in checkpoint['reviewed_color_and_grayscale_pixels'][fid].items():
        with Image.open(HERE/fid/name) as im:
            assert hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()==digest
            assert all(abs(d-300)<.1 for d in im.info['dpi'])
    previous = read_json(HERE/'archive/before_targeted_v3'/fid/(fid+'_audit.json'))
    assert all(sha(HERE/fid/n)==v for n,v in previous['files'].items() if n.endswith('.csv'))
    a.update(status='revision_3_visually_checked_awaiting_user_review', manual_color_review=True,
        manual_grayscale_review=True, legend_matches_actual_marks=True, nine_self_checks_passed=True,
        manual_no_explanatory_sentences=True, manual_no_clipping_or_label_overlap=True,
        existing_display_data_unchanged=True, user_figure_approval=False,
        final_pdf_inspection=inspect_pdf(HERE/fid/(BASES[fid]+'_v3.pdf')))
    if fid=='F2':
        a['normative_zoom_checked']=dict(source_frame=True,short_connectors=True,
            same_log_x_viewport=True,zoom_coordinates_explicit=True,
            series_styles_identical=True,no_main_curve_obscured=True)
    for n in [fid+'_audit.json',fid+'_audit_v3.json']:
        write_json(HERE/fid/n,a)
    audits[fid] = a
    base = BASES[fid]+'_v3'
    sources = '\n'.join(f"- [{Path(s['path']).name}](../../{s['path']})" for s in a['source_files'])
    review = f'''# {fid} v3 — {a['title']}

2026-11-27。本轮只修订合并审阅 PDF 的第 2、4、8 页；其他六图已获用户认可并原件保留。本图 v3 待用户验收。

用途：{PURPOSE[fid]}

本次修改：{CHANGE[fid]}

文件：[300 dpi PNG]({base}.png) / [矢量 PDF]({base}.pdf) / [完整灰度 PNG]({base}_grayscale.png)。印刷尺寸 {a['width_mm']:g} × {a['height_mm']:g} mm。

数据来源（只读，哈希见 [{fid}_audit_v3.json]({fid}_audit_v3.json)）：

{sources}

图例：{LEGEND[fid]}

Caption draft: {a['caption']}

Reading guide for manuscript: {a['reading_guide']}

- [x] 300 dpi PNG，另附矢量 PDF。
- [x] 最终尺寸下字号最低 8.5 pt。
- [x] 图内全英文、ASCII，无中文或中文标点。
- [x] 已打开完整灰度图检查；颜色外另有点形/线型、纹理或带符号数值编码。
- [x] 配色与本图登记一致；F2/A1 沿用 v2，A5 按用户本轮意见登记浅色修订。
- [x] Times New Roman 实际字体，PDF 已嵌入。
- [x] 无 suptitle 或全图大标题。
- [x] 无嵌入表格。
- [x] 文字仅为轴、图例、面板名及关键数值，无句子级说明。

未进行实体纸张打印；已检查实际导出尺寸和完整灰度渲染。只读取已有结果，新增拟合、校准拟合和 bootstrap 抽样均为 0。
'''
    for n in [fid+'_review.md',fid+'_review_v3.md']:
        (HERE/fid/n).write_text(review)

with (HERE/'figure_inventory.csv').open(newline='') as f:
    reader=csv.DictReader(f); fields=reader.fieldnames; inventory=list(reader)
assert len(fields)==16
for r in inventory:
    fid=r['figure_id']
    if fid not in TARGETS:
        r['status']=f'user_approved_revision_{VERSIONS[fid]}_original_unchanged'
        r['grayscale_ok']='previously checked; user approved; original files unchanged'
        continue
    a=audits[fid]
    r.update(figure_type=TYPES[fid][0],panels=TYPES[fid][1],caption=a['caption'],
        status=a['status'],final_width_mm=str(int(a['width_mm'])),min_font_pt='8.5',
        legend_defined='yes; matched line/marker keys, solid/hatched bars, or continuous colourbar',
        grayscale_ok='full export visually inspected; styles/hatch/signed values preserve meaning')
    r['notes']=(f"title={a['title']}; tier={'main_text' if fid=='F2' else 'appendix'}; model_chain=Model validation; "
        f"revision=3; design={a['design']}; palette={a['palette_file']}; "
        f"output=figures/{fid}/{BASES[fid]}_v3.pdf; review=figures/{fid}/{fid}_review_v3.md; "
        f"height_mm={a['height_mm']:g}; nine_checks=passed; new_fits=0; new_bootstrap_draws=0; accepted_files_unchanged=1")
with (HERE/'figure_inventory.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(inventory)

approval=read_json(HERE/'figure_inventory_approval.json')
approval.update(rendering_mode='user_authorized_targeted_three_figure_revision',
    superseding_authorization='figures/targeted_revision_v3_authorization.json',
    user_approved_figures=[f'{f} v{VERSIONS[f]}' for f in ORDER if f not in TARGETS],
    current_figure_status='F2_A1_A5_revision_3_awaiting_user_review',current_figure_revision=3,
    current_review_file='figures/P1_FIGURES_REVIEW.md',
    gate='F1/F3/A2/A3/A4/A6 accepted unchanged; only F2/A1/A5 v3 await user review. No manuscript embedding.')
write_json(HERE/'figure_inventory_approval.json',approval)

pdfs=[HERE/f/(BASES[f]+f'_v{VERSIONS[f]}.pdf') for f in ORDER]
merged_path=HERE/'P1_figures_review_v3.pdf'
with pymupdf.open() as merged:
    for p in pdfs:
        with pymupdf.open(p) as single:
            merged.insert_pdf(single)
    merged.set_toc([[1,f'{fid} v{VERSIONS[fid]} - '+('revised for review' if fid in TARGETS else 'accepted, unchanged'),i+1]
                    for i,fid in enumerate(ORDER)])
    merged.set_metadata(dict(title='P1 figures - targeted revision v3',author='',
        subject='F2 A1 A5 revised; six accepted originals preserved',creator='P1 figure packaging',
        producer='PyMuPDF',keywords='',creationDate='',modDate=''))
    merged.save(merged_path,garbage=4,deflate=True)
shutil.copyfile(merged_path,HERE/'P1_figures_review.pdf')
pdf_check=inspect_pdf(merged_path)
assert pdf_check['page_count']==9
with pymupdf.open(merged_path) as merged:
    for i,p in enumerate(pdfs):
        with pymupdf.open(p) as single:
            assert merged[i].rect==single[0].rect and merged[i].get_text()==single[0].get_text()
            assert merged[i].get_pixmap().samples==single[0].get_pixmap().samples

index='''# P1 图件审阅：三处修订 v3

2026-11-27。本轮只修改第 **2、4、8 页（F2、A1、A5）**。F1 v3、F3/A2/A3/A4/A6 v2 按“其他没问题”记录为已通过；其图件及原审图单、审计文件全部保持字节不变，历史文件内的待审状态由本索引更新。

**[合并审阅 PDF v3：仍为九图九页](P1_figures_review_v3.pdf)** · [原常用入口](P1_figures_review.pdf)

| 页码 | 图件与状态 | 本轮修改/用途 | 文件 | 审图单与来源 |
| --- | --- | --- | --- | --- |
'''
for i,fid in enumerate(ORDER):
    base=BASES[fid]+f'_v{VERSIONS[fid]}'
    status='本轮修订，待验收' if fid in TARGETS else '已通过，原件保留'
    description=CHANGE[fid] if fid in TARGETS else next(r['question_answered'] for r in inventory if r['figure_id']==fid)
    review=f'{fid}/{fid}_review_v3.md' if fid in TARGETS else f'{fid}/{fid}_review.md'
    index+=f'| {i+1} | {fid} v{VERSIONS[fid]}：{status} | {description} | [PNG]({fid}/{base}.png) / [PDF]({fid}/{base}.pdf) / [灰度]({fid}/{base}_grayscale.png) | [审图单]({review}) |\n'
index+='''
三张新版均为 300 dpi PNG、矢量 PDF 和完整灰度 PNG，实际 Times New Roman ≥8.5 pt；九项自查逐张附在审图单。F2 为 170 × 118 mm，A1 为 170 × 102 mm，A5 为 150 × 150 mm。图例、图元和色条已逐项核对，灰度图已打开检查。

A5 的浅色调整只作用于本次热图，负蓝/零白/正琥珀语义和 ±80% 色标不变，见 [配色记录](palette_A5_light_v3.json)。其 protocol-level evidence, not final-model 边界仍在 caption 中，未改变统计结论。完整伴随数字继续使用 [v2 伴随材料](P1_FIGURE_COMPANION_TABLES_v2.md)。

本轮只写 figures/，数据展示 CSV 未改；模型、P1 artifacts、官方 D 数据和拟合账本哈希未变，新增拟合与 bootstrap 抽样为 0。未嵌入论文。

- [16 列图件清单](figure_inventory.csv)
- [来源与输出核验、交付回执](P1_redesign_delivery_receipt_v3.json)
- [彩色与灰度目检记录](visual_review_checkpoint_v3.json)
- [仓库检查结果](P1_repository_checks_v3.json)
- [本轮授权与已接受原件哈希](targeted_revision_v3_authorization.json)
- [修订前索引及三图审计存档](archive/before_targeted_v3/P1_FIGURES_REVIEW.md)

仅重现本次三图：`PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_p1_revision_v3.py F2 A1 A5`。旧版生成器保留用于历史复现，不要运行其 all/finalizer 覆盖已接受原件。重新渲染后须重新目检并更新像素核验记录，再运行 finalize_revision_v3.py。
'''
(HERE/'P1_FIGURES_REVIEW.md').write_text(index)
(HERE/'figure_inventory_proposal.md').write_text('''# P1 图件清单：当前验收状态

2026-11-27。按用户最新审阅，仅修订合并 PDF 第 2、4、8 页：F2 的紧贴式放大带、A1 的逐 X 族成对横条、A5 的浅色方形热图。其余六图已通过，原件和历史审计文件不改。

当前九图与状态见 [审阅索引](P1_FIGURES_REVIEW.md)；[figure_inventory.csv](figure_inventory.csv) 沿用模板的 16 列，包括用途、来源、模型链条、图型和检查状态。本次三张 v3 待验收，正文/附录定位不变。写入范围仍仅 figures/，无新拟合。
''')
(HERE/'P1_BATCH_HANDOFF.md').write_text('''# P1 figure handoff — targeted revision v3

2026-11-27. The user accepted F1 v3 and F3/A2/A3/A4/A6 v2. Every file in those six folders is preserved byte-for-byte, including historical audit/review statuses; the current index and inventory record acceptance. Only review pages 2, 4 and 8 were revised: F2 v3 integrated low-EF enlargement, A1 v3 explicitly labelled paired bars, and A5 v3 lighter square heatmap. These three revisions await user review.

Current entry: P1_FIGURES_REVIEW.md and P1_figures_review_v3.pdf; the stable PDF alias is updated. New scripts: render_p1_revision_v3.py, p1_revision_v3_common.py and finalize_revision_v3.py. They reuse the unchanged template-based v2 foundation. Do not run the historical all-figure renderer/finalizer over accepted originals. Previous outputs and scripts remain available, with index/audit snapshots under archive/before_targeted_v3/.

The A5-only light blue-white-amber adjustment is recorded in palette_A5_light_v3.json. Signed scale, source values, data transformations and all statistical conclusions remain unchanged. No models loaded, fits, calibration fits or bootstrap draws. All writes remain in figures/; protected model/data/ledger hashes are checked in the v3 receipt. No manuscript embedding or P2/P3 work. This local handoff respects the figures-only write boundary; shared handoff documents are untouched.
''')

for group in ['accepted_folder_hashes','prior_target_v2_hashes','prior_source_hashes']:
    assert all(sha(HERE/p)==h for p,h in auth[group].items()),group
tracked=[HERE/n for n in ['P1_FIGURES_REVIEW.md','P1_figures_review_v3.pdf','P1_figures_review.pdf',
    'figure_inventory.csv','figure_inventory_proposal.md','figure_inventory_approval.json','P1_BATCH_HANDOFF.md',
    'render_p1_revision_v3.py','p1_revision_v3_common.py','finalize_revision_v3.py',
    'palette_A5_light_v3.json','visual_review_checkpoint_v3.json','targeted_revision_v3_authorization.json',
    'P1_repository_checks_v3.json']]
tracked += [p for fid in TARGETS for p in (HERE/fid).iterdir() if p.is_file()]
receipt=dict(date='2026-11-27',revision=3,status='three_targeted_revisions_delivered_for_user_review',
    revised_figures=TARGETS,accepted_unchanged=auth['accepted_unchanged'],page_order=ORDER,current_revisions=VERSIONS,
    accepted_original_files_verified=auth['accepted_folder_hashes'],accepted_original_files_unchanged=True,
    prior_versioned_figures_unchanged=True,prior_shared_renderer_and_palette_unchanged=True,
    existing_display_data_unchanged=True,protected_inputs_unchanged=True,protected_groups=protected,
    writes_limited_to='figures/',models_loaded=False,new_fits=0,new_bootstrap_draws=0,total_ledger_fit_starts=914,
    all_nine_self_checks_passed=True,all_legends_match_actual_marks=True,
    manual_color_and_grayscale_review=True,actual_paper_print_test_performed=False,
    original_vector_pages_preserved=True,merged_page_rendering_identical_to_source=True,
    review_collection_pdf=pdf_check,checks=checks,
    user_approval_of_three_revisions=False,manuscript_embedding_performed=False,
    files={str(p.relative_to(HERE)):sha(p) for p in sorted(set(tracked))})
write_json(HERE/'P1_redesign_delivery_receipt_v3.json',receipt)
write_json(HERE/'P1_batch_delivery_receipt.json',receipt)
print(json.dumps(dict(revised=TARGETS,accepted_files_unchanged=len(auth['accepted_folder_hashes']),
    protected_inputs_unchanged=True,pages=pdf_check['page_count'],new_fits=0),ensure_ascii=False))
