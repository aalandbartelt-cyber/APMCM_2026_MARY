# P2 A–H 原文阅读与决策证据索引

本表是研究记录，不是论文参考文献表。页码默认指仓库 PDF 的**物理页**；SDK 另列印刷页，避免三页前置造成错位。文本逐页提取至 `artifacts/p2_research_20261128/texts/`；来源路径、SHA256 和页数在 `source_manifest.json`、`new_sources_manifest.json`、`extra_sources_E/*manifest.json`。本表替代早期笔记中“尚未读完”的运行中状态；原笔记不删。

| 原文与覆盖 | 精确定位 | 改变的决策与不能外推之处 |
|---|---|---|
| Kaiwu SDK1.4.4 汇编164页；本任务相关章完整读 | TSP/真机物理19–32；精度34–45=印刷31–42；CIM物理52–57；preprocess100–113附近=印刷97起 | 最终Ising及参考边必须一起验位宽；精确同比例缩放不等于扩展精度；mutate不是PrecisionReducer默认流程；split量化及副本恢复必须单独认证；task_name+matrix决定任务身份 |
| Radons, arXiv2611.34168，42页全文 | §4.2 p11–13 IEM；§4.3 p13–14 BCE；§4.4 p15 ALM；§5.4.2 p21–22；§6、§7至p34 | 大罚导致业务信息丢失有直接前例；辅助编码与约束中心调整需区分；表示改进不保证采样；旧shift/row-column/mutate不能冒充其新方法或声称first |
| Wei, Light: Science & Applications2026，13页全文 | 主文硬件图、Results、Methods及补充说明引用 | MFB/FPGA和稳定化可作为架构来源；100计算自旋原型不是云550/1000合同；其benchmark不直接支持本题或量子优势 |
| Kitai2020 FMQA，10页全文 | p3结构化表示；p4采样/重复点；p5成本分解；p7未合成 | 允许字典编码有应用范式来源；训练、搜索、物理评价拆账；本题已经完整查表，不能移植指数黑箱搜索加速叙事 |
| 队友#8 Unbalanced penalization，14页全文 | 数学定义、参数选择、硬件实验全文 | 不对称罚允许业务最优不在基态，适用于探索性采样但不能解除G1/G2；调参可能利用已知最优 |
| 队友#9 Improving Performance，8页全文 | p5 COBYLA每次5000样本调罚；p7原LP对照 | 硬件调罚不免费；强制QUBO的成本与原问题求解难度分开 |
| 队友#10 Mirkarimi，32页全文 | p8–9线性罚边界；p15筛除1406/10000；p18多约束6066/10000；p19–22条件可行分析；p30–32调罚 | 不把条件质量当端到端成功；精确求解器平均约13次成本要计；D-Wave嵌入收益不自动迁移全连接CIM |
| 队友#11 Djidjev，22页全文 | ALM数学节；p11无解替代值；p12 HUBO/QUBO；后续修复 | 迭代更新并非一次冻结；其无可行返回处理与本任务不同；HUBO-SA直接高阶和QA降阶存在表示混杂 |
| 队友#12 量子组合优化算法研究进展，16页全文 | p11评价口径；p13–15文献表；p16英文摘要 | 用作方法导航与benchmark局限提示；综述的广义NP-hard措辞不能套到本题易枚举表；不是不可能性或速度保证的证明来源 |
| 队友#13 Kim，8页全文 | Methods p5：1000reads×1000sweeps；p6计时与best-known | QPU access不含队列通信；best-known非已证最优；HQA内部经典机制不公开；目标比值依赖零点 |
| 队友#14 D-Wave Problem Formulation Guide，26页全文 | §4.3（印刷p14–17）与小真值表建模例 | 常数、符号、双计数须显式核对；启发式调罚建议不是本任务额外扫描授权；保持枚举/原目标基线 |
| 队友#16 Shibata正文9页、#17 SI9页，正文和SI所有表全文读取 | 正文p6–8；SI S1–S2描述符、S3–S4的86氧化物 | 仅支持材料特征动机；58描述符、纯氧化物并非LaTiO2N实证；光谱窗口使带隙口径变化；LaCrO3数值与“误差均≤.2”文字不一致；SI图像未逐图目视，不能宣称已做图像审计 |
| Perplexity四/五/六轮审定版，三份全文 | 各版红线、表征/搜索、线性罚与基准节 | 导航与审阅约束；数学及硬件主张仍回原文和独立计算，不当独立实验数据 |
| Chancellor, arXiv1903.05068v4，18页全文含附录 | §II–X、附录；开头p1–2已补齐 | domain-wall为已有思想；稀疏QA嵌入优势不代表SPQC保证；使用联合候选字典时需新的decode合同 |
| Mücke, arXiv2307.02195v1，30页全文 | 动态范围定义、保最优压缩定理、算法及附录 | DR是系数距离比的log2，不是简单max/min非零值；保某原最优与排除所有错误新基态不同；记录v1，不能把期刊版本细节混入 |
| Gerlach, arXiv2409.10863v2，11页全文 | §IV p3已知解构造；TableI | 压缩后采样可变差（BINCLUS、SUBSUM）；已知最优可构造简单保解矩阵不等于求解；不采用依赖零点的能量比 |
| Chen, arXiv2102.12224v2，16页全文 | §II.B；§III p6–7；p9–13 | 分开物理链断裂、编码非法、目标质量；majority vote能改结论，必须另列；无势链硬件分布也非均匀；逐项降阶位数不是普适最小辅助位下界 |
| Berwald, arXiv2108.12004v4，20页全文 | §III自由度界；p14–15实验 | 一般DQM/多变量下界不能搬到本题特殊2变量表；10个embedding×10000reads仍有全零成功；热模型解释不是CIM实测 |
| Bennett, arXiv2206.02545v2，15页全文 | p2边界；Fig6；p9误差相关；p11–12 | 5–9自旋、三副本“至少一正确”改善不是全部基态保证；连接也可破坏原成功例；“额外bit”是曲线拟合而非真实位宽；未测试真实QA动力学 |
| Ohno, arXiv2604.03546v1，21页全文 | §III p4–6；§V p7；p9；p11；p15–18 | ALM中心移位在ε<.5范围最多减半空选罚且削弱多选罚；majority修复和正能量截0不能照搬；平均能量改善可与popt下降并存；嵌入SA也复现失败，不能归因为量子与经典差异 |
| Zeng, arXiv2601.11491v2，11页全文 | §III.B p4；§IV.A p5–6；§IV.B p7；§V p8–9 | 加µbΣx只在可行基数上为常数，未给G1；三种舍入及多次原目标择优成本要公开；分解是启发式；TTS95几何假设不一定适合多阶段；引出E01固定随机舍入反证审计 |

