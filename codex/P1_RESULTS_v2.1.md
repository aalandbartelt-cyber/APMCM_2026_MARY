# P1 v2.1 最终实验报告

日期：2026-11-26。状态：P1 实施完成；本报告由冻结实验产物生成，未作新一轮选模。

最终数值模型：**H-soft**；最终近正例筛选模型：**H-soft**。筛选事件固定为 **V<=2**，不是 V=0。正式数值输出与筛选打分分列。

## 主实验结果

下表 RMSE 和两项 MSE 贡献来自拼接的完整外层 OOF；EF/NDCG/regret 是五个完整外折评估池的均值。每折预算 20，因此 hits20_sum 的总预算为 100，不能解释为单池 Top-20 命中。

| route | RMSE | metal_MSE_contribution | nonmetal_MSE_contribution | EF_{V<=2}@20_mean | hits20_sum | NDCG@20_mean | regret@20_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-eps | NA | NA | NA | 64.2723 | 72 | 0.7023 | 0.0494 |
| H-soft | 4.6011 | 18.2920 | 2.8781 | 62.1024 | 68 | 0.6952 | 0.0437 |
| L-hash4 | NA | NA | NA | 46.8397 | 54 | 0.5718 | 0.0699 |
| L-single | NA | NA | NA | 28.6526 | 33 | 0.3554 | 0.2023 |
| R-log | 4.9048 | 21.0176 | 3.0398 | 60.4863 | 67 | 0.6671 | 0.0045 |
| R-raw | 4.7583 | 18.4524 | 4.1889 | 51.3372 | 57 | 0.6039 | 0.0049 |
| S-eps | NA | NA | NA | 62.2234 | 70 | 0.6479 | 0.0349 |
| W-log | 5.5580 | 28.1905 | 2.7011 | 59.2209 | 66 | 0.6828 | 0.0349 |

这是各登记候选的配对表现；据此挑最佳再报告同一表仍有开发选择乐观性。另存嵌套流程的独立外层评价：

| procedure | RMSE_pooled | EF_{V<=2}@20_mean | hits20_sum |
| --- | --- | --- | --- |
| numeric | 4.6011 | 62.1024 | 68 |
| screen | NA | 59.4536 | 67 |

## 03 开发选择

最多三个候选在拟合和名单冻结后一次性评估；03 不参与训练或校准，但本轮及历史均用于开发，不能称独立最终测试。此池 N=3969、M=41、k=20。

| route | RMSE | MAE | metal_MSE_contribution | nonmetal_MSE_contribution | EF_{V<=2}@20 | hits@20 | NDCG@20 | regret@20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H-soft | 4.5783 | 2.6241 | 17.1603 | 3.8008 | 62.9232 | 13 | 0.5974 | 0.0000 |
| B-eps | NA | NA | NA | NA | 62.9232 | 13 | 0.4573 | 0.1248 |

固定规则分别决定数值和筛选用途。H-soft 与 B-eps 的近正例命中同为 13/20；H-soft 由预登记的 NDCG 并列规则胜出，不是 EF 更高。没有 1.02 倍 RMSE 否决门槛，没有用 03 早停或挑哈希种子。H-soft 的筛选分数仍是 -Vhat，不宣称为近正例概率。

当前四条回归候选的 Pareto 非支配集合为：**H-soft**。这只限于登记菜单，不代表所有可能模型的最优性。

## 消融、外推与校准

完整逐折/逐 X/压力测试、F0/F3/F3+E1、三组反向消融、两次重复划分以及三 Query 种子记录位于 `artifacts/p1_v21/results/`。元素测试有重复覆盖的组成；X 留出同时排除测试 AB；目标区域留出不等价于真正零点外推。

特征与反向消融表：

| protocol | route | feature_set | RMSE_pooled | EF_{V<=2}@20_mean | hits20_sum |
| --- | --- | --- | --- | --- | --- |
| ablation | H-soft | minus_electronic | 4.6426 | 56.5887 | 63 |
| ablation | H-soft | minus_geometry | 4.7407 | 53.3975 | 58 |
| ablation | H-soft | minus_xstats | 4.6424 | 59.7091 | 66 |
| feature | R-log | F0 | 5.1954 | 27.0472 | 30 |
| feature | R-log | F3 | 4.9547 | 57.3660 | 64 |

