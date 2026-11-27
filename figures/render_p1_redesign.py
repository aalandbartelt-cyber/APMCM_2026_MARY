"""Eight P1 figures redesigned from existing artifacts, with zero new fits."""
from collections import defaultdict
import argparse
import json
from p1_redesign_common import *
from matplotlib.patches import ConnectionPatch


def render_F2():
    fid='F2'; verify_sources(fid)
    rows=read_csv('results/all_domain_metrics.csv')
    routes=['H-soft','additive_ridge','mean','random_hash']
    names=['H-soft','Additive Ridge','Mean','Random (fixed)']
    styles=[(CFG['model'],'o','-'),(CFG['ridge'],'s','--'),
            (CFG['mean'],'v',':'),(CFG['random'],'x','-.')]
    ks=[1,5,10,20,50,100]; data=[]; folds=[]
    for route in routes:
        protocol='outer' if route=='H-soft' else 'baseline'
        domains=[('main_outer_' if route=='H-soft' else 'baseline_')+str(i) for i in range(5)]
        rr=sorted([r for r in rows if r['route']==route and r['protocol']==protocol and r['domain'] in domains],key=lambda r:r['domain'])
        assert len(rr)==5
        for k in ks:
            data.append(dict(route=route,k_per_fold=k,total_budget=5*k,
                hits_total=sum(int(r[f'hits@{k}']) for r in rr),
                EF_macro=float(np.mean([fnum(r,f'EF@{k}') for r in rr]))))
        for i,r in enumerate(rr):
            folds.append(dict(route=route,fold=i+1,N=int(r['N']),M=int(r['M']),
                h=int(r['hits@20']),p_uniform=fnum(r,'p_uniform@20')))
    save_rows(fid,'F2_curve_data.csv',data); save_rows(fid,'F2_fold_uniform_null.csv',folds)
    fig=figure(118)
    a=panel(fig,[.085,.245,.365,.66],'(a) Hits')
    b=panel(fig,[.585,.555,.365,.35],'(b) Enrichment')
    handles=[]
    for j,(route,name,style) in enumerate(zip(routes,names,styles)):
        rr=[r for r in data if r['route']==route]
        color,marker,ls=style
        h=line(a,ks,[r['hits_total'] for r in rr],color,marker,ls,name,j==0)
        handles.append(h)
        line(b,ks,[r['EF_macro'] for r in rr],color,marker,ls,name,j==0)
        # Numeric endpoint labels, including the two low-hit references.
        ya=rr[-1]['hits_total']; yb=rr[-1]['EF_macro']
        a.annotate(str(ya),(100,ya),xytext=(5,3 if route=='random_hash' else (-5 if route=='mean' else 0)),
                   textcoords='offset points',ha='left',va='center',fontsize=8.5)
        if j < 2:
            b.annotate(f'{yb:.2f}',(100,yb),xytext=(5,0),textcoords='offset points',va='center',fontsize=8.5)
    for ax in [a,b]:
        ax.set_xscale('log'); ax.set_xlim(.85,165)
        ax.xaxis.set_major_locator(FixedLocator(ks)); ax.xaxis.set_major_formatter(FixedFormatter([str(k) for k in ks])); ax.xaxis.set_minor_locator(NullLocator())
        if ax is a: ax.set_xlabel('k per fold (log scale)')
        ax.axvline(20,color=CFG['brick'],ls=':',lw=1,zorder=0)
    a.set(ylim=(-4,122),yticks=[0,40,80,120],ylabel='Total hits (five folds)')
    b.set(ylim=(-2.5,85),yticks=[0,20,40,60,80],ylabel='Mean EF@k (V<=2)')
    a.annotate('68/100',(20,68),xytext=(-6,9),textcoords='offset points',ha='right',fontsize=9)
    b.annotate('62.10',(20,62.102380839),xytext=(3,10),textcoords='offset points',ha='left',fontsize=9)
    b.axhline(1,color=EDGE,ls='--',lw=.7,zorder=0)
    b.tick_params(axis='x',labelbottom=False)
    z=panel(fig,[.585,.245,.365,.19],'Zoom: EF 0-1.5')
    z.set_title('',loc='left')
    z.set_title('Zoom: EF 0-1.5',loc='center',fontsize=8.5,pad=8)
    for j in [2,3]:
        rr=[r for r in data if r['route']==routes[j]]
        line(z,ks,[r['EF_macro'] for r in rr],*styles[j])
        z.annotate(f"{rr[-1]['EF_macro']:.2f}",(100,rr[-1]['EF_macro']),xytext=(-4,2),
                   textcoords='offset points',ha='right',va='bottom',fontsize=8.5)
    z.set_xscale('log'); z.set(xlim=(.85,165),ylim=(-.08,1.5),yticks=[0,.5,1,1.5],ylabel='Mean EF@k')
    z.xaxis.set_major_locator(FixedLocator(ks)); z.xaxis.set_major_formatter(FixedFormatter([str(k) for k in ks])); z.xaxis.set_minor_locator(NullLocator())
    z.axhline(1,color=EDGE,ls='--',lw=.6)
    z.axvline(20,color=CFG['brick'],ls=':',lw=1,zorder=0)
    z.set_xlabel('k per fold (log scale)')
    z.tick_params(length=2,pad=2)
    box=Rectangle((1,0),99,1.5,facecolor='#E9EDF0',edgecolor=EDGE,lw=.8,zorder=.5)
    b.add_patch(box)
    for x,edge_x in [(1,0),(100,1)]:
        connector=ConnectionPatch(xyA=(x,0),coordsA=b.transData,xyB=(edge_x,1),coordsB=z.transAxes,
                                  color=EDGE,lw=.6,clip_on=False,zorder=0)
        fig.add_artist(connector)
    for s in z.spines.values():s.set_visible(True);s.set_linewidth(.6)
    fig.legend(handles,names,loc='lower center',bbox_to_anchor=(.52,.075),ncol=4,
               frameon=False,handlelength=2.2,columnspacing=1.25,handletextpad=.45)
    fig.legend(handles=[Line2D([],[],color=CFG['brick'],ls=':',lw=1,label='Budget: k=20'),
                        Line2D([],[],color=EDGE,ls='--',lw=.7,label='Random expectation: EF=1')],
               loc='lower center',bbox_to_anchor=(.52,.018),ncol=2,frameon=False,handlelength=2.2,columnspacing=2)
    return finish(fid,fig,'Near-positive enrichment under AB-blocked validation.',
        'Read the curves at the same per-fold budget k; hits sum the five folds and EF gives each fold equal weight. '
        'The dotted vertical line is k=20, corresponding to 100 selections overall. H-soft gives 68 hits and EF=62.1024, '
        'compared with 10, 1 and 0 hits for additive Ridge, mean and the fixed random realization. The event is V<=2. '
        'Endpoint labels refer to k=100; the separate zoom window enlarges the marked low-EF band of the parent panel, '
        'with matching log-budget coordinates and connector lines. The dashed horizontal line is EF=1, '
        'the uniform-random expectation, not the realized random curve. Per-fold N/M/h and existing unadjusted hypergeometric '
        'p values remain in F2_fold_uniform_null.csv; they are descriptive references after development selection, not a pooled test.',
        dict(folds=5,event='V<=2',k_values=ks,at_k20=[r for r in data if r['k_per_fold']==20]),
        'Four-colour curves, endpoint values, explicit reference keys, boxed low-EF zoom with source region and connectors; no embedded table.')


