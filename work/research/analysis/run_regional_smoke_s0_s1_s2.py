"""Single-province S0/S1/S2 smoke run on archive inputs (representative weeks).

EVIDENCE TIER: uncalibrated regional smoke test. It uses (i) the annual-anchored
2020 load shape whose hourly form is NOT validated, (ii) archive capacities NOT
verified as 2020 installed capacity, (iii) analyst-assumed AI pool size, idle
power, arrivals, deadlines and tariff shape, (iv) an external-market proxy for
interprovincial exchange. Its purpose is to exercise the S0/S1/S2 pipeline end to
end and to show the ORDER OF MAGNITUDE of the delivery gap under stated
assumptions. Nothing here is a China empirical result.

S0 rigid: AI pool runs the work-conserving ASAP schedule at full speed (fixed).
S1 firm-autonomous: pool minimises its own tariff bill (sequential_tasks.schedule),
   resulting trajectory is then FIXED in the system model.
S2 system-coordinated: pool tasks are free variables in the joint LP.
NOAI: same system without the AI pool (increment reference only).
"""
from pathlib import Path
import sys, json, argparse, time
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from coupled_grid_compute import Generator,Line,Storage,Batch,ComputePool,Scenario,solve
from sequential_tasks import Job,schedule,baseline_asap
SRC=ROOT/'work/research/sources/zenodo_13987282/selected/data'
OUT=ROOT/'outputs/research/tables'

CODE={'Beijing':'BJ','Tianjin':'TJ','Hebei':'HE','Shanxi':'SX','InnerMongolia':'NM','Shandong':'SD','Liaoning':'LN','Jilin':'JL','Heilongjiang':'HL','Shanghai':'SH','Jiangsu':'JS','Zhejiang':'ZJ','Anhui':'AH','Fujian':'FJ','Jiangxi':'JX','Henan':'HA','Hubei':'HB','Hunan':'HN','Chongqing':'CQ','Sichuan':'SC','Guangdong':'GD','Guangxi':'GX','Hainan':'HI','Guizhou':'GZ','Yunnan':'YN','Shaanxi':'SN','Gansu':'GS','Qinghai':'QH','Ningxia':'NX','Xinjiang':'XJ','Tibet':'XZ'}
WEEK_STARTS={'winter':288,'spring':2472,'summer':4656,'autumn':6840}  # 2020 Mondays, UTC+8 index into 8784h
HOURS_PER_YEAR=8784;WEEK=168

def costs_2020():
    c=pd.read_csv(SRC/'costs/costs_2020.csv')
    def g(t,p):
        r=c[(c.technology==t)&(c.parameter==p)];return float(r.value.iloc[0]) if len(r) else None
    def annuity(t,r=0.05):
        life=g(t,'lifetime');inv=g(t,'investment')*1000  # EUR/kW -> EUR/MW
        fom=(g(t,'FOM') or 0)/100
        return inv*(r/(1-(1+r)**-life)+fom)  # EUR per MW per year
    coal_mc=g('coal','fuel')/g('coal','efficiency')+g('coal','VOM');coal_co2=g('coal','CO2 intensity')/g('coal','efficiency')
    gas_mc=g('gas','fuel')/g('OCGT','efficiency')+g('OCGT','VOM');gas_co2=g('gas','CO2 intensity')/g('OCGT','efficiency')
    nuc_mc=g('nuclear','fuel')/g('nuclear','efficiency')+g('nuclear','VOM')
    return dict(coal_mc=coal_mc,coal_co2=coal_co2,gas_mc=gas_mc,gas_co2=gas_co2,nuclear_mc=nuc_mc,
        wind_mc=g('onwind','VOM'),solar_mc=g('solar','VOM'),
        coal_inv_yr=annuity('coal'),ocgt_inv_yr=annuity('OCGT'),
        batt_power_inv_yr=annuity('battery inverter'),batt_energy_inv_yr=g('battery storage','investment')*1000*(0.05/(1-1.05**-g('battery storage','lifetime'))),
        source='PyPSA-China V3.0 archive costs_2020.csv; 5% discount rate; EUR')