R-log 的 F3+E1 RMSE 为 4.9048，相比 F3 的 4.9547 有小幅改善；其配对区间见下表。H-soft 去几何后的 RMSE 增加约 0.1396；去电子或去 X 统计的误差增量更小，区间跨零，不能给出独立确定贡献的强结论。两次额外分组重复合并 RMSE 为 4.6088；不同划分的 EF 仍有波动。

预登记压力测试表：

| protocol | route | evaluations | EF_defined_evaluations | RMSE_pooled | EF_{V<=2}@20_mean | hits20_sum |
| --- | --- | --- | --- | --- | --- | --- |
| element | R-log | 5 | 5 | 5.7805 | 45.4607 | 49 |
| element | S-eps | 5 | 5 | NA | 51.4131 | 55 |
| target | R-log | 3 | 3 | 5.1796 | 16.7296 | 41 |
| target | S-eps | 3 | 3 | NA | 18.3601 | 45 |
| xleave | R-log | 35 | 29 | 6.5035 | 12.9015 | 99 |
| xleave | S-eps | 35 | 29 | NA | 14.7193 | 114 |

压力测试按计划只训练 R-log 和 S-eps，**不是最终 H-soft 的直接域外验证**。EF 均值只包含 M>0 的有效评估池，其数量单列；M=0 不填零。不同协议的评估池、M 和总预算不同，不能横向按 EF 大小比较“哪种外推更容易”。V<2 区域全部留出时，S-eps 条件事件头缺正类而退化为平滑先验，该情景的排序主要依赖门控，不能解释成恢复了未见零点监督。

概率校准在训练域 OOF 拟合。独立外层的 Brier、可靠性曲线、诊断斜率/截距以及 raw/calibrated OOF 拼接名单比较分别保存。诊断回归不改变任何预测，不据结果再选校准器。纯筛选器没有原尺度 RMSE。

拼接 OOF 的独立校准诊断如下；理想诊断截距/斜率为 0/1，但这里不据此作新的硬筛选：

| route | brier | mean_probability | prevalence | calibration_intercept | calibration_slope |
| --- | --- | --- | --- | --- | --- |
| B-eps | 0.0058 | 0.0126 | 0.0114 | 0.2785 | 1.2436 |
| L-hash4 | 0.0074 | 0.0128 | 0.0114 | -0.2503 | 0.9817 |
| L-single | 0.0109 | 0.0119 | 0.0114 | -0.5843 | 0.8406 |
| S-eps | 0.0061 | 0.0120 | 0.0114 | 0.9794 | 1.7617 |

门控平均 Brier 由 0.015913 变为 0.015893，条件事件头由 0.156119 变为 0.155870，改善很小。S-eps 乘积的诊断斜率约 1.76，说明分量经过校准并不保证乘积整体充分校准。B-eps 的 Brier 从 0.007372 降为 0.005750；不能把概率刻度改进等同于排序改进。

两种排序器及 B-eps 在每个外折内，校准前后 Top-20 都保持 20/20 一致；拼接 OOF 时重合数为 15/20 或 16/20。跨折尺度会改变全池排序，因此拼接名单作为诊断单列，没有替代每折完整池主终点。

额外 Query 种子相对登记种子 0 的稳定性：

| route | EF_mean | overlap_mean | overlap_min | overlap_max |
| --- | --- | --- | --- | --- |
| L-hash4-seed1 | 49.9038 | 15.0000 | 12.0000 | 17.0000 |
| L-hash4-seed2 | 48.9387 | 15.2000 | 13.0000 | 18.0000 |

种子 0 的 L-hash4 平均 EF 为 46.8397。额外种子 Top-20 平均重合约 15/20，不能称名单完全稳定；也没有把额外种子的较好结果替换主结果。单 Query 在本轮二元 relevance、固定容量配置下弱于四 Query，这不构成对全部 LambdaRank 设置的结论。

配对 AB bootstrap 的固定比较（5000 次，条件于既有 OOF 和既往选择，不包含完整研究选择不确定性；区间未作多重区间校正，按探索性解释）：

