# P1 收尾加固验收报告

日期：2026-11-27。四项产物均已落盘，机器验收回执为 `artifacts/p1_v21/hardening/hardening_audit.json`。本轮只处理既有表，未改变模型路线、loss、参数、校准器、候选选择或 P1 预测。拟合账本仍为 **914**，剩余 **86** 全部保留给后续 P23。

## P0-1：主 EF 与配对区间口径一致

主终点为五个固定外折内各取 Top-20 后等权平均的 `EF_{V<=2}@20`。5000 次配对 bootstrap 在每个外折内分别重采样有向 AB，所有模型共享频数；任一折 M=0 时整次宏平均无定义。实际所有 5000 次均有效。RMSE 按行汇总。以下差均为 H-soft − R-log：

| metric | delta_point | delta_p025 | delta_p975 | legacy_pooled_delta_p025 | legacy_pooled_delta_p975 |
| --- | --- | --- | --- | --- | --- |
| EF_macro@20 | 1.6160 | -5.9951 | 11.2022 | -13.4000 | 19.4069 |
| RMSE | -0.3037 | -0.4133 | -0.1943 | -0.4156 | -0.1956 |

数值误差改善的条件区间仍低于零；宏平均 EF 差区间跨零，不能声称筛选优势稳定成立。旧 pooled 区间保留在独立文件和 legacy_pooled_* 诊断列；它的 EF 是一次全池 Top-20，与五折总预算 100 的主终点不同，禁止混用。区间均条件于固定 OOF/既往选择，未经多重区间校正，不包含重新研究选模的不确定性。

## P0-2：四池决策稳定性与代价

名义候选来自原全 02 单模型表。rank 为候选在各成员表中的名次，频率分母为既有 20 成员，固定 tie hash。

| pool | nominal_minimizer | nominal_rank_median | nominal_rank_min | nominal_rank_max | nominal_top5_frequency | nominal_top20_frequency | nominal_argmin_frequency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 07 | La\|Ti\|NO2 | 6.0000 | 1 | 24 | 0.4500 | 0.9000 | 0.2000 |
| 08 | La\|Ti\|NO2 | 13.5000 | 1 | 72 | 0.2500 | 0.6500 | 0.1000 |
| 11 | La\|Ti\|NO2 | 2.0000 | 1 | 8 | 0.8000 | 1.0000 | 0.3000 |
| 12 | La\|Ti\|NO2 | 4.5000 | 1 | 15 | 0.6000 | 1.0000 | 0.2000 |

正向 regret 是成员表上坚持名义候选的损失；反向 regret 是名义表上改选成员最优的损失。两者均在原 V 的代理输出尺度，**不是真实 V regret**。成员间隔是该成员最优与次优的值差。

| pool | decision_regret_p50 | decision_regret_p90 | decision_regret_p95 | decision_regret_max | reverse_regret_p95 | reverse_regret_max | member_best_second_gap_p50 | member_best_second_gap_p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 07 | 0.8448 | 2.1975 | 2.8440 | 2.8676 | 2.1349 | 2.5625 | 0.1665 | 0.6627 |
| 08 | 1.1887 | 2.2350 | 3.2419 | 3.6878 | 4.2706 | 5.6729 | 0.1014 | 0.4065 |
| 11 | 0.2586 | 1.3919 | 1.8650 | 2.6991 | 2.1851 | 3.5665 | 0.2586 | 1.1864 |
| 12 | 0.7484 | 1.9964 | 2.7572 | 3.6878 | 6.6253 | 6.6253 | 0.1369 | 0.4200 |

四池均未达到预先登记的近优平台标准。不能仅凭身份轮换称为“失控”，也不能把这里非零的代价称为“都极小”。 预登记容差为双向 regret 的全部已观测值均 <=0.1；此描述性阈值不是物理可行阈值，也与 eps=2 无关。11/12 的名义候选始终在成员 Top-20 中，但 argmin 并不固定；08 的候选名次范围为 1–72。rank、频率、p50/p90/p95/max 和全部 80 成员记录均保留，不能只报中位数。

名义 Top-20 家族集中度如下；完整 Top-5/20 和全部 20 成员的 HHI/有效家族数/背景归一化占比见 family_concentration_detail.csv 与 summary.csv。

