# F1 单图审阅单

状态：**已制作，待用户本人审图**。色板与清单已经批准；本次仅制作 F1，尚未制作 F2 或后续图。

**图名**：Data audit and AB-blocked validation。

**用途一句话**：用数据分布、样本构成和 AB 阻断示意，解释 P1 的近正例任务及防泄漏验证结构。

- [300 dpi 彩色 PNG](F1_data_audit.png)
- [矢量 PDF](F1_data_audit.pdf)
- [整图灰度自查版](F1_data_audit_grayscale.png)
- [机器审计记录](F1_audit.json)

## 数据来源与数值口径

只读 `artifacts/p1_v21/` 的既有产物：

1. `domains/main_outer_0.csv.gz` 至 `main_outer_4.csv.gz`：每份只取 H-soft 行，还原 02 的 11,256 条唯一记录；不把同一对象的八路线记录重复计算。
2. `splits.json`：五外折与十五内折的 AB 分组。以永久样本 `id` 关联；`row_index` 是 02 表内局部行号，两者分别核验，不混用。
3. `experiment_freeze.json`：固定近正例阈值 eps=2。
4. `preflight.json`、`results/P1_main_per_fold.csv`：已批准来源清单中的规模及外折口径核对来源，原文件 SHA 保留。

主直方图宽度为 5 V，低 V 放大区宽度为 0.25 V；两者均显示原尺度。全部 11,256 行计入主图，128 个 V<=2 样本计入放大区。末箱包含右端点。金属 10,824（96.16%）、非金属 432（3.84%）；观测 V=0 为 0，最小 V 为 0.0004。

AB 组数为 1,608，各外折评估块含 322/322/322/321/321 组；每个 AB 对应七条 X 记录。五外折、十五内折均核验训练/评估 AB 不相交，且内折只覆盖所属外折训练部分。示意图中的等宽格代表分组结构；精确组数直接标在列上。

这些标签观察均限定在 **02 数据**。03 是开发选择数据；04 只有组成输入，未读取隐藏真值，不据此声称其 V=0 命中或未命中。

## Caption draft

> **Class imbalance and the absence of observed zero-V samples motivate near-positive screening.** The 02 development data contain 10,824 metal and 432 nonmetal samples, including 128 cases with V <= 2 and no observed V = 0. Histogram bin widths are 5 V in the main panel and 0.25 V in the inset. The 1,608 directed AB groups are kept disjoint across five outer evaluation folds and three inner folds within each outer-training set. Dataset 03 supports development selection; dataset 04 provides composition-only holdout inputs.

## 五项自查

- [x] **dpi**：PNG 300 dpi，2007×1842 px；另附全矢量 PDF。
- [x] **字号**：最终尺寸 170×156 mm，最小 8.5 pt；全部实际文本解析为 Times New Roman。已调用模板 `apply_apmcm_style()` 和 `use_times_new_roman()`；PDF 字体嵌入另行核查。
- [x] **零中文**：图内全部文字为 ASCII 英文；PDF 文本层可提取，未含中文或中文标点。
- [x] **灰度可辨**：完整灰度图已目检。M/N 明暗与纹理共同区分；近正例放大区有独立标题和边界；训练/评估块有纹理、明暗和 E 标签。未实际进行纸张打印测试。
- [x] **色板一致**：读取冻结 A 配置，M/N/P/W 的 Hex 未改；中性框线使用既定辅助色。图内无新增语义色。

布局目检未见文字遮挡或超出画布；低 V 放大区阈值线及浅黄柱有可见边界。主图及放大区都保留计数刻度，没有以归一化比例替换样本数。F1 是数据审计图，不引入无关 p 值或模型命中统计。

本轮仅写 `figures/`：包含制图脚本、直方图计数、划分计数、图件和审查记录。未加载或拟合模型，未改实验表、原始数据或拟合账本。交付保护哈希见 [F1_delivery_receipt.json](F1_delivery_receipt.json)。

复现：

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_F1.py
```

按用户指定的逐张审核流程，本次等待 **F1** 审批；通过后再制作 F2，不先嵌入论文。
