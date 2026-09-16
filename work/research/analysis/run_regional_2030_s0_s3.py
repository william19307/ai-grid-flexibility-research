"""Provincial 2030 scenario: S0 rigid / S1 firm-autonomous / S2 system-coordinated / S3 commitment mechanism.

EVIDENCE TIER: public-data scenario with documented assumptions; hourly load shape NOT independently validated.
Inputs: 2020 anchored hourly shape scaled by the archive's 2030/2020 provincial load ratio (shape held constant);
GEM unit-level 2030 thermal/nuclear fleet (operating + construction, retirements applied); 2020 archive wind/solar
capacity as existing with investable 2030 additions at archive 2030 costs; battery and OCGT investable; new coal not
allowed (policy assumption); interprovincial exchange via external-market proxy; committed-capacity must-run heuristic.
AI pool: analyst share of 2030 peak; Helios-derived batches whose slack is the job's own observed queue (lower bound)
times a multiplier plus a base slack. Four representative 2020 weather weeks.
S3: system declares event hours (top q% of NOAI nodal marginal cost per week); firm maximises deliverable reduction
relative to its own autonomous schedule and is compensated at least its opportunity cost; committed trajectory is then
fixed in the system model. Compensation is a transfer; resource cost is the system objective plus firm service cost.
"""
from pathlib import Path
import sys,json,argparse,time
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'));sys.path.insert(0,str(ROOT/'work/research/analysis'))
from coupled_grid_compute import Generator,Line,Storage,Batch,ComputePool,Scenario,solve
from sequential_tasks import Job,schedule,baseline_asap
from response_cost import cost_at_max_response
import run_regional_smoke_s0_s1_s2 as base
SRC=base.SRC;OUT=base.OUT;CODE=base.CODE;WEEK_STARTS=base.WEEK_STARTS;WEEK=168

def costs_2030():
    c=pd.read_csv(SRC/'costs/costs_2030.csv')
    def g(t,p):
        r=c[(c.technology==t)&(c.parameter==p)];return float(r.value.iloc[0]) if len(r) else None
    def annuity(t,r=0.05,inv=None):
        life=g(t,'lifetime');inv=(g(t,'investment') if inv is None else inv)*1000;fom=(g(t,'FOM') or 0)/100
        return inv*(r/(1-(1+r)**-life)+fom)
    return dict(coal_mc=g('coal','fuel')/g('coal','efficiency')+g('coal','VOM'),coal_co2=g('coal','CO2 intensity')/g('coal','efficiency'),
        gas_mc=g('gas','fuel')/g('OCGT','efficiency')+g('OCGT','VOM'),gas_co2=g('gas','CO2 intensity')/g('OCGT','efficiency'),
        nuclear_mc=g('nuclear','fuel')/g('nuclear','efficiency')+g('nuclear','VOM'),wind_mc=g('onwind','VOM'),solar_mc=g('solar','VOM'),
        ocgt_inv_yr=annuity('OCGT'),onwind_inv_yr=annuity('onwind'),solar_inv_yr=annuity('solar'),
        batt_power_inv_yr=annuity('battery inverter'),batt_energy_inv_yr=g('battery storage','investment')*1000*(0.05/(1-1.05**-g('battery storage','lifetime'))),
        source='PyPSA-China V3.0 archive costs_2030.csv; 5% discount; EUR')

GEM_NAME={'InnerMongolia':'Inner Mongolia'}
def gem_fleet_any(prov):
    t=pd.read_csv(OUT/'gem_fleet_all_provinces_2020_2030.csv');name=GEM_NAME.get(prov,prov);t=t[t.province==name].set_index('type')
    g=lambda k:float(t.loc[k,'mw_2030']) if k in t.index else 0.
    return dict(coal=g('coal'),gas=g('oil/gas'),nuclear=g('nuclear'),hydro_gem=g('hydropower'))

def neighbours(prov):
    code=CODE[prov];inv={v:k for k,v in CODE.items()}
    hvdc=pd.read_csv(ROOT/'work/research/prepared/HVDC_source_list_rebuilt_UNVERIFIED_GW.csv',index_col=0);hvac=pd.read_csv(ROOT/'work/research/prepared/HVAC_source_list_rebuilt_UNVERIFIED_GW.csv',index_col=0)
    link=(hvdc.loc[code]+hvac.loc[code]);return {inv[c]:float(v*1000) for c,v in link.items() if v>0 and c in inv}

