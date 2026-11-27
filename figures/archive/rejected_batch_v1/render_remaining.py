"""Render F2/F3/A1-A6 from frozen results; never load or fit a model.

Examples:
  /usr/bin/python3.10 -B figures/render_remaining.py F2 F3
  /usr/bin/python3.10 -B figures/render_remaining.py all
"""
from pathlib import Path
import argparse
import csv
import json
from collections import defaultdict
import numpy as np

from p1_plot_common import (
    HERE, ROOT, DATA, COLORS, INK, EDGE, SOURCES, plt, Line2D, Patch,
    FixedLocator, FixedFormatter, NullLocator, verify_sources, read_csv,
    fnum, figure, panel, outlined, line, key, reference, note, table,
    save_rows, export,
)

SCRIPT = Path(__file__).resolve()
EF = 'EF_{V<=2}@20_mean'
POOLS = ['07', '08', '11', '12']


def finish(fid, basename, fig, caption, diagnostics, adaptations):
    return export(fid, basename, fig, caption, diagnostics, adaptations, SCRIPT)


def render_F2():
    fid = 'F2'; verify_sources(fid)
    all_rows = read_csv('results/all_domain_metrics.csv')
    per_fold = read_csv('results/P1_main_per_fold.csv')
    ks = [1,5,10,20,50,100]
    names = {'H-soft':'H-soft','additive_ridge':'Additive Ridge','mean':'Mean','random_hash':'Random (fixed)'}
    styles = {'H-soft':dict(role='S',marker='o',ls='-'),
              'additive_ridge':dict(role='B',marker='s',ls='--',fill=False),
              'mean':dict(role='B',marker='v',ls=':',fill=False),
              'random_hash':dict(role='B',marker='x',ls='-.')}
    groups={}; display=[]; fold_display=[]
    for route in names:
        protocol, prefix = ('outer','main_outer_') if route=='H-soft' else ('baseline','baseline_')
        rr=sorted([r for r in all_rows if r['protocol']==protocol and r['route']==route and r['domain'] in [prefix+str(i) for i in range(5)]], key=lambda r:r['domain'])
        assert len(rr)==5
        groups[route]=rr
        for k in ks:
            for r in rr:
                expected=fnum(r,f'hits@{k}')/k/(fnum(r,'M')/fnum(r,'N'))
                assert np.isclose(expected,fnum(r,f'EF@{k}'))
            display.append(dict(route=route,k_per_fold=k,total_budget=5*k,
                hits_total=sum(int(r[f'hits@{k}']) for r in rr),
                EF_macro=float(np.mean([fnum(r,f'EF@{k}') for r in rr]))))
        for i,r in enumerate(rr):
            peer=[p for p in per_fold if p['route']==route and p['domain']==r['domain']]
            assert len(peer)==1 and peer[0]['h']==r['hits@20']
            assert np.isclose(fnum(peer[0],'p_uniform@20'),fnum(r,'p_uniform@20'),rtol=1e-12,atol=0)
            fold_display.append(dict(route=route,fold=i+1,N=int(r['N']),M=int(r['M']),k=20,
                hits=int(r['hits@20']),p_uniform=fnum(r,'p_uniform@20')))
    assert [next(r['hits_total'] for r in display if r['route']==route and r['k_per_fold']==20) for route in names]==[68,10,1,0]
    save_rows(fid,'F2_curve_data.csv',display); save_rows(fid,'F2_fold_uniform_null.csv',fold_display)
    fig=figure(171)
    note(fig,.978,'Near-positive event: V <= 2  |  Five fixed AB-blocked outer folds',size=9)
    handles=[key(names[r],**styles[r]) for r in names]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.52,.961),ncol=4,
               frameon=False,handlelength=2.2,columnspacing=1.0,handletextpad=.5)
    a=panel(fig,[.105,.585,.355,.305],'(a) Total hits')
    b=panel(fig,[.61,.585,.355,.305],'(b) Mean enrichment')
    for route in names:
        rr=[r for r in display if r['route']==route]
        line(a,ks,[r['hits_total'] for r in rr],label=names[route],**styles[route])
        line(b,ks,[r['EF_macro'] for r in rr],label=names[route],**styles[route])
    for ax in [a,b]:
        ax.set_xscale('log'); ax.set_xlim(.85,118)
        ax.xaxis.set_major_locator(FixedLocator(ks)); ax.xaxis.set_major_formatter(FixedFormatter([str(k) for k in ks])); ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xlabel('Selections per fold, k (log scale)')
        ax.axvline(20,ymax=1 if ax is a else .49,color=EDGE,ls=':',lw=.7,zorder=0)
    a.set(ylim=(-3,125),yticks=[0,40,80,120],ylabel='Hits across five folds')
    b.set(ylim=(-3,130),yticks=[0,40,80,120],ylabel='Mean EF@k (V<=2)')
    a.annotate('68 / 100',xy=(20,68),xytext=(-7,11),textcoords='offset points',ha='right',fontsize=9)
    b.annotate('H-soft: 62.10',xy=(20,62.102380839),xytext=(0,10),textcoords='offset points',ha='center',fontsize=8.5)
    b.axhline(1,color=EDGE,ls=(0,(4,2)),lw=.7,zorder=0)
    note(fig,.514,'Dashed reference: random expectation EF = 1',x=.785,size=8.5)
    # Preserve the observed random realization; the enlarged baseline region
    # makes the overlapping near-zero curves readable without altering values.
    zoom=b.inset_axes([.49,.68,.49,.25])
    for route in ['mean','random_hash']:
        rr=[r for r in display if r['route']==route]
        line(zoom,ks,[r['EF_macro'] for r in rr],**styles[route])
    zoom.axhline(1,color=EDGE,ls=(0,(4,2)),lw=.7)
    zoom.set_xscale('log'); zoom.set(xlim=(.85,118),ylim=(-.08,1.5),yticks=[0,1])
    zoom.xaxis.set_major_locator(FixedLocator([1,100])); zoom.xaxis.set_major_formatter(FixedFormatter(['1','100'])); zoom.xaxis.set_minor_locator(NullLocator())
    zoom.set_title('Low-EF detail',fontsize=8.5,pad=4)
    zoom.tick_params(length=2,pad=1,labelsize=8.5)
    note(fig,.482,'k = 20 per fold: 100 selections total',size=9)
    note(fig,.452,'Each table cell: hits h, then uniform-null p (uncorrected)',size=8.5)
    headers=['Method']+[f"Fold {i+1}\nN={int(r['N']):,}\nM={int(r['M'])}" for i,r in enumerate(groups['H-soft'])]
    table_rows=[]
    for route in names:
        label='Random\n(fixed)' if route=='random_hash' else ('Additive\nRidge' if route=='additive_ridge' else names[route])
        table_rows.append([label]+[f"h={int(r['hits@20'])}\np={fnum(r,'p_uniform@20'):.2e}" for r in groups[route]])
    table(fig,[.065,.095,.91,.32],headers,table_rows,widths=[.16]+[.168]*5)
    note(fig,.047,'N = fold size; M = near-positives. Each fold contributes equally to EF.',size=8.5)
    note(fig,.024,'p values are descriptive uniform-null references after development selection.',size=8.5)
    caption=('H-soft concentrates near-positive samples across the fixed AB-blocked folds. '
        'With 20 selections per fold (100 total), it yields 68 hits and mean EF=62.1024, '
        'versus 10, 1 and 0 hits for additive Ridge, mean and the fixed random realization. '
        'The event is V<=2; hits are summed and EF is averaged equally over the five folds. '
        'Budget axes are logarithmic. The inset enlarges mean/random EF on the same k scale. '
        'The EF=1 line is the uniform-random expectation, not the observed random curve. '
        'The table reports every fold-specific N, M, h and existing unadjusted hypergeometric '
        'p value at k=20. These p values are descriptive uniform-null references after development '
        'selection, not a pooled or selection-adjusted significance test.')
    return finish(fid,'F2_enrichment',fig,caption,dict(folds=5,event='V<=2',k_values=ks,
        at_k20={r['route']:r for r in display if r['k_per_fold']==20},p_values_reused_not_combined=True),
        ['plot_enrichment_bar: EF=1 reference and direct uniform-null statistics',
         'plot_tri_panel_precision: aligned budget curves; explicit baseline detail inset'])


