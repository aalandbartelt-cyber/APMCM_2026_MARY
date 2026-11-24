# Agent Instructions — APMCM 2026

本仓库是 2026 APMCM 亚太杯英文赛工作区。所有 AI Agent 先读本文件，再读指定 skill，再动文件。

## 默认执行约定

- 默认由当前主智能体独立完成；不要自动创建、恢复或委派子智能体，不要运行多 Agent 编排器。
- 只有用户明确要求，才开启并行/多智能体。
- 正式论文/正式图/交付包默认只由主智能体写；其他角色只写候选/评审/辅助文件。

## 角色

| 角色 | 位置 | 职责 |
|---|---|---|
| **Codex** | WSL | 默认主环境：建模、代码、结果、正式论文/包、`main` 集成 |
| **Cursor** | WSL | Codex 无额度/不可用时的备份主力：接手建模/代码/结果/图表/论文候选；写 `cursor/` 分支与 `05_论文/待审/` |
| **ZCode** | Windows | 辅助：数据、文档、复核、图稿候选、提交检查 |
| **dsh / 外部评审** | Windows | 论文评审/文字优化/评分建议；写 `docs/collab/reviews/` |

## 必读 skill

```text
/home/mary/.codex/skills/mary-modeling-contest-pipeline-apmcm/SKILL.md
```

再按任务读：

```text
references/01  赛制与提交
references/02  英文论文结构与写作（快表）
references/09  写作与审稿项目规范
references/10  图表与排版项目规范
references/11  验证与结果叙事
references/12  AI 工具与学术诚信（条件性）
references/13  评分与专家评阅
references/14  协作与 Git 规范
references/15  附录、支撑材料与复现
references/16  数据与业务题实战
```

Cursor 不自动加载 Codex skill；必须显式读上述路径。项目规则见 `.cursor/rules/apmcm.mdc`。

## 论文与图表任务必读

写作、绘图、整合或审稿前，读取：

- [写作与审稿规范](02_口径与约定/写作与审稿规范.md)
- [图表规范](02_口径与约定/图表规范.md)

这两份是**本比赛**的项目级规范；与 skill 的快速表冲突时，以 APMCM 官方规则 + 这两份项目规范为准。

## APMCM 硬边界

- 英文-only；正文/图题/表题/图例/坐标轴不得出现中文。
- p1 Summary；p2 Contents；正文 ≤25 页；附录不限；页眉 `Team #<team number> Page <x> of <y>`。
- Control Sheet 单独签名提交，**不进论文 PDF**。
- 论文/图表/代码/PDF 元数据不得出现姓名、学校、指导教师、邮箱。
- AI：APMCM 2026-11 官方规定；允许辅助，但核心模型构建、算法设计与求解、结果分析必须由队员独立完成；使用 AI 须正文标注 + References 工具条目 + `AI工具使用详情.pdf`；未使用须写官方中文声明。见 `02_口径与约定/AI工具使用规范.md`。
- **不要把另一赛事的页数口径、页眉格式、AIGC 阈值或 AI 报告模板直接套到 APMCM。**

## 数据与安全

- 原始数据/参考 PDF/大文件放 `00_赛题与规则/官方发布/`、`01_参考学习/` 或 D 盘；默认 gitignore。
- 不提交密钥、token、个人信息、control sheet 扫描件。
- 不改 `05_论文/正式`、`06_交付` 的正式件，除非用户明确授权。
- 提交前跑：

```bash
python ~/.codex/skills/mary-modeling-contest-pipeline-apmcm/scripts/audit_git_hygiene.py --root .
python ~/.codex/skills/mary-modeling-contest-pipeline-apmcm/scripts/env_doctor.py --project .
```

## 交接

- 跨 Agent 交接只写文件，不依赖对话上下文。
- 每次接手/交付更新 `docs/collab/CURSOR_HANDOFF.md`。
- 接手先读 `AGENTS.md`、skill、handoff、`git status --short --branch`。
- 不重做已完成部分；不恢复别人的对话线程。
- 冲突时保留双方内容，重新编号/重跑测试，不覆盖对方未合并工作。
