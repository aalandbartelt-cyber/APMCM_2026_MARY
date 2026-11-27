# A6 v2 — Feature additions and reverse ablations within model routes

2026-11-27。按首轮打回意见重做，已完成彩色/灰度自查，等待用户验收；F1 v3 已通过且原件未改。

用途：用双向须线展示最终 H-soft 三组反向消融的既有配对区间。

[300 dpi PNG](A6_ablation_v2.png) · [矢量 PDF](A6_ablation_v2.pdf) · [完整灰度版](A6_ablation_v2_grayscale.png) · [审计 JSON](A6_audit.json)

尺寸：170 × 78 mm；Times New Roman，最小 8.5 pt。图内单词数（含数字/刻度）由 119 降至 39；保留的文字仅用于标注。

## 图例与读法

灰色圆点与须线=CI crosses 0；琥珀方块与须线=CI above 0；钢蓝方块与须线=CI below 0。CI 指既有 95% 配对 bootstrap 区间；竖虚线为零效应，点旁数字为 removal minus full 的点估计。

图型：Two-panel forest plot: point estimates, bilateral interval whiskers, vertical zero line; grey crossing-zero effects.

## 数据来源

- [diagnostic_summary.csv](../../artifacts/p1_v21/results/diagnostic_summary.csv)
- [P1_final_experiment_table.csv](../../artifacts/p1_v21/results/P1_final_experiment_table.csv)
- [paired_AB_bootstrap_5000.csv](../../artifacts/p1_v21/results/paired_AB_bootstrap_5000.csv)
- [feature_schema.json](../../artifacts/p1_v21/feature_schema.json)

所有来源 SHA-256 已逐项核验。只有显示汇总写入本目录，没有新实验或新拟合。

- [A6_feature_additions.csv](A6_feature_additions.csv)
- [A6_reverse_ablation_intervals.csv](A6_reverse_ablation_intervals.csv)

## Short English caption

Reverse-ablation effects with paired bootstrap intervals.

## Reading guide and interpretation material

以下供后续正文使用，目前未嵌入论文或图内：

Each point is removal minus full H-soft, with horizontal two-ended 95% paired AB percentile intervals from 5,000 existing draws. Grey circles mark intervals crossing zero; coloured squares mark intervals excluding zero, with positive effects amber and negative effects blue. Geometry removal changes RMSE by +0.1396 and EF by -8.7049. The RMSE and equal-fold EF endpoints are separate panels. Intervals condition on frozen OOF and prior selection, are exploratory and are not multiplicity-adjusted. Removal uses dependency tags: removing X statistics also removes dependent geometry, so effects are not orthogonal causal attributions. The earlier R-log F0/F3/F3+E1 ladder is retained in companion data and moved out of this image as requested. No fit or bootstrap draw is added.

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