def render_F3():
    fid='F3'; verify_sources(fid)
    full={r['route']:r for r in read_csv('results/P1_final_experiment_table.csv')}
    pareto=read_csv('results/regression_pareto.csv')
    order=['H-soft','R-raw','R-log','W-log','additive_ridge','mean']
    rows=[]
    for route in order:
        r=full[route]; m=fnum(r,'metal_MSE_contribution'); n=fnum(r,'nonmetal_MSE_contribution')
        assert np.isclose(m+n,fnum(r,'RMSE')**2,rtol=1e-12)
        rows.append(dict(route=route,metal_contribution=m,nonmetal_contribution=n,total_MSE=m+n,RMSE=fnum(r,'RMSE')))
    assert len(pareto)==4 and [r['route'] for r in pareto if r['pareto_nondominated']=='True']==['H-soft']
    paired=next(r for r in read_csv('results/paired_AB_bootstrap_5000.csv') if r['model']=='H-soft' and r['reference']=='R-log' and r['metric']=='EF_macro@20')
    assert fnum(paired,'delta_p025')<0<fnum(paired,'delta_p975')
    save_rows(fid,'F3_MSE_contributions.csv',rows); save_rows(fid,'F3_registered_pareto.csv',pareto)
    fig=figure(132)
    note(fig,.976,'Frozen external OOF results  |  Near-positive event: V <= 2',size=9)
    a=panel(fig,[.15,.28,.34,.60],'(a) Error contributions')
    b=panel(fig,[.665,.28,.30,.60],'(b) RMSE-EF trade-off')
    yy=np.arange(6)
    a.barh(yy,[r['metal_contribution'] for r in rows],color=COLORS['M'],edgecolor=EDGE,lw=.45,hatch='//',height=.58)
    a.barh(yy,[r['nonmetal_contribution'] for r in rows],left=[r['metal_contribution'] for r in rows],color=COLORS['N'],edgecolor=EDGE,lw=.45,hatch='..',height=.58)
    a.set(yticks=yy,yticklabels=['H-soft','R-raw','R-log','W-log','Ridge','Mean'],xlim=(0,141),xticks=[0,40,80,120],xlabel='Contribution to MSE (V^2)')
    a.invert_yaxis()
    for y,r in zip(yy,rows):
        a.text(r['total_MSE']+3,y,f"{r['total_MSE']:.2f}",va='center',fontsize=8.5)
    fig.legend(handles=[Patch(facecolor=COLORS['M'],edgecolor=EDGE,hatch='//',lw=.45,label='Metal: SSE / total N'),
                      Patch(facecolor=COLORS['N'],edgecolor=EDGE,hatch='..',lw=.45,label='Nonmetal: SSE / total N')],
        frameon=False,loc='upper center',bbox_to_anchor=(.5,.971),ncol=2,handlelength=1.6,fontsize=8.5)
    # Registered candidates share surrogate color; marker shape and direct
    # labels identify routes. A single nondominated point is not a false line.
    markers={'H-soft':'o','R-log':'s','R-raw':'^','W-log':'D'}
    offsets={'H-soft':(5,12),'R-log':(6,-14),'R-raw':(4,10),'W-log':(-7,-14)}
    for r in pareto:
        route=r['route']; x=fnum(r,'RMSE'); y=fnum(r,'EF@20_mean')
        b.scatter([x],[y],s=45 if route=='H-soft' else 30,marker=markers[route],
            facecolor=COLORS['S'] if route=='H-soft' else 'white',edgecolor=EDGE,linewidth=.7,zorder=3)
        text='H-soft\n(4.6011, 62.1024)' if route=='H-soft' else route
        b.annotate(text,(x,y),xytext=offsets[route],textcoords='offset points',
            fontsize=8.5,ha='right' if route=='W-log' else 'left',va='bottom' if route=='H-soft' else 'center')
    b.set(xlim=(4.48,5.73),ylim=(47,68.5),xticks=[4.5,5,5.5],yticks=[50,55,60,65],xlabel='Pooled RMSE (V)',ylabel='Mean EF@20 (V<=2)')
    b.text(.97,.04,'Lower RMSE; higher EF',transform=b.transAxes,ha='right',fontsize=8.5)
    note(fig,.183,'H-soft MSE: 18.2920 (metal) + 2.8781 (nonmetal) = 21.1701.',size=8.5)
    note(fig,.14,'H-soft is nondominated within the four registered regressors.',size=8.5)
    note(fig,.091,f"H-soft - R-log EF: {fnum(paired,'delta_point'):+.4f}; 95% paired interval [{fnum(paired,'delta_p025'):.4f}, {fnum(paired,'delta_p975'):.4f}].",size=8.5)
    note(fig,.05,'Conditional on fixed OOF and prior selection; the EF interval crosses zero.',size=8.5)
    caption=('H-soft is nondominated within the registered regression menu, while its screening advantage over R-log remains uncertain. '
        'Its pooled RMSE is 4.6011 and its metal/nonmetal contributions to total MSE are 18.2920 and 2.8781. '
        'Each contribution is class-specific SSE divided by the total sample count; stacked sums equal pooled RMSE squared. '
        'Six numeric routes are shown for error decomposition, while the Pareto comparison uses only the four registered regressors. '
        'H-soft minus R-log has an EF difference of +1.6160 with the existing 95% paired AB percentile interval '
        '[-5.9951, 11.2022], conditional on frozen OOF predictions and prior selection without multiplicity correction. '
        'Pure screening routes have no assigned RMSE.')
    return finish(fid,'F3_error_tradeoff',fig,caption,dict(contributions_sum_to_RMSE_squared=True,
        registered_routes=[r['route'] for r in pareto],nondominated=['H-soft'],EF_difference=paired),
        ['plot_pareto_bubble_ledger: cost-quality scatter and direct point labels; no invented frontier segment',
         'plot_dashboard_2x2: aligned diagnostic panels; explicit additive error accounting'])


