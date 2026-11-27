# APMCM 2026 D 官方模板骨架

队号已确认：`apmcm26301618`，题号 `D`。

当前 `main.pdf` 以官方 `APMCM LaTeX 模板/main.pdf` 为版式基准。官方 `.cls`、`.cfg` 已逐字节恢复；摘要的两行队号表、粗横线、标题、页边距、行距、罗马数字章标题、目录层级及 caption 均沿用官方设置。此前自定义版式已撤下，不作为交付版本。

只保留用户明确要求的队号与页眉文字配置：`Team Dapmcm26301618 Page X of 25`。正文在目录后从 1 重新编号；`of 25` 为用户指定的固定值，并非当前骨架 PDF 的物理页数。

## 文件结构

```text
main.tex / main.pdf             论文入口与编译证据
apmcmthesis.cls / .cfg           官方原样副本
config/identity.tex             D、apmcm26301618、页眉固定 25
config/layout.sty               页眉文字、引用、空节及插图辅助命令
sections/                      空节；不含撰写后的正文
references.bib                 空的正式参考文献库
examples/references_examples.bib Castelli 2012、Lucas 2014 格式示例
apmcm-h5.bst                    编号引用及 [J]/[M]/访问日期格式
source_manifest.csv            待填的完整源码清单
upstream/official/             官方模板原件的只读留档副本
upstream/apmcm_d_table_templates.tex  T1–T8 原始模板库留档
tables/T1_*.tex ... T8_*.tex    可填表模板；结果单元格全为空
examples/f1_smoke.tex           独立 F1 插图测试入口
examples/style_smoke.tex        独立表格、子图和引用格式测试
scripts/build.sh               XeLaTeX / BibTeX 全链路编译
verification/                  截图、编译与哈希检查记录
build/                         本地编译中间文件，不作交付包
```

## 编译

WSL 已安装用户目录 TeX Live 2026；没有改系统软件包或全局 PATH。

在本目录运行：

```bash
bash scripts/build.sh
bash scripts/build.sh f1_smoke
bash scripts/build.sh style_smoke
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3.10 -B scripts/verify_layout.py
```

`build.sh` 默认使用 `$HOME/.local/share/texlive/2026/bin/x86_64-linux`，可通过 `APMCM_TEXBIN` 指定现有安装。当前主文件链路为 XeLaTeX → BibTeX → XeLaTeX → XeLaTeX。官方示例的 PDF 元数据明确为 XeTeX，正文实际为 **Times New Roman 10.5 pt**，页眉 9 pt、章标题 15 pt。本版按用户后续“官方有的全部按官方”的要求原样复现，未自行改动这些设置。此前要求的 11/12 pt、pdfLaTeX 与这份官方示例存在差异；不能同时声称本版满足 11/12 pt。pdfLaTeX 链路曾编译通过，但其字体与官方 PDF 不同，因此不作为当前外观交付。

## 占位章节

- Summary：一行摘要占位、关键词占位。
- Contents：官方样式自动目录。
- Introduction：一行背景占位；Problem Restatement 中 Problem 1–4 各两行动作槽；Our Work 一行占位，页底保留框架位置。
- Assumptions / Notations / Data Audit and Problem Formulation：各一行。
- Model I (P1) / Model II (P2) / Model III (P3)：各一行。
- Model Evaluation / Conclusions：各一行。
- References：两条标明 verification pending 的格式示例；正式库为空。
- Appendix：Software Environment / Computer Source Code / AI Tool Disclosure / Citation Format Check，各一行。

软件清单、全部计算机源码和 AI 使用说明目前只有位置，尚未填充；这属于空模板，不声称已经完成论文内容或提交材料。

## 图件与表格

主文件恢复官方左右各 31.8 mm 的页边距、146.4 mm 版心，不再为插图改变整篇版式。此前要求的 170 mm F1 测试放在独立的 [f1_inclusion_smoke.pdf](verification/f1_inclusion_smoke.pdf)：只在该测试中将图宽设为 170 mm、以页心居中。原图 `figures/F1/F1_data_audit_v3.pdf` 原样引用；实际路径不是 `figures/P1/`。

`\PaperFigure` 默认使用官方版心宽度、caption 在下；`\PaperSubfigure` 提供 (a)(b) 子图。将来若图宽改变，须重新检查印刷字号，不能直接将已经验收的 170 mm 图缩小后宣称仍符合字号要求。

T1–T8 由指定 skill 模板库对接，保留 booktabs 结构；官方表题样式不改。模板中的示例 Y/0/1.0、示例结果判断均清空，不把示例当作实测数据。表格未插入 `main.pdf`。

## 参考文献

正文多项引用输出 `[1][2]`，不合并为区间。期刊采用“著者. 文题[J]. 刊名. 年. 卷. 页码”，书籍含 `[M]`、出版社和引用页码，网络资源必须填 `urldate`。BibTeX 对缺少关键字段输出警告。

两条示例与正式空库隔离，并标注待核验：

- [Castelli et al. (2012), RSC 出版页](https://pubs.rsc.org/en/content/articlehtml/2012/ee/c2ee22341d)：9034–9043，DOI `10.1039/C2EE22341D`。
- [Lucas (2014), Frontiers 出版页](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00005/full)：卷 2，文章号 5；以 Article 5 表示电子定位号，没有伪造起止页码。

出版元数据已经查对；纳入正式论文前仍需核验正文用途。`examples/style_fixtures.bib` 的书籍/网页条目仅为明确标记的虚构格式测试，不进入正式文献库。

## 最终提交前的内容工作

英文正文、摘要、正式引用、软件名称、全部源码、AI 披露正文标注/工具参考条目/独立 `AI工具使用详情.pdf` 均须在后续写作阶段完成。Control Sheet 保持独立，不进入论文 PDF。

终态文件名仅登记，当前未生成提交包：`Dapmcm26301618.pdf`、`Dapmcm26301618cns.pdf`、`Dapmcm26301618fj.zip`。

官方原件、模型、数据、拟合账本与原图均受哈希检查保护；本轮没有新拟合，也没有撰写正文。