def gem_fleet(prov):
    t=pd.read_csv(OUT/'gem_fleet_three_provinces_2020_2030.csv');t=t[t.province==prov].set_index('type')
    return dict(coal=float(t.loc['coal','mw_2030_operating_plus_construction']),gas=float(t.loc['oil/gas','mw_2030_operating_plus_construction']),nuclear=float(t.loc['nuclear','mw_2030_operating_plus_construction']),hydro_gem=float(t.loc['hydropower','mw_2030_operating_plus_construction']))

def load_ratio(prov):
    L=pd.read_csv(SRC/'load/Province_Load_2020_2060.csv',index_col=0);r=L.loc[prov,'2030']/L.loc[prov,'2020'];return float(r)

def helios_queue_jobs(T,u,start_hour,slack_mult,slack_base_h,seed):
    """Like base.helios_jobs but slack = job's own observed queue (h) * slack_mult + slack_base_h."""
    hp=ROOT/'work/research/prepared/helios_completed_gpu_jobs_sample.csv.gz'
    d=pd.read_csv(hp);rng=np.random.default_rng(seed);byh=d.groupby('hour').size();byh=byh/byh.sum()
    ref_gpus=float((d.gpu_num*d.duration).sum()/d.duration.sum());batches={};target=u*T
    for t in range(T):
        h=(start_hour+t)%24;n=rng.poisson(max(1e-9,byh.get(h,0))*40)
        if n==0:continue
        sub=d.iloc[rng.choice(len(d),n,replace=True)]
        for _,r in sub.iterrows():
            run_h=min(r.duration/3600,T-t);w=r.gpu_num*run_h/ref_gpus/24.0
            slack=r.queue/3600*slack_mult+slack_base_h
            dl=min(T,t+int(np.ceil(run_h))+int(np.ceil(slack)));dl=max(dl,t+1);batches[(t,dl)]=batches.get((t,dl),0.)+w
    tot=sum(batches.values());f=target/tot if tot>0 else 0
    items=[(t,dl,w*f) for (t,dl),w in batches.items()]
    for it in range(6):  # iterate: guard, then rescale surviving work back to the target, until truncation is negligible
        free=np.ones(T);out=[];ext=0;dropped=0.;kept=[]
        for (t,dl,w) in sorted(items,key=lambda x:(x[1],x[0])):
            d_=dl
            while (free[t:d_].sum()<w-1e-9 or w>0.9*(d_-t)) and d_<T:d_+=1
            if free[t:d_].sum()<w-1e-9:dropped+=w-free[t:d_].sum();w=free[t:d_].sum()
            if w<=1e-9:continue
            if d_!=dl:ext+=1
            rem=w
            for hh in range(t,d_):
                take=min(free[hh],rem);free[hh]-=take;rem-=take
                if rem<=1e-12:break
            out.append(Batch(f'h{t}_{d_}_{len(out)}',t,d_,w));kept.append((t,d_,w))
        realised=sum(w for _,_,w in kept)
        if dropped/target<0.01 or realised<=0:break
        items=[(t,d_,w*target/realised) for (t,d_,w) in kept]
    return out,dict(extended=ext,dropped_share=dropped/target,n=len(out),realised_utilisation=sum(b.work for b in out)/T,guard_iterations=it+1)

