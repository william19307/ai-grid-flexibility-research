"""Exact interval integration; arrivals/exits at boundaries are not rounded."""
import numpy as np


def integrate_occupancy(starts,ends,resources,edges):
    starts=np.asarray(starts,float);ends=np.asarray(ends,float);resources=np.asarray(resources,float);edges=np.asarray(edges,float)
    if not (starts.shape==ends.shape==resources.shape) or starts.ndim!=1:raise ValueError('Interval dimensions')
    if len(edges)<2 or np.any(np.diff(edges)<=0) or not all(np.isfinite(x).all() for x in [starts,ends,resources,edges]):raise ValueError('Invalid time data')
    if np.any(ends<starts) or np.any(resources<0):raise ValueError('Invalid intervals/resources')
    left=np.maximum(starts,edges[0]);right=np.minimum(ends,edges[-1]);valid=right>left
    left=left[valid];right=right[valid];w=resources[valid]
    events=np.r_[left,right,edges];deltas=np.r_[w,-w,np.zeros(len(edges))]
    times,inv=np.unique(events,return_inverse=True)
    change=np.bincount(inv,weights=deltas,minlength=len(times));occupancy=np.cumsum(change)
    durations=np.diff(times);mass=occupancy[:-1]*durations
    bins=np.searchsorted(edges,times[:-1],side='right')-1
    amount=np.bincount(bins,weights=mass,minlength=len(edges)-1)
    peak=np.zeros(len(edges)-1);np.maximum.at(peak,bins,occupancy[:-1])
    expected=float(np.dot(right-left,w))
    if not np.isclose(amount.sum(),expected,atol=1e-5,rtol=1e-10):raise AssertionError('Occupancy integral mismatch')
    if np.min(occupancy)<-1e-8:raise AssertionError('Negative occupancy')
    return dict(resource_seconds=amount,mean_resources=amount/np.diff(edges),peak_resources=peak,
                total_resource_seconds=expected,conservation_error=float(abs(amount.sum()-expected)),
                carry_in_intervals=int(np.sum((starts<edges[0])&(ends>edges[0]))),
                carry_out_intervals=int(np.sum((starts<edges[-1])&(ends>edges[-1]))))
