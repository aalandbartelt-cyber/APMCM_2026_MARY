# P2 真机服务验证最终报告（2026-11-28）

**20个正式任务全部有效完成，全部取得严格整链可行的代理最优命中；任务最优原表regret均为0。** 5个先导独立记录，不混入正式统计。这里评价的是SDK默认路由的optimization服务返回解集，不是原始物理采样。

| 服务级对照 | 单元数 | 取得严格可行返回的单元 | 代理最优命中单元 | 每单元最优原regret |
|---|---:|---:|---:|---:|
| CIM optimization 正式任务 | 20 | 20 | 20 | 全部0 |
| 既有SA固定块（每块100次既有重启） | 5 | 5 | 5 | 全部0 |

两者计算预算和后处理不对称：CIM内部自适应计算、排序/聚类预算未公开；不作同预算优胜、逐解命中率或TTS声明。SA未追加运行。

正式任务均返回10解；原始自旋与业务映射已独立逐解复核。20个任务返回集的最低整数能量为−58638至−58546，仍比证书整数基态−58722高84至176。**代理最优命中与整数模型基态命中不同。** 不能据此宣称真实材料五条件验证或材料学全局最优。

合计真实创建25次、25个不同服务器ID，无重提/补槽；已核实550优化额度36→11，共扣25，1000保持2。用户先报12/2、随后纠正11/2，两个读数历史均保留，以最新为准。全部调用已结束，当前没有运行中的求解/轮询任务。

任务级95% Clopper–Pearson区间为[0.8315665290,1]，仅在近似独立、同成功概率且截止机制可接受的假设下辅助描述。5000次任务bootstrap的命中与条件regret退化，明确披露，不解释成零不确定性。

## 资产和复现

- 正式终态逐任务表：`codex/P2_CIM_FINAL_EXPERIMENT_TABLE_20261128.csv`（25行含独立先导标签；正式筛选stage=formal）。
- 完整结果和统计：`artifacts/p2_cim_go_20261128/reports/20261128T142429/`。
- 独立核验：`final_independent_return_audit.json`，25任务/250返回向量，全部能量/业务映射一致、40链0→1违例总数0；实现未导入建模/解码模块。
- 当前服务协议：`codex/P2_CIM_SERVICE_PROTOCOL_v3_1.md`；五先导门和首锚记录见`codex/p2_cim_service/`。
- 正式演化图6张：F03/F04/F06/F07/F08/F09，原样复制到`figures/shared/hardware/`，其余14个正式任务标明未提供图。P04先导图单独保存；图有无不改变数值回包有效性，不把a.u.解释成物理时间。图件归属依据用户逐项确认，图本身没有task ID。
- 4,727项旧保护资产及543项研究封存资产校验一致；新增拟合0、新增SA0、论文修改/编译0。

## 全部逐任务明细与统计（机器生成）

# P2 CIM optimization服务结果（全部已启动任务终态报告）

统计单位为服务任务；优化输出称“返回解集”。先导5槽不进入正式20槽。全程冻结矩阵/代理表；零新增拟合/SA，未写论文。正式锚 `4d02a7c2f4eb43daa261d0f0f536a104afde01ee`。

| 正式任务指标 | 计数 |
|---|---:|
| 计划任务 | 20 |
| 已尝试 | 20 |
| 有效服务返回 | 20 |
| 至少一个strict可行解 | 20 |
| strict原表最优命中 | 20 |
| strict原regret≤0.1 | 20 |

嵌套断言已检查：N_H≤N_eps≤N_F≤N_V≤N_A≤20。G20(0)=1.0；分母包含全部20计划槽。失败/pending/无可行解没有被静默剔除，条件regret不可用者记NA。

| 槽位 | 状态 | 返回解数 | strict解数 | 任务strict命中 | 最小原regret | 能量选解regret |
|---|---|---:|---:|---|---:|---:|
| P01 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| P02 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| P03 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| P04 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| P05 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F01 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F02 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F03 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F04 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F05 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F06 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F07 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F08 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F09 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F10 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F11 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F12 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F13 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F14 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F15 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F16 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F17 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F18 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F19 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |
| F20 | VALID_COMPLETED | 10 | 10 | True | 0.0 | 0.0 |

## 服务级经典对照

五个已封存SA块各100次既有重启：五块最优strict原regret均0，按物理能量选解的原regret也均0。CIM内部自适应计算次数及排序/聚类成本未公开；20个CIM任务与5个固定SA块不等计算预算、不等重复数。不把CIM返回解集与SA逐重启命中率并置，不推断量子优势或同预算优胜。所有逐解比例和TTS分析均取消。

## 描述性统计边界

已尝试任务strict命中率的95% Clopper–Pearson区间：[0.8315665290169146, 1.0]。仅在任务近似独立、同成功概率且截止机制可接受假设下辅助描述，不是跨实例或确认性硬件优胜结论。未启动槽位不被当成随机硬件试验。

5000次任务bootstrap，空条件regret子集0次；任务命中分位数[1.0, 1.0, 1.0]，条件中位regret分位数[0.0, 0.0, 0.0]。命中bootstrap退化=True；不得用零宽bootstrap冒充无不确定性。

## 可识别边界与文件

命中指冻结代理表La/Ti/NO2最优，不是材料真实性或五条件实验验证。整数基态性质由本地证书证明；物理返回相对整数基态的能量残差另列，不能因原表regret0就声称整数基态命中。服务端物理开始/结束时间、逐解能量与实际后端未提供；仅披露实际字段，不猜单位。

完整逐任务CSV、strict/partial字段、六指标、G20曲线表和bootstrap空子集计数见同目录。所有原始响应、终态文件、解码和SHA仍在live/及service_audit/；带签名URL的原始记录不外发。