| model | reference | metric | delta_p025 | delta_median | delta_p975 |
| --- | --- | --- | --- | --- | --- |
| H-soft | R-log | RMSE | -0.4156 | -0.3037 | -0.1956 |
| H-soft | R-log | EF_{V<=2}@20 | -13.4000 | 4.3628 | 19.4069 |
| S-eps | B-eps | EF_{V<=2}@20 | -25.1250 | -4.5024 | 14.1882 |
| L-single | L-hash4 | EF_{V<=2}@20 | -69.0226 | -39.9149 | -14.1882 |
| R-log | R-log_F3 | RMSE | -0.0756 | -0.0496 | -0.0237 |
| R-log | R-log_F3 | EF_{V<=2}@20 | -9.7900 | 3.9083 | 16.0829 |
| H-soft_minus_electronic | H-soft | RMSE | -0.0124 | 0.0414 | 0.0968 |
| H-soft_minus_electronic | H-soft | EF_{V<=2}@20 | -21.1599 | 0.0000 | 17.3203 |
| H-soft_minus_geometry | H-soft | RMSE | 0.0697 | 0.1392 | 0.2108 |
| H-soft_minus_geometry | H-soft | EF_{V<=2}@20 | -32.8309 | -13.1906 | 4.5756 |
| H-soft_minus_xstats | H-soft | RMSE | -0.0182 | 0.0414 | 0.0992 |
| H-soft_minus_xstats | H-soft | EF_{V<=2}@20 | -13.9537 | 4.4315 | 21.4400 |

H-soft 相对 R-log 的 RMSE 差区间完全低于零，但 EF 差区间跨零。因此可报告数值误差改善证据，不能把筛选优势写成已稳定证实。

20 次重训 bootstrap 的池内最优与 Top-20 稳定性：

| pool | nominal_minimizer_frequency | distinct_minimizers | top20_overlap_mean |
| --- | --- | --- | --- |
| 04 | 0.2000 | 14 | 11.9500 |
| 07 | 0.2000 | 9 | 14.0500 |
| 08 | 0.1000 | 12 | 7.9500 |
| 11 | 0.3000 | 7 | 16.5500 |
| 12 | 0.2000 | 12 | 14.2000 |

04 的名义最小值候选仅在 4/20 个成员中仍为最小，20 个成员出现 14 个不同最小值候选。这反映候选最优身份不稳定，不是真实材料成功概率。

## 预算、复现与限制

- 树模型拟合尝试 **914** 次，其中失败尝试 **1** 次；硬上限 1000。失败记账，没有扩大模型菜单。
- 现有 Python/LightGBM 安装未升级；使用隔离的 3.3.5 Query 上限补丁，小规模结果逐值一致。
- 20 个 AB bootstrap 数值模型保留整表；校准器固定。输出的 sd/p05/p95 是条件模型分散度，不是保证覆盖的真实 V 区间。
- 公开文件哈希、冻结代码/划分/候选/名单哈希及完整拟合账本均保留。
- 04 共 3703 行，只有组成输入，未取得隐藏标签；不能报告真实 V=0 的命中、召回或显著性。
- 历史宿主知情风险仍存在；新冻结不恢复旧盲态。未逆推宿主、未载入外部同源材料标签。
- P2/P3 候选表全部明确标 `P1_train02`，后续 `P23_train02val03` 重训未执行。未求解 QUBO、未调用真机、未改正式论文。

## 交付索引

- 方案：`codex/P1_PLANv2.md`；代码与复现入口：`03_求解/D/p1_v2/README.md`。
- 主结果：`artifacts/p1_v21/results/P1_final_experiment_table.csv`、`03_development_results.csv`。
- 04 预测：`artifacts/p1_v21/predictions/04_P1_train02_predictions.csv`；相应 Top-20 为 `04_screen_top20.csv`。
- 完整证据：`experiment_freeze.json`、`splits.json`、`fit_ledger.jsonl`、`final_selection.json`、`prediction_freeze.json`、`results/manifest.json`。

上述近正例结果只能支持指定开发协议中的代理富集；不能直接推出隐藏零点发现、真实物理最优或可合成性。
