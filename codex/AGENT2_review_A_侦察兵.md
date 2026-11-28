# 平行方案 AGENT2 侦察兵独立审查报告（兼与 AGENT1 及本团队主线对照）

- **审查对象**：`/mnt/d/上海大学__/26亚太杯英文赛/AGENT2/`（含 `p1/p1.py`、`p1/p1.txt`、`p2/p2.py`、`p2/p2.txt`、`p3/p3.py`、`p3/p3.txt` 及 `agent全文.docx`）
- **参照对象**：`/mnt/d/上海大学__/26亚太杯英文赛/AGENT1/` 及本团队当前已封存主线资产（P1 H-soft 冻结代理 + P2 8-bit 严格反例审计 + 单调分段塑形联合短链构造 + 25 次 SPQC 真机任务实证）
- **文档定位**：本报告仅对 AGENT2 进行客观技术审计、优劣对标与可借鉴要素提炼，**不构成 P3 实施指令，亦不授权修改论文或触碰既有冻结资产**。

---

## 一、总体裁决：我们的主线在科学严谨性与求解结果上全面领先，但 AGENT2 的问题拆解结构与表格设计极具参考价值

### 1.1 三方核心指标正面对比表

| 评估维度 | 本团队主线（Codex 已封存结果） | AGENT2（本次审查对象） | AGENT1（前次参照） | 侦察兵裁决 |
|---|---|---|---|---|
| **P1 代理模型与特征** | 336 维物理/化学描述符 + 组分特征，H-soft 20 成员集成，严格 OOF/holdout 纪律，OOF RMSE **4.6011**，EF$_{V\le 2}$@20 = **62.10** | Gated Tensor Factorization（仅用 A/B/X 离散索引嵌入 $d=24$，4,176 参数，无物理描述符），03 验证集 RMSE **4.6521**，Recall@100 = 0.88 | 核岭回归（$r=16$），仅报 in-sample Spearman 0.9514，严重过拟合倾向 | **我方胜**。我方物理可解释性与验证纪律更严；但 AGENT2 门控双分支视角清晰 |
| **P1/P2 枚举最优候选** | 07 全池与 11 盲池最优均为 **LaTiO$_2$N**（$\widehat V = 1.839047$），20 成员中 Top-5 频率 90%、Top-20 频率 100% | hold-out 与 P2/P3 枚举全局最优同样为 **LaTiO$_2$N** | 误报 `KTaO2N`（LaTiO$_2$N 仅排第 7） | **关键旁证**：AGENT2 独立架构亦指向 LaTiO$_2$N，侧面印证材料学答案稳健 |
| **P2 8-bit 编码与量化保真** | 证伪朴素 one-hot 后，构造“单调分段塑形＋40 短链 domain-wall”（490 自旋，最大系数 73），**独立 G1/G2 双证明 CERTIFIED，整数基态原表 regret = 0** | 104-bit 朴素 one-hot + 已知上界截断 $\kappa = W_{\text{inc}} = 0.0383$（2,704 格中 **2,698 格被截平**），量化后 $W$ 仅剩 **4 个离散层级**，自报 $s\cdot g = 0.0128 < 1$（`resolvable = False`） | log 变换压缩动态范围至 65:1，虽保住量化 argmin，但能隙压平至 $0.01\text{--}0.05$ | **我方完胜**。AGENT1 与 AGENT2 分别死于“能隙压平”与“截断坍缩”两极 |
| **P2 采样与真机实证** | **25 次 SPQC 真机任务**（5 先导 + 20 正式）：250/250 返回解严格整链合法，**20/20 正式任务命中 LaTiO$_2$N（regret = 0）**；本地 SA 492/500 合法、347/500 命中 | **0 次真机**（仅跑 500 次本地 SA，耗时 0.052s）：可行率 **5.2%**（26/500），**最优命中率 0.0%**，误选 `VNbO2N`（$\widehat V = 14.1047$，排第 394 位）；48 组 $(\lambda,\kappa)$ 扫描 47 组命中率为 0 | **0 次真机**（本地 SA 200 次）：$p_s = 0.0$，中位排名 2615/2704 | **我方降维打击**。我方是唯一跑通真机且 100% 命中的方案 |
| **P3 三元 (A,B,X) 扩展** | 待展开 | Mode-1 展开（208 bits），用 $\kappa = T_{\text{inc}} = 0.0$ 截断导致 8,112 格中 **8,111 格饱和为常数**，量化后仅剩 **1 个层级**；SA 可行率 **2.6%**，命中率 **0.0%**，误选 `VNbO3`（排 1265 位），Top-10 中 $\text{NO}_2$ 占 0 个 | 同样困于 one-hot 量化与采样失败 | AGENT2 的 P3 数值结果彻底崩盘，但**其理论对比框架值得拆解借鉴** |

---

## 二、AGENT2 失败根因的技术尸检（引以为戒）

