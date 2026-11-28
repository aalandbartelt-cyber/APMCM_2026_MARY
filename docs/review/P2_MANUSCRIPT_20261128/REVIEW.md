# P2 撰稿审阅记录 · 2026-11-28

官方入口为项目内 2026 年模板的 `main.tex`；同目录 `main.pdf` 为本轮审稿本。只读既有冻结代理、证书、终态回包与 14 张验收图。新产物为 P2 文字、短求解流程图、引用、工作备份与审稿记录。真机提交、拟合及新 SA 重启均为零。

## 阅读入口和布局

| PDF 物理页 | 已核对的内容 |
|---|---|
| 1 | 官方 Summary Sheet 与队号；摘要留待整合。 |
| 2 | 单页 Contents。正文的章、节和 A/B/C 三个附录入口共 31 项，62 个标题/页码链接。 |
| 3–11 | Introduction 从物理第 3 页起。第 3 页列齐三问重述，P2 分析为连续短段。第 4 页列两条 P2 假设及 P2 的查表、编码和能量符号。 |
| 12–13 | P2 从第 12 页开始。候选池、精确枚举、两个次优及各自的差距；景观和晶体图就近出现。 |
| 14–15 | 模型建立；原始/重参数化反例、塑形和链 QUBO。第 15 页的模型求解小节同页含两个实际 Kaiwu 求解器和三节点图。 |
| 16–17 | 验证：全局合法与最优、196 严格界和等号反例；残差图与唯一服务结果表在邻页。 |
| 18 | Kaiwu 服务综合图和 Direct answer，同页给出选择、两个池的名义最小值、SA 固定块和正式云端任务结果。 |
| 19–29 | 参考文献（9 条），附录 A 框架、既有 P1 附录 B；P3、模型评价、总结留白。 |
| 30–35 | B.7–B.10 覆盖九张补充图；物理第 35 页接附录 C 空框架。正文均有指引。 |

## 可核查的更改

- 官方类、配置、P1 正文及附录源文件、既有表格未改。用官方主稿接入两份新章节。纸面目录隐藏正文三级与附录内部条目；全部 50 个书签保留。若以后目录挤占物理第 3 页，主稿编译报告错误。
- 一页目录、所有编号链接、英文、PDF 元数据、图文相邻、原始板图哈希和入版字号纳入 `check_layout.py`。本次 154 个内部链接可跳转。15 个图题的完整文字均出现在单一印刷行。流程图字号约 9 pt，原有图件以官方版心排入，14 张中最小字在 7.32–8.19 pt；13 张低于 8 pt 目标，全部高于项目 7 pt 下限。正文与附录全部 25 张图均只在图下保留短图题。图 6、7 的另排补充说明已删除，晶体的 Materials Project 引用仍在引图段落。
- 复用 P1 三节点图的几何和配色，新图输出在 `figures/P2/solver_workflow/`。三个节点依次为枚举基准、Kaiwu 本地/云端求解、合法性与 regret 校核。原有图件的完整档案说明仍见 `figures/P2/captions/captions.json`。
- `before/` 和 `before.sha256` 为动笔前的 19 件备份。`before_readability_revision/` 单独保留初版 P2 审稿本；本次共享章节修订前的稿件另存于 `before_shared_sections_revision/`。当前稿以官方目录下的 PDF 为准。`source_changes.diff` 为从 P1 官方入口到本轮五个源文件的统一补丁。图件另有源稿。
- 官方字体、标题、caption、页眉未调；页眉分母沿用户指定固定为 25，附录沿官方连续编号。此 PDF 是分阶段草稿。

## 数字和文献来源