def render_F3():
    fid='F3'; verify_sources(fid)
    full={r['route']:r for r in read_csv('results/P1_final_experiment_table.csv')}
    order=['H-soft','R-raw','R-log','W-log','additive_ridge','mean']; display=[]
    for route in order:
        r=full[route]; m=fnum(r,'metal_MSE_contribution'); n=fnum(r,'nonmetal_MSE_contribution')
        assert np.isclose(m+n,fnum(r,'RMSE')**2,rtol=1e-12)
        display.append(dict(route=route,metal_contribution=m,nonmetal_contribution=n,total_MSE=m+n,RMSE=fnum(r,'RMSE')))
    pareto=read_csv('results/regression_pareto.csv')
    paired=next(r for r in read_csv('results/paired_AB_bootstrap_5000.csv') if r['model']=='H-soft' and r['reference']=='R-log' and r['metric']=='EF_macro@20')
    save_rows(fid,'F3_MSE_contributions.csv',display); save_rows(fid,'F3_registered_pareto.csv',pareto)
    fig=figure(90)
    a=panel(fig,[.135,.265,.355,.61],'(a) MSE contributions')
    b=panel(fig,[.65,.265,.31,.61],'(b) RMSE-EF')
    yy=np.arange(6)
    a.barh(yy,[r['metal_contribution'] for r in display],height=.64,color=CFG['steel'],edgecolor=EDGE,lw=.4)
    a.barh(yy,[r['nonmetal_contribution'] for r in display],left=[r['metal_contribution'] for r in display],
           height=.64,color=CFG['amber'],edgecolor=EDGE,lw=.4,hatch='///')
    a.set(yticks=yy,yticklabels=['H-soft','R-raw','R-log','W-log','Ridge','Mean'],xlim=(0,142),xticks=[0,40,80,120],xlabel='MSE contribution (V^2)')
    a.invert_yaxis()
    for i,r in enumerate(display):
        a.text(r['total_MSE']+2,i,f"{r['total_MSE']:.2f}",va='center',fontsize=8.5)
    fig.legend(handles=[Patch(facecolor=CFG['steel'],edgecolor=EDGE,label='Metal (gap=0)'),
                        Patch(facecolor=CFG['amber'],edgecolor=EDGE,hatch='///',label='Nonmetal (gap>0)')],
               loc='lower center',bbox_to_anchor=(.31,.015),ncol=1,frameon=False)
    markers={'H-soft':'o','R-log':'s','R-raw':'^','W-log':'D'}
    colors={'H-soft':CFG['model'],'R-log':CFG['green'],'R-raw':CFG['brick'],'W-log':CFG['pink']}
    offsets={'H-soft':(6,10),'R-log':(5,-13),'R-raw':(5,9),'W-log':(-5,-13)}
    for r in pareto:
        route=r['route']; x=fnum(r,'RMSE'); y=fnum(r,'EF@20_mean')
        b.scatter(x,y,s=58 if route=='H-soft' else 34,marker=markers[route],facecolor=colors[route],edgecolor=EDGE,lw=.6,zorder=3)
        b.annotate(route,(x,y),xytext=offsets[route],textcoords='offset points',ha='right' if route=='W-log' else 'left',fontsize=8.5)
    b.set(xlim=(4.48,5.76),ylim=(49,65.7),xticks=[4.5,5,5.5],yticks=[50,55,60,65],
          xlabel='RMSE (V)',ylabel='Mean EF@20 (V<=2)')
    fig.legend(handles=[Line2D([],[],ls='None',marker=markers[r],color=colors[r],markeredgecolor=EDGE,ms=5,label=r)
                        for r in ['H-soft','R-log','R-raw','W-log']],
               loc='lower center',bbox_to_anchor=(.81,.015),ncol=2,frameon=False,handlelength=1,columnspacing=1.0,handletextpad=.4)
    return finish(fid,fig,'Class contributions to error and the regression-screening trade-off.',
        'Each stacked segment is class-specific SSE divided by the total sample count; segment sums equal pooled RMSE squared. '
        'Metal and nonmetal are encoded by steel blue and hatched amber. The six stacked bars are decompositions, not confidence intervals. '
        'The scatter compares only four registered regressors: H-soft is nondominated at RMSE=4.6011 and EF=62.1024. '
        'Its MSE contributions are 18.2920 and 2.8781. H-soft minus R-log EF is +1.6160 with the existing 95% paired AB percentile '
        'interval [-5.9951,11.2022], conditional on frozen OOF and prior selection without multiplicity correction; '
        'the apparent screening advantage is therefore uncertain. No RMSE is assigned to probability-only routes.',
        dict(contributions_sum_to_RMSE_squared=True,registered_routes=[r['route'] for r in pareto],EF_difference=paired),
        'Steel-blue/amber stacked strips plus shape-coded Pareto points; no explanatory text block.')