| pool | axis | nominal_dominant_family | nominal_dominant_share | nominal_dominant_enrichment | nominal_HHI | member_HHI_p50 |
| --- | --- | --- | --- | --- | --- | --- |
| 07 | A_family | groups_3_to_12 | 0.4500 | 0.8357 | 0.3250 | 0.3400 |
| 07 | B_family | groups_3_to_12 | 0.6000 | 1.1143 | 0.4400 | 0.4950 |
| 07 | X | NO2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 08 | A_family | alkaline_earth | 0.3500 | 3.6400 | 0.2200 | 0.2425 |
| 08 | B_family | groups_3_to_12 | 0.5500 | 1.0214 | 0.4050 | 0.4975 |
| 08 | X | NO2 | 0.4000 | 1.2000 | 0.3400 | 0.4550 |
| 11 | A_family | alkaline_earth | 0.4000 | 3.0229 | 0.3050 | 0.3025 |
| 11 | B_family | groups_3_to_12 | 0.9000 | 1.6647 | 0.8200 | 0.8175 |
| 11 | X | NO2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 12 | A_family | alkaline_earth | 0.5500 | 4.1564 | 0.3600 | 0.3700 |
| 12 | B_family | groups_3_to_12 | 0.6500 | 1.2023 | 0.5450 | 0.5125 |
| 12 | X | NO2 | 0.4500 | 1.3500 | 0.3550 | 0.3900 |

例如 11 池名义 Top-20 中 B 的 groups_3_to_12 占 90%，相对池背景为 1.665 倍；需要保留家族集中的适用边界。07/11 本来只含 NO2，X 占比 100% 只是池定义，不能冒称模型额外偏好。52 元素映射固定且完整，La 单列，Zn/Cd/Hg 包含在 groups_3_to_12 中；不把形式氧化态当已知真值。

## P0-3：主表补齐原有基线及嵌套身份

主汇总共 13 行：8 候选、3 固定基线、2 嵌套流程；逐折明细共 65 行。全部基线直接读取既有 domains/baseline_*.json，未重新拟合。RMSE 是各折 SSE 加总再除总 N 后开方，不是五个 RMSE 的算术平均；金属/非金属贡献相加等于 RMSE 平方。

| route | row_kind | RMSE | metal_MSE_contribution | nonmetal_MSE_contribution | EF_{V<=2}@20_mean | hits20_sum | h_per_fold |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H-soft | registered_candidate | 4.6011 | 18.2920 | 2.8781 | 62.1024 | 68 | [14,14,14,14,12] |
| additive_ridge | fixed_baseline | 6.3206 | 33.5422 | 6.4084 | 8.7049 | 10 | [2,3,2,2,1] |
| mean | fixed_baseline | 11.0143 | 107.7997 | 13.5150 | 0.7271 | 1 | [1,0,0,0,0] |
| nested_numeric | nested_procedure | 4.6011 | 18.2920 | 2.8781 | 62.1024 | 68 | [14,14,14,14,12] |
| nested_screen | nested_procedure | NA | NA | NA | 59.4536 | 67 | [15,15,16,11,10] |
| random_hash | fixed_baseline | NA | NA | NA | 0.0000 | 0 | [0,0,0,0,0] |

| fold | N | M | k | h_H_soft | h_Ridge | h_mean | h_random | nested_numeric | nested_screen | h_nested_screen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 2254 | 31 | 20 | 14 | 2 | 1 | 0 | H-soft | W-log | 15 |
| 1 | 2254 | 29 | 20 | 14 | 3 | 0 | 0 | H-soft | B-eps | 15 |
| 2 | 2254 | 29 | 20 | 14 | 2 | 0 | 0 | H-soft | S-eps | 16 |
| 3 | 2247 | 22 | 20 | 14 | 2 | 0 | 0 | H-soft | W-log | 11 |
| 4 | 2247 | 17 | 20 | 12 | 1 | 0 | 0 | H-soft | S-eps | 10 |

完整主表每行同时保存 N/M/h 向量、嵌套数值与筛选选择身份、该行实际模型身份。mean 的唯一一次命中与固定随机实现的零命中如实报告；随机对照理论期望 EF=1，不能替换观测值。基线未加入新的自适应选型。候选表与嵌套流程有不同推断身份，不能重复计作独立证据。

