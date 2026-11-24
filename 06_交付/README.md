# 06 交付

最终提交件目录。APMCM 是三件分别上传：

```text
<题号><队号>.pdf            论文（只收 PDF；p1 Summary、p2 Contents）
<题号><队号>cns.pdf/jpg/png Control Sheet（单独签名；不进论文）
<题号><队号>fj.zip/rar      支撑材料（可选；≤20 MB 建议）
AI工具使用详情.pdf          使用 AI 时按官方要求提交；未使用则写官方中文声明
```

示例（队号报名后替换）：

```text
Aapmcm2600001.pdf
Aapmcm2600001cns.pdf
Aapmcm2600001fj.zip
```

## 规则

- 文件名前缀三件一致；不加空格/下划线。
- 论文 PDF 不含 control sheet；control sheet 不含在支撑包。
- 使用 AI：`AI工具使用详情.pdf` 必须包含工具/版本、用途/环节、关键提示与回复、采纳与人工修改；未使用 AI：References 后写官方原句 `本参赛队未使用任何AI工具`。
- 模板：`02_口径与约定/AI_Tool_Usage_Details_Template.docx`（English, 2 pages）；导出为官方要求的 AI usage details PDF 后放本目录。
- 支撑包不含赛题原始数据；附录仍须有软件名 + 全部源代码。
- 公开仓库不提交 `*cns.*` 和 `*fj.zip/rar`（已 gitignore）。
- 提交前逐件 SHA256/大小/页数记录；重传先删旧版对应项再传新版。

## 检查

见 `提交清单.md`；审计命令：

```bash
python ~/.codex/skills/mary-modeling-contest-pipeline-apmcm/scripts/audit_apmcm_submission.py \
  --paper Aapmcm2600001.pdf --control Aapmcm2600001cns.pdf --zip Aapmcm2600001fj.zip
```
