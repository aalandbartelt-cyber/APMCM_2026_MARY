# P1 图件重改 v2：审阅索引

2026-11-27。首轮仅 F1 通过；本轮已重做 F2、F3、A1–A6，F1 v3 的图件与原审计文件保持字节不变。

**[合并审阅 PDF v2：九图九页，带书签](P1_figures_review_v2.pdf)** · [同名常用入口](P1_figures_review.pdf)

按本轮要求取消全图大标题、嵌入表格和解释段落；八图改用不同图型，并补齐与图元匹配的图例。F2 低 EF 放大窗含原图范围框、连接线及明确坐标，颜色/点形/线型与主图一致。

| 图号 | 用途与新版图型 | 图件 | 来源、caption、图例与九项自查 |
| --- | --- | --- | --- |
| F1 v3（已通过） | 数据审计与 AB 阻断；原件未动 | [PNG](F1/F1_data_audit_v3.png) / [PDF](F1/F1_data_audit_v3.pdf) / [灰度](F1/F1_data_audit_v3_grayscale.png) | [原审图单](F1/F1_review.md) |
| F2 v2 | 在相同逐折预算下比较命中与富集，并放大分辨低 EF 的两条基线。 | [PNG](F2/F2_enrichment_v2.png) / [PDF](F2/F2_enrichment_v2.pdf) / [灰度](F2/F2_enrichment_v2_grayscale.png) | [逐图审图单](F2/F2_review.md) |
| F3 v2 | 展示金属/非金属误差贡献及登记回归路线的 RMSE–EF 权衡。 | [PNG](F3/F3_error_tradeoff_v2.png) / [PDF](F3/F3_error_tradeoff_v2.pdf) / [灰度](F3/F3_error_tradeoff_v2_grayscale.png) | [逐图审图单](F3/F3_review.md) |
| A1 v2 | 将 X 族的有符号偏差与 RMSE/q95 误差尺度并列比较。 | [PNG](A1/A1_residual_structure_v2.png) / [PDF](A1/A1_residual_structure_v2.pdf) / [灰度](A1/A1_residual_structure_v2_grayscale.png) | [逐图审图单](A1/A1_review.md) |
| A2 v2 | 展示四条既有折外概率曲线与理想校准线的差异。 | [PNG](A2/A2_calibration_v2.png) / [PDF](A2/A2_calibration_v2.pdf) / [灰度](A2/A2_calibration_v2_grayscale.png) | [逐图审图单](A2/A2_review.md) |
| A3 v2 | 同时展示四池名义候选的成员名次分布与双向代理 regret。 | [PNG](A3/A3_decision_stability_v2.png) / [PDF](A3/A3_decision_stability_v2.pdf) / [灰度](A3/A3_decision_stability_v2_grayscale.png) | [逐图审图单](A3/A3_review.md) |
| A4 v2 | 用四池斜率线对照 single 与十成员均值的决策稳定性。 | [PNG](A4/A4_split_half_v2.png) / [PDF](A4/A4_split_half_v2.pdf) / [灰度](A4/A4_split_half_v2_grayscale.png) | [逐图审图单](A4/A4_review.md) |
| A5 v2 | 用协议×指标矩阵展示既有压力结果及同路线 OOF 参照变化。 | [PNG](A5/A5_stress_protocols_v2.png) / [PDF](A5/A5_stress_protocols_v2.pdf) / [灰度](A5/A5_stress_protocols_v2_grayscale.png) | [逐图审图单](A5/A5_review.md) |
| A6 v2 | 用双向须线展示最终 H-soft 三组反向消融的既有配对区间。 | [PNG](A6/A6_ablation_v2.png) / [PDF](A6/A6_ablation_v2.pdf) / [灰度](A6/A6_ablation_v2_grayscale.png) | [逐图审图单](A6/A6_review.md) |

全部新图：300 dpi PNG + 矢量 PDF + 完整灰度 PNG；170 mm 宽，实际 Times New Roman ≥8.5 pt。九项自查逐张列在审图单，另核对图例、局部放大与无棒棒糖图。图内单词数（含刻度和数字）合计由 1065 降至 404，减少 62.1%。

本轮按用户新指令采用 reference 30 的钢蓝/琥珀及辅助色家族；[配色修订记录](palette_redesign_v2.json) 明确覆盖关系。原 A 色板文件保留，F1 作为已批准原件不改。A1/A5 的连续色条本身就是图例，A3 用发散色端点与左右位置区分 regret 方向。

短 caption 和正文读法分开保存；[完整伴随诊断数字](P1_FIGURE_COMPANION_TABLES_v2.md) 不再嵌入图内。A5 的 protocol-level evidence, not final-model 限定保留在 caption。A6 只画最终 H-soft 反向消融区间，原 R-log 特征阶梯移到伴随材料。

- [当前 16 列图件清单](figure_inventory.csv)
- [本轮视觉重设计说明](P1_VISUAL_REDESIGN_v2.md)
- [新版来源清单与哈希](figure_inventory_sources_v2.json)
- [交付回执与输入保护核验](P1_redesign_delivery_receipt_v2.json)
- [完整彩色/灰度目检记录](visual_review_checkpoint_v2.json)
- [仓库检查结果](P1_repository_checks_v2.json)
- [退回版完整存档](archive/rejected_batch_v1/P1_FIGURES_REVIEW.md)

所有八图仅提交审阅，尚未宣称用户通过或嵌入论文。全程只读 artifacts、只写 figures/；模型代码、P1 artifacts、官方 D 数据及拟合账本完整哈希未变，账本仍为 914 次 start，新增拟合与 bootstrap 抽样均为 0。

复现：`PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_p1_redesign.py all`。重新渲染后须按像素与视觉检查更新审阅状态；旧版 renderer 属于历史方案，不应覆盖本轮交付。
