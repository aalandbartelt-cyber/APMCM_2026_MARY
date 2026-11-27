# P1 图件审阅：三处修订 v3

2026-11-27。本轮只修改第 **2、4、8 页（F2、A1、A5）**。F1 v3、F3/A2/A3/A4/A6 v2 按“其他没问题”记录为已通过；其图件及原审图单、审计文件全部保持字节不变，历史文件内的待审状态由本索引更新。

**[合并审阅 PDF v3：仍为九图九页](P1_figures_review_v3.pdf)** · [原常用入口](P1_figures_review.pdf)

| 页码 | 图件与状态 | 本轮修改/用途 | 文件 | 审图单与来源 |
| --- | --- | --- | --- | --- |
| 1 | F1 v3：已通过，原件保留 | Show the V distribution, metal/nonmetal imbalance and leakage-controlled AB split. | [PNG](F1/F1_data_audit_v3.png) / [PDF](F1/F1_data_audit_v3.pdf) / [灰度](F1/F1_data_audit_v3_grayscale.png) | [审图单](F1/F1_review.md) |
| 2 | F2 v3：本轮修订，待验收 | 低 EF 放大区改为贴近主图的共享横轴窄带；统一左右边界，采用短竖直连接线，保留来源框及相同坐标含义。 | [PNG](F2/F2_enrichment_v3.png) / [PDF](F2/F2_enrichment_v3.pdf) / [灰度](F2/F2_enrichment_v3_grayscale.png) | [审图单](F2/F2_review_v3.md) |
| 3 | F3 v2：已通过，原件保留 | Show which sample class contributes to squared error and where registered regressors lie in RMSE-EF space. | [PNG](F3/F3_error_tradeoff_v2.png) / [PDF](F3/F3_error_tradeoff_v2.pdf) / [灰度](F3/F3_error_tradeoff_v2_grayscale.png) | [审图单](F3/F3_review.md) |
| 4 | A1 v3：本轮修订，待验收 | (b) 改成成对横条；每行重新标明 X 族，14 个值直接标在条末。RMSE 用实色，q95 用斜纹，避免灰度下依赖颜色辨认。 | [PNG](A1/A1_residual_structure_v3.png) / [PDF](A1/A1_residual_structure_v3.pdf) / [灰度](A1/A1_residual_structure_v3_grayscale.png) | [审图单](A1/A1_review_v3.md) |
| 5 | A2 v2：已通过，原件保留 | Evaluate probability scale separately from ranking performance without refitting calibrators. | [PNG](A2/A2_calibration_v2.png) / [PDF](A2/A2_calibration_v2.pdf) / [灰度](A2/A2_calibration_v2_grayscale.png) | [审图单](A2/A2_review.md) |
| 6 | A3 v2：已通过，原件保留 | Distinguish candidate identity changes from their cost in the existing surrogate tables. | [PNG](A3/A3_decision_stability_v2.png) / [PDF](A3/A3_decision_stability_v2.pdf) / [灰度](A3/A3_decision_stability_v2_grayscale.png) | [审图单](A3/A3_review.md) |
| 7 | A4 v2：已通过，原件保留 | Compare averaging and single-member stability under the existing fixed split-half design. | [PNG](A4/A4_split_half_v2.png) / [PDF](A4/A4_split_half_v2.pdf) / [灰度](A4/A4_split_half_v2_grayscale.png) | [审图单](A4/A4_review.md) |
| 8 | A5 v3：本轮修订，待验收 | 改为 150 × 150 mm 方形画布和等宽高网格；蓝端提亮为 #93BED7，琥珀端采用 #E7BF8E，零点、归一化范围和数值不变。 | [PNG](A5/A5_stress_protocols_v3.png) / [PDF](A5/A5_stress_protocols_v3.pdf) / [灰度](A5/A5_stress_protocols_v3_grayscale.png) | [审图单](A5/A5_review_v3.md) |
| 9 | A6 v2：已通过，原件保留 | Separate the R-log feature ladder from reverse ablations of the final H-soft model. | [PNG](A6/A6_ablation_v2.png) / [PDF](A6/A6_ablation_v2.pdf) / [灰度](A6/A6_ablation_v2_grayscale.png) | [审图单](A6/A6_review.md) |

三张新版均为 300 dpi PNG、矢量 PDF 和完整灰度 PNG，实际 Times New Roman ≥8.5 pt；九项自查逐张附在审图单。F2 为 170 × 118 mm，A1 为 170 × 102 mm，A5 为 150 × 150 mm。图例、图元和色条已逐项核对，灰度图已打开检查。

A5 的浅色调整只作用于本次热图，负蓝/零白/正琥珀语义和 ±80% 色标不变，见 [配色记录](palette_A5_light_v3.json)。其 protocol-level evidence, not final-model 边界仍在 caption 中，未改变统计结论。完整伴随数字继续使用 [v2 伴随材料](P1_FIGURE_COMPANION_TABLES_v2.md)。

本轮只写 figures/，数据展示 CSV 未改；模型、P1 artifacts、官方 D 数据和拟合账本哈希未变，新增拟合与 bootstrap 抽样为 0。未嵌入论文。

- [16 列图件清单](figure_inventory.csv)
- [来源与输出核验、交付回执](P1_redesign_delivery_receipt_v3.json)
- [彩色与灰度目检记录](visual_review_checkpoint_v3.json)
- [仓库检查结果](P1_repository_checks_v3.json)
- [本轮授权与已接受原件哈希](targeted_revision_v3_authorization.json)
- [修订前索引及三图审计存档](archive/before_targeted_v3/P1_FIGURES_REVIEW.md)

仅重现本次三图：`PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_p1_revision_v3.py F2 A1 A5`。旧版生成器保留用于历史复现，不要运行其 all/finalizer 覆盖已接受原件。重新渲染后须重新目检并更新像素核验记录，再运行 finalize_revision_v3.py。
