# P1 图件批量审阅索引

2026-11-27。按用户“后面几个图直接一口气全出”的新授权，F2、F3、A1–A6 八张已完成，F1 v3 原件保留。

**[连续翻阅 PDF：九图、九页、带书签](P1_figures_review.pdf)**。各页保留原矢量图和 170 mm 宽度，字体最小 8.5 pt；这是审阅合集，尚未嵌入论文。

| 编号 | 用途 | 图件 | 审图单 |
| --- | --- | --- | --- |
| F1 v3（原件） | 展示数据分布、类别构成及 AB 阻断协议。 | [PNG](F1/F1_data_audit_v3.png) / [PDF](F1/F1_data_audit_v3.pdf) / [灰度](F1/F1_data_audit_v3_grayscale.png) | [caption、来源与自查](F1/F1_review.md) |
| F2 | 在相同逐折预算下，对比 H-soft 与三种基线的命中数和近正例富集。 | [PNG](F2/F2_enrichment.png) / [PDF](F2/F2_enrichment.pdf) / [灰度](F2/F2_enrichment_grayscale.png) | [caption、来源与自查](F2/F2_review.md) |
| F3 | 同时展示金属/非金属的误差贡献及登记回归路线的 RMSE–EF 权衡。 | [PNG](F3/F3_error_tradeoff.png) / [PDF](F3/F3_error_tradeoff.pdf) / [灰度](F3/F3_error_tradeoff_grayscale.png) | [caption、来源与自查](F3/F3_review.md) |
| A1 | 定位七个 X 族的有符号偏差、RMSE 与绝对残差 q95 差异。 | [PNG](A1/A1_residual_structure.png) / [PDF](A1/A1_residual_structure.pdf) / [灰度](A1/A1_residual_structure_grayscale.png) | [caption、来源与自查](A1/A1_review.md) |
| A2 | 用既有折外概率检查四条筛选路线的概率刻度与拼接一致性。 | [PNG](A2/A2_calibration.png) / [PDF](A2/A2_calibration.pdf) / [灰度](A2/A2_calibration_grayscale.png) | [caption、来源与自查](A2/A2_review.md) |
| A3 | 结合全部成员的名次及双向代理 regret，判断四池候选轮换的代价。 | [PNG](A3/A3_decision_stability.png) / [PDF](A3/A3_decision_stability.pdf) / [灰度](A3/A3_decision_stability_grayscale.png) | [caption、来源与自查](A3/A3_review.md) |
| A4 | 对比十成员均值和单成员参照的 argmin 一致率与跨表 regret。 | [PNG](A4/A4_split_half.png) / [PDF](A4/A4_split_half.pdf) / [灰度](A4/A4_split_half_grayscale.png) | [caption、来源与自查](A4/A4_review.md) |
| A5 | 在明确分母及模型范围的前提下报告三种压力协议的结果。 | [PNG](A5/A5_stress_protocols.png) / [PDF](A5/A5_stress_protocols.pdf) / [灰度](A5/A5_stress_protocols_grayscale.png) | [caption、来源与自查](A5/A5_review.md) |
| A6 | 分开呈现 R-log 的特征增量与最终 H-soft 的三组反向消融。 | [PNG](A6/A6_ablation.png) / [PDF](A6/A6_ablation.pdf) / [灰度](A6/A6_ablation_grayscale.png) | [caption、来源与自查](A6/A6_review.md) |

八张新图均已检查：300 dpi PNG、白底矢量 PDF、Times New Roman ≥8.5 pt、图内零中文、完整灰度渲染可辨、冻结 A 色板。图例用名称配合线型、点形或纹理，不依赖颜色单独识别。每张审图单都附数据来源、过滤/汇总口径、英文结论式 caption 和五项自查。

F2 的筛选事件统一为 V<=2；k=20 是每折预算，五折共 100 次选择。F3 的 MSE 贡献使用总 N 作分母。A2 未重拟合校准器；A3/A4 的 regret 是代理表尺度；A5 保留 protocol-level evidence, not final-model；A6 的特征增量与反向消融分属不同路线，区间直接取既有结果。

本次只读既有 artifacts，只写 figures/；模型代码、全部 P1 artifacts、官方 D 数据与拟合账本的完整哈希保持不变。账本仍为 914 次 start，新增拟合及 bootstrap 抽样为 0。F1 的原件及其审计文件哈希未变；新授权替代了原逐张等候门禁，自查状态不代表用户已批准入稿。

- [更新后的 16 列图件清单](figure_inventory.csv)
- [批量制图授权](batch_rendering_authorization.json)
- [交付回执与输入保护核验](P1_batch_delivery_receipt.json)
- [彩色/灰度目检记录](visual_review_checkpoint.json)
- [仓库检查结果](P1_repository_checks.json)
- [仅 figures/ 的接续说明](P1_BATCH_HANDOFF.md)

复现绘图：`PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_remaining.py all`。重新渲染会将图件状态重置为待目检；须重新核验后再交付。屏幕灰度检查已完成，未做实物打印。
