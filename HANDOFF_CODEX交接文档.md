# APMCM 2026 · D 题全线交接文档 v2（for Codex · 主力复核版）

> 版本：v2.0 · Day 2 · 编写：Devin（侦察兵角色）
> **协作模式**：Devin 负责探路、排雷、搭脚手架、写验证基建；**Codex 是解题主力**，需逐项复核本文档及所有代码，可推翻可重写。所有脚本设计为一键重跑、自带验证。
> 项目根：`/home/mary/apmcm2026/`（WSL）；Windows 镜像：`D:\上海大学__\26亚太杯英文赛\`；暂存：`C:\Users\mary3\apmcm_stage\`

---

## 第一部分 · 环境与工具链（全部已验证，不要重装）

### 1.1 WSL Python 环境
- Python **3.10.12**（Kaiwu SDK 只支持 3.10.x——恰好命中，勿升级）
- 已装包（`~/.local/lib/python3.10/site-packages/`）：numpy 2.2.6 / scipy 1.15.3 / sklearn 1.7.2 / lightgbm 3.3.5 / mendeleev 1.3.0 / **kaiwu 1.4.4 + kaiwu_community 1.0.8** / matplotlib 3.10.3 / pandas 2.3.3
- 注意：scipy/numpy 必须用用户目录新版——系统 `/usr/lib/python3/dist-packages` 有旧 scipy 会抢占路径（已用 `--force-reinstall` 解决，若新环境复现此问题参照此法）

### 1.2 网络（已修复，勿再折腾）
- WSL2 是 **mirrored 网络模式**，与 Windows 共享 IP
- 用户已开启 Clash **Allow LAN**；WSL 内代理地址就是 `127.0.0.1:7890`（不是 Windows LAN IP——192.168.3.6 在 mirrored 模式下指向 WSL 自己！这个坑耗了一小时）
- 已持久化到 `~/.bashrc`：`export http_proxy=https_proxy=http://127.0.0.1:7890`
- pypi/qboson/github 全部 200 验证通过
- 备用绕行方案（若代理挂了）：Windows 侧 `py -V:Astral/CPython3.12.14 -m pip download <pkg> --platform manylinux2014_x86_64 --python-version 310 --only-binary=:all: -d C:\Users\mary3\apmcm_stage\wheels`，WSL 侧 `pip install --user --no-index --find-links /mnt/c/Users/mary3/apmcm_stage/wheels <pkg>`
- Windows 主 Python 3.14 安装损坏（无关，用 Astral 3.12 或 WSL）

### 1.3 Kaiwu SDK 安装与凭证
- **安装位置**：`~/.local/lib/python3.10/site-packages/kaiwu*`（pip 安装，非源码）
- **凭证**：`~/apmcm2026/configs/kaiwu_license.py`（用户本人凭证，2027-05-25 到期）
  ```python
  KAIWU_USER_ID = "<KAIWU_USER_ID>"
  KAIWU_SDK_CODE = "<KAIWU_SDK_CODE>"
  ```
- **激活**：`kw.license.init(user_id=..., sdk_code=...)`——**需联网**（从平台下载 license 文件），已验证激活成功
- **连经典 SA 求解器都要 license**——无凭证则全链不可用

### 1.4 Kaiwu SDK 实战 API（1.4.4 实测，与镜像文档有出入，以此为准）

```python
import sys; sys.path.insert(0, '/home/mary/apmcm2026/configs')
import numpy as np, kaiwu as kw
from kaiwu_license import KAIWU_USER_ID, KAIWU_SDK_CODE
kw.license.init(user_id=KAIWU_USER_ID, sdk_code=KAIWU_SDK_CODE)

# 经典求解器三件套
kw.classical.SimulatedAnnealingOptimizer(initial_temperature, alpha,
    cutoff_temperature, iterations_per_t, size_limit, rand_seed)  # 主力
kw.classical.TabuSearchOptimizer(...)
kw.classical.BruteForceOptimizer(...)  # 小规模真值核对用

# QUBO→Ising 转换
from kaiwu.core import qubo_matrix_to_ising_matrix
h, offset = qubo_matrix_to_ising_matrix(Q)  # Q 上三角/对称 numpy 矩阵

# 求解：输入 Ising 矩阵 h
raw = np.asarray(solver.solve(h))  # 返回 (n_solutions, n_bits+1)
```