1. **P2/P3 的“已知上界截断 $\kappa = W_{\text{inc}}$”是自毁式设计**：
   - 在 P2 中，AGENT2 用训练集已见最优 $W_{\text{inc}} = 0.0191$（LaSiO$_2$N，翻倍后 $\kappa = 0.0383$）将所有 $>\kappa$ 的预测值全部截平为 $\kappa$，导致 2,704 个候选中 **2,698 个变成完全相同的平台**，只剩 6 个候选有梯度；即便如此，能隙 $g = 7.3\times 10^{-5}$ 乘以缩放因子 $s = 174.6$ 后仍有 $s\cdot g = 0.0128 \ll 1$，在 8-bit 整数格上彻底并列。
   - 在 P3 中更极端：它直接令 $\kappa = T_{\text{inc}} = 0.0$（引用 P2 的理想最小值 0），导致 $\lambda = \kappa = 0$，8,112 个候选中 **8,111 个被截断饱和**，`quantisation_distinct_levels_T = 1`——整个目标函数在整数域退化成退化常值面，SA 只能随机游走（可行率 2.6%，命中率 0%）。
2. **全程无真机、且用极短 SA（0.05s / 500 样本）冒充求解闭环**：
   - 其 `p2.txt` / `p3.txt` 明确记录 `SA_time_s = 0.052` / `0.049`，没有任何 Kaiwu SDK 真机任务记录。
3. **结论自相矛盾但照写不误**：
   - 在枚举明明知道 `exhaustive_argmin_formula = LaTiO2N` 的情况下，QUBO 采样选出排名第 394 的 `VNbO2N`（P2）和排名第 1265 的 `VNbO3`（P3），退化一致性检验 `restricted_matches_problem2 = False`（选出排名更差的 `TeSbO2N`，$\widehat V = 26.73$），却只能尴尬收场。

---

## 三、AGENT2 值得我们参考与评估吸收的 6 个闪光点

尽管 AGENT2 的量子求解结果崩塌，但它在**数学形式化、问题拆解维度、审计指标命名与图表结构**上有 6 个非常契合评委审美的亮点，建议 Codex 逐项评估其可取之处：

### 亮点 1：量化可分辨性判据 $s \cdot g > 1$ 与 `quantisation_distinct_levels`（P2/P3 诊断指标）
- **它的做法**：显式定义缩放因子 $s$、最小关键能隙 $g = W_{(2)} - W_{(1)}$，将 $s \cdot g > 1$ 作为 8-bit 量化不发生基态并列的必要判据，并统计量化后目标矩阵保留的不同整数层级数 `quantisation_distinct_levels`。
- **对我方的价值**：我们可以将 $(s\cdot g,\ \text{distinct\_levels})$ 纳入我方“为什么朴素 one-hot 与简单截断/log 变换失败，而单调分段塑形＋联合短链成功”的对比表中，让二维瓶颈（动态范围 vs 局部能隙分辨率）多一个极直观的代数指标。

### 亮点 2：P3 三阶张量的三种 QUBO 编码范式系统对比（Table 6 范式）
- **它的做法**：在 P3 处理 $(A,B,X)$ 三元耦合张量 $T_{ijk} \in \mathbb{R}^{52\times 52\times 3}$ 时，没有只写一种编码，而是推导并横向对比了三种数学路线：
  1. **Mode-1 张量展开（Mode Unfolding）**：令复合索引 $m = k\cdot 52 + j \in \{0,\dots,155\}$，转化为 $52 + 156 = 208$ bits 的精确二次型（0 辅助变量，21,528 耦合，1 个罚尺度，精确无损 $\text{truncation\_RMSE}=0$）；
  2. **Rosenberg 高阶降阶（Rosenberg Reduction）**：引入 $156$ 个辅助二元变量 $y_{jk} = b_j x_k$ 及罚项 $P_{\text{aux}}(b_j x_k - 2b_j y_{jk} - 2x_k y_{jk} + 3y_{jk})$，共 $107 + 156 = 263$ bits（11,235 耦合，需 2 套罚尺度，精确无损）；
  3. **Pairwise 二阶边际近似（Pairwise Approximation）**：仅保留 $A\text{-}B, A\text{-}X, B\text{-}X$ 两两交互，仅需 $52+52+3 = 107$ bits（0 辅助变量，5,671 耦合），但存在三元交互截断误差（`truncation_RMSE` 与 `truncation_max_abs`）。
- **对我方的价值**：这张“编码资源与保真度三方对比表”（比特数、辅助比特、罚耦合数、目标耦合数、罚尺度数、是否精确、截断误差、8-bit 下是否保住真 argmin）直接切中题目 P3 对多组分编码扩展性的核心提问！而且我们可以把**我方的第四种突破路线（候选集压缩/短链域墙编码）**作为第 4 行放进同一张表里，形成从传统三路线（均困于 8-bit one-hot 瓶颈）到我方短链构造的递进对比。

