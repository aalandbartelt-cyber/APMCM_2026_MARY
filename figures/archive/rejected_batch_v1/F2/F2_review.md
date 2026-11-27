# F2 — Near-positive enrichment under fixed AB blocking

2026-11-27。已按“后面几个图直接一口气全出”的授权制作并完成彩色/灰度自查，提交用户批量审阅；自查不等于用户已批准入稿。

用途：在相同逐折预算下，对比 H-soft 与三种基线的命中数和近正例富集。 定级：正文图。支撑环节：Model validation。

## 图件

[300 dpi PNG](F2_enrichment.png) · [矢量 PDF](F2_enrichment.pdf) · [完整灰度版](F2_enrichment_grayscale.png) · [机器审计](F2_audit.json)

印刷尺寸 170 × 171 mm；全部使用 Times New Roman，最小 8.5 pt。按此尺寸排版，不再缩小字体。

## 图例指代

H-soft：浅蓝实线、实心圆；Additive Ridge：灰色虚线、空心方块；Mean：灰色点线、空心倒三角；Random (fixed)：灰色点划线、叉号。水平细虚线表示随机期望 EF=1，竖点线定位每折 k=20。局部放大保留 Mean/Random 的同一套图例。

## 数据来源与口径

- [all_domain_metrics.csv](../../artifacts/p1_v21/results/all_domain_metrics.csv)
- [P1_main_per_fold.csv](../../artifacts/p1_v21/results/P1_main_per_fold.csv)
- [experiment_freeze.json](../../artifacts/p1_v21/experiment_freeze.json)

- 过滤：H-soft: protocol=outer and domains main_outer_0..4; baselines: protocol=baseline and domains baseline_0..4; no inner/by_X/stress/pooled rows.
- 汇总：Sum fold-specific hits; equal mean of fold-specific EF. At k=20 total budget=100. Do not compute pooled Top-20.
- 声称边界：Observed random curve is not replaced by theoretical EF=1. No p-value averaging or invented pooled test. p_uniform is a descriptive uniform-null reference after development selection.

来源 SHA-256 逐项匹配批准清单，展示派生表仅写在本目录：

- [F2_curve_data.csv](F2_curve_data.csv)
- [F2_fold_uniform_null.csv](F2_fold_uniform_null.csv)

## English caption draft

H-soft concentrates near-positive samples across the fixed AB-blocked folds. With 20 selections per fold (100 total), it yields 68 hits and mean EF=62.1024, versus 10, 1 and 0 hits for additive Ridge, mean and the fixed random realization. The event is V<=2; hits are summed and EF is averaged equally over the five folds. Budget axes are logarithmic. The inset enlarges mean/random EF on the same k scale. The EF=1 line is the uniform-random expectation, not the observed random curve. The table reports every fold-specific N, M, h and existing unadjusted hypergeometric p value at k=20. These p values are descriptive uniform-null references after development selection, not a pooled or selection-adjusted significance test.

## 提交自查

- [x] dpi：PNG 为 300 dpi，另附纯矢量 PDF。
- [x] 字号：实际 Times New Roman 字体已核验并嵌入 PDF，最小 8.5 pt。
- [x] 零中文：图内全部文本为 ASCII 英文及数字/符号。
- [x] 灰度可辨：已查看完整灰度渲染；线型、点形、纹理或直接标签对应图例。
- [x] 色板一致：冻结 A 的语义色与中性描边；色板哈希保持不变。

已检查标签与图形无明显遮挡、文字不越出画布。灰度检查为屏幕渲染检查，尚未做实物打印。模型加载为 0，新增拟合与 bootstrap 抽样均为 0。