def render_A1():
    fid='A1'; verify_sources(fid)
    rows=read_csv('results/OOF_residual_scales_by_X.csv')
    assert len(rows)==7 and all(int(r['n'])==1608 for r in rows)
    save_rows(fid,'A1_residual_values.csv',rows)
    fig=figure(87)
    a=panel(fig,[.12,.27,.19,.61],'(a) Bias')
    b=panel(fig,[.45,.27,.50,.61],'(b) Error scale')
    norm=TwoSlopeNorm(vmin=-.25,vcenter=0,vmax=.25)
    for i,r in enumerate(rows):
        val=fnum(r,'bias')
        a.add_patch(Rectangle((0,i-.46),1,.92,facecolor=CMAP(norm(val)),edgecolor='white',lw=1))
        a.text(.5,i,f'{val:+.3f}',ha='center',va='center',fontsize=9)
    a.set(xlim=(0,1),ylim=(6.5,-.5),yticks=range(7),yticklabels=[r['X'] for r in rows],xticks=[],ylabel='X family')
    for s in a.spines.values():s.set_visible(False)
    a.tick_params(length=0)
    for metric,mark,col in [('RMSE','o',CFG['green']),('q95_absolute','D',CFG['pink'])]:
        vals=[fnum(r,metric) for r in rows]
        b.scatter(vals,range(7),s=39,marker=mark,facecolor=col,edgecolor=EDGE,lw=.5,label='RMSE' if metric=='RMSE' else 'q95 absolute error',zorder=3)
        i=int(np.argmax(vals)); v=vals[i]
        b.annotate(f'{v:.2f}',(v,i),xytext=(5,6),textcoords='offset points',fontsize=8.5)
    b.set(ylim=(6.5,-.5),xlim=(0,15.6),xticks=[0,5,10,15],yticks=[],xlabel='Error (V)')
    b.spines['left'].set_visible(False)
    b.legend(frameon=False,loc='lower left',bbox_to_anchor=(-.015,-.38),ncol=2,handletextpad=.4,columnspacing=1)
    colorbar(fig,[.105,.135,.235,.045],norm,'Bias (Vhat - V)',[-.25,0,.25])
    return finish(fid,fig,'Residual bias and error scale across X families.',
        'The left heat strip maps signed mean residual Vhat-V to blue-white-amber, centred at zero; signed values preserve the '
        'encoding in grayscale. The right panel overlays RMSE circles and empirical absolute-residual q95 diamonds on a common '
        'original-V scale. Each family contains 1,608 external OOF predictions from frozen H-soft. N3 has the largest RMSE '
        '(6.6515) and absolute-error q95 (13.8694). These are empirical error summaries, not calibrated prediction intervals.',
        dict(families=7,n_each=1608,bias_colour_limits=[-.25,.25],q95_is_empirical=True),
        'Signed heat strip plus overlaid circle/diamond error scales; blue-white-amber zero-centred colour map.')


