# A2 v2 — External OOF probability calibration diagnostics

2026-11-27。按首轮打回意见重做，已完成彩色/灰度自查，等待用户验收；F1 v3 已通过且原件未改。

用途：展示四条既有折外概率曲线与理想校准线的差异。

[300 dpi PNG](A2_calibration_v2.png) · [矢量 PDF](A2_calibration_v2.pdf) · [完整灰度版](A2_calibration_v2_grayscale.png) · [审计 JSON](A2_audit.json)

尺寸：170 × 136 mm；Times New Roman，最小 8.5 pt。图内单词数（含数字/刻度）由 211 降至 58；保留的文字仅用于标注。

## 图例与读法

五项图例逐项对应 B-eps observed（蓝圆实线）、S-eps observed（琥珀方块虚线）、L-single observed（灰绿三角点划线）、L-hash4 observed（灰粉菱形点线）与 Ideal: y=x（中性虚线）。按用户“每线一个斜率数值”的要求保留单个 slope 标注；完整斜率/截距表移到伴随材料。

图型：Four compact colour-specific reliability panels; diagonal plus one slope value per curve, no numeric text blocks.

## 数据来源

- [main_outer_0.csv.gz](../../artifacts/p1_v21/domains/main_outer_0.csv.gz)
- [main_outer_1.csv.gz](../../artifacts/p1_v21/domains/main_outer_1.csv.gz)
- [main_outer_2.csv.gz](../../artifacts/p1_v21/domains/main_outer_2.csv.gz)
- [main_outer_3.csv.gz](../../artifacts/p1_v21/domains/main_outer_3.csv.gz)
- [main_outer_4.csv.gz](../../artifacts/p1_v21/domains/main_outer_4.csv.gz)
- [oof_calibration_consistency.csv](../../artifacts/p1_v21/results/oof_calibration_consistency.csv)
- [oof_calibration_ranking_checks.csv](../../artifacts/p1_v21/results/oof_calibration_ranking_checks.csv)

所有来源 SHA-256 已逐项核验。只有显示汇总写入本目录，没有新实验或新拟合。

- [A2_existing_pooled_diagnostics.csv](A2_existing_pooled_diagnostics.csv)
- [A2_reliability_bins.csv](A2_reliability_bins.csv)

## Short English caption

External OOF probability reliability.

## Reading guide and interpretation material

以下供后续正文使用，目前未嵌入论文或图内：

Curves pair mean stored probability with empirical V<=2 frequency in ten fixed equal-width bins; empty bins are omitted. Each panel contains 11,256 external OOF observations with 128 near-positives. The diagonal is ideal calibration. Each curve has one existing pooled slope annotation; full slopes, intercepts, Brier scores and bin counts are supplied in the companion data/body-table material, not embedded in the image. S-eps slope=1.7617 and intercept=0.9794 indicate a remaining scale discrepancy. No calibrator was fitted. Sparse high-probability bins, including singleton bins, remain descriptive; pooled diagnostic curves do not replace the fold-specific EF endpoint.

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
