"""Build the solve ledger from the independently replayed tables, without any SA calls."""
import csv
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from register import ROOT, OUTPUT, FAMILIES, BUDGETS, digest


def read_rows(name):
    with (OUTPUT/name).open(newline='') as f:
        return list(csv.DictReader(f))


def report():
    audit=json.loads((OUTPUT/'verification.json').read_text())
    launch=json.loads((OUTPUT/'launch.json').read_text())
    reg=json.loads((OUTPUT/'registration.json').read_text())
    reg_hash=digest((OUTPUT/'registration.json').read_bytes())
    raw=read_rows('raw_index.csv')
    records=read_rows('formal_results.csv')
    pre=read_rows('budget_prefixes.csv')
    summary=read_rows('budget_summary.csv')
    tz=ZoneInfo('Asia/Shanghai')
    begin=datetime.fromisoformat(launch['started_utc']).astimezone(tz)
    end=max(datetime.fromisoformat(r['finished_utc']) for r in raw).astimezone(tz)
    duration=(end-begin).total_seconds()
    cpu='Kaiwu SDK 1.4.4 的 SimulatedAnnealingOptimizer，四个独立 CPU worker，每个求解实例 process_num=1'
    lines=['# P3 正式 SA 基线执行记录','',
           f"**已复核 {audit['verified_raw_files']}/900 个原始向量、9 个块、63 个嵌套预算前缀。** 正式求解器为{cpu if launch['backend']=='kaiwu_cpu4' else '通过双门的 CUDA 单翻转 SA'}。下表的分母是每个切片预先分配的三个块。",
           '', '## 七档预算的实际精确命中块数','','| 切片 | '+' | '.join(map(str,BUDGETS))+' |','|---|'+''.join('---:|' for _ in BUDGETS)]
    for f in FAMILIES:
        s=[r for r in summary if r['family']==f]
        lines.append('| '+f+' | '+' | '.join(r['n_exact_planned']+'/3' for r in s)+' |')
    lines+=['','前缀共享同一块中的早期重启。每个前缀先筛出全 40 链合法的原始向量，再按（整数能量，重启序号）取最小。命中表示该向量按（q，候选行号）解出的 ID 等于冻结切片赢家。无严格向量记 NO_STRICT，主选解与 regret 留空。前缀不完整记 INCOMPLETE。','',
            '## 单次重启的严格性与命中','','| 切片 | 计划重启 | 可评分 | 严格向量 | 严格且精确 | 非法向量 |','|---|---:|---:|---:|---:|---:|']
    for f in FAMILIES:
        r=[x for x in records if x['family']==f]
        scored=sum(x['status']=='SCORED' for x in r)
        strict=sum(x['strict']=='True' for x in r)
        hit=sum(x['exact']=='True' for x in r)
        lines.append(f'| {f} | {len(r)} | {scored} | {strict} | {hit} | {scored-strict} |')
    lines+=['','## 每块 100 次重启后的主选解','','| 切片 | 块 | 胜出重启（1–100） | 数据集 ID | 整数能量 | 残差 | 原表 regret | 精确命中 |','|---|---:|---:|---:|---:|---:|---:|---|']
    for r in pre:
        if r['budget']=='100':
            lines.append('| '+' | '.join(r[k] or 'NA' for k in ('family','block','selected_restart','selected_id','selected_energy','selected_residual','selected_regret','selected_exact'))+' |')
    lines+=['','## 日程与预登记','','- 三张整数矩阵及评分协议字节与封存提交 §'+reg['sealed_anchor']+'§ 一致。']
    lines+=[f"- 正式种子登记 SHA-256 为 §{reg_hash}§，补充登记为 §{launch['registration_addendum_sha256']}§。新基数 7300000 保留族、块、序号的预设结构，避免沿用旧基数与 P2 留存记录中的 {len(reg['original_formula_p2_overlap'])} 个重号。900 个唯一编号与 P3 的 144 个摸底种子、门验证的 480 个编号均无交集。",
            "- 正式日程使用初温为最大绝对行和的四倍、降温率 0.99、终温绝对值 0.0001，每温度 490 次迭代。P3 历史预测参照用相对终温 T0×0.0001。历史预测阈值仍取原回执；本表度量本轮绝对终温日程。",
            f"- 本地运行时间为 {begin:%Y-%m-%d %H:%M:%S} 至 {end:%H:%M:%S}（上海），从启动到最后一次返回共 {duration:.1f} 秒。此时间仅记录本地作业。"]
    if launch['backend']=='kaiwu_cpu4':
        lines.append('- GPU 精确单步验证通过，但两自旋反例显示，已登记 CUDA 实现与 Kaiwu 对起始态的保留规则不同。正式 900 次全部使用 CPU。GPU 验证向量独立留档。')
    lines+=['','## 归档与回放','',
            '- §seeds.csv§ 为全部 900 个族／块／重启／种子。每次启动与返回分别有独占 JSON，§vectors/§ 中每次有效求解都有一份原始 NPY，§raw_index.csv§ 记录路径、时间、类型及逐文件哈希。',
            '- §formal_results.csv§ 保留严格性、能量、残差和严格解码结果。独立复算遍历上三角无向边，按每条链两端补定值后的畴壁位置解码；逐条比对封存评分器的整数能量、非法链编号、ID、原表值、regret、精确命中。',
            '- §budget_prefixes.csv§ 含 63 个块前缀及所选重启；§budget_summary.csv§ 汇总 21 个族×预算，列出已完成块数、取得严格解块数、主选解精确命中块数、条件最大 regret。',
            '- 在项目根使用 NumPy 环境执行以下只读复核。表已存在时逐字节比对；复核不调用求解器。',
            '', '§§§bash', 'python -B 03_求解/D/p3_run/sa/test_scoring.py', 'python -B 03_求解/D/p3_run/sa/score.py', '(cd artifacts/p3_run/B/formal && sha256sum --check --quiet vectors.sha256)', '§§§',
            '', '数据目录为 §artifacts/p3_run/B/formal/§，GPU 判决存于 §artifacts/p3_run/B/gpu_gate/decision.json§。','']
    return '\n'.join(lines).replace('§', chr(96))


if __name__=='__main__':
    path=ROOT/'codex/P3_SA_BASELINE_RESULTS.md'
    data=report()
    if path.exists():
        if path.read_text()!=data:
            raise ValueError('Existing final report differs.')
    else:
        with path.open('x') as out:
            out.write(data)
