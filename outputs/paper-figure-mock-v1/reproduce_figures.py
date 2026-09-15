from pathlib import Path
import csv, shutil, zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.backends.backend_pdf import PdfPages

OUT=Path('../../outputs/paper-figure-mock-v1')
OUT.mkdir(parents=True,exist_ok=True)
BLUE='#3B6F9E'; ORANGE='#CF8643'; GREEN='#238779'; INK='#23333E'; GREY='#71808A'; LIGHT='#E9EDF0'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'text.color':INK,'axes.labelcolor':INK,'xtick.color':GREY,'ytick.color':GREY,'axes.edgecolor':'#9DA8AF','axes.linewidth':.7,'pdf.fonttype':42,'svg.fonttype':'none','savefig.facecolor':'white'})
figures=[]
def footer(fig):
    fig.text(.06,.026,'ILLUSTRATIVE MOCK  /  All numbers are synthetic; no empirical findings or uncertainty estimates.',fontsize=8,color=GREY)
def title(fig,n,t,sub):
    fig.text(.06,.946,f'FIGURE {n:02}',fontsize=9,weight='bold',color=GREEN)
    fig.text(.06,.90,t,fontsize=21,weight='bold')
    fig.text(.06,.857,sub,fontsize=10,color=GREY)
def panel(ax,l,t):
    ax.set_title(t,loc='left',pad=13,fontsize=11,weight='bold')
    ax.text(-.13,1.055,l,transform=ax.transAxes,fontsize=15,weight='bold',color=INK)
    ax.spines[['top','right']].set_visible(False)
    ax.tick_params(length=3,width=.6,labelsize=9)
def save(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=210)
    fig.savefig(OUT/f'{name}.svg')
    figures.append(fig)
def csvout(name,header,rows):
    with (OUT/name).open('w',newline='') as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)

# Figure 1: research architecture, deliberately no invented geographic boundaries.
fig=plt.figure(figsize=(12,6.1));title(fig,1,'From flexible computing to power-system value','Study design  |  Workload constraints, incentives and system outcomes')
ax=fig.add_axes([.045,.23,.91,.54]);ax.set_xlim(0,12);ax.set_ylim(0,4);ax.axis('off')
xs=[.15,3.32,6.5,9.45]
heads=['AI workload','Feasible response','Operating choices','System outcomes']
for i,(x,h) in enumerate(zip(xs,heads)):
    ax.text(x,3.65,chr(97+i),weight='bold',fontsize=15)
    ax.text(x+.30,3.65,h,weight='bold',fontsize=12)
for x in [2.73,5.9,8.86]:
    ax.add_patch(FancyArrowPatch((x,2.12),(x+.40,2.12),arrowstyle='-|>',mutation_scale=14,color='#A5AFB5',lw=1.2))
# workload rows
for y,label,col,width in [(2.75,'Training',BLUE,1.65),(1.92,'Batch inference',GREEN,1.25),(1.09,'Real-time inference',ORANGE,.72)]:
    ax.text(.22,y+.33,label,fontsize=10)
    ax.add_patch(Rectangle((.22,y),2.10,.15,facecolor=LIGHT,edgecolor='none'))
    ax.add_patch(Rectangle((.22,y),width,.15,facecolor=col,edgecolor='none'))
ax.text(.22,.51,'Different completion deadlines',fontsize=8.5,color=GREY)
# response envelopes no quantitative axes
ax.plot([3.43,3.43,5.61],[2.92,1.35,1.35],lw=.8,color=GREY)
tx=np.linspace(3.43,5.55,80);ty=2.36+.29*np.cos((tx-3.43)*3)
ax.fill_between(tx,ty-.24,ty+.24,color=GREEN,alpha=.13)
ax.plot(tx,ty,color=GREEN,lw=2)
ax.text(3.48,3.10,'Power response envelope',fontsize=9)
ax.text(3.45,.88,'Delay  /  migration  /  recovery',fontsize=8.5,color=GREY)
ax.text(3.45,.51,'Bounded by service guarantees',fontsize=8.5,color=GREY)
# comparative scenarios
for y,label,col,ls in [(2.82,'Rigid baseline',BLUE,'-'),(2.03,'Private operation',ORANGE,'--'),(1.24,'System coordination',GREEN,'-')]:
    ax.plot([6.55,6.9],[y,y],color=col,lw=2,ls=ls)
    ax.text(7.02,y,label,va='center',fontsize=10)
ax.text(6.55,.51,'Same workload and reliability',fontsize=8.5,color=GREY)
# outcomes
for y,label in [(2.82,'Investment avoided'),(2.03,'Emissions avoided'),(1.24,'Reliable capacity')]:
    ax.scatter([9.55],[y],marker='s',s=24,facecolor='white',edgecolor=GREEN,lw=1.4)
    ax.text(9.76,y,label,va='center',fontsize=10)
