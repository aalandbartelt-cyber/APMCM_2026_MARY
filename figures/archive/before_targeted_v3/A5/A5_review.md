# A5 v2 — Protocol-level extrapolation stress diagnostics

2026-11-27。按首轮打回意见重做，已完成彩色/灰度自查，等待用户验收；F1 v3 已通过且原件未改。

用途：用协议×指标矩阵展示既有压力结果及同路线 OOF 参照变化。

[300 dpi PNG](A5_stress_protocols_v2.png) · [矢量 PDF](A5_stress_protocols_v2.pdf) · [完整灰度版](A5_stress_protocols_v2_grayscale.png) · [审计 JSON](A5_audit.json)

尺寸：170 × 88 mm；Times New Roman，最小 8.5 pt。图内单词数（含数字/刻度）由 109 降至 38；保留的文字仅用于标注。

## 图例与读法

底部连续色条是百分比变化图例：蓝为负变化，白为零，琥珀为正变化。列名指定路线与原始指标；格内大数字为原始结果，小百分数为相对同路线 AB-blocked OOF 的变化，符号在灰度下仍可辨。

图型：Compact 3-by-3 diverging matrix heatmap, original values plus signed percentage changes; no embedded table object.

## 数据来源

- [stress_summary.csv](../../artifacts/p1_v21/results/stress_summary.csv)
- [stress_detail.csv](../../artifacts/p1_v21/results/stress_detail.csv)
- [P1_final_experiment_table.csv](../../artifacts/p1_v21/results/P1_final_experiment_table.csv)

所有来源 SHA-256 已逐项核验。只有显示汇总写入本目录，没有新实验或新拟合。

- [A5_heatmap_values.csv](A5_heatmap_values.csv)
- [A5_protocol_denominators.csv](A5_protocol_denominators.csv)
- [A5_stress_values.csv](A5_stress_values.csv)

## Short English caption

Stress-test outcomes and matched OOF-relative changes: protocol-level evidence, not final-model.

## Reading guide and interpretation material

以下供后续正文使用，目前未嵌入论文或图内：

Rows are protocols and columns are route-specific metrics. Large cell labels are the original stored values; small labels and the blue-white-amber colour encode 100*(stress/reference-1), with zero at the same route's AB-blocked OOF reference. References are R-log RMSE=4.904836, R-log EF=60.486349 and S-eps EF=62.223405. Signed colour indicates raw change, not a universal better/worse direction: lower RMSE and higher EF are desirable. No estimates are refitted. Valid EF evaluations are 5/5, 3/3 and 29/35; zero-positive cases remain undefined. Total budgets are 100,60,700 and defined-EF budgets 100,60,580. Populations, prevalences and budgets differ, so cross-protocol colours cannot rank extrapolation difficulty. These are R-log/S-eps protocol-level evidence, not final-model H-soft validation.

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
