"""Package inspected P1 figure revisions; all writes remain in figures/."""
from pathlib import Path
import csv
import hashlib
import json
import re
import shutil

from PIL import Image
import pymupdf

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
IDS=['F2','F3','A1','A2','A3','A4','A5','A6']
BASES=dict(zip(IDS,['F2_enrichment','F3_error_tradeoff','A1_residual_structure',
    'A2_calibration','A3_decision_stability','A4_split_half','A5_stress_protocols','A6_ablation']))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def read_json(path):return json.loads(Path(path).read_text())
def write_json(path,x):Path(path).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def rows(path):
    with Path(path).open(newline='') as f:return list(csv.DictReader(f))


def tree_hash(path):
    files=sorted(p for p in path.rglob('*') if p.is_file()); h=hashlib.sha256()
    for p in files:h.update(str(p.relative_to(ROOT)).encode()+b'\0'+bytes.fromhex(sha(p)))
    return dict(files=len(files),bytes=sum(p.stat().st_size for p in files),sha256=h.hexdigest())


def inspect_pdf(path):
    with pymupdf.open(path) as doc:
        info=[]
        for page in doc:
            fonts=page.get_fonts(full=True)
            spans=[s for b in page.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]
            assert fonts and spans and not page.get_images()
            assert all('TimesNewRoman' in f[3] and doc.extract_font(f[0])[3] for f in fonts)
            assert page.get_text().isascii() and min(s['size'] for s in spans)>=8.49
            info.append(dict(width_mm=page.rect.width*25.4/72,height_mm=page.rect.height*25.4/72,
                             minimum_font_pt=min(s['size'] for s in spans),
                             all_fonts_embedded=True,Times_New_Roman_only=True,all_text_ascii=True,raster_images=0))
        assert not doc.metadata.get('author')
        return dict(page_count=len(doc),pages=info,personal_metadata_absent=True)


PURPOSE={
 'F2':'在相同逐折预算下比较命中与富集，并放大分辨低 EF 的两条基线。',
 'F3':'展示金属/非金属误差贡献及登记回归路线的 RMSE–EF 权衡。',
 'A1':'将 X 族的有符号偏差与 RMSE/q95 误差尺度并列比较。',
 'A2':'展示四条既有折外概率曲线与理想校准线的差异。',
 'A3':'同时展示四池名义候选的成员名次分布与双向代理 regret。',
 'A4':'用四池斜率线对照 single 与十成员均值的决策稳定性。',
 'A5':'用协议×指标矩阵展示既有压力结果及同路线 OOF 参照变化。',
 'A6':'用双向须线展示最终 H-soft 三组反向消融的既有配对区间。',
}
LEGEND={
 'F2':'浅钢蓝实线圆点=H-soft；暗琥珀虚线方块=Additive Ridge；灰绿点线倒三角=Mean；灰粉点划线叉号=Random (fixed)。砖红点线=每折预算 k=20；中性虚线=随机期望 EF=1。下方独立放大窗对应主图框选的 k=1–100、EF=0–1.5 数据范围，连接线标明对应关系；两窗颜色、点形、线型、坐标含义一致。',
 'F3':'左图：钢蓝实块=Metal (gap=0)，琥珀斜纹=Nonmetal (gap>0)，条末数字=总 MSE。右图：圆点=H-soft、方块=R-log、三角=R-raw、菱形=W-log；与实际填色及点形匹配的四项图例位于该面板下方。',
 'A1':'左侧连续色条是 Bias 的图例：负值蓝、零白、正值琥珀，每个色块保留带正负号数值。右图图例：灰绿圆点=RMSE，灰粉菱形=q95 absolute error。',
 'A2':'五项图例逐项对应 B-eps observed（蓝圆实线）、S-eps observed（琥珀方块虚线）、L-single observed（灰绿三角点划线）、L-hash4 observed（灰粉菱形点线）与 Ideal: y=x（中性虚线）。按用户“每线一个斜率数值”的要求保留单个 slope 标注；完整斜率/截距表移到伴随材料。',
 'A3':'左侧白心圆图例 Member rank 表示一个既有成员，池编号直接在纵轴。右侧两项颜色图例：蓝=Reverse cost（左半轴），琥珀=Forward cost（右半轴）；下方形状图例圆/三角/方块/竖帽分别为 p50/p90/p95/Max。左右位置只编码方向，两个 regret 原始值均非负。',
 'A4':'Pool 07=钢蓝实线圆，08=琥珀虚线方，11=灰绿点划线三角，12=灰粉点线菱形。各图例与实际连线、空心端点一致；左列 Single、右列 Mean of 10 明确对照端点，邻近数字用短引线对应真实端点。',
 'A5':'底部连续色条是百分比变化图例：蓝为负变化，白为零，琥珀为正变化。列名指定路线与原始指标；格内大数字为原始结果，小百分数为相对同路线 AB-blocked OOF 的变化，符号在灰度下仍可辨。',
 'A6':'灰色圆点与须线=CI crosses 0；琥珀方块与须线=CI above 0；钢蓝方块与须线=CI below 0。CI 指既有 95% 配对 bootstrap 区间；竖虚线为零效应，点旁数字为 removal minus full 的点估计。',
}
TYPES={
 'F2':('Enrichment curves with connected magnification','2 main panels + a boxed low-EF zoom'),
 'F3':('Steel-blue/amber stacked bars + shaped Pareto scatter','2: error contributions; RMSE-EF'),
 'A1':('Diverging heat strip + overlaid marker plot','2: signed bias; RMSE/q95 point overlay'),
 'A2':('Reliability small multiples with matched five-item legend','4: one stored probability route per panel'),
 'A3':('Rank violins + diverging quantile whiskers','2: observed ranks; reverse/forward costs'),
 'A4':('Two slope graphs','2: agreement; mean regret on a log axis'),
 'A5':('Protocol-by-metric diverging matrix heatmap','1 matrix + continuous colour legend'),
 'A6':('Two-panel forest plot','2: delta RMSE; delta equal-fold EF'),
}

