# F3 v2 — Error contributions and the regression-screening trade-off

2026-11-27。按首轮打回意见重做，已完成彩色/灰度自查，等待用户验收；F1 v3 已通过且原件未改。

用途：展示金属/非金属误差贡献及登记回归路线的 RMSE–EF 权衡。

[300 dpi PNG](F3_error_tradeoff_v2.png) · [矢量 PDF](F3_error_tradeoff_v2.pdf) · [完整灰度版](F3_error_tradeoff_v2_grayscale.png) · [审计 JSON](F3_audit.json)

尺寸：170 × 90 mm；Times New Roman，最小 8.5 pt。图内单词数（含数字/刻度）由 108 降至 48；保留的文字仅用于标注。

## 图例与读法

左图：钢蓝实块=Metal (gap=0)，琥珀斜纹=Nonmetal (gap>0)，条末数字=总 MSE。右图：圆点=H-soft、方块=R-log、三角=R-raw、菱形=W-log；与实际填色及点形匹配的四项图例位于该面板下方。

图型：Steel-blue/amber stacked strips plus shape-coded Pareto points; no explanatory text block.

## 数据来源

- [P1_final_experiment_table.csv](../../artifacts/p1_v21/results/P1_final_experiment_table.csv)
- [regression_pareto.csv](../../artifacts/p1_v21/results/regression_pareto.csv)
- [paired_AB_bootstrap_5000.csv](../../artifacts/p1_v21/results/paired_AB_bootstrap_5000.csv)

所有来源 SHA-256 已逐项核验。只有显示汇总写入本目录，没有新实验或新拟合。

- [F3_MSE_contributions.csv](F3_MSE_contributions.csv)
- [F3_registered_pareto.csv](F3_registered_pareto.csv)

## Short English caption

Class contributions to error and the regression-screening trade-off.

## Reading guide and interpretation material

以下供后续正文使用，目前未嵌入论文或图内：

Each stacked segment is class-specific SSE divided by the total sample count; segment sums equal pooled RMSE squared. Metal and nonmetal are encoded by steel blue and hatched amber. The six stacked bars are decompositions, not confidence intervals. The scatter compares only four registered regressors: H-soft is nondominated at RMSE=4.6011 and EF=62.1024. Its MSE contributions are 18.2920 and 2.8781. H-soft minus R-log EF is +1.6160 with the existing 95% paired AB percentile interval [-5.9951,11.2022], conditional on frozen OOF and prior selection without multiplicity correction; the apparent screening advantage is therefore uncertain. No RMSE is assigned to probability-only routes.

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
