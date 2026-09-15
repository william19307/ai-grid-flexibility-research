"""Reproduce the observed-arrival diagnostic figure from audited hourly counts."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
ROOT=Path(__file__).resolve().parents[3]
p=ROOT/'outputs/research'
d=pd.read_csv(p/'tables/burstgpt_v2_part1_hourly_recorded_requests.csv')
d=d[~d.is_last_partial_hour]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,
    'axes.spines.right':False,'axes.linewidth':.7,'svg.fonttype':'none','pdf.fonttype':42,
    'text.color':'#283741','axes.labelcolor':'#283741'})
f,ax=plt.subplots(2,1,figsize=(11,6.4),sharex=True)
f.subplots_adjust(left=.10,right=.96,top=.76,bottom=.20,hspace=.35)
f.text(.08,.94,'OBSERVED REQUEST TRACE / SOURCE AUDIT 02',fontsize=9,color='#247F70',weight='bold')
f.text(.08,.875,'Recorded arrivals vary sharply over time',fontsize=20,weight='bold')
f.text(.08,.818,'BurstGPT v2.0, part 1 | 1,429,737 records | Final partial hour excluded from plots',fontsize=9,color='#65737C')
for a,model,color,letter in zip(ax,['ChatGPT','GPT-4'],['#306D99','#C47C3C'],'ab'):
    h=d[d.Model==model].groupby('hour_index').recorded_requests.sum()
    a.plot(h.index/24,h.values,lw=.65,color=color)
    a.set_title(model+' label',loc='left',fontsize=10,weight='bold')
    a.text(-.075,1.06,letter,transform=a.transAxes,fontsize=13,weight='bold')
    a.set_ylabel('Recorded requests / hour');a.set_ylim(bottom=0)
    a.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x/1000:g}k' if x>=1000 else f'{x:g}'))
    a.set_xlim(0,61);a.grid(axis='y',alpha=.15)
ax[1].set_xlabel('Days since the trace time origin (calendar date unspecified)')
f.text(.08,.104,'Source: Wang et al., BurstGPT (KDD 2025), release v2.0 / BurstGPT_1.csv. Counts include zero-output records.',fontsize=8,color='#65737C')
f.text(.08,.066,'Arrival counts are not GPU power, completed compute work or permissible deferral. Missing coverage cannot be ruled out.',fontsize=8,color='#65737C')
for ext in ['png','svg','pdf']:
    f.savefig(p/f'figures/burstgpt_observed_arrivals.{ext}',dpi=190)
plt.close(f)