old=read_json(HERE/'archive/rejected_batch_v1/P1_batch_delivery_receipt.json')
protected={name:tree_hash(ROOT/p) for name,p in {
 'p1_artifacts':'artifacts/p1_v21','p1_code':'03_求解/D/p1_v2',
 'official_D_data':'00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date'}.items()}
protected['fit_ledger_sha256']=sha(ROOT/'artifacts/p1_v21/fit_ledger.jsonl')
assert protected==old['protected_groups']
assert all(sha(HERE/p)==digest for p,digest in old['F1_verified_files'].items())
assert sha(HERE/'palette_frozen.json')==old['palette_frozen_sha256']
checkpoint=read_json(HERE/'visual_review_checkpoint_v2.json')
checks=read_json(HERE/'P1_repository_checks_v2.json')
assert all(r['exit_code']==0 for r in checks.values())
audits={}
for fid in IDS:
    a=read_json(HERE/fid/(fid+'_audit.json'))
    assert a['renderer_sha256']==sha(HERE/'render_p1_redesign.py')
    assert a['common_helper_sha256']==sha(HERE/'p1_redesign_common.py')
    for s in a['source_files']:assert sha(ROOT/s['path'])==s['sha256']
    for name,digest in a['files'].items():assert sha(HERE/fid/name)==digest
    for name,digest in checkpoint['reviewed_color_and_grayscale_pixels'][fid].items():
        p=HERE/fid/name
        with Image.open(p) as im:
            assert hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()==digest
            assert all(abs(d-300)<.1 for d in im.info['dpi'])
    a.update(status='revision_2_visually_checked_awaiting_user_review',manual_color_review=True,
             manual_grayscale_review=True,legend_matches_actual_marks=True,
             manual_no_explanatory_sentences=True,manual_no_clipping_or_label_overlap=True,
             user_figure_approval=False,nine_self_checks_passed=True,
             final_pdf_inspection=inspect_pdf(HERE/fid/(BASES[fid]+'_v2.pdf')))
    if fid=='F2':a['normative_zoom_checked']=dict(source_frame=True,connectors=True,
        zoom_coordinates_explicit=True,series_styles_identical=True,no_main_curve_obscured=True)
    write_json(HERE/fid/(fid+'_audit.json'),a)
    audits[fid]=a

