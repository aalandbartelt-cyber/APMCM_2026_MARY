# F1 v2 单图审阅单

状态：**按用户意见修订，待用户本人审图**。删除了 03/04 页脚与独立流程框，黄色小图明确为近正例局部分布；底部用单一矩阵直接标注训练与评估块。未制作 F2 或后续图。原版保留在 `archive/v1_rejected/`。

**图名**：Data audit and AB-blocked validation。

**用途一句话**：用数据分布、样本构成和 AB 阻断示意，解释 P1 的近正例任务及防泄漏验证结构。

- [300 dpi 彩色 PNG v2](F1_data_audit_v2.png)
- [矢量 PDF v2](F1_data_audit_v2.pdf)
- [整图灰度自查版 v2](F1_data_audit_v2_grayscale.png)
- [机器审计记录](F1_audit.json)

## 数据来源与数值口径

只读 `artifacts/p1_v21/` 的既有产物：

1. `domains/main_outer_0.csv.gz` 至 `main_outer_4.csv.gz`：每份只取 H-soft 行，还原 02 的 11,256 条唯一记录；不把同一对象的八路线记录重复计算。
2. `splits.json`：五外折与十五内折的 AB 分组。以永久样本 `id` 关联；`row_index` 是 02 表内局部行号，两者分别核验，不混用。
3. `experiment_freeze.json`：固定近正例阈值 eps=2。
4. `preflight.json`、`results/P1_main_per_fold.csv`：已批准来源清单中的规模及外折口径核对来源，原文件 SHA 保留。

主直方图宽度为 5 V，低 V 放大区宽度为 0.25 V；两者均显示原尺度。全部 11,256 行计入主图，128 个 V<=2 样本计入放大区。末箱包含右端点。金属 10,824（96.16%）、非金属 432（3.84%）；观测 V=0 为 0，最小 V 为 0.0004。

AB 组数为 1,608，各外折评估块含 322/322/322/321/321 组；每个 AB 对应七条 X 记录。图中每一行代表一次外折：深色块用于评估，其余四个斜线块用于训练；列对应固定的 AB 分组。五外折、十五内折均核验训练/评估 AB 不相交，且内折只覆盖所属外折训练部分。内层三折说明移到图注，不再画独立流程框。等宽格表示分组结构，精确组数标在列上。

这些标签观察均限定在 **02 训练数据**。本图不展示其他数据集，也不据此判断隐藏 holdout 的 V=0 命中情况。

## Caption draft

> **Metal samples dominate the training set, while near-positive cases form a small subset.** Among 11,256 training samples, 96.16% have gap = 0 and none have V = 0. The yellow inset shows the 128 near-positive cases with V <= 2, all of which are nonmetal samples; bin widths are 5 in the main histogram and 0.25 in the inset. In (c), the dark block is evaluated and the other four blocks provide training data. All compositions sharing an ordered (A, B) pair stay together. Three-fold inner selection uses only the training blocks and is omitted from the diagram for clarity.

## 五项自查

- [x] **dpi**：PNG 300 dpi，2007×1606 px；另附全矢量 PDF。
- [x] **字号**：最终尺寸 170×136 mm，最小 8.5 pt；全部实际文本解析为 Times New Roman。已调用模板 `apply_apmcm_style()` 和 `use_times_new_roman()`；PDF 字体已核验嵌入。
- [x] **零中文**：图内全部文字为 ASCII 英文；PDF 文本层可提取，未含中文或中文标点。
- [x] **灰度可辨**：完整灰度图已目检。M/N 明暗与纹理共同区分；近正例放大区有明确标题、坐标轴和边界；训练/评估块有纹理、明暗和完整 Evaluate 标签。未实际进行纸张打印测试。
- [x] **色板一致**：读取冻结 A 配置，M/N/P/W 的 Hex 未改；中性框线使用既定辅助色。图内无新增语义色。

布局目检未见文字遮挡或超出画布；低 V 放大区阈值线及浅黄柱有可见边界。主图及放大区都保留计数刻度，没有以归一化比例替换样本数。F1 是数据审计图，不引入无关 p 值或模型命中统计。

本轮仅写 `figures/`：包含制图脚本、直方图计数、划分计数、图件和审查记录。未加载或拟合模型，未改实验表、原始数据或拟合账本。交付保护哈希见 [F1_delivery_receipt.json](F1_delivery_receipt.json)。

复现：

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /usr/bin/python3.10 -B figures/render_F1.py
```

按用户指定的逐张审核流程，本次等待 **F1** 审批；通过后再制作 F2，不先嵌入论文。
