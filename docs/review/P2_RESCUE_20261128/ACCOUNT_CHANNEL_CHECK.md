# 账号、配额与通道只读核验

核验日：2026-11-28。创建任务数 **0**；未调用 `solve`、`_create_task`、OSS 上传或充值接口。

| 项目 | 实测或来源 | 状态 |
|---|---|---|
| SDK | 安装版 Kaiwu 1.4.4，Python 3.10；运行时初始化许可证成功 | 通过本地初始化 |
| 只读链路 | 真实 GET `https://new-open.qboson.com/api/system/software_task_manager_pro/get_sdk_task_result/`，探针名称、全零占位文件哈希；HTTP 200，code 10320，数据不存在，SDK 返回 None | 查询链路可达；不等于有效硬件回包合同通过 |
| 网络边界 | 请求拦截器只放行上述查询 URL，其他 URL 抛错；20 秒超时 | 本次未触达创建接口 |
| 本地缓存 | 必须先设 `CheckpointManager.save_dir`；首次构造因未设目录失败，网络请求数为 0；设置独立空目录后查询成功 | 修正本地查询前置条件；两份记录均保留 |
| 采样参数 | 安装签名及 1.4.4 官方文档：sampling、sample_number=100；允许范围 10–2000 | 静态核实 |
| 任务身份 | 官方文档以 task_name + matrix 识别任务；改任一项形成新任务；project_no 是项目编号 | 静态核实，不能把项目编号当设备型号 |
| 剩余余额/到期日 | 用户提供基准 SPQC550 35 次、SPQC1000 2 次；本轮无创建，但未访问登录后配额看板 | **未核验实际余额**，不能声称余额未被其他端使用 |
| 上传失败扣费 | 官方平台指南明确“上传失败的任务不消耗配额” | 只覆盖上传失败；非 SDK 所有失败的统一豁免 |
| 提交失败/计算失败/pending 扣费 | 本次官方公开指南及 SDK 1.4.4 接口未提供足够事实 | **UNKNOWN**；需账户说明/账单或平台明确规则 |
| 排队量级/设备可用性 | 无真实任务，SDK 未公开只读队列/余额方法；公开页面无当前队列数 | **UNKNOWN**；不拿本次查询延迟当排队时间 |
| 调度到 SPQC550 | 105 自旋满足名义容量；实际资源绑定、采样配额换算尚无账户证据 | **UNKNOWN** |
| 缓存/回包/返回能量 | 本次不存在的探针没有结果，不可核实实际样本数、spin 轴、能量口径和缓存复用 | **UNKNOWN** |
| 提交门限 | 救援两配置均 COUNTEREXAMPLE | **FAIL：不得提交** |

没有可用的已登录云平台浏览器连接；SDK 的公开 CIM 类没有账户余额或队列列表接口。本次没有猜测接口路径、试探提交或把待核项当作通过。侦察兵可在登录控制台补录：设备类型/可用性、配额与到期日、sampling=100 的扣费单位、提交及计算失败扣费、当前队列状态。该信息即使补齐，也不能解除本次证书失败。

## 来源与适用边界

- [Kaiwu SDK 1.4.4 CIM API](https://kaiwu-sdk-docs.qboson.com/en/latest/source/modules/kaiwu.cim.html)，访问 2026-11-28：构造参数、缓存前置条件、任务身份和查询 API。
- [官方云平台使用指南](https://kaiwu.qboson.com/docs/usingPlatform.html)，访问 2026-11-28：“控制台”配额字段、“上传任务数据”上传失败不扣费、“确认提交后不可终止”。文内同时残留不同容量描述，不能据其泛化本账户当前扣费合同。
- [官方云平台服务链路指南](https://kaiwu.qboson.com/docs/serviceChain.html)，访问 2026-11-28：排队/系统占用/回传分离，sampling 与 optimization 的不同资源单位；没有本账户实时余额和队列。

原始脱敏记录：`artifacts/p2_rescue1/account_probe.json`、`account_probe_query.json`。没有保存用户 ID、SDK code、Authorization 内容或许可证正文。