ax.text(9.49,.51,'Net of delivery costs',fontsize=8.5,color=GREY)
fig.text(.075,.165,'Research question',fontsize=10,weight='bold',color=GREEN)
fig.text(.075,.113,'How much technically feasible flexibility becomes real system value — and under which rules?',fontsize=12)
footer(fig);save(fig,'fig01_research_framework')

# Figure 2: all values are hand-designed or generated analytically for layout only.
fig=plt.figure(figsize=(12,9.7));title(fig,2,'The value and limits of AI load flexibility','Synthetic demonstration  |  A four-panel results figure, ready for replacement with model outputs')
gs=fig.add_gridspec(2,2,left=.09,right=.94,bottom=.115,top=.77,wspace=.39,hspace=.63)
axs=[fig.add_subplot(gs[i,j]) for i in range(2) for j in range(2)]
h=np.arange(24); rigid=np.full(24,10.)
private=10+2.5*np.cos((h-3)/24*2*np.pi)-1.2*np.exp(-((h-18)/2)**2);private*=240/private.sum()
coord=10+3.0*np.exp(-((h-12)/3.3)**2)-2.8*np.exp(-((h-19)/2.7)**2);coord*=240/coord.sum()
renew=3.2+6.5*np.exp(-((h-12)/4.0)**2)
ax=axs[0];panel(ax,'a','Daily workload scheduling')
ax.fill_between(h,0,renew,color=LIGHT,label='Renewable profile (illustrative)')
ax.plot(h,rigid,color=BLUE,lw=1.9,label='Rigid',ls=':')
ax.plot(h,private,color=ORANGE,lw=2,label='Private',ls='--')
ax.plot(h,coord,color=GREEN,lw=2.2,label='Coordinated')
ax.set(xlim=(0,23),ylim=(0,16),xticks=[0,6,12,18,23],xlabel='Hour of day',ylabel='Power (MW)')
ax.set_xticklabels(['00','06','12','18','23'])
ax.text(.02,.95,'AI energy = 240 MWh in each scenario',transform=ax.transAxes,fontsize=8.2,color=GREY,va='top')
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.24),frameon=False,ncol=2,fontsize=8,columnspacing=1.1)
csvout('panel_a_hourly_synthetic.csv',['hour','rigid_MW','private_MW','coordinated_MW','renewable_profile_MW'],zip(h,rigid,private,coord,renew))

ax=axs[1];panel(ax,'b','Potential versus realized savings')
vals=[100,94,84];cats=['Rigid','Private','Coordinated']
ax.bar(range(3),vals,color=[BLUE,ORANGE,GREEN],width=.56)
for i,v in enumerate(vals):ax.text(i,v+2,str(v),ha='center',fontsize=11,weight='bold')
ax.set(xticks=range(3),xticklabels=cats,ylim=(0,119),ylabel='Total system cost index (rigid = 100)')
ax.axhline(100,color=GREY,ls=':',lw=.8,zorder=0)
ax.annotate('',xy=(2.55,84),xytext=(2.55,94),arrowprops={'arrowstyle':'|-|','lw':1,'color':INK})
ax.text(2.7,89,'10-point\ngap',fontsize=9,va='center')
ax.set_xlim(-.65,3.18)
csvout('panel_b_cost_synthetic.csv',['scenario','cost_index'],zip(cats,vals))

ax=axs[2];panel(ax,'c','Sensitivity to operational constraints')
delay=np.array([0,1,2,4,8]);spare=np.array([0,5,10,20,30])
heat=np.array([[-2,-1,1,3,4],[-1,1,3,5,6],[0,2,5,8,9],[1,4,7,11,12],[1,4,8,12,13]])
cmap=LinearSegmentedColormap.from_list('benefit',[ORANGE,'#FAFAF7',GREEN])
im=ax.imshow(heat,origin='lower',cmap=cmap,norm=TwoSlopeNorm(vmin=-3,vcenter=0,vmax=14),aspect='auto')
ax.set(xticks=range(5),xticklabels=delay,yticks=range(5),yticklabels=spare,xlabel='Maximum task deferral (h)',ylabel='Spare compute at destination (%)')
for y in range(5):
    for x in range(5):ax.text(x,y,f'{heat[y,x]:+d}',ha='center',va='center',fontsize=10,color='white' if heat[y,x]>8 else INK)
cb=fig.colorbar(im,ax=ax,fraction=.047,pad=.045);cb.set_label('Net cost saving (%)',fontsize=9);cb.ax.tick_params(labelsize=8)
csvout('panel_c_sensitivity_synthetic.csv',['deferral_h','spare_compute_pct','net_saving_pct'],[(d,s,heat[i,j]) for i,s in enumerate(spare) for j,d in enumerate(delay)])

