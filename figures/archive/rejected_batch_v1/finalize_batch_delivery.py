"""Package the already rendered and visually inspected P1 figures.

This utility only reads protected inputs and writes review material in figures/.
It does not render figures, load models, fit calibrators, or resample data.
"""
from pathlib import Path
import csv
import hashlib
import json

from PIL import Image
import pymupdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
IDS = ['F2', 'F3', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6']
DATE = '2026-11-27'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def tree_hash(folder):
    files = sorted(p for p in folder.rglob('*') if p.is_file())
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(ROOT)).encode() + b'\0' + bytes.fromhex(sha(p)))
    return dict(files=len(files), bytes=sum(p.stat().st_size for p in files), sha256=h.hexdigest())


def inspect_pdf(path):
    with pymupdf.open(path) as doc:
        pages = []
        for pg in doc:
            fonts = pg.get_fonts(full=True)
            spans = [s for b in pg.get_text('dict')['blocks'] if b['type'] == 0
                     for line in b['lines'] for s in line['spans']]
            assert fonts and spans
            assert all('TimesNewRoman' in f[3] and doc.extract_font(f[0])[3] for f in fonts)
            assert min(s['size'] for s in spans) >= 8.49
            assert pg.get_text().isascii() and not pg.get_images()
            pages.append(dict(width_mm=pg.rect.width * 25.4 / 72,
                              height_mm=pg.rect.height * 25.4 / 72,
                              minimum_font_pt=min(s['size'] for s in spans),
                              fonts=sorted({f[3] for f in fonts}), raster_images=0,
                              all_text_ascii=True, all_fonts_embedded=True))
        assert not doc.metadata.get('author')
        return dict(pages=pages, page_count=len(doc), personal_metadata_absent=True)


PURPOSES = {
    'F2': '在相同逐折预算下，对比 H-soft 与三种基线的命中数和近正例富集。',
    'F3': '同时展示金属/非金属的误差贡献及登记回归路线的 RMSE–EF 权衡。',
    'A1': '定位七个 X 族的有符号偏差、RMSE 与绝对残差 q95 差异。',
    'A2': '用既有折外概率检查四条筛选路线的概率刻度与拼接一致性。',
    'A3': '结合全部成员的名次及双向代理 regret，判断四池候选轮换的代价。',
    'A4': '对比十成员均值和单成员参照的 argmin 一致率与跨表 regret。',
    'A5': '在明确分母及模型范围的前提下报告三种压力协议的结果。',
    'A6': '分开呈现 R-log 的特征增量与最终 H-soft 的三组反向消融。',
}

LEGENDS = {
    'F2': 'H-soft：浅蓝实线、实心圆；Additive Ridge：灰色虚线、空心方块；Mean：灰色点线、空心倒三角；Random (fixed)：灰色点划线、叉号。水平细虚线表示随机期望 EF=1，竖点线定位每折 k=20。局部放大保留 Mean/Random 的同一套图例。',
    'F3': '误差堆叠条：紫色斜纹为 Metal 的 SSE/总 N，浅绿色点纹为 Nonmetal 的 SSE/总 N，条末数字为总 MSE。散点直接标模型名：H-soft 为浅蓝实心圆，R-log 为空心方块，R-raw 为空心三角，W-log 为空心菱形。',
    'A1': '三个面板分别直接命名 Bias、RMSE、q95；所有浅蓝条均表示同一 H-soft 路线。横向位置给出数值，左侧为 X 族，点线表示零偏差。不存在另一条未命名比较系列。',
    'A2': '浅蓝圆点折线为每个非空概率箱的 Observed frequency，灰色虚线为 Ideal calibration: y=x。每个小面板标题为路线名称；下方 n 按从低到高的十个箱依次列出。',
    'A3': '左面板每个点为一个既有成员给名义候选的名次，仅竖向错开重叠点；横轴为对数名次。右面板圆/三角/方块/叉号分别为 p50/p90/p95/max。F 用实线实心标记，表示名义选择在成员表中的代价；R 用虚线空心标记，表示成员选择在名义表中的代价。点线为 0.1 描述性容忍值。',
    'A4': '浅蓝实心圆为 Mean of 10 members，灰色空心方块为 Single-member reference。两面板点和数字均为既有均值；右面板竖线为既有切分的 p50–p95 描述性范围。',
    'A5': '纯浅蓝柱为 R-log，浅蓝斜纹柱为 S-eps；左面板只报告 R-log 的 RMSE。横轴直接命名 Element、Target、X-leave，下方表格给出各自评价次数、样本暴露量与预算。',
    'A6': '上排直接标出 R-log 的 F0、F3、F3+E1；下排直接标出 H-soft 的去电子、去几何、去 X 统计。浅蓝点为观测差值，横线为已存在的 95% 配对区间，点状竖线为零差异；正负号统一为 removal minus full。',
}