**实测踩坑清单（重要）**：
1. `solve()` 输出每行末位是符号位：解码用 `spins = row[:-1] * row[-1]`，再 `x = (spins+1)//2` 得二进制
2. **`output[0]` 不一定最优**——必须遍历全部解按业务目标取最优（教程实例 output[0] 只得 13，最优 19 藏在其他行）
3. 没有 `kw.sampler.optimal_sampler`——镜像文档示例代码过时
4. 已验证 SA 参数：`initial_temperature, alpha, cutoff_temperature, iterations_per_t, size_limit, rand_seed, process_num`——**不要传** `seed/time_limit/num_reads`（不存在）
5. 初温启发式：`initial_temperature = max(100, 2*np.max(np.abs(h)))`（罚系数大时 100 根本不够探索）
6. SA 很快：104bit/128解池/200迭代仅 0.5s——可以大方调参
7. **惩罚为零≠约束满足**——解码后必须独立重算业务约束（kaiwu 官方纪律）

**符号建模层**（kaiwu-coding-skill 权威流程，适合复杂约束）：
```python
from kaiwu.core import (ndarray, Binary, QuboModel, PenaltyMethodConstraint,
                        qubo_model_to_ising_model, get_sol_dict, get_val)
x = ndarray(3, 'x', Binary)
model = QuboModel()
model.set_objective(3*x[0] + 2*x[1] + 10*(x.sum()-1)**2)
model.set_constraint_handler(PenaltyMethodConstraint)  # 传类不实例化
q = model.get_matrix()
```
约束编码模板（skill 原文）：恰好一个 `P*(sum(x)-c)**2`；至多一个 `P*sum(x[i]*x[j])`；整数上限需非负松弛比特。罚系数纪律：P 大于原目标上下界之差即可，**过大会拉爆动态范围**——写明依据不靠无限加大。

### 1.5 SDK 文档与 skill 位置（全部已镜像 WSL，无需再提取）
```
01_参考学习/量子知识补充（forD题）/
├── 01_Kaiwu官方/sdk_docs_full/        34 页 API 文档镜像（模块参考/教程/进阶/案例）
├── 01_Kaiwu官方/学习文档_md/           83 页学习地图 markdown（含索引 学习文档_md_INDEX.md）
├── 02_GitHub开源/kaiwu-coding-skill/   ★官方 AI 技能包——SKILL.md 是权威 API 流程，写 Kaiwu 代码前必读
├── 02_GitHub开源/kaiwu_community/      SDK 开源核（60 文件，可查求解器精确行为）
└── 02_GitHub开源/qdock-kaiwu-workshop/ 分子对接 QUBO 全管线+经典/真机双轨范本
```

---

## 第二部分 · 选题决策与 D 题分析

### 2.1 为什么选 D（四题审计后结论）
| | A 洪水遥感 | C 鲸豚声学 | **D（选定）** |
|---|---|---|---|
| 差异化天花板 | 中（CV强队都有GPU） | 低（红海+原研究R代码直接给，趋同） | **最高（量子+零正例+QUBO三重劝退）** |
| 外部依赖 | P3需自采横州洪水影像（不可控） | 无 | **零** |
| 客观可验证性 | 中 | 低 | **极高（盲池命中率可验证）** |
B 题（炼钢光谱 xlsb）最早排除：GPU 无用、领域不透明。

### 2.2 题目本质
Castelli et al. 2012 (Energy Environ. Sci.) 钙钛矿数据集（52 元素 A/B × 7 族 X = 18,928 全因子网格）。四物理条件 `e_form<0.21 / 1.4≤gap≤3.1 / VBM>5.73 / CBM<4.50`，违反度 `V=Σ[max(0,dev/0.5)]²`，全空间 **19 个 V=0**（正例率 0.1%）。三问：P1 代理模型 / P2 X=NO2 选 (A,B) QUBO / P3 X 三选一+(A,B) QUBO+SPQC 硬件成本。

### 2.3 致命陷阱（全部已验证，违反即团灭）
1. `gap=0`=金属性**非缺失**（96.12% 行）；2. train/val **零正例**（19 正例全锁 holdout 的 (A,B) 对）；3. 推理只有 (A,B,X)——a_lat/volume/mu_b/fermi* 禁入特征；4. 题面"15 vs 19"矛盾——以 README 的 V=0/19 为准（Castelli 原文 strict 口径=15）；5. a_eq_b 合法但无正例。

---

## 第三部分 · 已完成工作（含全部数字，可逐项复核）

### 3.1 数据审计 ✅ `03_代码/verify_data.py`（33 项全 PASS，一键重跑）
sha256 9/9；V 重算 max diff 1.02e-5（=README 声明舍入传播）；零正例确认；全因子网格 18,928 唯一三元组；池文件一致性（07=NO2全集2,704 / 08=三族8,112 / 盲池=∩holdout）。

