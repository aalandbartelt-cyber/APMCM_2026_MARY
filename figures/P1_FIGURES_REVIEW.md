# P1 图件审阅：第八页配色 v4

2026-11-27。本轮只更新第 **8 页（A5 v4）**：按用户提供的 A1(a) 图片匹配钢蓝—白—琥珀色图，数字改用清晰深色。其余八张图及原审计文件保持字节不变，既有验收状态沿用上轮记录。

**[合并审阅 PDF v4：仍为九图九页](P1_figures_review_v4.pdf)** · [原常用入口](P1_figures_review.pdf)

| 页码 | 图件与状态 | 本轮修改/用途 | 文件 | 审图单与来源 |
| --- | --- | --- | --- | --- |
| 1 | F1 v3：已通过，原件保留 | Show the V distribution, metal/nonmetal imbalance and leakage-controlled AB split. | [PNG](F1/F1_data_audit_v3.png) / [PDF](F1/F1_data_audit_v3.pdf) / [灰度](F1/F1_data_audit_v3_grayscale.png) | [审图单](F1/F1_review.md) |
| 2 | F2 v3：上轮修订，待验收 | 低 EF 放大区改为贴近主图的共享横轴窄带；统一左右边界，采用短竖直连接线，保留来源框及相同坐标含义。 | [PNG](F2/F2_enrichment_v3.png) / [PDF](F2/F2_enrichment_v3.pdf) / [灰度](F2/F2_enrichment_v3_grayscale.png) | [审图单](F2/F2_review_v3.md) |
| 3 | F3 v2：已通过，原件保留 | Show which sample class contributes to squared error and where registered regressors lie in RMSE-EF space. | [PNG](F3/F3_error_tradeoff_v2.png) / [PDF](F3/F3_error_tradeoff_v2.pdf) / [灰度](F3/F3_error_tradeoff_v2_grayscale.png) | [审图单](F3/F3_review.md) |
| 4 | A1 v3：上轮修订，待验收 | (b) 改成成对横条；每行重新标明 X 族，14 个值直接标在条末。RMSE 用实色，q95 用斜纹，避免灰度下依赖颜色辨认。 | [PNG](A1/A1_residual_structure_v3.png) / [PDF](A1/A1_residual_structure_v3.pdf) / [灰度](A1/A1_residual_structure_v3_grayscale.png) | [审图单](A1/A1_review_v3.md) |
| 5 | A2 v2：已通过，原件保留 | Evaluate probability scale separately from ranking performance without refitting calibrators. | [PNG](A2/A2_calibration_v2.png) / [PDF](A2/A2_calibration_v2.pdf) / [灰度](A2/A2_calibration_v2_grayscale.png) | [审图单](A2/A2_review.md) |
| 6 | A3 v2：已通过，原件保留 | Distinguish candidate identity changes from their cost in the existing surrogate tables. | [PNG](A3/A3_decision_stability_v2.png) / [PDF](A3/A3_decision_stability_v2.pdf) / [灰度](A3/A3_decision_stability_v2_grayscale.png) | [审图单](A3/A3_review.md) |
| 7 | A4 v2：已通过，原件保留 | Compare averaging and single-member stability under the existing fixed split-half design. | [PNG](A4/A4_split_half_v2.png) / [PDF](A4/A4_split_half_v2.pdf) / [灰度](A4/A4_split_half_v2_grayscale.png) | [审图单](A4/A4_review.md) |
| 8 | A5 v4：本轮配色修订，待验收 | 复用参考图的钢蓝—白—琥珀渐变；150 × 150 mm 方形布局、全部数据不变。 | [PNG](A5/A5_stress_protocols_v4.png) / [PDF](A5/A5_stress_protocols_v4.pdf) / [灰度](A5/A5_stress_protocols_v4_grayscale.png) | [审图单](A5/A5_review_v4.md) |
| 9 | A6 v2：已通过，原件保留 | Separate the R-log feature ladder from reverse ablations of the final H-soft model. | [PNG](A6/A6_ablation_v2.png) / [PDF](A6/A6_ablation_v2.pdf) / [灰度](A6/A6_ablation_v2_grayscale.png) | [审图单](A6/A6_review.md) |

当前 F2/A1/A5 均为 300 dpi PNG、矢量 PDF 和完整灰度 PNG，实际 Times New Roman ≥8.5 pt；九项自查逐张附在审图单。F2 为 170 × 118 mm，A1 为 170 × 102 mm，A5 为 150 × 150 mm。图例、图元和色条已逐项核对，灰度图已打开检查。

A5 直接复用用户所附 A1(a) 参考图的连续色图，见 [当前配色记录](palette_A5_reference_v4.json)。负蓝/零白/正琥珀及 ±80% 归一化范围未变。格内数字最低对比度为 4.65:1，灰度已检查；protocol-level evidence, not final-model 边界保留在 caption。完整数字继续使用 [伴随材料](P1_FIGURE_COMPANION_TABLES_v2.md)。

本轮只写 figures/，数据展示 CSV 未改；模型、P1 artifacts、官方 D 数据和拟合账本哈希未变，新增拟合与 bootstrap 抽样为 0。未嵌入论文。

- [16 列图件清单](figure_inventory.csv)
- [来源与输出核验、交付回执](P1_redesign_delivery_receipt_v4.json)
- [彩色与灰度目检记录](visual_review_checkpoint_v4.json)
- [仓库检查结果](P1_repository_checks_v4.json)
- [本轮授权与已接受原件哈希](A5_color_revision_v4_authorization.json)
- [上一轮索引存档](archive/before_A5_color_v4/P1_FIGURES_REVIEW.md)

仅重现本次第八页：`PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_A5_palette_v4.py`。重新渲染后需更新目检像素记录，再运行 finalize_A5_palette_v4.py；不要运行旧版批量生成器覆盖其余图。
