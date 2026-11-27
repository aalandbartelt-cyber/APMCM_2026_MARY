# A2 — External OOF probability calibration diagnostics

2026-11-27。已按“后面几个图直接一口气全出”的授权制作并完成彩色/灰度自查，提交用户批量审阅；自查不等于用户已批准入稿。

用途：用既有折外概率检查四条筛选路线的概率刻度与拼接一致性。 定级：附录图。支撑环节：Model validation。

## 图件

[300 dpi PNG](A2_calibration.png) · [矢量 PDF](A2_calibration.pdf) · [完整灰度版](A2_calibration_grayscale.png) · [机器审计](A2_audit.json)

印刷尺寸 170 × 181 mm；全部使用 Times New Roman，最小 8.5 pt。按此尺寸排版，不再缩小字体。

## 图例指代

浅蓝圆点折线为每个非空概率箱的 Observed frequency，灰色虚线为 Ideal calibration: y=x。每个小面板标题为路线名称；下方 n 按从低到高的十个箱依次列出。

## 数据来源与口径

- [main_outer_0.csv.gz](../../artifacts/p1_v21/domains/main_outer_0.csv.gz)
- [main_outer_1.csv.gz](../../artifacts/p1_v21/domains/main_outer_1.csv.gz)
- [main_outer_2.csv.gz](../../artifacts/p1_v21/domains/main_outer_2.csv.gz)
- [main_outer_3.csv.gz](../../artifacts/p1_v21/domains/main_outer_3.csv.gz)
- [main_outer_4.csv.gz](../../artifacts/p1_v21/domains/main_outer_4.csv.gz)
- [oof_calibration_consistency.csv](../../artifacts/p1_v21/results/oof_calibration_consistency.csv)
- [oof_calibration_ranking_checks.csv](../../artifacts/p1_v21/results/oof_calibration_ranking_checks.csv)

- 过滤：External OOF calibrated score for the four probability routes; no H-soft -vhat used as probability. Diagnostic intercept/slope from fold=pooled rows only.
- 汇总：Presentation-only 10 fixed equal-width bins over [0,1] from stored OOF probabilities; count-weighted means; empty bins omitted and identified. Use existing diagnostic coefficients; fit nothing.
- 声称边界：No new logistic/Platt/isotonic fit. Coefficients and reliability curves are diagnostic, not new selection rules. Pooled ranking diagnostics do not replace fold-specific EF.

来源 SHA-256 逐项匹配批准清单，展示派生表仅写在本目录：

- [A2_existing_pooled_diagnostics.csv](A2_existing_pooled_diagnostics.csv)
- [A2_reliability_bins.csv](A2_reliability_bins.csv)

## English caption draft

The chained S-eps probability retains a scale discrepancy despite component calibration. Its stored pooled diagnostic slope is 1.7617 and intercept is 0.9794. The four panels use the same 11,256 external OOF observations (128 V<=2 cases) and ten pre-specified equal-width probability bins. Points show the mean stored probability and empirical event frequency in each nonempty bin; counts are listed in bin order, with the final bin including 1. Intercepts, slopes and Brier scores are read from existing results; no calibration is refitted. Raw-versus-calibrated Top-20 overlap is 20/20 within every fold for B-eps, L-single and L-hash4, but 15/20, 16/20 and 16/20 after pooling, respectively. This comparison is not recorded for S-eps. Pooled diagnostics assess probability scale and do not replace the fold-specific screening endpoint; sparse high-probability bins remain descriptive.

## 提交自查

- [x] dpi：PNG 为 300 dpi，另附纯矢量 PDF。
- [x] 字号：实际 Times New Roman 字体已核验并嵌入 PDF，最小 8.5 pt。
- [x] 零中文：图内全部文本为 ASCII 英文及数字/符号。
- [x] 灰度可辨：已查看完整灰度渲染；线型、点形、纹理或直接标签对应图例。
- [x] 色板一致：冻结 A 的语义色与中性描边；色板哈希保持不变。

已检查标签与图形无明显遮挡、文字不越出画布。灰度检查为屏幕渲染检查，尚未做实物打印。模型加载为 0，新增拟合与 bootstrap 抽样均为 0。