### 3.2 切分算法完全逆向 ✅（论文数据审计节杀手锏）
```
L1: 2704 (A,B) 对按 sha256("2026|A|B") 升序 → 最小 510 对填位 holdout
L2: 19 正例宿主对强制锁入 → 510+19=529（510/510 全命中验证）
L3: 剩余 2175 对按 sha256("2027|A|B") 升序 → 最小 567=val（567/567 全命中）
```
19 锁定对：Ag-Nb, Au-Hf, Ba-Ga, Ba-In, Ba-Sn, Ba-Ta, Ca-Ge, Ca-Nb, Ca-Sn, Cs-Nb, In-Hf, La-Ti, Pb-Ga, Rb-Ti, Sr-Ga, Sr-Sn, Sr-Ta, Y-Pb, Y-Ta
**伦理铁律：仅作审计证据写入论文，建模/选择/迭代一律不用；冻结前不做命中检查。**

### 3.3 P1 基线 ✅ `03_代码/p1_baseline.py`
- 特征：52元素×14描述符（mendeleev+zunger）→A/B展开+4交互+X one-hot = 40 维；LightGBM log1p(V)，best_iter 529
- **数字**：val RMSE 4.85 / 全局 tau 0.777 / top-20 富集 29×（30% vs 基线 1%）
- **弱点（增强靶心）**：val V<2 子集 tau 仅 0.32、**group-CV tau(V<2) 仅 0.11（fold2 为负）**——近正例外推排序弱
- 特征重要性 top：sum_ie1/d_irad/d_en/d_Z/B_ea
- 共享特征模块已抽离：`feature_utils.py`（canonical，新代码用它；p1_baseline 内联副本未动）

### 3.4 P2 QUBO 管线 ✅ `03_代码/p2_qubo.py`（端到端跑通并验证）
**核心建模洞察（论文级）**：one-hot 编码下二次项 a_i·b_j 的系数就是 (i,j) 对的 V̂ 表值——**QUBO 精确承载全池表值，无需 FM 近似**（FMQA 仅在池不可枚举时必要）。且池可枚举→暴力枚举作真值，**QUBO 求解器精确性可被严格验证**。

`p2_report.json` 全部数字：
- surrogate 02+03 合并训练（题面规定）；池预测 vhat ∈ [4.056, 64.149]
- **暴力最优：A=Y, B=Zr, vhat=4.0563**
- λ = max(vhat)+1 = 65.149（推导：违反 one-hot 最大收益≈免付最高表值）；Q: 104×104，系数∈[-65.1, 130.3]
- Ising 转换 offset 97711.09，max|h|=1053.3→初温 2107（2·max|h| 启发式）
- SA：128 解池/iterations_per_t=200/0.5s
- **结果：128/128 全部可行，最优 = Y,Zr 与暴力枚举完全一致 ✅**
- 产出：p2_report.json / p2_pool_predictions.csv / p2_qubo_matrix.npy

**注意**：vhat 最低 4.06——surrogate 在池上预测不到任何近零候选，零正例外推弱点在 P2 结果上直接体现。P1 增强是提升 P2/P3 答案质量的唯一路径。

### 3.5 P3 关键发现（进行中，重要）
**朴素 P3 目标是三次项**：`Σ Vhat(i,j,x)·a_i·b_j·x_x` 含三变量乘积，**QUBO 只支持二次**——这是 P3 真正的建模难点（很多队会在这里出错）。三条出路：

| 方案 | bit 数 | 精确性 | 评价 |
|---|---|---|---|
| A. X 分解：3 个独立 P2（每族一个 104bit QUBO）取最优 | 3×104 | **数学上严格等价精确** | 最简单最稳；但"回避"了联合编码 |
| B. 复合位编码：z_{j,x}="B=j且X=x" 156 位替代 b+x | 52+156=**208** | 精确二次 | 联合编码的正解；约束 sum z=1 |
| C. 辅助位线性化 y_{j,x}=b_j∧x_x | 52+52+3+156=263 | 精确但引入线性化罚 | bit 最多、罚结构复杂、最易错 |

**建议**：论文呈现 B 作为联合 QUBO 正式建模（满足题面"model in QUBO form"），A 作为精确性交叉验证+成本对比——"分解 vs 联合"的 bit/成本对比本身就是成本账本的亮点素材。C 仅作反面教材提及。SPQC 550 qubit 三种都装得下。

---

## 第四部分 · 资料库地图（811+ 文件，`01_参考学习/量子知识补充（forD题）/`）

