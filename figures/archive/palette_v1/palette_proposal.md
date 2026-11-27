# P1/P2/P3 统一色板提案 v1

日期：2026-11-27。状态：**待用户批准色板**。字体按用户追加要求固定为 **Times New Roman**，适用于本次试色及后续全部 P1/P2/P3 图表；不得回退到其他字体。

本次提交 [palette_strip.png](palette_strip.png) 与本提案；[palette_strip_grayscale.png](palette_strip_grayscale.png) 是同一张试色页的灰度自查副本。用途是审定全论文的语义色与辨识规则，属于设计校样；图中交叉线和连续条的 0–1 数值为 synthetic design values，未引用或生成任何实验结果。

## 1. 八种固定语义色

采用深石板蓝、砖褐、暗金、灰绿和赭石搭配中性灰。全部离散语义色 CIELAB 色度 C*ab（D65）为 1.80–21.95，L* 为 20.05–68.94；压低色度与明度，未采用纯红、纯绿、纯蓝或 jet。

| ID | 语义角色 / 色名 | Hex | RGB（0–255） | 相对亮度 Y | 灰度明度 L* | 等亮灰度 G8 |
| --- | --- | --- | --- | ---: | ---: | ---: |
| S | 代理模型主色 / 深石板蓝 | `#2C4256` | (44, 66, 86) | 0.05104 | 27.03 | 64 |
| B | 基线对照色 / 中性冷灰 | `#949699` | (148, 150, 153) | 0.30409 | 62.01 | 150 |
| Q | 量子方法色 / 低彩赭石 | `#8B6C52` | (139, 108, 82) | 0.16823 | 48.04 | 114 |
| C | 经典方法色 / 深灰绿 | `#3C554B` | (60, 85, 75) | 0.07966 | 33.91 | 80 |
| W | 约束与警示线色 / 深砖褐 | `#492725` | (73, 39, 37) | 0.03001 | 20.05 | 48 |
| M | 金属样本色 / 暖灰 | `#AAA8A5` | (170, 168, 165) | 0.39268 | 68.94 | 168 |
| N | 非金属样本色 / 鼠尾草灰绿 | `#728A74` | (114, 138, 116) | 0.23015 | 55.09 | 132 |
| P | 近正例高亮色 / 暗金褐 | `#715E3D` | (113, 94, 61) | 0.11853 | 40.98 | 97 |

- **S** — H-soft 及代理预测；同类模型用标记、线型、直接标签区分。
- **B** — 加性 Ridge、mean、random；统计基线始终共用这一色。
- **Q** — 未来量子/量子启发方法；硬件与模拟由线型及标签区别。
- **C** — 未来经典优化求解器、枚举或经典求解参照。
- **W** — 约束界限、阈值或警示；附线型及文字，不仅靠红绿。
- **M** — gap=0 样本与其 MSE 贡献。
- **N** — gap>0 样本与其 MSE 贡献。
- **P** — 开发集已知 V<=2 样本；使用星形、边框或直接标注。

白底 `#FFFFFF`、正文/轮廓墨色 `#20252B` 及矩阵分隔线 `#E1E1E1` 为辅助色，不增加数据类别。深色块文字用白色、浅色块文字用黑色，按对比度较大者选取；本页最小块内文字对比度为 4.81:1。

## 2. 灰度辨识证据与冗余编码

