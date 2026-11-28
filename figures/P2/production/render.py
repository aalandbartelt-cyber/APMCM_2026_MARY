"""Render P2 review plates using the archived figure specification and local inputs."""
import csv, json, sys, hashlib
from pathlib import Path
from datetime import timezone, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors, patches, ticker, dates
from matplotlib.lines import Line2D
from matplotlib.collections import LineCollection
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
from PIL import Image
import numpy as np
import pandas as pd
from scipy.stats import norm

HERE=Path(__file__).resolve().parent
P2=HERE.parent
ROOT=P2.parents[1]
sys.path.insert(0,str(Path.home()/'.codex/skills/mary-modeling-contest-pipeline-apmcm/assets'))
from apmcm_d_plot_templates import apply_apmcm_style,use_times_new_roman
apply_apmcm_style()
use_times_new_roman()
plt.rcParams.update({'font.size':9,'axes.labelsize':9,'xtick.labelsize':8.5,'ytick.labelsize':8.5,
                     'legend.fontsize':8.5,'axes.titlesize':10,'pdf.fonttype':42,'savefig.bbox':None,
                     'axes.linewidth':.65,'xtick.major.width':.6,'ytick.major.width':.6,
                     'text.color':'#262B32','axes.labelcolor':'#262B32','axes.edgecolor':'#565B60',
                     'xtick.color':'#3B4046','ytick.color':'#3B4046','figure.facecolor':'white',
                     'axes.facecolor':'white','legend.frameon':False,'lines.linewidth':1.45})
S,B,Q,G,W,P='#587AA4','#737579','#DC9848','#7C9C8B','#B65D48','#B78CA2'
INK='#29323A'; PALE='#D8E7ED'; LIGHT='#EAECEF'
DIV=colors.LinearSegmentedColormap.from_list('steel-white-amber',['#416796','#FAFAF8','#CC873C'])
SEQ=colors.LinearSegmentedColormap.from_list('blue-count',['#F6F7F7','#C5DCE8','#83A7C3','#365977'])
SPEC=json.loads((P2/'specs/specifications.json').read_text())
specs={s['id']:s for s in SPEC['figures']}
def data(name): return pd.read_csv(P2/'data'/name)
def load(path): return json.loads((ROOT/path).read_text())
def src(i,k=0): return ROOT/specs[i]['files'][k]
def fig(w,h): return plt.figure(figsize=(w/25.4,h/25.4))
def ax(f,xy): return f.add_axes(xy)
def title(a,label): a.set_title(label,loc='left',pad=5)
def key(color,marker='o',line='-',label='',open_=False):
    return Line2D([],[],color=color,marker=marker,linestyle=line,markerfacecolor='white' if open_ else color,markersize=4,label=label)
def note(a,x,y,t,**kw): return a.text(x,y,t,transform=a.transAxes,fontsize=8.5,**kw)
def arrow(f,a,b,curve=0):
    f.add_artist(patches.FancyArrowPatch(a,b,transform=f.transFigure,arrowstyle='-|>',mutation_scale=11,
        connectionstyle=f'arc3,rad={curve}',lw=1.15,color='#6E7A86',clip_on=False))
def soft_grid(a): a.grid(axis='y',color='#E8EAEC',lw=.45,zorder=0);a.set_axisbelow(True)
def legend(f,handles,y=0.02,cols=2):
    f.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,y),ncol=cols,columnspacing=1.6,handlelength=1.8)
