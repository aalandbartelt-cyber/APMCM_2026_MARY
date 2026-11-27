# F3 — Error contributions and the regression-screening trade-off

2026-11-27。已按“后面几个图直接一口气全出”的授权制作并完成彩色/灰度自查，提交用户批量审阅；自查不等于用户已批准入稿。

用途：同时展示金属/非金属的误差贡献及登记回归路线的 RMSE–EF 权衡。 定级：正文图。支撑环节：Model validation。

## 图件

[300 dpi PNG](F3_error_tradeoff.png) · [矢量 PDF](F3_error_tradeoff.pdf) · [完整灰度版](F3_error_tradeoff_grayscale.png) · [机器审计](F3_audit.json)

印刷尺寸 170 × 132 mm；全部使用 Times New Roman，最小 8.5 pt。按此尺寸排版，不再缩小字体。

## 图例指代

误差堆叠条：紫色斜纹为 Metal 的 SSE/总 N，浅绿色点纹为 Nonmetal 的 SSE/总 N，条末数字为总 MSE。散点直接标模型名：H-soft 为浅蓝实心圆，R-log 为空心方块，R-raw 为空心三角，W-log 为空心菱形。

## 数据来源与口径

- [P1_final_experiment_table.csv](../../artifacts/p1_v21/results/P1_final_experiment_table.csv)
- [regression_pareto.csv](../../artifacts/p1_v21/results/regression_pareto.csv)
- [paired_AB_bootstrap_5000.csv](../../artifacts/p1_v21/results/paired_AB_bootstrap_5000.csv)

- 过滤：Four registered numeric candidates plus additive_ridge and mean for MSE; Pareto eligibility exactly the four rows of regression_pareto.csv. Pure screening NA values excluded; nested duplicates not double counted.
- 汇总：Metal and nonmetal SSE/total N sum to pooled RMSE squared; never plot conditional class MSE as contributions.
- 声称边界：No RMSE assigned to pure classifiers/rankers. Pareto dominance is limited to the registered regression menu, not a universal or causal claim.

来源 SHA-256 逐项匹配批准清单，展示派生表仅写在本目录：

- [F3_MSE_contributions.csv](F3_MSE_contributions.csv)
- [F3_registered_pareto.csv](F3_registered_pareto.csv)

## English caption draft

H-soft is nondominated within the registered regression menu, while its screening advantage over R-log remains uncertain. Its pooled RMSE is 4.6011 and its metal/nonmetal contributions to total MSE are 18.2920 and 2.8781. Each contribution is class-specific SSE divided by the total sample count; stacked sums equal pooled RMSE squared. Six numeric routes are shown for error decomposition, while the Pareto comparison uses only the four registered regressors. H-soft minus R-log has an EF difference of +1.6160 with the existing 95% paired AB percentile interval [-5.9951, 11.2022], conditional on frozen OOF predictions and prior selection without multiplicity correction. Pure screening routes have no assigned RMSE.

## 提交自查

- [x] dpi：PNG 为 300 dpi，另附纯矢量 PDF。
- [x] 字号：实际 Times New Roman 字体已核验并嵌入 PDF，最小 8.5 pt。
- [x] 零中文：图内全部文本为 ASCII 英文及数字/符号。
- [x] 灰度可辨：已查看完整灰度渲染；线型、点形、纹理或直接标签对应图例。
- [x] 色板一致：冻结 A 的语义色与中性描边；色板哈希保持不变。

已检查标签与图形无明显遮挡、文字不越出画布。灰度检查为屏幕渲染检查，尚未做实物打印。模型加载为 0，新增拟合与 bootstrap 抽样均为 0。