Y 按 sRGB 先线性化后加权计算，避免直接平均 R/G/B：`c_lin=c/12.92`（c<=0.04045），否则 `((c+0.055)/1.055)^2.4`；`Y=0.2126*R_lin+0.7152*G_lin+0.0722*B_lin`。权重与线性化依据 [W3C 相对亮度定义](https://www.w3.org/TR/WCAG22/#dfn-relative-luminance)。

灰度明度取 CIE L*（白点归一化 Yn=1）：当 Y>(6/29)^3，`L*=116*cbrt(Y)-16`，否则 `L*=(29/3)^3*Y`；G8 是把 Y 重新进行 sRGB 编码后乘 255 并四舍五入得到的中性灰代码。L* 用于描述感知明度，不以 HSL lightness 代替；[W3C 颜色说明](https://www.w3.org/TR/css-color-4/#the-hsl-notation)也区分这两个概念。本提案给出的 C*ab 另按 D65 白点计算。

本页的实际检查结果：

- 8 个 G8 均不同；全部 28 对的最小 `abs(delta L*)` 为 **6.88**，最小 G8 间隔为 **16/255**。
- 辅查常见的 gamma 编码通道加权 `0.299R+0.587G+0.114B`，其 8 个灰度代码也均不同，最小间隔为 **13/255**。
- 试色图上排为原色、下排为等亮中性灰；矩阵上三角展示全部 28 对原色组合，下三角展示对应灰度组合。另对整图转换灰度并目检，检查曲线交叉处及浅色标记。
- 数值间隔与本次渲染共同支持该设计的灰度辨识；不把单个 delta L* 阈值当作所有打印机和纸张的保证。正式图继续使用下列非颜色线索。

| ID | 默认非颜色线索 |
| --- | --- |
| S | 圆点 + 实线 |
| B | 方块 + 虚线 |
| Q | 菱形 + 虚线 |
| C | 上三角 + 实线 |
| W | 叉形 + 点线 |
| M | 下三角 + 点线 / 斜线填充 |
| N | 实心十字 + 点划线 / 点状填充 |
| P | 星形 + 直接标注 |

基线内部固定：Ridge=方块虚线，mean=下三角点线，random=叉号点划线，三者颜色均为 B。浅色 B/M 的细线或标记必须有深色轮廓；金属/非金属柱或面积使用不同纹理及直接标签。红绿不单独承担任何区分。置信/分散区间若采用透明填充，必须保留边界线或纹理，不能只靠透明色深浅。

方法图按方法语义着色；MSE 组成图按样本类别着色。量子/经典角色只为后续图表预留。本轮不开展 P2。模板原有 feasible 绿色不沿用为额外状态色：通过/失败以文字、符号和方法本色表达，不能挪用非金属色表示“通过”。

## 3. 连续色图和版面规则

连续量使用原生感知均匀顺序色图。默认 **viridis，固定取原色图 [0.15,0.80]**；材料景观/热图可使用 **plasma，[0.10,0.70]**，具体使用位置在后续经批准的图件清单中指定。区间裁去亮黄端点；不手工混白、改造或重新排列色图。两段色图在本地版本采样检查中 L* 均单调不减；viridis/plasma 的类别见 [Matplotlib 官方色图说明](https://matplotlib.org/stable/users/explain/colors/colormaps.html)。

离散语义色与连续数值色标承担不同含义。色标必须写真实量与单位，同量纲且需对比的面板使用同一归一化范围；高值只表示数值高，不自动表示“好”。本次色条的 0–1 仅用于试色。涉及零线或阈值时，以标注、等值线或区间带表达，不另加 jet 或未经批准的发散配色。

版面沿用 2025D 多面板验证布局与 2025B 热图/区间带表达：白底、细框或去上/右边框、无装饰网格、少量直接注释；正式单面板最多约五种语义色。八色全展示仅限当前色板校样。

## 4. 字体、尺寸与本次自查

实际调用指定模板库的 `apply_apmcm_style()`，再按用户要求把字体统一覆盖为 **Times New Roman**。已加载真实 `times.ttf / timesbd.ttf / timesi.ttf / timesbi.ttf`，逐个文本对象解析实际字体文件并核验家族名；禁用字体替代。数学文字也固定该家族。模板示例里低于 8pt 的字号不继承。

- [x] **dpi**：300 dpi PNG，2100×2940 px；白底、嵌入 sRGB 配置。
- [x] **字号 / 字体**：实际 Times New Roman；最小 **9 pt**，常规及粗体已核对。校样按 **177.8×248.9 mm** 输出；下阶段每张图按最终印刷尺寸单独排版。
- [x] **零中文**：图内全部可见文本为 ASCII 英文，无中文或中文标点；画布边界检查通过。
- [x] **灰度可辨**：全 28 对数值检查、整图灰度渲染和目检通过；标记/线型在交叉处保留身份。
- [x] **色板一致**：八角色取自唯一 [palette_candidate.json](palette_candidate.json)，未使用模型默认循环色。

已目检彩色和灰度最终版，标题、图注、RGB 数字与色块间无相互遮挡。技术记录见 [palette_audit.json](palette_audit.json)，包含字体文件 SHA、全部色值、28 对明度差和输出图哈希。

## 5. Caption 草案、来源与复现

**Caption draft (design proof, not a paper result):**

> Fixed semantic colours retain their identities in the grayscale proof. All 28 pairs have distinct lightness levels (minimum dL* = 6.88; gray-code gap = 16/255), while markers and line styles preserve identity at crossings. Swatches and glyphs are synthetic design examples, not experimental observations.

**图文件路径**：`figures/palette_strip.png`。**用途一句话**：审定 P1/P2/P3 通用语义色在彩色、灰度和交叉线中的可读性。**数据来源文件**：`figures/palette_candidate.json`（人工颜色规范与程序生成的校样几何）；未从实验表抽样，未读取模型进行预测。

必读材料已按指定顺序完成：

1. [Windows skill](</mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm/SKILL.md>) §2.5、§7。
2. [figure playbook](</mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm/assets/apmcm_figure_playbook.md>) 全文，包括 §13–15、§13.5/13.6。
3. [D plotting templates](</mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm/assets/apmcm_d_plot_templates.py>) 全文；直接复用样式底座并改造校样布局。
4. [reference 25](</mnt/c/Users/mary3/.agents/skills/mary-modeling-contest-pipeline-apmcm/references/25_D题量子优化优秀论文解剖.md>) §25.9–25.12；2025B 的具体视觉说明实际在 §25.13，已补读。

四个来源的 SHA-256 与阅读范围写入 palette_audit.json。并已核对本项目的写作与图表规范。本轮仅写 `figures/`，包含 Matplotlib 缓存；模型、原始数据、实验结果与拟合账本只作前后哈希核对。原账本保持 914，新增拟合为 0。

复现命令（只生成校样）：

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_palette.py
```

## 6. 批准后冻结及当前停止点

**此色板将贯穿 P1/P2/P3 全部图表，获用户批准后冻结。** 冻结内容包括八个 Hex/RGB 值、语义映射、基线子线型、Times New Roman 字体族和连续色图区间；不得后续逐图换色或改变颜色含义。批准后记录配置 SHA 和批准时间；目前文件状态明确为 awaiting_user_approval。

当前只提交色板。下一步须先获用户批准色板，再按指定模板交 figure_inventory.csv；清单获批后，才按逐张出图、逐张自查、逐张提交、逐张过审的顺序继续。当前未生成正式 P1 图件或图件清单，也未开始 P2。

只读核对补记：P1 实验产物、求解代码、官方数据与账本前后哈希一致。根目录 `HANDOFF_CODEX交接文档.md` 在工作期间出现另外的变更；本轮工具未写该文件，保留其当前内容。其余六个方案/报告/交接文件与上一交付哈希一致。详见 palette_review_receipt.json。
