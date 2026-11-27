# P1 图件清单与定级提案

日期：2026-11-27。**色板 A 与本清单已批准；用户随后授权“后面几个图直接一口气全出”，替代原逐张等候门禁。** F2、F3、A1–A6 已全部制作并完成彩色/灰度自查；F1 v3 原件保留。共 3 张正文图、6 张附录图，见 [九图审阅索引](P1_FIGURES_REVIEW.md) 与 [连续翻阅 PDF](P1_figures_review.pdf)。图件自查不等于用户已批准入稿。

- 清单：[figure_inventory.csv](figure_inventory.csv)。严格保留 skill 模板的 16 列；模板未提供独立的标题、定级和三模环节列，因此在 `notes` 中明确写入 `title=…; tier=…; model_chain=…`，`section` 同时标注 Main text / Appendix。
- 逐图来源与 SHA：[figure_inventory_sources.json](figure_inventory_sources.json)。26 个来源文件均已确认存在；包含每图的过滤条件、汇总方式、必标信息与声称边界。
- 冻结色板：[palette_frozen.json](palette_frozen.json)，SHA-256 `8cd969d67c966c78ad1b41fc5f7859f98e04acfb37850039d13a98c9e66a64d1`；批准记录：[palette_freeze_record.json](palette_freeze_record.json)。

CSV 的 `physical_page` 留空，待论文排版阶段确定；`grayscale_ok` 已按每张图的实际灰度渲染更新，自查与用户审核状态分别记录。英文 caption 已随最终图件核对并写入 CSV，以下保留批准的用途和定级。

## 1. 九张图的定级

所有相对数据路径均以 `artifacts/p1_v21/` 为根。三模链条指**模型建立—模型求解—模型检验**；接口证据属于 P1 交付质量检验，不表示已经开展 P2/P3。

| 编号 | 英文标题 | 定级 | 用途一句话 | 主要数据文件 | 支撑环节 |
| --- | --- | --- | --- | --- | --- |
| F1 | Data audit and AB-blocked validation | 正文 | 展示 V 分布、金属占比和 AB 阻断结构，解释任务的类别不平衡及防泄漏设计。 | `domains/main_outer_{0..4}.csv.gz`、`preflight.json`、`splits.json` | 建立 + 求解 |
| F2 | Near-positive enrichment under fixed AB blocking | 正文 | 在相同逐折筛选预算下比较 H-soft、Ridge、mean、固定 random 的命中与富集。 | `results/all_domain_metrics.csv`、`P1_main_per_fold.csv` | 检验 |
| F3 | Error contributions and the regression-screening trade-off | 正文 | 同时呈现误差来自哪类样本，以及登记回归模型的 RMSE–EF 权衡。 | `results/P1_final_experiment_table.csv`、`regression_pareto.csv` | 检验 |
| A1 | Residual structure by X family | 附录 | 分开检查七个 X 族的有符号偏差、RMSE 和绝对残差 q95。 | `results/OOF_residual_scales_by_X.csv` | 检验 |
| A2 | External OOF probability calibration diagnostics | 附录 | 将概率刻度诊断与排序效果分开，核对四条概率路线的可靠性。 | `results/oof_calibration_consistency.csv`、`oof_calibration_ranking_checks.csv`、五折已有 OOF 概率表 | 检验 |
| A3 | Nominal-candidate rank and surrogate decision regret | 附录 | 结合名次分布和双向代理 regret 判断四池候选轮换的代价。 | `hardening/decision_stability_members.csv`、`decision_stability_summary.csv` | 检验 / P1 输出接口 |
| A4 | Split-half averaging and decision stability | 附录 | 展示十成员均值相对单成员参照的决策稳定性及剩余不确定性。 | `hardening/split_half_summary.csv`、`protocol.json` | 检验 / P1 输出接口 |
| A5 | Protocol-level extrapolation stress diagnostics | 附录 | 明确报告 element、target、xleave 三种压力协议的适用范围。 | `results/stress_summary.csv`、`stress_detail.csv` | 检验 |
| A6 | Feature additions and reverse ablations within model routes | 附录 | 分开呈现 R-log 的特征阶梯与最终 H-soft 的反向消融。 | `results/diagnostic_summary.csv`、`P1_final_experiment_table.csv`、`paired_AB_bootstrap_5000.csv` | 建立 + 检验 |