for fid,a in audits.items():
    base=BASES[fid]+'_v2'
    source_list='\n'.join(f"- [{Path(s['path']).name}](../../{s['path']})" for s in a['source_files'])
    csv_list='\n'.join(f'- [{p.name}]({p.name})' for p in sorted((HERE/fid).glob('*.csv')))
    text=f'''# {fid} v2 — {a['title']}

2026-11-27。按首轮打回意见重做，已完成彩色/灰度自查，等待用户验收；F1 v3 已通过且原件未改。

用途：{PURPOSE[fid]}

[300 dpi PNG]({base}.png) · [矢量 PDF]({base}.pdf) · [完整灰度版]({base}_grayscale.png) · [审计 JSON]({fid}_audit.json)

尺寸：170 × {a['height_mm']:g} mm；Times New Roman，最小 8.5 pt。图内单词数（含数字/刻度）由 {a['rejected_v1_text_word_count']} 降至 {a['text_word_count']}；保留的文字仅用于标注。

## 图例与读法

{LEGEND[fid]}

图型：{a['design']}

## 数据来源

{source_list}

所有来源 SHA-256 已逐项核验。只有显示汇总写入本目录，没有新实验或新拟合。

{csv_list}

## Short English caption

{a['caption']}

## Reading guide and interpretation material

以下供后续正文使用，目前未嵌入论文或图内：

{a['reading_guide']}

完整配套数值见 [伴随表件](../P1_FIGURE_COMPANION_TABLES_v2.md)，图内不嵌表格。

## 九项自查

- [x] dpi：PNG 300 dpi，另附矢量 PDF。
- [x] 字号：最终 170 mm 宽度下，所有图内文字 ≥8.5 pt。
- [x] 零中文：图内全部文字为英文/数字/ASCII 符号。
- [x] 灰度可辨：已目检完整灰度渲染；形状、线型、纹理、位置或数值保留含义。
- [x] 色板：遵循本轮指定的钢蓝/琥珀/灰绿/砖红/灰粉及蓝—白—琥珀发散规则。
- [x] TNR 字体：调用 use_times_new_roman()，实际字体已核验，PDF 全部嵌入 Times New Roman。
- [x] 无 suptitle：无全图大标题，只有简短面板名。
- [x] 无嵌入表格：图内无 Table 对象、数据表或表格截图；热图为数值色标编码。
- [x] 文字预算：仅轴、图例、关键数值与面板名，没有句子级解释。

补充核对：图例逐项匹配实际图元；无棒棒糖图。灰度检查为屏幕渲染，未做实物打印。新增拟合=0；新增 bootstrap 抽样=0；仅写 figures/。
'''
    (HERE/fid/(fid+'_review.md')).write_text(text)

# Full diagnostic numbers move to companion material, never into an image.
body='''# P1 companion numeric material for redesigned figures

These are existing diagnostics and display summaries. They are not embedded in any figure or manuscript. All quantities retain their original scope and conditioning.

## F2: fold-specific uniform-null references at k=20

The event is V<=2. Each row uses one outer fold; p values are existing, unadjusted descriptive references after development selection. They are not pooled or averaged.

| Route | Fold | N | M | Hits | p |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
for r in rows(HERE/'F2/F2_fold_uniform_null.csv'):
    body+=f"| {r['route']} | {r['fold']} | {r['N']} | {r['M']} | {r['h']} | {float(r['p_uniform']):.6g} |\n"
body+='''
## A2: existing pooled diagnostic coefficients

No calibration was refitted. Only the single requested slope annotation per curve remains in the image. Bin counts and singleton high-probability bins remain documented in A2_reliability_bins.csv.

| Route | Slope | Intercept | Brier | N | Positives |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
for r in rows(HERE/'A2/A2_existing_pooled_diagnostics.csv'):
    body+=f"| {r['route']} | {float(r['calibration_slope']):.6f} | {float(r['calibration_intercept']):.6f} | {float(r['brier']):.8f} | {r['n']} | {r['n_positive']} |\n"
body+='''
## A5: protocol denominators

N and M are evaluation exposures, not necessarily unique compositions. EF omits undefined zero-positive evaluations. The heatmap is protocol-level evidence, not final-model validation.

| Protocol | Evaluations | N sum | M sum | EF defined | Total budget | Defined-EF budget |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''
for r in rows(HERE/'A5/A5_protocol_denominators.csv'):
    body+=f"| {r['protocol']} | {r['evaluations']} | {r['N_evaluated_sum']} | {r['M_evaluated_sum']} | {r['EF_defined']} | {r['total_budget']} | {r['EF_defined_budget']} |\n"
body+='''
The colour reference is the same route's frozen AB-blocked OOF metric: R-log RMSE 4.9048363921; R-log EF 60.4863492710; S-eps EF 62.2234054773. Colour is 100*(stress/reference-1), not an ease ranking across protocols.

