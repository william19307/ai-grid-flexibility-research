"""Chronological transport-grid + local compute planning LP.

Investments are shared across supplied scenarios; dispatch/tasks have perfect
foresight within each scenario. Monetary capacity costs apply to the modeled
study horizon (caller must annualize consistently). MW, MWh, hours, currency.
Optional fixed-capacity thermal unit commitment uses a MILP.
This module does not implement AC power flow, task migration,
checkpoint overhead or stochastic/nonanticipative real-time control.
Reservoir cascades conserve water volume with fixed specific water consumption,
zero routing delay and no evaporation; inflows must be local incremental inflows.
"""
from dataclasses import dataclass,field
from typing import Mapping,Sequence
import numpy as np
from scipy.optimize import linprog, milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix, vstack
import thermal_commitment as thermal
import industrial_captive as industrial


@dataclass
class Generator:
    name:str
    node:str
    existing_mw:float
    max_new_mw:float
    investment_cost:float
    marginal_cost:float
    emissions_t_per_mwh:float=0.
    availability:Mapping[str,Sequence[float]]=field(default_factory=dict)
    min_output_fraction:float=0.  # must-run share of available capacity (existing+new); 0 keeps prior behaviour


@dataclass
class Line:
    name:str
    source:str
    target:str
    existing_mw:float
    max_new_mw:float=0.
    investment_cost:float=0.
    loss_fraction:float=0.
    flow_cost_per_mwh:float=1e-5


@dataclass
class Storage:
    name:str
    node:str
    existing_power_mw:float=0.
    existing_energy_mwh:float=0.
    max_new_power_mw:float=0.
    max_new_energy_mwh:float=0.
    power_investment_cost:float=0.
    energy_investment_cost:float=0.
    charge_efficiency:float=1.
    discharge_efficiency:float=1.
    initial_soc_fraction:float=0.
    throughput_cost:float=.001


@dataclass
class Reservoir:
    name:str
    node:str
    turbine_mw:float
    usable_volume_hm3:float  # 1 hm3 = 1 million m3
    initial_volume_hm3:float # same usable-storage reference, not total volume
    specific_water_m3_per_mwh:float
    inflow_hm3_per_hour:Mapping[str,Sequence[float]] # local incremental inflow
    downstream:str|None=None  # dam name; zero river travel time approximation
    marginal_cost:float=0.
    spillage_cost_per_hm3:float=0.
    availability:Mapping[str,Sequence[float]]=field(default_factory=dict)


@dataclass
class Batch:
    name:str
    release:int
    deadline:int
    work:float  # full-speed-equivalent pool-hours, for this pool's configuration
    delay_cost_per_work_hour:float=0.


@dataclass
class ComputePool:
    name:str
    node:str
    rates:Sequence[float]
    mode_power_mw:Sequence[float]
    idle_power_mw:float
    jobs:Mapping[str,Sequence[Batch]]
    connection_limit_mw:float=np.inf


@dataclass
class Scenario:
    name:str
    probability:float
    load_mw:Mapping[str,Sequence[float]]


class Matrix:
    def __init__(self):self.cost=[];self.bounds=[];self.vars=[];self.eq=[];self.ub=[];self.beq=[];self.bub=[];self.eq_names=[];self.integrality=[]
    def var(self,name,cost=0.,lower=0.,upper=None,binary=False):
        i=len(self.cost);self.vars.append(name);self.cost.append(cost);self.bounds.append((lower,upper));self.integrality.append(int(binary));return i
    def equal(self,row,rhs,name):self.eq.append(row);self.beq.append(rhs);self.eq_names.append(name)
    def upper(self,row,rhs):self.ub.append(row);self.bub.append(rhs)
    def sparse(self,rows):
        rr=[];cc=[];vv=[]
        for i,row in enumerate(rows):
            for j,v in row.items():
                if v:rr.append(i);cc.append(j);vv.append(v)
        return coo_matrix((vv,(rr,cc)),shape=(len(rows),len(self.cost))).tocsr()


