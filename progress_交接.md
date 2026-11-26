# APMCM 2026 D 题 · 进度交接（Day 1 末）

## 已完成 ✅

1. **数据审计**（`03_代码/verify_data.py`，33 项全 PASS）：sha256 9/9、V 重算 1.02e-5、零正例确认、切分结构、池文件一致性。
2. **切分算法完全逆向**：hash2026 最小 510 填位+19 正例对锁定=holdout(529)；剩余按 hash2027 最小 567=val。19 锁定对已知（见口径文档§2，含伦理裁决：**仅作审计证据，不入建模**）。
3. **口径文档** `02_口径与约定/D题口径.md`：V=0/19 正例、边界 inclusive、gap=0=金属性、评估协议身份表。
4. **P1 基线**（`03_代码/p1_baseline.py`，已跑通）：
   - 特征：mendeleev 全属性+zunger 半径，52 元素×14 描述符 → A/B 展开+差值+X one-hot = 40 维
   - 模型：LightGBM log1p(V)，best_iter 529
   - **结果**（关键诚实数字）：
     - val RMSE 4.85，全局 tau 0.777
     - **val V<2 子集 tau 仅 0.32；group-CV tau(V<2) 仅 0.11（fold2 为负）**
     - top-20 命中率 30%（基线 1%，29x 富集）
   - **结论：全局排序强但近正例排序弱——正是零正例外推的核心难点，后续所有增强的靶心**
   - 特征重要性 top：sum_ie1, d_irad, d_en, d_Z, B_ea（电离能/半径/电负性主导——物理合理）
   - 产出：`p1_lgbm_baseline.txt`、`p1_feature_importance.csv`、`element_descriptors.csv`

## 环境状态

- WSL Python 3.10.12（符合 Kaiwu 要求）；sklearn 1.7.2/lightgbm 3.3.5/mendeleev 1.3.0 已离线装好
- **WSL 网络仍断**（iKuuuVPN TUN 模式下 TCP 不通，ICMP 通）；绕行方案已验证：Windows `py -V:Astral/CPython3.12.14 -m pip download --platform manylinux2014_x86_64 --python-version 310 --only-binary=:all:` → WSL `pip install --user --no-index --find-links`
- Windows 主 Python 3.14 安装损坏（不影响，用 Astral 3.12）

## 下一会话立即执行（按序）

1. **P1 增强**（靶心：近正例排序 tau 0.11→0.4+）：
   - 分位数回归/排序目标（lambdarank）替代纯回归
   - 单调性约束、特征交互（容忍因子类组合特征）
   - 深度集成 uncertainty（GPU/CPU 皆可，MLP 小规模）
   - 对照实验表：回归 vs 排序目标 vs 分位数
2. **P2 QUBO**：one-hot A(52)+B(52) 编码，λ 惩罚，Kaiwu SA 求解 2704 态——需先装 kaiwu SDK（走 Windows pip download 绕行）
3. **用户人工（已提醒，状态未知）**：平台注册+license+SPQC 机时——https://platform.qboson.com/
4. 题面重读确认 Q2/Q3 用全量池还是盲池（口径文档§4 待办）
5. saikr 系统查 P1 预测文件提交格式

## 关键认知（勿丢失）

- 近正例层 V<2 仅 169 条（train+val），是真正学习目标
- 推理时只有 (A,B,X)——DFT 输出列禁入特征（已遵守）
- 19 锁定对：Ag-Nb, Au-Hf, Ba-Ga, Ba-In, Ba-Sn, Ba-Ta, Ca-Ge, Ca-Nb, Ca-Sn, Cs-Nb, In-Hf, La-Ti, Pb-Ga, Rb-Ti, Sr-Ga, Sr-Sn, Sr-Ta, Y-Pb, Y-Ta
- GPU 五出口按优先级：自盲测蒙特卡洛 > 深度集成 > dSB 对照 > 采样预算仿真
- simulated-bifurcation-algorithm 已入库可 pip 装（GPU 对照组）