```
├── README_策展摘要.md           ★先读：FMQA技术定性/陷阱/8红线/QUBO骨架/Castelli溯源
├── 00_题面官方链接与资料/        题面7链接清单
├── 01_Kaiwu官方/                sdk_docs_full(34页) + 学习文档_md(83页+索引)
├── 02_GitHub开源/               kaiwu-coding-skill★(权威API) / kaiwu_community★(SDK源码) /
│                                qdock-kaiwu-workshop★(双轨范本) / simulated-bifurcation-algorithm★(GPU dSB) /
│                                perovskite-tutorial★(ion.csv+zunger半径表) / perovskite-ml /
│                                kaiwu-pytorch-plugin(域外) / kaiwu-cli-mcp / dsh-qboson-ising-solver / QUBO
├── 03_学术论文/                 7篇PDF+INDEX_文献索引：FMQA综述(6.9MB)/Kitai开创/Glover QUBO手册(3.2MB)/
│                                Goto+Tatsumura dSB原文/QA虚拟筛选/钙钛矿SHAP-SISSO
└── 04_QUBO基础/                 第三轮(五岳杯拆解)+第四轮(GitHub灵感)索引
```
**五岳杯审美**（评委大概率同源）：ML问题QUBO化+真机/经典对比+百分比提升表；技巧：n-bit压缩编码、不平衡惩罚分层λ。真机 550 qubit。
**待补**（不阻塞）：imbalanced regression PDF（arXiv 2102.09554，零正例理论根基）；五岳杯历届赛题（开物论坛 forum.php 可爬）。

---

## 第五部分 · GPU 差异化五出口（Day4 增强，不得挤占主线）

用户：云 A100 + 本地 5070Ti。核心定位：**GPU=别人买不起的证据密度**。
1. **自盲测蒙特卡洛**：lock 已知数据→重训→重解 QUBO→命中率分布×300 复制——提前分布估计盲池评分
2. **深度集成 surrogate**（30-50 成员）→认知不确定性进选择目标
3. **GPU dSB 求解器**（simulated-bifurcation-algorithm 已入库，pip 直装）→成本账本三档对比+万次 bootstrap 稳定性
4. **采样预算仿真战役**（主动学习采集函数对比）——直接回答题眼
5. 反清单：不做 CGCNN/张量网络/Blender

---

## 第六部分 · 下一步行动序列

1. **P3 实现**（按§3.5 方案 B+A 双轨）
2. **P1 增强攻坚**（靶心 group-CV tau(V<2) 0.11→0.4+）：lambdarank 排序目标/分位数回归对照、容忍因子组合特征、深度集成 uncertainty——**P2/P3 答案质量完全取决于此**
3. **精度适配**：kaiwu preprocess 模块 8bit 位宽压缩实测——SPQC 硬件约束的操作化（成本账本核心）
4. **CIM 真机试投**（若用户已拿配额）：先投教程级小实例验证链路，再投 P2 的 104bit
5. saikr 系统查 P1 预测文件提交格式
6. 论文骨架搭建（LaTeX 模板在 `00_赛题与规则/官方发布/2026论文规范与模板/`）

## 第七部分 · 红线（违反任何一条都是事故）
1. gap=0 不得当缺失删；2. 19 锁定对不入建模；3. DFT 输出列不入特征；4. val 只做选择不做训练（P2/P3 按题面用 02+03 合并训练）；5. holdout 只在冻结后预测一次；6. 求解必须走 Kaiwu SDK（dSB 只是对照组）；7. 论文数据节必须显式处理 15 vs 19 口径；8. 惩罚为零≠约束满足，独立重算；9. 不许声称保证最优；10. 罚系数写明依据，不靠无限加大。

## 第八部分 · 用户人工任务状态
- [x] 平台注册+凭证（已拿到，存 configs/kaiwu_license.py）
- [x] ~~新手教程提交答案 `19`**（划分{2,4,5,9}|{1,3,6,7,8,10}，暴力+SDK双验证）→ 换真机配额~~（已完成）
- [x] ~~SPQC 机时申请~~（已完成——33×SPQC-550 + 1×SPQC-1000 到账）：https://kaiwu.qboson.com/plugin.php?id=computingPower&type=eb78f5c1-1e22-4cbe-a482-45ba2543248a
- **状态：配额已全额到账，真机通道可用。进入"68元纪律"预算管理阶段。**

## 第九部分 · 真机配额与 CIM 调用（Day2 更新）

### 12.1 配额现状
| 机型 | 比特数 | optimization credits | 用途定位 |
|---|---|---|---|
| SPQC-550 | 550 | **33** | 主力：P2(104bit)/P3联合(208bit) 都装得下 |
| SPQC-1000 | 1000 | **1** | 珍贵单次——留给最终关键对比或演示 |

**财务纪律：单买 1 次 SPQC-550 配额 = 68 元——33+1 次全是真金白银。每次提交前必须过三道闸：①矩阵冻结了吗（surrogate 还会变吗）②这个实验回答什么问题 ③能不能用 SA/暴力先模拟掉。宁可少投不乱投。**

### 12.2 控制台 vs SDK
**SDK 直接提交真机任务，控制台只用于监控/购买**——解题全流程不需要控制台操作。任务会出现在控制台任务列表里（可观察状态/耗时——成本账本素材）。