def barlabel(a,v,y,t): a.annotate(t,(v,y),xytext=(4,0),textcoords='offset points',va='center',fontsize=8.5)
def f1():
    f=fig(170,100)
    xs=np.linspace(.11,.89,5)
    for i,(x,t) in enumerate(zip(xs,['Candidate\npools','Frozen proxy\nprediction','Enumerated\nlandscape','Piecewise\ncost map','Blind pool only\n40-chain encoding'])):
        f.add_artist(patches.FancyBboxPatch((x-.081,.805),.162,.133,transform=f.transFigure,
              boxstyle='round,pad=0.003,rounding_size=0.012',fc=['#EEF2F4','#DDECF4','#E7EEE9','#F8EEDE','#E2EAF0'][i],ec='#87929B',lw=.65))
        f.text(x,.872,t,ha='center',va='center',fontsize=9.5)
        if i<4: arrow(f,(x+.083,.872),(xs[i+1]-.083,.872))
    vals=[]
    cm=plt.get_cmap('viridis').copy();cm.set_bad('#E4E4E3')
    for i,code in enumerate(['07','11']):
        z=np.load(src('F1',i)); mask=z['allowed'][:,:,0]; v=z['vhat'][:,:,0]
        enum=pd.read_csv(src('F1',2+i));np.testing.assert_allclose(np.sort(v[mask]),enum.vhat)
        assert enum.iloc[0]['key']=='La|Ti|NO2' and mask.sum()==[2704,529][i]
        vals.append(enum.vhat.to_numpy())
        a=ax(f,[[.073,.26,.22,.40],[.335,.26,.22,.40]][i])
        im=a.pcolormesh(np.arange(53)-.5,np.arange(53)-.5,np.ma.array(v,mask=~mask),cmap=cm,vmin=0,vmax=62,shading='flat',ec='none')
        a.set(xlim=(-.5,51.5),ylim=(51.5,-.5),aspect='equal')
        if i==1:
            yy,xx=np.nonzero(~mask)
            a.add_collection(LineCollection(np.stack([np.c_[xx-.20,yy+.20],np.c_[xx+.20,yy-.20]],axis=1),color='#B0B6B9',lw=.19))
        jj=np.where(z['B']=='Ti')[0][0]; ii=np.where(z['A']=='La')[0][0]
        a.plot(jj,ii,'*',ms=8,mec=INK,mew=.65,mfc='#FFF19B')
        title(a,['(a) Full pool · 2,704','(b) Blind pool · 529'][i]);a.set_xlabel('B-site index',labelpad=.2);a.set_ylabel('A-site index' if i==0 else '')
        a.set_xticks([0,25,51],[1,26,52]);a.set_yticks([0,25,51],[1,26,52])
    cb=f.colorbar(im,cax=ax(f,[.085,.11,.20,.033]),orientation='horizontal',ticks=[0,30,60]);cb.set_label('Proxy violation',labelpad=0)
    f.legend(handles=[patches.Patch(fc='#E4E4E3',ec='#A4A4A4',hatch='///',label='Excluded'),Line2D([],[],ls='',marker='*',mec=INK,mfc='#FFF19B',markersize=7,label='LaTiO₂N')],loc='center',bbox_to_anchor=(.443,.10),frameon=False)
    a=ax(f,[.665,.235,.31,.49]); bins=np.arange(0,66,3)
    for i,(v,c) in enumerate(zip(vals,[B,S])):
        h,_=np.histogram(v,bins);assert h.sum()==len(v)
        a.stairs(h*100/len(v),bins,color=c,linestyle=['--','-'][i],lw=1.5,label=['Full','Blind'][i])
    m=vals[0][0];a.axvline(m,color=W,ls=':',lw=1.1);a.annotate('LaTiO₂N\n1.839',(m,1),xytext=(16,6),arrowprops=dict(arrowstyle='->',lw=.65,color=W),fontsize=8.5,bbox=dict(fc='white',ec='none',alpha=.9,pad=1))
    title(a,'(c) Enumerated values');a.set_xlabel('Frozen proxy violation');a.set_ylabel('Pool share per bin (%)');a.legend(loc='upper right',handlelength=1.2)
    return f
def f2():
    f=fig(168,89)
    for i,(path,t) in enumerate([(src('F2',0),'(a) Double one-hot'),(src('F2',3),'(b) Packed short chains')]):
        J=np.load(path)['J'];n=len(J);v=np.abs(J).max()
        a=ax(f,[.085+i*.49,.255,.33,.64]);title(a,t)
        scale=colors.SymLogNorm(linthresh=1,vmin=-v,vmax=v,base=10)
        if i==0:
            im=a.pcolormesh(np.arange(n+1)-.5,np.arange(n+1)-.5,J,cmap=DIV,norm=scale,shading='flat');a.set(xlim=(-.5,n-.5),ylim=(n-.5,-.5),aspect='equal')
            for u in [51.5,103.5]:
                a.axhline(u,c='#758189',lw=.45);a.axvline(u,c='#758189',lw=.45)
            a.set_xticks([25,77,104],['A','B','Ref.']);a.set_yticks([25,77,104],['A','B','Ref.'])
        else:
            y,x=np.nonzero(J);a.scatter(x,y,c=J[y,x],cmap=DIV,norm=scale,marker='s',s=1.7,lw=0)
            a.set(xlim=(-6,n+3),ylim=(n+3,-6),aspect='equal')
            a.set_xticks([0,244,489],['1','245','Ref.']);a.set_yticks([0,244,489],['1','245','Ref.'])
            # The most densely occupied row/column is the reference. The inset shows
            # all entries in the upper-left 26-spin region at an identifiable scale.
            ins=a.inset_axes([.075,.11,.385,.385]); sub=J[:26,:26]
            ins.pcolormesh(np.arange(27)-.5,np.arange(27)-.5,sub,cmap=DIV,norm=scale,shading='flat')
            ins.set(xlim=(-.5,25.5),ylim=(25.5,-.5),xticks=[],yticks=[],aspect='equal')
            for spine in ins.spines.values():spine.set_visible(True);spine.set_color('#81909B');spine.set_linewidth(.55)
            ins.axhline(12.5,c='#AFBAC1',ls=':',lw=.65);ins.axvline(12.5,c='#AFBAC1',ls=':',lw=.65)
            ins.set_title('Chains 1–2',fontsize=8.5,pad=2)
            a.add_patch(patches.Rectangle((-.5,-.5),26,26,fill=False,ec=INK,lw=.65))
            a.annotate('',xy=(25,24),xytext=(67,230),arrowprops=dict(arrowstyle='-',color='#81909B',lw=.55))
        for s in ['top','right']:a.spines[s].set_visible(True)
        cax=ax(f,[.16+i*.49,.147,.19,.025]); cb=f.colorbar(plt.cm.ScalarMappable(norm=scale,cmap=DIV),cax=cax,orientation='horizontal',ticks=[-v,0,v])
        cb.ax.set_xticklabels([f'−{v:.0f}','0',f'+{v:.0f}'])
        f.text(.25+i*.49,.04,['105 spins · 8-bit legality failed','490 spins · G1 and G2 certified'][i],ha='center',fontsize=9)
    return f
