# A4 — Split-half averaging and decision stability

2026-11-27。已按“后面几个图直接一口气全出”的授权制作并完成彩色/灰度自查，提交用户批量审阅；自查不等于用户已批准入稿。

用途：对比十成员均值和单成员参照的 argmin 一致率与跨表 regret。 定级：附录图。支撑环节：Model validation; P1 output-interface evidence。

## 图件

[300 dpi PNG](A4_split_half.png) · [矢量 PDF](A4_split_half.pdf) · [完整灰度版](A4_split_half_grayscale.png) · [机器审计](A4_audit.json)

印刷尺寸 170 × 118 mm；全部使用 Times New Roman，最小 8.5 pt。按此尺寸排版，不再缩小字体。

## 图例指代

浅蓝实心圆为 Mean of 10 members，灰色空心方块为 Single-member reference。两面板点和数字均为既有均值；右面板竖线为既有切分的 p50–p95 描述性范围。

## 数据来源与口径

- [split_half_summary.csv](../../artifacts/p1_v21/hardening/split_half_summary.csv)
- [protocol.json](../../artifacts/p1_v21/hardening/protocol.json)
- [P23_construction_decision.json](../../artifacts/p1_v21/hardening/P23_construction_decision.json)

- 过滤：bagged_half10 and single_member; 1000 fixed complementary splits of the same 20 members.
- 汇总：Use stored means; regret p50/p95 labels are descriptive split dispersion, not confidence limits. Single-member reference is the average of all 100 cross-half pairs per split.
- 声称边界：This is 10-versus-10 stability evidence, not 1000 independent experiments or verified accuracy of the future mean20 table. No P23 retraining or QUBO solve.

来源 SHA-256 逐项匹配批准清单，展示派生表仅写在本目录：

- [A4_split_half_values.csv](A4_split_half_values.csv)

## English caption draft

Averaging improves observed split-half decision stability while leaving the minimizer uncertain. Mean-of-ten halves reduce mean symmetric cross-table regret in all four pools. Their argmin agreement in pools 11 and 12 is still only 0.192 and 0.174. Each of the 1,000 complementary partitions reuses the same 20 existing members; the single-member reference averages all 100 cross-half member pairs in that partition. Markers and numeric labels show stored means, and vertical regret ranges show stored p50-p95 dispersion, not confidence limits from independent experiments. These are ten-versus-ten stability results and do not verify the accuracy of a future full twenty-member mean table.

## 提交自查

- [x] dpi：PNG 为 300 dpi，另附纯矢量 PDF。
- [x] 字号：实际 Times New Roman 字体已核验并嵌入 PDF，最小 8.5 pt。
- [x] 零中文：图内全部文本为 ASCII 英文及数字/符号。
- [x] 灰度可辨：已查看完整灰度渲染；线型、点形、纹理或直接标签对应图例。
- [x] 色板一致：冻结 A 的语义色与中性描边；色板哈希保持不变。

已检查标签与图形无明显遮挡、文字不越出画布。灰度检查为屏幕渲染检查，尚未做实物打印。模型加载为 0，新增拟合与 bootstrap 抽样均为 0。
