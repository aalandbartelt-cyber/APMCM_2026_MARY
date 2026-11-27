# A1 v3 — Residual structure by X family

2026-11-27。本轮只修订合并审阅 PDF 的第 2、4、8 页；其他六图已获用户认可并原件保留。本图 v3 待用户验收。

用途：按明确标注的 X 族，对照有符号偏差、RMSE 与绝对误差 q95。

本次修改：(b) 改成成对横条；每行重新标明 X 族，14 个值直接标在条末。RMSE 用实色，q95 用斜纹，避免灰度下依赖颜色辨认。

文件：[300 dpi PNG](A1_residual_structure_v3.png) / [矢量 PDF](A1_residual_structure_v3.pdf) / [完整灰度 PNG](A1_residual_structure_v3_grayscale.png)。印刷尺寸 170 × 102 mm。

数据来源（只读，哈希见 [A1_audit_v3.json](A1_audit_v3.json)）：

- [OOF_residual_scales_by_X.csv](../../artifacts/p1_v21/results/OOF_residual_scales_by_X.csv)
- [final_selection.json](../../artifacts/p1_v21/final_selection.json)

图例：左色条：负偏差蓝、零白、正偏差琥珀；右图：实色灰绿横条=RMSE，斜纹灰粉横条=q95 absolute error。每组两条共用零起点，不堆叠。两面板的纵向分类均明确为 X family。

Caption draft: Residual bias and error scale across X families.

Reading guide for manuscript: The left heat strip maps signed mean residual Vhat-V to blue-white-amber, centred at zero; signed values preserve the encoding in grayscale. Each right-panel row is explicitly labelled with its X family. Solid green bars encode RMSE; hatched pink bars encode empirical absolute-residual q95. Paired bars start from the same zero on the original-V scale and carry their values at the ends. The two summaries are not additive and are not stacked. Each family contains 1,608 external OOF predictions from frozen H-soft. N3 has the largest RMSE (6.6515) and absolute-error q95 (13.8694). These are empirical error summaries, not calibrated prediction intervals.

- [x] 300 dpi PNG，另附矢量 PDF。
- [x] 最终尺寸下字号最低 8.5 pt。
- [x] 图内全英文、ASCII，无中文或中文标点。
- [x] 已打开完整灰度图检查；颜色外另有点形/线型、纹理或带符号数值编码。
- [x] 配色与本图登记一致；F2/A1 沿用 v2，A5 按用户本轮意见登记浅色修订。
- [x] Times New Roman 实际字体，PDF 已嵌入。
- [x] 无 suptitle 或全图大标题。
- [x] 无嵌入表格。
- [x] 文字仅为轴、图例、面板名及关键数值，无句子级说明。

未进行实体纸张打印；已检查实际导出尺寸和完整灰度渲染。只读取已有结果，新增拟合、校准拟合和 bootstrap 抽样均为 0。