## A6: R-log feature ladder moved out of the image

The redesigned A6 contains only reverse-ablation intervals for H-soft. This separate R-log comparison is preserved without joining the two routes into one ladder.

| Route | Feature block | RMSE | Mean EF@20 |
| --- | --- | ---: | ---: |
'''
for r in rows(HERE/'A6/A6_feature_additions.csv'):
    body+=f"| {r['route']} | {r['feature']} | {float(r['RMSE']):.6f} | {float(r['EF_macro']):.6f} |\n"
(HERE/'P1_FIGURE_COMPANION_TABLES_v2.md').write_text(body)

# Refresh the 16-column inventory; F1 acceptance is recorded outside F1/.
with (HERE/'figure_inventory.csv').open(newline='') as f:
    reader=csv.DictReader(f); fields=reader.fieldnames; inventory=list(reader)
assert len(fields)==16
for r in inventory:
    fid=r['figure_id']
    if fid=='F1':
        r['status']='user_approved_revision_3_original_unchanged'
        r['grayscale_ok']='previously checked; user approved F1 v3'
        continue
    a=audits[fid]
    r.update(figure_type=TYPES[fid][0],panels=TYPES[fid][1],caption=a['caption'],
             status=a['status'],legend_defined='yes; explicit matched keys and continuous colourbar where applicable',
             grayscale_ok='full grayscale export visually inspected; user review pending',final_width_mm='170',min_font_pt='8.5',
             data_source_version='P1 v2.1 frozen artifacts; '+'; '.join(s['path'] for s in a['source_files']))
    r['notes']=(f"title={a['title']}; tier={'main_text' if fid.startswith('F') else 'appendix'}; "
        f"model_chain={'Model establishment; Model validation' if fid=='A6' else 'Model validation'}; "
        f"revision=2; design={a['design']}; palette=palette_redesign_v2.json per latest user instruction; "
        f"output=figures/{fid}/{BASES[fid]}_v2.pdf; review=figures/{fid}/{fid}_review.md; "
        f"height_mm={a['height_mm']:g}; nine_checks=passed; new_fits=0; no_new_bootstrap=1; "
        'no_suptitle=1; no_embedded_table=1; annotation_only=1; F1_unchanged=1')
    if fid=='A1':r['axes_units']='X family; signed bias (Vhat-V); RMSE/q95 (V)'
    if fid=='A4':r['axes_units']='Single/Mean of 10; agreement fraction; mean regret (Vhat; logarithmic axis)'
    if fid=='A5':r['axes_units']='Protocol by route/metric; raw RMSE/EF; colour=percent change from matched OOF reference'
    if fid=='A6':r['axes_units']='Electronic/Geometry/X statistics removal; delta RMSE (V); delta EF_{V<=2}@20'
with (HERE/'figure_inventory.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(inventory)
write_json(HERE/'figure_inventory_sources_v2.json',{
    'date':'2026-11-27','prior_manifest_retained':'figure_inventory_sources.json',
    'source_files_by_figure':{fid:a['source_files'] for fid,a in audits.items()},
    'A5_reference_extension':'Existing main table added only for matched-reference display normalisation; no new experiment.'})
approval=read_json(HERE/'figure_inventory_approval.json')
approval.update(rendering_mode='user_authorized_eight_figure_redesign',
    superseding_authorization='figures/redesign_authorization.json',
    user_approved_figures=['F1 v3'],current_figure_status='eight_revisions_delivered_for_user_review',
    current_review_file='figures/P1_FIGURES_REVIEW.md',
    gate='F1 accepted unchanged; the eight revised figures await individual user acceptance. No manuscript embedding.')
write_json(HERE/'figure_inventory_approval.json',approval)

# Same nine-page review format, native dimensions, searchable vector text.
pdfs=[HERE/'F1/F1_data_audit_v3.pdf']+[HERE/fid/(BASES[fid]+'_v2.pdf') for fid in IDS]
with pymupdf.open() as merged:
    for p in pdfs:
        with pymupdf.open(p) as single:merged.insert_pdf(single)
    toc=[[1,'F1 v3 - accepted original',1]]+[[1,f'{fid} v2 - {audits[fid]["title"]}',i+2] for i,fid in enumerate(IDS)]
    merged.set_toc(toc)
    merged.set_metadata(dict(title='P1 figures - visual redesign v2',author='',
        subject='Accepted F1 original and eight redesigned P1 figure sheets',creator='P1 figure packaging',
        producer='PyMuPDF',keywords='',creationDate='',modDate=''))
    merged.save(HERE/'P1_figures_review_v2.pdf',garbage=4,deflate=True)
shutil.copyfile(HERE/'P1_figures_review_v2.pdf',HERE/'P1_figures_review.pdf')
pdf_check=inspect_pdf(HERE/'P1_figures_review_v2.pdf')
assert pdf_check['page_count']==9
with pymupdf.open(HERE/'P1_figures_review_v2.pdf') as merged:
    for i,p in enumerate(pdfs):
        with pymupdf.open(p) as single:
            assert merged[i].rect==single[0].rect and merged[i].get_text()==single[0].get_text()

index='''# P1 图件重改 v2：审阅索引