### 12.3 CIM API（官方文档实测版）
```python
import kaiwu as kw
from kaiwu.cim import TaskMode
kw.common.CheckpointManager.save_dir = '/tmp'  # 必须设置（结果缓存）
optimizer = kw.cim.CIMOptimizer(task_name='apmcm_p2_v1', task_mode=TaskMode.OPTIMIZATION)
solution = optimizer.solve(h)   # h 是 Ising 矩阵，返回 spin 位形数组
```
关键行为：
- **任务唯一性 = ising_matrix + task_name**——相同矩阵+同名重复提交走缓存**不重复扣配额**；改 task_name 才会新建任务；
- wait=False 默认异步，轮询 interval 下限 5 秒；task_mode 还有 SAMPLING（sample_number 10-2000）；
- 每次"新矩阵或新名"= 新任务 = 扣 1 credit——**33 次机会要当实验预算管理**；
- 建议命名规约：`apmcm26_p2_joint_vN` / `apmcm26_p3_trackB_vN`，版本递增。

### 12.4 精度适配（真机前必做）
P2 QUBO 系数范围 [-65, 130]、Ising max|h|≈1053——SPQC 硬件系数位宽有限，必须先经 preprocess 精度适配（文档专页 `source__advanced_topics__precision_adaptation` 在镜像里）。**适配前后求解质量对比本身就是成本账本的官方要求项**（"hardware coefficient constraints"）。

### 12.5 轨B 成本曲线实验（P3 求解器难度的实证，论文级素材）
208bit 联合编码，SA 递增投入：
| iterations_per_t | 耗时 | 可行率 | 最优 vhat | 命中暴力真值(2.3622) |
|---|---|---|---|---|
| 200 | 0.6s | 96/128 | 4.43 | 否 |
| 800 | 2.4s | 128/128 | 4.34 | 否 |
| 2400 | 6.9s | 128/128 | 2.53 | **仍否** |

**结论**：联合编码即便 12× 投入仍不命中精确最优；分解法 0.6s 精确命中。**编码结构主导求解难度**——"item-by-item cost"分析的核心实证已到手。待测：2400 之上是否存在命中阈值（cpu 便宜可扫），以及真机在同一矩阵上的表现对比。

## 第十部分 · 精度适配复核报告（Devin 自复核 + 待 Codex 二审）

> 背景：用户质疑"8bit 截断后求解崩溃"结果过于糟糕。复核后分层结论如下——**部分坐实、部分翻案、关键问题未决**。

### 10.1 坐实（数学层面无可争议）

1. `adjust_ising_matrix_precision(h, 8)` 行为已受控推断确认 = **`round(h × 127/max|h|)`**，无hidden cleverness（小矩阵 max<127 时原样返回；与手动实现逐元差异 0.0）。
2. **截断崩溃是真实的数学必然，不是实验 artifact**：one-hot-52 结构中每个变量与组内 51 个变量耦合，罚项在场强中累加 → max|h|≈1053 由罚结构主导；vhat 耦合贡献仅 vhat/4≈1–16。缩放比 0.12 后，**vhat<16.6 的耦合全部 round 到 0**——而最优候选 vhat 4–10 恰好全在被抹零区间。量化噪声/判别尺度 ≈ 663/256 ≈ **2.6 倍**——判别力数学上死绝。
3. 结论：**直连 one-hot-52 + 大 λ 的 QUBO 与 8bit 精度根本不相容**——这正是题面"hardware coefficient constraints"的牙齿所在，论文里可以作为核心分析（不是实验错误）。

### 10.2 翻案（我此前表述的不严谨处）

- 我把 naive 截断的失败讲成了"硬件约束的终极结论"——**错**。naive 截断只是最笨的基线，真机的精度策略远未穷尽。正确表述：naive 截断=稻草人基线，其失败精确量化了问题的难度，但不是终点。
- `calculate_ising_matrix_bit_width` 返回 `{'precision': inf, 'multiplier': inf}` 的含义我**未解读**——可能与分数系数的倍率表示有关，待查。

### 10.3 未决问题（待 Codex 二审与实验，按优先级）