def render_A2():
    fid='A2'; verify_sources(fid)
    routes=['B-eps','S-eps','L-single','L-hash4']
    diag={r['route']:r for r in read_csv('results/oof_calibration_consistency.csv') if r['fold']=='pooled'}
    grouped=defaultdict(list)
    for i in range(5):
        for r in read_csv(f'domains/main_outer_{i}.csv.gz'):
            if r['route'] in routes:grouped[r['route']].append(r)
    bins=[]
    for route in routes:
        rr=grouped[route]; assert len(rr)==len({r['id'] for r in rr})==11256
        p=np.array([fnum(r,'score') for r in rr]); y=np.array([fnum(r,'V')<=2 for r in rr])
        assert y.sum()==128 and ((p>=0)&(p<=1)).all()
        assert np.isclose(np.mean((p-y)**2),fnum(diag[route],'brier'),atol=1e-14)
        ix=np.minimum((p*10).astype(int),9)
        for j in range(10):
            mask=ix==j; n=int(mask.sum())
            bins.append(dict(route=route,bin=j+1,left=j/10,right=(j+1)/10,n=n,
                mean_probability=float(p[mask].mean()) if n else '',observed_frequency=float(y[mask].mean()) if n else '',
                hits=int(y[mask].sum()),right_inclusive=j==9))
    save_rows(fid,'A2_reliability_bins.csv',bins)
    save_rows(fid,'A2_existing_pooled_diagnostics.csv',[diag[r] for r in routes])
    fig=figure(136)
    boxes=[[.115,.615,.35,.30],[.60,.615,.35,.30],[.115,.205,.35,.30],[.60,.205,.35,.30]]
    handles=[]
    for i,(route,box,col,marker,ls) in enumerate(zip(routes,boxes,CFG['pool_colours'],['o','s','^','D'],['-','--','-.',':'])):
        ax=panel(fig,box,f'({chr(97+i)}) {route}')
        rr=[r for r in bins if r['route']==route and r['n']>0]
        ax.plot([0,1],[0,1],color=CFG['neutral'],ls='--',lw=.8,zorder=0)
        handles.append(line(ax,[r['mean_probability'] for r in rr],[r['observed_frequency'] for r in rr],col,marker,ls,label=route+' observed'))
        ax.set(xlim=(-.025,1.025),ylim=(-.035,1.075),xticks=[0,.5,1],yticks=[0,.5,1])
        ax.text(.045,.91,f"slope {fnum(diag[route],'calibration_slope'):.2f}",transform=ax.transAxes,fontsize=9)
        if i in [0,2]:ax.set_ylabel('Observed frequency')
        if i in [2,3]:ax.set_xlabel('Mean probability')
    handles.append(Line2D([],[],color=CFG['neutral'],ls='--',lw=.8,label='Ideal: y=x'))
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.53,.012),ncol=3,frameon=False,
               handlelength=2.1,columnspacing=1.4,handletextpad=.5)
    return finish(fid,fig,'External OOF probability reliability.',
        'Curves pair mean stored probability with empirical V<=2 frequency in ten fixed equal-width bins; empty bins are omitted. '
        'Each panel contains 11,256 external OOF observations with 128 near-positives. The diagonal is ideal calibration. '
        'Each curve has one existing pooled slope annotation; full slopes, intercepts, Brier scores and bin counts are supplied '
        'in the companion data/body-table material, not embedded in the image. S-eps slope=1.7617 and intercept=0.9794 indicate '
        'a remaining scale discrepancy. No calibrator was fitted. Sparse high-probability bins, including singleton bins, '
        'remain descriptive; pooled diagnostic curves do not replace the fold-specific EF endpoint.',
        dict(N_per_route=11256,positives_per_route=128,bin_width=.1,coefficients_reused=True,calibrators_fitted=0,
             slope_annotation_only=True,intercepts_in_companion_table=True),
        'Four compact colour-specific reliability panels; diagonal plus one slope value per curve, no numeric text blocks.')


