# CURSOR_HANDOFF

## 最新交付：P1 收尾加固四项完成（2026-11-27）

- 用户目标限定 P0-1–P0-4，明确禁止模型再搜索。本轮全为既有表后处理；树、标量校准、Ridge 新拟合均为 0。总账仍 914，86 次余额全部保留给 P23 确定性重训。
- `report.py` 配对 AB bootstrap 已改为固定外折内分别取 Top-20 后宏平均 EF；旧 pooled 文件字节保留，并在并列表中单列诊断。H-soft − R-log 的主 EF 差 +1.6160，95% 区间 [−5.9951, 11.2022]，仍跨零。
- 四池 07/08/11/12 已补名义候选 rank 范围、Top-5/20 频率、双向 regret 分位数、成员最优—次优间隔与元素家族集中度。regret 并非都极小，未达到登记的近优平台标准；不能仅凭身份轮换称为失控。
- 主表已纳入原有加性 Ridge、均值、固定随机基线：13 行汇总、65 行逐折 N/M/h 与嵌套身份。原八候选点估计及 03 决策未变。
- 使用原 20 张表完成固定 1000 个 10/10 split-half。P23 构造冻结为 `bagged_mean_20`；只据决策稳定性，不看 EF/RMSE。11/12 池均值表 argmin 一致率仍仅 19.2%/17.4%，不能称最优身份稳定。
- `codex/P1_PLANv2.md` §6 写死 P23 配方，原训练前方案存 `codex/P1_PLANv2.1_FROZEN.md` 并匹配原始冻结哈希。未来 02+03、同 H-soft/F3+E1、20 固定 bootstrap、先形成完整成员 Vhat 再等权平均；预计 65 次树拟合，余 21 次只留同配方故障恢复。**本轮未执行 P23 重训/求解或真机。**
- 收尾报告：`codex/P1_HARDENING_REPORT.md`；全部统计和构造冻结：`artifacts/p1_v21/hardening/`。7 项数值测试通过；收尾审计核对 2630 个受保护文件、独立重算 5000 次区间；原 P1 审计仍通过 73 划分、911 模型来源及独立推断。回执：`hardening/hardening_audit.json`、`final_audit.json`。
- 当前仅可按 README 的 postprocessing 命令复算；不运行历史训练入口，不改冻结表，不以新增统计结果重开 03 选模。下方为此前交付记录。

## 最新交付：P1 v2.1 已完成（2026-11-26）

- 用户已审议并明确授权：修订五项要求后直接实施 P1，无需二次确认。当前已退出 Plan Mode；下方“待确认/不训练”为历史停止点。
- 主方案：`codex/P1_PLANv2.md`（正文 v2.1）；代码：`03_求解/D/p1_v2/`；实验产物：`artifacts/p1_v21/`。拟合预算 992，硬上限 1000，失败尝试计数。
- 02 拟合、03 最多三冻结候选开发选择、04 最终推断。防泄漏与历史暴露声明继续有效。不新做 P2/P3 求解、不提交真机、不改正式论文/交付件、不委派子智能体。
- Python 固定 `/usr/bin/python3.10`。LightGBM 3.3.5 仅在实验目录隔离构建 Query 长度上限补丁，不升级现有安装。
- P1 已完整执行，914 次拟合尝试（911 个实际 P1 树模型、2 次库验收、1 次兼容性失败）。73 个划分、911 个模型训练来源、独立 04 推断、模型/特征/数据哈希与显式候选 mask 均通过；不再扩展搜索。
- 最终数值与筛选均选 H-soft。03 RMSE=4.578330268；H-soft/B-eps 均命中 13/20 个 V<=2 近正例，EF=62.92317073；H-soft 依预登记 NDCG 并列规则胜出。04 共 3703 行已预测，无隐藏真值，不能声称 V=0 命中。
- 正式本轮报告：`codex/P1_RESULTS_v2.1.md`；主表：`codex/P1_FINAL_RESULTS_v2.1.csv`。全实验、模型卡、审计和预测：`artifacts/p1_v21/`；复现入口：`03_求解/D/p1_v2/README.md`。
- 特别限制：H-soft 数值改善有配对证据，但相对 R-log 的筛选 EF 区间跨零；04 名义最优在 20 个 bootstrap 中仅保持 4 次。压力测试固定 R-log/S-eps，不冒称最终 H-soft 的直接域外验证。
- P2/P3 输入表含显式 allowed mask，全部标 `P1_train02`；后续 02+03 重训及 3x104/208/HOBO 同表求解未执行。下方为历史复核证据。

## 最新接手：WSL 主力 Codex · D 题独立复核（2026-11-26）