保留用户提出的全部九图及原定级，不增加正文图。F1 满足“每问至少一张数据处理/分析图”的要求。

## 2. 逐图可独立审定的口径

### F1：三联数据审计

三个面板分别为 V 分布、金属/非金属构成、五外折 AB 阻断示意。按 F1 第一轮审阅意见，内层三折说明移入图注，不再单画流程框；黄色放大区直接命名为近正例子集。只取五份外折文件的 **H-soft 行**还原 02 数据，不把同一对象的八路线重复记录算作八个样本。

已核实：N=11,256；金属 10,824（96.16%），非金属 432；有向 AB 组 1,608；V<=2 共 128 行；观测 V=0 为 0；最小 V=0.0004。零正例结论限于这份 02 数据，不能外推到隐藏 holdout。V 轴保留任务定义的原尺度，低 V 局部放大须标清范围。

分布与构成用 M/N，近正例用 P、eps=2 阈值用 W。AB 示意用中性框线、纹理和 Train/Evaluate 标签，避免擅自给训练/验证状态另配语义色。F1 v2 已移除含糊的 03/04 页脚，图面只描述 02 训练数据；其他数据集的角色留在正文协议说明中。

### F2：两面板富集曲线，预算与分母写在图上

横轴固定为每折 k=1,5,10,20,50,100。左面板画五折命中总数，右面板画五折 EF 等权均值。**k=20 对应总预算 100**，H-soft 的 68 次命中不能写成 68/20；也不改成一次全池 Top-20。

H-soft 过滤 `protocol=outer`、`domain=main_outer_0..4`；三基线过滤 `protocol=baseline`、`domain=baseline_0..4`。屏蔽 inner、by_X、stress 等其他行。图上固定写 `V<=2`、H-soft 68/100 和 EF=62.1024，以及 Ridge 10/100、mean 1/100、random 0/100。

random 的观测曲线保留真实零命中，理论 EF=1 另画参考线并注明 expectation。逐折 N/M/h 与已有 `p_uniform@20` 随图标明；p 值是**未校正的 uniform-null 描述性参照**，不平均 p 值，不编造五折合并检验，也不据此宣称选模后总体显著性。

S 用于 H-soft；三基线共用 B，分别用已冻结的方块虚线、下三角点线、叉号点划线和直接标签。重合时通过标签与必要局部放大解决，不改数据或颜色。

### F3：误差贡献与双目标

左面板用金属/非金属**对总 N 的 MSE 贡献**作堆叠条；二者相加必须等于 pooled RMSE²。包括四个登记回归候选及 Ridge、mean 两个数值基线。不得误用类别内部 MSE 代替贡献。

右面板按 `regression_pareto.csv` 的四个登记回归候选展示 RMSE–EF，前沿身份直接读取现成结果。纯筛选路线没有 RMSE，不填零；nested 行与已有候选重复时不重复作独立点。H-soft RMSE=4.6011、MSE 贡献 18.2920+2.8781、EF=62.1024 直接标注。已有 H-soft−R-log 的 EF 配对区间跨零，不能把菜单内 Pareto 结果写成稳定筛选优势。

### A1：三个对齐面板

将用户原先的“bias/RMSE/q95 分组柱”细化为三个对齐面板，原因是 bias 有正负号，另外两项均非负，合在一组容易误读。保留全部七个 X 族及每族 n=1,608。bias 定义为 `vhat−V`；q95 是 `abs(vhat−V)` 的经验分位数，不能称为保证覆盖的预测区间。

### A2：四路线可靠性小面板

每个面板对应 B-eps、S-eps、L-single、L-hash4 之一，统一事件 V<=2。读取既有外层 OOF 概率，按预定 **10 个等宽概率箱 [0,1]** 做展示性汇总，空箱不补点，显示各箱计数；只在 `figures/` 保存后续作图派生表。

斜率、截距和 Brier **直接读取** `oof_calibration_consistency.csv` 的 pooled 诊断行，不重新做 logistic/Platt/isotonic 拟合。扩充 OOF 概率表作为来源的原因是：汇总诊断 CSV 本身没有可靠性曲线的分箱数据。图上注明拼接 OOF 是概率刻度诊断，不替代逐折主终点；已有折内/拼接 Top-20 一致性结果以简短旁注呈现。H-soft 的 `-vhat` 不是概率，不进入此可靠性图。

