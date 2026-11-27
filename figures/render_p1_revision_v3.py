"""Three targeted visual revisions from frozen artifacts. No training or resampling."""
import argparse
from p1_revision_v3_common import *
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
    b=panel(fig,[.585,.480,.365,.425],'(b) Enrichment')
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
    b.tick_params(axis='x',labelbottom=False,bottom=False)
    b.spines['bottom'].set_visible(False)
    z=panel(fig,[.585,.245,.365,.20],'')
    z.text(.035,.91,'Low-EF zoom',transform=z.transAxes,ha='left',va='top',fontsize=8.5)
    for j in [2,3]:
        rr=[r for r in data if r['route']==routes[j]]
        line(z,ks,[r['EF_macro'] for r in rr],*styles[j])
        z.annotate(f"{rr[-1]['EF_macro']:.2f}",(100,rr[-1]['EF_macro']),xytext=(-4,2),
                   textcoords='offset points',ha='right',va='bottom',fontsize=8.5)
    z.set_xscale('log'); z.set(xlim=(.85,165),ylim=(-.08,1.5),yticks=[0,.5,1,1.5])
    z.xaxis.set_major_locator(FixedLocator(ks)); z.xaxis.set_major_formatter(FixedFormatter([str(k) for k in ks])); z.xaxis.set_minor_locator(NullLocator())
    z.axhline(1,color=EDGE,ls='--',lw=.6)
    z.axvline(20,color=CFG['brick'],ls=':',lw=1,zorder=0)
    z.set_xlabel('k per fold (log scale)')
    z.tick_params(length=2,pad=2)
    # Match the entire horizontal viewport: the two short vertical links now
    # join a compact shared-x enlargement, without a separate floating box.
    box=Rectangle((.85,0),165-.85,1.5,facecolor='#F1F4F6',edgecolor=EDGE,lw=.55,zorder=.5)
    b.add_patch(box)
    for x,edge_x in [(.85,0),(165,1)]:
        connector=ConnectionPatch(xyA=(x,0),coordsA=b.transData,xyB=(edge_x,1),coordsB=z.transAxes,
                                  color='#9AA4AD',lw=.5,clip_on=False,zorder=0)
        fig.add_artist(connector)
    for s in z.spines.values():s.set_visible(True);s.set_linewidth(.55)
    fig.legend(handles,names,loc='lower center',bbox_to_anchor=(.52,.075),ncol=4,
               frameon=False,handlelength=2.2,columnspacing=1.25,handletextpad=.45)
    fig.legend(handles=[Line2D([],[],color=CFG['brick'],ls=':',lw=1,label='Budget: k=20'),
                        Line2D([],[],color=EDGE,ls='--',lw=.7,label='Random expectation: EF=1')],
               loc='lower center',bbox_to_anchor=(.52,.018),ncol=2,frameon=False,handlelength=2.2,columnspacing=2)
    return finish(fid,fig,'Near-positive enrichment under AB-blocked validation.',
        'Read the curves at the same per-fold budget k; hits sum the five folds and EF gives each fold equal weight. '
        'The dotted vertical line is k=20, corresponding to 100 selections overall. H-soft gives 68 hits and EF=62.1024, '
        'compared with 10, 1 and 0 hits for additive Ridge, mean and the fixed random realization. The event is V<=2. '
        'Endpoint labels refer to k=100. The compact lower strip enlarges EF=0-1.5 from the marked parent band; '
        'both panels share the same log-budget viewport, and short vertical connectors mark the correspondence. '
        'The data occupy k=1-100; the identical 0.85-165 viewport adds endpoint-label padding only. '
        'The dashed horizontal line is EF=1, '
        'the uniform-random expectation, not the realized random curve. Per-fold N/M/h and existing unadjusted hypergeometric '
        'p values remain in F2_fold_uniform_null.csv; they are descriptive references after development selection, not a pooled test.',
        dict(folds=5,event='V<=2',k_values=ks,at_k20=[r for r in data if r['k_per_fold']==20],
             zoom_source_bounds=[.85,165,0,1.5],same_log_x_viewport=True,zoom_layout='compact shared-x lower strip'),
        'Four-colour curves with a compact shared-x low-EF enlargement, short vertical connectors and matched reference keys.')