def render_A1():
    fid='A1'; verify_sources(fid)
    rows=read_csv('results/OOF_residual_scales_by_X.csv')
    selection=json.loads((DATA/'final_selection.json').read_text())
    assert selection['numeric']=='H-soft' and len(rows)==7 and all(int(r['n'])==1608 for r in rows)
    save_rows(fid,'A1_residual_values.csv',rows)
    fig=figure(103)
    note(fig,.965,'Frozen H-soft  |  External OOF residuals  |  n = 1,608 per X family',size=9)
    boxes=[[.125,.21,.21,.63],[.435,.21,.21,.63],[.745,.21,.21,.63]]
    titles=['(a) Signed bias','(b) RMSE','(c) Absolute-error q95']
    metrics=['bias','RMSE','q95_absolute']
    labels=['Mean(Vhat - V)','RMSE (V)','q95(|Vhat - V|)']
    limits=[(-.34,.25),(0,8.1),(0,17)]
    for j,(box,title,metric,xlabel,lim) in enumerate(zip(boxes,titles,metrics,labels,limits)):
        ax=panel(fig,box,title)
        values=[fnum(r,metric) for r in rows]; yy=np.arange(7)
        ax.barh(yy,values,height=.6,color=COLORS['S'],edgecolor=EDGE,linewidth=.5)
        ax.set(yticks=yy,yticklabels=[r['X'] for r in rows] if j==0 else [],xlabel=xlabel,xlim=lim)
        ax.invert_yaxis()
        if j==0:
            ax.set_ylabel('X family'); reference(ax,0,axis='x')
            ax.set_xticks([-.3,0,.2])
        elif j==1: ax.set_xticks([0,2,4,6,8])
        else: ax.set_xticks([0,5,10,15])
        for y,v in enumerate(values):
            inside_negative = j==0 and v < -.2
            ax.annotate(f'{v:+.3f}' if j==0 else f'{v:.2f}',(v,y),xytext=(-4 if v<0 and not inside_negative else 4,0),
                textcoords='offset points',ha='right' if v<0 and not inside_negative else 'left',va='center',fontsize=8.5)
    note(fig,.097,'Bias uses Vhat - V. The dotted line marks zero bias; q95 is an empirical residual quantile.',size=8.5)
    note(fig,.049,'All three panels use the original V scale; q95 is not a calibrated prediction interval.',size=8.5)
    caption=('Small signed biases coexist with substantial differences in error scale across X families. '
        'Each family contains 1,608 external OOF predictions from the frozen H-soft route. '
        'Bias is the mean of Vhat-V, RMSE is the root mean squared residual, and q95 is the '
        'empirical 95th percentile of absolute residuals, all read from the stored summaries. '
        'N3 has the largest RMSE (6.6515) and absolute-error q95 (13.8694); these empirical '
        'quantiles are not calibrated coverage guarantees.')
    return finish(fid,'A1_residual_structure',fig,caption,dict(families=7,n_each=1608,
        signed_bias_definition='Vhat - V',q95_definition='empirical quantile of abs(Vhat - V)'),
        ['plot_tri_panel_precision: three aligned diagnostic panels',
         'plot_dashboard_2x2: zero/reference line and directly labeled bars'])


