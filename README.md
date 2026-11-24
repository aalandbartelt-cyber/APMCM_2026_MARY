# APMCM 2026 · MARY 比赛仓库

2026 年第十六届 APMCM 亚太地区大学生数学建模竞赛（英文，A—D 任选一题）的比赛工作区。

> 这是公开仓库：不要提交赛题原始数据、参考论文 PDF、承诺书/control sheet 扫描件、密钥、个人信息或本机绝对路径。
> 队号/题号在报名后填入 `00_赛题与规则/赛事参数.md`；当前用 `apmcm26XXXXX` / `TBD` 占位。

## 关键信息

- 比赛：APMCM 2026（第十六届）
- 时间：2026-11-26 06:00 — 2026-11-30 09:00（北京时间；以官方为准）
- 语言：English only；正文/图题/表题/图例/坐标轴不得出现中文
- 版式：p1 Summary；p2 Contents；正文 ≤25 页；附录不限；页眉 `Team #<team number> Page <x> of <y>`
- 提交：论文 PDF + control sheet 单独签名 + 支撑材料（可选，`.zip/.rar`）；如使用 AI，另提交 `AI工具使用详情.pdf`；未使用 AI 须在 References 后写官方中文声明
- AI：允许辅助，但核心模型构建、算法设计与求解、结果分析必须由队员独立完成；使用 AI 须正文标注 + References 工具条目 + `AI工具使用详情.pdf`；见 `02_口径与约定/AI工具使用规范.md`
- 技能：`mary-modeling-contest-pipeline-apmcm`
  - WSL：`~/.codex/skills/mary-modeling-contest-pipeline-apmcm/SKILL.md`
  - Windows：`C:\Users\mary3\.agents\skills\mary-modeling-contest-pipeline-apmcm\SKILL.md`

**不要把另一赛事的页数口径、页眉格式、AIGC 阈值或 AI 报告模板直接套到 APMCM。** 先读 APMCM skill 的 `references/01`、`09`—`16`。

## 环境与职责

| 角色 | 位置 | 职责 | 不做什么 |
|---|---|---|---|
| Codex | WSL | 默认主环境：建模/代码/结果/正式论文/正式包；`main` 集成 | 不替用户签名/上传 |
| Cursor | WSL | Codex 不可用时的备份主力；写 `cursor/` 分支与 `05_论文/待审/` | 默认不改 `05_论文/正式`、`06_交付` |
| ZCode | Windows | 数据、文档、复核、图稿候选、提交检查 | 不覆盖正式论文/交付件 |
| dsh / 外部评审 | Windows | 论文评审、文字优化、评分建议 | 不建模/不选型/不改正式件 |

- WSL 主路径：`~/apmcm2026`
- Windows 访问：`\\wsl.localhost\Ubuntu-22.04\home\mary\apmcm2026`
- GitHub：`https://github.com/aalandbartelt-cyber/APMCM_2026_MARY`

## 目录

```text
00_赛题与规则/      官方规则、模板、赛事参数；官方发布/ 不入库
01_参考学习/        参考论文/资料；默认不入库，仅 README 入库
02_口径与约定/      赛事参数、写作/图表/Git 规范
03_求解/            代码/结果/图源；选题后按题目建子目录
05_论文/待审/       候选稿、图源、编译脚本
05_论文/正式/       正式论文（仅主智能体/授权角色写）
06_交付/            最终 PDF/control sheet/支撑包/提交清单
docs/collab/        handoff、决策、评审
docs/analysis/      数据分析/图件设计记录
src/ scripts/ tests/ configs/   代码与实验
artifacts/          本地中间产物（gitignore）
```

## 先读

1. `AGENTS.md`（角色与边界）
2. `00_赛题与规则/赛事参数.md`
3. `02_口径与约定/写作与审稿规范.md`
4. `02_口径与约定/图表规范.md`
5. `02_口径与约定/Git规范.md`
6. `docs/collab/README.md` 与 `docs/collab/CURSOR_HANDOFF.md`
7. Skill 的 `SKILL.md`、`references/09`—`16`

## 快速命令

```bash
cd ~/apmcm2026
git pull --ff-only
python ~/.codex/skills/mary-modeling-contest-pipeline-apmcm/scripts/env_doctor.py --project .
python ~/.codex/skills/mary-modeling-contest-pipeline-apmcm/scripts/audit_git_hygiene.py --root .
```

## 提交

```bash
git switch -c codex/<problem>-<topic>
# 改动 + 证据
git add ...
git commit -m "feat(q1): ..."
git push -u origin codex/<problem>-<topic>
```

正式论文/正式包由主智能体合并到 `main`；不要直接改 `05_论文/正式`、`06_交付`，除非用户明确授权。

**不要提交**：赛题原始数据、参考 PDF、视频、模型权重、control sheet 扫描件、密钥、个人信息、`artifacts/`、`_archive/`、环境目录。
