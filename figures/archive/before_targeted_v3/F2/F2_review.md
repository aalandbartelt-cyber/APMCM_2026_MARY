# F2 v2 — Near-positive enrichment under fixed AB blocking

2026-11-27。按首轮打回意见重做，已完成彩色/灰度自查，等待用户验收；F1 v3 已通过且原件未改。

用途：在相同逐折预算下比较命中与富集，并放大分辨低 EF 的两条基线。

[300 dpi PNG](F2_enrichment_v2.png) · [矢量 PDF](F2_enrichment_v2.pdf) · [完整灰度版](F2_enrichment_v2_grayscale.png) · [审计 JSON](F2_audit.json)

尺寸：170 × 118 mm；Times New Roman，最小 8.5 pt。图内单词数（含数字/刻度）由 186 降至 72；保留的文字仅用于标注。

## 图例与读法

浅钢蓝实线圆点=H-soft；暗琥珀虚线方块=Additive Ridge；灰绿点线倒三角=Mean；灰粉点划线叉号=Random (fixed)。砖红点线=每折预算 k=20；中性虚线=随机期望 EF=1。下方独立放大窗对应主图框选的 k=1–100、EF=0–1.5 数据范围，连接线标明对应关系；两窗颜色、点形、线型、坐标含义一致。

图型：Four-colour curves, endpoint values, explicit reference keys, boxed low-EF zoom with source region and connectors; no embedded table.

## 数据来源

- [all_domain_metrics.csv](../../artifacts/p1_v21/results/all_domain_metrics.csv)
- [P1_main_per_fold.csv](../../artifacts/p1_v21/results/P1_main_per_fold.csv)
- [experiment_freeze.json](../../artifacts/p1_v21/experiment_freeze.json)

所有来源 SHA-256 已逐项核验。只有显示汇总写入本目录，没有新实验或新拟合。

- [F2_curve_data.csv](F2_curve_data.csv)
- [F2_fold_uniform_null.csv](F2_fold_uniform_null.csv)

## Short English caption

Near-positive enrichment under AB-blocked validation.

## Reading guide and interpretation material

以下供后续正文使用，目前未嵌入论文或图内：

Read the curves at the same per-fold budget k; hits sum the five folds and EF gives each fold equal weight. The dotted vertical line is k=20, corresponding to 100 selections overall. H-soft gives 68 hits and EF=62.1024, compared with 10, 1 and 0 hits for additive Ridge, mean and the fixed random realization. The event is V<=2. Endpoint labels refer to k=100; the separate zoom window enlarges the marked low-EF band of the parent panel, with matching log-budget coordinates and connector lines. The dashed horizontal line is EF=1, the uniform-random expectation, not the realized random curve. Per-fold N/M/h and existing unadjusted hypergeometric p values remain in F2_fold_uniform_null.csv; they are descriptive references after development selection, not a pooled test.

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
