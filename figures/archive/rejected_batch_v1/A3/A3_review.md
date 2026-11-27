# A3 — Nominal-candidate rank and surrogate decision regret

2026-11-27。已按“后面几个图直接一口气全出”的授权制作并完成彩色/灰度自查，提交用户批量审阅；自查不等于用户已批准入稿。

用途：结合全部成员的名次及双向代理 regret，判断四池候选轮换的代价。 定级：附录图。支撑环节：Model validation; P1 output-interface evidence。

## 图件

[300 dpi PNG](A3_decision_stability.png) · [矢量 PDF](A3_decision_stability.pdf) · [完整灰度版](A3_decision_stability_grayscale.png) · [机器审计](A3_audit.json)

印刷尺寸 170 × 142 mm；全部使用 Times New Roman，最小 8.5 pt。按此尺寸排版，不再缩小字体。

## 图例指代

左面板每个点为一个既有成员给名义候选的名次，仅竖向错开重叠点；横轴为对数名次。右面板圆/三角/方块/叉号分别为 p50/p90/p95/max。F 用实线实心标记，表示名义选择在成员表中的代价；R 用虚线空心标记，表示成员选择在名义表中的代价。点线为 0.1 描述性容忍值。

## 数据来源与口径

- [decision_stability_members.csv](../../artifacts/p1_v21/hardening/decision_stability_members.csv)
- [decision_stability_summary.csv](../../artifacts/p1_v21/hardening/decision_stability_summary.csv)
- [protocol.json](../../artifacts/p1_v21/hardening/protocol.json)

- 过滤：Four pools; all 20 pre-existing members; nominal candidate La|Ti|NO2; fixed tie hash.
- 汇总：Use all 80 member records and stored quantiles; report min/max ranks and the descriptive 0.1 regret tolerance.
- 声称边界：Regret is surrogate-table cost, not true-V regret. Identity rotation alone is not instability severity; no tiny-cost claim; no truth labels read.

来源 SHA-256 逐项匹配批准清单，展示派生表仅写在本目录：

- [A3_member_ranks.csv](A3_member_ranks.csv)
- [A3_regret_quantiles.csv](A3_regret_quantiles.csv)

## English caption draft

Nominal-candidate identity changes have nonzero costs in the existing surrogate tables. All 20 member ranks are shown for each pool; the pool-08 rank spans 1-72. Nearby ranks are spread vertically for visibility; ranks use a logarithmic horizontal axis without changing their values. In the right panel, F measures the nominal choice against the optimum in each member table, and R measures the member's choice against the optimum in the nominal table. Markers show p50, p90, p95 and maximum regret; solid/filled versus dashed/open marks distinguish the directions. No pool satisfies the registered rule requiring both directions to stay within 0.1 for every observed member. The tolerance is descriptive and all costs are on the surrogate Vhat scale, not physical truth.

## 提交自查

- [x] dpi：PNG 为 300 dpi，另附纯矢量 PDF。
- [x] 字号：实际 Times New Roman 字体已核验并嵌入 PDF，最小 8.5 pt。
- [x] 零中文：图内全部文本为 ASCII 英文及数字/符号。
- [x] 灰度可辨：已查看完整灰度渲染；线型、点形、纹理或直接标签对应图例。
- [x] 色板一致：冻结 A 的语义色与中性描边；色板哈希保持不变。

已检查标签与图形无明显遮挡、文字不越出画布。灰度检查为屏幕渲染检查，尚未做实物打印。模型加载为 0，新增拟合与 bootstrap 抽样均为 0。
