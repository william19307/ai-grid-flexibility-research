"""Research diagnostic from verified quarterly aggregates, not final manuscript figure."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/rudong_h2_quarterly'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 audit=json.loads((OUT/'comparison_audit.json').read_text());check=json.loads((OUT/'independent_verification.json').read_text())
 assert check['status']=='PASS' and check['analysis_sha256']==sha(OUT/'comparison_audit.json')
 assert sha(OUT/'quarterly_comparison.csv')==audit['quarterly_comparison_sha256']
 df=pd.read_csv(OUT/'quarterly_comparison.csv');annual=pd.read_csv(OUT/'annual_cancellation.csv')
 curves=['NREL_ReferenceTurbine_5MW_offshore','Vestas_V112_3MW','legacy_generic']
 labels=['NREL reference','V112 reference','Generic (physically rejected)'];colors=['#007e87','#9061a8','#cf8242']
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
 fig,(ax,bx)=plt.subplots(2,1,figsize=(12,7.7),gridspec_kw={'height_ratios':[1.6,1]})
 fig.subplots_adjust(left=.20,right=.96,top=.86,bottom=.17,hspace=.48)
 fig.suptitle('Annual agreement can conceal seasonal errors',x=.20,ha='left',y=.97,fontsize=18,fontweight='bold')
 fig.text(.20,.918,'Exploratory H2 proxy: company offshore totals; fixed calibration from 2022 only',fontsize=10,color='#4c5665')
 x=np.arange(12);observed=df[df.curve==curves[0]].sort_values(['year','quarter'])
 ax.plot(x,observed.observed_gross_mwh/1000,color='#20252c',marker='o',lw=2,label='Reported gross generation')
 for curve,label,color in zip(curves,labels,colors):
  g=df[df.curve==curve].sort_values(['year','quarter'])
  ax.plot(x,g.scaled_mwh/1000,label=label,color=color,marker='s',markersize=4,lw=1.6,ls='--' if curve=='legacy_generic' else '-')
 ax.set_ylabel('Quarterly generation (GWh)');ax.set_xticks(x,[f'{r.year} Q{r.quarter}' for r in observed.itertuples()],rotation=35,ha='right',fontsize=9)
 ax.set_xlim(-.3,11.3);ax.grid(axis='y',alpha=.15);ax.set_title('a  Reported and modelled quarterly energy',loc='left',fontsize=11,fontweight='bold')
 ax.legend(loc='upper left',frameon=False,fontsize=8.5,ncol=2)
 matrix=np.array([df[df.curve==c].sort_values(['year','quarter']).scaled_error_pct.to_numpy() for c in curves])
 im=bx.imshow(matrix,cmap='RdBu_r',vmin=-25,vmax=25,aspect='auto')
 bx.set_yticks(np.arange(3),['NREL reference','V112 reference','Generic (rejected)'])
 bx.set_xticks(x,[f'Q{q}' for q in [1,2,3,4]*3]);bx.tick_params(length=0)
 for r in range(3):
  for c in range(12):bx.text(c,r,f'{matrix[r,c]:+.1f}',ha='center',va='center',fontsize=8.5,color='white' if abs(matrix[r,c])>17 else '#18252e')
 for p in [3.5,7.5]:bx.axvline(p,color='white',lw=2)
 for mid,year in [(1.5,2022),(5.5,2023),(9.5,2024)]:bx.text(mid,-.68,str(year),ha='center',fontsize=10)
 bx.set_title('b  Quarterly error (%) after annual calibration',loc='left',fontsize=11,fontweight='bold',pad=26)
 a2023=annual[(annual.year==2023)&(annual.curve==curves[0])].iloc[0]
 fig.text(.20,.078,f'2023 NREL: annual bias {a2023.annual_signed_error_pct:.2f}%; sum of absolute quarterly errors / annual generation {a2023.quarterly_absolute_error_over_annual_generation_pct:.2f}%.',fontsize=10,fontweight='bold')
 fig.text(.20,.044,'Sources: issuer Q1/H1/9M and annual reports; ERA5 wind with reference curves. No quarterly refit.\nQ2-Q4 derived from cumulative differences. Rounding is not a confidence interval. No hourly validation.',fontsize=8.5,color='#4c5665')
 for ext in ['png','pdf','svg']:fig.savefig(OUT/('quarterly_diagnostic.'+ext),dpi=180)
 svg=OUT/'quarterly_diagnostic.svg'
 svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
 plt.close(fig)
 (OUT/'figure_audit.json').write_text(json.dumps(dict(script_sha256=sha(Path(__file__)),analysis_sha256=sha(OUT/'comparison_audit.json'),verification_sha256=sha(OUT/'independent_verification.json'),artifacts={ext:sha(OUT/('quarterly_diagnostic.'+ext)) for ext in ['png','pdf','svg']},scope='Diagnostic figure, not final manuscript evidence'),indent=2)+'\n')
if __name__=='__main__':main()