def province_inputs(prov):
    z=np.load(ROOT/'work/research/prepared/load_2020_annual_anchored_hourly_shape_UNVALIDATED.npz')
    a=np.load(ROOT/'work/research/prepared/archive_2020_source_inputs_NOT_calibrated.npz')
    i=list(z['provinces']).index(prov)
    cur=pd.read_csv(SRC/'existing_infrastructure/China_current_capacity.csv')
    cur['Province']=cur['Province'].str.replace(' ','')
    cap=cur[cur.Province==prov].groupby('Type').Value.sum().to_dict()
    dams=pd.read_csv(SRC/'hydro/dams_large.csv');big=float(dams[dams.Province==prov]['installed_capacity_10MW'].sum()*10)
    code=CODE[prov]
    hvdc=pd.read_csv(ROOT/'work/research/prepared/HVDC_source_list_rebuilt_UNVERIFIED_GW.csv',index_col=0)
    hvac=pd.read_csv(ROOT/'work/research/prepared/HVAC_source_list_rebuilt_UNVERIFIED_GW.csv',index_col=0)
    inter=float((hvdc.loc[code].sum()+hvac.loc[code].sum())*1000)
    hyd=a['other_hydro_pu'][:,i].copy();valid=a['hydro_valid_hours']
    hyd[~valid]=np.nan;hyd=pd.Series(hyd).interpolate(limit_direction='both').values
    hydro_pu_max=float(np.nanmax(hyd));hyd=np.clip(hyd/max(hydro_pu_max,1e-9),0,1)  # archive 'other hydro' curve is not bounded by 1; normalised to its own annual maximum (assumption)
    clip=lambda x:np.clip(np.nan_to_num(x,nan=0.0),0,1)  # floating-point >1 and offshore NaN (no offshore in province) handled explicitly
    return dict(load=z['load_MW'][:,i],solar_pu=clip(a['solar_pu'][:,i]),onwind_pu=clip(a['onwind_pu'][:,i]),offwind_pu=clip(a['offwind_pu'][:,i]),hydro_pu=hyd,
        cap=cap,big_hydro_mw=big,interconnection_mw=inter,peak=float(z['load_MW'][:,i].max()),hydro_pu_max=hydro_pu_max)

def dvfs_modes(config='ft_llama_8b_dolly'):
    m=pd.read_csv(OUT/'dvfs_measured_and_derived.csv');m=m[m.Workload==config].sort_values('GPU power cap')
    return m['normalized throughput'].values,m['measured_power_ratio'].values,config

def tariff_shape(hours_local,kind):
    """Analyst-assumed TOU shape (relative to flat). Placeholder until official provincial 2020 TOU is transcribed."""
    h=np.asarray(hours_local)%24
    if kind=='flat':return np.ones(len(h))
    s=np.ones(len(h));s[(h>=8)&(h<11)]=1.5;s[(h>=18)&(h<21)]=1.5;s[(h>=23)|(h<7)]=0.5
    return s

def build_jobs(T,u,W):
    """Uniform hourly arrivals of u full-speed pool-hours, deadline W hours later (clipped to horizon).
Analyst assumption; to be replaced by trace-derived arrivals/work distributions."""
    return [Batch(f'b{t}',t,min(t+W,T),u) for t in range(T-0) if t< T]