def f3():
    d=data('task_margin.csv');f=fig(170,89);a=ax(f,[.095,.245,.59,.64]);x=np.arange(len(d))
    a.fill_between([4.6,24.45],84,188,color=PALE,alpha=.55)
    a.axhline(196,c=W,ls='--');a.text(.5,197.5,'196  decision boundary',va='bottom',color=W,fontsize=8.5)
    a.axvline(4.5,c=B,lw=.6,ls=':');a.vlines(x,d.min_residual,d.max_residual,color=B,lw=1.3)
    a.scatter(x,d.max_residual,s=20,marker='s',facecolor='white',edgecolor=B,zorder=3)
    a.scatter(x,d.min_residual,s=12,color=S,zorder=4)
    a.set(ylim=(75,215),xlim=(-.8,24.8),ylabel='Integer energy above ground',xlabel='Optimization task')
    a.set_xticks([0,4,9,14,19,24],['P01','P05','F05','F10','F15','F20'],rotation=35,ha='right')
    title(a,'(a) Returned sets');a.set_yticks([84,120,160,188])
    b=ax(f,[.795,.285,.18,.54]); rr=d.set_index('slot');v=[rr.loc['F03','selected_margin'],rr.loc['F14','set_min_margin']]
    bars=b.bar([0,1],v,color=[S,'white'],edgecolor=[S,W],lw=1.25,width=.62,hatch=None);bars[1].set_hatch('///')
    b.bar_label(bars,labels=['20','8'],padding=2);b.set(ylim=(0,26),ylabel='Margin to 196');b.set_xticks([0,1],['F03\nselected','F14\nset-wide'])
    title(b,'(b) Closest calls')
    legend(f,[key(S,'o','None','Selected minimum'),key(B,'s','None','Set maximum',True),patches.Patch(color=PALE,label='Formal span 84–188')],.008,3)
    return f
def f4():
    d=data('sa_budget_curve.csv'); f=fig(168,88)
    for i,(cohort,arms) in enumerate([('fresh',['40_real','40_zero']),('fresh_length_paired',['40_real','single_real'])]):
        a=ax(f,[.09+i*.495,.285,.365,.53]);title(a,['(a) Business cost · 20 blocks','(b) Chain length · 2 blocks'][i])
        for j,arm in enumerate(arms):
            g=d[(d.source==cohort)&(d.arm==arm)].sort_values('budget'); assert len(g)==7
            x=g.budget.to_numpy();n=g.planned_blocks.to_numpy();p=g.strict_hit_fraction.to_numpy()
            z=norm.ppf(.975); den=1+z*z/n;mid=(p+z*z/(2*n))/den; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
            c=[S,[Q,G][i]][j];a.fill_between(x,(mid-h)*100,(mid+h)*100,fc=c,alpha=.17,zorder=0)
            a.plot(x,p*100,marker=['o',['s','^'][i]][j],ls=['-','--'][j],color=c,mfc=['white',c][j],ms=4)
        a.set_xscale('log');a.set_xticks(x,x);a.xaxis.set_minor_locator(ticker.NullLocator());a.set_ylim(-5,107)
        a.set_yticks([0,25,50,75,100]);a.set_xlabel('Restart budget per block');a.set_ylabel('Blocks with a strict hit (%)' if i==0 else '')
        if i==0:
            a.axvline(5,c=B,ls=':',lw=.8);f.text(.09,.88,'At 5 restarts: p = 0.000122 (this instance and schedule)',fontsize=9)
            a.annotate('20/20',(5,100),xytext=(7,-12),textcoords='offset points',color=S,fontsize=8.5)
            a.annotate('6/20',(5,30),xytext=(-25,7),textcoords='offset points',color=INK,fontsize=8.5)
    legend(f,[key(S,'o','-','40 short, business',True),key(Q,'s','--','40 short, zero cost'),key(G,'^','--','One long, business'),patches.Patch(fc='#D6DEE1',label='95% interval')],.025,4)
    return f