def render_A2():
    fid='A2'; verify_sources(fid)
    names=['B-eps','S-eps','L-single','L-hash4']
    diagnostics={r['route']:r for r in read_csv('results/oof_calibration_consistency.csv') if r['fold']=='pooled'}
    ranking=read_csv('results/oof_calibration_ranking_checks.csv')
    grouped=defaultdict(list)
    for fold in range(5):
        for row in read_csv(f'domains/main_outer_{fold}.csv.gz'):
            if row['route'] in names: grouped[row['route']].append(row)
    display=[]; counts={}; curves={}
    for route in names:
        rr=grouped[route]; assert len(rr)==len({r['id'] for r in rr})==11256
        p=np.array([fnum(r,'score') for r in rr]); y=np.array([fnum(r,'V')<=2 for r in rr],dtype=float)
        assert ((p>=0)&(p<=1)).all() and int(y.sum())==128
        assert np.isclose(np.mean((p-y)**2),fnum(diagnostics[route],'brier'),atol=1e-14)
        ix=np.minimum(np.floor(p*10).astype(int),9); counts[route]=[]; curves[route]=[]
        for j in range(10):
            mask=ix==j; n=int(mask.sum()); counts[route].append(n)
            entry=dict(route=route,bin=j+1,left=j/10,right=(j+1)/10,n=n,
                mean_probability=float(p[mask].mean()) if n else '',observed_frequency=float(y[mask].mean()) if n else '',
                hits=int(y[mask].sum()),right_inclusive=j==9)
            display.append(entry)
            if n: curves[route].append(entry)
    for route in ['B-eps','L-single','L-hash4']:
        rr=[r for r in ranking if r['route']==route and r['fold']!='pooled']
        assert len(rr)==5 and all(int(r['top20_overlap'])==20 for r in rr)
    save_rows(fid,'A2_reliability_bins.csv',display)
    save_rows(fid,'A2_existing_pooled_diagnostics.csv',[diagnostics[r] for r in names])
    fig=figure(181)
    note(fig,.981,'External OOF probabilities  |  Event: V <= 2  |  N = 11,256; positives = 128',size=9)
    fig.legend(handles=[key('Observed frequency',marker='o'),Line2D([],[],color=EDGE,ls='--',lw=.8,label='Ideal calibration: y = x')],
        frameon=False,loc='upper center',bbox_to_anchor=(.52,.961),ncol=2,columnspacing=2)
    boxes=[[.115,.60,.35,.285],[.615,.60,.35,.285],[.115,.18,.35,.285],[.615,.18,.35,.285]]
    count_y=[(.535,.510),(.535,.510),(.115,.09),(.115,.09)]
    for j,(route,box) in enumerate(zip(names,boxes)):
        ax=panel(fig,box,f'({chr(97+j)}) {route}')
        ax.plot([0,1],[0,1],color=EDGE,lw=.8,ls='--',zorder=1)
        rr=curves[route]
        line(ax,[r['mean_probability'] for r in rr],[r['observed_frequency'] for r in rr])
        ax.set(xlim=(-.025,1.03),ylim=(-.025,1.04),xticks=[0,.5,1],yticks=[0,.5,1],
               xlabel='Mean predicted probability',ylabel='Observed frequency')
        d=diagnostics[route]
        ax.text(.035,.955,f"Slope = {fnum(d,'calibration_slope'):.4f}\nIntercept = {fnum(d,'calibration_intercept'):+.4f}\nBrier = {fnum(d,'brier'):.5f}",
            transform=ax.transAxes,va='top',fontsize=8.5,linespacing=1.25)
        cx=box[0]+box[2]/2
        note(fig,count_y[j][0],'n, bins 1-5: '+', '.join(str(n) for n in counts[route][:5]),x=cx,size=8.5)
        note(fig,count_y[j][1],'n, bins 6-10: '+', '.join(str(n) for n in counts[route][5:]),x=cx,size=8.5)
    note(fig,.066,'Ten fixed bins of width 0.1; empty bins (n=0) are omitted from the curves.',size=8.5)
    note(fig,.041,'Raw/calibrated Top-20 overlap: 20/20 in every fold for B-eps, L-single and L-hash4.',size=8.5)
    note(fig,.016,'Pooled overlap: B-eps 15/20; L-single 16/20; L-hash4 16/20. S-eps: not recorded.',size=8.5)
    caption=('The chained S-eps probability retains a scale discrepancy despite component calibration. '
        'Its stored pooled diagnostic slope is 1.7617 and intercept is 0.9794. The four panels use '
        'the same 11,256 external OOF observations (128 V<=2 cases) and ten pre-specified equal-width '
        'probability bins. Points show the mean stored probability and empirical event frequency in '
        'each nonempty bin; counts are listed in bin order, with the final bin including 1. '
        'Intercepts, slopes and Brier scores are read from existing results; no calibration is refitted. '
        'Raw-versus-calibrated Top-20 overlap is 20/20 within every fold for B-eps, L-single and '
        'L-hash4, but 15/20, 16/20 and 16/20 after pooling, respectively. This comparison is not '
        'recorded for S-eps. Pooled diagnostics assess probability scale and do not replace the '
        'fold-specific screening endpoint; sparse high-probability bins remain descriptive.')
    return finish(fid,'A2_calibration',fig,caption,dict(N_per_route=11256,positives_per_route=128,
        bin_edges=[j/10 for j in range(11)],bin_counts=counts,
        coefficients_reused=True,brier_independently_checked=True,calibrators_fitted=0,
        ranking_overlap_route_order=['B-eps','L-single','L-hash4'],pooled_overlap=[15,16,16]),
        ['plot_dashboard_2x2: four aligned diagnosis panels and reference lines',
         'plot_tri_panel_precision: consistent scale and directly printed diagnostic values'])