def run(prov,ai_share=0.05,W=24,u=0.7,idle_frac=0.25,tariff='tou',ext_load_frac=0.6,out_tag='',export=True,coal_min=0.0):
    t0=time.time();c=costs_2020();p=province_inputs(prov)
    q,pr,cfg=dvfs_modes();P_full=ai_share*p['peak'];idle=idle_frac*P_full
    mode_power=idle+(P_full-idle)*(pr-pr.min())/(1-pr.min()) if False else P_full*pr  # measured power ratio scaled to nameplate
    mode_power=np.maximum(mode_power,idle+1e-6)
    wk=1/52.18  # weekly share of annual investment cost
    scen=[];fixed_S0={};fixed_S0b={};fixed_S1={};s1_meta={};jobs_by={}
    for name,start in WEEK_STARTS.items():
        sl=slice(start,start+WEEK);T=WEEK
        scen.append(dict(name=name,load=p['load'][sl],solar=p['solar_pu'][sl],onwind=p['onwind_pu'][sl],offwind=p['offwind_pu'][sl],hydro=p['hydro_pu'][sl]))
        jobs=[Job(f'b{t}',t,min(t+W,T),u) for t in range(T)];jobs_by[name]=jobs
        base=baseline_asap(jobs,1.0,float(mode_power[-1]),T,idle)
        fixed_S0[name]=base
        # S0b: rigid in time (each hour's work done within the hour) but at the lowest-energy measured mode able to do it
        ok=[m for m in range(len(q)) if q[m]>=u-1e-9];mb=min(ok,key=lambda m:(mode_power[m]-idle)*u/q[m]+idle)
        fixed_S0b[name]=np.full(T,idle+(mode_power[mb]-idle)*u/q[mb])
        hours=np.arange(start,start+WEEK)%24
        prices=tariff_shape(hours,tariff)*c['coal_mc']*1.5  # analyst-assumed retail level: 1.5x coal marginal, TOU-shaped
        r=schedule(jobs,q,mode_power,T,idle,prices=prices)
        assert r['feasible'];fixed_S1[name]=np.array(r['slot_average_power']);s1_meta[name]=dict(bill=r['energy_cost'],energy=r['energy'])
    cap=p['cap'];nodes=[prov,'EXT']
    def gens(av):
        G=[]
        coal=cap.get('coal power plant',0)+cap.get('CHP coal',0)
        G.append(Generator('coal',prov,coal,1e6,c['coal_inv_yr']*wk,c['coal_mc'],c['coal_co2'],min_output_fraction=coal_min))  # must-run share of ALL coal capacity is an assumption; real fleets commit units
        G.append(Generator('ocgt',prov,cap.get('OCGT',0),1e6,c['ocgt_inv_yr']*wk,c['gas_mc'],c['gas_co2']))
        G.append(Generator('nuclear',prov,cap.get('nuclear',0),0,0,c['nuclear_mc'],0))
        G.append(Generator('hydro',prov,cap.get('hydroelectricity',0)+p['big_hydro_mw'],0,0,0.,0,availability={s['name']:s['hydro'] for s in scen}))
        G.append(Generator('onwind',prov,cap.get('onshore wind',0),0,0,c['wind_mc'],0,availability={s['name']:s['onwind'] for s in scen}))
        G.append(Generator('offwind',prov,cap.get('offshore wind',0),0,0,c['wind_mc'],0,availability={s['name']:s['offwind'] for s in scen}))
        G.append(Generator('solar',prov,cap.get('solar PV',0),0,0,c['solar_mc'],0,availability={s['name']:s['solar'] for s in scen}))
        G.append(Generator('ext_supply','EXT',1e7,0,0,c['coal_mc']*1.1,c['coal_co2']))  # external market proxy
        return G
    lines=[Line('interconnection',prov,'EXT',p['interconnection_mw'] if export else 0.0,0,0,0.03)]
    stor=[Storage('battery',prov,0,0,1e6,4e6,c['batt_power_inv_yr']*wk,c['batt_energy_inv_yr']*wk,0.95,0.95,0.5)]
    ext_load=ext_load_frac*p['interconnection_mw']
    def scenarios(ai_add=None):
        return [Scenario(s['name'],0.25,{prov:s['load']+(0 if ai_add is None else 0),'EXT':np.full(WEEK,ext_load)}) for s in scen]
    pool=ComputePool('ai',prov,q,mode_power,idle,{s['name']:[Batch(j.name,j.release,j.deadline,j.work) for j in jobs_by[s['name']]] for s in scen})
    res={}
    def summarize(r,tag):
        d=dict(tag=tag,feasible=r['feasible'])
        if not r['feasible']:d.update(status=r.get('solver_status'),message=r.get('message'));return d
        d.update(total_cost=r['total_cost'],**{'cost_'+k:v for k,v in r['cost_components'].items()},new_mw=r['new_generator_mw'],new_batt_mw=r['new_storage_power_mw']['battery'],new_batt_mwh=r['new_storage_energy_mwh']['battery'],
            emissions_t=r['expected_emissions_t'],unserved_mwh=r['expected_unserved_mwh'])
        curt=0;avail=0;imp=0;exp=0;ai=0
        for s in scen:
            rr=r['scenarios'][s['name']]
            for gname,pu,capk in [('onwind',s['onwind'],cap.get('onshore wind',0)),('offwind',s['offwind'],cap.get('offshore wind',0)),('solar',s['solar'],cap.get('solar PV',0))]:
                a=pu*capk;g=np.array(rr['generation'][gname]);avail+=a.sum()*0.25;curt+=(a-g).sum()*0.25
            imp+=np.array(rr['line_reverse']['interconnection']).sum()*0.25;exp+=np.array(rr['line_forward']['interconnection']).sum()*0.25
            if 'ai' in rr['compute_power_mw']:ai+=np.sum(rr['compute_power_mw']['ai'])*0.25
        d.update(re_curtailment_mwh_expweek=curt,re_available_mwh_expweek=avail,re_curtail_rate=curt/avail if avail else None,import_mwh_expweek=imp,export_mwh_expweek=exp,ai_energy_mwh_expweek=ai)
        d['ai_power_series']={s['name']:r['scenarios'][s['name']]['compute_power_mw'].get('ai') for s in scen}
        return d
    r=solve(nodes,scenarios(),gens(None),lines,stor,[],expected_unserved_limit_mwh=0.);res['NOAI']=summarize(r,'NOAI')
    r=solve(nodes,scenarios(),gens(None),lines,stor,[pool],fixed_compute={s['name']:{'ai':fixed_S0[s['name']]} for s in scen},expected_unserved_limit_mwh=0.);res['S0']=summarize(r,'S0_rigid')
    r=solve(nodes,scenarios(),gens(None),lines,stor,[pool],fixed_compute={s['name']:{'ai':fixed_S0b[s['name']]} for s in scen},expected_unserved_limit_mwh=0.);res['S0b']=summarize(r,'S0b_rigid_time_efficient_mode')
    r=solve(nodes,scenarios(),gens(None),lines,stor,[pool],fixed_compute={s['name']:{'ai':fixed_S1[s['name']]} for s in scen},expected_unserved_limit_mwh=0.);res['S1']=summarize(r,'S1_firm_autonomous')
    r=solve(nodes,scenarios(),gens(None),lines,stor,[pool],expected_unserved_limit_mwh=0.);res['S2']=summarize(r,'S2_system_coordinated')
    meta=dict(province=prov,evidence_tier='uncalibrated regional smoke test; not an empirical result',weeks=WEEK_STARTS,
        assumptions=dict(ai_nameplate_mw=P_full,ai_share_of_peak=ai_share,idle_fraction=idle_frac,utilization=u,deadline_hours=W,arrivals='uniform hourly',dvfs_config=cfg,
            tariff=f'{tariff} shape, level 1.5x coal marginal (placeholder)',coal_min_output_fraction=coal_min,external_market='EXT node load = %.2f x interconnection, supply at 1.1x coal marginal, 3%% loss'%ext_load_frac,
            investment='annualized at 5%%, weekly share; new coal/OCGT/battery allowed; renewables fixed',capacities_mw={k:float(v) for k,v in cap.items()},big_hydro_mw=p['big_hydro_mw'],interconnection_mw=p['interconnection_mw'],peak_load_mw=p['peak']),
        costs=c,s1_bills=s1_meta,runtime_s=time.time()-t0)
    out=dict(meta=meta,results=res)
    tag=f"{CODE[prov]}_W{W}_ai{int(ai_share*100)}{'' if export else '_noexport'}{'' if coal_min==0 else f'_coalmin{int(coal_min*100)}'}{out_tag}"
    json.dump(out,open(OUT/f'regional_smoke_{tag}.json','w'),ensure_ascii=False,indent=1,default=float)
    rows=[]
    for k,d in res.items():
        if d['feasible']:rows.append(dict(case=k,total_cost=d['total_cost'],investment=d['cost_investment'],operating=d['cost_operating'],new_coal=d['new_mw']['coal'],new_ocgt=d['new_mw']['ocgt'],new_batt_mw=d['new_batt_mw'],new_batt_mwh=d['new_batt_mwh'],emissions_t=d['emissions_t'],curtail_rate=d['re_curtail_rate'],import_mwh=d['import_mwh_expweek'],export_mwh=d['export_mwh_expweek'],ai_mwh=d['ai_energy_mwh_expweek']))
        else:rows.append(dict(case=k,total_cost=None,note=d.get('message')))
    df=pd.DataFrame(rows);df.to_csv(OUT/f'regional_smoke_{tag}.csv',index=False)
    print(f'== {prov} W={W} ai_share={ai_share} runtime {time.time()-t0:.0f}s');pd.set_option('display.width',250);print(df.to_string(index=False))
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--province',default='Gansu');ap.add_argument('--W',type=int,default=24);ap.add_argument('--ai_share',type=float,default=0.05);ap.add_argument('--tariff',default='tou');ap.add_argument('--noexport',action='store_true');ap.add_argument('--grid',action='store_true');ap.add_argument('--coal_min',type=float,default=0.0)
    a=ap.parse_args()
    if a.grid:
        rows=[]
        for prov in ['Gansu','Jiangsu','Guizhou']:
            for export in [True,False]:
                for ai in [0.05,0.20]:
                    for W in [6,24,72]:
                        o=run(prov,ai,W,tariff=a.tariff,export=export,coal_min=a.coal_min);r=o['results']
                        for k,d in r.items():
                            if d['feasible']:rows.append(dict(province=prov,export=export,ai_share=ai,W=W,case=k,total_cost=d['total_cost'],investment=d['cost_investment'],new_coal=d['new_mw']['coal'],new_ocgt=d['new_mw']['ocgt'],new_batt_mw=d['new_batt_mw'],emissions_t=d['emissions_t'],curtail_rate=d['re_curtail_rate'],ai_mwh=d['ai_energy_mwh_expweek'],export_mwh=d['export_mwh_expweek'],import_mwh=d['import_mwh_expweek']))
                            else:rows.append(dict(province=prov,export=export,ai_share=ai,W=W,case=k,note=d.get('message')))
        pd.DataFrame(rows).to_csv(OUT/('regional_smoke_grid_summary.csv' if a.coal_min==0 else f'regional_smoke_grid_summary_coalmin{int(a.coal_min*100)}.csv'),index=False);print('grid written')
    else:run(a.province,a.ai_share,a.W,tariff=a.tariff,export=not a.noexport,coal_min=a.coal_min)
