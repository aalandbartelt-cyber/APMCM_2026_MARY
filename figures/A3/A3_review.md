# A3 v2 — Nominal-candidate rank and surrogate decision regret

2026-11-27。按首轮打回意见重做，已完成彩色/灰度自查，等待用户验收；F1 v3 已通过且原件未改。

用途：同时展示四池名义候选的成员名次分布与双向代理 regret。

[300 dpi PNG](A3_decision_stability_v2.png) · [矢量 PDF](A3_decision_stability_v2.pdf) · [完整灰度版](A3_decision_stability_v2_grayscale.png) · [审计 JSON](A3_audit.json)

尺寸：170 × 103 mm；Times New Roman，最小 8.5 pt。图内单词数（含数字/刻度）由 129 降至 55；保留的文字仅用于标注。

## 图例与读法

左侧白心圆图例 Member rank 表示一个既有成员，池编号直接在纵轴。右侧两项颜色图例：蓝=Reverse cost（左半轴），琥珀=Forward cost（右半轴）；下方形状图例圆/三角/方块/竖帽分别为 p50/p90/p95/Max。左右位置只编码方向，两个 regret 原始值均非负。

图型：Four coloured violins with raw ranks; diverging two-ended quantile whiskers. No lollipop or zero-anchored stem.

## 数据来源

- [decision_stability_members.csv](../../artifacts/p1_v21/hardening/decision_stability_members.csv)
- [decision_stability_summary.csv](../../artifacts/p1_v21/hardening/decision_stability_summary.csv)
- [protocol.json](../../artifacts/p1_v21/hardening/protocol.json)

所有来源 SHA-256 已逐项核验。只有显示汇总写入本目录，没有新实验或新拟合。

- [A3_member_ranks.csv](A3_member_ranks.csv)
- [A3_regret_quantiles.csv](A3_regret_quantiles.csv)

## Short English caption

Nominal-candidate rank distributions and bidirectional regret.

## Reading guide and interpretation material

以下供后续正文使用，目前未嵌入论文或图内：

Each violin displays the 20 existing ranks of La|Ti|NO2, with all observations overlaid. Width is a graphics-only Gaussian-kernel density in log10 rank using fixed bandwidth 0.12; the display is cut at rank 1 and closes 0.30 log10 units above the largest observed rank. Width is normalized separately within each pool, not fitted or used for inference. Maximum ranks are annotated. In the right panel, reverse regret is placed left and forward regret right, using the blue and amber ends of the common diverging palette, with white at zero. Colour encodes direction only; position encodes cost. Both costs are nonnegative: the leftward sign encodes direction only. Forward means the nominal choice evaluated in each member table; reverse means each member choice evaluated in the nominal table. Quantile symbols identify p50/p90/p95 and maxima; no line is anchored at zero. All quantiles match stored summaries. None of the pools satisfies the registered 0.1 tolerance in both directions for all members. These are surrogate-table costs, not true-V regret.

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