ax=axs[3];panel(ax,'d','Cost–emissions trade-off')
front_x=np.array([1,3,6,9,12,16]);front_y=np.array([.5,3.5,7,9.5,10.8,11.4])
ax.plot(front_x,front_y,color='#A8B2B8',lw=1.2,ls='--')
ax.scatter(front_x,front_y,facecolor='white',edgecolor='#A8B2B8',s=34,zorder=3)
points=[(0,0,'Rigid',BLUE,'s'),(6,2.7,'Private',ORANGE,'^'),(16,11.4,'Coordinated',GREEN,'o')]
for x,y,label,col,m in points:
    ax.scatter(x,y,s=75,color=col,marker=m,zorder=4,edgecolor='white',linewidth=.7)
    ax.annotate(label,(x,y),xytext=((8,9) if label!='Coordinated' else (-78,-17)),textcoords='offset points',fontsize=9,color=col)
ax.text(3.6,11.9,'Illustrative policy envelope',color=GREY,fontsize=8.5)
ax.set(xlim=(-1,18),ylim=(-1,14),xticks=[0,4,8,12,16],yticks=[0,4,8,12],xlabel='System cost saving vs rigid (%)',ylabel='Emissions reduction vs rigid (%)')
ax.grid(color=LIGHT,lw=.6);ax.set_axisbelow(True)
csvout('panel_d_tradeoff_synthetic.csv',['type','label','cost_saving_pct','emissions_reduction_pct'], [('scenario',p[2],p[0],p[1]) for p in points]+[('envelope','illustrative',x,y) for x,y in zip(front_x,front_y)])
footer(fig);save(fig,'fig02_synthetic_results')
assert np.allclose([rigid.sum(),private.sum(),coord.sum()],240)
assert vals[1]-vals[2]==10
with PdfPages(OUT/'paper_figures_mock.pdf') as pdf:
    for f in figures:pdf.savefig(f)
readme='''# 论文配图 Mock v1

本包仅展示论文配图的视觉风格与叙事方式。全部数字为人为设定或解析公式生成的虚构示例；没有运行电力系统优化、实际任务调度或因果识别。不能引用为研究发现，不代表期刊已认可。

## 图 1：研究机制图
任务类型 → 满足服务约束的可调功率 → 三种运行方式 → 系统收益。
强调在完成同等算力服务、保持同等供电可靠性条件下比较。条形长度和功率包络均为概念示意，无定量意义。

## 图 2：数据结果图
- a 逐时曲线：展示刚性、企业自主调度、系统协调的区别。24 个点分别代表每个一小时区间的平均功率；三条 AI 曲线均为 240 MWh/日。灰色仅为示意新能源出力，曲线没有经过电网平衡或任务可行性验证。相同电量不等于已证明相同算力服务。
- b 柱状图：刚性成本指数 100，企业自主 94，系统协调 84，后两者相差 10 个指数点。不是现实节约比例的预测。总系统成本的正式版本应统一投资年化、运行和灵活性兑现成本口径。
- c 热力图：不同延迟上限与异地可用算力下的虚构净成本收益。格子为离散情景，间距不表示连续参数距离。负值表示示例成本增加。
- d 散点与虚线：示例成本与减排权衡。虚线只展示可能的政策边界画法，没有优化证明，不是计算所得的帕累托前沿。b、d 中三种运行方式的成本数字一致。

## 正式版本怎么做
机制图由人工明确对象、因果方向与约束后制作矢量图；数据图由原始数据或模型导出表格后确定性绘制。应补齐参数来源、基准、单位、样本、验证、方法和不确定性定义。不能使用图像生成模型凭空画正式数值、坐标、误差条或中国地图边界。

当前没有误差条和置信区间，避免让虚构示例看起来像统计结果。将来有真实不确定性分析再加入，并标明是情景区间、参数分布区间还是统计置信区间。

## 文件
- PNG：高分辨率预览。
- SVG：矢量图，文本可编辑；可供 Illustrator、Inkscape 等继续修改。
- PDF：两页矢量图，便于讨论与放大查看。
- CSV：各面板全部虚构输入数据。
- reproduce_figures.py：可复现绘图源文件，依赖 numpy、matplotlib。OUT 默认指向原交付目录，可自行修改。

这是期刊论文风格探索，不是 Nature 或 Nature Energy 官方模板。英文标注适用于预览英文投稿版；本说明提供中文解释。
'''
(OUT/'说明_全部为虚构数据.md').write_text(readme)
shutil.copy2(__file__,OUT/'reproduce_figures.py')
with zipfile.ZipFile(OUT.parent/'论文配图_mock_v1.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):z.write(p,arcname=f'paper-figure-mock-v1/{p.name}')
print('Created 2 figures, editable SVGs, 2-page PDF and synthetic source tables.')
