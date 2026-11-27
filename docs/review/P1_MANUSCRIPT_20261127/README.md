# P1 论文稿与验收记录（2026-11-27）

当前唯一论文入口为项目内 `00_赛题与规则/官方发布/2026论文规范与模板/APMCM LaTeX 模板/main.tex`，对应 PDF 为同目录 `main.pdf`。已删除的 `05_论文/待审/APMCM2026_D_template_20261127_codex/` 不恢复。

当前最新版为修订 02：43 项检查通过、目录 40/40 目标正确；新增紧凑三节点流程图已入正文 Figure 2，等待用户审阅。

## 本轮范围

- 完成简短全局前置部分中与 P1 有关的内容、P1 正文、4 条实际引用文献、附录 B 的 P1 补充图表。
- Summary、P2/P3、综合评价、Conclusion、AI 披露暂不填写。附录 A 仅支撑材料目录框架，附录 C 仅分问源码框架。
- 学习用户数维杯的内容层次、短段与图表衔接；保留亚太杯官方字体、字号、版心、标题、目录和 caption 样式。官方 `.cls/.cfg` 未改。
- 既有 P1 结果、模型、数据、拟合账本与图件只读。没有新拟合、模型重选或 P2/P3 求解。

## 编译

在官方模板目录执行两次（交叉引用变更时执行第三次）：

```bash
/home/mary/.local/share/texlive/2026/bin/x86_64-linux/xelatex -interaction=nonstopmode -halt-on-error main.tex
```

采用官方 PDF 原有 XeTeX/Times New Roman 分支，不替换为其他字体。模板新增的 `placeins`、`threeparttable`、`float` 仅用于图表就近放置和左对齐表注；没有重定义官方排版尺寸。缺失包已装入用户自己的 TeX Live 2026。修订 02 增加隐形超链接，并兼容当前 LaTeX 内核与 titlesec 的标题锚点；不改变目录显示形式。

## 文件说明

| 文件 | 用途 |
|---|---|
| `official_original/` | 撰稿前官方 main.tex/main.pdf 备份，用于形式对照 |
| `build_tables.py` | 只读既有 CSV，生成 11 张数值表的 LaTeX |
| `table_source_map.json` | 表格单元格、来源和生成文件哈希 |
| `verify_manuscript.py` | 数值口径、引用、官方字体、PDF、受保护文件检查 |
| `verification.json` | 本次最终自动检查结果及 PDF SHA-256 |
| `SOURCE_MAP.md` | 正文数字、图件、方法与文献的来源映射 |
| `REVIEW.md` | 页面检查及用户反馈落实记录 |
| `revision_02/preview_final/` | 当前 22 页逐页渲染和 6 张接触表 |
| `revision_02/navigation_check.json` | 40 个目录目标与实际标题页逐项核对 |
| `revision_02/REVIEW.md` | 五项修订、流程图简化与 humanizer 覆盖记录 |
| `preview_checked/` | 上一轮稿件截图，已被 revision_02 取代 |
| `preview/`、`preview_final/` | 中间检查截图，非最终成稿依据 |
| `revision_02/compile_12.txt` | 当前无警告编译日志 |

在项目根目录复核：

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3.10 -B docs/review/P1_MANUSCRIPT_20261127/verify_manuscript.py
```

不需要运行训练入口。只有确需从相同冻结 CSV 重新生成表格时才运行 `build_tables.py`，随后重新编译并目检。

## 后续写作约束

必读 `02_口径与约定/逐问撰稿规则_用户确认.md`；该文件已同步为 WSL 和 Windows 亚太杯 skill 的 `references/31_逐问撰稿与官方模板保真规范.md`。当前为 P1 内容审阅稿，非最终提交件；全文完成后统一核定页数、Summary、综合评价、总结、源码与 AI 披露。