sources = read_json(HERE / 'figure_inventory_sources.json')['sources_and_filters']
auth = read_json(HERE / 'batch_rendering_authorization.json')
assert auth['status'] == 'approved_for_remaining_batch_rendering' and auth['figures'] == IDS
old_receipt = read_json(HERE / 'F1/F1_delivery_receipt.json')
palette_sha = sha(HERE / 'palette_frozen.json')
assert palette_sha == old_receipt['palette_frozen_sha256']

# Protect the source tree and F1 against accidental changes during packaging.
protected = {name: tree_hash(ROOT / path) for name, path in {
    'p1_artifacts': 'artifacts/p1_v21',
    'p1_code': '03_求解/D/p1_v2',
    'official_D_data': '00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date',
}.items()}
protected['fit_ledger_sha256'] = sha(ROOT / 'artifacts/p1_v21/fit_ledger.jsonl')
assert protected == old_receipt['protected_groups']
f1_files = {name: digest for name, digest in old_receipt['files'].items() if name.startswith('F1/')}
assert all(sha(HERE / name) == digest for name, digest in f1_files.items())

checkpoint = read_json(HERE / 'visual_review_checkpoint.json')
for fid in IDS:
    pixels = {p.name: hashlib.sha256(Image.open(p).convert('RGB').tobytes()).hexdigest()
              for p in (HERE / fid).glob('*.png')}
    assert len(pixels) == 2
    if fid in checkpoint['reviewed_color_and_grayscale_pixels']:
        assert pixels == checkpoint['reviewed_color_and_grayscale_pixels'][fid]
    else:
        # F2/F3 final color and full grayscale renders were explicitly inspected
        # immediately before invoking this packaging utility.
        assert fid in ['F2', 'F3']
        checkpoint['reviewed_color_and_grayscale_pixels'][fid] = pixels
checkpoint['review_scope'] = 'All eight final color and full grayscale PNGs; no physical print test.'
write_json(HERE / 'visual_review_checkpoint.json', checkpoint)