2026-11-27。首轮仅 F1 通过；本轮已重做 F2、F3、A1–A6，F1 v3 的图件与原审计文件保持字节不变。

**[合并审阅 PDF v2：九图九页，带书签](P1_figures_review_v2.pdf)** · [同名常用入口](P1_figures_review.pdf)

按本轮要求取消全图大标题、嵌入表格和解释段落；八图改用不同图型，并补齐与图元匹配的图例。F2 低 EF 放大窗含原图范围框、连接线及明确坐标，颜色/点形/线型与主图一致。

| 图号 | 用途与新版图型 | 图件 | 来源、caption、图例与九项自查 |
| --- | --- | --- | --- |
| F1 v3（已通过） | 数据审计与 AB 阻断；原件未动 | [PNG](F1/F1_data_audit_v3.png) / [PDF](F1/F1_data_audit_v3.pdf) / [灰度](F1/F1_data_audit_v3_grayscale.png) | [原审图单](F1/F1_review.md) |
'''
for fid in IDS:
    base=BASES[fid]+'_v2'
    index+=f'| {fid} v2 | {PURPOSE[fid]} | [PNG]({fid}/{base}.png) / [PDF]({fid}/{base}.pdf) / [灰度]({fid}/{base}_grayscale.png) | [逐图审图单]({fid}/{fid}_review.md) |\n'
total=sum(a['text_word_count'] for a in audits.values()); before=sum(a['rejected_v1_text_word_count'] for a in audits.values())
index+=f'''
全部新图：300 dpi PNG + 矢量 PDF + 完整灰度 PNG；170 mm 宽，实际 Times New Roman ≥8.5 pt。九项自查逐张列在审图单，另核对图例、局部放大与无棒棒糖图。图内单词数（含刻度和数字）合计由 {before} 降至 {total}，减少 {100*(1-total/before):.1f}%。

本轮按用户新指令采用 reference 30 的钢蓝/琥珀及辅助色家族；[配色修订记录](palette_redesign_v2.json) 明确覆盖关系。原 A 色板文件保留，F1 作为已批准原件不改。A1/A5 的连续色条本身就是图例，A3 用发散色端点与左右位置区分 regret 方向。

短 caption 和正文读法分开保存；[完整伴随诊断数字](P1_FIGURE_COMPANION_TABLES_v2.md) 不再嵌入图内。A5 的 protocol-level evidence, not final-model 限定保留在 caption。A6 只画最终 H-soft 反向消融区间，原 R-log 特征阶梯移到伴随材料。

- [当前 16 列图件清单](figure_inventory.csv)
- [本轮视觉重设计说明](P1_VISUAL_REDESIGN_v2.md)
- [新版来源清单与哈希](figure_inventory_sources_v2.json)
- [交付回执与输入保护核验](P1_redesign_delivery_receipt_v2.json)
- [完整彩色/灰度目检记录](visual_review_checkpoint_v2.json)
- [仓库检查结果](P1_repository_checks_v2.json)
- [退回版完整存档](archive/rejected_batch_v1/P1_FIGURES_REVIEW.md)

所有八图仅提交审阅，尚未宣称用户通过或嵌入论文。全程只读 artifacts、只写 figures/；模型代码、P1 artifacts、官方 D 数据及拟合账本完整哈希未变，账本仍为 914 次 start，新增拟合与 bootstrap 抽样均为 0。