def render_A3():
    fid='A3'; verify_sources(fid)
    members=read_csv('hardening/decision_stability_members.csv')
    summaries={r['pool']:r for r in read_csv('hardening/decision_stability_summary.csv')}
    assert len(members)==80
    quantiles=[]
    for p in POOLS:
        rr=[r for r in members if r['pool']==p]; assert len(rr)==20
        for direction,stem in [('F','decision_regret'),('R','reverse_regret')]:
            vals=np.quantile([fnum(r,stem) for r in rr],[.5,.9,.95,1])
            for q,v in zip(['p50','p90','p95','max'],vals):
                assert np.isclose(v,fnum(summaries[p],stem+'_'+q),rtol=1e-12)
                quantiles.append(dict(pool=p,direction=direction,quantile=q,value=float(v)))
    save_rows(fid,'A3_member_ranks.csv',members); save_rows(fid,'A3_regret_quantiles.csv',quantiles)
    fig=figure(103)
    a=panel(fig,[.08,.18,.38,.67],'(a) Rank distribution')
    b=panel(fig,[.60,.18,.36,.67],'(b) Decision regret')
    for i,p in enumerate(POOLS):
        yy=3-i; rr=[r for r in members if r['pool']==p]
        ranks=np.array([int(r['nominal_rank']) for r in rr]); log_ranks=np.log10(ranks)
        grid=np.linspace(0,log_ranks.max()+.30,300)
        # Fixed graphics kernel, no bandwidth fit, model, or resampling.
        density=np.exp(-.5*((grid[:,None]-log_ranks[None,:])/.12)**2).mean(axis=1)
        density=.34*density/density.max()
        density[-1]=0
        a.fill_between(grid,yy-density,yy+density,color=POOL_COLORS[p],alpha=.72,edgecolor=EDGE,lw=.55,zorder=1)
        order=np.argsort(log_ranks,kind='stable')
        offs=np.zeros(20)
        for val in np.unique(log_ranks):
            ix=np.where(log_ranks==val)[0]; offs[ix]=np.linspace(-.13,.13,len(ix)) if len(ix)>1 else 0
        a.scatter(log_ranks[order],yy+offs[order],s=7,facecolor='white',edgecolor=EDGE,lw=.35,zorder=3)
        a.annotate(str(ranks.max()),(log_ranks.max(),yy),xytext=(4,8),textcoords='offset points',fontsize=8.5)
        for direction,sign in [('R',-1),('F',1)]:
            vals=np.array([next(r['value'] for r in quantiles if r['pool']==p and r['direction']==direction and r['quantile']==q) for q in ['p50','p90','p95','max']])*sign
            # A two-ended quantile whisker, with no stem from the zero axis.
            direction_colour=CMAP(0.0 if sign<0 else 1.0)
            b.plot([vals[0],vals[-1]],[yy,yy],color=direction_colour,lw=1.6,zorder=2)
            for value,marker in zip(vals,['o','^','s','|']):
                b.plot(value,yy,ls='None',marker=marker,ms=5 if marker!='|' else 8,
                       markerfacecolor=direction_colour,markeredgecolor=EDGE,markeredgewidth=.6,zorder=3)
            b.annotate(f'{abs(vals[-1]):.2f}',(vals[-1],yy),xytext=(-4 if sign<0 else 4,8),textcoords='offset points',
                       ha='right' if sign<0 else 'left',fontsize=8.5)
    a.set(xlim=(-.03,np.log10(150)),ylim=(-.6,3.6),yticks=[3,2,1,0],yticklabels=POOLS,
          xticks=np.log10([1,2,5,10,20,50]),xticklabels=['1','2','5','10','20','50'],xlabel='Rank (log scale)',ylabel='Pool')
    b.set(xlim=(-7.7,4.6),ylim=(-.6,3.6),yticks=[3,2,1,0],yticklabels=POOLS,
          xticks=[-6,-4,-2,0,2,4],xticklabels=['6','4','2','0','2','4'],xlabel='Surrogate regret (Vhat)')
    b.axvline(0,color=CFG['neutral'],ls='--',lw=.6,zorder=0,ymax=.90)
    b.legend(handles=[Line2D([],[],color=CMAP(0.0),lw=1.6,label='Reverse cost'),
                      Line2D([],[],color=CMAP(1.0),lw=1.6,label='Forward cost')],
             loc='upper center',bbox_to_anchor=(.52,1.025),ncol=2,frameon=False,
             handlelength=1.2,columnspacing=.9,handletextpad=.4)
    handles=[Line2D([],[],ls='None',marker=m,ms=4,markerfacecolor='white',markeredgecolor=EDGE,color=EDGE,label=q)
             for m,q in [('o','p50'),('^','p90'),('s','p95'),('|','Max')]]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.77,.005),ncol=4,frameon=False,handlelength=.6,columnspacing=.8,handletextpad=.4)
    fig.legend(handles=[Line2D([],[],ls='None',marker='o',ms=3.5,markerfacecolor='white',markeredgecolor=EDGE,label='Member rank')],
               loc='lower center',bbox_to_anchor=(.28,.005),frameon=False,handlelength=1.0,handletextpad=.4)
    return finish(fid,fig,'Nominal-candidate rank distributions and bidirectional regret.',
        'Each violin displays the 20 existing ranks of La|Ti|NO2, with all observations overlaid. Width is a graphics-only '
        'Gaussian-kernel density in log10 rank using fixed bandwidth 0.12; the display is cut at rank 1 and closes 0.30 '
        'log10 units above the largest observed rank. Width is normalized separately within each pool, '
        'not fitted or used for inference. Maximum ranks are annotated. In the right panel, reverse regret is placed left '
        'and forward regret right, using the blue and amber ends of the common diverging palette, with white at zero. '
        'Colour encodes direction only; position encodes cost. Both costs are nonnegative: the leftward sign encodes direction '
        'only. Forward means the nominal choice evaluated in each member table; reverse means each member choice evaluated '
        'in the nominal table. Quantile symbols identify p50/p90/p95 and maxima; no line is anchored at zero. All quantiles '
        'match stored summaries. None of the pools satisfies the registered 0.1 tolerance in both directions for all members. '
        'These are surrogate-table costs, not true-V regret.',
        dict(members=80,n_per_pool=20,quantiles_independently_checked=True,fixed_graphics_kernel_bandwidth_log10=.12,
             bandwidth_estimated=False,negative_side_is_direction_only=True,new_density_model_fits=0),
        'Four coloured violins with raw ranks; diverging two-ended quantile whiskers. No lollipop or zero-anchored stem.')