1. **split 法内存爆炸**：`perform_precision_adaption_split(h, param_bit=8)` 默认参数对 104bit 矩阵试图分配 466,325×466,325 矩阵（1.58 TiB）——auto `min_increment` 估计过细。**待办**：手动设置 min_increment（建议从 vhat 顶部间隙倒推，如 0.05–0.5 扫描），测位宽开销与命中保持率。若 split 后总 bit ≤550 且命中保住，真机路径通。
2. **vhat 高端压缩**：`vhat'=min(vhat, cap)` 允许 λ 从 65 降到 cap+1——但初步估算（cap=20）缩放后 vhat 耦合仍大多 round 到 0/1，**可能不够**。需实测 cap∈{15,20,30} 三级。
3. **分层预筛选混合架构**（最有工程前景）：经典预筛每位置 top-k（k=10-15）→ 小规模 QUBO（20-30bit/组）——罚累加降 5×、系数比改善 5×，8bit 可能直接够用。代价：削弱"量子解全问题"叙事。**论文定位建议：作为精度驱动设计的正当工程方案呈现，并给出与不筛选版本的成本对比**——这本身就是"item-by-item cost"的正面回答。
4. **真机实测对照**：上述全部是经典模拟推断。真机 CIM 在 8bit 矩阵上的实际表现（含其物理噪声）从未验证——首投实验设计应包含"已知答案的小矩阵"标定。

### 10.4 复核纪律

- `03_代码/precision_report.json` 为初版实验数据；本节数学推导可独立验证（纸笔即可复核 51×2λ/4 的累加估算）；
- **Codex 二审要点**：①10.1.2 的累加因子推导 ②split 参数实验 ③分层预筛选架构是否合理稀释题意——若评委视角认为预筛选=回避量子建模，则只能走 split 或硬着陆上报退化。


## 第十一部分 · 姊妹篇指引

**批判性复核必读**：——含赛题位置、数据基本分析（四条件稀有性结构/O2S陷阱/低V元素fingerprint）、Devin全部思路与自知缺陷清单（P1基线六大硬伤：无容忍因子/纯回归目标错位/价态半径粗糙等）、复核标注体系。


## 第十二部分 · 近五年文献增补（Day2，18 篇已入库）

位置：（INDEX_增补索引.md 为导读）
全部 2021-2026（多数 2025-2026），按五线组织，每篇标注用途：

- **A. FMQA 方法线**：stage-encoding（编码阶段依赖★）/ initial-data-design（训练数据设计×bit覆盖——零正例困境理论武装★）/ alloy-recycling（FM+QA材料应用先例★）/ QA-materials综述 / binary-autoencoder
- **B. 求解器实证线**：photonic-solver-landscape（CIM性能随地形变化——轨B发现的文献呼应★）/ adaptive-penalties / knapsack-encoding
- **C. 不平衡回归线（P1理论根基★Codex重点）**：LDS/FDS ICML2021 源头 / DIR-eval-blindspots（评估盲区——支撑tau指标体系★）/ instance-hardness / DADIR
- **D. 钙钛矿ML线**：interpretable-ML-perovskite-eform-gap（与P1几乎同题，容忍因子正确使用参照★★必读）/ chemical-looping / tabular-foundation-BO
- **E. BO与硬件线**：self-driving-lab-review / BO-tutorial（采样预算仿真设计库）/ distributed-digital-ising（经典专用硬件档）

引用策略：奠基概念引原文，方法合法性引 2025-2026 增补。

## 第十三部分 · 学习地图完整版入库 + 精度问题重大修正（Day2 晚）

### 13.1 新资源：「01_Kaiwu官方/学习地图完整版docx/」（19 个 docx，自 D 盘同步）
与已有 83 个 md 网页版互补，docx 版含图片且章节完整。最高价值文件：
- 「1参数精度适配指南（8bit整数）.docx」★★★——精度问题的官方完整答案（见 13.2 修正）
- 「18优秀论文引用库.docx」★★——论文写作期直接用
- 「17量子+AI论文解读.docx」「16组合优化论文解读.docx」★
- 「12新手实操教程.docx」——含控制台实机图的性质描述（见 13.3）
- 「核查报告_APMCM课程文档.docx」——官方核查 APMCM 赛题课程适配性的报告（稀有视角）

### 13.2 精度适配重大修正（推翻第十部分的部分结论）
官方文档列出四种方法，第四种正是此前"未裁决三方案"的官方答案：
1. 「adjust_ising_matrix_precision」——全局缩放+取整（我测过的稻草人，会崩）
2. 「perform_precision_adaption_split」——变量拆分（官方称无损，内存问题需调参）
3. 手动建模预处理：★构建矩阵前对源数据取整/减小数位——教程明示"成本矩阵小数部分对解区分度低时取整不影响最优解"。对本题直接适用：vhat 是 surrogate 预测值，在构建 QUBO 前对 vhat 做精度感知变换是官方认可路径——直接支持"重构时精度感知缩放"方案；
4. 「PrecisionReducer」装饰类（官方推荐"一般情况使用该方法可更便捷地结合上述两种方式，保留更多原矩阵信息"）：kw.preprocess.PrecisionReducer(optimizer, precision=8, truncated_precision=10)——先放大舍入截到 10bit，再自适应拆分无损降到 8bit。已验证存在于安装的 SDK 1.4.4 的 kw.preprocess（注意：不在 kw.cim！），可本地用 SA 包装器零成本测试，不必烧真机配额。

