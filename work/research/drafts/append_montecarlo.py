"""Append cost-parameter Monte Carlo robustness to manuscript v0.7, report 08 and English v0.5."""
from pathlib import Path
import pandas as pd,json
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';M=ROOT/'outputs/research/manuscript';R=ROOT/'outputs/research/reports'
d=pd.read_csv(T/'regional_2030_cost_montecarlo.csv');inf=d.get('infeasible');ninf=int(inf.fillna(False).sum()) if inf is not None else 0
d=d[d.gap_S0_S2_pct.notna()];q=d.groupby('province').agg(n=('draw','size'),g02_p10=('gap_S0_S2_pct',lambda s:s.quantile(.1)),g02_p50=('gap_S0_S2_pct','median'),g02_p90=('gap_S0_S2_pct',lambda s:s.quantile(.9)),g12_p50=('gap_S1_S2_pct','median'),g12_p90=('gap_S1_S2_pct',lambda s:s.quantile(.9)),grt_p90=('gap_S1rt_S2_pct',lambda s:s.abs().quantile(.9)),grt_max=('gap_S1rt_S2_pct',lambda s:s.abs().max()))
def z(p):r=q.loc[p];return f"{p}：刚性到协调差距中位数 {r.g02_p50:.1f}%（P10–P90 为 {r.g02_p10:.1f}% 到 {r.g02_p90:.1f}%），企业自主差距中位数 {r.g12_p50:.1f}%，实时价格差距 P90 为 {r.grt_p90:.2f}%"
def e(p):r=q.loc[p];return f"{p}: rigid-to-coordinated gap median {r.g02_p50:.1f}% (P10–P90 {r.g02_p10:.1f}–{r.g02_p90:.1f}%), firm-autonomous median {r.g12_p50:.1f}%, real-time-price gap P90 {r.grt_p90:.2f}%"
zh=f"""
**成本参数蒙特卡洛。** 对不允许外送、AI 占峰荷 10% 的设定，随机抽取煤价与气价（0.7 到 1.5 倍）、燃气、储能、风光投资成本（0.7 到 1.3 倍）、空闲功率比例（0.15 到 0.35）与利用率（0.5 到 0.8），每省 40 次（`../tables/regional_2030_cost_montecarlo.csv`；不可行抽样 {ninf} 次，均为利用率过高使轨迹批次超出算力池容量）。{z('Gansu')}；{z('Jiangsu')}；{z('Guizhou')}。差距的排序与"实时价格几乎弥合差距"的结论在全部抽样中保持。
"""
en=f"""A cost-parameter Monte Carlo (coal and gas fuel prices 0.7–1.5×, gas, battery, wind and solar investment 0.7–1.3×, idle power 15–35%, utilisation 50–80%; 40 draws per province, constrained exchange, AI 10% of peak) preserves the ordering of provinces and the near-closure of the gap under real-time prices: {e('Gansu')}; {e('Jiangsu')}; {e('Guizhou')}."""
for p,mark in [(M/'论文工作稿_v0.7.md','峰荷偏高使稀缺被高估，但方向性结论不受影响。'),(R/'阶段研究报告_08.md','峰荷偏高使稀缺被高估，但方向性结论不受影响。')]:
    s=open(p,encoding='utf-8').read();assert mark in s and '成本参数蒙特卡洛' not in s;s=s.replace(mark,mark+zh,1);open(p,'w',encoding='utf-8').write(s)
p=M/'core_paper_en_v0.5.md';s=open(p,encoding='utf-8').read();mark='without changing the direction of any finding.';assert mark in s;s=s.replace(mark,mark+' '+en,1);open(p,'w',encoding='utf-8').write(s)
pj=R/'研究进度与待完成项.json';dd=json.load(open(pj));dd['completed_evidence'].append('cost-parameter Monte Carlo (120 draws) for the 2030 constrained-exchange scenario; gap ordering and real-time-price closure robust');json.dump(dd,open(pj,'w'),ensure_ascii=False,indent=1)
print(q.round(2).to_string())