def label_column(ax, values, x, side, log=False):
    """Separate adjacent numeric labels, retaining leader lines to true values."""
    transform=np.log if log else lambda x:np.asarray(x)
    inverse=np.exp if log else lambda x:np.asarray(x)
    vv=transform(np.asarray(values,dtype=float)); order=np.argsort(vv)
    loc=vv.copy(); span=float(np.ptp(transform(np.asarray(ax.get_ylim()))))
    gap=span*.075
    for j in range(1,len(order)):
        loc[order[j]]=max(loc[order[j]],loc[order[j-1]]+gap)
    # Center the label block near the original values.
    loc-=np.mean(loc-vv)
    for i,(value,label_y) in enumerate(zip(values,inverse(loc))):
        ax.annotate(f'{value:.3f}',(x,value),xytext=(x+side*.16,label_y),
                    textcoords='data',ha='left' if side>0 else 'right',va='center',fontsize=8.5,
                    arrowprops=dict(arrowstyle='-',color=POOL_COLORS[POOLS[i]],lw=.5,shrinkA=2,shrinkB=3))


def render_A4():
    fid='A4'; verify_sources(fid)
    rows=read_csv('hardening/split_half_summary.csv')
    assert len(rows)==8 and all(int(r['n_partitions'])==1000 and int(r['n_underlying_members'])==20 for r in rows)
    by={(r['pool'],r['method']):r for r in rows}
    save_rows(fid,'A4_split_half_values.csv',rows)
    fig=figure(93)
    a=panel(fig,[.085,.23,.35,.65],'(a) Argmin agreement')
    b=panel(fig,[.61,.23,.35,.65],'(b) Cross-table regret')
    configs=[(a,'argmin_agreement',(0,.60),False),(b,'symmetric_cross_table_decision_regret',(.14,3.4),True)]
    pool_styles=dict(zip(POOLS,['-','--','-.',':']))
    for ax,metric,limits,islog in configs:
        if islog:ax.set_yscale('log')
        ax.set(xlim=(-.42,1.43),ylim=limits,xticks=[0,1],xticklabels=['Single','Mean of 10'])
        left=[];right=[]
        for p in POOLS:
            values=[fnum(by[(p,m)],metric) for m in ['single_member','bagged_half10']]
            left.append(values[0]);right.append(values[1])
            obj=line(ax,[0,1],values,POOL_COLORS[p],POOL_MARKERS[p],pool_styles[p])
            obj.set_markerfacecolor('white')
        label_column(ax,left,0,-1,islog);label_column(ax,right,1,1,islog)
        ax.spines['bottom'].set_visible(False);ax.tick_params(axis='x',length=0,pad=8)
        for x in [0,1]:ax.axvline(x,color='#CED8DF',lw=.6,zorder=0)
    a.set(ylabel='Agreement fraction',yticks=[0,.2,.4,.6])
    b.set_ylabel('Mean regret (Vhat; log scale)')
    b.yaxis.set_major_locator(FixedLocator([.2,.5,1,2,3]));b.yaxis.set_major_formatter(FixedFormatter(['0.2','0.5','1','2','3']));b.yaxis.set_minor_locator(NullLocator())
    fig.legend(handles=[Line2D([],[],color=POOL_COLORS[p],marker=POOL_MARKERS[p],markerfacecolor='white',ms=4,lw=1.3,ls=pool_styles[p],label='Pool '+p) for p in POOLS],
               loc='lower center',bbox_to_anchor=(.52,.005),ncol=4,frameon=False,handlelength=1.6,columnspacing=1.4)
    return finish(fid,fig,'Split-half effects of averaging on decision stability.',
        'Each pool connects the single-member reference on the left to the mean of ten members on the right; endpoints '
        'show stored means. The agreement axis is linear and the regret axis logarithmic. Values label the actual endpoints; '
        'short leader lines separate nearby labels without moving data. The 1,000 complementary 10/10 splits reuse the same '
        '20 members, and each single-member reference averages all 100 cross-half pairs. Averaging lowers surrogate regret '
        'in all four pools; agreement in pools 11/12 remains 0.192/0.174. These are dependent split-half stability diagnostics, '
        'not independent replicates or an accuracy test of a future mean-of-twenty table.',
        dict(partitions=1000,underlying_members=20,logarithmic_regret_axis=True,endpoint_values_unchanged=True),
        'Two slope graphs with four pool-specific colours and shapes; no zero baseline stems or lollipop form.')


