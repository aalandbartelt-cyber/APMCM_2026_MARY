# CURSOR_HANDOFF

> 更新：2026-11-24 初始化；之后每次接手/交付更新本文件。

## 当前状态

- 工作区：`~/apmcm2026`
- 赛事：APMCM 2026（第十六届）
- 题号：TBD
- 队号：apmcm26XXXXX（报名后填）
- 阶段：仓库初始化，未开赛；官方规则/模板待放入 `00_赛题与规则/官方发布/`（gitignore）。
- 正式论文/交付件：尚未开始。

## 已完成

- 目录骨架、README、AGENTS、Git 规范、写作/图表规范、提交清单。
- APMCM skill 已由 Devin 优化并同步到 `~/.codex/skills/mary-modeling-contest-pipeline-apmcm`（commit `7a4a375`，含 09—22 深度参考；新增 17 在线信息约束/盲测、18 C 题逐页、19 获奖论文追踪、20 建模叙事、21 自有论文蒸馏、22 摘要解剖；指标脚本 v2）。

## 下一步

1. 报名后填 `00_赛题与规则/赛事参数.md` 的队号/题号/截止。
2. 下载官方规则/模板/control sheet 到 `00_赛题与规则/官方发布/`（不入库）。
3. 读 skill `references/01`、`09`、`10`；确认 APMCM 页数/页眉/AI 要求。
4. 开赛后选题，建 `03_求解/<题号>/`。
5. 建 `key_numbers.csv`、`terminology.md`、图件清单。

## 不能动的东西

- `05_论文/正式/`、`06_交付/`：默认只由主智能体/授权角色写。
- 不提交赛题原始数据、参考 PDF、control sheet、密钥、个人信息。
- 不把另一赛事的页数/页眉/AIGC 阈值/AI 报告模板套到 APMCM。

## 验证命令

```bash
cd ~/apmcm2026
git status --short --branch
python ~/.codex/skills/mary-modeling-contest-pipeline-apmcm/scripts/env_doctor.py --project .
python ~/.codex/skills/mary-modeling-contest-pipeline-apmcm/scripts/audit_git_hygiene.py --root .
```

## 风险/待核

- 2026 APMCM 官方页数/页眉/AI 要求需按当届原件复核。
- 队号/题号未定，文件名/页眉暂不能最终生成。
- 支撑材料是否提交待定。
