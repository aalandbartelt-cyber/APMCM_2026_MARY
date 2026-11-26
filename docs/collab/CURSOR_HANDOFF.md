# CURSOR_HANDOFF

## 最新接手：WSL 主力 Codex · D 题独立复核（2026-11-26）

- 本次用户已明确移交 D 题给 Codex；下方旧“建议 C / 题号待定”为历史记录，不代表本轮任务。
- 当前分支 `codex/d-independent-review`，接手时的未提交改动均保留，没有恢复其他智能体线程或启用子智能体。
- 用户授权范围：按序通读交接、独立读题、系统学习资料库、复核旧资产，产出复核报告和 P1 方法设计；交付后待命。
- 禁止越界：未确认不做新 P1 实现；不推进 P2/P3 新求解；不生成正式 holdout 预测；不提交任何真机任务；不改正式论文和交付件。
- 已完成/下一步/真实阅读覆盖见 `docs/review/CODEX_D_REVIEW_PROGRESS.md`；独立题面理解已单独冻结在 `docs/review/CODEX_D_独立题面理解.md`。
- 阅读增量：11 份独立核心原文全文文本已读，核心卡已写；当前 R0917 只读至 490 行，下一段从 491 开始，不能误标全文完成。资料库 961 文件仍有大量待系统阅读，尚未进入旧实验代码复核阶段。
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