## P0-4：只按稳定性冻结 P23 均值表规则

1000 个固定互补 10/10 split-half；单模型基准为每次切分两半间全部 100 个成员对的平均，均值表基准为两半各十成员的算术均值。使用同一候选池、同一 tie hash。Top-20 overlap 是重合数/20，regret 是双方在对方表上采用自己选择时的损失均值。

| pool | method | argmin_agreement | top20_overlap_fraction | top20_jaccard | symmetric_cross_table_decision_regret |
| --- | --- | --- | --- | --- | --- |
| 07 | bagged_half10 | 0.538000 | 0.807050 | 0.679126 | 0.250515 |
| 07 | single_member | 0.120580 | 0.632516 | 0.468773 | 1.294868 |
| 08 | bagged_half10 | 0.504000 | 0.682350 | 0.521546 | 0.317291 |
| 08 | single_member | 0.053730 | 0.344842 | 0.214142 | 2.616358 |
| 11 | bagged_half10 | 0.192000 | 0.939100 | 0.886134 | 0.183845 |
| 11 | single_member | 0.163620 | 0.807512 | 0.681166 | 1.071651 |
| 12 | bagged_half10 | 0.174000 | 0.833150 | 0.717432 | 0.241327 |
| 12 | single_member | 0.062440 | 0.632621 | 0.469715 | 2.676668 |

固定条件全部满足，未来采用 **bagged_mean_20**。四池宏平均 Top-20 overlap 增量为 0.211039；没有查看 EF、RMSE 或隐藏真值来挑构造方法。11/12 池十成员均值间 argmin 一致率仍仅 0.192/0.174，均值构造改善了已观测稳定性，不能称最优身份已稳定。

1000 个切分共享 20 个经验成员，不是 1000 次独立实验；split-half 分位数是描述性分散度，不是独立样本置信区间。10 对 10 支持平均化的稳定性，不是对未来全 20 均值准确率的直接验证。原 P1 模型与表保持不变，03 不被重开选模。

`codex/P1_PLANv2.md` §6 已写死未来配方：02+03 固定 H-soft F3+E1、两折 AB OOF 门控校准一次后固定、20 个预定 AB-bootstrap 种子、先按成员计算完整 H-soft 混合 Vhat 再等权平均；相同均值表进 P2/P3，显式 mask/NaN、原尺度 float64 和全部成员分散度保留。预计 65 次确定性树拟合，余下 21 次只留同配方故障恢复。**本轮未执行这 65 次重训，也未求解 P2/P3。**

## 验收与证据索引

- 主结果：`codex/P1_RESULTS_v2.1.md`、`codex/P1_FINAL_RESULTS_v2.1.csv`；逐折：`artifacts/p1_v21/results/P1_main_per_fold.csv`。
- 修正区间：`results/paired_AB_bootstrap_5000.csv`；新旧并列：`results/paired_AB_bootstrap_endpoint_comparison.csv`；原始 pooled 字节保留在 `results/paired_AB_bootstrap_pooled_diagnostic_legacy.csv`。
- 稳定性：`hardening/decision_stability_summary.csv`、`decision_stability_members.csv`、`decision_stability_leading_candidates.csv`、`decision_stability_all_candidates.csv.gz`、`family_concentration_*.csv`。
- Split-half：`hardening/protocol.json`、`split_half_detail.csv.gz`、`split_half_summary.csv`、`P23_construction_decision.json`。全 20 均值与原单表的比较另存 nominal_vs_mean20_diagnostic.csv，仅作描述，不用于选择。
- 原方案：`codex/P1_PLANv2.1_FROZEN.md`；方案增补冻结：`hardening/plan_amendment_freeze.json`。初始保护快照：`hardening/protected_before.json`。
- 验收代码：`03_求解/D/p1_v2/test_hardening.py`、`hardening_audit.py`；验收回执 `hardening/hardening_audit.json`。原 P1 防泄漏审计另存 `final_audit.json`。

仍只能声称指定开发协议中的回归误差、近正例富集和代理决策稳定性；不能声称已验证隐藏 V=0、真实物理最优、可合成性或恢复历史盲态。未新增模型搜索、未提交真机、未改正式论文/交付件。
