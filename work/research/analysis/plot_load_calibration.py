"""Standalone research figure from audited real statistics and model inputs."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
T=ROOT/'outputs/research/tables'
F=ROOT/'outputs/research/figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
 'axes.spines.right':False,'axes.labelcolor':'#262b30','text.color':'#262b30',
 'xtick.color':'#42484d','ytick.color':'#42484d','svg.fonttype':'none','pdf.fonttype':42})
d=pd.read_csv(T/'provincial_load_2020_annual_calibration.csv').sort_values('source_relative_difference_pct')
m=pd.read_csv(T/'jiangsu_2020_unused_temporal_checks.csv').iloc[:4]
blue='#275775';gold='#BA8B3C';gray='#555d64'
fig=plt.figure(figsize=(12,10),facecolor='white')
gs=fig.add_gridspec(2,2,width_ratios=[1.13,1],height_ratios=[1,0.6],left=.15,right=.97,top=.84,bottom=.12,wspace=.45,hspace=.48)
a=fig.add_subplot(gs[:,0]);b=fig.add_subplot(gs[0,1]);c=fig.add_subplot(gs[1,1])
v=d.source_relative_difference_pct.to_numpy();y=np.arange(len(d))
a.barh(y,v,color=[blue if x>=0 else gold for x in v],height=.64,zorder=3)
a.set_yticks(y,d.province.str.replace('InnerMongolia','Inner Mongolia'))
a.tick_params(axis='y',length=0,labelsize=9)
a.axvline(0,color=gray,lw=.8);a.set_xlim(-10,17)
a.set_xticks([-10,-5,0,5,10,15],['−10','−5','0','5','10','15'])
a.grid(axis='x',color='#e7eaec',lw=.6,zorder=0)
a.set_xlabel('Source model minus official annual demand (%)',labelpad=9)
a.set_title('a  Provincial annual discrepancies',loc='left',fontweight='bold',pad=15)
for yy,xx in zip(y,v):
 if abs(xx)>5:a.text(xx+(.22 if xx>0 else -.22),yy,f'{xx:+.1f}',va='center',ha='left' if xx>0 else 'right',fontsize=8)
x=np.arange(4);w=.34
b.bar(x-w/2,m.official_electricity_TWh,w,label='Official monthly statistic',color=blue)
b.bar(x+w/2,m.annual_anchored_model_TWh,w,label='Annual-anchored model',facecolor='white',edgecolor=gold,linewidth=1.4,hatch='///')
b.set_xticks(x,['Jul','Sep','Oct','Nov']);b.set_ylim(0,80)
b.set_ylabel('Jiangsu electricity consumption (TWh)')
b.set_title('b  Monthly structure after annual fitting',loc='left',fontweight='bold',pad=15)
b.legend(frameon=False,loc='upper center',fontsize=9)
b.spines['left'].set_bounds(0,80)
b.text(.02,-.19,'2020; four available months, shown separately',transform=b.transAxes,fontsize=9,color=gray)
e=m.annual_anchored_error_pct.to_numpy()
c.bar(x,e,color=[blue if z>=0 else gold for z in e],width=.6)
c.axhline(0,color=gray,lw=.8);c.set_xticks(x,['Jul','Sep','Oct','Nov']);c.set_ylim(-13,13)
c.set_ylabel('Monthly discrepancy (%)')
c.set_title('c  Residual temporal mismatch',loc='left',fontweight='bold',pad=15)
for xx,yy in zip(x,e):c.text(xx,yy+(.6 if yy>=0 else -.6),f'{yy:+.2f}%',ha='center',va='bottom' if yy>=0 else 'top',fontsize=9)
fig.text(.07,.955,'Annual agreement does not validate hourly demand',fontsize=19,fontweight='bold')
fig.text(.07,.911,'2020 China baseline audit  |  31 provinces; reconstructed source-model demand',fontsize=11,color=gray)
fig.text(.07,.88,'National annual discrepancy: +0.88% against the provincial sum. Nine provinces differ by more than 5%.',fontsize=10)
fig.text(.07,.057,'Annual anchoring fits each province to its official annual total; it preserves the original hourly shape.',fontsize=10)
fig.text(.07,.035,'Sources: China Statistical Yearbook 2021, table 9-14; NEA Jiangsu monthly reports; PyPSA-China V3.0.',fontsize=9,color=gray)
fig.text(.07,.015,'Input calibration diagnostic only. These are not estimates of AI flexibility, emissions benefits or reliability.',fontsize=9,color=gray)
for ext in ['png','svg','pdf']:fig.savefig(F/f'load_2020_calibration_diagnostics.{ext}',dpi=200)
plt.close(fig)
print('Saved load_2020_calibration_diagnostics in PNG, SVG and PDF.')