## 在线原始来源核验（2026-11-28）

- [SDK参数精度](https://kaiwu-sdk-docs.qboson.com/zh/latest/source/advanced/precision.html)：当前在线版本标签不总与安装版一致，技术细节以冻结1.4.4汇编和安装签名为主。
- [官方采样精度策略](https://kaiwu.qboson.com/docs/sample.html)：明确标准8-bit预处理，并说明更高精度可另行申请；未核实本账户服务权限，不能声称没有此类服务。
- [官方CIM架构概览](https://kaiwu.qboson.com/docs/cim.html)：公开550/1000容量及MFB流程，不把宣传性的普遍加速/必达最优文字当科学保证。
- [官方FAQ](https://kaiwu.qboson.com/docs/FAQ.html)：PrecisionReducer与mutate角色分开；其“QUBO和Ising均8精度”简述不能覆盖汇编“检查最终Ising”的明确解释。
- [Chancellor](https://arxiv.org/abs/1903.05068)、[Mücke](https://arxiv.org/abs/2307.02195)、[Gerlach](https://arxiv.org/abs/2409.10863)、[Chen](https://arxiv.org/abs/2102.12224)、[Berwald](https://arxiv.org/abs/2108.12004)、[Bennett](https://arxiv.org/abs/2206.02545)、[Ohno](https://arxiv.org/abs/2604.03546)、[Zeng](https://arxiv.org/abs/2601.11491)：下载的PDF版本/hash与上述manifest绑定，不靠搜索摘要裁决。

## 对侦察兵输入的处理

AGENT1 `q2.txt` 与 `p2.py` 只读、未导入拟合入口。前者SHA256为 `7bff75a097c1896f831da61040a8140eac6856579a12791cb1ba228d5d85dae8`。其Q层DR、最终Ising位宽、允许态最优、非法态和重启独立性分别核查；不把其结论直接当作本代理表结果。详见 `agent1_source_audit.json`、`sdk_probes/results.json`。
