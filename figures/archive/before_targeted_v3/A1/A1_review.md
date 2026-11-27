# A1 v2 — Residual structure by X family

2026-11-27。按首轮打回意见重做，已完成彩色/灰度自查，等待用户验收；F1 v3 已通过且原件未改。

用途：将 X 族的有符号偏差与 RMSE/q95 误差尺度并列比较。

[300 dpi PNG](A1_residual_structure_v2.png) · [矢量 PDF](A1_residual_structure_v2.pdf) · [完整灰度版](A1_residual_structure_v2_grayscale.png) · [审计 JSON](A1_audit.json)

尺寸：170 × 87 mm；Times New Roman，最小 8.5 pt。图内单词数（含数字/刻度）由 103 降至 40；保留的文字仅用于标注。

## 图例与读法

左侧连续色条是 Bias 的图例：负值蓝、零白、正值琥珀，每个色块保留带正负号数值。右图图例：灰绿圆点=RMSE，灰粉菱形=q95 absolute error。

图型：Signed heat strip plus overlaid circle/diamond error scales; blue-white-amber zero-centred colour map.

## 数据来源

- [OOF_residual_scales_by_X.csv](../../artifacts/p1_v21/results/OOF_residual_scales_by_X.csv)
- [final_selection.json](../../artifacts/p1_v21/final_selection.json)

所有来源 SHA-256 已逐项核验。只有显示汇总写入本目录，没有新实验或新拟合。

- [A1_residual_values.csv](A1_residual_values.csv)

## Short English caption

Residual bias and error scale across X families.

## Reading guide and interpretation material

以下供后续正文使用，目前未嵌入论文或图内：

The left heat strip maps signed mean residual Vhat-V to blue-white-amber, centred at zero; signed values preserve the encoding in grayscale. The right panel overlays RMSE circles and empirical absolute-residual q95 diamonds on a common original-V scale. Each family contains 1,608 external OOF predictions from frozen H-soft. N3 has the largest RMSE (6.6515) and absolute-error q95 (13.8694). These are empirical error summaries, not calibrated prediction intervals.

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
