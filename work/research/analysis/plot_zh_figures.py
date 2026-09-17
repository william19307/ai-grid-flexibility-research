"""中文稿配图（中文标签）：图1 转移价值兑现份额；图2 相对刚性运行的增量成本降幅；图3 稳健性。数据与英文稿同源。"""
from pathlib import Path
import pandas as pd,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib import font_manager
for fp in ['/System/Library/Fonts/PingFang.ttc','/System/Library/Fonts/STHeiti Light.ttc','/System/Library/Fonts/Hiragino Sans GB.ttc']:
    try:font_manager.fontManager.addfont(fp);FONT=font_manager.FontProperties(fname=fp).get_name();break
    except Exception:FONT=None
plt.rcParams.update({'font.family':[FONT,'DejaVu Sans'] if FONT else ['DejaVu Sans'],'axes.unicode_minus':False,'font.size':8,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':0.6})
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';F=ROOT/'outputs/research/figures/submission_zh';F.mkdir(exist_ok=True,parents=True)
P=['Gansu','Jiangsu','Guizhou'];ZH={'Gansu':'甘肃','Jiangsu':'江苏','Guizhou':'贵州'};IDLE=0.41
C={'S0e':'#bcbd22','S1':'#1f77b4','S3':'#d62728','S1rt':'#ff7f0e','S2':'#2ca02c'}
L={'S0e':'S0e 高效档位、不转移','S1':'S1 企业按分时电价形状优化','S3':'S3 事件型承诺合同','S1rt':'S1rt 企业按边际成本形状价格优化','S2':'S2 系统协调'}
g=pd.read_csv(T/'regional_2030_gaps.csv');g=g[(~g.export)&(g.slack_mult==1.0)]
# 图1 转移价值兑现份额
fig,ax=plt.subplots(figsize=(7.2,2.8));rows=[]
for p in P:
    for _,r in g[g.province==p].sort_values('ai_share').iterrows():
        den=r.cost_S0e-r.cost_S2;rows.append(dict(province=p,ai=r.ai_share,**{c:((r.cost_S0e-r[f'cost_{c}'])/den if den>1 else np.nan) for c in ['S1','S3','S1rt']}))
d=pd.DataFrame(rows);x=np.arange(len(d));w=0.25
for k,c in enumerate(['S1','S3','S1rt']):
    ax.bar(x+(k-1)*w,d[c].clip(-0.6,1.2),w,color=C[c],label=L[c],linewidth=0)
    for xi,v in zip(x+(k-1)*w,d[c]):
        if v<-0.6:ax.text(xi,-0.63,f'{v:.1f}',ha='center',va='top',fontsize=5,rotation=90)
ax.axhline(1,color='k',lw=.6,ls='--');ax.axhline(0,color='k',lw=.6);ax.set_xticks(x);ax.set_xticklabels([f"{ZH[r.province]}\n{int(r.ai*100)}%" for _,r in d.iterrows()],fontsize=7)
ax.set_ylabel('时间转移价值兑现份额\n(S0e − X)/(S0e − S2)');ax.grid(axis='y',alpha=.25,linewidth=.5);ax.set_ylim(-0.95,1.25);ax.set_xlabel('省份与 AI 负荷占 2030 年峰荷比例')
h,l=ax.get_legend_handles_labels();fig.legend(h,l,loc='upper center',ncol=3,fontsize=6.5,frameon=False,bbox_to_anchor=(0.5,1.0))
fig.tight_layout(rect=[0,0,1,0.9]);[fig.savefig(F/f'zh_fig1_realised_share.{e}',dpi=300) for e in ['pdf','png','svg']]
# 图2 降幅
fig,ax=plt.subplots(1,3,figsize=(7.2,2.9),sharey=True)
for j,p in enumerate(P):
    s=g[g.province==p].sort_values('ai_share');x=np.arange(3);w=0.16
    for k,c in enumerate(['S0e','S1','S3','S1rt','S2']):ax[j].bar(x+(k-2)*w,(1-s[f'cost_{c}']/s['cost_S0'])*100,w,color=C[c],label=L[c] if j==0 else None,linewidth=0)
    ax[j].set_xticks(x);ax[j].set_xticklabels([f'{int(a*100)}%' for a in s.ai_share]);ax[j].set_title(ZH[p],fontsize=9);ax[j].set_xlabel('AI 负荷占 2030 年峰荷比例');ax[j].grid(axis='y',alpha=.25,linewidth=.5);ax[j].axhline(0,color='k',lw=.5)
ax[0].set_ylabel('相对刚性运行的\n增量系统成本降幅 (%)')
h,l=ax[0].get_legend_handles_labels();fig.legend(h,l,loc='upper center',ncol=3,fontsize=6.5,frameon=False,bbox_to_anchor=(0.5,1.0))
fig.tight_layout(rect=[0,0,1,0.88]);[fig.savefig(F/f'zh_fig2_cost_by_scenario.{e}',dpi=300) for e in ['pdf','png','svg']]
# 图3 稳健性
mw=pd.read_csv(T/'regional_2030_multiweather.csv');mw=mw[mw.red_S0_S2_pct.notna()];mc=pd.read_csv(T/'regional_2030_cost_montecarlo.csv');mc=mc[mc.red_S0_S2_pct.notna()]
fig,ax=plt.subplots(1,3,figsize=(7.2,2.5))
for i,(df,title,col,yl) in enumerate([(mw[mw.idle==IDLE],'(a) 十个气象年','red_S0_S2_pct','刚性到协调的\n成本降幅 (%)'),(mc,'(b) 成本参数蒙特卡洛','red_S0_S2_pct','刚性到协调的\n成本降幅 (%)'),(mw[mw.idle==IDLE],'(c) S1rt 与协调最优的差距','gap_S1rt_S2_pct','与协调最优的差距 (%)')]):
    data=[df[df.province==p][col].values for p in P]
    ax[i].boxplot(data,tick_labels=[ZH[p] for p in P],widths=0.5,patch_artist=True,medianprops=dict(color='k',lw=.8),whiskerprops=dict(lw=.6),capprops=dict(lw=.6),boxprops=dict(lw=.6,facecolor='#dfe8f3'),flierprops=dict(marker='o',ms=2,lw=.4))
    ax[i].set_title(title,fontsize=8.5,loc='left');ax[i].grid(axis='y',alpha=.25,linewidth=.5);ax[i].set_ylabel(yl,fontsize=7.5)
fig.tight_layout();[fig.savefig(F/f'zh_fig3_robustness.{e}',dpi=300) for e in ['pdf','png','svg']]
print('zh figures saved, font',FONT)