def render_A1():
    fid='A1'; verify_sources(fid)
    rows=read_csv('results/OOF_residual_scales_by_X.csv')
    assert len(rows)==7 and all(int(r['n'])==1608 for r in rows)
    save_rows(fid,'A1_residual_values.csv',rows)
    fig=figure(102)
    a=panel(fig,[.12,.245,.19,.65],'(a) Bias')
    b=panel(fig,[.47,.245,.48,.65],'(b) Error by X family')
    norm=TwoSlopeNorm(vmin=-.25,vcenter=0,vmax=.25)
    for i,r in enumerate(rows):
        val=fnum(r,'bias')
        a.add_patch(Rectangle((0,i-.46),1,.92,facecolor=CMAP(norm(val)),edgecolor='white',lw=1))
        a.text(.5,i,f'{val:+.3f}',ha='center',va='center',fontsize=9)
    a.set(xlim=(0,1),ylim=(6.5,-.5),yticks=range(7),yticklabels=[r['X'] for r in rows],xticks=[],ylabel='X family')
    for s in a.spines.values():s.set_visible(False)
    a.tick_params(length=0)
    for metric,offset,col,hatch in [('RMSE',-.17,CFG['green'],''),
                                   ('q95_absolute',.17,CFG['pink'],'///')]:
        vals=[fnum(r,metric) for r in rows]
        ys=np.arange(7)+offset
        b.barh(ys,vals,height=.28,color=col,edgecolor=EDGE,lw=.35,hatch=hatch,
               label='RMSE' if metric=='RMSE' else 'q95 absolute error',zorder=2)
        for v,y in zip(vals,ys):
            b.annotate(f'{v:.2f}',(v,y),xytext=(3,0),textcoords='offset points',va='center',fontsize=8.5)
    b.set(ylim=(6.5,-.5),xlim=(0,16.1),xticks=[0,5,10,15],
          yticks=range(7),yticklabels=[r['X'] for r in rows],xlabel='Error (V)')
    b.tick_params(axis='y',length=0,pad=6)
    b.legend(frameon=False,loc='lower center',bbox_to_anchor=(.5,-.285),ncol=2,
             handlelength=1.4,handletextpad=.45,columnspacing=1.1)
    colorbar(fig,[.105,.115,.235,.035],norm,'Bias (Vhat - V)',[-.25,0,.25])
    return finish(fid,fig,'Residual bias and error scale across X families.',
        'The left heat strip maps signed mean residual Vhat-V to blue-white-amber, centred at zero; signed values preserve the '
        'encoding in grayscale. Each right-panel row is explicitly labelled with its X family. Solid green bars encode RMSE; '
        'hatched pink bars encode empirical absolute-residual q95. Paired bars start from the same zero on the original-V '
        'scale and carry their values at the ends. The two summaries are not additive and are not stacked. '
        'Each family contains 1,608 external OOF predictions from frozen H-soft. N3 has the largest RMSE '
        '(6.6515) and absolute-error q95 (13.8694). These are empirical error summaries, not calibrated prediction intervals.',
        dict(families=7,n_each=1608,bias_colour_limits=[-.25,.25],q95_is_empirical=True,
             both_panels_explicit_X_labels=True,bar_metrics_not_stacked=True),
        'Unchanged signed-bias heat strip beside labelled paired horizontal bars; values, fill/hatch legend and explicit X-family rows.')


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
    fig=figure(150)
    fig.set_figwidth(150/25.4)
    ax=fig.add_axes([.20,.20,.72,.72]); norm=TwoSlopeNorm(vmin=-80,vcenter=0,vmax=80)
    light_palette=json.loads((HERE/'palette_A5_light_v3.json').read_text())
    light_cmap=LinearSegmentedColormap.from_list('light_steel_white_amber',light_palette['diverging'],N=257)
    for i,pr in enumerate(protocols):
        for j,(route,metric,ref,label) in enumerate(columns):
            r=next(r for r in matrix if r['protocol']==pr and r['route']==route and r['metric']==metric)
            ax.add_patch(Rectangle((j+.015,i+.015),.97,.97,facecolor=light_cmap(norm(r['change_pct'])),edgecolor='white',lw=.8))
            ax.text(j+.5,i+.42,f"{r['value']:.2f}",ha='center',va='center',fontsize=14)
            ax.text(j+.5,i+.66,f"{r['change_pct']:+.1f}%",ha='center',va='center',fontsize=10)
    ax.set(xlim=(0,3),ylim=(3,0),xticks=np.arange(3)+.5,xticklabels=[x[3] for x in columns],
           yticks=np.arange(3)+.5,yticklabels=['Element','Target','X-leave'])
    ax.set_aspect('equal')
    ax.xaxis.tick_top();ax.tick_params(length=0,pad=7)
    for spine in ax.spines.values():spine.set_visible(False)
    from matplotlib.cm import ScalarMappable
    cb=fig.colorbar(ScalarMappable(norm=norm,cmap=light_cmap),cax=fig.add_axes([.28,.102,.60,.023]),
                    orientation='horizontal',ticks=[-80,-40,0,40,80])
    cb.set_label('Change from AB-blocked OOF (%)',fontsize=8.5,labelpad=3)
    cb.ax.tick_params(labelsize=8.5,length=2,pad=2)
    cb.outline.set_linewidth(.45);cb.solids.set_rasterized(False)
    return finish(fid,fig,'Stress-test outcomes and matched OOF-relative changes: protocol-level evidence, not final-model.',
        'Rows are protocols and columns are route-specific metrics. Large cell labels are the original stored values; small '
        'labels and the blue-white-amber colour encode 100*(stress/reference-1), with zero at the same route\'s AB-blocked OOF '
        'reference. References are R-log RMSE=4.904836, R-log EF=60.486349 and S-eps EF=62.223405. Signed colour indicates raw '
        'change, not a universal better/worse direction: lower RMSE and higher EF are desirable. No estimates are refitted. '
        'Valid EF evaluations are 5/5, 3/3 and 29/35; zero-positive cases remain undefined. Total budgets are 100,60,700 and '
        'defined-EF budgets 100,60,580. Populations, prevalences and budgets differ, so cross-protocol colours cannot rank '
        'extrapolation difficulty. These are R-log/S-eps protocol-level evidence, not final-model H-soft validation.',
        dict(scope=scope,colour_transform='100 * (stress / matched same-route OOF reference - 1)',
             colour_limits_pct=[-80,80],no_undefined_EF_zero_fill=True,added_source_is_existing_main_result=True,
             square_canvas=True,square_cells=True,colour_endpoints=light_palette['diverging']),
        'Square canvas and equal-aspect 3-by-3 matrix; lighter blue-white-amber endpoints with unchanged signed scale and values.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("figures", nargs="*", default=["F2", "A1", "A5"])
    args = parser.parse_args()
    renderers = {"F2": render_F2, "A1": render_A1, "A5": render_A5}
    assert set(args.figures) <= set(renderers)
    for fid in args.figures:
        renderers[fid]()