audits = {}
review_links = []
for fid in IDS:
    folder = HERE / fid
    a = read_json(folder / (fid + '_audit.json'))
    assert a['palette_sha256'] == palette_sha
    assert a['renderer_sha256'] == sha(HERE / 'render_remaining.py')
    assert a['common_helper_sha256'] == sha(HERE / 'p1_plot_common.py')
    for s in a['source_files']:
        assert sha(ROOT / s['path']) == s['sha256']
    for name, digest in a['files'].items():
        assert sha(folder / name) == digest
    pdf = next(name for name in a['files'] if name.endswith('.pdf'))
    png = pdf[:-4] + '.png'
    gray = pdf[:-4] + '_grayscale.png'
    for name in [png, gray]:
        with Image.open(folder / name) as im:
            assert all(abs(d - 300) < .1 for d in im.info['dpi'])
            assert list(im.size) == a['pixels']
    pdf_inspection = inspect_pdf(folder / pdf)
    assert pdf_inspection['page_count'] == 1
    a.update(status='visually_checked_awaiting_user_batch_review', manual_color_review=True,
             manual_grayscale_review=True, user_figure_approval=False,
             actual_paper_print_test_performed=False,
             legend_matches_marks=True, no_text_clipping_observed=True,
             pdf_final_inspection=pdf_inspection,
             batch_authorization='figures/batch_rendering_authorization.json')
    write_json(folder / (fid + '_audit.json'), a)
    audits[fid] = a
    s = sources[fid]
    source_list = '\n'.join(f"- [{Path(r['path']).name}](../../{r['path']})" for r in a['source_files'])
    display_list = '\n'.join(f'- [{name}]({name})' for name in a['files'] if name.endswith('.csv'))
    doc = f'''# {fid} — {a['title']}

{DATE}。已按“后面几个图直接一口气全出”的授权制作并完成彩色/灰度自查，提交用户批量审阅；自查不等于用户已批准入稿。

用途：{PURPOSES[fid]} 定级：{'正文图' if fid.startswith('F') else '附录图'}。支撑环节：{s['model_chain']}。

## 图件

[300 dpi PNG]({png}) · [矢量 PDF]({pdf}) · [完整灰度版]({gray}) · [机器审计]({fid}_audit.json)

印刷尺寸 {a['width_mm']:g} × {a['height_mm']:g} mm；全部使用 Times New Roman，最小 {a['minimum_font_pt']:g} pt。按此尺寸排版，不再缩小字体。

## 图例指代

{LEGENDS[fid]}

## 数据来源与口径

{source_list}

- 过滤：{s['filter']}
- 汇总：{s['aggregation']}
- 声称边界：{s['claim_limits']}

来源 SHA-256 逐项匹配批准清单，展示派生表仅写在本目录：

{display_list}

## English caption draft

{a['caption']}

## 提交自查

- [x] dpi：PNG 为 300 dpi，另附纯矢量 PDF。
- [x] 字号：实际 Times New Roman 字体已核验并嵌入 PDF，最小 {a['minimum_font_pt']:g} pt。
- [x] 零中文：图内全部文本为 ASCII 英文及数字/符号。
- [x] 灰度可辨：已查看完整灰度渲染；线型、点形、纹理或直接标签对应图例。
- [x] 色板一致：冻结 A 的语义色与中性描边；色板哈希保持不变。

已检查标签与图形无明显遮挡、文字不越出画布。灰度检查为屏幕渲染检查，尚未做实物打印。模型加载为 0，新增拟合与 bootstrap 抽样均为 0。
'''
    (folder / (fid + '_review.md')).write_text(doc)
    review_links.append(f"| {fid} | {PURPOSES[fid]} | [PNG]({fid}/{png}) / [PDF]({fid}/{pdf}) / [灰度]({fid}/{gray}) | [caption、来源与自查]({fid}/{fid}_review.md) |")

# Keep the approved 16-column schema and F1 row intact.
with (HERE / 'figure_inventory.csv').open(newline='') as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    inventory = list(reader)
assert len(fields) == 16
for row in inventory:
    fid = row['figure_id']
    if fid not in IDS:
        continue
    a = audits[fid]
    row.update(status=a['status'], caption=a['caption'],
               legend_defined='yes; explicit local keys, matched shapes/line styles/hatches, and direct series labels',
               grayscale_ok='rendered and visually checked; user batch review pending',
               final_width_mm='170', min_font_pt='8.5')
    suffix = (f"; delivered=figures/{fid}/{fid}_review.md; actual_height_mm={a['height_mm']:g}; "
              'rendering=batch_authorized; authorization=figures/batch_rendering_authorization.json; '
              'new_fits=0; new_bootstrap_draws=0')
    if '; delivered=' in row['notes']:
        row['notes'] = row['notes'].split('; delivered=')[0]
    row['notes'] += suffix
