"""APMCM palette comparison, built on the mandatory D figure template.

Synthetic design geometry only; no experimental tables, models, or fit calls.
All writes (including the Matplotlib cache) stay inside figures/.
"""
from pathlib import Path
import os
import sys
import json
import csv
import hashlib
import importlib.util

HERE = Path(__file__).resolve().parent
SOURCE = Path('/mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm')
TEMPLATE = SOURCE / 'assets/apmcm_d_plot_templates.py'
os.environ['MPLCONFIGDIR'] = str(HERE / '.cache/matplotlib')
os.environ['MPLBACKEND'] = 'Agg'
sys.dont_write_bytecode = True

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import patheffects
from matplotlib.text import Text
from matplotlib.font_manager import findfont, FontProperties
from PIL import Image, ImageCms, PngImagePlugin

spec = importlib.util.spec_from_file_location('apmcm_d_plot_templates', TEMPLATE)
template = importlib.util.module_from_spec(spec)
spec.loader.exec_module(template)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def linearise(x):
    x = np.asarray(x, dtype=float)
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)


def encode(x):
    x = np.asarray(x, dtype=float)
    return np.where(x <= .0031308, 12.92 * x, 1.055 * np.maximum(x, 0) ** (1 / 2.4) - .055)


def lightness(y):
    y = np.asarray(y)
    return np.where(y > (6 / 29) ** 3, 116 * np.cbrt(y) - 16, (29 / 3) ** 3 * y)


def colour_record(hex_value):
    rgb = np.array([int(hex_value[i:i + 2], 16) for i in (1, 3, 5)])
    lin = linearise(rgb / 255)
    xyz = lin @ np.array([[.4124564, .2126729, .0193339],
                         [.3575761, .7151522, .1191920],
                         [.1804375, .0721750, .9503041]])
    ratios = xyz / np.array([.95047, 1., 1.08883])
    delta = 6 / 29
    f = np.where(ratios > delta ** 3, np.cbrt(ratios), ratios / (3 * delta ** 2) + 4 / 29)
    lab = np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])
    # XYZ Y is used for L* and the matched grayscale. W3C Y is used for contrast.
    y_contrast = float(lin @ [.2126, .7152, .0722])
    gray = int(round(float(encode(xyz[1])) * 255))
    return dict(hex=hex_value, rgb=rgb.tolist(), Lab=lab.tolist(), L_star=float(lab[0]),
                C_ab=float(np.hypot(lab[1], lab[2])), Y_XYZ=float(xyz[1]),
                Y_contrast=y_contrast, gray8=gray, gray_hex=f'#{gray:02X}{gray:02X}{gray:02X}',
                gray8_L_star=float(lightness(linearise(gray / 255))),
                white_contrast=1.05 / (y_contrast + .05),
                black_contrast=(y_contrast + .05) / .05)


def assess(cfg):
    assessed = []
    ids = [r['id'] for r in cfg['roles']]
    for candidate in cfg['candidates']:
        roles = [dict(**role, **colour_record(hx)) for role, hx in zip(cfg['roles'], candidate['colours'])]
        lab = np.array([r['Lab'] for r in roles])
        de = np.linalg.norm(lab[:, None] - lab[None, :], axis=-1)
        dl = np.abs(lab[:, None, 0] - lab[None, :, 0])
        pairs = [dict(first=ids[i], second=ids[j], delta_E76=float(de[i, j]),
                      delta_L_star=float(dl[i, j])) for i in range(8) for j in range(i + 1, 8)]
        gray_pairs = []
        for first, second in cfg['grayscale_pairs']:
            a, b = roles[ids.index(first)], roles[ids.index(second)]
            gray_pairs.append(dict(first=first, second=second,
                delta_L_star=abs(a['L_star'] - b['L_star']),
                delta_L_star_quantized_gray8=abs(a['gray8_L_star'] - b['gray8_L_star']),
                delta_gray8=abs(a['gray8'] - b['gray8'])))
        min_de = min(p['delta_E76'] for p in pairs)
        assert min_de >= cfg['minimum_pairwise_delta_E76'], (candidate['id'], min_de)
        assert min(p['delta_L_star'] for p in gray_pairs) >= 15
        assert min(p['delta_L_star_quantized_gray8'] for p in gray_pairs) >= 15
        assessed.append(dict(**candidate, roles=roles, delta_E76_matrix=de.tolist(),
            delta_L_star_matrix=dl.tolist(), pairs=pairs, grayscale_pairs=gray_pairs,
            mean_L_star=float(lab[:, 0].mean()), minimum_delta_E76=min_de,
            minimum_comparison_delta_L_star=min(p['delta_L_star'] for p in gray_pairs),
            all_28_delta_E76_pass=True, all_3_grayscale_pairs_pass=True,
            all_28_grayscale_pairs_pass=all(p['delta_L_star'] >= 15 for p in pairs),
            lightest_role=max(roles, key=lambda r: r['L_star'])['id'],
            minimum_raw_white_contrast=min(r['white_contrast'] for r in roles)))
    return assessed