复现：`PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_p1_redesign.py all`。重新渲染后须按像素与视觉检查更新审阅状态；旧版 renderer 属于历史方案，不应覆盖本轮交付。
'''
(HERE/'P1_FIGURES_REVIEW.md').write_text(index)

proposal='''# P1 图件清单：本轮重改状态

2026-11-27。用户首轮验收仅 F1 通过，F2/F3/A1–A6 全部重改。当前八张 v2 已出齐，见 [审阅索引](P1_FIGURES_REVIEW.md)。旧设计与审阅记录保存在 archive/rejected_batch_v1/，不再代表现行方案。

本轮按用户要求依次读完 references/30 全文、playbook §13–16、references/25 §25.9–25.12，并应用 SKILL §2.5 的六条视觉纪律。色板、图例和放大窗口径见 [重设计说明](P1_VISUAL_REDESIGN_v2.md)。

| 编号 | 正文/附录 | 当前图型 |
| --- | --- | --- |
| F1 | 正文 | 原数据审计图 v3：已通过，原件未动 |
'''
for fid in IDS:proposal+=f"| {fid} | {'正文' if fid.startswith('F') else '附录'} | {TYPES[fid][0]} |\n"
proposal+='''
[figure_inventory.csv](figure_inventory.csv) 保留模板的 16 列；每行包含用途、来源、图型、caption、审核状态及模型链条环节。物理页码仍留待论文排版阶段确定。本轮只做 P1 图件，不推进 P2/P3，不写论文正文或正式交付目录。
'''
(HERE/'figure_inventory_proposal.md').write_text(proposal)

(HERE/'P1_VISUAL_REDESIGN_v2.md').write_text('''# P1 visual redesign v2

2026-11-27. The user's latest visual instructions supersede the previous rejected eight-figure design. F1 v3 is accepted and remains byte-for-byte unchanged.

## Reference foundation

Read in the requested order: reference 30 in full; figure playbook sections 13-16; reference 25 sections 25.9-25.12. The required D plotting template remains the actual style foundation through apply_apmcm_style() followed by use_times_new_roman().

## Encoding decisions

- F2: four explicit route colours, shapes and dashes; labelled k=20 and EF=1 references. The low-EF window has a source-region rectangle, two connecting lines, a bounded zoom label, and the same x-coordinate semantics and series marks. It covers the original data range k=1-100, EF=0-1.5; extra axis padding is only layout space.
- F3: steel-blue metal / hatched amber nonmetal stacks; all four Pareto symbols have matched keys and direct route labels.
- A1: zero-centred blue-white-amber bias heat strip, signed values for grayscale; RMSE circles and absolute-error q95 diamonds.
- A2: only reliability observations, an ideal diagonal, route names and one requested slope annotation per curve. Full coefficients and counts move to companion numeric material. Every observed route and the ideal line has an explicit matching key.
- A3: four rank violins with all raw ranks; a fixed graphics-only kernel in log10 rank, no estimated bandwidth or model fitting. Reverse and forward costs use the blue/amber ends of the common diverging palette on opposite sides of a white zero, with explicit direction keys; intensity adds no further variable. Quantiles have four separate shape keys.
- A4: single-to-mean-of-ten slope graphs; pool identity is redundant in colour, line pattern and shape. Nearby value labels use short leaders to unchanged data coordinates.
- A5: route-specific raw metrics annotated in a matrix; colour encodes signed percentage change from the same route's existing AB-blocked OOF reference. This is not a cross-protocol difficulty ranking. Continuous colourbars count as legends, with their quantity and centre explicitly labelled.
- A6: existing bilateral 95% interval whiskers, square/circle point estimates and a vertical zero line. Grey crosses zero, amber stays above, blue stays below. There is no zero-to-point stem.

## Palette amendment

The current directive explicitly changes F2 baseline colours and F3 metal/nonmetal colours and requires steel-blue/amber/green/brick/pink families. palette_redesign_v2.json records this authorised amendment; palette_frozen.json remains the historical approval and is not overwritten. F1 is the user's explicit unchanged exception. The historical all-eight-colour Delta-E assertion is not silently attributed to the amended palette; grayscale readability is checked on each actual export using shapes, dashes, hatch, position and signed numbers.

