# A5 v4 — Protocol-level extrapolation stress diagnostics

2026-11-27。本轮仅更新合并 PDF 第八页的配色和格内文字颜色；其他八图原件保留。本图 v4 待用户验收。

用途：用方形矩阵展示压力协议结果及相对同路线 OOF 的变化。

本次修改：按用户提供的 A1(a) 参考图，复用钢蓝 #587AA4—白—琥珀 #DC9848 连续色图。格内数字使用深色 #080808，最低文字/底色对比度为 4.65:1。150 × 150 mm 方形布局、±80% 色标、字体字号和全部数值保持不变。

文件：[300 dpi PNG](A5_stress_protocols_v4.png) / [矢量 PDF](A5_stress_protocols_v4.pdf) / [完整灰度 PNG](A5_stress_protocols_v4_grayscale.png)。印刷尺寸 150 × 150 mm。

数据来源（只读，哈希见 [A5_audit_v4.json](A5_audit_v4.json)）：

- [stress_summary.csv](../../artifacts/p1_v21/results/stress_summary.csv)
- [stress_detail.csv](../../artifacts/p1_v21/results/stress_detail.csv)
- [P1_final_experiment_table.csv](../../artifacts/p1_v21/results/P1_final_experiment_table.csv)

图例：底部连续色条：负变化钢蓝、零白、正变化琥珀。每格上方大数值为原始指标，下方带符号百分数为相对同路线 AB-blocked OOF 的变化；行标协议，列标模型路线与指标。

Caption draft: Stress-test outcomes and matched OOF-relative changes: protocol-level evidence, not final-model.

Reading guide for manuscript: Rows are protocols and columns are route-specific metrics. Large cell labels are the original stored values; small labels and the blue-white-amber colour encode 100*(stress/reference-1), with zero at the same route's AB-blocked OOF reference. References are R-log RMSE=4.904836, R-log EF=60.486349 and S-eps EF=62.223405. Signed colour indicates raw change, not a universal better/worse direction: lower RMSE and higher EF are desirable. No estimates are refitted. Valid EF evaluations are 5/5, 3/3 and 29/35; zero-positive cases remain undefined. Total budgets are 100,60,700 and defined-EF budgets 100,60,580. Populations, prevalences and budgets differ, so cross-protocol colours cannot rank extrapolation difficulty. These are R-log/S-eps protocol-level evidence, not final-model H-soft validation.

- [x] 300 dpi PNG，另附矢量 PDF。
- [x] 最终尺寸下字号最低 8.5 pt。
- [x] 图内全英文、ASCII，无中文或中文标点。
- [x] 已打开完整灰度图检查；颜色外另有点形/线型、纹理或带符号数值编码。
- [x] 配色与用户所附 A1(a) 参考图一致，见 ../palette_A5_reference_v4.json；格内深色数字另经对比度核验。
- [x] Times New Roman 实际字体，PDF 已嵌入。
- [x] 无 suptitle 或全图大标题。
- [x] 无嵌入表格。
- [x] 文字仅为轴、图例、面板名及关键数值，无句子级说明。

未进行实体纸张打印；已检查实际导出尺寸和完整灰度渲染。只读取已有结果，新增拟合、校准拟合和 bootstrap 抽样均为 0。
