# D 题独立复核：开源资产与 SDK 实现

本文件是资料审查，不是 P1 实施或 P2/P3 求解。所有参考仓库仅按文本/AST/ZIP 读取；未导入仓库、安装包、运行示例、授权或联网调用。`corpus_source_outline.py` 产生结构地图，**结构审阅不等于全文读完**。最终阅读量按 CSV 状态分开报告。

## 1. 最重要的发现：wheel 中藏有 1.3.1 实现

R0822（QDock `vendor/kaiwu-1.3.1-py3-none-any.whl`）是 68 项成员的 ZIP，内含可读 Python。已直接读 `_precision_reducer.py`、Ising `_precision.py`、`_precision_adaption_split.py`、`_precision_adaption_mutate.py`、`_bound.py`、`_utils.py`、SA、`OptimizerBase`、`HeapUniquePool` 全文，以及 CIM 构造/solve 和约束编译关键方法。这是 **1.3.1 源码证据**，不冒充当前安装版本。

- 精度流程：先检测能否等比例整数化，否则截断至 `truncated_precision`；再拆分至目标位宽；超过 `target_bits` 时尝试中间截断，再超限就直接截断到目标精度。故“有官方 Reducer”不推出“原目标无损”。
- 1.3.1 `only_feasible_solution=True` 默认；1.4.0 文档默认 False。True 只丢弃副本不一致样本；False 时若还原失败，直接取每组最后副本，仍需重新验证业务约束和原目标。
- `target_bits` 是拆分后的维度上限，参考自旋也计入。1.3.1 在原维度 `>= target_bits` 即拒绝，不能按错误提示的“larger”误认为允许等于。
- 拆分返回的 `last_var_idx` 实际是每组**最后**位置，文档某处写“第一次”与实现不符；还原逐组检查一致性。默认分辨率取全矩阵不同系数的最小正间隔，不是最小非零绝对值。
- 全零矩阵的位宽检测分支返回 tuple，其他分支返回 dict；后续 `.get` 在此边界存在静态不一致。只记录源码风险，不声称已运行触发。
- 1.3.1 CIM 构造读取授权，`solve` 可能创建远程任务；`interval` 乘 60，为分钟。当前 1.4.4 文档为秒，必须按安装版核对。不能为“检查接口”创建 CIM 实例。
- `track_data` 装饰器也出现于本地预处理/SA，不能把“算法本地”自动等同于“执行完全不联网”；此次只静态读源码。

## 2. 能量、候选和罚系数

社区源码 R0747/R0749/R0758/R0759 确认 (H=-s^TJs)，矩阵对称项会计两次。QUBO 转换器已经负号和参考自旋化，不能再随手取负。业务二进制恢复为 (x_i=(1+s_i s_{ref})/2)，偏置必须单独计入。

- 新版基类 `solve(..., sort_solutions=False)` 不排序；`solve_qubo` 自己排序。1.3.1 单进程 SA 的 `HeapUniquePool.get_solutions()` 则排序；多进程最后 `np.unique(axis=0)` 不保持能量排序。故“任何版本第一行都最优”与“任何版本都未排序”两个概括都不成立，必须检查实际调用链。
- 1.3.1 `size_limit` 是沿退火轨迹维护的去重候选池上限，不是独立读次数。QDock 对它的 independent reads 解释不继承。采样器、优化器解池和独立重复运行分开记。
- R0752 `_constraint.py` 和 R0773 测试全文确认：`get_min_penalty_for_equal_constraint` 保护可行点的一位翻转局部意义，不是全局联合约束定理。`diff` 仅考察 0/1/2 个邻接项估最小变化；`exhaust` 也不自动化为整个业务模型的全局证明。
- 1.3.1 的等式 `PenaltyMethodConstraint.from_constraint_definition` 注释说平方，实际只返回 `left_operand-expected_value`，确有线性罚项风险。新版源码是另一实现，不能跨版本推断。报告建议显式写清平方罚项与独立业务校验，不把 `verify_constraint==0` 当无条件证明。
- 社区新版显式构造 `Constraint(..., expected_value!=0)` 的校验和罚项编译对右端处理不一致，常见 `expression == constant` 重载已将常数移入左端，二者不要混为同一调用。此次不改第三方代码。