def a2():
    f=fig(152,83); j=np.load(src('A2'))['J']; u,v=np.triu_indices(105,1);nz=j[u,v]!=0; u,v=u[nz],v[nz]; weight=j[u,v]
    a=ax(f,[.035,.09,.51,.81]);a.set_xlim(-1.22,1.22);a.set_ylim(-1.1,1.15);a.set_aspect('equal');a.axis('off')
    groups=np.r_[np.repeat(np.arange(8),[13]*8),8]; ang=np.radians([128,154,180,206,-26,0,26,52,90]); pos=np.c_[np.cos(ang),np.sin(ang)]
    for i in range(9):
        for k in range(i,9):
            for sign,col in [(-1,S),(1,Q)]:
                keep=(groups[u]==i)&(groups[v]==k)&(np.sign(weight)==sign)
                if not keep.any():continue
                p,q=pos[i],pos[k]; tot=abs(weight[keep]).sum()
                if k==i:
                    mid=p*.90
                    path=MPath([p,mid+.13*np.array([-p[1],p[0]]),mid-.13*np.array([-p[1],p[0]]),p],[1,4,4,4])
                else:
                    path=MPath([p,p*(.56 if i//4==k//4 else .18),q*(.56 if i//4==k//4 else .18),q],[1,4,4,4])
                a.add_patch(PathPatch(path,fill=False,color=col,lw=.22+.022*np.sqrt(tot),alpha=.65))
    for h,p in enumerate(pos):
        a.scatter(*p,s=46,marker=['o','s','D'][min(h//4,2)],fc=['#E5EAF0','#F8EAD6','#D6E4D9'][min(h//4,2)],ec=INK,lw=.8,zorder=4)
    a.text(-.96,.69,'A',weight='bold');a.text(.85,.69,'B',weight='bold');a.text(0,1.10,'Ref.',ha='center')
    title(a,'(a) Bundled registers')
    b=ax(f,[.64,.24,.32,.54]); counts=[sum((u<52)&(v<52)),sum((u>=52)&(v<104)),sum((u<52)&(v>=52)&(v<104)),sum(v==104)]
    y=np.arange(4);b.barh(y,counts,color=[S,Q,G,B],height=.50);b.set_yticks(y,['A–A','B–B','A–B','Ref.']);b.invert_yaxis();b.set_xlim(0,max(counts)*1.28);b.set_xlabel('Nonzero logical edges')
    for z,num in enumerate(counts):barlabel(b,num,z,f'{num:,}')
    title(b,'(b) Edge counts');legend(f,[key(S,'','-','Negative coupling (all edges)'),Line2D([],[],c=S,lw=3,label='Width: bundled magnitude')],.01,2)
    return f
def a3():
    f=fig(158,73); d=data('return_energy.csv');bins=np.arange(-58724,-58517,4)
    for i,(stage,c) in enumerate([('pilot',G),('formal',S)]):
        a=ax(f,[.10,.58-i*.40,.85,.29]);v=d.loc[d.stage==stage,'energy']; cnt,_=np.histogram(v,bins);assert cnt.sum()==len(v)
        a.bar(bins[:-1]+2,cnt,width=3.4,color=c,ec='none');a.set_xlim(-58733,-58513);a.axvline(-58722,c=INK,ls='--',lw=1)
        a.axvline(-58526,c=W,ls=':',lw=1.35);a.set_ylabel('Count');a.yaxis.set_major_locator(ticker.MaxNLocator(nbins=3,integer=True))
        a.xaxis.set_major_formatter(ticker.FuncFormatter(lambda q,pos:f'{q:,.0f}'))
        a.set_xticks([-58722,-58680,-58640,-58600,-58560,-58526])
        title(a,['(a) Pilot · 50 returned vectors','(b) Formal · 200 returned vectors'][i])
        if i==0:
            a.tick_params(labelbottom=False);note(a,.02,.82,'Ground −58,722');note(a,.99,.82,'Boundary −58,526',ha='right',color=W)
        else:a.set_xlabel('Recomputed integer energy')
    return f
def a4():
    f=fig(163,77);ds=pd.read_csv(src('A4'));bs=pd.DataFrame(load(specs['A4']['files'][1])['rows'])
    a=ax(f,[.19,.245,.38,.57]);cim=ds[ds.stage=='formal'].reset_index(drop=True)
    for k,(lab,ms,col) in enumerate([('Valid return','s',B),('Strict feasible','o',G),('Regret ≤ 0.1','D',Q),('Exact hit','o',S)]):
        ok=[cim.status.eq('VALID_COMPLETED'),cim.strict_solution_count.gt(0),cim.best_regret_strict.le(.1),cim.hit_strict][k]
        a.scatter(np.flatnonzero(ok)+1,np.full(ok.sum(),3-k),marker=ms,s=12,fc=col,ec=col)
    a.set_yticks([3,2,1,0],['Valid return','Strict feasible','Regret ≤ 0.1','Exact hit']);a.set_xticks([1,5,10,15,20])
    a.set(xlim=(0,21),ylim=(-.55,3.6),xlabel='Formal attempt slot');title(a,'(a) Formal attainment')
    b=ax(f,[.70,.245,.27,.57]); y=[2,1,0]; labs=['Pilot','Formal','SA block']; ns=[5,20,5]
    for i,(group,n) in enumerate(zip([ds[ds.stage=='pilot'],cim,bs],ns)):
        h1=int(group.best_regret_strict.eq(0).sum());h2=int(group.energy_selected_regret_strict.eq(0).sum())
        for off,k,marker,col in [(.10,h1,'s',Q),(-.10,h2,'o',S)]:
            b.plot(k/n*100,y[i]+off,marker=marker,mfc='white' if off>0 else col,mec=col,ms=5)
        b.text(93,y[i],f'{h2}/{n}',ha='right',va='center',fontsize=8.5)
    b.set(xlim=(-2,108),ylim=(-.55,2.6),xlabel='Units with exact hit (%)');b.set_yticks(y,labs);b.set_xticks([0,50,100]);title(b,'(b) Two selection rules')
    legend(f,[key(Q,'s','None','Best original regret',True),key(S,'o','None','Minimum integer energy')],.016,2)
    return f
def a5():
    f=fig(164,90);d=data('task_timeline.csv');tz=timezone(timedelta(hours=8))
    for i,stage in enumerate(['pilot','formal']):
        a=ax(f,[[.105,.22,.32,.63],[.547,.22,.42,.63]][i]);g=d[d.stage==stage].reset_index(drop=True)
        start=pd.to_datetime(g.accepted_at_local);end=pd.to_datetime(g.terminal_observed_at_local)
        for k,(s,e) in enumerate(zip(start,end)):
            a.plot([s,e],[k,k],c='#A7B3BC',lw=1.2);a.scatter(s,k,color=S,s=13,marker='o');a.scatter(e,k,edgecolor=W,facecolor='white',s=17,marker='s',linewidth=.8)
        ticks=[0,1,2,3,4] if i==0 else [0,4,9,14,19];a.set_yticks(ticks,g.slot.iloc[ticks]);a.set_ylim(len(g)-.4,-.8)
        a.xaxis.set_major_locator(dates.MinuteLocator(interval=[7,2][i],tz=tz));a.xaxis.set_major_formatter(dates.DateFormatter('%H:%M',tz=tz))
        a.set_xlabel('Local clock (UTC+8)');title(a,['(a) Pilot tasks','(b) Formal tasks'][i])
    legend(f,[key(S,'o','None','Accepted by service'),key(W,'s','None','Terminal state observed',True)],.015,2)
    return f
def a6():
    f=fig(166,89);d=pd.read_csv(src('A6')); rep=pd.read_csv(src('A6',1)).set_index('id');reg=pd.read_csv(src('A6',2));m=data('task_margin.csv');m=m[m.stage=='formal']
    a=ax(f,[.155,.57,.75,.29]);sel=d.set_index('stage').loc[['training','representation_audit','SA'],'seconds']
    y=np.arange(3);a.barh(y,sel,color=[G,Q,S],height=.54);a.set_yticks(y,['Training','Audit','SA']);a.invert_yaxis();a.set_xlim(0,435);a.set_xlabel('Classical phase duration (s)',labelpad=1)
    for k,v in enumerate(sel):barlabel(a,v,k,f'{v:.1f}')
    title(a,'(a) Logged classical phases')
    axes=[ax(f,[.09,.17,.22,.165]),ax(f,[.415,.17,.23,.165]),ax(f,[.755,.17,.20,.165])]
    rm=float(reg.loc[reg.route=='H-soft','RMSE'].iloc[0]);b=axes[0];b.plot(rm,0,'o',color=G);b.set(xlim=(0,6),ylim=(-.4,.6),yticks=[],xlabel='Group-CV RMSE');b.text(rm,.18,f'{rm:.2f}',ha='center')
    b=axes[1]
    for k,enc in enumerate(['raw','rc']):
        v=rep.loc[f'11-{enc}-N8','worst_ground_regret'];b.scatter(v,k,marker=['o','s'][k],color=[Q,S][k]);b.annotate(f'{v:.1f}',(v,k),xytext=(0,4),textcoords='offset points',ha='center',fontsize=8.5)
    b.set(xlim=(0,28),ylim=(-.45,1.8),xlabel='Allowed-minimum regret');b.set_yticks([0,1],['Raw','RC'])
    b=axes[2];lo=m.min_residual.min();hi=m.min_residual.max();b.hlines(0,lo,hi,color=S,lw=2);b.plot([lo,hi],[0,0],'|',color=S,ms=9);b.set(xlim=(70,195),ylim=(-.4,.6),yticks=[],xlabel='Selected residual');b.set_xticks([lo,hi])
    for b,t in zip(axes,['(b) Proxy','(c) 8-bit one-hot','(d) Service']):title(b,t)
    return f
def a7():
    f=fig(170,114);r=pd.read_csv(src('A7')).set_index('id'); cfg=[(p,e) for p in ['07','11'] for e in ['raw','rc']]
    cmap=plt.get_cmap('viridis_r');nrm=colors.Normalize(0,60); codes={'CERTIFIED':'C','COUNTEREXAMPLE':'×','UNKNOWN':'?','IMPLEMENTATION_ERROR':'!'}
    for i,variants in enumerate([['N4','N6','N8','N10','N12','N16'],['lambda0.1-N8','N8','lambda2.2-N8']]):
        a=ax(f,[[.13,.565,.44,.28],[.707,.565,.23,.28]][i]); rows=[[r.loc[f'{p}-{e}-{v}'] for v in variants] for p,e in cfg];arr=np.array([[v.worst_ground_regret for v in row] for row in rows])
        a.pcolormesh(np.arange(len(variants)+1)-.5,np.arange(5)-.5,arr,cmap=cmap,norm=nrm);a.set(xlim=(-.5,len(variants)-.5),ylim=(3.5,-.5))
        for y,row in enumerate(rows):
            for x,v in enumerate(row):
                rgba=np.array(cmap(nrm(v.worst_ground_regret))[:3]);col='white' if np.dot(rgba,[.2126,.7152,.0722])<.52 else INK
                a.text(x,y,codes[v.certificate],color=col,ha='center',va='center',weight='bold',fontsize=12)
        a.set_xticks(range(len(variants)),['4','6','8','10','12','16'] if i==0 else ['0.1','1','2.2'])
        a.set_yticks(range(4),['07 raw','07 RC','11 raw','11 RC'] if i==0 else ['', '', '', '']);a.set_xlabel(['Nominal width (bits)','Penalty multiplier'][i]);a.axhline(1.5,c='white',lw=2)
        title(a,['(a) Precision audit','(b) 8-bit penalties'][i])
    cb=f.colorbar(plt.cm.ScalarMappable(norm=nrm,cmap=cmap),cax=ax(f,[.17,.405,.35,.019]),orientation='horizontal',ticks=[0,20,40,60]);cb.set_label('Worst allowed-minimum regret',labelpad=1)
    f.text(.615,.41,'C   Certified        ×   Counterexample',fontsize=8.5)
    f.text(.615,.365,'?   Unknown        !   Implementation error',fontsize=8.5)
    c=ax(f,[.142,.125,.405,.135]); labs=['07 raw','07 RC','11 raw','11 RC']
    values=[load(filename)['changed_entries'] for filename in specs['A7']['files'][1:5]];bars=c.bar(np.arange(4),values,color=[S,Q,S,Q],width=.48)
    c.bar_label(bars,padding=1,fontsize=8.5);c.set(ylim=(0,1940),ylabel='Entries');c.set_xticks(np.arange(4),labs);c.set_yticks([0,1500]);title(c,'(c) Zero-cost control')
    status=pd.read_csv(src('A7',5));assert len(status)==8 and status.feasible_raw.sum()==0
    t=ax(f,[.68,.127,.24,.136]);t.set(ylim=(-.6,.6),xlim=(.5,8.5),yticks=[]);t.plot(np.arange(1,9),np.zeros(8),'x',color=W,ms=6)
    t.set_xticks([1,4,8]);t.set_xlabel('Rescue configuration');title(t,'(d) Rescue grid');note(t,.5,.79,'0 / 1,000 feasible each',ha='center')
    return f
def a8():
    f=fig(164,94);r=pd.read_csv(src('A8'),dtype={'pool':str})
    for i,p in enumerate(['07','11']):
        grp=r[r.pool==p].drop_duplicates('key').reset_index(drop=True);ranks=pd.read_csv(src('A8',1+i),index_col=0)
        a=ax(f,[.16,.62-i*.41,.33,.23]);b=ax(f,[.625,.62-i*.41,.34,.23])
        for k,row in grp.iterrows():
            vals=ranks.loc[row.key].to_numpy(dtype=int)
            for t in np.unique(vals):
                n=(vals==t).sum();a.scatter([t]*n,k+(np.arange(n)-(n-1)/2)*.060,s=13,facecolor=PALE,edgecolor=S,lw=.6)
            a.plot(np.median(vals),k,marker='D',ms=4,color=S)
            b.plot([row.cvar90,row.worst_regret],[k,k],c=B,lw=1);b.scatter(row.cvar90,k,marker='o',s=28,c=G);b.scatter(row.worst_regret,k,marker='s',s=26,c=Q)
        labs=[z.split('|')[0]+'TiO₂N' for z in grp.key]
        a.set_yticks(range(2),labs);b.set_yticks(range(2),labs);a.set(xlim=(-1,42),ylim=(1.48,-.48));b.set(xlim=(2.55,4.45),ylim=(1.48,-.48))
        for aa,t in [(a,'Member ranks'),(b,'Upper-tail regret')]:title(aa,('('+'abcd'[i*2+(aa is b)]+') ')+p+' · '+t)
        if i==1:a.set_xlabel('Rank in one member table');b.set_xlabel('Original proxy regret')
    legend(f,[key(S,'D','None','Median rank'),key(G,'o','None','CVaR (worst 10%)'),key(Q,'s','None','Worst member')],.005,3)
    return f
def a9():
    f=fig(161,91);d=data('chain_task_25x40.csv');v=d.filter(regex='^chain_').to_numpy()
    a=ax(f,[.09,.21,.77,.67]);im=a.pcolormesh(np.arange(41)-.5,np.arange(26)-.5,v,cmap=SEQ,vmin=0,vmax=10);a.set(xlim=(-.5,39.5),ylim=(24.5,-.5))
    a.add_patch(patches.Rectangle((15.5,-.5),1,25,fill=False,lw=1.15,edgecolor='#B66E35'));a.axhline(4.5,c='white',lw=2)
    a.set_xticks([0,4,9,16,24,29,34,39],[1,5,10,17,25,30,35,40]);a.set_yticks([0,3,5,9,14,19,24],d.slot.iloc[[0,3,5,9,14,19,24]])
    a.set(xlabel='Chain index',ylabel='Optimization task')
    a.annotate('Optimum-containing group',xy=(16,1),xytext=(19,-2.35),arrowprops=dict(arrowstyle='->',color=W,lw=.8),color=W,fontsize=8.5,annotation_clip=False)
    cb=f.colorbar(im,cax=ax(f,[.89,.29,.025,.47]),ticks=[0,2,5,8,10]);cb.set_label('Local optima per 10 returns')
    return f
def a1():
    f=fig(169,91);root=HERE/'crystal';xs=[.31,.575,.84];ys=[.67,.30]
    for j,view in enumerate(['c','a','oblique']):
        f.text(xs[j],.947,['Along c','Along a','Oblique'][j],ha='center',fontsize=10)
        for i,mode in enumerate(['poly','stick']):
            from scipy import ndimage
            im=Image.open(root/f'{mode}_{view}.png').convert('RGB');canvas_w,canvas_h=im.size
            pixels=np.asarray(im);white=np.all(pixels==255,axis=2);seed=np.zeros_like(white)
            seed[[0,-1],:]=white[[0,-1],:];seed[:,[0,-1]]=white[:,[0,-1]]
            bg=ndimage.binary_propagation(seed,mask=white);im.putalpha(Image.fromarray((~bg).astype('uint8')*255))
            # Identical orthographic scale and common scene-centred crop in all six images.
            half=round(canvas_w*440/1410);cx=canvas_w//2;cy=round(canvas_h/2+canvas_w*19/1410)
            im=im.crop((cx-half,cy-half,cx+half,cy+half))
            a=ax(f,[xs[j]-.114,ys[i]-.18,.228,.36]);a.imshow(im,interpolation='lanczos');a.axis('off')
            if j<2:arrow(f,(xs[j]+.103,ys[i]+.028),(xs[j+1]-.104,ys[i]+.028),-.34)
    for y,txt in zip(ys,['(a) Ti-centred\npolyhedra','(b) Ball and\nstick']):
        f.text(.018,y,txt,ha='left',va='center',fontsize=9.5)
    cols=['#B2BE7E','#46779F','#D59275','#544178'];legend(f,[key(c,'o','None',label) for c,label in zip(cols,['La','Ti','O','N'])],.012,4)
    return f
def a10():
    f=fig(91,90);a=ax(f,[.08,.10,.84,.86]);a.imshow(Image.open(src('A10')),interpolation='lanczos');a.axis('off')
    f.text(.5,.045,'SPQC-550  ·  Generated illustration',ha='center',fontsize=10);return f
def a11():
    from scipy.ndimage import label,find_objects
    f=fig(170,96)
    labels=['F03','F04','F06','F07','F08','F09']
    ticks=[(-35000,5000),(-30000,5000),(-57000,200),(-55500,500),(-30000,5000),(-54000,1000)]
    def centres(line):
        return np.array([(s[0].start+s[0].stop-1)/2 for s in find_objects(label(line)[0])])
    for k,(slot,(top,step)) in enumerate(zip(labels,ticks)):
        a=ax(f,[.09+(k%3)*.324,.59-(k//3)*.40,.238,.28]);img=np.array(Image.open(src('A11',k)).convert('RGB')); dark=img.max(2)<100
        sx=np.where(dark.sum(0)>700)[0];sy=np.where(dark.sum(1)>1500)[0];x0,x1=sx[:3].max()+1,sx[-3:].min();y0,y1=sy[:3].max()+1,sy[-3:].min()
        xc=centres(dark[sy[-1]+3,:]);xc=xc[(xc>x0)&(xc<x1)];yc=centres(dark[:,sx[0]-3]);yc=yc[(yc>y0)&(yc<y1)]
        px=np.polyfit(np.arange(9)*250,xc,1);py=np.polyfit(top-step*np.arange(len(yc)),yc,1)
        assert max(abs(np.polyval(px,np.arange(9)*250)-xc))<1 and max(abs(np.polyval(py,top-step*np.arange(len(yc)))-yc))<1
        crop=img[y0:y1,x0:x1].astype('int16');blue=(crop[:,:,2]-crop[:,:,0]>40)&(crop[:,:,1]-crop[:,:,0]>25)
        xx=(np.arange(x0,x1)-px[1])/px[0]; yy=(np.arange(y0,y1)-py[1])/py[0]/1000
        # Silhouette of original blue ink, with a constant print outline. No curve is inferred.
        a.contourf(xx,yy,blue,levels=[.5,1.5],colors=['#31739D'],antialiased=False)
        a.contour(xx,yy,blue,levels=[.5],colors=['#31739D'],linewidths=.29)
        a.set(xlim=(xx.min(),xx.max()),ylim=(yy.min(),yy.max()));a.set_xticks([0,1000,2000]);a.yaxis.set_major_locator(ticker.MaxNLocator(nbins=3))
        a.tick_params(pad=2,length=2.5)
        title(a,'('+'abcdef'[k]+') '+slot)
    f.text(.5,.049,'Displayed T (a.u.)',ha='center');f.text(.012,.525,'Displayed Hamiltonian (10³ a.u.)',va='center',rotation=90)
    return f
def a12():
    f=fig(168,101);d=data('chain_ablation.csv');a=ax(f,[.255,.25,.475,.615]);labels=['Single · linear','Packed · linear','Packed · shaped','20 · business','20 · zero','40 · business','40 · zero','Single · business','40 · business']
    y=np.array([9,8,7,5.8,4.8,3.8,2.8,1.55,.55]);a.text(104,9.60,'Hits / slots',fontsize=8.5)
    for n,(_,r) in enumerate(d.iterrows()):
        a.barh(y[n],100*r.strict/r.planned,height=.57,fc=PALE,ec=S,lw=.6)
        a.barh(y[n],100*r.strict_hits/r.planned,height=.24,fc=S,ec=S)
        a.text(104,y[n],f'{r.strict_hits}/{r.planned}',va='center',fontsize=8.5)
    a.set_yticks(y,labels);a.set(xlim=(-.5,135),ylim=(-.1,9.7),xlabel='Planned restarts (%)');a.set_xticks([0,25,50,75,100])
    for yt in [6.4,2.15]:a.axhline(yt,c='#B8BDC1',lw=.65,ls=':')
    title(a,'(a) Feasibility and strict hits')
    for yy,name in [(.802,'H02'),(.597,'H05'),(.365,'Matched')]:f.text(.01,yy,name,weight='bold',fontsize=8.5)
    b=ax(f,[.82,.405,.15,.355]);b.bar([0,1],[0,39],color=[B,Q],width=.54);b.set(xlim=(-.6,1.6),ylim=(0,45),ylabel='Comparisons');b.set_xticks([0,1],['1','40']);b.set_xlabel('Candidates per vector');b.text(0,2,'0',ha='center');b.text(1,40,'39',ha='center');title(b,'(b) Aggregation')
    legend(f,[patches.Patch(fc=PALE,ec=S,label='Strict feasible'),patches.Patch(fc=S,label='Strict hit')],.045,2)
    return f

build={'F1':f1,'A1':a1,'F2':f2,'F3':f3,'F4':f4,'A2':a2,'A3':a3,'A4':a4,'A5':a5,'A6':a6,'A7':a7,'A8':a8,'A9':a9,'A10':a10,'A11':a11,'A12':a12}
names={'F1':'data_pipeline','A1':'crystal_orientations','F2':'coupling_matrices','F3':'residual_margins','F4':'restart_budgets','A2':'grouped_lookup','A3':'return_energies','A4':'task_attainment','A5':'task_timeline','A6':'cost_and_error','A7':'precision_audit','A8':'tail_regret','A9':'chain_heatmap','A10':'platform_illustration','A11':'archived_evolution','A12':'chain_ablation'}
def basename(i):return 'P2-'+i+'_'+names[i]
def render(i):
    f=build[i]();d=P2/'plates';d.mkdir(exist_ok=True);dpi=600 if i=='A1' else 450
    out=d/basename(i); f.savefig(out.with_suffix('.pdf'),dpi=dpi,metadata={'Creator':'P2 figure archive','Title':specs[i]['title'],'CreationDate':None})
    f.savefig(out.with_suffix('.png'),dpi=dpi);plt.close(f)
if __name__=='__main__':
    for i in sys.argv[1:] or build:print('Render',i,flush=True);render(i)
