# A4 v2 — Split-half averaging and decision stability

2026-11-27。按首轮打回意见重做，已完成彩色/灰度自查，等待用户验收；F1 v3 已通过且原件未改。

用途：用四池斜率线对照 single 与十成员均值的决策稳定性。

[300 dpi PNG](A4_split_half_v2.png) · [矢量 PDF](A4_split_half_v2.pdf) · [完整灰度版](A4_split_half_v2_grayscale.png) · [审计 JSON](A4_audit.json)

尺寸：170 × 93 mm；Times New Roman，最小 8.5 pt。图内单词数（含数字/刻度）由 100 降至 54；保留的文字仅用于标注。

## 图例与读法

Pool 07=钢蓝实线圆，08=琥珀虚线方，11=灰绿点划线三角，12=灰粉点线菱形。各图例与实际连线、空心端点一致；左列 Single、右列 Mean of 10 明确对照端点，邻近数字用短引线对应真实端点。

图型：Two slope graphs with four pool-specific colours and shapes; no zero baseline stems or lollipop form.

## 数据来源

- [split_half_summary.csv](../../artifacts/p1_v21/hardening/split_half_summary.csv)
- [protocol.json](../../artifacts/p1_v21/hardening/protocol.json)
- [P23_construction_decision.json](../../artifacts/p1_v21/hardening/P23_construction_decision.json)

所有来源 SHA-256 已逐项核验。只有显示汇总写入本目录，没有新实验或新拟合。

- [A4_split_half_values.csv](A4_split_half_values.csv)

## Short English caption

Split-half effects of averaging on decision stability.

## Reading guide and interpretation material

以下供后续正文使用，目前未嵌入论文或图内：

Each pool connects the single-member reference on the left to the mean of ten members on the right; endpoints show stored means. The agreement axis is linear and the regret axis logarithmic. Values label the actual endpoints; short leader lines separate nearby labels without moving data. The 1,000 complementary 10/10 splits reuse the same 20 members, and each single-member reference averages all 100 cross-half pairs. Averaging lowers surrogate regret in all four pools; agreement in pools 11/12 remains 0.192/0.174. These are dependent split-half stability diagnostics, not independent replicates or an accuracy test of a future mean-of-twenty table.

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