## 3. KPP 的可借鉴内容及边界

R0383 中文 README 与 R0482 发行说明全文；源码/测试逐文件结构地图；R0693 MAIFS QUBO 辅助文件 857 行全文。

- `PrecisionSplitExplorer` 先把原矩阵按源精度取整，再拆分，在维度预算内搜索源精度。源精度本身就是近似；“highest feasible”粗细搜索在首次不可行处停，源码未提供拆分维度随精度单调的证明，不能据此声称全局最优适配。
- 该文件默认 CIM 目标 14 bit，但软件默认值不授予账户/任务 14 bit 权限；仍按官方通道和配额纪律。函数取第一条硬件结果且默认删除目录下记录，不适合本队可审计资产链；不得照抄。
- `_to_kaiwu_ising_matrix` 清楚区分正二次目标和 SDK 负哈密顿量，是有用的接口设计。MAIFS 特征掩码优化不等于 D 题组成筛选，也不能证明量子提升 P1 泛化。
- README 的 BM/RBM/QVAE/QDiffusion 是生成/表示建模框架；缺失真实正例时，生成更多样本不产生新的 DFT 标签。无需为满足 P2/P3 的 Kaiwu 要求而把 P1 强行改造成量子训练。
- 88 个 PO 是翻译目录，包含旧路径的重复翻译；单列为目录审阅，不计 88 篇论文或 88 份独立理论阅读。多个 130 字节“PNG”是 Git LFS 指针，不能算已看过实际图。

## 4. 其他开源资产

- QUBO R0235–R0237 全文：信用脚本把对角 QUBO 直接传 Ising 求解器，对角在自旋域是常数，且未实现声称的选取数量约束；新闻脚本 `solver` 未定义、松弛最大值 3 对 (k=4) 不覆盖零选择。只能当错误案例，不继承。
- perovskite-ML README 与完整 `Python Code` 已读；脚本带 `%matplotlib inline`，作为 `.py` 直接解析失败。各模型切分种子不统一，GridSearch 候选多为单点，不能以其结果替代统一 AB 分组协议。数据含其他 DFT 属性（如 energy above hull）的路线不能照搬成推断输入。`combine.zip` 只看成员名，未读取标签，来源与题目潜在重合未排除。
- perovskite-tutorial 两份 notebook 的全部 Markdown/code 单元已读，不读取 pickle、不运行 notebook。按位元素特征、容忍因子构造有启发；但使用平均离子半径、随机行切分、B/B' 对称化有具体材料假设。D 题 A/B 是不同位点，不能套 B/B' 无序对称；混合阴离子的有效半径也不唯一。HSE+SOC 标签不是本题标签体系。
- QDock README、backends 和 QUBO 构造全文：8 bit 无扩展截断是有代价的示例，不是通用保最优定理；最小 RMSD 用已知晶体真值挑最优样本，只是回顾性采样能力。当前盲测不能照用不可得真值选解。重试“一定只重取缓存、不重新扣费”需远程状态证明，不能凭注释继承。
- dsh 和 CLI/MCP 是授权、环境、进程与调用封装，不是新的量子求解算法。原始任务名/矩阵哈希/候选来源保存有用；自动安装、授权、批次提交和清理记录不能绕过本项目边界。
- SB README 和 quadratic optimization 文档全文；其余结构地图。SB 是经典数值模拟，可作以后经典比较候选，不可冒充真机。README 的返回值变量顺序在示例间自相矛盾，需按真实函数核实；文档“连续二次优化即凸”缺少半正定条件，“离散必须用启发式”也忽略适用规模内精确方法。其代码与文献均不自动成为权威结论。

阶段记录：本笔记完成时下一步是优秀论文/往届赛题。现已完成这些阅读与旧资产核查，结论见根目录复核报告；仍未实施新模型。


## 用户增补1.4.4汇编后的优先级

后续版本口径以 `CODEX_D_Kaiwu144_增补复核.md` 为准：新汇编164页正文全文已读，1.4.4模块定义优先旧HTML；当前core来自community1.0.8，get_min_penalty调用链同源；企业精度核心仍为.so，不能把以上1.3.1具体实现当作1.4.4已验证行为。新版支持var/item与不同恢复映射，only_feasible默认False，interval按秒。原笔记保留为旧版源码审查证据。
