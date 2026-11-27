"""A5 colour-only revision; square layout and frozen source values unchanged."""
from p1_revision_v4_common import *


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
    muted_palette=json.loads((HERE/'palette_A5_reference_v4.json').read_text())
    muted_cmap=LinearSegmentedColormap.from_list('muted_steel_white_amber',muted_palette['diverging'],N=257)
    text_contrasts=[]
    def luminance(rgb):
        rgb=np.asarray(rgb,dtype=float)
        linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        return float(linear@[.2126,.7152,.0722])
    cell_ink=muted_palette['cell_text']
    ink_lum=luminance([int(cell_ink[k:k+2],16)/255 for k in (1,3,5)])
    for i,pr in enumerate(protocols):
        for j,(route,metric,ref,label) in enumerate(columns):
            r=next(r for r in matrix if r['protocol']==pr and r['route']==route and r['metric']==metric)
            fill=muted_cmap(norm(r['change_pct']))
            lum=luminance(fill[:3])
            ink_contrast=(lum+.05)/(ink_lum+.05)
            foreground=cell_ink
            text_contrasts.append(dict(protocol=pr,route=route,metric=metric,
                text_colour=foreground,contrast_ratio=ink_contrast))
            ax.add_patch(Rectangle((j+.015,i+.015),.97,.97,facecolor=fill,edgecolor='white',lw=.8))
            ax.text(j+.5,i+.42,f"{r['value']:.2f}",ha='center',va='center',fontsize=14,color=foreground)
            ax.text(j+.5,i+.66,f"{r['change_pct']:+.1f}%",ha='center',va='center',fontsize=10,color=foreground)
    ax.set(xlim=(0,3),ylim=(3,0),xticks=np.arange(3)+.5,xticklabels=[x[3] for x in columns],
           yticks=np.arange(3)+.5,yticklabels=['Element','Target','X-leave'])
    ax.set_aspect('equal')
    ax.xaxis.tick_top();ax.tick_params(length=0,pad=7)
    for spine in ax.spines.values():spine.set_visible(False)
    from matplotlib.cm import ScalarMappable
    cb=fig.colorbar(ScalarMappable(norm=norm,cmap=muted_cmap),cax=fig.add_axes([.28,.102,.60,.023]),
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
             square_canvas=True,square_cells=True,colour_endpoints=muted_palette['diverging'],
             cell_text_contrasts=text_contrasts,minimum_cell_text_contrast=min(x['contrast_ratio'] for x in text_contrasts)),
        'Square matrix with the same blue-white-amber map as A1 and dark cell labels; unchanged scale, geometry and values.')


if __name__ == "__main__":
    render_A5()
