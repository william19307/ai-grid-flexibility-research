"""Conservative capability-share bounds from per-cell cost brackets."""
import numpy as np
from scipy.optimize import linprog

def attribution(cells):
    c0,c10,c01,c11=[cells[k] for k in ['C00','C10','C01','C11']]
    total=c0-c11;mode=.5*(c0-c10+c01-c11);timing=total-mode
    return dict(total_saving=total,mode_shapley=mode,start_shapley=timing,
        interaction_saving=c10+c01-c0-c11,mode_share_pct=100*mode/total if total>1e-9 else None,
        mode_first=c0-c10,mode_last=c01-c11,start_first=c0-c01,start_last=c10-c11)

def optimal_share_bracket(lower,upper):
    """Charnes-Cooper LP over unknown global cell optima inside valid brackets.

Variables are (scaled C10, C01, C11, reciprocal total saving). Bounds also
impose nested capabilities. These intervals are not statistical uncertainty.
"""
    c0=upper['C00'];lo=np.array([lower[k] for k in ['C10','C01','C11']]);hi=np.array([upper[k] for k in ['C10','C01','C11']])
    if c0-hi[2]<=1e-8:return dict(lower_pct=None,upper_pct=None,reason='Constructed saving too small for stable share')
    aub=[];bub=[]
    for i in range(3):
        row=np.zeros(4);row[i]=1;row[3]=-hi[i];aub.append(row);bub.append(0.)
        row=np.zeros(4);row[i]=-1;row[3]=lo[i];aub.append(row);bub.append(0.)
    for i in [0,1]:
        row=np.zeros(4);row[2]=1;row[i]=-1;aub.append(row);bub.append(0.)
        row=np.zeros(4);row[i]=1;row[3]=-c0;aub.append(row);bub.append(0.)
    obj=np.array([-.5,.5,0,0]);eq=np.array([[0,0,-1,c0]])
    a=linprog(obj,A_ub=aub,b_ub=bub,A_eq=eq,b_eq=[1.],bounds=[(0,None)]*4,method='highs')
    b=linprog(-obj,A_ub=aub,b_ub=bub,A_eq=eq,b_eq=[1.],bounds=[(0,None)]*4,method='highs')
    if not a.success or not b.success:raise ValueError('Invalid cost brackets')
    return dict(lower_pct=max(0.,100*(.5+a.fun)),upper_pct=min(100.,100*(.5-b.fun)),
        reason='Certified interval for globally optimal capability allocation, conditional on cost bounds and this policy matrix; not a confidence interval')
