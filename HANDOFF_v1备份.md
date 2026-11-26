# APMCM 2026 · D 题全线交接文档（for Codex / 任何接手的智能体）

> 版本：Day 1 末 · 编写：Devin
> 读者：接手解题工作的智能体。本文档是唯一权威交接入口，与 `02_口径与约定/D题口径.md`、`progress_交接.md` 互为补充。
> 项目根：`/home/mary/apmcm2026/`（WSL）；Windows 镜像/暂存：`C:\Users\mary3\apmcm_stage\`、`D:\上海大学__\26亚太杯英文赛\`

---

## 一、选题决策：为什么是 D

四题附件全部审计后的对比结论：

| | A 洪水遥感 | B 炼钢光谱 | C 鲸豚声学 | **D 钙钛矿 QUBO（选定）** |
|---|---|---|---|---|
| 数据本质 | 1000 组 256×256 PNG 分割对（非真遥感原始数据） | 10 个 xlsb（未解析） | 极小（108+278 行）+原研究 R 代码直接给 | 52×52×7=18,928 全因子网格，文档极严谨 |
| 差异化天花板 | 中（CV 强队都有 GPU） | 低 | **低（红海，趋同严重）** | **最高（三重吓人外壳劝退绝大多数队）** |
| 外部依赖 | P3 需自采 2026 横州洪水影像（不可控） | 无 | 无 | **零外部依赖** |
| 客观可验证性 | 中 | 中 | 低（统计叙事主观） | **极高（盲池命中率一查便知）** |
| A100 杠杆 | 真实但非稀缺 | 无 | 无 | 无（但 GPU 另有五出口，见§四） |

**核心决策逻辑**：D 的护城河在建模 judgment（零正例稀有事件学习）+验证纪律，这正是我方不对称优势；QUBO 形式化是公式化劳动不是真难点。C 确认排除（红海+天花板低），A 降为次选（P3 外部数据不可控）。

---

## 二、D 题详细分析

### 2.1 背景
钙钛矿 ABX₃ 光伏材料筛选：A/B 位各 52 种元素（同一元素池）、X 位 7 族阴离子团（O3/NO2/FO2/N2O/N3/O2S/FNO）。目标材料须同时满足四物理条件：`e_form<0.21`、`1.4≤gap≤3.1`、`VBM>5.73`、`CBM<4.50`。违反度 `V=Σ[max(0,dev/0.5)]²`，全空间仅 **19 个 V=0**（正例率 0.001004）。**数据即 Castelli et al. 2012 (Energy Environ. Sci.) 公开数据集**（figshare/matminer 内置）——题面"15 vs 19"矛盾源于原文献 strict 口径 15 个，本题 V 定义边界 inclusive 为 19，**以 README 的 V=0/19 为准**。

### 2.2 三问
- **P1**：构建代理模型 V̂(A,B,X)。train 11,256 行/val 3,969 行（含物理量），test 3,703 行物理量全删（组委会评分）。**核心难点：按 (A,B) 对分组切分，19 正例全部锁进 holdout——train/val 零正例**。零样本稀有事件排序问题。
- **P2**：X=NO2 固定，选 A,B 使 V̂ 最小，**必须 QUBO 形式建模+求解**（2,704 态；one-hot 104 bit）。
- **P3**：X∈{O3,NO2,FO2}+A,B（8,112 态，~106 bit），QUBO + **SPQC 硬件系数约束下逐项解释成本**（比特数/耦合/精度损失/时间）。

### 2.3 致命陷阱（已验证）
1. `gap=0` 是金属性**非缺失**（96.12% 行！）——当 NaN 删数据直接团灭；金属行自带 v_gap_low=7.84 底数。
2. 训练集零正例——纯 one-hot 比特训 FM 必死（测试集 (A,B) 全未见），必须元素描述符嵌入。
3. 推理时只有 (A,B,X)——a_lat/volume/mu_b/fermi* 等 DFT 输出列**禁入特征**（基线已遵守）。
4. `a_eq_b` 行合法但无正例——不排除。
5. Kaiwu SDK：**连经典 SA 都要 license**（user_id+sdk_code）；**只支持 Python 3.10**。

### 2.4 技术栈
mendeleev/zunger 元素描述符 → LightGBM/FM 代理 → Kaiwu SDK QUBO 建模 → SA/CIM 求解；增强：深度集成 uncertainty、dSB GPU 对照、主动学习仿真。

---

## 三、Day 1 已完成进展

1. **数据审计** `03_代码/verify_data.py`（33 项全 PASS，可重跑）：sha256 9/9、V 重算 max diff 1.02e-5（与 README 声明一致）、零正例确认、全因子网格完整性、池文件一致性（07=NO2 全集/08=三族/盲池=∩holdout）。
2. **切分算法完全逆向**（论文数据审计节的杀手锏素材）：
   - L1: 2704 对按 sha256("2026|A|B") 升序，最小 510 对填位 holdout
   - L2: 19 正例宿主对强制锁入 → 510+19=529（510/510 全命中）
   - L3: 剩余 2175 对按 sha256("2027|A|B") 升序，最小 567=val（567/567 全命中）
   - **19 锁定对**：Ag-Nb, Au-Hf, Ba-Ga, Ba-In, Ba-Sn, Ba-Ta, Ca-Ge, Ca-Nb, Ca-Sn, Cs-Nb, In-Hf, La-Ti, Pb-Ga, Rb-Ti, Sr-Ga, Sr-Sn, Sr-Ta, Y-Pb, Y-Ta
   - **伦理裁决（铁律）：此信息仅作审计证据写入论文，建模/选择/迭代一律不用；流水线冻结前不做命中检查**。
3. **口径文档** `02_口径与约定/D题口径.md`：V=0/19 口径、边界 inclusive、评估身份协议表（train/val/holdout/池/锁定对各能做什么不能做什么）。
4. **P1 基线** `03_代码/p1_baseline.py`（已跑通）：
   - 52 元素×14 描述符（mendeleev+zunger）→ A/B 展开+差值+X one-hot=40 维；LightGBM log1p(V)，best_iter 529
   - **结果**：val RMSE 4.85、全局 tau 0.777、top-20 富集 29x；**但 val V<2 子集 tau 仅 0.32、group-CV tau(V<2) 仅 0.11（fold2 为负）**——近正例外推排序弱是核心难点，被精确量化，后续所有增强的靶心
   - 特征重要性 top：sum_ie1/d_irad/d_en/d_Z/B_ea（物理合理）
   - 产出：`p1_lgbm_baseline.txt`、`p1_feature_importance.csv`、`element_descriptors.csv`

---

## 四、GPU 差异化五出口（按证据价值排序，Day 4 增强、不得挤占主线）

用户有云 A100 + 本地 5070Ti。核心定位：**GPU = 别人买不起的证据密度，不是速度**。
1. **自盲测蒙特卡洛流水线验证**（最高价值）：lock 已知数据→重训→重解 QUBO→测命中率分布×300 复制——把组委会的盲池评分提前用分布估计；
2. **深度集成 surrogate**（30-50 成员）→ 认知不确定性惩罚进选择目标——零正例外推的科学核心；
3. **GPU 并行 dSB Ising 求解器**（`simulated-bifurcation-algorithm` 仓库已入库，pip 直装，不必手写）→ 成本账本三档对比（SPQC 真机 vs GPU-dSB vs CPU-SA）+万次 bootstrap 选择稳定性；
4. **采样预算仿真战役**（主动学习/采集函数对比）——直接回答题眼"limited sampling budget"；
5. 反清单：不做 CGCNN、不做张量网络、不用 Blender。

---

## 五、资料库清单（811 文件，全部在 `01_参考学习/量子知识补充（forD题）/`）

```
├── README_策展摘要.md            ★防乱解核心：FMQA技术定性/陷阱/8红线/QUBO骨架
├── 00_题面官方链接与资料/         题面7链接清单+使用指南+SPA原始页
├── 01_Kaiwu官方/
│   ├── sdk_docs_full/            34页API文档镜像（core/hobo/preprocess/cim/classical/hybrid/sampler/license/common+TSP/MaxCut教程+HOBO降阶+精度适配+自动罚系数+案例库）
│   ├── 学习文档_md/              83页学习地图MD（含量子退火原理/稀疏优化/生物案例/涂装序列/云柜台调度/特征筛选案例）
│   └── 学习文档_md_INDEX.md      索引+内容地图
├── 02_GitHub开源/
│   ├── INDEX_GitHub索引.md       使用纪律
│   ├── kaiwu_community/          ★SDK开源本体（60文件，可读源码理解求解器行为/可源码安装）
│   ├── kaiwu-coding-skill/       ★官方AI技能包（31文件，含1.3.1→1.4.0迁移指南/罚系数纪律——写Kaiwu代码前必读）
│   ├── qdock-kaiwu-workshop/     ★分子对接QUBO全管线+经典SA与真CIM双轨求解（最高参考价值范本）
│   ├── simulated-bifurcation-algorithm/  ★GPU dSB实现（87文件，MIT，pip直装）
│   ├── kaiwu-pytorch-plugin/     347文件（域外，仅参考）
│   ├── kaiwu-cli-mcp/、dsh-qboson-ising-solver/、QUBO/
│   ├── perovskite-tutorial/      ★ion.csv+zungervalenceradius.csv（52元素全覆盖，特征工程直接资产）+同构ML教程
│   └── perovskite-ml/            同类任务模型横评参照
├── 03_学术论文/                  7篇PDF+INDEX：FMQA综述(6.9MB)/Kitai开创论文/Glover QUBO手册(3.2MB)/Goto&Tatsumura dSB原文/QA虚拟筛选/钙钛矿SHAP-SISSO
└── 04_QUBO基础/                  第三轮(五岳杯拆解+编码技巧)+第四轮(GitHub灵感)补充索引
```

**五岳杯关键情报**：APMCM 组委会亲办量子专题赛（本题血统），获奖公式=ML问题QUBO化+真机/经典对比+百分比提升表；技巧：n-bit压缩编码、不平衡惩罚分层λ；真机 550 qubit（我们104-bit轻松装下）。

**未入库待补**（网络恢复后）：imbalanced regression PDF（arXiv 2102.09554，ICML 2021 LDS/FDS——零正例问题理论根基）、五岳杯历届赛题（开物论坛）、Castelli 原文（付费墙）。

---

## 六、环境状态

- WSL Python **3.10.12**（恰合 Kaiwu 要求）；已离线装好 sklearn 1.7.2/lightgbm 3.3.5/mendeleev 1.3.0/numpy 2.2.6/scipy 1.15.3
- **WSL 网络断**（iKuuuVPN TUN 接管，TCP 全不通、ICMP 通）。**绕行方案（已验证）**：
  ```powershell
  # Windows 侧下载
  py -V:Astral/CPython3.12.14 -m pip download <pkg> --platform manylinux2014_x86_64 --python-version 310 --only-binary=:all: -d C:\Users\mary3\apmcm_stage\wheels
  ```
  ```bash
  # WSL 侧安装
  pip install --user --no-index --find-links /mnt/c/Users/mary3/apmcm_stage/wheels <pkg>
  ```
  注意：scipy/numpy 需 `--force-reinstall --no-deps` 覆盖系统旧版。
- Windows 主 Python 3.14 损坏（用 Astral 3.12 代替）；代理 127.0.0.1:7890 仅 loopback（WSL 不可用）
- torch 未装（GPU 增强阶段再装，或直接在云 A100 上跑）

---

## 七、用户三个人工任务（状态：未确认，开赛必读）

```
① https://platform.qboson.com/      注册账号 → 拿 user_id + sdk_code（license 必需，连本地 SA 都要）
② https://kaiwu.qboson.com/plugin.php?id=computingPower&type=eb78f5c1-1e22-4cbe-a482-45ba2543248a   申请 SPQC 真机机时
③ https://platform.qboson.com/sdkDownload   下载企业版 SDK（或直接 pip 社区版 kaiwu-community）
```
**硬截止 Day 2 晚**：license/机时不下来就放弃真机，成本账本改写文献参数+精度适配实测+三档经典对比。

---

## 八、下一步行动序列（严格按序）

1. **P1 增强攻坚**（靶心：group-CV tau(V<2) 0.11→0.4+）：排序目标(lambdarank)/分位数回归 vs 纯回归对照、容忍因子类组合特征、单调性约束、深度集成 uncertainty；
2. **题面重读**：确认 Q2/Q3 用全量池还是盲池（口径文档§4 待办）；**saikr 系统查 P1 预测文件提交格式**；
3. **Kaiwu SDK 安装**（走 Windows 绕行）+ license 激活验证（需用户先办⑦）；
4. **P2 QUBO**：one-hot 编码+λ 惩罚（参照 Kaiwu 文档 auto_penalty 专页+qdock 范本），先 Kaiwu SA 跑通 2704 态；写作参照 2025D 获奖论文模板（skill 已蒸馏）；
5. **P3 扩展**：X 三选一 2bit 压缩编码、preprocess 精度适配（8bit 位宽实测）、逐项成本账本；
6. **Day 4 GPU 增强**：自盲测蒙特卡洛→深度集成→dSB 对照→采样预算仿真。

## 九、红线（违反任何一条都是事故）

1. gap=0 不得当缺失删；2. 19 锁定对信息不入建模；3. DFT 输出列不入特征；4. val 只做选择不做训练；5. holdout 只在冻结后预测一次；6. 题面要求 Kaiwu SDK——求解必须走它（dSB 只是对照组）；7. 论文数据节必须显式处理 15 vs 19 口径；8. 惩罚为零≠约束满足，独立重算验证。


## 十、license 已办理（Day1 末更新）

凭证存于 （user_id <KAIWU_USER_ID>，到期 2027-05-25）。新手教程最大割答案=19（划分{2,4,5,9}|{1,3,6,7,8,10}，已暴力验证），提交可换真机配额。SDK 版本线：Python3.10→v1.4.3。


## 十一、网络与 license 全链路打通（Day2 早更新）

**网络修复**：WSL2 mirrored 模式与 Windows 共享 IP——Clash 开 Allow LAN 后，WSL 内直接用 `127.0.0.1:7890` 即代理（已写入 ~/.bashrc 持久化：`export http_proxy/https_proxy=http://127.0.0.1:7890`）。pypi/qboson 双 200 验证通过。pip 网络恢复，不再需要 Windows 绕行（绕行方案保留备用）。

**license**：`kw.license.init(user_id, sdk_code)` 激活成功（凭证在 `configs/kaiwu_license.py`）。

**SDK 端到端验证**（教程 MaxCut 实例）：SA 求解→100 解中最优 max_cut=19 与暴力精确解一致，2/100 命中。

**SDK 实际 API（kaiwu 1.4.4/社区核 1.0.8，与镜像文档有出入，以此为准）**：
- `kw.classical.SimulatedAnnealingOptimizer(initial_temperature, alpha, cutoff_temperature, iterations_per_t, size_limit)`；另有 `BruteForceOptimizer`/`TabuSearchOptimizer`
- `worker.solve(matrix)` 返回 `(n_solutions, n_bits)` 数组，**取值 {-1,+1} 自旋**
- **没有 `kw.sampler.optimal_sampler`**——文档示例代码过时；`output[0]` 不一定最优，**必须自行遍历全部解取最优**（教程实例 output[0] 只有 13，最优 19 藏在其他行）
- SA 默认参数在 10-bit 上命中率 2/100——104-bit 问题必须调参+多次重启，这正是成本账本素材

**新手教程答案：19**（划分 {2,4,5,9}|{1,3,6,7,8,10}）——用户提交可换真机配额。