def render_A5():
    fid='A5'; verify_sources(fid)
    rows=read_csv('results/stress_summary.csv'); detail=read_csv('results/stress_detail.csv')
    by={(r['protocol'],r['route']):r for r in rows}
    full={r['route']:r for r in read_csv('results/P1_final_experiment_table.csv')}
    protocols=['element','target','xleave']; scope=[]; matrix=[]
    columns=[('R-log','RMSE_pooled','RMSE','R-log\nRMSE (V)'),
             ('R-log','EF@20_mean','EF_{V<=2}@20_mean','R-log\nEF@20'),
             ('S-eps','EF@20_mean','EF_{V<=2}@20_mean','S-eps\nEF@20')]
    for pr in protocols:
        rr=[r for r in detail if r['protocol']==pr and r['route']=='R-log']
        valid=[r for r in rr if r['EF@20']]
        scope.append(dict(protocol=pr,evaluations=len(rr),N_evaluated_sum=sum(int(r['N']) for r in rr),
            M_evaluated_sum=sum(int(r['M']) for r in rr),total_budget=sum(min(20,int(r['N'])) for r in rr),
            EF_defined=len(valid),EF_undefined=len(rr)-len(valid),EF_defined_budget=sum(min(20,int(r['N'])) for r in valid)))
        assert all((int(r['M'])==0)==(not r['EF@20']) for r in rr)
        for route,metric,reference,label in columns:
            value=fnum(by[(pr,route)],metric); ref=fnum(full[route],reference)
            matrix.append(dict(protocol=pr,route=route,metric=metric,value=value,OOF_reference=ref,change_pct=100*(value/ref-1)))
    save_rows(fid,'A5_stress_values.csv',rows);save_rows(fid,'A5_protocol_denominators.csv',scope);save_rows(fid,'A5_heatmap_values.csv',matrix)
    fig=figure(88)
    ax=fig.add_axes([.16,.28,.80,.59]); norm=TwoSlopeNorm(vmin=-80,vcenter=0,vmax=80)
    for i,pr in enumerate(protocols):
        for j,(route,metric,ref,label) in enumerate(columns):
            r=next(r for r in matrix if r['protocol']==pr and r['route']==route and r['metric']==metric)
            ax.add_patch(Rectangle((j+.025,i+.025),.95,.95,facecolor=CMAP(norm(r['change_pct'])),edgecolor='white',lw=.8))
            ax.text(j+.5,i+.42,f"{r['value']:.2f}",ha='center',va='center',fontsize=12)
            ax.text(j+.5,i+.73,f"{r['change_pct']:+.1f}%",ha='center',va='center',fontsize=8.5)
    ax.set(xlim=(0,3),ylim=(3,0),xticks=np.arange(3)+.5,xticklabels=[x[3] for x in columns],
           yticks=np.arange(3)+.5,yticklabels=['Element','Target','X-leave'])
    ax.xaxis.tick_top();ax.tick_params(length=0,pad=6)
    for spine in ax.spines.values():spine.set_visible(False)
    colorbar(fig,[.28,.13,.57,.045],norm,'Change from AB-blocked OOF (%)',[-80,-40,0,40,80])
    return finish(fid,fig,'Stress-test outcomes and matched OOF-relative changes: protocol-level evidence, not final-model.',
        'Rows are protocols and columns are route-specific metrics. Large cell labels are the original stored values; small '
        'labels and the blue-white-amber colour encode 100*(stress/reference-1), with zero at the same route\'s AB-blocked OOF '
        'reference. References are R-log RMSE=4.904836, R-log EF=60.486349 and S-eps EF=62.223405. Signed colour indicates raw '
        'change, not a universal better/worse direction: lower RMSE and higher EF are desirable. No estimates are refitted. '
        'Valid EF evaluations are 5/5, 3/3 and 29/35; zero-positive cases remain undefined. Total budgets are 100,60,700 and '
        'defined-EF budgets 100,60,580. Populations, prevalences and budgets differ, so cross-protocol colours cannot rank '
        'extrapolation difficulty. These are R-log/S-eps protocol-level evidence, not final-model H-soft validation.',
        dict(scope=scope,colour_transform='100 * (stress / matched same-route OOF reference - 1)',
             colour_limits_pct=[-80,80],no_undefined_EF_zero_fill=True,added_source_is_existing_main_result=True),
        'Compact 3-by-3 diverging matrix heatmap, original values plus signed percentage changes; no embedded table object.')