def render_A3():
    fid='A3'; verify_sources(fid)
    members=read_csv('hardening/decision_stability_members.csv')
    summaries={r['pool']:r for r in read_csv('hardening/decision_stability_summary.csv')}
    protocol=json.loads((DATA/'hardening/protocol.json').read_text())
    assert protocol['member_count']==20 and protocol['plateau_tolerance_V']==.1
    assert len(members)==80 and all(summaries[p]['near_optimal_plateau']=='False' for p in POOLS)
    quantiles=[]
    for p in POOLS:
        rr=[r for r in members if r['pool']==p]; assert len(rr)==20
        ranks=[int(r['nominal_rank']) for r in rr]
        assert min(ranks)==int(summaries[p]['nominal_rank_min']) and max(ranks)==int(summaries[p]['nominal_rank_max'])
        for direction,stem in [('F','decision_regret'),('R','reverse_regret')]:
            vals=[fnum(r,stem) for r in rr]
            q=np.quantile(vals,[.5,.9,.95,1])
            for suffix,v in zip(['p50','p90','p95','max'],q):
                assert np.isclose(v,fnum(summaries[p],stem+'_'+suffix),rtol=1e-12)
                quantiles.append(dict(pool=p,direction=direction,quantile=suffix,value=float(v)))
    save_rows(fid,'A3_member_ranks.csv',members); save_rows(fid,'A3_regret_quantiles.csv',quantiles)
    fig=figure(142)
    note(fig,.976,'Nominal candidate: La | Ti | NO2  |  20 existing members per pool',size=9)
    markers={'p50':'o','p90':'^','p95':'s','max':'x'}
    fig.legend(handles=[key(q,marker=m,ls='None') for q,m in markers.items()],
        frameon=False,loc='upper center',bbox_to_anchor=(.75,.946),ncol=4,
        handlelength=1.1,columnspacing=.9)
    note(fig,.922,'One dot = one member',x=.28,size=8.5)
    a=panel(fig,[.115,.26,.34,.58],'(a) Nominal rank')
    b=panel(fig,[.605,.26,.35,.58],'(b) Regret quantiles')
    for i,p in enumerate(POOLS):
        yy=3-i; rr=sorted([r for r in members if r['pool']==p],key=lambda r:int(r['member']))
        placed=[]
        candidates=[0]+[s*k*.085 for k in range(1,6) for s in [1,-1]]
        for r in sorted(rr,key=lambda r:(int(r['nominal_rank']),int(r['member']))):
            rank=int(r['nominal_rank'])
            offset=next(off for off in candidates if all(((np.log10(rank)-np.log10(x))/.060)**2+((off-y)/.078)**2 >= 1-1e-9 for x,y in placed))
            placed.append((rank,offset))
            a.scatter([rank],[yy+offset],s=18,facecolor=COLORS['S'],edgecolor=EDGE,lw=.5,zorder=3)
        lo=int(summaries[p]['nominal_rank_min']); hi=int(summaries[p]['nominal_rank_max'])
        a.hlines(yy,lo,hi,color=EDGE,lw=.55,zorder=1)
        a.text(1.035,yy,f'{lo}-{hi}',transform=a.get_yaxis_transform(),ha='left',va='center',fontsize=8.5)
        for j,direction in enumerate(['F','R']):
            yrow=7-(i*2+j)
            vals=[next(q['value'] for q in quantiles if q['pool']==p and q['direction']==direction and q['quantile']==qname) for qname in markers]
            obj,=b.plot(vals,[yrow]*4,color=COLORS['S'],ls='-' if direction=='F' else '--',lw=1.5,zorder=2)
            outlined(obj)
            for (qn,marker),v in zip(markers.items(),vals):
                b.plot(v,yrow,ls='None',marker=marker,ms=4.5,color=EDGE,markerfacecolor=COLORS['S'] if direction=='F' else 'white',markeredgewidth=.6,zorder=4)
            b.text(vals[-1]+.14,yrow,f'{vals[-1]:.2f}',va='center',fontsize=8.5)
    a.set_xscale('log')
    a.set(xlim=(.82,90),ylim=(-.5,3.5),yticks=[3,2,1,0],yticklabels=POOLS,
        xlabel='Nominal rank (log scale)',ylabel='Pool')
    a.xaxis.set_major_locator(FixedLocator([1,2,5,10,20,50]))
    a.xaxis.set_major_formatter(FixedFormatter(['1','2','5','10','20','50']))
    a.xaxis.set_minor_locator(NullLocator())
    a.text(1.035,.98,'Min-max',transform=a.transAxes,ha='left',va='top',fontsize=8.5)
    b.set(xlim=(-.06,7.65),ylim=(-.6,7.6),xticks=[0,2,4,6],yticks=list(range(7,-1,-1)),
        yticklabels=[p+' '+d for p in POOLS for d in ['F','R']],xlabel='Surrogate regret (Vhat scale)')
    reference(b,.1,axis='x')
    note(fig,.17,'F: cost of the nominal choice in each member table (filled markers).',size=8.5)
    note(fig,.127,"R: cost of each member's choice in the nominal table (open markers).",size=8.5)
    note(fig,.083,'Dotted line: 0.1 descriptive tolerance; labels at the right mark maximum regret.',size=8.5)
    note(fig,.04,'No pool passes the registered plateau rule. Surrogate regret is not true-V regret.',size=8.5)
    caption=('Nominal-candidate identity changes have nonzero costs in the existing surrogate tables. '
        'All 20 member ranks are shown for each pool; the pool-08 rank spans 1-72. Nearby ranks '
        'are spread vertically for visibility; ranks use a logarithmic horizontal axis without changing their values. In the right panel, '
        'F measures the nominal choice against the optimum in each member table, and R measures the '
        "member's choice against the optimum in the nominal table. Markers show p50, p90, p95 and maximum "
        'regret; solid/filled versus dashed/open marks distinguish the directions. No pool satisfies '
        'the registered rule requiring both directions to stay within 0.1 for every observed member. '
        'The tolerance is descriptive and all costs are on the surrogate Vhat scale, not physical truth.')
    return finish(fid,'A3_decision_stability',fig,caption,dict(members=80,n_per_pool=20,
        pool08_range=[1,72],quantiles_independently_checked=True,plateau_passes=0,
        jitter='Only deterministic vertical spreading of nearby ranks; logarithmic rank axis; values unchanged'),
        ['plot_dashboard_2x2: separate identity and cost diagnostics',
         'plot_tri_panel_precision: explicit tolerance line and multi-marker comparison'])