### A3：四池全部成员与双向代价

左面板显示四池各 20 个成员给名义候选的名次，保留全部 80 条记录与 min/max；右面板显示正向、反向 regret 的 p50/p90/p95/max，不能只画中位数。Pool 08 的名次范围 1–72 直接标注。实际绘图采用明确标注的对数名次横轴，并仅竖向错开邻近点，以保证低名次聚集区可辨；名次值未改变。

regret 坐标注明 surrogate/Vhat scale，0.1 线注明 descriptive tolerance，不能叫物理可行阈值，也不能当真实 V regret。四池均未满足近优平台标准。此图只展示 P1 已有输出的决策质量。

### A4：split-half 双面板

左面板比较 argmin agreement，右面板比较 symmetric cross-table regret；使用既有 `bagged_half10` 和 `single_member` 汇总值。单成员基准为每次切分的全部 100 个跨半区成员对平均，不是任取一个单模型。

明确写 1,000 个切分复用同一批 20 成员；若标 p50/p95，它们是描述性分散度，不是独立样本置信区间。11/12 池均值半表的一致率仍只有 0.192/0.174，须显示。只说明十对十平均化的已观测稳定性，不宣称未来全 20 均值的准确率已经验证。

### A5：压力协议边界随图保留

两面板分别为 R-log 的 RMSE，以及 R-log/S-eps 的 EF；三种协议分组呈现，不连成性能改善轨迹。图上必须原样出现：**`protocol-level evidence, not final-model`**。

EF 有效池数为 element 5/5、target 3/3、xleave 29/35。M=0 的未定义 EF 不填零。不同协议的 N、M、总预算不同，不能按 EF 的高低得出外推难易排序；这些是 R-log/S-eps 的证据，不是最终 H-soft 的域外验证。

### A6：四面板，严格分开两类比较

上排展示 **R-log** 的 F0→F3→F3+E1：RMSE 与 EF 分列。下排展示 **H-soft** 去电子/去几何/去 X 统计相对完整 H-soft 的 ΔRMSE 与 ΔEF。内部文件中的 F4 在图中统一显示为 F3+E1。

这样拆开的原因是正向阶梯和最终模型反向消融使用不同模型路线，不能连成同一条改进链。反向消融区间读取修正后的 `paired_AB_bootstrap_5000.csv`，EF 使用 `EF_macro@20`，不用旧 pooled Top-20 诊断列。注明条件于冻结 OOF 和既往选择、探索性、未作多重区间校正；不新增拟合或 bootstrap 抽样。

## 3. 全图共同技术与审查约定

正式图采用 170 mm 宽，最小 8.5 pt；字体仅 Times New Roman，先调用指定 D 模板样式，再调用 `use_times_new_roman()`。按最终印刷尺寸安排面板，不把大图缩小以挤入版心。每图输出 300 dpi PNG、PDF 矢量和完整灰度 PNG，图内英文-only、白底、细框、无装饰网格。

所有颜色从 `palette_frozen.json` 读取。色板 A 的三组灰度门槛只适用于 S/B、Q/C、M/N；同一家族的其他方法/指标用面板、标记、线型、纹理及直接标签区分，不新增颜色含义。浅色线采用已展示的中性轮廓；各张图都另渲染完整灰度副本并目检。

每图审图单已附文件路径、用途一句话、来源文件、英文 caption，以及 dpi/字号/零中文/灰度可辨/色板一致五项自查。CSV 中 caption 与最终图件一致；灰度自查采用屏幕渲染，未进行实物打印。

## 4. 批量授权与当前状态

原制图顺序为 **F1 → F2 → F3 → A1 → A2 → A3 → A4 → A5 → A6**。用户最新指令“后面几个图直接一口气全出”已明确允许余下八张批量制作与提交，记录见 [批量授权](batch_rendering_authorization.json)。原逐张等待规则作为历史记录保留，不再阻止本轮制图。全部图件已交审，尚未嵌入论文。

本次只读既有 artifacts；只写 `figures/`。模型、原始数据、实验表与拟合账本哈希不变，新增拟合及 bootstrap 抽样均为 0。F1 v3 已明确样本类别、近正例子集、阈值线与训练/评估块的图例指代，本轮未改动。全部文件、逐图说明与审计回执集中在 [P1 图件审阅索引](P1_FIGURES_REVIEW.md)，色板与清单不再重复征询。
