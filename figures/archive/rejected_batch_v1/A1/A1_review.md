# A1 — Residual structure by X family

2026-11-27。已按“后面几个图直接一口气全出”的授权制作并完成彩色/灰度自查，提交用户批量审阅；自查不等于用户已批准入稿。

用途：定位七个 X 族的有符号偏差、RMSE 与绝对残差 q95 差异。 定级：附录图。支撑环节：Model validation。

## 图件

[300 dpi PNG](A1_residual_structure.png) · [矢量 PDF](A1_residual_structure.pdf) · [完整灰度版](A1_residual_structure_grayscale.png) · [机器审计](A1_audit.json)

印刷尺寸 170 × 103 mm；全部使用 Times New Roman，最小 8.5 pt。按此尺寸排版，不再缩小字体。

## 图例指代

三个面板分别直接命名 Bias、RMSE、q95；所有浅蓝条均表示同一 H-soft 路线。横向位置给出数值，左侧为 X 族，点线表示零偏差。不存在另一条未命名比较系列。

## 数据来源与口径

- [OOF_residual_scales_by_X.csv](../../artifacts/p1_v21/results/OOF_residual_scales_by_X.csv)
- [final_selection.json](../../artifacts/p1_v21/final_selection.json)

- 过滤：All seven X families; frozen H-soft external OOF residual summaries; preserve family order.
- 汇总：Use stored values; bias=vhat-V; q95_absolute is an empirical residual quantile.
- 声称边界：Residual quantiles are not calibrated prediction intervals or bootstrap model dispersion. Separate panels avoid mixing signed bias and positive scales.

来源 SHA-256 逐项匹配批准清单，展示派生表仅写在本目录：

- [A1_residual_values.csv](A1_residual_values.csv)

## English caption draft

Small signed biases coexist with substantial differences in error scale across X families. Each family contains 1,608 external OOF predictions from the frozen H-soft route. Bias is the mean of Vhat-V, RMSE is the root mean squared residual, and q95 is the empirical 95th percentile of absolute residuals, all read from the stored summaries. N3 has the largest RMSE (6.6515) and absolute-error q95 (13.8694); these empirical quantiles are not calibrated coverage guarantees.

## 提交自查

- [x] dpi：PNG 为 300 dpi，另附纯矢量 PDF。
- [x] 字号：实际 Times New Roman 字体已核验并嵌入 PDF，最小 8.5 pt。
- [x] 零中文：图内全部文本为 ASCII 英文及数字/符号。
- [x] 灰度可辨：已查看完整灰度渲染；线型、点形、纹理或直接标签对应图例。
- [x] 色板一致：冻结 A 的语义色与中性描边；色板哈希保持不变。

已检查标签与图形无明显遮挡、文字不越出画布。灰度检查为屏幕渲染检查，尚未做实物打印。模型加载为 0，新增拟合与 bootstrap 抽样均为 0。
