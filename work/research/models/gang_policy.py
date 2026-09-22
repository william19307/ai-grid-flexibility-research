"""Price-based gang policy factorial with fixed or flexible starts.

All cells share perfect retrospective information. This is feasible coordinate
improvement, not globally optimal scheduling. Each single-job price minimization
is exact for its current contiguous capacity blocks and piecewise-constant price.
"""
import numpy as np


def price_integral(t,edges,prices):
    edges=np.asarray(edges,float);prices=np.asarray(prices,float);t=np.asarray(t,float)
    if edges.ndim!=1 or prices.shape!=(len(edges)-1,) or np.any(np.diff(edges)<=0) or not np.isfinite(prices).all() or np.any(prices<0):raise ValueError('Invalid price series')
    if np.any(t<edges[0]-1e-9) or np.any(t>edges[-1]+1e-9):raise ValueError('Integral outside price domain')
    return np.interp(t,edges,np.r_[0.,np.cumsum(prices*np.diff(edges))])


def best_interval(blocks,duration,price_edges,prices,fixed_start=None):
    """Return exact least-price continuous interval inside a union of blocks.

For F(s+d)-F(s), slopes change at price edges or price edges minus d.
Together with block endpoints these exhaust candidate minima. Earliest tie wins.
"""
    pe=np.asarray(price_edges,float);best=None
    for a,b in blocks:
        last=b-duration
        if last<a-1e-11:continue
        if fixed_start is not None:
            if fixed_start<a-1e-11 or fixed_start>last+1e-11:continue
            candidates=np.array([fixed_start])
        else:
            candidates=np.unique(np.r_[a,max(a,last),pe[(pe>a)&(pe<last)],(pe-duration)[(pe-duration>a)&(pe-duration<last)]])
        ends=np.minimum(candidates+duration,b)
        costs=price_integral(ends,pe,prices)-price_integral(candidates,pe,prices)
        minimum=float(costs.min());indices=np.flatnonzero(costs<=minimum+1e-12)
        k=int(indices[0]);proposal=(float(costs[k]),float(candidates[k]),float(ends[k]))
        if best is None or proposal[0]<best[0]-1e-12 or (abs(proposal[0]-best[0])<=1e-12 and proposal[1]<best[1]):best=proposal
    return best


def independent_job_bound(release,deadline,work,gpus,original_start,rates,power,price_edges,prices,allow_modes,allow_start):
    """Exact non-preemptive per-job optimum ignoring all resource competition."""
    q=np.asarray(rates);p=np.asarray(power);allowed=np.arange(len(q)) if allow_modes else np.flatnonzero(q==1.)
    costs=[]
    for r,d,w,g,s in zip(release,deadline,work,gpus,original_start):
        values=[]
        for m in allowed:
            result=best_interval([(r,d)],w/g/q[m],price_edges,prices,None if allow_start else s)
            if result is not None:values.append(g*p[m]*result[0])
        if not values:raise ValueError('Individual window infeasible')
        costs.append(min(values))
    return np.asarray(costs)


def schedule_cost(plan,gpus,power,price_edges,prices):
    plan=np.asarray(plan,float);m=plan[:,2].astype(int)
    return float(np.sum(np.asarray(gpus)*np.asarray(power)[m]*(price_integral(plan[:,1],price_edges,prices)-price_integral(plan[:,0],price_edges,prices))))


def coordinate_policy(release,deadline,work,gpus,original_start,initial_plan,edges,free_capacity,rates,power,price_edges,prices,allow_modes,allow_start):
    """One fixed-order sweep, keeping other jobs' complete reservations.

free_capacity describes unused resources with initial_plan already reserved.
Only strict cost improvements are accepted. Original starts are immutable in
fixed-start arms; durations may change when mode changes.
"""
    release=np.asarray(release,float);deadline=np.asarray(deadline,float);work=np.asarray(work,float);gpus=np.asarray(gpus,float)
    original_start=np.asarray(original_start,float);q=np.asarray(rates,float);p=np.asarray(power,float)
    plan=np.asarray(initial_plan,float).copy();edges=np.asarray(edges,float).copy();free=np.asarray(free_capacity,float).copy()
    if plan.shape!=(len(work),3) or len(free)!=len(edges)-1 or np.min(free)<-1e-7:raise ValueError('Invalid initial plan or capacity')
    if not np.isfinite(q).all() or not np.isfinite(p).all() or np.any(q<=0) or np.any(p<0) or not np.any(q==1.):raise ValueError('Invalid modes')
    modes=plan[:,2].astype(int)
    if np.any(modes<0) or np.any(modes>=len(q)) or not np.array_equal(modes,plan[:,2]):raise ValueError('Invalid initial modes')
    if np.max(abs((plan[:,1]-plan[:,0])*gpus*q[modes]-work))>1e-7:raise ValueError('Initial work mismatch')
    if np.any(plan[:,0]<release-1e-9) or np.any(plan[:,1]>deadline+1e-9):raise ValueError('Invalid service')
    if not allow_modes and np.any(q[modes]!=1.):raise ValueError('Non-full-speed seed in fixed-mode arm')
    if not allow_start and np.max(abs(plan[:,0]-original_start))>1e-9:raise ValueError('Shifted seed in fixed-start arm')
    def split(t):
        nonlocal edges,free
        i=int(np.searchsorted(edges,t))
        if i<len(edges) and abs(edges[i]-t)<1e-12:return i
        if i>0 and abs(edges[i-1]-t)<1e-12:return i-1
        if i==0 or i==len(edges):raise ValueError('Event outside domain')
        edges=np.insert(edges,i,t);free=np.insert(free,i,free[i-1]);return i
    def change(a,b,amount):
        l=split(a);r=split(b);free[l:r]+=amount
    allowed=np.arange(len(q)) if allow_modes else np.flatnonzero(q==1.)
    initial_cost=schedule_cost(plan,gpus,p,price_edges,prices);improved=0
    for i in sorted(range(len(work)),key=lambda j:(original_start[j],j)):
        a,b,m0=plan[i];m0=int(m0);change(a,b,gpus[i])
        l=max(0,int(np.searchsorted(edges,release[i],side='right')-1));r=min(len(free),int(np.searchsorted(edges,deadline[i],side='left')))
        good=free[l:r]>=gpus[i]-1e-8;flips=np.flatnonzero(np.diff(np.r_[False,good,False].astype(int)))
        blocks=[(max(release[i],edges[l+x]),min(deadline[i],edges[l+y])) for x,y in zip(flips[::2],flips[1::2])]
        oldcost=gpus[i]*p[m0]*float(price_integral(b,price_edges,prices)-price_integral(a,price_edges,prices))
        best=(oldcost,a,b,m0)
        for m in allowed:
            choice=best_interval(blocks,work[i]/gpus[i]/q[m],price_edges,prices,None if allow_start else original_start[i])
            if choice is None:continue
            cost=gpus[i]*p[m]*choice[0]
            if cost<best[0]-1e-10:best=(cost,choice[1],choice[2],int(m))
        _,a,b,m=best;l=split(a);r=split(b);a=float(edges[l]);b=float(edges[r]);free[l:r]-=gpus[i];plan[i]=[a,b,m]
        if best[0]<oldcost-1e-10:improved+=1
        if np.min(free)<-1e-7:raise AssertionError('Capacity exceeded')
    cost=schedule_cost(plan,gpus,p,price_edges,prices)
    if cost>initial_cost+1e-6:raise AssertionError('Improvement increased bill')
    return dict(plan=plan,incremental_bill=cost,initial_bill=initial_cost,changed_jobs=improved,edges=edges,free_capacity=free)