def render_A6():
    fid='A6'; verify_sources(fid)
    paired=read_csv('results/paired_AB_bootstrap_5000.csv')
    blocks=[('Electronic','minus_electronic'),('Geometry','minus_geometry'),('X statistics','minus_xstats')]
    metrics=['RMSE','EF_macro@20']; values=[]
    for block,key in blocks:
        for metric in metrics:
            r=next(r for r in paired if r['model']=='H-soft_'+key and r['reference']=='H-soft' and r['metric']==metric)
            values.append(dict(block=block,metric=metric,delta=fnum(r,'delta_point'),low=fnum(r,'delta_p025'),high=fnum(r,'delta_p975'),n_resamples=int(r['n_resamples'])))
    save_rows(fid,'A6_reverse_ablation_intervals.csv',values)
    fig=figure(78)
    a=panel(fig,[.16,.26,.32,.62],'(a) Delta RMSE')
    b=panel(fig,[.62,.26,.34,.62],'(b) Delta EF@20')
    for j,(ax,metric) in enumerate(zip([a,b],metrics)):
        ax.axvline(0,color=CFG['neutral'],ls='--',lw=.8,zorder=0)
        for i,(block,key) in enumerate(blocks):
            r=next(r for r in values if r['block']==block and r['metric']==metric)
            crosses=r['low']<=0<=r['high']
            color=CFG['neutral'] if crosses else (CFG['amber'] if r['delta']>0 else CFG['steel'])
            marker='o' if crosses else 's'
            ax.errorbar(r['delta'],2-i,xerr=[[r['delta']-r['low']],[r['high']-r['delta']]],
                        fmt=marker,ms=5.8 if not crosses else 4.8,color=color,ecolor=color,
                        elinewidth=1.55,capsize=3,capthick=.9,markeredgecolor=EDGE,markeredgewidth=.5,zorder=3)
            ax.annotate(f"{r['delta']:+.4f}" if j==0 else f"{r['delta']:+.2f}",(r['delta'],2-i),
                        xytext=(0,10),textcoords='offset points',ha='center',fontsize=8.5)
        ax.set(ylim=(-.4,2.5),yticks=[2,1,0],yticklabels=[x[0] for x in blocks] if j==0 else [],
               xlabel='Removal - full (V)' if j==0 else 'Removal - full (EF)')
        ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0)
    a.set(xlim=(-.045,.23),xticks=[0,.1,.2])
    b.set(xlim=(-25,7),xticks=[-20,-10,0])
    fig.legend(handles=[Line2D([],[],color=CFG['neutral'],marker='o',ms=4,label='CI crosses 0'),
                        Line2D([],[],color=CFG['amber'],marker='s',ms=4,label='CI above 0'),
                        Line2D([],[],color=CFG['steel'],marker='s',ms=4,label='CI below 0')],
               loc='lower center',bbox_to_anchor=(.57,.015),ncol=3,frameon=False,handlelength=2,columnspacing=1.5)
    return finish(fid,fig,'Reverse-ablation effects with paired bootstrap intervals.',
        'Each point is removal minus full H-soft, with horizontal two-ended 95% paired AB percentile intervals from 5,000 '
        'existing draws. Grey circles mark intervals crossing zero; coloured squares mark intervals excluding zero, '
        'with positive effects amber and negative effects blue. Geometry removal changes RMSE by +0.1396 and EF by -8.7049. '
        'The RMSE and equal-fold EF endpoints are separate panels. Intervals condition on frozen OOF and prior selection, '
        'are exploratory and are not multiplicity-adjusted. Removal uses dependency tags: removing X statistics also '
        'removes dependent geometry, so effects are not orthogonal causal attributions. The earlier R-log F0/F3/F3+E1 ladder '
        'is retained in companion data and moved out of this image as requested. No fit or bootstrap draw is added.',
        dict(removals=values,stored_draws=5000,new_draws=0,EF_endpoint='EF_macro@20',
             intervals_reused=True,forward_ladder_moved_to_companion_data=True),
        'Two-panel forest plot: point estimates, bilateral interval whiskers, vertical zero line; grey crossing-zero effects.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('figures',nargs='+',choices=['all']+list(OUT))
    args=parser.parse_args()
    for fid in list(OUT) if 'all' in args.figures else args.figures:
        globals()['render_'+fid]()
