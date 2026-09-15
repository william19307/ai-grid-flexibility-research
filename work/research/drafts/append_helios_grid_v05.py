"""Append trace-arrival / official-tariff grid findings to manuscript v0.5 and phase report 06 (numbers read from tables)."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];T=ROOT/'outputs/research/tables';M=ROOT/'outputs/research/manuscript';R=ROOT/'outputs/research/reports'
g=pd.read_csv(T/'regional_smoke_gaps_helios_arrivals_official_tou.csv');u=pd.read_csv(T/'regional_smoke_gaps_coal_min_0.csv')
raw=pd.read_csv(T/'regional_smoke_grid_summary_helios_offtou.csv')
def row(df,p,e,a):return df[(df.province==p)&(df.export==e)&(df.ai_share==a)].iloc[0]
gz=row(g,'Guizhou',False,0.2);gzu=row(u,'Guizhou',False,0.2);js=row(g,'Jiangsu',False,0.2);jsu=row(u,'Jiangsu',False,0.2)
ext=raw[raw.case=='S1'].deadline_extensions.max();drop=raw[raw.case=='S1'].dropped_share.max()
para=f"""
**轨迹到达与官方电价变体。** 把均匀到达替换为从 Helios 已完成 GPU 作业按提交小时、GPU 数与运行时长抽样生成的批次（期限 = 发布 + 运行时长上取整 + 松弛 W，松弛是假设；跨时段末尾的工作按稳态截断），并把分时电价形状替换为三省官方文件（江苏 苏发改价格发〔2020〕1183号、甘肃 2020 年 12 月通知、贵州 黔发改价格〔2023〕481号，来源与年份差异登记为 D15–D17；价格水平仍为占位）。批次可行性保护把最多 {int(ext)} 个批次的期限向后延长，时段末尾截断的工作量占比最大 {drop*100:.1f}%。在 W=24 小时下，贵州不允许外送、AI 占峰荷 20% 的刚性到协调差距从均匀到达的 {gzu.gap_S0_S2_pct:.1f}% 变为 {gz.gap_S0_S2_pct:.1f}%，企业自主与协调的差距从 {gzu.gap_S1_S2_pct:.1f}% 变为 {gz.gap_S1_S2_pct:.1f}%；江苏同一设定下刚性情景的燃气调峰投资为 {row(raw[raw.case=='S0'],'Jiangsu',False,0.2).new_ocgt:.0f} MW（均匀到达为 {jsu.new_ocgt_S0:.0f} MW）。真实作业结构使工作量在时间上更集中，也改变了刚性基准本身，因此差距的大小和方向都依赖到达结构，这支持把到达与期限作为按业务类别校准的输入而不是常数。表：`../tables/regional_smoke_gaps_helios_arrivals_official_tou.csv`。
"""
p=M/'论文工作稿_v0.5.md';s=open(p,encoding='utf-8').read()
marker="\n\n这些结果表明管线可以同时输出投资、运行、排放与弃电指标并区分四种情景，但其数值不能用于任何实证陈述。"
assert marker in s and '轨迹到达与官方电价变体' not in s
s=s.replace(marker,"\n\n"+para.strip()+marker);open(p,'w',encoding='utf-8').write(s)
p=R/'阶段研究报告_06.md';s=open(p,encoding='utf-8').read()
m2="\n\n这些方向与既有规划研究一致，不构成新发现；"
assert m2 in s and '轨迹到达与官方电价变体' not in s
s=s.replace(m2,"\n\n"+para.strip().replace('**轨迹到达与官方电价变体。** ','- 轨迹到达与官方电价变体：')+m2)
s=s.replace("4. 为联合模型加入可选的机组最小出力约束","4. 取得并登记江苏、甘肃、贵州官方分时电价文件（D15–D17），管线支持 Helios 轨迹到达与官方电价形状。\n5. 为联合模型加入可选的机组最小出力约束")
open(p,'w',encoding='utf-8').write(s);print('appended')
