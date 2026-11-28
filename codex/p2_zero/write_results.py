"""Make the standalone internal reports directly from validated figure data."""
import csv
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'figures/P2/data'
P=ROOT/'codex/p2_zero'
ZONE=timezone(timedelta(hours=8))
def read(name):
    with (D/name).open(newline='') as f:return list(csv.DictReader(f))
def timefmt(t):
    return datetime.fromtimestamp(t,ZONE).strftime('%H:%M:%S')
def main():
    t=json.loads((D/'sa_paired_test.json').read_text())
    if not t['complete']:raise RuntimeError('Use an explicit incomplete-run report at cutoff')
    curves=read('sa_budget_curve.csv')
    counts=t['table']; delta=t['delta'];p=t['p_two_sided']
    effect='业务矩阵在预登记的低预算端点取得较高的 strict 命中块比例' if delta>0 and p<.05 else ('零业务对照在预登记的低预算端点取得较高的 strict 命中块比例' if delta<0 and p<.05 else '主检验未分辨两组在该预算下的命中差异')
    r5=counts['11']+counts['10'];z5=counts['11']+counts['01']
    fresh=[r for r in read('sa_attempts.csv') if r['source']=='fresh']
    nvalid=sum(r['status']=='VALID_COMPLETED' for r in fresh);nattempt=sum(r['status']!='NOT_STARTED' for r in fresh)
    assert len(fresh)==4200
    a=read('chain_ablation.csv')
    paired={r['arm']:r for r in a if r['cohort']=='fresh_matched_2'}
    short,long=paired['40_real'],paired['single_real']
    timing=read('task_timeline.csv')
    allobs=sum('NA' not in (r['accepted_at_local'],r['terminal_observed_at_local']) for r in timing)
    m=read('task_margin.csv')
    job=ROOT/'artifacts/p2_zero'
    host_start=float((job/'run_intent').read_text())
    host_end=max(f.stat().st_mtime for f in job.glob('*.jsonl'))
    results=f'''# P2 零配额优化 · 离线结果

2026-11-28。正式服务终态继续以 [FINAL](P2_CIM_FINAL_RESULTS_20261128.md) 为唯一引用。本轮新增真机任务 0、模型拟合 0、论文修改 0。以下均为后续本地试验或封存返回的复算。

| 问题 | 核对结果 | 证据范围 |
|---|---|---|
| 只凭分发文件能否复算？ | 独立 clone 通过；529 个候选、25 个 ID、250 个原始向量逐一核对 | Python 3 标准库，本地项目克隆与 D 盘分发克隆各一次 |
| 正式返回离严格失效边界多近？ | 最低能量选解最小裕度 20（F03）；整个返回集中最小裕度 8（F14） | 固定整数矩阵，确认性算术复核；196 定理于观测后推导 |
| 本地 SA 在预算 5 能否区分实/零业务？ | {r5}/20 对 {z5}/20，差 {100*delta:+.0f} 个百分点，双侧精确 p={p:.8g} | 预先冻结的新种子块主检验；仅限当前实例、解码器及 SA 参数 |
| 匹配两块下长短链结果如何？ | 严格命中数为单长链 {long['strict_hits']}/200、40 短链 {short['strict_hits']}/200 | 探索性，两对块；分组和经典聚合工作量一起改变 |

## 1　证据包、证书和版本时点

[复核入口](../evidence/p2/README.md)在无许可、无访问密钥、无第三方依赖的环境中可运行。D 盘交付目录为 `D:/上海大学__/26亚太杯英文赛/codex/P2零配额优化/`。执行：

```sh
git clone '/mnt/d/上海大学__/26亚太杯英文赛/codex/P2零配额优化/P2_evidence_20261128.bundle' p2-review
cd p2-review
python3 -I -B evidence/p2/verify.py
```

两份克隆读回相同，见[分发回执](p2_zero/distribution_receipt.json)。原结果映射按服务器 ID、原始字节哈希、阶段及候选字典校验，P01 来自首份终态档案。脚本独立解固定参考位后的链动态规划，另逐边求和复算每个返回向量。证据包可验证本地整数结论，服务商没有提供光学物理能量遥测。第三方实际接收或独立签收另计。

[检查器补丁](p2_zero/validation_checker.diff)要求盲池候选排序后精确等于 0…528，所有块指向矩阵末位。H05 的 4 个配置和 H07/H08 的 23 个配置各自重放；完整池 5 片的实/零矩阵都逐片核对字典。两套审计各包含 10,200 个小状态穷举交叉验证。合法置换通过；缺项、等 q 重复、越界、参考错误和字节篡改均被相应检查拒绝。[H05](p2_zero/replay_h05.json) · [H07/H08](p2_zero/replay_final.json) · [故障注入](p2_zero/fault_results.json)

之前的报告原件继续与研究回执匹配。[时点标注阅读版](P2_RESEARCH_REPORT_20261128_阅读版.md)与[结果索引](README.md)明确标出后续正式终态。历史 SA 置换/线性两组的 partial 命中分别为 56/100 与 35/100，strict 分别为 55/100 与 30/100。旧零业务证书沿用已归档勘误：存在合法基态反例，G2=COUNTEREXAMPLE；40 链控制可构造原 regret 22.26637 的基态选择。

## 2　逐任务裕度与严格边界

用 Δ=E−E₀，整数基态 E₀=−58722。逐链认证给出任意非法态 Δ≥340。合法向量的 Δ=4∑(qᵦ−min qᵦ)。第 17 组含唯一全局 q=0 的候选 226；若该组错选，组内最小替代 q=49，其余增量非负。因此 **Δ<196 时全部链合法，聚合候选在冻结原表的 regret=0**。令其余 39 组分别局部最优而第 17 组选 217，Δ 恰为 196，跨组选出 448，原 regret=0.46513924572935705。证书的严格不等号不可改成含等号。聚合比较 (q,原索引)，链数不能判定成败。

| 阶段与口径 | 最小裕度 | 中位裕度 | 最大裕度 |
|---|---:|---:|---:|
| 先导，最低能量选解 | 68 | 76 | 84 |
| 先导，全集最小裕度 | 56 | 72 | 84 |
| 正式，最低能量选解 | 20 | 72 | 112 |
| 正式，全集最小裕度 | 8 | 64 | 112 |

正式 20 个选解 Δ 为 84–176，200 个正式返回 Δ 为 84–188；观察跨度占证书阈值 (188−84)/196=53.06%，最大 Δ 使用了 95.92% 的阈值。F14 的最弱返回仅余 8/196=4.08%。这些数值度量距离已知失败构型的能量界，对其他矩阵、噪声源或下一服务任务均无频率保证。

| 任务 | 最低 Δ | 最高 Δ | 选解裕度 | 全集最小裕度 |
|---|---:|---:|---:|---:|
'''
    for r in m:results+='| '+' | '.join(r[k] for k in ['slot','min_residual','max_residual','selected_margin','set_min_margin'])+' |\n'
    results+='''
[逐任务 CSV](../figures/P2/data/task_margin.csv)可关联 result ID；[逐向量 CSV](../figures/P2/data/return_energy.csv)保留原始序号及能量选解标记。

## 3　组内位置、身份与聚合（探索性）

250 个返回向量产生 10,000 个向量–组观测。正式向量达到局部最优的链数为 19–28，19 到 28 条对应向量计数依次为 11、15、16、12、52、37、17、15、15、10。三个组（4、17、39）在所有正式返回中均取到组内最低 q。只有第 17 组包含表中唯一代理最优，因而能量证书与其他组中的局部误差可同时成立。

在每个正式任务内，用 400 个组选择计算相对位置与 q 超额的含并列 Spearman 相关，20 个系数范围 −0.221 至 +0.281，中位 −0.044；只取正超额，范围 −0.366 至 +0.545，中位 +0.154。每个正式任务涉及 15–32 个不同的次优候选，中位 20。候选身份与链中的固定位置绑定，任务内解也经过筛选；这些观测不能分离位置效应与材料身份效应。按任务附并列高频身份；计数包含原返回集的重复向量，没有去重择优。[任务关联表](../figures/P2/data/chain_association.csv) · [身份明细](../figures/P2/data/chain_position_identity.csv) · [逐链计数与任务等权占比](../figures/P2/data/chain_summary.csv)

'''
    results+=f'''## 4　SA 预算标度

主检验、截止、三类矩阵、4200 槽和种子已于首个 SA 前登记（提交 `5aff9d3`）。矩阵选择早于本轮，推断条件限定于这一选择。工作区 slots.csv 的 CRLF 原字节在首份登记里已有 SHA-256，Git 首提交默认将换行存为 LF。后续提交 `95458e1` 指定逐字节保留，内容和种子顺序均相同；运行时验算与新克隆的 SHA 均与首份登记一致。

本地 Kaiwu 1.4.4 SA，Ubuntu 22.04 / Intel Core Ultra 9 275HX，24 个可见逻辑 CPU，4 个工作进程，每次求解单进程、size_limit=1。盘点到 NVIDIA RTX 5070 Ti Laptop，12227 MiB；沿用 SDK CPU 路径以维持同算法和温度协议。每个新重启单独构造优化器，初温 26284，终温 2.6284，α=0.99，550 次/温度。实/零业务同一组种子配对，共 20×100×2 次；前两组同步种子运行单长链 200 次。新鲜种子 710001–712000 与历史已核查的 5600 个 seed 字段无冲突。计入计划 {len(fresh)}，实际启动 {nattempt}，有效 {nvalid}，失败 {nattempt-nvalid}，未启动 {len(fresh)-nattempt}。失败计未命中，无补跑；历史 H07 另有 5 个失败也保留原分母。

预登记 B=5 两侧精确 McNemar，配对表为“两者命中 {counts['11']}、仅业务 {counts['10']}、仅零业务 {counts['01']}、均未命中 {counts['00']}”。效应差 {100*delta:+.0f} 个百分点，p={p:.8g}，α=0.05。**{effect}**。随机种子块近似独立，零假设下不一致配对的方向可交换。其余 B 是同块嵌套前缀，保留描述性用途。两种端点为每块任意 strict 命中与在 strict 返回中按 (E,序号) 只取一个。每格给出“至少一次命中 / 最低能量选解命中”的块数。

| 数据组 | 块数 | B=1 | 2 | 5 | 10 | 20 | 50 | 100 |
|---|---:|---|---|---|---|---|---|---|
'''
    for so,arm in [('H07','40_real'),('H07','40_zero'),('fresh','40_real'),('fresh','40_zero'),('fresh_length_paired','40_real'),('fresh_length_paired','single_real')]:
        rr=sorted((r for r in curves if r['source']==so and r['arm']==arm),key=lambda r:int(r['budget']))
        results+=f"| {so} / {arm} | {rr[0]['planned_blocks']} | "+' | '.join(f"{r['strict_hit_blocks']}/{r['energy_hit_blocks']}" for r in rr)+' |\n'
    results+='''
业务项移除后，解码器仍使用真实 q，从至多 40 个局部候选中比较选一个；“至少一次命中”还在块内累积。此次 B=50 和 B=100 时两组均为 20/20 块至少一次命中；同两个预算下按最低能量只选一个，业务为 20/20，零业务为 0/20。两套选择规则均已公开，比较只发生在各自 SA 组别内。真机与本地算法的迭代预算不可换算。分发的原矩阵与位串还可由标准库独立复算：`python3 -I -B codex/p2_zero/check_sa_export.py`。

[全部前缀、无 strict 块与条件 regret](../figures/P2/data/sa_budget_curve.csv) · [成对检验](../figures/P2/data/sa_paired_test.json)

## 5　链长与经典聚合成本（探索性）

| 数据组 | 配置 | 自旋 / 链 | 计划 / 有效 | 严格可行 | 严格命中 | 条件中位 regret | 每向量最多比较 |
|---|---|---|---|---:|---:|---:|---:|
'''
    for r in a:results+=f"| {r['cohort']} | {r['arm']} | {r['spins']} / {r['chains']} | {r['planned']} / {r['valid']} | {r['strict']} | {r['strict_hits']} | {r['conditional_median_regret']} | {r['max_classical_min_comparisons']} |\n"
    results+=f'''
H02 的端点填充、P=254、Q=127 及温标与 H05 不同；历史对照按队列分别呈现。新匹配对照固定 q、P=128、温度及种子，单链 529 自旋、40 链 490 自旋。两矩阵都通过 G1/G2，最坏基态原 regret=0。给定合法向量时单链直接读 1 个候选，短链需从最多 40 个候选中作 39 次比较；本地消融不识别光学硬件因果效应。[标准消融表](../figures/P2/data/chain_ablation.csv)

## 6　交付与时间

- {allobs}/25 个任务具有经 ID 核对的本地受理及首次终态观测时点。物理起止时刻均无来源，登记为 NA。[任务时间线数据](../figures/P2/data/task_timeline.csv)
- [P2 图件总清单](P2图件总清单.md)默认正文四张、最多五张；[图件数据清单](../figures/P2/data/figure_data_manifest.csv)与[列字典](../figures/P2/data/columns.md)支持后续装配。晶体单视角已归档；三种取向仍须使用修正后的 VESTA 设置重导；MP 出版记录的访问日期与 DOI 已核实（见图件总清单）。无正式图或论文嵌入。
- [措辞纪律](P2叙事纪律与措辞禁令手册.md)汇总 P 的四条 Fatal 和一条重大 Warning；[P3 可迁移接口](p2_zero/P3_迁移接口.md)仅记录可复用资产及需重证的假设。
- 按本轮登记，方案计入 30 分钟，T0=15:58:45，实施开始 16:28:45。本地 SA 于 {timefmt(host_start)} 启动，最后一个槽在 {timefmt(host_end)} 落盘，实耗约 {(host_end-host_start)/60:.1f} 分钟。T+4:15 截止 20:13:45，五小时总限至 20:58:45，均以北京时间计。封存原件逐项核对见[交付验算](p2_zero/delivery_checks.json)。
'''
    (ROOT/'codex/P2_ZERO_QUOTA_RESULTS.md').write_text(results)
if __name__=='__main__':main()