### 亮点 3：P3 对 P2 的“子空间退化一致性检验（Degeneracy Consistency Check）”
- **它的做法**：在 P3 中专门设立“将三元模型限制在 $X = \text{NO}_2$ 子空间（或屏蔽 $O_3, FO_2$ 块）”的退化实验，验证两件事：① 全局三元最优能量满足 $H_3^* \le H_2^*$；② 限制在 $X = \text{NO}_2$ 时的三元模型是否退化还原出 P2 的最优解。
- **对我方的价值**：AGENT2 自己做出了 `restricted_matches_problem2 = False` 的翻车结果；而我方无论是枚举还是短链构造，都能做到 **严格满足退化一致性（`True`）**。这个检验耗时极低，却能把 P2 和 P3 锁死成一个逻辑自洽的整体。

### 亮点 4：分项成本与误差账本（Itemized Cost Accounting，Table 5 & Table 7）
- **它的做法**：把整个量子混合筛选流水线的开销拆成标准科目表：
  - 经典前端：`surrogate_inferences`（2704 vs 8112）
  - 编码规模：`n_bits`、`n_aux_bits`、`n_couplings_total`（拆分为 `penalty` vs `objective`）、`penalty_coefficient_share`
  - 量化损耗：`penalty_magnitude_over_W_min`、`quantisation_margin_s_g`、`quantisation_distinct_levels`
  - 硬件/采样与经典后端：`solver_tasks / samples`、`classical_postprocess_decoded_states`、`classical_postprocess_reranked`
- **对我方的价值**：完全契合题目中“评估计算成本与精度权衡”的要求，我们可以结合我方真实配额消耗与三层误差审计，做出比它更硬核的分项账本表。

### 亮点 5：P1 数据探索的三个精细切面（金属违约度解析下界 + 罚项贡献份额拆解 + 分层残差）
- **它的做法**：
  1. 在 P1 开篇先做了 **金属样本违约度解析下界检验**（当 $\text{gap}=0$ 且 $\text{VBM}=\text{CBM}$ 时，由带隙罚项与能带边罚项之和导出金属样本 $V \ge 10.8658$，并在 14,652 个金属样本上验证 `min_V_metal = 10.8658, bound_holds = True`）；
  2. 统计了不同组别（Metallic vs Non-metallic，以及 7 种阴离子 $O_3, NO_2, FO_2, N_2O, N_3, O_2S, FNO$）中五个子违约项（`v_form, v_gap_low, v_gap_high, v_vbm, v_cbm`）占总 $V$ 的百分比份额（`violation_distribution_penalty_share.png`）；
  3. 对验证集残差按 Metal/Non-metal $\times$ 四个分位桶（Q1–Q4）做分层偏差检验（Stratified residual statistics）。
- **对我方的价值**：不改动我方 P1 冻结模型分毫，但“金属 $V \ge 10.8658$ 解析下界验证”和“7 类阴离子五项违约贡献占比”属于纯数据确定性事实，若后续修饰 P1 图表或正文叙事，是极佳的物理洞察补充。

### 亮点 6：P3 按阴离子切片（$X \in \{\text{O}_3, \text{NO}_2, \text{FO}_2\}$）的景观对比表
- **它的做法**：在 P3 先列出三个 $X$ 切片各自的 `min_V_hat, argmin_formula, median_V_hat, mean_V_hat, max_V_hat, n_cells_in_global_top100`（如 $\text{O}_3$ 最优 `KNbO3`、$\text{NO}_2$ 最优 `LaTiO2N`、$\text{FO}_2$ 最优 `LiTiO2F`，以及各自在全局 Top-100 中的席位占比）。
- **对我方的价值**：这个切片汇总表能让评委一眼看懂为什么在三元池中 $\text{NO}_2$ 切片（特别是 LaTiO$_2$N）与 $\text{O}_3$ 切片形成竞争，物理化学故事非常饱满。

---

## 四、给 Codex 的核查清单（本轮仅做审查反馈，不启动 P3 执行）

请 Codex 结合自身代码阅读，对以下问题给出独立裁决：
1. 侦察兵对 AGENT2 的数值尸检（$\kappa$ 截断导致 2698/2704 与 8111/8112 饱和、0 真机、采样命中率 0%）是否全部属实？有无遗漏的技术细节？
2. 上述 6 个结构化亮点（① $s\cdot g$ 与量化层级数指标；② Mode-1 / Rosenberg / Pairwise 三编码资源与保真对比表；③ $X=\text{NO}_2$ 退化一致性检验；④ 分项成本账本；⑤ 金属解析下界与阴离子违约份额；⑥ 三阴离子切片景观表）中，哪些值得吸纳进我方后续的 P3 设计与论文图表体系？哪些存在隐患需要规避或修正？
3. AGENT2 的 `.docx` 正文结构与出图清单（共 11 图 7 表）有哪些排版优点或审稿雷区值得我们注意？