## Delivery discipline

No overall titles, embedded tables, explanatory sentences, or lollipop plots in the revised eight figures. All figures have nine technical/design checks plus matching-legend review. Full colour and grayscale PNGs were visually inspected; no physical print test was performed. Every PDF uses embedded Times New Roman at 8.5 pt or larger and retains native 170 mm width. Sources, models, code and the fit ledger remain unchanged. All new writes are confined to figures/.
''')
(HERE/'P1_BATCH_HANDOFF.md').write_text('''# P1 figure handoff — visual redesign v2

2026-11-27. User accepted only F1 v3 and rejected the previous F2/F3/A1-A6 batch. The primary WSL agent has redesigned all eight; read P1_FIGURES_REVIEW.md for the current files and nine-item checks. F1 v3 and its original audit files are unchanged. User acceptance of the eight revisions is still pending; do not embed them or start P2/P3.

Current entry points: render_p1_redesign.py and finalize_redesign.py. The old renderer/finalizer describe the rejected design; their archived snapshots are in archive/rejected_batch_v1/. The current palette amendment implements the user's newer reference-30 instructions, and the explicit legend and connected-zoom requirements are incorporated. No new fits, calibrations or bootstrap draws were performed.

This handoff is stored under figures/ to respect the current task's explicit write boundary. Shared handoff documents outside figures/ are not edited in this plotting-only task.
''')

ledger=[json.loads(line) for line in (ROOT/'artifacts/p1_v21/fit_ledger.jsonl').read_text().splitlines()]
assert sum(r.get('event')=='start' for r in ledger)==914
receipt=dict(date='2026-11-27',revision=2,status='eight_redesigned_figures_delivered_for_user_review',
    figures=IDS,F1_status='user_approved_v3_original_unchanged',F1_files_unchanged=True,
    F1_verified_files=old['F1_verified_files'],protected_inputs_unchanged=True,protected_groups=protected,
    prior_frozen_palette_unchanged=True,palette_amendment_sha256=sha(HERE/'palette_redesign_v2.json'),
    writes_limited_to='figures/',models_loaded=False,new_fits=0,new_bootstrap_draws=0,total_ledger_fit_starts=914,
    all_nine_self_checks_passed=True,all_legends_match_actual_marks=True,
    F2_source_frame_connectors_and_coordinate_zoom_verified=True,
    manual_visual_review=dict(colour_pngs=8,full_grayscale_pngs=8,actual_paper_print_test_performed=False),
    text_words_before=before,text_words_after=total,text_reduction_fraction=1-total/before,
    review_collection_pdf=pdf_check,original_vector_pages_preserved=True,checks=checks,
    user_approval_of_revisions=False,manuscript_embedding_performed=False)
files=[p for fid in IDS for p in (HERE/fid).iterdir() if p.is_file()]
files += [HERE/p for p in ['P1_figures_review_v2.pdf','P1_figures_review.pdf','P1_FIGURES_REVIEW.md',
 'P1_FIGURE_COMPANION_TABLES_v2.md','P1_VISUAL_REDESIGN_v2.md','P1_BATCH_HANDOFF.md',
 'figure_inventory.csv','figure_inventory_proposal.md','figure_inventory_approval.json','figure_inventory_sources_v2.json',
 'palette_redesign_v2.json','redesign_authorization.json','visual_review_checkpoint_v2.json','P1_repository_checks_v2.json',
 'render_p1_redesign.py','p1_redesign_common.py','finalize_redesign.py']]
receipt['files']={str(p.relative_to(HERE)):sha(p) for p in sorted(files)}
write_json(HERE/'P1_redesign_delivery_receipt_v2.json',receipt)
shutil.copyfile(HERE/'P1_redesign_delivery_receipt_v2.json',HERE/'P1_batch_delivery_receipt.json')
for p in [HERE/'P1_FIGURES_REVIEW.md']+[HERE/fid/(fid+'_review.md') for fid in IDS]:
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
        if not target.startswith(('https:','http:','#')):assert (p.parent/target).exists(),(p,target)
print(json.dumps(dict(revised_figures=8,review_pdf_pages=9,all_nine_checks=True,all_links_valid=True,
    F1_unchanged=True,protected_inputs_unchanged=True,new_fits=0,text_reduction_pct=round(100*(1-total/before),1))))