def solve(nodes,scenarios,generators,lines=(),storage=(),pools=(),dt=1.,
          fixed_compute=None,expected_unserved_limit_mwh=0.,unserved_cost=10000.,
          emissions_limit_t=None,reservoirs=(),commitments=(),milp_time_limit_s=120.,external_fixed_load=None,
          industrial_sites=()):
    """Optimize shared investment and scenario dispatch.

fixed_compute[scenario][pool] can fix a *verified* task-feasible power sequence.
The task variables and exact per-batch work constraints remain in that solve,
so an infeasible externally supplied power trajectory is rejected.
external_fixed_load adds separately verified mandatory power at each node. It
does not create fluid task variables and cannot be shed as non-compute load; the
caller must supply its scheduling certificate and power-boundary assumptions.
industrial_sites adds mandatory private gross process demand, shared gas fuel,
generator auxiliaries and a lossless signed grid interface. These are explicit
conditional inputs, not evidence of calibrated industrial flexibility.
    """
    nodes=list(nodes);scenarios=list(scenarios);generators=list(generators);lines=list(lines);storage=list(storage);pools=list(pools)
    reservoirs=list(reservoirs)
    commitments=list(commitments)
    industrial_sites=list(industrial_sites)
    controls={c.generator:c for c in commitments}
    if len(controls)!=len(commitments):raise ValueError("Duplicate commitment controls")
    gen_by_name={g.name:g for g in generators}
    if not set(controls)<=set(gen_by_name):raise ValueError("Unknown committable generator")
    for name,control in controls.items():thermal.validate(control,gen_by_name[name])
    if not np.isfinite(milp_time_limit_s) or milp_time_limit_s<=0:raise ValueError("Invalid MILP time limit")
    if not nodes or len(set(nodes))!=len(nodes) or not scenarios or not np.isfinite(dt) or dt<=0:raise ValueError('Invalid nodes/scenarios/time')
    if len({s.name for s in scenarios})!=len(scenarios):raise ValueError('Scenario names must be unique')
    if not np.isclose(sum(s.probability for s in scenarios),1) or any(s.probability<=0 for s in scenarios):raise ValueError('Probabilities must be positive and sum to one')
    T=len(scenarios[0].load_mw[nodes[0]])
    if T==0:raise ValueError('Empty horizon')
    for s in scenarios:
        if set(s.load_mw)!=set(nodes):raise ValueError('Each scenario must supply exactly all nodes')
        for a in s.load_mw.values():
            a=np.asarray(a,float)
            if a.shape!=(T,) or not np.isfinite(a).all() or (a<0).any():raise ValueError('Invalid non-compute load')
    if external_fixed_load is not None:
        if set(external_fixed_load)!={s.name for s in scenarios}:raise ValueError('External power must cover exactly all scenarios')
        for name,node_power in external_fixed_load.items():
            if set(node_power)!=set(nodes):raise ValueError('External power must cover exactly all nodes')
            for values in node_power.values():
                a=np.asarray(values,float)
                if a.shape!=(T,) or not np.isfinite(a).all() or (a<0).any():raise ValueError('Invalid external fixed power')
    for collection in [generators,lines,storage,pools,reservoirs]:
        if len({a.name for a in collection})!=len(collection):raise ValueError('Asset names must be unique within type')
    scenario_names={s.name for s in scenarios}
    def finite_nonnegative(values):
        return all(np.isfinite(v) and v>=0 for v in values)
    for g in generators:
        if not finite_nonnegative([g.existing_mw,g.max_new_mw,g.investment_cost,g.marginal_cost,g.emissions_t_per_mwh]):raise ValueError('Nonfinite or negative generator parameter')
        if g.availability and set(g.availability)!=scenario_names:raise ValueError('Explicit availability must cover exactly all scenarios')
        if g.node not in nodes or min(g.existing_mw,g.max_new_mw,g.investment_cost,g.marginal_cost,g.emissions_t_per_mwh)<0:raise ValueError('Invalid generator')
        if not np.isfinite(g.min_output_fraction) or not 0<=g.min_output_fraction<=1:raise ValueError('min_output_fraction must be in [0,1]')
    for l in lines:
        if not finite_nonnegative([l.existing_mw,l.max_new_mw,l.investment_cost,l.flow_cost_per_mwh]):raise ValueError('Nonfinite or negative line parameter')
        if l.source not in nodes or l.target not in nodes or l.source==l.target or not 0<=l.loss_fraction<1 or min(l.existing_mw,l.max_new_mw,l.investment_cost,l.flow_cost_per_mwh)<0:raise ValueError('Invalid line')
    for b in storage:
        if not finite_nonnegative([b.existing_power_mw,b.existing_energy_mwh,b.max_new_power_mw,b.max_new_energy_mwh,b.power_investment_cost,b.energy_investment_cost,b.throughput_cost]):raise ValueError('Nonfinite or negative storage parameter')
        if b.node not in nodes or not 0<b.charge_efficiency<=1 or not 0<b.discharge_efficiency<=1 or not 0<=b.initial_soc_fraction<=1:raise ValueError('Invalid storage')
        if min(b.existing_power_mw,b.existing_energy_mwh,b.max_new_power_mw,b.max_new_energy_mwh,b.power_investment_cost,b.energy_investment_cost,b.throughput_cost)<0:raise ValueError('Negative storage parameter')
    for p in pools:
        if not np.isfinite(p.idle_power_mw) or np.isnan(p.connection_limit_mw) or p.connection_limit_mw<p.idle_power_mw:raise ValueError('Invalid idle power or connection limit')
        q=np.asarray(p.rates,float);power=np.asarray(p.mode_power_mw,float)
        if p.node not in nodes or q.ndim!=1 or len(q)==0 or power.shape!=q.shape or not np.isfinite(q).all() or not np.isfinite(power).all() or (q<=0).any() or (power<p.idle_power_mw).any() or p.idle_power_mw<0:raise ValueError('Invalid pool modes')
        if set(p.jobs)!=set(s.name for s in scenarios):raise ValueError('Pool jobs must be explicit for all scenarios')
        for s in scenarios:
            jobs=p.jobs[s.name]
            if len({j.name for j in jobs})!=len(jobs):raise ValueError('Job names must be unique per pool/scenario')
            for j in jobs:
                if not isinstance(j.release,(int,np.integer)) or not isinstance(j.deadline,(int,np.integer)) or not finite_nonnegative([j.work,j.delay_cost_per_work_hour]):raise ValueError('Invalid batch time or work')
                if not 0<=j.release<j.deadline<=T or j.work<0 or j.delay_cost_per_work_hour<0:raise ValueError('Invalid batch')
    reservoir_by_name={h.name:h for h in reservoirs}
    for h in reservoirs:
        if h.node not in nodes or not finite_nonnegative([h.turbine_mw,h.usable_volume_hm3,h.initial_volume_hm3,h.specific_water_m3_per_mwh,h.marginal_cost,h.spillage_cost_per_hm3]):raise ValueError('Invalid reservoir parameter')
        if h.specific_water_m3_per_mwh<=0 or h.initial_volume_hm3>h.usable_volume_hm3:raise ValueError('Invalid reservoir conversion or initial state')
        if h.downstream is not None and h.downstream not in reservoir_by_name:raise ValueError('Unknown downstream reservoir')
        if set(h.inflow_hm3_per_hour)!=scenario_names:raise ValueError('Explicit local inflow required for all scenarios')
        if h.availability and set(h.availability)!=scenario_names:raise ValueError('Explicit turbine availability must cover all scenarios')
        for s in scenarios:
            inflow=np.asarray(h.inflow_hm3_per_hour[s.name],float)
            availability=np.asarray(h.availability.get(s.name,np.ones(T)),float)
            if inflow.shape!=(T,) or not np.isfinite(inflow).all() or (inflow<0).any():raise ValueError('Invalid local reservoir inflow')
            if availability.shape!=(T,) or not np.isfinite(availability).all() or (availability<0).any() or (availability>1).any():raise ValueError('Invalid turbine availability')
        seen=set();current=h.name
        while current is not None:
            if current not in reservoir_by_name:raise ValueError('Unknown downstream reservoir')
            if current in seen:raise ValueError('Reservoir routing must be acyclic')
            seen.add(current);current=reservoir_by_name[current].downstream
    if expected_unserved_limit_mwh is None or not finite_nonnegative([expected_unserved_limit_mwh,unserved_cost]):raise ValueError('Explicit finite nonnegative expected unserved limit and cost required')
    if emissions_limit_t is not None and not finite_nonnegative([emissions_limit_t]):raise ValueError('Invalid emissions limit')
    if fixed_compute is not None:
        if not set(fixed_compute)<=scenario_names or any(not set(v)<={p.name for p in pools} for v in fixed_compute.values()):raise ValueError('Unknown fixed-compute scenario or pool')
    industrial_nodes=industrial.validate(industrial_sites,nodes,generators,lines,controls,scenario_names,T)
    m=Matrix();gen_new={};line_new={};sp_new={};se_new={}
    for g in generators:gen_new[g.name]=m.var(('new_gen',g.name),g.investment_cost,upper=g.max_new_mw)
    for l in lines:line_new[l.name]=m.var(('new_line',l.name),l.investment_cost,upper=l.max_new_mw)
    for b in storage:
        sp_new[b.name]=m.var(('new_storage_power',b.name),b.power_investment_cost,upper=b.max_new_power_mw)
        se_new[b.name]=m.var(('new_storage_energy',b.name),b.energy_investment_cost,upper=b.max_new_energy_mwh)
    result_indices={};eens_row={};co2_row={};service_indices=[];op_indices=[];fixed_co2=0.
    for s in scenarios:
        probability=s.probability;balances={(n,t):{} for n in nodes for t in range(T)}
        external={n:np.zeros(T) if external_fixed_load is None else np.asarray(external_fixed_load[s.name][n],float) for n in nodes}
        rhs={(n,t):float(s.load_mw[n][t]+external[n][t]) for n in nodes for t in range(T)}
        ix={'generation':{},'unserved':{},'line_forward':{},'line_reverse':{},'charge':{},'discharge':{},'soc':{},'compute':{},'tasks':{},'balance_rows':{},'commitment':{}}
        ix.update({'hydro_generation':{},'hydro_spillage_hm3_per_hour':{},'hydro_volume_hm3':{}})
        for n in nodes:
            arr=[]
            for t in range(T):
                v=m.var(('unserved',s.name,n,t),probability*dt*unserved_cost,upper=0. if n in industrial_nodes else float(s.load_mw[n][t]))
                arr.append(v);balances[n,t][v]=1;eens_row[v]=probability*dt
            ix['unserved'][n]=arr
        for g in generators:
            availability=np.asarray(g.availability.get(s.name,np.ones(T)),float)
            if availability.shape!=(T,) or not np.isfinite(availability).all() or (availability<0).any() or (availability>1).any():raise ValueError('Invalid availability')
            arr=[]
            for t,a in enumerate(availability):
                v=m.var(('generation',s.name,g.name,t),probability*dt*g.marginal_cost)
                arr.append(v);balances[g.node,t][v]=1
                m.upper({v:1,gen_new[g.name]:-a},a*g.existing_mw)
                if g.name not in controls and g.min_output_fraction>0:m.upper({v:-1,gen_new[g.name]:g.min_output_fraction*a},-g.min_output_fraction*a*g.existing_mw)
                co2_row[v]=probability*dt*g.emissions_t_per_mwh;op_indices.append(v)
            ix['generation'][g.name]=arr
            if g.name in controls:
                unit=thermal.add_constraints(m,g,arr,controls[g.name],s.name,dt,probability,availability)
                ix['commitment'][g.name]=unit
                for ids in unit.values():op_indices.extend(ids)
        if industrial_sites:
            extra_op,extra_co2,constant_co2=industrial.add_constraints(m,industrial_sites,s,dt,ix,balances)
            op_indices.extend(extra_op);co2_row.update(extra_co2);fixed_co2+=constant_co2
        for l in lines:
            fw=[];rv=[];eff=1-l.loss_fraction
            for t in range(T):
                a=m.var(('flow_forward',s.name,l.name,t),probability*dt*l.flow_cost_per_mwh)
                b=m.var(('flow_reverse',s.name,l.name,t),probability*dt*l.flow_cost_per_mwh)
                fw.append(a);rv.append(b);op_indices.extend([a,b])
                balances[l.source,t][a]=-1;balances[l.target,t][a]=eff
                balances[l.target,t][b]=-1;balances[l.source,t][b]=eff
                m.upper({a:1,b:1,line_new[l.name]:-1},l.existing_mw)
            ix['line_forward'][l.name]=fw;ix['line_reverse'][l.name]=rv
        for b in storage:
            cs=[];ds=[];es=[]
            for t in range(T+1):
                e=m.var(('soc',s.name,b.name,t));es.append(e)
                m.upper({e:1,se_new[b.name]:-1},b.existing_energy_mwh)
            m.equal({es[0]:1,se_new[b.name]:-b.initial_soc_fraction},b.initial_soc_fraction*b.existing_energy_mwh,('initial_soc',s.name,b.name))
            m.equal({es[T]:1,es[0]:-1},0,('terminal_soc',s.name,b.name))
            for t in range(T):
                c=m.var(('charge',s.name,b.name,t),probability*dt*b.throughput_cost)
                d=m.var(('discharge',s.name,b.name,t),probability*dt*b.throughput_cost)
                cs.append(c);ds.append(d);op_indices.extend([c,d])
                m.upper({c:1,d:1,sp_new[b.name]:-1},b.existing_power_mw)
                balances[b.node,t][c]=-1;balances[b.node,t][d]=1
                m.equal({es[t+1]:1,es[t]:-1,c:-dt*b.charge_efficiency,d:dt/b.discharge_efficiency},0,('storage_transition',s.name,b.name,t))
            ix['charge'][b.name]=cs;ix['discharge'][b.name]=ds;ix['soc'][b.name]=es
        # Define every dam first so routed releases can reference another dam
        # regardless of input ordering. Water is never passed as copied energy.
        for h in reservoirs:
            av=h.availability.get(s.name,np.ones(T));gs=[];sp=[];vs=[]
            for t in range(T):
                g=m.var(('hydro_generation',s.name,h.name,t),probability*dt*h.marginal_cost,upper=float(h.turbine_mw*av[t]))
                v=m.var(('hydro_spill_hm3_per_hour',s.name,h.name,t),probability*dt*h.spillage_cost_per_hm3)
                gs.append(g);sp.append(v);op_indices.extend([g,v]);balances[h.node,t][g]=1
            for t in range(T+1):vs.append(m.var(('hydro_volume_hm3',s.name,h.name,t),upper=h.usable_volume_hm3))
            m.equal({vs[0]:1},h.initial_volume_hm3,('initial_reservoir',s.name,h.name))
            m.equal({vs[T]:1,vs[0]:-1},0,('terminal_reservoir',s.name,h.name))
            ix['hydro_generation'][h.name]=gs;ix['hydro_spillage_hm3_per_hour'][h.name]=sp;ix['hydro_volume_hm3'][h.name]=vs
        for h in reservoirs:
            upstream=[u for u in reservoirs if u.downstream==h.name]
            for t in range(T):
                vs=ix['hydro_volume_hm3'][h.name];g=ix['hydro_generation'][h.name][t];sp=ix['hydro_spillage_hm3_per_hour'][h.name][t]
                row={vs[t+1]:1,vs[t]:-1,g:dt*h.specific_water_m3_per_mwh/1e6,sp:dt}
                for u in upstream:
                    row[ix['hydro_generation'][u.name][t]]=-dt*u.specific_water_m3_per_mwh/1e6
                    row[ix['hydro_spillage_hm3_per_hour'][u.name][t]]=-dt
                m.equal(row,float(h.inflow_hm3_per_hour[s.name][t])*dt,('reservoir_water_balance',s.name,h.name,t))
        for p in pools:
            jobs=p.jobs[s.name];pool_capacity=[{} for t in range(T)];power_rows=[{} for t in range(T)]
            task_rows={j.name:{} for j in jobs};tasks=[]
            for j in jobs:
                for t in range(j.release,j.deadline):
                    for mode,(q,pw) in enumerate(zip(p.rates,p.mode_power_mw)):
                        c=probability*j.delay_cost_per_work_hour*(t-j.release)*dt*q*dt
                        v=m.var(('task',s.name,p.name,j.name,t,mode),c,upper=1.)
                        tasks.append((v,j.name,t,mode,q));service_indices.append(v)
                        pool_capacity[t][v]=1;power_rows[t][v]=pw-p.idle_power_mw
                        balances[p.node,t][v]=-(pw-p.idle_power_mw);task_rows[j.name][v]=q*dt
            fixed=None if fixed_compute is None else fixed_compute.get(s.name,{}).get(p.name)
            if fixed is not None:
                fixed=np.asarray(fixed,float)
                if fixed.shape!=(T,) or not np.isfinite(fixed).all():raise ValueError('Invalid fixed compute power')
            for t in range(T):
                rhs[p.node,t]+=p.idle_power_mw
                m.upper(pool_capacity[t],1.)
                if np.isfinite(p.connection_limit_mw):m.upper(power_rows[t],p.connection_limit_mw-p.idle_power_mw)
                if fixed is not None:m.equal(power_rows[t],fixed[t]-p.idle_power_mw,('fixed_compute',s.name,p.name,t))
            for j in jobs:m.equal(task_rows[j.name],j.work,('task_work',s.name,p.name,j.name))
            ix['compute'][p.name]=power_rows;ix['tasks'][p.name]=tasks
        for n in nodes:
            ix['balance_rows'][n]=[]
            for t in range(T):
                ix['balance_rows'][n].append(len(m.eq));m.equal(balances[n,t],rhs[n,t],('balance',s.name,n,t))
        result_indices[s.name]=ix
    m.upper(eens_row,expected_unserved_limit_mwh)
    if emissions_limit_t is not None:m.upper(co2_row,emissions_limit_t-fixed_co2)
    ae=m.sparse(m.eq);au=m.sparse(m.ub)
    if controls:
        lower=np.array([a for a,b in m.bounds]);upper=np.array([np.inf if b is None else b for a,b in m.bounds])
        constraints=LinearConstraint(vstack([ae,au]).tocsc(),np.r_[m.beq,np.full(len(m.bub),-np.inf)],np.r_[m.beq,m.bub])
        fit=milp(m.cost,integrality=m.integrality,bounds=Bounds(lower,upper),constraints=constraints,
                 options={'time_limit':milp_time_limit_s,'mip_rel_gap':0.})
    else:
        fit=linprog(m.cost,A_eq=ae,b_eq=m.beq,A_ub=au,b_ub=m.bub,bounds=m.bounds,method='highs')
    if not fit.success:return {'feasible':False if int(fit.status)==2 else None,'solver_status':int(fit.status),'message':fit.message,
                               'proven_infeasible':int(fit.status)==2,'accepted_optimal_solution':False,
                               'incumbent_available':getattr(fit,'x',None) is not None}
    if controls and np.max(np.abs(fit.x[np.array(m.integrality,dtype=bool)]-np.rint(fit.x[np.array(m.integrality,dtype=bool)])))>1e-6:raise RuntimeError('Nonintegral commitment solution')
    x=fit.x;eq_error=float(np.max(np.abs(ae@x-np.array(m.beq))))
    ub_error=float(np.max(np.maximum(au@x-np.array(m.bub),0)))
    if eq_error>1e-6 or ub_error>1e-6:raise RuntimeError(('Constraint residual',eq_error,ub_error))
    investment_ids=list(gen_new.values())+list(line_new.values())+list(sp_new.values())+list(se_new.values())
    cost=np.asarray(m.cost);investment=float(cost[investment_ids]@x[investment_ids]);service=float(cost[service_indices]@x[service_indices]);operating=float(cost[op_indices]@x[op_indices])
    penalty=float(sum(cost[v]*x[v] for v in eens_row))
    assert np.isclose(investment+service+operating+penalty,fit.fun,atol=1e-5)
    out={'feasible':True,'total_cost':float(fit.fun),'cost_components':{'investment':investment,'operating':operating,'service_delay':service,'unserved_penalty':penalty},
         'new_generator_mw':{k:float(x[v]) for k,v in gen_new.items()},'new_line_mw':{k:float(x[v]) for k,v in line_new.items()},
         'new_storage_power_mw':{k:float(x[v]) for k,v in sp_new.items()},'new_storage_energy_mwh':{k:float(x[v]) for k,v in se_new.items()},
         'expected_unserved_mwh':float(sum(v*x[i] for i,v in eens_row.items())),
         'expected_emissions_t':float(fixed_co2+sum(v*x[i] for i,v in co2_row.items())),
         'max_equality_residual':eq_error,'max_inequality_violation':ub_error,
         'solver_type':'MILP' if controls else 'LP','solver_status':int(fit.status),
         'mip_gap':float(fit.mip_gap) if controls else None,'mip_dual_bound':float(fit.mip_dual_bound) if controls else None,
         'variables':len(x),'equalities':ae.shape[0],'inequalities':au.shape[0], 'scenarios':{}}
    for s in scenarios:
        ix=result_indices[s.name];r={}
        r['external_fixed_load_mw']={n:np.zeros(T).tolist() if external_fixed_load is None else list(map(float,external_fixed_load[s.name][n])) for n in nodes}
        for key in ['generation','unserved','line_forward','line_reverse','charge','discharge','soc','hydro_generation','hydro_spillage_hm3_per_hour','hydro_volume_hm3']:
            r[key]={name:x[ids].tolist() for name,ids in ix[key].items()}
        r['compute_power_mw']={};r['completed_work']={};r['task_allocations']={}
        for p in pools:
            r['compute_power_mw'][p.name]=[float(p.idle_power_mw+sum(a*x[v] for v,a in row.items())) for row in ix['compute'][p.name]]
            r['completed_work'][p.name]={j.name:0. for j in p.jobs[s.name]};alloc=[]
            for v,name,t,mode,q in ix['tasks'][p.name]:
                r['completed_work'][p.name][name]+=float(x[v]*q*dt)
                if x[v]>1e-9:alloc.append({'batch':name,'slot':t,'mode':mode,'pool_fraction':float(x[v])})
            r['task_allocations'][p.name]=alloc
        r['unit_commitment']={name:{key:x[ids].tolist() for key,ids in unit.items()} for name,unit in ix['commitment'].items()}
        r['terminal_unit_state']={name:thermal.terminal_state(controls[name],r['generation'][name],unit['on']) for name,unit in r['unit_commitment'].items()}
        if industrial_sites:r['industrial_sites']=industrial.extract(industrial_sites,s,ix,x,dt)
        # MILP commitment changes are discrete: LP balance duals are not available.
        r['nodal_balance_marginal_cost']=None if controls else {n:(fit.eqlin.marginals[ids]/(s.probability*dt)).tolist() for n,ids in ix['balance_rows'].items()}
        r['simultaneous_storage_slots']={b.name:int(np.sum((x[ix['charge'][b.name]]>1e-7)&(x[ix['discharge'][b.name]]>1e-7))) for b in storage}
        out['scenarios'][s.name]=r
    return out
