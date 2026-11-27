# P1 稿件来源映射

本文件是内部来源记录，不进入论文正文。以下结果路径以 `artifacts/p1_v21/` 为根；只读取既有产物。表格的精确单元格见 `table_source_map.json`。

## 正文与附录证据

| 稿件位置 | 来源 | 使用口径 |
|---|---|---|
| 数据角色、样本构成、特征数量 | `model_card.json`、`feature_schema.json`、`final_audit.json`；`codex/P1_RESULTS_v2.1.md` | 02 拟合 11,256；03 开发 3,969；04 未知标签 3,703；非金属 432；训练近正例 128；336 维 |
| 目标、条件回归、概率链、求解器 | `03_求解/D/p1_v2/models.py`、`features.py`、`metrics.py`、`experiment.py`（静态阅读） | 五项正部平方；0.5 eV 归一化；LightGBM 3.3.5；标量校准 L-BFGS-B；不导入拟合模块 |
| Table 3、B.3、B.4；主结果 | `results/P1_final_experiment_table.csv` | 候选路线与嵌套程序分别列示；RMSE 合并残差；EF 为外折宏平均；Top-20/折总预算 100 |
| Table 4、开发选择 | `results/03_development_results.csv` | H-soft RMSE 4.5783；两候选均 13/20；EF 62.9232；NDCG 打破并列；仍属开发证据 |
| 双目标配对结论、Table B.11 | `results/paired_AB_bootstrap_5000.csv` | 5,000 次外折内配对 A–B 重采样；EF 宏平均；固定已拟合预测的条件区间，不用旧 pooled 版本 |
| 残差族结构 | `results/OOF_residual_scales_by_X.csv` | N3 RMSE 6.6515、绝对误差 q95 13.8694；族均值偏差不等于个体误差小 |
| Table B.5 与概率诊断 | `results/oof_calibration_consistency.csv`、`oof_calibration_ranking_checks.csv` | pooled 斜率/截距为评价诊断；折内与拼接排序分开；S-eps 乘积不因组件校准自动充分校准 |
| Table B.6 | `results/query_seed_stability.csv` | 相同外折、多查询哈希种子；相对主分配的 Top-20 重叠 |
| Table B.7、四池名义候选 | `hardening/decision_stability_summary.csv`、`decision_stability_members.csv` | 20 张既有成员表；排名范围和双向预测 regret；不能称真实材料 regret |
| Table B.8 | `hardening/split_half_summary.csv` | 同一批 20 模型的 1,000 次 10/10 划分；不是 1,000 次独立拟合 |
| Table B.9、压力测试 | `results/stress_summary.csv` | R-log/S-eps 协议证据；不是最终 H-soft 域外验证；X 族 35 次中 29 次 EF 有定义 |
| Table B.10、特征阶梯与反向消融 | `results/diagnostic_summary.csv`、`P1_final_experiment_table.csv` | 阶梯固定 R-log；反向消融固定 H-soft；各块含派生量及缺失标记 |
| 04 与优化接口的局限 | `results/bootstrap_pool_stability.csv`、`bootstrap/manifest.json`、`interface/manifest.json`；`codex/P1_HARDENING_REPORT.md` | 04 名义首位仅 4/20 稳定；当前表为 P1_train02；02+03 重训留待后续 |

开发集超几何尾概率独立复核：`hypergeom.sf(12, 3969, 41, 20)`；两比较 Holm 值为该值的 2 倍。该检验比较均匀抽样，并非与所有可能学习算法比较。已知训练数据无 V=0 正例，不把 V≤2 富集改写为零违约发现。

## 图件入版映射

| 稿件编号 | 原图（项目根目录相对路径） | 原数据 |
|---|---|---|
| Figure 1 | `figures/F1/F1_data_audit_v3.pdf` | 既有训练审计、分组划分 |
| Figure 2 | `figures/F4/F4_model_workflow_v2.pdf` | `03_求解/D/p1_v2/models.py`、`experiment.py`，既有求解流程静态摘要 |
| Figure 3 | `figures/F2/F2_enrichment_v3.pdf` | `results/all_domain_metrics.csv` |
| Figure 4 | `figures/F3/F3_error_tradeoff_v2.pdf` | `results/P1_final_experiment_table.csv`、`results/regression_pareto.csv` |
| Figure B.1 | `figures/A1/A1_residual_structure_v3.pdf` | `results/OOF_residual_scales_by_X.csv` |
| Figure B.2 | `figures/A2/A2_calibration_v2.pdf` | `results/oof_calibration_*` |
| Figure B.3 | `figures/A3/A3_decision_stability_v2.pdf` | `hardening/decision_stability_*.csv` |
| Figure B.4 | `figures/A4/A4_split_half_v2.pdf` | `hardening/split_half_summary.csv` |
| Figure B.5 | `figures/A5/A5_stress_protocols_v4.pdf` | `results/stress_summary.csv` |
| Figure B.6 | `figures/A6/A6_ablation_v2.pdf` | `results/paired_AB_bootstrap_5000.csv` |

9 份原图全部按文件引用，未修改或重绘。新增 Figure 2 为用户要求的紧凑流程图 v2：137.6 × 30 mm、三个节点、Times New Roman 最小 8.5 pt；首版大面积嵌套流程图已停用，不进入论文。A5 取最后指定版本 v4；旧审图状态不因本轮排版而擅自重写。现有图按用户明确选择保留整图缩入官方 146.4 mm 版心，个别最小文字约 7.3–8 pt；A5 为 0.92 倍版心。此例外不降低后续新图标准。

## 文献核验入口

1. Castelli et al. (2012), *New cubic perovskites for one- and two-photon water splitting using the computational materials repository*, Energy & Environmental Science 5, 9034–9043. [RSC 原刊页面](https://pubs.rsc.org/en/content/articlehtml/2012/ee/c2ee22341d)，DOI 10.1039/C2EE22341D。原刊页面有访问限制，标题/作者/卷页以可检索原刊元信息核验。
2. Ward et al. (2016), *A general-purpose machine learning framework for predicting properties of inorganic materials*, npj Computational Materials 2, 16028. [原刊页面](https://www.nature.com/articles/npjcompumats201628)，DOI 10.1038/npjcompumats.2016.28。
3. Bartel et al. (2019), *New tolerance factor to predict the stability of perovskite oxides and halides*, Science Advances 5(2), eaav0693. [作者提供的原文 PDF](https://cjbartel.github.io/assets/files/papers/bartel.scheffler_2019-ScienceAdvances.pdf)，DOI 10.1126/sciadv.aav0693。
4. Ke et al. (2017), *LightGBM: A Highly Efficient Gradient Boosting Decision Tree*, Advances in Neural Information Processing Systems 30, 3146–3154. [会议官方页面](https://proceedings.neurips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html)。

以上均已在对应正文处引用。期刊用 [J]、会议论文用 [C]；内部核验链接不另作论文网络资源条目。AI 工具条目依用户阶段要求留待全文整合。