_RE_MY=None
def re_profiles_year(prov,year):
    global _RE_MY
    if _RE_MY is None:_RE_MY=pd.read_csv(ROOT/'work/research/prepared/re_profiles_2015_2024_three_provinces.csv.gz',index_col=0,parse_dates=True)
    d=_RE_MY[_RE_MY.index.year==year]
    # map the weather year onto the 2020 (leap) calendar used by the load/hydro arrays: pad/truncate to 8784 hours
    w=d[f'{prov}|wind'].values;sv=d[f'{prov}|solar'].values
    def fit(a):
        if len(a)>=8784:return a[:8784]
        return np.concatenate([a,a[-24*(8784-len(a))//24 - 0:][:8784-len(a)]]) if 8784-len(a)<=24 else np.resize(a,8784)
    return np.clip(fit(w),0,1),np.clip(fit(sv),0,1)

def run(prov,ai_share=0.10,u=0.7,idle_frac=0.41,slack_mult=1.0,slack_base_h=6.0,export=True,ext_load_frac=0.6,coal_min=0.4,event_q=0.05,allow_new_coal=False,tag='',ext_mode='price',rt_price=True,peak_target_2020=None,weather_year=None):
    t0=time.time();c=costs_2030();p=base.province_inputs(prov);fleet=gem_fleet(prov);ratio=load_ratio(prov)
    if weather_year is not None:
        wpu,spu=re_profiles_year(prov,weather_year);p=dict(p);p['onwind_pu']=wpu;p['solar_pu']=spu  # offshore and hydro stay archive 2020
    load20=p['load']
    if peak_target_2020 is not None:
        # peak-adjusted sensitivity: compress deviations from the annual mean so the 2020 peak equals the target while annual energy is conserved
        mu=load20.mean();k=(peak_target_2020-mu)/(load20.max()-mu);load20=mu+k*(load20-mu);assert load20.min()>0
    load30=load20*ratio;peak30=float(load30.max())
    q,pr,cfg=base.dvfs_modes();P_full=ai_share*peak30;idle=idle_frac*P_full
    keep=pr>idle_frac+0.02  # modes whose measured power lies below node idle are not achievable at node level; drop them (no clipping to idle)
    q,pr=q[keep],pr[keep];mode_power=P_full*pr
    wk=1/52.18;scen=[];jobs_by={};fixed_S0={};fixed_S0e={};fixed_S1={};meta_jobs={};prices_by={}
    for name,start in WEEK_STARTS.items():
        sl=slice(start,start+WEEK);T=WEEK
        scen.append(dict(name=name,load=load30[sl],solar=p['solar_pu'][sl],onwind=p['onwind_pu'][sl],offwind=p['offwind_pu'][sl],hydro=p['hydro_pu'][sl]))
        bb,mj=helios_queue_jobs(T,u,start%24,slack_mult,slack_base_h,seed=start);meta_jobs[name]=mj
        jobs=[Job(b.name,b.release,b.deadline,b.work) for b in bb];jobs_by[name]=jobs
        fixed_S0[name]=baseline_asap(jobs,1.0,float(mode_power[-1]),T,idle)
        flat=np.full(T,float(c['coal_mc']*1.5));delay=np.array([[1e-3*max(0,t-j.release) for t in range(T)] for j in jobs])  # tie-break: earliest execution
        r0e=schedule(jobs,q,mode_power,T,idle,prices=flat,service_cost_per_work=delay)
        if not r0e['feasible']:raise RuntimeError(('S0e infeasible',name))
        fixed_S0e[name]=np.array(r0e['slot_average_power'])
        hours=np.arange(start,start+WEEK)%24;prices=base.tariff_shape(hours,'official',prov)*c['coal_mc']*1.5;prices_by[name]=prices
        r=schedule(jobs,q,mode_power,T,idle,prices=prices)
        if not r['feasible']:raise RuntimeError(('S1 infeasible',name))
        fixed_S1[name]=np.array(r['slot_average_power']);meta_jobs[name]['s1_bill']=r['energy_cost']
    cap=p['cap'];nodes=[prov,'EXT'];hydro_mw=fleet['hydro_gem']  # GEM 2030 hydro units (operating+construction); archive other-hydro profile applied
    nb={}
    if ext_mode=='neighbours':
        # EXT = aggregate of directly connected provinces: anchored load x their 2030 ratio, GEM 2030 fleets, archive RE capacities and profiles
        nbs=neighbours(prov);agg=dict(load=np.zeros(len(p['load'])),solar=np.zeros(len(p['load'])),onwind=np.zeros(len(p['load'])),offwind=np.zeros(len(p['load'])),hydro=np.zeros(len(p['load'])),coal=0.,gas=0.,nuclear=0.,hydro_mw=0.,solar_mw=0.,onwind_mw=0.,offwind_mw=0.)
        for n_ in nbs:
            try:pn=base.province_inputs(n_)
            except Exception as ex:print('skip neighbour',n_,ex);continue
            fn=gem_fleet_any(n_);rn=load_ratio(n_)
            agg['load']+=pn['load']*rn;agg['solar']+=pn['solar_pu']*pn['cap'].get('solar PV',0);agg['onwind']+=pn['onwind_pu']*pn['cap'].get('onshore wind',0);agg['offwind']+=pn['offwind_pu']*pn['cap'].get('offshore wind',0)
            agg['hydro']+=pn['hydro_pu']*fn['hydro_gem'];agg['coal']+=fn['coal'];agg['gas']+=fn['gas'];agg['nuclear']+=fn['nuclear'];agg['hydro_mw']+=fn['hydro_gem']
            agg['solar_mw']+=pn['cap'].get('solar PV',0);agg['onwind_mw']+=pn['cap'].get('onshore wind',0);agg['offwind_mw']+=pn['cap'].get('offshore wind',0)
        nb=dict(names=list(nbs),links_mw=nbs,agg=agg)
    # committed-capacity heuristic per week: coal committed to cover weekly max residual after RE/nuclear/hydro, /0.85, using rigid AI level
    def committed(s):
        re=s['onwind']*cap.get('onshore wind',0)+s['offwind']*cap.get('offshore wind',0)+s['solar']*cap.get('solar PV',0)
        resid=s['load']+fixed_S0[s['name']]-re-fleet['nuclear']*0.9-hydro_mw*s['hydro']
        need=max(0.,float(np.max(resid))/0.85);return min(need,fleet['coal'])
    comm={s['name']:committed(s) for s in scen}
    def gens():
        G=[Generator('coal',prov,fleet['coal'],1e6 if allow_new_coal else 0.,0. if not allow_new_coal else 0.,c['coal_mc'],c['coal_co2'],availability={s['name']:np.full(WEEK,comm[s['name']]/fleet['coal'] if fleet['coal']>0 else 0.) for s in scen},min_output_fraction=coal_min),
           Generator('ocgt',prov,fleet['gas'],1e6,c['ocgt_inv_yr']*wk,c['gas_mc'],c['gas_co2']),
           Generator('nuclear',prov,fleet['nuclear'],0,0,c['nuclear_mc'],0,availability={s['name']:np.full(WEEK,0.9) for s in scen}),
           Generator('hydro',prov,hydro_mw,0,0,0.,0,availability={s['name']:s['hydro'] for s in scen}),
           Generator('onwind',prov,cap.get('onshore wind',0),1e6,c['onwind_inv_yr']*wk,c['wind_mc'],0,availability={s['name']:s['onwind'] for s in scen}),
           Generator('offwind',prov,cap.get('offshore wind',0),0,0,c['wind_mc'],0,availability={s['name']:s['offwind'] for s in scen}),
           Generator('solar',prov,cap.get('solar PV',0),1e6,c['solar_inv_yr']*wk,c['solar_mc'],0,availability={s['name']:s['solar'] for s in scen}),
           ]
        if ext_mode=='neighbours':
            a=nb['agg'];avail=lambda arr:{s_['name']:np.clip(arr[WEEK_STARTS[s_['name']]:WEEK_STARTS[s_['name']]+WEEK]/max(1e-9,x_),0,1) for s_ in scen}
            G+=[Generator('nb_coal','EXT',a['coal'],0,0,c['coal_mc'],c['coal_co2'],min_output_fraction=coal_min*0.5),  # neighbour must-run applied at half strength (no committed-capacity heuristic there)
                Generator('nb_gas','EXT',a['gas'],1e6,c['ocgt_inv_yr']*wk,c['gas_mc'],c['gas_co2']),
                Generator('nb_nuclear','EXT',a['nuclear'],0,0,c['nuclear_mc'],0,availability={s_['name']:np.full(WEEK,0.9) for s_ in scen}),
                Generator('nb_hydro','EXT',a['hydro_mw'],0,0,0.,0,availability={s_['name']:np.clip(a['hydro'][WEEK_STARTS[s_['name']]:WEEK_STARTS[s_['name']]+WEEK]/max(a['hydro_mw'],1e-9),0,1) for s_ in scen}),
                Generator('nb_solar','EXT',a['solar_mw'],1e6,c['solar_inv_yr']*wk,c['solar_mc'],0,availability={s_['name']:np.clip(a['solar'][WEEK_STARTS[s_['name']]:WEEK_STARTS[s_['name']]+WEEK]/max(a['solar_mw'],1e-9),0,1) for s_ in scen}),
                Generator('nb_onwind','EXT',a['onwind_mw'],1e6,c['onwind_inv_yr']*wk,c['wind_mc'],0,availability={s_['name']:np.clip(a['onwind'][WEEK_STARTS[s_['name']]:WEEK_STARTS[s_['name']]+WEEK]/max(a['onwind_mw'],1e-9),0,1) for s_ in scen}),
                Generator('nb_offwind','EXT',a['offwind_mw'],0,0,c['wind_mc'],0,availability={s_['name']:np.clip(a['offwind'][WEEK_STARTS[s_['name']]:WEEK_STARTS[s_['name']]+WEEK]/max(a['offwind_mw'],1e-9),0,1) for s_ in scen}),
                Generator('nb_unserved_proxy','EXT',1e7,0,0,c['gas_mc']*3,c['gas_co2'])]  # very expensive backstop so neighbour scarcity is priced, not free
        else:G.append(Generator('ext_supply','EXT',1e7,0,0,c['coal_mc']*1.1,c['coal_co2']))
        return G
    lines=[Line('interconnection',prov,'EXT',p['interconnection_mw'] if export else 0.,0,0,0.03)]
    stor=[Storage('battery',prov,0,0,1e6,4e6,c['batt_power_inv_yr']*wk,c['batt_energy_inv_yr']*wk,0.95,0.95,0.5)]
    if ext_mode=='neighbours':stor.append(Storage('nb_battery','EXT',0,0,1e6,4e6,c['batt_power_inv_yr']*wk,c['batt_energy_inv_yr']*wk,0.95,0.95,0.5))
    ext_load=ext_load_frac*p['interconnection_mw']
    if ext_mode=='neighbours':scenarios=[Scenario(s['name'],0.25,{prov:s['load'],'EXT':nb['agg']['load'][WEEK_STARTS[s['name']]:WEEK_STARTS[s['name']]+WEEK]}) for s in scen]
    else:scenarios=[Scenario(s['name'],0.25,{prov:s['load'],'EXT':np.full(WEEK,ext_load)}) for s in scen]
    pool=ComputePool('ai',prov,q,mode_power,idle,{s['name']:[Batch(j.name,j.release,j.deadline,j.work) for j in jobs_by[s['name']]] for s in scen})
    def summarize(r,tagname):
        d=dict(tag=tagname,feasible=r['feasible'])
        if not r['feasible']:d.update(message=r.get('message'));return d
        d.update(total_cost=r['total_cost'],**{'cost_'+k:v for k,v in r['cost_components'].items()},new_mw=r['new_generator_mw'],new_batt_mw=r['new_storage_power_mw']['battery'],new_batt_mwh=r['new_storage_energy_mwh']['battery'],emissions_t=r['expected_emissions_t'],unserved_mwh=r['expected_unserved_mwh'])
        curt=avail=imp=exp=ai=0.;mc={}
        for s in scen:
            rr=r['scenarios'][s['name']]
            for gname,pu,capk in [('onwind',s['onwind'],cap.get('onshore wind',0)+r['new_generator_mw']['onwind']),('offwind',s['offwind'],cap.get('offshore wind',0)),('solar',s['solar'],cap.get('solar PV',0)+r['new_generator_mw']['solar'])]:
                a=pu*capk;g=np.array(rr['generation'][gname]);avail+=a.sum()*0.25;curt+=(a-g).sum()*0.25
            imp+=np.array(rr['line_reverse']['interconnection']).sum()*0.25;exp+=np.array(rr['line_forward']['interconnection']).sum()*0.25
            if 'ai' in rr['compute_power_mw']:ai+=np.sum(rr['compute_power_mw']['ai'])*0.25
            mc[s['name']]=rr['nodal_balance_marginal_cost'][prov]
        d.update(curtail_rate=curt/avail if avail else None,import_mwh=imp,export_mwh=exp,ai_mwh=ai,marginal_cost=mc)
        return d
    res={}
    r=solve(nodes,scenarios,gens(),lines,stor,[],expected_unserved_limit_mwh=0.);res['NOAI']=summarize(r,'NOAI')
    r=solve(nodes,scenarios,gens(),lines,stor,[pool],fixed_compute={s['name']:{'ai':fixed_S0[s['name']]} for s in scen},expected_unserved_limit_mwh=0.);res['S0']=summarize(r,'S0')
    r=solve(nodes,scenarios,gens(),lines,stor,[pool],fixed_compute={s['name']:{'ai':fixed_S0e[s['name']]} for s in scen},expected_unserved_limit_mwh=0.);res['S0e']=summarize(r,'S0e')
    r=solve(nodes,scenarios,gens(),lines,stor,[pool],fixed_compute={s['name']:{'ai':fixed_S1[s['name']]} for s in scen},expected_unserved_limit_mwh=0.);res['S1']=summarize(r,'S1')
    r=solve(nodes,scenarios,gens(),lines,stor,[pool],expected_unserved_limit_mwh=0.);res['S2']=summarize(r,'S2')
    if rt_price and res['S2']['feasible']:
        fixed_S1rt={}
        for s in scen:
            name=s['name'];mc2=np.array(res['S2']['marginal_cost'][name]);pr_=np.maximum(mc2,0.)
            pr_=pr_*(prices_by[name].mean()/max(pr_.mean(),1e-9))  # same average level as the tariff, S2 real-time shape
            rr=schedule(jobs_by[name],q,mode_power,WEEK,idle,prices=pr_)
            fixed_S1rt[name]=np.array(rr['slot_average_power']) if rr['feasible'] else fixed_S1[name]
        r=solve(nodes,scenarios,gens(),lines,stor,[pool],fixed_compute={s['name']:{'ai':fixed_S1rt[s['name']]} for s in scen},expected_unserved_limit_mwh=0.);res['S1rt']=summarize(r,'S1rt_firm_under_S2_realtime_price')
    # S3: events = top event_q hours of S1-run nodal marginal cost per week; firm commits max deliverable reduction vs its own S1 schedule
    fixed_S3={};s3meta={}
    for s in scen:
        name=s['name']
        if not res['S1']['feasible']:fixed_S3[name]=fixed_S1[name];s3meta[name]=dict(commitment_mw=0.,opportunity_cost=0.,compensation_floor=0.,events=[],reason='S1 infeasible');continue
        mcs=np.array(res['S1']['marginal_cost'][name]);k=max(1,int(round(event_q*WEEK)))
        med=float(np.median(mcs));cand=[int(i) for i in np.argsort(-mcs)[:k] if mcs[i]>1.2*med]  # scarcity rule: only hours >20% above weekly median
        events=sorted(cand)
        if not events:
            fixed_S3[name]=fixed_S1[name];s3meta[name]=dict(commitment_mw=0.,opportunity_cost=0.,compensation_floor=0.,events=[],reason='no scarcity hours (marginal cost flat)');continue
        rr=cost_at_max_response(jobs_by[name],q,mode_power,WEEK,idle,fixed_S1[name],events,prices_by[name])
        if rr['feasible']:
            fixed_S3[name]=np.array(rr['committed']['slot_average_power']);s3meta[name]=dict(commitment_mw=rr['commitment'],opportunity_cost=rr['opportunity_cost'],compensation_floor=rr['minimum_total_compensation_for_weak_participation'],events=events,event_mc_mean=float(mcs[events].mean()))
        else:fixed_S3[name]=fixed_S1[name];s3meta[name]=dict(commitment_mw=0.,opportunity_cost=0.,compensation_floor=0.,events=events,reason=rr.get('reason'))
    r=solve(nodes,scenarios,gens(),lines,stor,[pool],fixed_compute={s['name']:{'ai':fixed_S3[s['name']]} for s in scen},expected_unserved_limit_mwh=0.);res['S3']=summarize(r,'S3')
    for k_ in res:res[k_].pop('marginal_cost',None)
    meta=dict(province=prov,evidence_tier='public-data 2030 scenario; hourly load shape unvalidated; documented assumptions',load_ratio_2030_2020=ratio,peak_2030_mw=peak30,fleet_2030_gem=fleet,hydro_mw_gem_2030=hydro_mw,committed_coal_mw=comm,
        neighbours=(nb.get('names'),nb.get('links_mw')) if nb else None,exchange='islanded (interconnection = 0)' if not export else ('fixed-price external market' if ext_mode=='price' else 'neighbour aggregate node'),ai_work_pool_hours={s['name']:float(sum(j.work for j in jobs_by[s['name']])) for s in scen},assumptions=dict(modes_kept=int(len(q)),weather_year=weather_year,peak_target_2020=peak_target_2020,ext_mode=ext_mode,ai_share_of_peak=ai_share,ai_nameplate_mw=P_full,idle_fraction=idle_frac,utilization=u,slack='job observed queue x %.1f + %.1f h'%(slack_mult,slack_base_h),dvfs_config=cfg,tariff='official shape, level 1.5x coal marginal',coal_min_of_committed=coal_min,allow_new_coal=allow_new_coal,export=export,event_top_share=event_q,external_market='EXT load %.2f x interconnection at 1.1x coal marginal, 3%% loss'%ext_load_frac),
        job_meta=meta_jobs,s3=s3meta,costs=c,runtime_s=time.time()-t0)
    out=dict(meta=meta,results=res);name=f"{CODE[prov]}_2030_ai{int(ai_share*100)}{'' if export else '_noexport'}_sm{slack_mult:g}_sb{int(slack_base_h)}{'_nb' if ext_mode=='neighbours' else ''}{'' if peak_target_2020 is None else '_pk'}{'' if weather_year is None else f'_wy{weather_year}'}{tag}"
    json.dump(out,open(OUT/f'regional_2030_{name}.json','w'),ensure_ascii=False,indent=1,default=float)
    rows=[]
    for k_,d in res.items():
        if d['feasible']:rows.append(dict(case=k_,total_cost=d['total_cost'],investment=d['cost_investment'],new_ocgt=d['new_mw']['ocgt'],new_onwind=d['new_mw']['onwind'],new_solar=d['new_mw']['solar'],new_batt_mw=d['new_batt_mw'],emissions_t=d['emissions_t'],curtail=d['curtail_rate'],ai_mwh=d['ai_mwh'],import_mwh=d['import_mwh'],export_mwh=d['export_mwh']))
        else:rows.append(dict(case=k_,note=d.get('message')))
    df=pd.DataFrame(rows);df.to_csv(OUT/f'regional_2030_{name}.csv',index=False)
    print(f'== {prov} 2030 ai={ai_share} export={export} runtime {time.time()-t0:.0f}s ratio {ratio:.2f} peak {peak30:.0f} committed {({k:round(v) for k,v in comm.items()})}');pd.set_option('display.width',250);print(df.to_string(index=False))
    print('S3:',{k:{kk:(round(vv,1) if isinstance(vv,float) else vv) for kk,vv in v.items() if kk!='events'} for k,v in s3meta.items()})
    return out

def grid(ext_mode='price',out_name='regional_2030_grid_summary.csv'):
    rows=[]
    for prov in ['Gansu','Jiangsu','Guizhou']:
        for export in [True,False]:
            for ai in [0.05,0.10,0.20]:
                for sm,sb in [(1.0,6.0),(3.0,24.0)]:
                    o=run(prov,ai,slack_mult=sm,slack_base_h=sb,export=export,ext_mode=ext_mode);r=o['results'];m=o['meta']
                    comp=sum(v.get('compensation_floor',0) for v in m['s3'].values())*0.25;commit=np.mean([v.get('commitment_mw',0) for v in m['s3'].values()])
                    for k,d in r.items():
                        if d['feasible']:rows.append(dict(province=prov,export=export,ai_share=ai,slack_mult=sm,slack_base_h=sb,case=k,total_cost=d['total_cost'],investment=d['cost_investment'],new_ocgt=d['new_mw']['ocgt'],new_onwind=d['new_mw']['onwind'],new_solar=d['new_mw']['solar'],new_batt_mw=d['new_batt_mw'],emissions_t=d['emissions_t'],curtail=d['curtail_rate'],ai_mwh=d['ai_mwh'],import_mwh=d['import_mwh'],export_mwh=d['export_mwh'],s3_compensation_floor_expweek=comp,s3_mean_commitment_mw=commit,peak_2030=m['peak_2030_mw']))
                        else:rows.append(dict(province=prov,export=export,ai_share=ai,slack_mult=sm,slack_base_h=sb,case=k,note=d.get('message')))
    pd.DataFrame(rows).to_csv(OUT/out_name,index=False);print('GRID2030_DONE')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--grid',action='store_true');ap.add_argument('--ext_mode',default='price');ap.add_argument('--province',default='Guizhou');ap.add_argument('--ai_share',type=float,default=0.10);ap.add_argument('--noexport',action='store_true');ap.add_argument('--slack_mult',type=float,default=1.0);ap.add_argument('--slack_base',type=float,default=6.0);ap.add_argument('--coal_min',type=float,default=0.4)
    a=ap.parse_args()
    if a.grid:grid(a.ext_mode,'regional_2030_grid_summary.csv' if a.ext_mode=='price' else 'regional_2030_grid_summary_neighbours.csv')
    else:run(a.province,a.ai_share,slack_mult=a.slack_mult,slack_base_h=a.slack_base,export=not a.noexport,coal_min=a.coal_min,ext_mode=a.ext_mode)
