# F2 v3 — Near-positive enrichment under fixed AB blocking

2026-11-27。本轮只修订合并审阅 PDF 的第 2、4、8 页；其他六图已获用户认可并原件保留。本图 v3 待用户验收。

用途：比较固定逐折预算下的近正例命中与富集，清晰展示低 EF 基线。

本次修改：低 EF 放大区改为贴近主图的共享横轴窄带；统一左右边界，采用短竖直连接线，保留来源框及相同坐标含义。

文件：[300 dpi PNG](F2_enrichment_v3.png) / [矢量 PDF](F2_enrichment_v3.pdf) / [完整灰度 PNG](F2_enrichment_v3_grayscale.png)。印刷尺寸 170 × 118 mm。

数据来源（只读，哈希见 [F2_audit_v3.json](F2_audit_v3.json)）：

- [all_domain_metrics.csv](../../artifacts/p1_v21/results/all_domain_metrics.csv)
- [P1_main_per_fold.csv](../../artifacts/p1_v21/results/P1_main_per_fold.csv)
- [experiment_freeze.json](../../artifacts/p1_v21/experiment_freeze.json)

图例：H-soft=浅钢蓝实线圆点；Additive Ridge=琥珀虚线方块；Mean=灰绿点线倒三角；Random (fixed)=灰粉点划线叉号。砖红点线为 k=20；中性虚线为 EF=1。下带显示 EF=0–1.5，使用与主图相同的 log-k 横轴范围和系列样式。

Caption draft: Near-positive enrichment under AB-blocked validation.

Reading guide for manuscript: Read the curves at the same per-fold budget k; hits sum the five folds and EF gives each fold equal weight. The dotted vertical line is k=20, corresponding to 100 selections overall. H-soft gives 68 hits and EF=62.1024, compared with 10, 1 and 0 hits for additive Ridge, mean and the fixed random realization. The event is V<=2. Endpoint labels refer to k=100. The compact lower strip enlarges EF=0-1.5 from the marked parent band; both panels share the same log-budget viewport, and short vertical connectors mark the correspondence. The data occupy k=1-100; the identical 0.85-165 viewport adds endpoint-label padding only. The dashed horizontal line is EF=1, the uniform-random expectation, not the realized random curve. Per-fold N/M/h and existing unadjusted hypergeometric p values remain in F2_fold_uniform_null.csv; they are descriptive references after development selection, not a pooled test.

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
