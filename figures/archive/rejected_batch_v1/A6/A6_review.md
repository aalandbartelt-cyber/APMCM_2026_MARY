# A6 — Feature additions and reverse ablations within model routes

2026-11-27。已按“后面几个图直接一口气全出”的授权制作并完成彩色/灰度自查，提交用户批量审阅；自查不等于用户已批准入稿。

用途：分开呈现 R-log 的特征增量与最终 H-soft 的三组反向消融。 定级：附录图。支撑环节：Model establishment; model validation。

## 图件

[300 dpi PNG](A6_ablation.png) · [矢量 PDF](A6_ablation.pdf) · [完整灰度版](A6_ablation_grayscale.png) · [机器审计](A6_audit.json)

印刷尺寸 170 × 158 mm；全部使用 Times New Roman，最小 8.5 pt。按此尺寸排版，不再缩小字体。

## 图例指代

上排直接标出 R-log 的 F0、F3、F3+E1；下排直接标出 H-soft 的去电子、去几何、去 X 统计。浅蓝点为观测差值，横线为已存在的 95% 配对区间，点状竖线为零差异；正负号统一为 removal minus full。

## 数据来源与口径

- [diagnostic_summary.csv](../../artifacts/p1_v21/results/diagnostic_summary.csv)
- [P1_final_experiment_table.csv](../../artifacts/p1_v21/results/P1_final_experiment_table.csv)
- [paired_AB_bootstrap_5000.csv](../../artifacts/p1_v21/results/paired_AB_bootstrap_5000.csv)
- [feature_schema.json](../../artifacts/p1_v21/feature_schema.json)

- 过滤：R-log feature F0/F3 plus outer R-log F4=F3+E1; H-soft minus_electronic/minus_geometry/minus_xstats against full H-soft.
- 汇总：Use stored means and corrected paired_AB_bootstrap_5000 EF_macro@20 intervals; exclude legacy pooled Top-20 intervals.
- 声称边界：Do not connect R-log and H-soft into one feature ladder. No new fits, bootstrap draws or selection. Intervals condition on fixed OOF and prior selection and are not multiplicity-adjusted.

来源 SHA-256 逐项匹配批准清单，展示派生表仅写在本目录：

- [A6_feature_additions.csv](A6_feature_additions.csv)
- [A6_reverse_ablation_intervals.csv](A6_reverse_ablation_intervals.csv)

## English caption draft

Feature additions and reverse ablations support distinct within-route comparisons. F0 contains the baseline descriptors; F3 adds composition chemistry, missingness and charge/ionic-geometry descriptors including tau; E1 adds the neutral-atom electronic block. For R-log, pooled RMSE falls from 5.1954 at F0 to 4.9547 at F3 and 4.9048 at F3+E1; mean EF rises from 27.05 to 57.37 and 60.49. The lower panels compare H-soft after removing electronic, geometry or X-statistics blocks with full H-soft, using removal minus full as the sign convention. Removing geometry increases RMSE by 0.1396 and decreases EF by 8.7049. Horizontal bars reuse the corrected 95% paired AB percentile intervals from 5,000 stored resamples; EF uses the equal-fold macro endpoint. The intervals condition on frozen OOF and prior selection, are exploratory, and have no multiplicity correction. Removals include tagged dependencies; X-statistics removal also removes dependent geometry terms, so these are not orthogonal causal effects. No additional fits, bootstrap draws or selection are performed.

## 提交自查

- [x] dpi：PNG 为 300 dpi，另附纯矢量 PDF。
- [x] 字号：实际 Times New Roman 字体已核验并嵌入 PDF，最小 8.5 pt。
- [x] 零中文：图内全部文本为 ASCII 英文及数字/符号。
- [x] 灰度可辨：已查看完整灰度渲染；线型、点形、纹理或直接标签对应图例。
- [x] 色板一致：冻结 A 的语义色与中性描边；色板哈希保持不变。

已检查标签与图形无明显遮挡、文字不越出画布。灰度检查为屏幕渲染检查，尚未做实物打印。模型加载为 0，新增拟合与 bootstrap 抽样均为 0。
