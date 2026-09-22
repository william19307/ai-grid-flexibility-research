"""Component-consistent sensitivity family, NOT measured node calibration.

All powers are normalized to full-workload node active power (not nameplate TDP).
GPU idle g and non-GPU active-minus-idle overhead d are explicit assumptions.
For node idle I, GPU active share a=(1-I-d)/(1-g). Thus non-GPU
active=1-a, non-GPU idle=1-a-d, node mode=1-a+a*GPU_mode_ratio.
"""
import numpy as np


def map_gpu_to_node(gpu_power_ratios,node_idle,gpu_idle_ratio,non_gpu_active_overhead=0.):
    r=np.asarray(gpu_power_ratios,float)
    I,g,d=map(float,[node_idle,gpu_idle_ratio,non_gpu_active_overhead])
    if r.ndim!=1 or not len(r) or not np.isfinite(r).all() or (r<=0).any():
        raise ValueError('GPU mode powers must be finite and positive')
    if not all(np.isfinite(x) for x in [I,g,d]) or not 0<=g<1 or not 0<=I<1 or d<0:
        raise ValueError('Invalid component assumptions')
    a=(1-I-d)/(1-g);active=1-a;idle=active-d
    if a<=0 or a>1 or idle<-1e-12 or np.min(r)<g:
        raise ValueError('Inconsistent node/GPU power boundary')
    p=active+a*r
    if np.min(p)<I-1e-12:raise ValueError('Active mode below node idle')
    return p,dict(node_idle_ratio=I,gpu_idle_ratio=g,non_gpu_active_overhead=d,
                  gpu_share_of_full_node_power=a,non_gpu_active_share=active,
                  non_gpu_idle_share=idle,
                  evidence='component-consistent sensitivity, not calibrated measurements')