实测可用的诊断工具：calculate_ising_matrix_bit_width、get_dynamic_range_metric、get_min_diff、perform_precision_adaption_mutate、construct/restore_split_solution。

关键硬件事实（新确认）：QUBO 转 Ising 上真机时自动多一个辅助比特（线性项须转二次项，引入辅助自旋 sa），104bit QUBO 实际 105bit 上机——比特预算要算这个。解码：原解 s = s̄·ŝa（辅助问题有两个简并解属正常现象）。
官方留的口子："如果需要更高精度，请联系官方人员申请"——若精度实在不够，这是合规升级路径。

Codex 行动更新：原"未决三方案"现在优先做——用 SA 包装 PrecisionReducer 在本地测 104bit 矩阵的命中保持率（零成本），与 naive 截断对照，一张表直接进论文。

### 13.3 控制台"量子计算机出的图"与 SDK 的关系（用户问题）
控制台示例图有两种：①哈密顿量随计算时间演化曲线（能量收敛过程，证明真机毫秒级收敛）②光量子比特相位圆图（蓝/绿点=自旋±1终态）。
答案：这些图属于"任务"而非"提交渠道"。SDK 提交的任务与控制台任务是同一种服务端对象（SDK 文档明示控制台可监控 SDK 任务），因此理论上在控制台打开 SDK 提交的任务详情同样有这些图。但 SDK 返回值本身只含自旋解+哈密顿量数值，不含演化数据——图只能在控制台截图获取。
待首投实证确认（写进首投检查单）：提交后立刻在控制台打开该任务，确认演化曲线/相位图是否齐全，截图存档——这两张图是论文里"真机证据"的最佳素材。


## 第十四部分 · 学习地图深度分析导读（Day2 晚，重要）

新文档：「01_Kaiwu官方/学习地图完整版_深度分析导读.md」（15KB，19/19 docx 全文通读后的分析，WSL+D盘双份）
配套：「01_Kaiwu官方/学习地图完整版_文本提取/」19 个 txt 逐字提取版（可 grep 检索）

★★★ 对主线方案的四个修正点（详读导读第三、六节）：
1. P3 应走 kw.hobo.HoboModel 原生降阶路径（reduce 自动加 Rosenberg 惩罚），我的手工双轨降级为对照组；
2. 罚系数有官方四函数（get_min_penalty 系列），one-hot 等式约束有专用精确工具，与 lambda=65.149 对照；
3. 混合架构正名——官方论文自己做 Quantum Benders 量子-经典混合分解，分层预筛选路线合规性证据确立；
4. SPQC-X 支持 14bit 精度 [-8192,8191]，申请前提 10+ 标准任务——真机实验从第一次就攒数量。

论文素材：Janus-QUBO（化学空间探索，与 P3 同构必读）、稀疏优化 K 位编码、QDOCK 成本分析范式、引用库含 QBoson 平台论文+两篇 Science CIM+97% 省时官方数字。真机证据链：PDF 报告下载+Hamiltonian 演化图+相位圆图截图。


## 第十五部分 · 文献三轮补缺（Day2 深夜，8 篇入库，累计 26 篇增补）

位置同第十二部分。三线归位：
- FMQA 正统确立：Tamura/Tsuda 官方综述（APR 2026）——surrogate→QUBO 桥接的师承引用；kernel-QA 备选桥；
- 零正例理论武器：metalearning_extrapolation（元学习外推，验证集就是钙钛矿带隙）★P1 重做前 Codex 必读；
- 基准方法论：PRE2025 统一栈基准（dSB 对照实验设计模板）+参数策略成本（成本账本调参项学术依据）。
未入库定位：npj QI 2024 MFB-CIM TTS 次指数、CommsPhys QAIA（dSB 超 D-Wave）——待补。

G 线（成本账本弹药）：NatComm2024 超磁伊辛 TSP 跨平台能耗表+CommsPhys2025 SPIM 硬件对比表（含耦合精度列——8bit 约束的国际谱系证据）已誊录入索引，PDF 反爬需浏览器人工下载。

I 线（机构权限）：JACS 带隙描述符已入库（Sangfor VPN+浏览器管线打通，headed 过 Cloudflare）。JCIS 待补。管线脚本 pw_download.py 固化 D 盘，复用要点见索引 I 节。

J 线：JCIS2025 数据稀缺知识蒸馏入库（B位电负性结论直接服务 P1 特征工程）。真机构权限链路端到端打通（要点：iKuuu 必关+Cloudflare 手动一次+CARSI 登录+CDN 签名链收割）。批量收割移交下一会话，管线就绪。


