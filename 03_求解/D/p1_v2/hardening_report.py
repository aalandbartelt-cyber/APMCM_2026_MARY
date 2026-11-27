"""Write the postprocessing report and freeze the future P23 table recipe."""
import json
import pandas as pd
from common import ROOT, OUT, CODE, sha, dump, now
from report import md

HARD = OUT/'hardening'
START = '<!-- P1_HARDENING_2026_11_27 -->'


def main():
    protocol = json.loads((HARD/'protocol.json').read_text())
    choice = json.loads((HARD/'P23_construction_decision.json').read_text())
    assert choice['protocol_sha256'] == sha(HARD/'protocol.json')
    assert choice['construction'] in ('bagged_mean_20', 'single_full_fit')
    freeze = json.loads((OUT/'experiment_freeze.json').read_text())
    frozen = ROOT/'codex/P1_PLANv2.1_FROZEN.md'
    assert sha(frozen) == freeze['plan_sha256']
    stable = pd.read_csv(HARD/'decision_stability_summary.csv', dtype={'pool': str})
    split = pd.read_csv(HARD/'split_half_summary.csv', dtype={'pool': str})
    families = pd.read_csv(HARD/'family_concentration_summary.csv', dtype={'pool': str})
    main_table = pd.read_csv(OUT/'results/P1_final_experiment_table.csv')
    folds = pd.read_csv(OUT/'results/P1_main_per_fold.csv')
    intervals = pd.read_csv(OUT/'results/paired_AB_bootstrap_endpoint_comparison.csv')
    compact = []
    for f, rows in folds.groupby('fold'):
        g = rows.set_index('route'); first = g.iloc[0]
        compact.append(dict(fold=f, N=int(first.N), M=int(first.M), k=20,
            h_H_soft=int(g.loc['H-soft','h']), h_Ridge=int(g.loc['additive_ridge','h']),
            h_mean=int(g.loc['mean','h']), h_random=int(g.loc['random_hash','h']),
            nested_numeric=first.selected_numeric_route, nested_screen=first.selected_screen_route,
            h_nested_screen=int(g.loc['nested_screen','h'])))
    table_cols = ['pool','method','argmin_agreement','top20_overlap_fraction',
                  'top20_jaccard','symmetric_cross_table_decision_regret']
    chosen = choice['construction']
    amendment = f'''

{START}
## 6. P1 收尾加固与 P23 预测表构造冻结（2026-11-27）

本节是 P1 完成后的统计修正与未来接口预登记，不追溯改变 §1–5 的选模规则、候选、权重、预测或 03 决策。原始训练前方案逐字节存为 `codex/P1_PLANv2.1_FROZEN.md`，SHA-256 为 `{sha(frozen)}`，继续匹配 `experiment_freeze.json`。原实验冻结文件和训练核心代码不改。

### 6.1 停止拟合与主统计口径

P1 拟合封闭：914 次已用，86 次余额全部留给 P23 确定性重训。本轮新树/标量校准/Ridge 拟合均为 0；不得新增路线、loss、容量、特征或以 EF/RMSE 点估计改善为目标的尝试。所有修复只读取既有 OOF、基线 JSON 和 20 张 bootstrap 表。

主 EF 终点为 `EF_{{V<=2}}@20_macro_outer_folds = (1/5)*sum_f ((h_f/20)/(M_f/N_f))`。配对 bootstrap 在固定五外折内分别对有向 AB 重采样，所有模型用同一次抽样；每折取 Top-20 再平均，任一折 M=0 则整次宏平均为 NA。重复抽中的 AB 保留全部七 X 和重复次数。RMSE 仍为按行汇总的平方误差均值再开方。旧 pooled 单次 Top-20 区间完整保留为诊断列，不能解释为主 EF 区间。

主表并列八候选、原有加性 Ridge / 训练均值 / 固定随机基线、两条嵌套流程；逐折 N/M/h 和内层选择身份同时给出。固定随机实现的 EF 与理论期望 EF=1 区分报告。重算统计不能触发选模。

### 6.2 决策稳定性判据（先登记、后计算）

名义候选为原 P1 全 02 单模型表的 argmin，tie 仍用 `P1v2.1/tie/<key>` SHA-256。仅用 07/08/11/12 成员表，输出名义候选 rank 中位数/范围、Top-5/20 频率、成员最优—次优间隔及双向 regret：`r_b=Vhat_b(c_nom)-min Vhat_b`，`r_reverse_b=Vhat_nom(argmin Vhat_b)-min Vhat_nom`。均是代理表间决策代价，不能称真实 V/物理 regret。分位数固定 p50/p90/p95/max。

仅当身份轮换且所有已观测成员的双向 regret 均 <=0.1 原 V 单位时称“小代价近优平台”。0.1 是预先登记的描述性容差，与 eps=2 和真实可行性无关；不因结果改容差。前列 Top-5/20 同时报 A 家族、B 家族、家族配对及 X 的占比、HHI、有效家族数与相对池背景占比。家族表固定，Zn/Cd/Hg 归 groups_3_to_12，La 单列；不以集中度优化名单。

### 6.3 P23 构造选择与冻结结论

在新决策结果生成前登记协议 `artifacts/p1_v21/hardening/protocol.json`，SHA-256 `{sha(HARD/'protocol.json')}`。1000 个唯一互补 10/10 切分，种子 270026，左半固定含成员 0 以消除互补重复；所有切分列表已保存。每个切分的单模型对照取两半间全部 100 个成员配对的平均；bagged 对照为两张各自十成员均值表。比较 argmin 一致率、Top-20 重合比例/Jaccard、双向交叉表 regret 的均值。

预登记采用 bagged-mean 的条件同时为：(a) 四池等权 Top-20 重合比例增量 >=0.05；(b) 每池 Top-20 重合不下降；(c) 每池 argmin 一致率不下降；(d) 每池交叉表 regret 不增加；数值容差 1e-12。否则采用全域单模型表。不读 EF、RMSE、真实 V 或隐藏标签来定构造法；不分池选不同构造，也不选成员/权重/种子。

实测结论：**固定采用 `{chosen}`**，检查结果 `{json.dumps(choice['checks'], ensure_ascii=False)}`。四池宏平均 Top-20 重合比例增量 `{choice['macro_top20_overlap_gain']:.6f}`。完整结果见收尾报告与 split_half_summary.csv。1000 个切分复用同 20 成员，不能当作 1000 次独立实验；10 对 10 的稳定性优势只支持均值构造选择，不证明未来全 20 均值的准确率，也不恢复历史盲态。P1 原表和原结果不被均值表替换。

### 6.4 后续 P23 确定性重训配方（本轮不得执行）

1. 训练域仅 02+03，共 15225 行；按 02 原顺序后接 03 原顺序，保留原始 id 并加 source 前缀保证唯一。04 只有组成可预测，绝不进入监督、校准、阈值或构造选择。范围标记统一为 `P23_train02val03`，使用独立产物目录，禁止复用以行号为键的 P1 拟合缓存。
2. 固定 H-soft、F3+E1（代码中的 F4，336 维），与已冻结代码完全相同的中性元素、几何、缺失及特征顺序。完整域门控两折 AB OOF 校准，沿用 `fold_ids(ab,2,'calibration/0')` 和现有单调 sigmoid 配方；再固定此校准器用于全部 20 bootstrap。不得用 P1 的仅 02 校准器冒充 P23 校准器。
3. 树参数和随机种子沿用冻结实现：400 轮、learning_rate=.03、15 leaves、min_child_samples=40、L2=1、4 线程；非金属小头 7 leaves/min_child=10；种子 210026，禁止 early stopping/调参/搜索。两折门控+全域门控+两专家共 5 次树拟合。所有新拟合（包括失败）继续累计到总账 1000 上限，不能重置为 0。
4. 冻结 20 个 AB-bootstrap 数据种子 211026..211045。有向 AB 字符串排序后有放回抽取同数 AB，保留每次抽中组的七 X 及多重性；每成员拟合门控、金属专家、非金属专家共 3 次，60 次合计。顺序依成员 00..19，绝不筛选成员或根据任何效果分数补种子。仅允许相同输入/参数的故障恢复；余额不足时停止，不能悄悄缩减成员数。
5. 每成员先按 `Vhat_b=(1-p_b)*(7.84+max(0,u0_b))+p_b*max(0,u1_b)` 形成完整 float64 表，再按固定选择 `{chosen}` 导出 P23 主系数表。若选择 bagged_mean_20，则 `Vhat_P23(c)=sum_b Vhat_b(c)/20`，不混入全域单模型表、不先平均各头再相乘、不学习权重、不作风险惩罚或分数再标定。全域单表仅留作可追踪基准。
6. 07/08/11/12 从同一完整成员预测阵列按 key 裁切，重叠组成必须逐值一致。显式 allowed mask；不在池中的组合保持 NaN，禁止填 0。screen_score 若需要则为 `-Vhat_P23`，不称概率。保留全部 20 成员、sd/p05/p95 和同一均值表的哈希；这些是固定校准器条件下的模型分散度，不是覆盖保证或 P(V=0)。P2/P3 共享该表，量化/约束比较不得换表。
7. 预留确定性树拟合 5+20*3=65，86 中留 21 次仅供必要同配方故障恢复。标量校准另记一次且禁止搜索。P3 208-bit 复合编码继续保留，未来与 3x104-bit 和 HOBO 降阶同表对照；本轮不训练 P23、不求解、不调用真机。

构造冻结回执：`artifacts/p1_v21/hardening/plan_amendment_freeze.json`；原训练冻结、保护快照和新方案哈希均可追溯。未来实现必须先通过该回执校验。
'''
    plan = ROOT/'codex/P1_PLANv2.md'
    current = plan.read_text()
    # Idempotent regeneration changes only this explicitly marked amendment.
    original = current.split(START)[0].rstrip() if START in current else current.rstrip()
    assert original == frozen.read_text().rstrip(), 'Unexpected concurrent plan edit; preserve it'
    plan.write_text(original + amendment)
    freeze_record = dict(time=now(), status='frozen_before_any_P23_retraining',
        original_plan=str(frozen.relative_to(ROOT)), original_plan_sha256=sha(frozen),
        amended_plan=str(plan.relative_to(ROOT)), amended_plan_sha256=sha(plan),
        protocol_sha256=sha(HARD/'protocol.json'), decision_sha256=sha(HARD/'P23_construction_decision.json'),
        split_half_summary_sha256=sha(HARD/'split_half_summary.csv'), construction=chosen,
        fits_at_freeze=914, remaining_reserved_for_P23=86, P23_executed=False)
    dump(HARD/'plan_amendment_freeze.json', freeze_record)
    summary_cols=['pool','nominal_minimizer','nominal_rank_median','nominal_rank_min','nominal_rank_max',
                  'nominal_top5_frequency','nominal_top20_frequency','nominal_argmin_frequency']
    regret_cols=['pool','decision_regret_p50','decision_regret_p90','decision_regret_p95','decision_regret_max',
                 'reverse_regret_p95','reverse_regret_max','member_best_second_gap_p50','member_best_second_gap_p95']
    baseline = main_table[main_table.route.isin(['H-soft','additive_ridge','mean','random_hash','nested_numeric','nested_screen'])]
    interval = intervals[(intervals.model=='H-soft') & (intervals.reference=='R-log')]
    no_plateau = not stable.near_optimal_plateau.any()
    interpretation = ('四池均未达到预先登记的近优平台标准。不能仅凭身份轮换称为“失控”，也不能把这里非零的代价称为“都极小”。'
                      if no_plateau else '达到预先登记小代价标准的池明确标为近优平台，其他池保留代价与身份轮换的区别。')
    report=f'''# P1 收尾加固验收报告

日期：2026-11-27。四项产物均已落盘，机器验收回执为 `artifacts/p1_v21/hardening/hardening_audit.json`。本轮只处理既有表，未改变模型路线、loss、参数、校准器、候选选择或 P1 预测。拟合账本仍为 **914**，剩余 **86** 全部保留给后续 P23。

## P0-1：主 EF 与配对区间口径一致

主终点为五个固定外折内各取 Top-20 后等权平均的 `EF_{{V<=2}}@20`。5000 次配对 bootstrap 在每个外折内分别重采样有向 AB，所有模型共享频数；任一折 M=0 时整次宏平均无定义。实际所有 5000 次均有效。RMSE 按行汇总。以下差均为 H-soft − R-log：

{md(interval,['metric','delta_point','delta_p025','delta_p975','legacy_pooled_delta_p025','legacy_pooled_delta_p975'])}

数值误差改善的条件区间仍低于零；宏平均 EF 差区间跨零，不能声称筛选优势稳定成立。旧 pooled 区间保留在独立文件和 legacy_pooled_* 诊断列；它的 EF 是一次全池 Top-20，与五折总预算 100 的主终点不同，禁止混用。区间均条件于固定 OOF/既往选择，未经多重区间校正，不包含重新研究选模的不确定性。

## P0-2：四池决策稳定性与代价

名义候选来自原全 02 单模型表。rank 为候选在各成员表中的名次，频率分母为既有 20 成员，固定 tie hash。

{md(stable,summary_cols)}

正向 regret 是成员表上坚持名义候选的损失；反向 regret 是名义表上改选成员最优的损失。两者均在原 V 的代理输出尺度，**不是真实 V regret**。成员间隔是该成员最优与次优的值差。

{md(stable,regret_cols)}

{interpretation} 预登记容差为双向 regret 的全部已观测值均 <=0.1；此描述性阈值不是物理可行阈值，也与 eps=2 无关。11/12 的名义候选始终在成员 Top-20 中，但 argmin 并不固定；08 的候选名次范围为 1–72。rank、频率、p50/p90/p95/max 和全部 80 成员记录均保留，不能只报中位数。

名义 Top-20 家族集中度如下；完整 Top-5/20 和全部 20 成员的 HHI/有效家族数/背景归一化占比见 family_concentration_detail.csv 与 summary.csv。

{md(families[(families.k==20)&(families.axis.isin(['A_family','B_family','X']))],['pool','axis','nominal_dominant_family','nominal_dominant_share','nominal_dominant_enrichment','nominal_HHI','member_HHI_p50'])}

例如 11 池名义 Top-20 中 B 的 groups_3_to_12 占 90%，相对池背景为 1.665 倍；需要保留家族集中的适用边界。07/11 本来只含 NO2，X 占比 100% 只是池定义，不能冒称模型额外偏好。52 元素映射固定且完整，La 单列，Zn/Cd/Hg 包含在 groups_3_to_12 中；不把形式氧化态当已知真值。

## P0-3：主表补齐原有基线及嵌套身份

主汇总共 13 行：8 候选、3 固定基线、2 嵌套流程；逐折明细共 65 行。全部基线直接读取既有 domains/baseline_*.json，未重新拟合。RMSE 是各折 SSE 加总再除总 N 后开方，不是五个 RMSE 的算术平均；金属/非金属贡献相加等于 RMSE 平方。

{md(baseline,['route','row_kind','RMSE','metal_MSE_contribution','nonmetal_MSE_contribution','EF_{V<=2}@20_mean','hits20_sum','h_per_fold'])}

{md(pd.DataFrame(compact))}

完整主表每行同时保存 N/M/h 向量、嵌套数值与筛选选择身份、该行实际模型身份。mean 的唯一一次命中与固定随机实现的零命中如实报告；随机对照理论期望 EF=1，不能替换观测值。基线未加入新的自适应选型。候选表与嵌套流程有不同推断身份，不能重复计作独立证据。

## P0-4：只按稳定性冻结 P23 均值表规则

1000 个固定互补 10/10 split-half；单模型基准为每次切分两半间全部 100 个成员对的平均，均值表基准为两半各十成员的算术均值。使用同一候选池、同一 tie hash。Top-20 overlap 是重合数/20，regret 是双方在对方表上采用自己选择时的损失均值。

{md(split,table_cols,digits=6)}

固定条件全部满足，未来采用 **{chosen}**。四池宏平均 Top-20 overlap 增量为 {choice['macro_top20_overlap_gain']:.6f}；没有查看 EF、RMSE 或隐藏真值来挑构造方法。11/12 池十成员均值间 argmin 一致率仍仅 0.192/0.174，均值构造改善了已观测稳定性，不能称最优身份已稳定。

1000 个切分共享 20 个经验成员，不是 1000 次独立实验；split-half 分位数是描述性分散度，不是独立样本置信区间。10 对 10 支持平均化的稳定性，不是对未来全 20 均值准确率的直接验证。原 P1 模型与表保持不变，03 不被重开选模。

`codex/P1_PLANv2.md` §6 已写死未来配方：02+03 固定 H-soft F3+E1、两折 AB OOF 门控校准一次后固定、20 个预定 AB-bootstrap 种子、先按成员计算完整 H-soft 混合 Vhat 再等权平均；相同均值表进 P2/P3，显式 mask/NaN、原尺度 float64 和全部成员分散度保留。预计 65 次确定性树拟合，余下 21 次只留同配方故障恢复。**本轮未执行这 65 次重训，也未求解 P2/P3。**

## 验收与证据索引

- 主结果：`codex/P1_RESULTS_v2.1.md`、`codex/P1_FINAL_RESULTS_v2.1.csv`；逐折：`artifacts/p1_v21/results/P1_main_per_fold.csv`。
- 修正区间：`results/paired_AB_bootstrap_5000.csv`；新旧并列：`results/paired_AB_bootstrap_endpoint_comparison.csv`；原始 pooled 字节保留在 `results/paired_AB_bootstrap_pooled_diagnostic_legacy.csv`。
- 稳定性：`hardening/decision_stability_summary.csv`、`decision_stability_members.csv`、`decision_stability_leading_candidates.csv`、`decision_stability_all_candidates.csv.gz`、`family_concentration_*.csv`。
- Split-half：`hardening/protocol.json`、`split_half_detail.csv.gz`、`split_half_summary.csv`、`P23_construction_decision.json`。全 20 均值与原单表的比较另存 nominal_vs_mean20_diagnostic.csv，仅作描述，不用于选择。
- 原方案：`codex/P1_PLANv2.1_FROZEN.md`；方案增补冻结：`hardening/plan_amendment_freeze.json`。初始保护快照：`hardening/protected_before.json`。
- 验收代码：`03_求解/D/p1_v2/test_hardening.py`、`hardening_audit.py`；验收回执 `hardening/hardening_audit.json`。原 P1 防泄漏审计另存 `final_audit.json`。

仍只能声称指定开发协议中的回归误差、近正例富集和代理决策稳定性；不能声称已验证隐藏 V=0、真实物理最优、可合成性或恢复历史盲态。未新增模型搜索、未提交真机、未改正式论文/交付件。
'''
    (ROOT/'codex/P1_HARDENING_REPORT.md').write_text(report)
    print(json.dumps({'report_written': True, 'P23_construction_frozen': chosen, 'new_fits': 0}))


if __name__ == '__main__':
    main()
