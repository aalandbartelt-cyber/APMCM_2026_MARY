# P2 真机接口事实复核 v3

2026-11-28；主 Codex 独立执行。证据限已安装 SDK 与入库官方文档，本次未访问账户、未提交任务、未拟合或更改矩阵。本文件是操作审计，不是论文稿。

## 裁决

| 用户问题 | 可确认的事实 | 不能据此推断的内容 |
|---|---|---|
| 是否有 optimization 路径 | 有。相同 `CIMOptimizer` 和 `solve()`，由 `task_mode` 选择；默认 optimization。两模式共用创建/查询端点 | 不存在已证实的另一条可固定100原始采样的“solve专用”路径 |
| 分别使用什么配额 | 官方指南：optimization 对应 Optimization Credits；sampling 对应 Sampling Credits。SDK TaskMode 文档称前者为原 QUOTA 模式 | 当前具体扣哪桶、一次扣多少、失败是否扣费均须P01实证 |
| optimization 接受 sample_number=100 吗 | 本地构造及提交前序列化接受，拦截的POST明确携带100；默认未传时携带10 | 客户端发送不证明后端采用，更不保证返回100个未筛选样本 |
| 回包结构相同吗 | 文档公开的 `solve()` 返回接口同为 ndarray。相同本地缓存加载器可原样读取3×490和100×490合成数组 | 不能证明两模式真实响应字段、返回个数、重数或物理采样语义相同 |
| 能否原样保留100样本分布统计 | 整链/部分链解码、原表regret算法可保留。原100样本主统计合同暂未成立 | optimization 经能量排序、聚类筛选；即使100行，也不能自动作为100次原始硬件采样分布 |

## 精确依据

1. **SDK汇编印刷页44–47（PDF物理页47–50）**：“专用量子计算云平台计算模式”。印刷页45将sample_number限定于Sampling，印刷页46说明Optimization动态调整计算次数并排序、聚类后处理。
2. **印刷页49–51（PDF物理页52–54）**：`CIMOptimizer` 构造、`solve` 返回ndarray、TaskMode定义。印刷页51明确 `OPTIMIZATION` 为原QUOTA、`SAMPLING` 为原SAMPLE；印刷页50仅示例十行，不能当作任何任务的固定个数保证。
3. **入库《4量子云服务使用指南.txt》**：第22、92–93行区分两种Credits；第96行说明优化后处理；第111行限定sample_number；第121–132行对照表明确optimization返回个数“系统决定”、输出为“聚合后的优先结果”。这些是已入库官方页面提取，不是临时猜测账户规则。来源页面为 `https://kaiwu.qboson.com/docs/serviceChain.html`。
4. **已安装发行包**：`kaiwu==1.4.4`、`kaiwu-community==1.0.8`。`kaiwu.__version__` 实际显示community的1.0.8，不能据此误判企业SDK版本。CIM二进制SHA256：`a42fe39552ea92ed5a98dff15844bce9e007041766951169074a8e4cfe16f066`。

原文摘取及来源文件哈希在 `artifacts/p2_cim_go_20261128/{sdk_mode_pages_v3.txt,cloud_guide_mode_lines_v3.txt,interface_sources_v3.json}`。

## 离线客户端核验

脚本 `03_求解/D/p2_cim_go/audit_modes_offline_v3.py` 拦截全部HTTP，并禁用socket连接；无账号凭据、无真实上传、无真实提交、无扣费。权威结果 `artifacts/p2_cim_go_20261128/interface_v3_offline_03/audit.json`。

- sampling/100、optimization/100、optimization默认三个请求案例全部通过。相同端点 `/api/system/software_task_manager_pro/create_sdk_task/`；相同查询端点 `get_sdk_task_result/`；区别为task_mode，默认样本字段10、显式字段100。请求均含490位、sample_sort_mode=2，无机型选择字段。
- 三案序列化矩阵payload SHA256完全相同：`a4f24e1b99fef30155cd66afccc08f41f01c0edbbc54eddd2a0e44bc347b0dd9`；原矩阵未变。
- 两模式各用3行和100行合成缓存，四案均返回对应ndarray且逐元素一致。只证明客户端不强制100行，不证明服务端实际返回格式。
- 两份早期离线调试报告保留：首版缺缓存父目录；第二版尝试用dict子类追踪私有读取函数，被Cython严格类型拒绝。没有把这些实现错误算成真机失败；最后改为测试公开可确认的本地缓存读取，不继续猜服务器字段。全部网络调用为0。

## P01 实施边界

用户已授权转optimization，P01单发设计不变。提交前仍需新Git锚定、证书、输入/代码哈希与解码验收；入口使用 `task_mode='optimization', sample_number=100, wait=False`，且 `solve(..., negtail_flip=False, sort_solutions=False)`。后两个开关只禁本地翻转/排序，不承诺禁服务端后处理。

P01前余额已由用户报为550=36、1000=2，均为优化次数；Sampling Credits=0单列。前后记录两桶，不假定可互换。P01后若只从550扣1，则预算规则25≤0.8×36成立；未实际扣费前不能当结论。没有必要主动提交一笔零余额sampling；当前没有实际拒绝记录。

**P01先核验服务事实，P02及正式扩展暂不开放。** 若回包不支持100原始样本合同，保留全部实际返回解、解码/能量/链诊断，原主统计标为NOT_EVALUABLE，暂停并报告。不能复制补足100、截取较好100、把筛选后频率当原始采样概率，或在看到结果后悄悄改分母。算法和矩阵未变，但若需改统计对象，应明示由用户裁决，不能用“事实更正”掩盖实质语义差异。