with (HERE / 'figure_inventory.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(inventory)

approval = read_json(HERE / 'figure_inventory_approval.json')
approval.setdefault('historical_gate', approval['gate'])
# The status and original approved hashes are historical and retained so the
# already-delivered F1 renderer remains reproducible.
approval.update(rendering_mode='batch_remaining_authorized',
                superseding_authorization='figures/batch_rendering_authorization.json',
                gate='Remaining figures rendered in one authorized batch; all figures await user review before manuscript embedding.',
                current_figure='F1, F2, F3, A1-A6',
                current_figure_status='batch_delivered_for_user_review',
                current_review_file='figures/P1_FIGURES_REVIEW.md',
                current_figure_revision=None,
                status_field_scope='Historical inventory approval; current rendering cadence is defined by rendering_mode and superseding_authorization.')
write_json(HERE / 'figure_inventory_approval.json', approval)

# Concatenate vector pages without scaling, annotations, or manuscript insertion.
all_ids = ['F1'] + IDS
pdfs = [HERE / 'F1/F1_data_audit_v3.pdf'] + [next((HERE / f).glob('*.pdf')) for f in IDS]
out_pdf = HERE / 'P1_figures_review.pdf'
with pymupdf.open() as result:
    for path in pdfs:
        with pymupdf.open(path) as single:
            result.insert_pdf(single)
    result.set_toc([[1, f'{fid}: {sources[fid]["title"]}', i + 1] for i, fid in enumerate(all_ids)])
    result.set_metadata(dict(title='P1 figures - review collection', author='',
                             subject='Nine P1 figure sheets at their native print dimensions',
                             creator='P1 figure packaging', producer='PyMuPDF',
                             keywords='', creationDate='', modDate=''))
    result.save(out_pdf, garbage=4, deflate=True)
pdf_check = inspect_pdf(out_pdf)
assert pdf_check['page_count'] == 9
with pymupdf.open(out_pdf) as merged:
    for i, path in enumerate(pdfs):
        with pymupdf.open(path) as single:
            assert merged[i].get_text() == single[0].get_text()
            assert merged[i].rect == single[0].rect

index = '''# P1 图件批量审阅索引

2026-11-27。按用户“后面几个图直接一口气全出”的新授权，F2、F3、A1–A6 八张已完成，F1 v3 原件保留。

**[连续翻阅 PDF：九图、九页、带书签](P1_figures_review.pdf)**。各页保留原矢量图和 170 mm 宽度，字体最小 8.5 pt；这是审阅合集，尚未嵌入论文。

| 编号 | 用途 | 图件 | 审图单 |
| --- | --- | --- | --- |
| F1 v3（原件） | 展示数据分布、类别构成及 AB 阻断协议。 | [PNG](F1/F1_data_audit_v3.png) / [PDF](F1/F1_data_audit_v3.pdf) / [灰度](F1/F1_data_audit_v3_grayscale.png) | [caption、来源与自查](F1/F1_review.md) |
''' + '\n'.join(review_links) + '''

八张新图均已检查：300 dpi PNG、白底矢量 PDF、Times New Roman ≥8.5 pt、图内零中文、完整灰度渲染可辨、冻结 A 色板。图例用名称配合线型、点形或纹理，不依赖颜色单独识别。每张审图单都附数据来源、过滤/汇总口径、英文结论式 caption 和五项自查。

F2 的筛选事件统一为 V<=2；k=20 是每折预算，五折共 100 次选择。F3 的 MSE 贡献使用总 N 作分母。A2 未重拟合校准器；A3/A4 的 regret 是代理表尺度；A5 保留 protocol-level evidence, not final-model；A6 的特征增量与反向消融分属不同路线，区间直接取既有结果。

本次只读既有 artifacts，只写 figures/；模型代码、全部 P1 artifacts、官方 D 数据与拟合账本的完整哈希保持不变。账本仍为 914 次 start，新增拟合及 bootstrap 抽样为 0。F1 的原件及其审计文件哈希未变；新授权替代了原逐张等候门禁，自查状态不代表用户已批准入稿。

- [更新后的 16 列图件清单](figure_inventory.csv)
- [批量制图授权](batch_rendering_authorization.json)
- [交付回执与输入保护核验](P1_batch_delivery_receipt.json)
- [彩色/灰度目检记录](visual_review_checkpoint.json)
- [仓库检查结果](P1_repository_checks.json)
- [仅 figures/ 的接续说明](P1_BATCH_HANDOFF.md)

复现绘图：`PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_remaining.py all`。重新渲染会将图件状态重置为待目检；须重新核验后再交付。屏幕灰度检查已完成，未做实物打印。
'''
(HERE / 'P1_FIGURES_REVIEW.md').write_text(index)
(HERE / 'P1_BATCH_HANDOFF.md').write_text('''# P1 figure handoff

2026-11-27. The primary WSL agent completed F2, F3 and A1-A6 under the user's explicit batch-rendering authorization. Read P1_FIGURES_REVIEW.md for all final files, captions and checks. F1 v3 was preserved byte-for-byte. Every figure remains subject to user review before manuscript embedding.

The current authorization supersedes only the earlier sequential rendering gate. The frozen palette A, Times New Roman, 300 dpi, source hashes, model/data boundaries and no-new-fit requirement remain in effect. No P2/P3 work was performed. All writes remain under figures/; this local handoff respects that narrower scope rather than modifying the shared handoff outside figures/.

Do not regenerate palette candidates or silently overwrite frozen sources. The existing renderer verifies every approved data-source hash. The display CSVs are presentation aggregates, not new experiment results. The receipt documents protected tree hashes, unchanged ledger and required repository checks.
''')

checks = read_json(HERE / 'P1_repository_checks.json')
assert all(value['exit_code'] == 0 for value in checks.values())
ledger = [json.loads(line) for line in (ROOT / 'artifacts/p1_v21/fit_ledger.jsonl').read_text().splitlines()]
assert sum(r.get('event') == 'start' for r in ledger) == 914
receipt = dict(date=DATE, figures=IDS, included_unchanged='F1 v3',
               status='delivered_for_user_batch_review',
               authorization='figures/batch_rendering_authorization.json',
               writes_limited_to='figures/', models_loaded=False, new_fits=0,
               new_bootstrap_draws=0, total_ledger_fit_starts=914,
               protected_inputs_unchanged=True, protected_groups=protected,
               F1_files_unchanged=True, F1_verified_files=f1_files,
               palette_frozen_sha256=palette_sha, checks=checks,
               manual_visual_review=dict(color_pngs=8, full_grayscale_pngs=8,
                                         legend_matches_marks=True,
                                         actual_paper_print_test_performed=False),
               review_collection_pdf=pdf_check, individual_pdf_pages_preserved=True,
               manuscript_embedding_performed=False, user_figure_approval=False)
tracked = [p for fid in IDS for p in (HERE / fid).iterdir() if p.is_file()]
tracked += [HERE / name for name in ['P1_figures_review.pdf', 'P1_FIGURES_REVIEW.md',
             'P1_BATCH_HANDOFF.md', 'figure_inventory.csv', 'figure_inventory_approval.json',
             'figure_inventory_proposal.md', 'batch_rendering_authorization.json',
             'visual_review_checkpoint.json', 'P1_repository_checks.json',
             'render_remaining.py', 'p1_plot_common.py', 'finalize_batch_delivery.py']]
receipt['files'] = {str(p.relative_to(HERE)): sha(p) for p in sorted(tracked)}
write_json(HERE / 'P1_batch_delivery_receipt.json', receipt)
print(json.dumps(dict(new_figures=len(IDS), review_pdf_pages=9,
                      protected_inputs_unchanged=True, F1_unchanged=True,
                      all_pdfs_embedded_Times_New_Roman=True,
                      new_fits=0, new_bootstrap_draws=0)))