- 本次用户已明确移交 D 题给 Codex；下方旧“建议 C / 题号待定”为历史记录，不代表本轮任务。
- 当前分支 `codex/d-independent-review`，接手时的未提交改动均保留，没有恢复其他智能体线程或启用子智能体。
- 用户授权范围：按序通读交接、独立读题、系统学习资料库、复核旧资产，产出复核报告和 P1 方法设计；交付后待命。
- 禁止越界：未确认不做新 P1 实现；不推进 P2/P3 新求解；不生成正式 holdout 预测；不提交任何真机任务；不改正式论文和交付件。
- 已完成/下一步/真实阅读覆盖见 `docs/review/CODEX_D_REVIEW_PROGRESS.md`；独立题面理解已单独冻结在 `docs/review/CODEX_D_独立题面理解.md`。
- 本轮四阶段已完成。根目录交付 `CODEX_D_独立复核报告.md`、`CODEX_D_P1_方法论方案_待确认.md`；**方案待用户确认，增强 P1 / 04 正式预测 / 新 P2/P3 / 真机均未启动**。
- 资料库初盘961、新增SDK汇编后962文件全部分类处置：19 篇独立相关主论文全文、其余24篇摘要/结论、2重复、2身份错配排除；官方层/开源/优秀论文/往届题有逐文件真实覆盖，不能声称全部全文。阅读台账和详细限制见 progress 与报告。
- 旧 P1 隔离重放：模型、元素表、特征重要性与旧资产逐字节一致；fold2 错误分析已补。公开9项哈希、已有P2/P3矩阵的可行态恒等式独立通过；未运行这些问的求解入口。原 `verify_data.py` 含切分逆推/宿主输出，禁止直接重跑，替代为本轮安全审计。
- 核验脚本/证据：`docs/review/{replay_scout_p1,diagnose_scout_p1,audit_scout_assets}.py`；`artifacts/codex_review/`（ignored）。最终检查与镜像见 `docs/review/CODEX_D_FINAL_CHECKS.md`。
- 用户增补的Kaiwu SDK1.4.4汇编164页正文全文已读，关键4页视觉核对，R0962；优先于旧HTML。自动罚系数同源/调用链、Reducer第4组合方案、var/item映射、默认值和interval单位见 `docs/review/CODEX_D_Kaiwu144_增补复核.md`。仅静态阅读，无SDK执行。
- 执行旧代码时指定 `/usr/bin/python3.10`；当前默认 `python` 为 conda 3.13.12，不沿用交接中的默认解释器假设。

---

> 更新：2026-11-26。选题分析已写完，题号未锁定。Cursor 仍是 Codex 平替。

## 当前状态

- 工作区：`~/apmcm2026`
- 赛事：APMCM 2026（第十六届）
- 开赛：2026-11-26 06:00 — 2026-11-30 09:00（北京时间）
- 题号：TBD（A / B / C / D，只能选一个）
- 队号：apmcm26XXXXX（报名后填）
- 分支：`cursor/standby-takeover`（从 `main` `89350ab` 切出；不直接改 `main`）
- 阶段：赛题已发布。四题分析在 `docs/analysis/2026_选题分析.md`。按数据处理长处改为建议选 C；题号等用户确认后再写入赛事参数。
- 角色：用户指定 Cursor 作为 Codex 平替。建模、代码、结果、图表、论文候选由当前主智能体写。正式件在 `05_论文/正式/`、`06_交付/`，需用户明确授权后才写。

## 已完成

- 目录骨架、README、AGENTS、Git 规范、写作/图表规范、提交清单、赛事参数骨架。
- APMCM skill 已同步到 `~/.codex/skills/mary-modeling-contest-pipeline-apmcm`（含 references 09—22）。
- 2026-11-26 同一份 skill 已安装到 Cursor 个人 skill：`skills/mary-modeling-contest-pipeline-apmcm/`（用户存储，54 个文件，与 Codex 副本逐文件一致）。Cursor 侧入口读这份；Codex 路径仍是源头副本。
- 2026-11-26 赛题分析：A 的 tar、B 的 7z 已在官方目录解开；C、D 原就是表。核对记录在 `docs/analysis/2026_选题分析.md`。
- 建议选 C。深入分析在 `docs/analysis/C_赛题分析.md`。关键口径：90/139 对回放距离不对齐；三种相关不能直接平均；附件没做潜伏期和阈值距离。

## 下一步

1. 用户确认 C 后，写入赛事参数和 `decisions.md`，建 `03_求解/C/`。
2. 开工先落数据审计：缺失规则、配对距离差、传播表有效样本量。附件 brms 和 GAM 只作基线。
3. 队号仍缺，页眉和文件名不能定稿。

## 不能动的东西

- `05_论文/正式/`、`06_交付/`：未经用户明确授权不写。
- 不提交赛题原始数据、参考 PDF、control sheet、密钥、个人信息。
- 不把另一赛事的页数/页眉/AIGC 阈值/AI 报告模板套到 APMCM。
- 不恢复 Codex 旧对话线程；上下文只从仓库文件补。

## 验证命令

```bash
cd ~/apmcm2026
git status --short --branch
python ~/.codex/skills/mary-modeling-contest-pipeline-apmcm/scripts/env_doctor.py --project .
python ~/.codex/skills/mary-modeling-contest-pipeline-apmcm/scripts/audit_git_hygiene.py --root .
```

## 风险/待核

- 队号、题号未定；文件名和页眉不能最终生成。
- 2026 官方页数/页眉/AI 要求以 `00_赛题与规则/官方发布/` 原件为准，skill 只作流程提炼。
- 支撑材料是否提交，等题面是否明确要求。
- 本次接手只更新交接记录，尚未跑 env_doctor / git hygiene。
