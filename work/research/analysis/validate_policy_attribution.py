"""Fractional LP bounds checked by independent polytope vertex enumeration."""
from pathlib import Path
import sys,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/models'));sys.path.insert(0,str(ROOT/'work/research/analysis'))
from policy_attribution import attribution,optimal_share_bracket
from verify_gang_policy_revision import share_vertices
rng=np.random.default_rng(79013);checks=0
for _ in range(100):
    c0=float(rng.uniform(5,100));c11=float(rng.uniform(.1,.7)*c0)
    upper=dict(C00=c0,C10=float(rng.uniform(c11,c0)),C01=float(rng.uniform(c11,c0)),C11=c11)
    lower={k:(v if k=='C00' else v*float(rng.uniform(.05,.95))) for k,v in upper.items()}
    expected=share_vertices(lower,upper);actual=optimal_share_bracket(lower,upper)
    assert np.allclose(expected,[actual['lower_pct'],actual['upper_pct']],atol=1e-6)
    d=attribution(upper);assert abs(d['mode_shapley']+d['start_shapley']-d['total_saving'])<1e-9
    # A constructed-policy share is not necessarily inside the interval for
    # globally optimal cell shares; never assert that distinct objects coincide.
    checks+=1
    lower['C10']=upper['C10']=c0
    actual=optimal_share_bracket(lower,upper);assert actual['upper_pct']<=50+1e-6;checks+=1
# No pure-mode or pure-start saving: all gain is interaction, split equally.
upper=dict(C00=10.,C10=10.,C01=10.,C11=7.);lower=dict(C00=10.,C10=10.,C01=10.,C11=3.)
a=optimal_share_bracket(lower,upper);assert abs(a['lower_pct']-50)<1e-8 and abs(a['upper_pct']-50)<1e-8;checks+=1
report=dict(checks=checks,random_fractional_lp_vs_vertex_oracles=100,zero_allowance_mode_share_upper_limit_oracles=100,pure_interaction_share_oracle=True)
out=ROOT/'outputs/research/revision/policy/validation';out.mkdir(exist_ok=True);(out/'attribution_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
