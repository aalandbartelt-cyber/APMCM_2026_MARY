# APMCM Git 规范

> 公开仓库：不提交原始数据、参考 PDF、control sheet 扫描件、密钥、个人信息。
> 环境/代理细节见 skill `references/common/17_WSL_Windows环境与Git.md`；本文件是分支/提交/交接约定。

## 1. 分支

```text
main                  稳定可交付；只合并已验证内容
codex/<problem>-<topic> Codex 主工作分支
cursor/<problem>-<topic> Cursor 备份分支
zcode/<topic>          Windows 辅助/文档
review/<topic>         评审/评分报告，不改论文正文
```

- 一个分支只做一件事；不要混“改模型 + 改论文 + 改图”。
- 合并前同步 `main`，跑相关检查。
- 冲突保留双方内容，重新编号/重跑验证，不覆盖对方未合并工作。
- 不 force-push 共享分支。

## 2. Commit

```text
<type>(<scope>): <short imperative summary>
```

常用 type：`feat`、`fix`、`docs`、`fig`、`exp`、`chore`、`revert`。

示例：

```text
feat(q2): add matched-window baseline comparison
fix(data): correct environment grouping key
docs(paper): tighten summary and direct answers
fig(q3): redraw capacity tradeoff at final print size
```

- 一个 commit 一类变化；不要 `update`/`final`/`fix again`。
- 提交前 `git diff --stat`；不要把大文件/数据/PDF/密钥混入。

## 3. 路径所有权

- `05_论文/正式/`、`06_交付/`：主智能体/用户授权角色写；其他角色只写候选。
- `05_论文/待审/`：所有角色可写候选，但文件命名带日期/负责人。
- `03_求解/`、`src/`、`scripts/`：代码/结果；改动要能追溯到实验/命令。
- `docs/collab/`：handoff、决策、评审；不放大文件。

## 4. 不提交

- 赛题原始数据、参考 PDF、视频、模型权重；
- control sheet 扫描件/签名；
- `.env`、token、密钥、个人信息；
- `__pycache__`、`.venv`、`node_modules`、临时编译产物；
- 重复旧版本 PDF/zip。

## 5. 提交前

```bash
git status --short
git diff --stat
python ~/.codex/skills/mary-modeling-contest-pipeline-apmcm/scripts/audit_git_hygiene.py --root .
```

仓库未跟踪体积建议 <100 MB；正式交付物在 `06_交付/`。

## 6. 交接

每个 handoff 至少：

```text
# HANDOFF
- 当前状态/版本/hash：
- 已完成：
- 未完成/下一步：
- 关键文件/路径：
- 不能动的东西：
- 验证命令/预期结果：
- 风险/待核：
```

接手先读 `AGENTS.md`、skill、handoff、`git status`；不重做已完成部分。
