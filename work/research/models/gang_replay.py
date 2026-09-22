"""Construct a non-preemptive fixed-size gang schedule from a feasible baseline.

All unprocessed tasks remain reserved at their observed times. Releasing one
reservation and replacing it with a feasible whole-gang interval preserves
aggregate GPU-capacity feasibility inductively. Node locality is not modelled.
"""
import numpy as np


def individual_energy_bound(work,gpus,window,rates,power):
    points=sorted([(0.,0.)]+[(float(q),float(p)) for q,p in zip(rates,power)])
    unique={}
    for q,p in points:unique[q]=min(p,unique.get(q,float('inf')))
    hull=[]
    for q,p in sorted(unique.items()):
        while len(hull)>1:
            a,b=hull[-2:]
            if (b[1]-a[1])*(q-b[0]) >= (p-b[1])*(b[0]-a[0])-1e-14:hull.pop()
            else:break
        hull.append((q,p))
    rho=np.asarray(work)/np.asarray(gpus)/np.asarray(window)
    if np.any(rho>hull[-1][0]+1e-9):raise ValueError('Individual deadline infeasible')
    lower=np.asarray(gpus)*np.asarray(window)*np.interp(rho,[x[0] for x in hull],[x[1] for x in hull])
    return lower


def schedule_gangs(release,deadline,original_start,original_end,gpus,edges,free_capacity,rates,power):
    release=np.asarray(release,float);deadline=np.asarray(deadline,float);begin=np.asarray(original_start,float);finish=np.asarray(original_end,float)
    gpus=np.asarray(gpus,float);q=np.asarray(rates,float);p=np.asarray(power,float)
    edges=np.asarray(edges,float).copy();free=np.asarray(free_capacity,float).copy()
    if free.shape!=(len(edges)-1,) or np.min(free)<-1e-7 or np.any(np.diff(edges)<=0):raise ValueError('Invalid baseline capacity')
    if np.any(begin<release-1e-9) or np.any(finish>deadline+1e-9) or np.any(finish<=begin):raise ValueError('Baseline service invalid')
    if len(q)!=len(p) or np.any(q<=0) or np.any(p<0) or not np.any(q==1.):raise ValueError('Modes require full-speed reference')
    def split(t):
        nonlocal edges,free
        i=int(np.searchsorted(edges,t))
        if i<len(edges) and abs(edges[i]-t)<1e-12:return i
        if i>0 and abs(edges[i-1]-t)<1e-12:return i-1
        if i==0 or i==len(edges):raise ValueError('Event outside replay domain')
        edges=np.insert(edges,i,t);free=np.insert(free,i,free[i-1]);return i
    def change(a,b,amount):
        left=split(a);right=split(b);free[left:right]+=amount
    chosen=[];order=sorted(range(len(begin)),key=lambda i:(begin[i],i));rank=np.argsort(p/q,kind='stable')
    for i in order:
        change(begin[i],finish[i],gpus[i])
        placed=None
        for m in rank:
            duration=(finish[i]-begin[i])/q[m]
            if duration>deadline[i]-release[i]+1e-9:continue
            left=max(0,int(np.searchsorted(edges,release[i],side='right')-1));right=min(len(free),int(np.searchsorted(edges,deadline[i],side='left')))
            good=free[left:right]>=gpus[i]-1e-8
            flips=np.flatnonzero(np.diff(np.r_[False,good,False].astype(int)))
            for a,b in zip(flips[::2],flips[1::2]):
                start=max(release[i],edges[left+a]);stop=min(deadline[i],edges[left+b])
                if stop-start+1e-12>=duration:
                    placed=(start,min(stop,start+duration),int(m));break
            if placed is not None:break
        if placed is None:raise AssertionError('Original reservation must remain a feasible fallback')
        start,stop,m=placed;left=split(start);right=split(stop)
        start=float(edges[left]);stop=float(edges[right]);free[left:right]-=gpus[i]
        if np.min(free)<-1e-7:raise AssertionError('Gang exceeds aggregate capacity')
        chosen.append((i,float(start),float(stop),m))
    chosen.sort();work=gpus*(finish-begin)
    actual=sum(gpus[i]*(stop-start)*p[m] for i,start,stop,m in chosen)
    lower=float(individual_energy_bound(work,gpus,deadline-release,q,p).sum())
    if actual<lower-1e-6:raise AssertionError('Constructed cost below relaxation bound')
    return dict(schedule=chosen,incremental_energy=float(actual),individual_lower_bound=lower,
                max_capacity_excess_gpus=max(0.,float(-free.min())),
                scope='Non-preemptive, fixed-size gangs in one aggregate GPU pool; node placement and quality effects unverified')
