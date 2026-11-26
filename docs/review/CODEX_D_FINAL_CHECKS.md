# D 题独立复核：交付核验记录

日期：2026-11-26。WSL 主力 Codex。本轮交付为根目录复核报告与 P1 待确认方案；增强建模尚未开始。

## 已执行检查

| 检查 | 结果 | 证据 |
|---|---|---|
| 公开数据 SHA | 8 CSV + README 共9项全部匹配 | `artifacts/codex_review/stored_asset_audit.json` |
| 旧 P1 隔离重放 | 原参数/特征/折不变；模型/元素表/重要性逐字节一致 | `scout_p1_replay.log`、`scout_p1_replay/byte_identity.json` |
| fold2 诊断重算 | 26尾部行/22AB；配对分解、5000次条件簇bootstrap可复算 | `diagnose_scout_p1.py`、`fold2_error_analysis.json` |
| 已有 QUBO 矩阵 | 全部2704/8112可行态恒等式、独立重建通过；无求解调用 | `stored_asset_audit.json` |
| naive量化 | 原表最优量化排名576；2449/2704交叉耦合归零 | 同上；不是新P2求解 |
| 原代码保护 | 六个旧脚本 SHA 与静态审查时一致 | `artifacts/codex_review/provenance.json` |
| 辅助脚本语法 | 6份本轮 Python 源码 `compile` 通过，无导入执行 | `docs/review/*.py` |
| 台账 | 新增汇编后962行、60字节重复；旧961个ID不变，新增R0962；覆盖计数与报告一致 | `CODEX_D_READING_LEDGER.csv`、`ledger_increment_check.json` |
| SDK增补 | 164页正文全文、关键4页视觉核对；当前core罚系数调用链只读核对 | `kaiwu_144_review_evidence.json`、增补复核笔记 |
| 文档交叉引用 | 两份根报告、progress、核验记录的本地Markdown链接目标核对 | 交付后本地文件均保留 |
| Git hygiene | exit0、10 checks、0 FAIL；改动/未跟踪为WARN | `artifacts/codex_review/git_hygiene.log` |
| env doctor | exit0、14 checks、0 FAIL；pypdf可选未安装为WARN | `artifacts/codex_review/env_doctor.log` |

执行解释器 `/usr/bin/python3.10`（3.10.12）；PATH默认 `python` 指向 conda3.13.12，未改环境。当前检测到 lxml、fitz；不要沿用早期其他解释器下的缺包结论。Kaiwu1.4.4、community1.0.8 等安装元数据保留在 provenance。只读安装元数据不等于导入 SDK 或获得硬件授权。

仓库卫生工具只检查其定义范围，密钥模式扫描针对未跟踪文本；0 FAIL 不证明历史交接不存在凭证。本轮没有复制这些原文，没有使用 `--check-push`、没有commit/push，没有改变原始数据/旧模型/正式件。

## 双盘镜像

镜像目标 `/mnt/d/上海大学__/26亚太杯英文赛/`。同步本轮两份根报告、review笔记/台账/辅助脚本、更新后的协作handoff和关键核验/重放证据，并补齐新增SDK汇编；不拷贝原交接凭证、配置、外部标签、整套原始参考库或大批提取缓存，不删除镜像中的已有内容。

逐文件SHA及数量由 `artifacts/codex_review/delivery_mirror_manifest.json` 记录；同步后逐项比对WSL源与D盘副本，manifest本身也写双份。该manifest不自列其哈希，避免递归。只覆盖本轮明确持有的文件；发现非本轮差异即停止处理该路径、保留双方。

## 停止点

方案供用户确认。没有训练增强P1、生成04正式预测、运行新P2/P3/精度求解或任何真机任务；没有子智能体。旧P2/P3采样次数/耗时没有重新执行，只能按旧报告引用。本轮工作不能被写成已独立完成的新模型实验。
