# 00 赛题与规则

放置 APMCM 2026 官方规则、论文格式规范、LaTeX/Word 模板、control sheet 模板和正式赛题。

## 重要

- 官方发布/赛题原始数据放在 `官方发布/`，该目录已 gitignore，不进入公开仓库。
- 大文件/压缩包/参考 PDF 不要提交；只在 README 记录文件名、版本、获取日期。
- 队号/题号在报名后填入 `赛事参数.md`；不要把个人信息写进论文或公开仓库。

## 已放入（2026-11-25 更新）

```text
官方发布/2026论文规范与模板/
  2026 APMCM Essay format and submission specifications.pdf   官方格式规范（2 页，2026.11）
  2026 APMCM Summary Sheet.docx                               p1 Summary + p2 Contents
  2026 APMCM Control Sheet.docx                               单独一页承诺书
  APMCM LaTeX 模板/                                            cls/cfg/main.tex/ControlSheet.tex + 示例 PDF
  README_官方发布说明.md                                        通知原文 + 硬规则提取 + 模板实测
官方发布/_archives/2026 APMCM 论文提交规范、论文模板、承诺书.zip
```

## 2026 赛题（2026-11-26 发布，已入库）

```text
官方发布/2026赛题/
  2026 APMCM Problem A/  题面 PDF + Attachment 1 Model Training Dataset.tar（397 MB）
  2026 APMCM Problem B/  题面 PDF + Data.7z（106 MB，10 炉次光谱/烟气/氧枪）
  2026 APMCM Problem C/  题面 PDF + date/（R 代码 2 份、CSV 10 组、补充 PDF 5 份、回放视频、3 段 wav）
  2026 APMCM Problem D/  题面 PDF + date/（训练/验证/盲测/候选池 CSV、数据说明、sha256）
官方发布/2026论文规范与模板/2026年第十六届APMCM…参赛纪律和论文提交方式说明.pdf
```

四题主题：A 洪水灾害评估与应急救援优化（图像识别）；B 转炉炼钢双模态时序融合；C 非洲企鹅声通信与回放响应；D 量子计算机钙钛矿稀有目标搜索。题面画像与选题建议见 skill `references/03_四题路线与选题.md` 3.1.1。

> 纪律新红线（2026-11-26 说明）：自建库查重相似度 >30% 判作弊、取消资格；摘要/正文出现个人信息最高只获成功参赛奖；承诺书英文签名；提前 30–60 分钟提交；重传须点“提交电子档”。

> 2026-11 官方新规要点：论文 `#***.pdf`；承诺书 `#***cns.pdf/.jpg` 单独一页三人签名；支撑材料 `#***fj.rar/.zip` 且**题面未明确要求不要提交**；p1 Summary、p2 Contents；正文 ≤25 页；页眉只含队号+页码；格式不合规无条件取消资格。详见 skill `references/01_APMCM赛制与提交.md`。

## 2026-11-24 已放入

```text
官方发布/2026年第十六届APMCM...参赛规则.pdf
官方发布/2026_AI工具使用规定.md
官方发布/2026规则页图/rule_2026_p1—p6.png
官方发布/2025论文规范与模板/
  2025 APMCM Essay format and submission specifications.pdf
  2025 APMCM Summary Sheet.docx
  2025 APMCM Control Sheet.docx
  APMCM LaTex模板.zip
  APMCM LaTeX 模板/（cls/cfg/guide/ControlSheet/main.tex 等）
官方发布/_archives/2025 APMCM 论文提交规范、论文模板、承诺书.zip
```

这些文件在 `官方发布/` 下，整目录 gitignore，不进入公开仓库。

## 建议文件

```text
赛事参数.md                 本队参数、题号、页数/页眉口径
官方发布/                   官方规则/模板/赛题（gitignore）
  2026_APMCM_Rules.pdf
  2026_APMCM_Format.pdf
  LaTeX_Template.zip
  Control_Sheet.pdf
```

## 先读

- APMCM skill `references/01_APMCM赛制与提交.md`
- `02_口径与约定/写作与审稿规范.md`
- `02_口径与约定/图表规范.md`