def render_A4():
    fid='A4'; verify_sources(fid)
    rows=read_csv('hardening/split_half_summary.csv')
    assert len(rows)==8 and all(int(r['n_partitions'])==1000 and int(r['n_underlying_members'])==20 for r in rows)
    by={(r['pool'],r['method']):r for r in rows}
    save_rows(fid,'A4_split_half_values.csv',rows)
    fig=figure(118)
    note(fig,.975,'1,000 complementary 10/10 splits of the same 20 fixed members',size=9)
    styles={'bagged_half10':dict(role='S',marker='o',ls='None'),
            'single_member':dict(role='B',marker='s',ls='None',fill=False)}
    fig.legend(handles=[key('Mean of 10 members',**styles['bagged_half10']),
                        key('Single-member reference',**styles['single_member'])],
        frameon=False,loc='upper center',bbox_to_anchor=(.52,.943),ncol=2,columnspacing=1.8)
    a=panel(fig,[.115,.255,.34,.59],'(a) Argmin agreement')
    b=panel(fig,[.62,.255,.34,.59],'(b) Cross-table regret')
    for j,method in enumerate(styles):
        xx=np.arange(4)+(-.14 if j==0 else .14)
        agreements=[fnum(by[(p,method)],'argmin_agreement') for p in POOLS]
        line(a,xx,agreements,**styles[method])
        means=[fnum(by[(p,method)],'symmetric_cross_table_decision_regret') for p in POOLS]
        lo=[fnum(by[(p,method)],'symmetric_cross_table_decision_regret_p50') for p in POOLS]
        hi=[fnum(by[(p,method)],'symmetric_cross_table_decision_regret_p95') for p in POOLS]
        for x,l,h in zip(xx,lo,hi):
            obj,=b.plot([x,x],[l,h],color=COLORS[styles[method]['role']],lw=1.5)
            if j==0: outlined(obj)
            b.hlines([l,h],x-.045,x+.045,color=EDGE,lw=.6)
        line(b,xx,means,**styles[method])
        for x,v in zip(xx,agreements):
            a.annotate(f'{v:.3f}',(x,v),xytext=(0,9 if j==0 else -13),textcoords='offset points',
                ha='center',fontsize=8.5)
        for x,v,h in zip(xx,means,hi):
            b.annotate(f'{v:.3f}',(x,h),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8.5)
    for ax in [a,b]:ax.set(xlim=(-.55,3.55),xticks=np.arange(4),xticklabels=POOLS,xlabel='Pool')
    a.set(ylim=(-.04,1),yticks=[0,.25,.5,.75,1],ylabel='Fraction of matching minimizers')
    b.set(ylim=(-.10,3.45),yticks=[0,1,2,3],ylabel='Symmetric regret (Vhat scale)')
    note(fig,.155,'Markers and labels show means. Regret bars span p50-p95 across the stored splits.',size=8.5)
    note(fig,.102,'Single-member reference: average over all 100 cross-half member pairs per split.',size=8.5)
    note(fig,.049,'The splits are dependent; the ranges describe dispersion, not confidence intervals.',size=8.5)
    caption=('Averaging improves observed split-half decision stability while leaving the minimizer uncertain. '
        'Mean-of-ten halves reduce mean symmetric cross-table regret in all four pools. Their argmin '
        'agreement in pools 11 and 12 is still only 0.192 and 0.174. Each of the 1,000 complementary '
        'partitions reuses the same 20 existing members; the single-member reference averages all '
        '100 cross-half member pairs in that partition. Markers and numeric labels show stored means, '
        'and vertical regret ranges show stored p50-p95 dispersion, not confidence limits from '
        'independent experiments. These are ten-versus-ten stability results and do not verify '
        'the accuracy of a future full twenty-member mean table.')
    return finish(fid,'A4_split_half',fig,caption,dict(partitions=1000,underlying_members=20,
        mean10_pool11_agreement=.192,mean10_pool12_agreement=.174,
        ranges='Stored p50-p95 descriptive dispersion, not inferential intervals'),
        ['plot_dashboard_2x2: paired stability and regret diagnostics',
         'plot_tri_panel_precision: direct comparisons with explicit uncertainty semantics'])