def curve(ax, x, y, role, cfg, *, raw=False, lw=None, marker=True):
    lw = cfg['thin_line_core_pt'] if lw is None else lw
    line, = ax.plot(x, y, color=role['hex'], lw=lw, ls=role['linestyle'],
        marker=role['marker'] if marker else None, ms=4.2,
        markeredgecolor=cfg['outline'], markeredgewidth=.45,
        markerfacecolor=role['hex'], solid_capstyle='round', zorder=3)
    if not raw and role['white_contrast'] < cfg['outline_trigger_white_contrast']:
        line.set_path_effects([patheffects.Stroke(linewidth=lw + .6, foreground=cfg['outline']),
                               patheffects.Normal()])
    return line


def draw_candidate(fig, candidate, top, cfg):
    roles = candidate['roles']; by_id = {r['id']: r for r in roles}
    ink = cfg['ink']; edge = cfg['outline']
    fig.text(.06, top, f"{candidate['id']}  {candidate['name']}", fontsize=11.5,
             weight='bold', va='top')
    fig.text(.98, top - .002,
        f"Min dE76 {candidate['minimum_delta_E76']:.2f} | Mean L* {candidate['mean_L_star']:.1f}",
        ha='right', va='top', fontsize=8.5)

    # Colour and equal-lightness grayscale for every role, at the same size in A/B/C.
    strip = fig.add_axes([.055, top - .095, .93, .068])
    strip.set(xlim=(0, 8), ylim=(0, 1)); strip.axis('off')
    for i, role in enumerate(roles):
        strip.text(i + .5, .99, role['short'], ha='center', va='top', fontsize=8.5)
        text_colour = 'white' if role['white_contrast'] > role['black_contrast'] else 'black'
        for y, colour, label in [(.405, role['hex'], role['hex']),
                                  (.04, role['gray_hex'], f"L* {role['L_star']:.1f}")]:
            strip.add_patch(Rectangle((i + .035, y), .93, .28,
                                     facecolor=colour, edgecolor=edge, lw=.4))
            strip.text(i + .5, y + .14, label, ha='center', va='center',
                       fontsize=8.5, color=text_colour)

    # Shared axis geometry ensures an honest side-by-side palette comparison.
    axes = [fig.add_axes([x, top - .235, .181, .105]) for x in (.08, .315, .55, .785)]
    for ax, title in zip(axes, ('(i) Lines', '(ii) Scatter', '(iii) Bars', '(iv) Band')):
        ax.set_title(title, loc='left', fontsize=9.5, pad=5)
        ax.set(ylim=(0, 1), yticks=[0, .5, 1])
        ax.set_yticklabels(['0', '.5', '1'])
        ax.tick_params(length=2.5, pad=2, labelsize=8.5)
        for spine in ax.spines.values():
            spine.set_linewidth(.55); spine.set_color(edge)

    x = np.arange(5)
    ax = axes[0]
    curve(ax, x, [.16, .30, .50, .65, .79], by_id['S'], cfg)
    curve(ax, x, [.12, .26, .32, .44, .50], by_id['B'], cfg)
    ax.text(4.2, .79, 'S', fontsize=8.5, va='center')
    ax.text(4.2, .50, 'B', fontsize=8.5, va='center')
    ax.set(xlim=(-.25, 4.65), xticks=[0, 2, 4])

    ax = axes[1]
    for rid, xx, yy in [('M', [.9, 1.5, 2.1, 2.8], [.18, .28, .16, .30]),
                       ('N', [1.2, 1.9, 2.6, 3.3], [.59, .71, .65, .81])]:
        r = by_id[rid]
        ax.scatter(xx, yy, s=23, marker=r['marker'], facecolors=r['hex'],
                   edgecolors=edge, linewidths=.45, zorder=4)
        ax.text(3.75, yy[-1], rid, ha='left', va='center', fontsize=8.5)
    ax.scatter([3.5], [.52], s=53, marker='*', color=by_id['P']['hex'],
               edgecolors=edge, linewidths=.55, zorder=5)
    curve(ax, [0, 4.4], [.41, .41], by_id['W'], cfg, marker=False, lw=1.1)
    ax.text(.12, .43, 'W', fontsize=8.5, va='bottom')
    ax.set(xlim=(0, 4.5), xticks=[0, 2, 4])

    ax = axes[2]
    ax.bar([0, 1], [.65, .84], width=.54,
           color=[by_id['Q']['hex'], by_id['C']['hex']], edgecolor=edge, linewidth=.5)
    for i, value in enumerate((.65, .84)):
        ax.text(i, value + .035, f'{value:.2f}', ha='center', fontsize=8.5)
    ax.set(xlim=(-.7, 1.7), xticks=[0, 1], xticklabels=['Q', 'C'])

    ax = axes[3]
    xx = np.linspace(0, 4, 50); yy = .19 + .14 * xx
    ax.fill_between(xx, yy - .11, yy + .11, color=by_id['S']['hex'], alpha=.30,
                    edgecolor='none', zorder=1)
    ax.plot(xx, yy - .11, color=edge, lw=.4, zorder=2)
    ax.plot(xx, yy + .11, color=edge, lw=.4, zorder=2)
    curve(ax, [0, 2, 4], [.19, .47, .75], by_id['S'], cfg)
    curve(ax, [0, 2, 4], [.15, .31, .51], by_id['B'], cfg)
    ax.text(.2, .92, 'alpha = .30', fontsize=8.5, va='top')
    ax.set(xlim=(-.2, 4.2), xticks=[0, 2, 4])

    # The raw and outlined lightest-colour specimens expose the white contrast
    # trade-off; the neutral border never changes the reported raw colour value.
    test = fig.add_axes([.06, top - .280, .92, .023])
    test.set(xlim=(0, 1), ylim=(0, 1)); test.axis('off')
    p = by_id[candidate['lightest_role']]
    test.text(0, .75, f"Lightest {p['id']} | white CR {p['white_contrast']:.2f}:1", fontsize=8.5, va='center')
    curve(test, [.39, .48], [.75, .75], p, cfg, raw=True, marker=False)
    test.text(.50, .75, 'Raw', va='center', fontsize=8.5)
    curve(test, [.63, .72], [.75, .75], p, cfg, marker=False)
    test.text(.74, .75, 'Outlined (required)', va='center', fontsize=8.5)
    if candidate['id'] != 'C':
        fig.add_artist(plt.Line2D([.06, .98], [top - .289, top - .289],
                                 transform=fig.transFigure, color='#DDE2E6', lw=.5))


