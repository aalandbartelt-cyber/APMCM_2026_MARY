"""Summarize frozen service-level outcomes; no fitting or new solver calls."""
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import argparse
import csv
import hashlib
import json
import numpy as np
from scipy.stats import beta
from contract import ROOT
from service_contract import AUDIT, LIVE, verify_service, summarize


def interval(k,n):
    if n==0:return None
    return [0.0 if k==0 else float(beta.ppf(.025,k,n-k+1)),
            1.0 if k==n else float(beta.ppf(.975,k+1,n-k))]


def main():
    p=argparse.ArgumentParser();p.add_argument('--anchor',required=True);p.add_argument('--snapshot',action='store_true')
    args=p.parse_args();verify_service(args.anchor)
    rows=[]
    for stage,n in [('P',5),('F',20)]:
        for i in range(1,n+1):
            slot=f'{stage}{i:02}';path=AUDIT/slot/'result.json'
            if path.exists():r=json.loads(path.read_text())
            else:r={'slot':slot,'stage':'pilot' if stage=='P' else 'formal',
                    'status':'PENDING' if (LIVE/slot/'create_intent.json').exists() else 'NOT_STARTED'}
            rows.append(r)
    formal=[r for r in rows if r['slot'].startswith('F')]
    if not args.snapshot and any(r['status'] in ['PENDING','NOT_STARTED'] for r in formal):
        raise ValueError('Not a final report: unresolved formal slots remain')
    counts=summarize(formal)
    inference=json.loads((ROOT/'codex/p2_cim_service/inference_registration.json').read_text())
    rng=np.random.default_rng(inference['bootstrap_seed'])
    bh=[];br=[];empty=0
    for _ in range(inference['bootstrap_replicates']):
        draw=[formal[i] for i in rng.integers(0,20,20)]
        bh.append(sum(r['status']=='VALID_COMPLETED' and r['hit_strict'] for r in draw)/20)
        conditional=[r['best_regret_strict'] for r in draw if r['status']=='VALID_COMPLETED' and r['feasible_strict']]
        if conditional:br.append(float(np.median(conditional)))
        else:empty+=1
    auxiliary={'task_hit_95pct_Clopper_Pearson_per_attempt':interval(counts['N_H'],counts['N_A']),
               'assumptions':inference['binomial_assumptions'],
               'bootstrap_replicates':5000,'bootstrap_empty_regret_subsets':empty,
               'bootstrap_task_hit_quantiles':np.quantile(bh,[.025,.5,.975]).tolist(),
               'bootstrap_conditional_median_regret_quantiles':np.quantile(br,[.025,.5,.975]).tolist() if br else None,
               'bootstrap_task_hit_degenerate':len(set(bh))==1,
               'bootstrap_conditional_regret_degenerate':len(set(br))==1 if br else None}
    stamp=datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%dT%H%M%S')
    out=ROOT/'artifacts/p2_cim_go_20261128/reports'/stamp;out.mkdir(parents=True,exist_ok=False)
    cols=['slot','stage','status','result_id','returned_set_size','strict_solution_count','partial_solution_count',
          'hit_strict','hit_partial','best_regret_strict','best_regret_partial','energy_selected_regret_strict',
          'min_integer_energy','max_integer_energy','source_sha256']
    with (out/'task_results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
    result={'as_of':stamp,'anchor':args.anchor,'counts':counts,'auxiliary':auxiliary,
            'unit':'optimization service task','per_solution_rates':False,'TTS_analysis':False,'records':rows}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    baseline=json.loads((ROOT/'codex/p2_cim_service/SA_service_baseline.json').read_text())
    text=f'''# P2 CIM optimization服务结果（{'进行中快照' if args.snapshot else '全部已启动任务终态报告'}）

统计单位为服务任务；优化输出称“返回解集”。先导5槽不进入正式20槽。全程冻结矩阵/代理表；零新增拟合/SA，未写论文。正式锚 `{args.anchor}`。

| 正式任务指标 | 计数 |
|---|---:|
| 计划任务 | 20 |
| 已尝试 | {counts['N_A']} |
| 有效服务返回 | {counts['N_V']} |
| 至少一个strict可行解 | {counts['N_F']} |
| strict原表最优命中 | {counts['N_H']} |
| strict原regret≤0.1 | {counts['N_eps']} |

嵌套断言已检查：N_H≤N_eps≤N_F≤N_V≤N_A≤20。G20(0)={counts['G20']['0']}；分母包含全部20计划槽。失败/pending/无可行解没有被静默剔除，条件regret不可用者记NA。

'''
    text+='| 槽位 | 状态 | 返回解数 | strict解数 | 任务strict命中 | 最小原regret | 能量选解regret |\n|---|---|---:|---:|---|---:|---:|\n'
    for r in rows:
        text+='| '+' | '.join(str(r.get(k,'NA')) for k in ['slot','status','returned_set_size','strict_solution_count','hit_strict','best_regret_strict','energy_selected_regret_strict'])+' |\n'
    text+='''
## 服务级经典对照

五个已封存SA块各100次既有重启：五块最优strict原regret均0，按物理能量选解的原regret也均0。CIM内部自适应计算次数及排序/聚类成本未公开；20个CIM任务与5个固定SA块不等计算预算、不等重复数。不把CIM返回解集与SA逐重启命中率并置，不推断量子优势或同预算优胜。所有逐解比例和TTS分析均取消。

## 描述性统计边界

'''
    text+=f"已尝试任务strict命中率的95% Clopper–Pearson区间：{auxiliary['task_hit_95pct_Clopper_Pearson_per_attempt']}。仅在任务近似独立、同成功概率且截止机制可接受假设下辅助描述，不是跨实例或确认性硬件优胜结论。未启动槽位不被当成随机硬件试验。\n\n"
    text+=f"5000次任务bootstrap，空条件regret子集{empty}次；任务命中分位数{auxiliary['bootstrap_task_hit_quantiles']}，条件中位regret分位数{auxiliary['bootstrap_conditional_median_regret_quantiles']}。命中bootstrap退化={auxiliary['bootstrap_task_hit_degenerate']}；不得用零宽bootstrap冒充无不确定性。\n\n"
    text+='''## 可识别边界与文件

命中指冻结代理表La/Ti/NO2最优，不是材料真实性或五条件实验验证。整数基态性质由本地证书证明；物理返回相对整数基态的能量残差另列，不能因原表regret0就声称整数基态命中。服务端物理开始/结束时间、逐解能量与实际后端未提供；仅披露实际字段，不猜单位。

完整逐任务CSV、strict/partial字段、六指标、G20曲线表和bootstrap空子集计数见同目录。所有原始响应、终态文件、解码和SHA仍在live/及service_audit/；带签名URL的原始记录不外发。
'''
    (out/'REPORT.md').write_text(text)
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(AUDIT.glob('*/result.json'))}
    (out/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'report_dir':str(out.relative_to(ROOT)),'counts':counts,'auxiliary':auxiliary},indent=2))


if __name__=='__main__':main()