def render_A5():
    fid='A5'; verify_sources(fid)
    rows=read_csv('results/stress_summary.csv'); detail=read_csv('results/stress_detail.csv')
    protocols=['element','target','xleave']; names=['Element','Target','X-leave']
    by={(r['protocol'],r['route']):r for r in rows}; scope=[]
    for pr in protocols:
        rr=[r for r in detail if r['protocol']==pr and r['route']=='R-log']
        ss=by[(pr,'R-log')]
        valid=[r for r in rr if r['EF@20']]
        assert len(rr)==int(ss['evaluations']) and len(valid)==int(ss['EF_defined_evaluations'])
        assert all((int(r['M'])==0)==(not r['EF@20']) for r in rr)
        for route in ['R-log','S-eps']:
            route_rows=[r for r in detail if r['protocol']==pr and r['route']==route]
            vv=[fnum(r,'EF@20') for r in route_rows if r['EF@20']]
            assert np.isclose(np.mean(vv),fnum(by[(pr,route)],'EF@20_mean'))
        n=sum(int(r['N']) for r in rr)
        rmse=np.sqrt(sum(fnum(r,'RMSE')**2*int(r['N']) for r in rr)/n)
        assert np.isclose(rmse,fnum(ss,'RMSE_pooled'))
        scope.append(dict(protocol=pr,evaluations=len(rr),N_evaluated_sum=n,
            M_evaluated_sum=sum(int(r['M']) for r in rr),total_budget=sum(min(20,int(r['N'])) for r in rr),
            EF_defined=len(valid),EF_undefined=len(rr)-len(valid),EF_defined_budget=sum(min(20,int(r['N'])) for r in valid)))
    save_rows(fid,'A5_stress_values.csv',rows); save_rows(fid,'A5_protocol_denominators.csv',scope)
    fig=figure(139)
    note(fig,.977,'Near-positive event: V <= 2  |  20 selections per evaluation',size=9)
    note(fig,.943,'protocol-level evidence, not final-model',size=9)
    fig.legend(handles=[Patch(facecolor=COLORS['S'],edgecolor=EDGE,lw=.5,label='R-log'),
                        Patch(facecolor=COLORS['S'],edgecolor=EDGE,lw=.5,hatch='//',label='S-eps')],
        frameon=False,loc='upper center',bbox_to_anchor=(.78,.919),ncol=2,columnspacing=1.7)
    a=panel(fig,[.105,.49,.35,.345],'(a) R-log regression')
    b=panel(fig,[.62,.49,.34,.345],'(b) Screening enrichment')
    vals=[fnum(by[(p,'R-log')],'RMSE_pooled') for p in protocols]
    a.bar(np.arange(3),vals,width=.53,color=COLORS['S'],edgecolor=EDGE,lw=.5)
    for x,v in enumerate(vals):a.annotate(f'{v:.4f}',(x,v),xytext=(0,5),textcoords='offset points',ha='center',fontsize=8.5)
    for j,route in enumerate(['R-log','S-eps']):
        xx=np.arange(3)+(-.18 if j==0 else .18)
        vals=[fnum(by[(p,route)],'EF@20_mean') for p in protocols]
        b.bar(xx,vals,width=.32,color=COLORS['S'],edgecolor=EDGE,lw=.5,hatch=None if j==0 else '//')
        for x,v in zip(xx,vals):b.annotate(f'{v:.2f}',(x,v),xytext=(0,4 if j==0 else 14),textcoords='offset points',ha='center',fontsize=8.5)
    for ax in [a,b]:ax.set(xlim=(-.65,2.65),xticks=[0,1,2],xticklabels=names)
    a.set(ylim=(0,7.5),yticks=[0,2,4,6],ylabel='Pooled RMSE (V)')
    b.set(ylim=(0,68),yticks=[0,20,40,60],ylabel='Mean EF@20 (V<=2)')
    note(fig,.398,'Protocol denominators and budgets',size=9)
    tabrows=[[name,str(r['evaluations']),f"{r['N_evaluated_sum']:,}",f"{r['M_evaluated_sum']:,}",str(r['total_budget']),f"{r['EF_defined']}/{r['evaluations']}"] for name,r in zip(names,scope)]
    table(fig,[.065,.135,.91,.225],['Protocol','Evaluations','Sum N','Sum M','Total budget','EF valid'],tabrows,
        widths=[.18,.18,.17,.14,.18,.15])
    note(fig,.085,'N = evaluated samples; M = V<=2 samples. Sums include repeated element evaluations.',size=8.5)
    note(fig,.046,'Undefined EF (M=0) is omitted, not zero-filled; populations and budgets differ by protocol.',size=8.5)
    caption=('The stress results describe the registered protocols rather than validate the final H-soft model out of domain. '
        'R-log pooled RMSE is 5.7805, 5.1796 and 6.5035 under element, target and X-leave evaluation, '
        'respectively. Screening EF is shown separately for R-log and S-eps, with equal weight per '
        'evaluation where EF is defined. Valid EF counts are 5/5, 3/3 and 29/35; six zero-positive '
        'X-leave evaluations remain undefined. The table includes all-evaluation budgets of 100, '
        '60 and 700 selections; the defined-EF budgets are 100, 60 and 580. N/M sums are evaluation '
        'exposures, including repeated compositions in element tests. Different populations, '
        'prevalences and budgets prevent an ease ranking from cross-protocol EF magnitudes. '
        'These are protocol-level evidence, not final-model results.')
    return finish(fid,'A5_stress_protocols',fig,caption,dict(scope=scope,methods=['R-log','S-eps'],
        no_undefined_EF_zero_fill=True,stored_aggregates_independently_checked=True,
        mandatory_label='protocol-level evidence, not final-model'),
        ['plot_dashboard_2x2: aligned protocol diagnostics and explicit scope table',
         'plot_enrichment_bar: direct enrichment annotations and patterned method keys'])