def matrix_markdown(ids, values):
    rows = ['| ID | ' + ' | '.join(ids) + ' |', '| --- | ' + ' | '.join(['---:'] * len(ids)) + ' |']
    for rid, row in zip(ids, values):
        rows.append('| ' + rid + ' | ' + ' | '.join(f'{v:.2f}' for v in row) + ' |')
    return '\n'.join(rows)


def write_proposal(cfg, candidates, audit):
    ids = [r['id'] for r in cfg['roles']]
    summary = []
    for c in candidates:
        gray = c['grayscale_pairs']
        summary.append(f"| {c['id']} {c['zh']} | {c['mean_L_star']:.2f} | {c['minimum_delta_E76']:.2f} | "
            + ' / '.join(f"{p['delta_L_star']:.2f}" for p in gray)
            + f" | {c['minimum_raw_white_contrast']:.2f}:1 |")
    text = '''# P1/P2/P3 统一色板提案 v2：A/B/C 三选一

日期：2026-11-27。状态：**待用户选择与批准，尚未冻结**。v1 已被否决并移入 [archive/palette_v1](archive/palette_v1/STATUS.md)，不再作为有效配置。字体固定 **Times New Roman**。

[A/B/C 同版试色页](palette_strip_v2.png) · [整页灰度副本](palette_strip_v2_grayscale.png) · [唯一候选配置](palette_candidates_v2.json) · [量化审计](palette_audit_v2.json)

## 1. 推荐与选择依据

**推荐 A**：最贴近用户认可的浅蓝、浅黄、浅绿方向，保留中等色度。B 整体比 A 稍深，颜色区分度余量更大；C 以较深蓝色和较强的明暗对照呈现经典期刊观感。三套使用完全相同的图形、尺寸与线宽，可以直接比较颜色，不受不同示例数据干扰。

基础参考为 [Okabe–Ito 的 Color Universal Design](https://jfly.uni-koeln.de/color/)：蓝/天蓝、橙/黄、蓝绿、红紫色相家族，以及形状、线型、直接标签的冗余编码原则。A/B 是按本任务指标调整的浅化衍生方案，**不把浅化后的颜色宣称为未经验证的原版色觉安全认证**。C 参考 [Nature Methods 的色觉友好图形讨论](https://www.nature.com/articles/nmeth.1618)及上述色相家族；“经典期刊型”是风格说明，并非 Nature/Science 官方指定色板。三套均为本项目衍生配置，不能与原版 Okabe–Ito 八色等同。

下表灰度差顺序为 **S/B、Q/C、M/N**；全部 28 对色差均按未四舍五入的数值检验。

| 候选 | 平均 L* | 最小两两 ΔE76 | 三组灰度 ΔL* | 最浅色对白底 CR |
| --- | ---: | ---: | ---: | ---: |
''' + '\n'.join(summary) + '''

**灰度验收口径已获用户明确确认**：按“同图实际对照配对”（代理/基线、量子/经典、金属/非金属）执行 ΔL*≥15，其余颜色仍全部检查 ΔE≥30。15% 在此解释为 L* 0–100 标尺上的 15 点，不是相对百分比或 HSL 明度。三套各 28/28 对 ΔE76≥30、3/3 组灰度差≥15。**不声称全部 28 对灰度差都≥15**；完整灰度差矩阵也保留在审计 JSON 中。

## 2. 数值定义与白底细线规则

- 色差：sRGB → 线性 RGB → XYZ（D65，白点 0.95047/1/1.08883）→ CIELAB。`ΔE76 = sqrt((ΔL*)² + (Δa*)² + (Δb*)²)`。这是 **CIE76 ΔE*ab，不是 CIEDE2000**。矩阵显示两位小数，验收使用全精度。
- 灰度：由 XYZ 的 Y 计算 L*，再把 Y 编码为等亮 sRGB 中性灰 G8。另核对 8-bit 量化后灰度的 L* 差，三组配对依旧通过。图中灰色色带里的 L* 是原色的目标明度。
- 白底对比度：按 [W3C 相对亮度定义](https://www.w3.org/TR/WCAG22/#dfn-relative-luminance)先线性化 RGB，用 `Yc=0.2126R+0.7152G+0.0722B`；`CR=1.05/(Yc+0.05)`。该公式只用于记录颜色与白底的对比度，不把网页合规阈值当作印刷质量保证。

**浅黄裸色细线的对比度不足以独立承担辨识**。三套最浅色均为 P，表中给出的低对比度是真实裸色值，未把深色边框算进去。试色页每套底部直接对照 1.5 pt 裸线与加轮廓细线；裸线样例用于暴露限制，不是推荐样式。

拟随候选一并批准的细线规则：裸色对白底 CR<3:1 时，1.5 pt 彩色线芯外必须加 **2.1 pt 总宽的中性轮廓**（每侧 0.3 pt）；中性轮廓 `#4C5662` 对白底 CR=''' + f"{colour_record(cfg['outline'])['white_contrast']:.2f}:1" + '''。3:1 是本提案选择的保守渲染触发值，不是用户另加的数值硬门槛。轮廓、线型和标签提供可见性，**不改变语义色 Hex，也不提高裸色本身的 CR**。如果要求浅黄本色在白底上不加轮廓也达到 3:1，则三套均不满足该额外要求，不能标记为裸色细线通过。

点、星形与柱采用 0.45–0.55 pt 中性边框；透明填充带使用 alpha=0.30 并保留边界与中心线。文字使用统一深墨色 `#303841`；不把浅色用于正文数字。辅助中性色不增加数据类别。红绿不单独承担语义区分。

## 3. 八色语义表与完整 ΔE 矩阵

共同 ID：S=代理模型；B=统计基线；Q=量子方法；C=经典优化方法；W=约束/警示；M=金属；N=非金属；P=近正例高亮。
'''
    for candidate in candidates:
        text += f"\n### {candidate['id']} · {candidate['zh']}\n\n"
        text += '| ID / 语义 | Hex | RGB | L* | G8 | C*ab | 白底 CR |\n| --- | --- | --- | ---: | ---: | ---: | ---: |\n'
        for r in candidate['roles']:
            text += f"| {r['id']} {r['zh']} | `{r['hex']}` | ({', '.join(map(str, r['rgb']))}) | {r['L_star']:.2f} | {r['gray8']} | {r['C_ab']:.2f} | {r['white_contrast']:.2f}:1 |\n"
        text += '\n**完整两两 ΔE76 矩阵**（对称，主对角线为 0）：\n\n'
        text += matrix_markdown(ids, candidate['delta_E76_matrix']) + '\n'
        text += '\n**实际系列配对灰度验证**：\n\n| 配对 | 原色目标 ΔL* | 8-bit 灰度实际 ΔL* | G8 间隔 | 判定 |\n| --- | ---: | ---: | ---: | --- |\n'
        for p in candidate['grayscale_pairs']:
            text += f"| {p['first']}/{p['second']} | {p['delta_L_star']:.2f} | {p['delta_L_star_quantized_gray8']:.2f} | {p['delta_gray8']} | ≥15，通过 |\n"
        weakest = min(candidate['pairs'], key=lambda p: p['delta_E76'])
        text += f"\n最接近色对为 {weakest['first']}/{weakest['second']}，ΔE76={weakest['delta_E76']:.2f}。28/28 对通过；不是只检查上面三组灰度配对。\n"
    text += '''
## 4. 后续正式图的语义与灰度边界

| ID | 固定用法 | 非颜色线索 |
| --- | --- | --- |
| S | H-soft / 代理预测 | 圆点、实线、直接标签 |
| B | additive Ridge / mean / random | Ridge 方块虚线；mean 下三角点线；random 叉号点划线 |
| Q | 后续量子或量子启发方法 | 菱形、虚线、方法标签 |
| C | 后续经典优化器、枚举或求解参照 | 上三角、实线、方法标签 |
| W | 约束、阈值、警示线 | 点线、叉形、阈值文字 |
| M | gap=0 样本及其误差贡献 | 下三角、斜线纹理、直接标签 |
| N | gap>0 样本及其误差贡献 | 实心十字、点状纹理、直接标签 |
| P | 开发集已知 V<=2 近正例 | 星形、有边框的高亮、直接标签 |

基线三条曲线共享 B，因此 F2 中 Ridge/mean/random 必须同时使用上表的三种线型/标记与直接标签，不能宣称这三条是不同灰度。方法图按方法着色；金属/非金属分解按样本类别着色。P 不能用于标记“真 holdout V=0”或仅凭低预测值认定的正例。通过/失败使用文字或符号，不能占用 N 绿色表达“可行”。

三组之外的颜色若在后续图中作为直接比较系列同现，必须在该图逐张审查中另列明度差和冗余编码；本次配对批准不能扩张为任意八色在灰度下都可仅靠颜色区分。单一正式面板尽量不超过五个语义色；本页八色属于校样例外。

连续量保留原生感知均匀顺序色图 **viridis [0.15, 0.80]**，景观/热图可采用 **plasma [0.10, 0.70]**；不手动混白、重排色阶或使用 jet。色图类型见 [Matplotlib 官方说明](https://matplotlib.org/stable/users/explain/colors/colormaps.html)。连续色标与离散角色含义分开；具体用途待图件清单批准时确定，同一物理量跨面板比较固定色标范围。

## 5. 实际样张、技术自查与复现

`palette_strip_v2.png` 按 A/B/C 上下排列；每套均含八色 Hex、等亮灰度色带和四个实际绘图小组：S/B 折线、M/N 散点及 P 高亮/W 阈值、Q/C 柱、S 区间填充带。所有坐标、柱高与点位都是**相同的合成设计几何**，不代表实验结果或不确定性估计。

**用途一句话**：比较三套全论文配色在实际图元、白底细线与灰度输出中的可读性。**数据来源文件**：`figures/palette_candidates_v2.json` 与 `figures/render_palette_v2.py` 内的合成校样几何。

- [x] **dpi**：300 dpi，2160×3600 px，白底，嵌入 sRGB 配置。
- [x] **字体 / 字号**：先调用指定模板 `apply_apmcm_style()`，再调用 **`use_times_new_roman()`**；逐个实际文本对象验证解析为 Times New Roman。最低 **8.5 pt**，设计尺寸 **182.88×304.8 mm**；试色页按 100% 查看/打印，后续正式图需按论文印刷尺寸重排，不能把整页任意缩小后宣称字号合格。
- [x] **零中文**：所有可见图中文字均为 ASCII 英文；图内无中文标点。
- [x] **灰度量化**：三套全部三组批准的灰度配对通过 ≥15；另输出整页灰度副本。视觉核查记录见 `palette_review_receipt_v2.json`。
- [x] **候选内一致**：所有语义颜色来自同一候选配置，四个小组没有另用 Matplotlib 默认颜色循环。

低对比度裸线未标记为通过；可供正式使用的是本页示范的“固定语义色 + 必要中性轮廓 + 冗余编码”组合。最终观感由用户在 A/B/C 中选定。

**Caption draft (design proof only):**

> Candidate A gives the lightest overall appearance, while B increases the minimum colour separation. All three candidates exceed dE76 = 30 for all 28 colour pairs and dL* = 15 for the three approved comparison pairs. Matched synthetic line, scatter, bar and band examples expose the contrast trade-off; light pastel lines require the illustrated neutral outline.

模板及参考仍使用已按顺序读过的 [APMCM skill](</mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm/SKILL.md>) §2.5/§7、[playbook](</mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm/assets/apmcm_figure_playbook.md>) 全文、[D 模板库](</mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm/assets/apmcm_d_plot_templates.py>)、[参考 25](</mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm/references/25_D题量子优化优秀论文解剖.md>) §25.9–25.12，并补读实际含 2025B 视觉分析的 §25.13。版式沿用模板的细框、白底、直接标注与多面板诊断布局；字体采用新版强制助手函数，不静默回退。

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_palette_v2.py
```

机器可读矩阵见 `palette_delta_E76_v2.csv`（长表 3×28 对）及 `palette_audit_v2.json`（完整矩阵、字体文件 SHA、图件 SHA、配对明度与白底对比度）。

## 6. 批准后的冻结与当前停止点

**选中的一套将贯穿 P1/P2/P3 全部图表，批准后冻结**：8 个 Hex/RGB、角色映射、线型/标记、浅色轮廓规则、Times New Roman 和连续色图使用规则。不会跨阶段更换整套风格。

当前仅提交三选一色板校样；待用户选择并批准后再提交 `figure_inventory.csv`。清单获批后才逐张出正式图并逐张审查。没有生成正式实验图、开展 P2、加载模型或新增拟合。v2 本轮只写 `figures/`，实验产物、模型、数据、求解代码与拟合账本的前后哈希检查记录在 `palette_review_receipt_v2.json`；交接状态也限于此目录记录。
'''
    (HERE / 'palette_proposal.md').write_text(text, encoding='utf-8')


