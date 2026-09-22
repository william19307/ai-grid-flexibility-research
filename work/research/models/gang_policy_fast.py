"""Equivalent interval-price search for sorted disjoint capacity blocks.

Batches price integrals and caches their primitive; preserves reference
within-block and across-block tie handling. No scheduling-policy change.
"""
from functools import lru_cache
import numpy as np
from gang_policy import best_interval as reference_best_interval

@lru_cache(maxsize=32)
def primitive(edges_bytes,prices_bytes):
    edges=np.frombuffer(edges_bytes,dtype=np.float64);prices=np.frombuffer(prices_bytes,dtype=np.float64)
    if len(edges)!=len(prices)+1 or np.any(np.diff(edges)<=0) or not np.isfinite(prices).all() or np.any(prices<0):raise ValueError('Invalid price series')
    return edges,np.r_[0.,np.cumsum(prices*np.diff(edges))]

def best_interval(blocks,duration,price_edges,prices,fixed_start=None):
    if not blocks:return None
    b=np.asarray(blocks,float)
    # Reference accepts arbitrary unions; this optimized path requires the
    # disjoint ordered blocks supplied by the reservation algorithm.
    if np.any(b[1:,0]<b[:-1,1]):return reference_best_interval(blocks,duration,price_edges,prices,fixed_start)
    pe=np.asarray(price_edges,dtype=np.float64);pr=np.asarray(prices,dtype=np.float64)
    xp,fp=primitive(pe.tobytes(),pr.tobytes())
    a=b[:,0];end=b[:,1];last=end-duration;valid=last>=a-1e-11
    a=a[valid];end=end[valid];last=last[valid]
    if not len(a):return None
    if fixed_start is not None:
        valid=(fixed_start>=a-1e-11)&(fixed_start<=last+1e-11)
        if not valid.any():return None
        starts=np.full(int(valid.sum()),fixed_start);ends=np.minimum(starts+duration,end[valid]);groups=np.arange(len(starts))
    else:
        seeds=np.r_[pe,pe-duration];group=np.searchsorted(a,seeds,side='right')-1
        keep=group>=0;seeds=seeds[keep];group=group[keep]
        keep=(seeds>a[group])&(seeds<last[group]);seeds=seeds[keep]
        starts=np.unique(np.r_[a,np.maximum(a,last),seeds]);groups=np.searchsorted(a,starts,side='right')-1
        ends=np.minimum(starts+duration,end[groups])
    if np.any(starts<xp[0]-1e-9) or np.any(ends>xp[-1]+1e-9):raise ValueError('Integral outside price domain')
    costs=np.interp(ends,xp,fp)-np.interp(starts,xp,fp)
    count=int(groups.max())+1;mins=np.full(count,np.inf);np.minimum.at(mins,groups,costs)
    take=np.flatnonzero(costs<=mins[groups]+1e-12);first=np.full(count,len(costs),dtype=int);np.minimum.at(first,groups[take],take)
    best=None
    for k in first:
        if k==len(costs):continue
        candidate=(float(costs[k]),float(starts[k]),float(ends[k]))
        if best is None or candidate[0]<best[0]-1e-12 or (abs(candidate[0]-best[0])<=1e-12 and candidate[1]<best[1]):best=candidate
    return best
