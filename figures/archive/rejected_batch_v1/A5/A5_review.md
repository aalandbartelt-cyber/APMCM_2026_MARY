# A5 — Protocol-level extrapolation stress diagnostics

2026-11-27。已按“后面几个图直接一口气全出”的授权制作并完成彩色/灰度自查，提交用户批量审阅；自查不等于用户已批准入稿。

用途：在明确分母及模型范围的前提下报告三种压力协议的结果。 定级：附录图。支撑环节：Model validation。

## 图件

[300 dpi PNG](A5_stress_protocols.png) · [矢量 PDF](A5_stress_protocols.pdf) · [完整灰度版](A5_stress_protocols_grayscale.png) · [机器审计](A5_audit.json)

印刷尺寸 170 × 139 mm；全部使用 Times New Roman，最小 8.5 pt。按此尺寸排版，不再缩小字体。

## 图例指代

纯浅蓝柱为 R-log，浅蓝斜纹柱为 S-eps；左面板只报告 R-log 的 RMSE。横轴直接命名 Element、Target、X-leave，下方表格给出各自评价次数、样本暴露量与预算。

## 数据来源与口径

- [stress_summary.csv](../../artifacts/p1_v21/results/stress_summary.csv)
- [stress_detail.csv](../../artifacts/p1_v21/results/stress_detail.csv)

- 过滤：Only registered R-log and S-eps stress results; three distinct protocols; no substitution as final H-soft validation.
- 汇总：Use stored summaries and valid evaluation counts: element 5/5; target 3/3; xleave 29/35 for EF. Undefined M=0 cases remain undefined.
- 声称边界：No cross-protocol ease ranking from EF magnitudes: populations, prevalence and total budgets differ. Element evaluation repeats compositions; no independent-row CI.

来源 SHA-256 逐项匹配批准清单，展示派生表仅写在本目录：

- [A5_protocol_denominators.csv](A5_protocol_denominators.csv)
- [A5_stress_values.csv](A5_stress_values.csv)

## English caption draft

The stress results describe the registered protocols rather than validate the final H-soft model out of domain. R-log pooled RMSE is 5.7805, 5.1796 and 6.5035 under element, target and X-leave evaluation, respectively. Screening EF is shown separately for R-log and S-eps, with equal weight per evaluation where EF is defined. Valid EF counts are 5/5, 3/3 and 29/35; six zero-positive X-leave evaluations remain undefined. The table includes all-evaluation budgets of 100, 60 and 700 selections; the defined-EF budgets are 100, 60 and 580. N/M sums are evaluation exposures, including repeated compositions in element tests. Different populations, prevalences and budgets prevent an ease ranking from cross-protocol EF magnitudes. These are protocol-level evidence, not final-model results.

## 提交自查

- [x] dpi：PNG 为 300 dpi，另附纯矢量 PDF。
- [x] 字号：实际 Times New Roman 字体已核验并嵌入 PDF，最小 8.5 pt。
- [x] 零中文：图内全部文本为 ASCII 英文及数字/符号。
- [x] 灰度可辨：已查看完整灰度渲染；线型、点形、纹理或直接标签对应图例。
- [x] 色板一致：冻结 A 的语义色与中性描边；色板哈希保持不变。

已检查标签与图形无明显遮挡、文字不越出画布。灰度检查为屏幕渲染检查，尚未做实物打印。模型加载为 0，新增拟合与 bootstrap 抽样均为 0。