| 数字或口径 | 已核对来源 |
|---|---|
| 2,704/529、均值最小值及两个 runner-up | `artifacts/p2_v2/enumeration_07.csv`、`enumeration_11.csv` |
| 浮点跨寄存器权重与参考峰值，取整后只剩两值 | `artifacts/p2_v2/representations/11-{raw,rc}-{float,N8}.npz` |
| 非法见证及允许整数最优的最坏原 regret | 同目录两份 N8 certificate.json、representation_summary.csv（在 results/ 下） |
| 490 自旋、40 组、基态 −58722、340/196、等号反例 | `evidence/p2/matrix.npz`、`blocks.json`、`candidates.csv` 与独立 `verify.py` |
| 5 个先导、20 个正式，每任务 10 个筛选返回 | `codex/P2_CIM_FINAL_RESULTS_20261128.md`、终态逐任务表与 `evidence/p2/returns/` |
| 选解 84–176、全部正式向量 84–188，F03/F14 裕度 20/8 | `figures/P2/data/task_margin.csv`、`return_energy.csv` |
| 本地求解器、温度与服务模式 | `03_求解/D/p2_research/validation_batch.py`、历史 SA settings.json；`03_求解/D/p2_cim_go/service_entry.py`、Kaiwu SDK 1.4.4 汇编印刷 p.46 |
| 风险情景、五重启配对检验、链长消融 | `artifacts/p2_v2/uncertainty_{07,11}.csv`、`figures/P2/data/sa_paired_test.json`、`chain_ablation.csv` |
| P2 新增引文 | Kasahara 2002 (10.1021/jp025961+)，Materials Project mp-1222738 (10.17188/1745405)，Chancellor 2019 (10.1088/2058-9565/ab33c2)，Kaiwu SDK 1.4.4 与 QBoson service guide，Wei 2026 (10.1038/s41377-025-02178-1)。访问日期为 2026-11-28。 |

## 入版逐图记录

物理页按 PDF 阅读器计数；“引出页”是主体或附录的就近段落。所有附录图另有 P2 正文指引。字号从验收原件最小字号和实际 PDF 嵌入比例计算；新图直接读回 PDF 的字形大小。

| 图号 | 资产 | 引出页 | 图页 | 最小 pt | 论文短图题 |
|---|---|---:|---:|---:|---|
| 5 | P2-F1 | 12 | 13 | 7.32 | Predicted violation in the full and blind pools |
| 6 | P2-A1 | 13 | 13 | 7.32 | Three views of the LaTiO2N coordination network |
| 7 | P2-F2 | 15 | 15 | 7.41 | Couplings in the lookup and short-chain models |
| 8 | P2-workflow | 15 | 15 | 9.00 | Enumeration, Kaiwu optimization and verification |
| 9 | P2-F3 | 16 | 17 | 7.32 | Residual margins for pilot and formal tasks |
| 10 | P2-F5 | 17 | 18 | 7.32 | Kaiwu optimization returns by chain and task |
| B.7 | P2-A2 | 30 | 31 | 8.19 | Couplings within and between the two registers |
| B.8 | P2-A7 | 30 | 31 | 7.32 | Precision and legality of the lookup encoding |
| B.10 | P2-A4 | 32 | 32 | 7.63 | Task-level hits under two selection rules |
| B.9 | P2-A3 | 31 | 32 | 7.88 | Integer energies of the returned solutions |
| B.11 | P2-A5 | 32 | 33 | 7.59 | Observed task intervals on the Kaiwu service |
| B.12 | P2-A6 | 32 | 33 | 7.50 | Classical costs and three measures of error |
| B.13 | P2-A8 | 33 | 34 | 7.59 | Candidate rankings under alternative risk criteria |
| B.14 | P2-F4 | 34 | 34 | 7.41 | Strict hits by local restart budget |
| B.15 | P2-A12 | 35 | 35 | 7.41 | Single-chain and grouped encodings under local annealing |

当前 PDF 的 SHA-256 为 `7e56aa9c7190b70cdd367e07fc9333d65670b0bacfb218217975e304bb29b5e5`。XeLaTeX 多遍引用稳定，日志无警告、缺字、溢出。离线证据包验证通过。审阅页按全册渲染检查，并放大复核了目录、求解器图、证明和直接答复。