def main():
    cfg = json.loads((HERE / 'palette_candidates_v2.json').read_text())
    candidates = assess(cfg)
    template.apply_apmcm_style()
    assert template.use_times_new_roman()
    plt.rcParams.update({'font.size': 8.5, 'axes.labelsize': 8.5, 'axes.titlesize': 9.5,
        'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5, 'legend.fontsize': 8.5,
        'text.color': cfg['ink'], 'axes.labelcolor': cfg['ink'],
        'xtick.color': cfg['ink'], 'ytick.color': cfg['ink'],
        'axes.grid': False, 'savefig.bbox': None, 'savefig.dpi': 300})
    fig = plt.figure(figsize=cfg['figure_inches'], facecolor='white')
    fig.text(.06, .985, 'P1/P2/P3 palette comparison', fontsize=14, weight='bold', va='top')
    fig.text(.06, .963, 'Eight fixed roles | Colour above, matched gray below | Times New Roman', fontsize=9, va='top')
    for candidate, top in zip(candidates, (.932, .634, .336)):
        draw_candidate(fig, candidate, top, cfg)
    fig.text(.06, .026, 'Matched synthetic geometry only; not experimental results. Approval pending.', fontsize=8.5, va='bottom')
    fig.text(.06, .013, 'Gray criterion: S/B, Q/C, M/N each dL* >= 15. All 28 colour pairs: dE76 >= 30.', fontsize=8.5, va='bottom')
    fig.canvas.draw()
    texts = [t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
    assert all(t.get_text().isascii() for t in texts)
    assert min(t.get_fontsize() for t in texts) >= cfg['minimum_font_pt']
    fonts = {Path(findfont(t.get_fontproperties(), fallback_to_default=False)) for t in texts}
    assert all(FontProperties(fname=p).get_name() == 'Times New Roman' for p in fonts)
    renderer = fig.canvas.get_renderer(); width, height = fig.canvas.get_width_height()
    outside = []
    for t in texts:
        box = t.get_window_extent(renderer)
        if box.x0 < 0 or box.y0 < 0 or box.x1 > width or box.y1 > height:
            outside.append(t.get_text())
    assert not outside, outside
    path = HERE / 'palette_strip_v2.png'
    fig.savefig(path, dpi=300, facecolor='white', metadata={'Title': 'Palette comparison v2',
        'Description': 'Synthetic design geometry; approval pending', 'Software': 'Matplotlib'})
    plt.close(fig)
    rgb = Image.open(path).convert('RGB')
    pixels = np.asarray(rgb, dtype=np.float32) / 255
    y = linearise(pixels) @ [.2126729, .7151522, .0721750]
    gray = np.rint(np.clip(encode(y), 0, 1) * 255).astype(np.uint8)
    gray_image = Image.fromarray(np.repeat(gray[:, :, None], 3, axis=2))
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    meta = PngImagePlugin.PngInfo()
    meta.add_text('Title', 'Palette comparison v2')
    meta.add_text('Description', 'Synthetic design proof only; no experimental data; approval pending')
    rgb.save(path, dpi=(300, 300), icc_profile=profile, pnginfo=meta)
    gray_path = HERE / 'palette_strip_v2_grayscale.png'
    gray_image.save(gray_path, dpi=(300, 300), icc_profile=profile, pnginfo=meta)
    with Image.open(path) as im:
        assert im.size == (2160, 3600)
        assert all(abs(d - 300) < .1 for d in im.info['dpi'])
    csv_path = HERE / 'palette_delta_E76_v2.csv'
    with csv_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['candidate', 'first', 'second', 'delta_E76', 'delta_L_star', 'grayscale_required_pair'])
        writer.writeheader()
        required = {frozenset(pair) for pair in cfg['grayscale_pairs']}
        for c in candidates:
            for pair in c['pairs']:
                writer.writerow(dict(candidate=c['id'], **pair,
                    grayscale_required_pair=frozenset([pair['first'], pair['second']]) in required))
    audit = dict(version=cfg['version'], date=cfg['date'], status=cfg['status'],
        source_sha256={str(p.relative_to(SOURCE)): sha(p) for p in
            [SOURCE/'SKILL.md', SOURCE/'assets/apmcm_figure_playbook.md', TEMPLATE,
             SOURCE/'references/25_D题量子优化优秀论文解剖.md']},
        template_functions_called=['apply_apmcm_style', 'use_times_new_roman'],
        config_sha256=sha(HERE/'palette_candidates_v2.json'), renderer_sha256=sha(Path(__file__)),
        colour_metric=cfg['colour_metric'], grayscale_scope=cfg['grayscale_scope_authorization'],
        candidates=candidates, all_text_actual_times_new_roman=True, all_text_ascii=True,
        fonts={p.name: sha(p) for p in sorted(fonts)}, mathtext_fontset='stix (template default; no mathtext in this proof)',
        minimum_font_pt=min(t.get_fontsize() for t in texts), all_text_within_canvas=True,
        dpi=300, dimensions_px=[2160, 3600], dimensions_inches=cfg['figure_inches'],
        low_contrast_lines_require_outline=True, all_raw_colours_contrast_at_least_3_to_1=False,
        outline_white_contrast=colour_record(cfg['outline'])['white_contrast'],
        no_experimental_data_used=True, models_loaded=False, new_fits=0,
        formal_figures_generated=False, figure_inventory_generated=False,
        outputs={p.name: sha(p) for p in [path, gray_path, csv_path]})
    (HERE / 'palette_audit_v2.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    write_proposal(cfg, candidates, audit)
    print(json.dumps({c['id']: {k: c[k] for k in
        ['minimum_delta_E76', 'mean_L_star', 'minimum_comparison_delta_L_star', 'minimum_raw_white_contrast']}
        for c in candidates}, indent=2))
    print('Times New Roman verified; 300 dpi; minimum 8.5 pt; all figure text ASCII.')


if __name__ == '__main__':
    main()