> 文献收割封盘（本轮）：增补库达 40 篇 PDF，含 4 篇 2024-2026 新文献（迁移学习/渐进描述符/符号回归/筛选工作流，全部 pdfinfo 验证），检索页管线已打通可复用。覆盖无死角度，建议主线优先。


> 新增资产：队友提取的《kaiwu SDK 1.4.4 官方文档汇编》164 页 PDF 已入库 01_Kaiwu官方/kaiwu_SDK_1.4.4_官方文档汇编_164页.pdf，版本与已装 SDK 精确匹配，含参数精度 p31/自动惩罚系数 p43/HOBO p91/preprocess p97 完整模块手册，查阅优先级高于散装 HTML。


> Perplexity 第一轮调研审定版已入库：01_参考学习/量子知识补充（forD题）/03_学术论文/Perplexity调研/第一轮_审定版.md（原文同目录）。重大发现：本题是氧化物/氧氮化物体系非卤化物，文献迁移需降权；精度分析五漏洞清单+统计辩护策略+修复三优先级，Codex 必读。


> skill 已按 D 题优化（Devin）：新增 references/25_D题量子优化优秀论文解剖.md（2025D 深度蒸馏：QUBO 逐约束章法/步骤复述块/表驱动证据链/2026D 差异对照），figure playbook 增加 §13-15 量子题专题（QUBO 矩阵热图/精度位宽曲线/真机证据规程/富集度统计图/成本账本图/配色注释细则/衔接句式）。写论文前必读 25 号和 playbook §13-15。路径：C:/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm/


> Perplexity 第二轮审定版已入库：01_参考学习/量子知识补充（forD题）/03_学术论文/Perplexity调研/第二轮_审定版.md。含三大硬核发现：① Mayr&Gagliardi 2021 与 Talapatra 2023 原文实证支持“两阶段分类+排序+X总价态特征”，并证伪 Roost-SSL；② 致命分母修正：若从 3,703 行 holdout 选 20 个，命中 2 个应报 EF=19.49x, p=0.00449（非全网格 99.6x）；③ D 题出版级出图样板库已落盘于 skill 的 assets/apmcm_d_plot_templates.py（py_compile 通过）。


> Perplexity 第三轮审定版已入库：01_参考学习/量子知识补充（forD题）/03_学术论文/Perplexity调研/第三轮_审定版.md。对 Codex P1_PLANv2 的两条致命修订（H-soft 仅作 RMSE 对照+新增条件概率乘积/连续效用筛选分数；取消 RMSE<=1.02x 一票否决改双目标 Pareto）、LambdaRank 单 Query 对照、电子描述符 E1 增量块，已全部审定落盘。


> Perplexity 第四轮审定版已入库：01_参考学习/量子知识补充（forD题）/03_学术论文/Perplexity调研/第四轮_审定版.md。P2/P3 全套弹药：λ 解析定标终案（减最小值重参数化+1.1x裕量）、8-bit 双失败机制框架、可行域枚举审计器、208-bit 计数修正（K=7 时实为 416-bit）、成本账本结构、查表价值论证模板句。


> skill 新增 references/26_D题三模链条完整性与诚信纪律检查清单.md——每问交付验收闸口（R1-R8 一票否决红线/三模链条逐问表/高奖反超点/评委攻防七问）。Codex 每问交付后将按 26.2 逐项验收；25 号文档新增 §25.15（2025D 评估章与参考文献水位解剖+2026D 评估章四小节模板）。


> skill 新增 references/27_Kaiwu_SDK_1.4.4_精读蒸馏.md——SDK 1.4.4 API 级精读（QUBO→Ising 精确公式+常数项纪律、mutate 保最优性质、split item/var 模式差异、get_min_penalty 算法实质、真机双模式规程、八雷速查表、方法节英文句式）。P2/P3 实施前必读。


> skill 新增 assets/apmcm_d_table_templates.tex（T1-T8 表格骨架，含验证列内嵌/成本账本/误差账本/富集统计/精度策略）+ 25号文档 §25.16（首页版面学与 QUBO 密集页解剖：框架图压正文第1页、问题重述压缩术、约束物理意义加粗开场、对称约束压缩）。


> 【最高优先级】docs/题目原文精读与口径锁定.md 已入库（D盘根目录同份）。三大终审：① P3=O3/NO2/FO2 三族，208-bit 口径确认正确；② 15/19=严格/非严格边界语义，官方原文并置两数字；③ 【实证新发现】盲池 11/12 恰好=全池与 holdout 04 的交集（11∩04=529 全集、与 02/03 零交集）——全池含 2,175 个训练可见组合的记忆捷径，盲池是唯一诚实考场与 probable 评分池。实施纪律：两池都做、V̂ 全池统一用代理预测值不得换真值、headline 用盲池结果。P1 方案无需修改。