def render_A6():
    fid='A6'; verify_sources(fid)
    diag=read_csv('results/diagnostic_summary.csv')
    full={r['route']:r for r in read_csv('results/P1_final_experiment_table.csv')}
    pairs=read_csv('results/paired_AB_bootstrap_5000.csv')
    additions=[]
    for feature,label in [('F0','F0'),('F3','F3'),('F4','F3+E1')]:
        if feature=='F4':
            r=full['R-log']; rmse=fnum(r,'RMSE'); ef=fnum(r,EF)
        else:
            r=next(r for r in diag if r['protocol']=='feature' and r['route']=='R-log' and r['feature_set']==feature)
            rmse=fnum(r,'RMSE_pooled'); ef=fnum(r,'EF@20_mean')
        additions.append(dict(route='R-log',feature=label,RMSE=rmse,EF_macro=ef))
    blocks=[('minus_electronic','Electronic'),('minus_geometry','Geometry'),('minus_xstats','X statistics')]
    removals=[]
    for feature,label in blocks:
        r=next(r for r in diag if r['protocol']=='ablation' and r['feature_set']==feature and r['route']=='H-soft')
        for metric,src,ref in [('RMSE','RMSE_pooled','RMSE'),('EF_macro@20','EF@20_mean',EF)]:
            p=next(p for p in pairs if p['model']=='H-soft_'+feature and p['reference']=='H-soft' and p['metric']==metric)
            assert int(p['n_resamples'])==5000 and np.isclose(fnum(r,src)-fnum(full['H-soft'],ref),fnum(p,'delta_point'))
            removals.append(dict(block=label,metric=metric,delta=fnum(p,'delta_point'),low=fnum(p,'delta_p025'),high=fnum(p,'delta_p975'),n_resamples=5000))
    save_rows(fid,'A6_feature_additions.csv',additions); save_rows(fid,'A6_reverse_ablation_intervals.csv',removals)
    fig=figure(158)
    note(fig,.973,'F0: baseline  |  F3: chemistry + geometry  |  E1: added electronic descriptors',size=9)
    a=panel(fig,[.12,.655,.34,.225],'(a) R-log: RMSE')
    b=panel(fig,[.62,.655,.34,.225],'(b) R-log: enrichment')
    for ax,col in [(a,'RMSE'),(b,'EF_macro')]:
        vals=[r[col] for r in additions]
        line(ax,[0,1,2],vals)
        for x,v in enumerate(vals):
            offset=(5,10) if col=='RMSE' and x==1 else (0,9)
            ax.annotate(f'{v:.4f}' if col=='RMSE' else f'{v:.2f}',(x,v),xytext=offset,
                textcoords='offset points',ha='left' if col=='RMSE' and x==1 else 'center',fontsize=8.5)
        ax.set(xlim=(-.35,2.35),xticks=[0,1,2],xticklabels=['F0','F3','F3+E1'],xlabel='Feature set')
    a.set(ylim=(4.80,5.31),yticks=[4.8,5,5.2],ylabel='Pooled RMSE (V)')
    b.set(ylim=(0,74),yticks=[0,20,40,60],ylabel='Mean EF@20 (V<=2)')
    note(fig,.521,'Remove one block from full H-soft (F3+E1)',size=9)
    c=panel(fig,[.185,.19,.275,.235],'(c) H-soft: RMSE change')
    d=panel(fig,[.62,.19,.34,.235],'(d) H-soft: EF change')
    for ax,metric in [(c,'RMSE'),(d,'EF_macro@20')]:
        reference(ax,0,axis='x')
        for i,(_,label) in enumerate(blocks):
            r=next(r for r in removals if r['block']==label and r['metric']==metric); y=2-i
            obj,=ax.plot([r['low'],r['high']],[y,y],color=COLORS['S'],lw=1.5,zorder=2); outlined(obj)
            ax.vlines([r['low'],r['high']],y-.07,y+.07,color=EDGE,lw=.6,zorder=3)
            line(ax,[r['delta']],[y],ls='None')
            ax.annotate(f"{r['delta']:+.4f}" if metric=='RMSE' else f"{r['delta']:+.2f}",
                (r['delta'],y),xytext=(0,9),textcoords='offset points',ha='center',fontsize=8.5,
                bbox=dict(facecolor='white',edgecolor='none',pad=.2))
        ax.set(ylim=(-.55,2.65),yticks=[2,1,0],yticklabels=[label for _,label in blocks] if ax is c else [])
    c.set(xlim=(-.04,.25),xticks=[0,.1,.2],xlabel='RMSE change (V)')
    d.set(xlim=(-26,8),xticks=[-20,-10,0],xlabel='EF@20 change (V<=2)')
    note(fig,.104,'Removal minus full H-soft; dotted line = no change. Points show observed differences.',size=8.5)
    note(fig,.066,'Bars: 95% paired AB percentile intervals from 5,000 existing bootstrap draws.',size=8.5)
    note(fig,.028,'Conditional on fixed OOF and prior selection; exploratory, without multiplicity correction.',size=8.5)
    caption=('Feature additions and reverse ablations support distinct within-route comparisons. '
        'F0 contains the baseline descriptors; F3 adds composition chemistry, missingness and '
        'charge/ionic-geometry descriptors including tau; E1 adds the neutral-atom electronic block. '
        'For R-log, pooled RMSE falls from 5.1954 at F0 to 4.9547 at F3 and 4.9048 at F3+E1; '
        'mean EF rises from 27.05 to 57.37 and 60.49. The lower panels compare H-soft after '
        'removing electronic, geometry or X-statistics blocks with full H-soft, using removal '
        'minus full as the sign convention. Removing geometry increases RMSE by 0.1396 and '
        'decreases EF by 8.7049. Horizontal bars reuse the corrected 95% paired AB percentile '
        'intervals from 5,000 stored resamples; EF uses the equal-fold macro endpoint. '
        'The intervals condition on frozen OOF and prior selection, are exploratory, and have '
        'no multiplicity correction. Removals include tagged dependencies; X-statistics removal '
        'also removes dependent geometry terms, so these are not orthogonal causal effects. '
        'No additional fits, bootstrap draws or selection are performed.')
    return finish(fid,'A6_ablation',fig,caption,dict(additions=additions,removals=removals,
        separate_model_routes=True,stored_draws=5000,new_draws=0,EF_endpoint='EF_macro@20',
        feature_alias={'F4':'F3+E1'}),
        ['plot_dashboard_2x2: four panels separating model routes',
         'plot_tri_panel_precision: labeled feature ladder and zero-reference comparison',
         'plot_pareto_bubble_ledger: direct numerical annotations with no added color semantics'])


RENDERERS={'F2':render_F2,'F3':render_F3,'A1':render_A1,'A2':render_A2,
           'A3':render_A3,'A4':render_A4,'A5':render_A5,'A6':render_A6}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('figures',nargs='+',choices=list(RENDERERS)+['all'])
    args=parser.parse_args()
    selected=list(RENDERERS) if 'all' in args.figures else args.figures
    for fid in selected:RENDERERS[fid]()
