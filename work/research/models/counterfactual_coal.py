"""Explicit coal-boundary diagnostics, not unit commitment or outage modelling."""
from dataclasses import replace
import numpy as np


def coal_boundary(generators,scenarios,province,policy,has_compute):
    if policy not in {'legacy','independent_reference','dispatch_relaxation'}:raise ValueError(policy)
    coal=next(g for g in generators if g.name=='coal' and g.node==province)
    before={s.name:float(np.asarray(coal.availability[s.name])[0]*coal.existing_mw) for s in scenarios}
    if policy=='legacy' or (policy=='independent_reference' and has_compute):
        return list(generators),dict(policy=policy,has_compute=has_compute,coal_upper_mw=before,
                                     minimum_output_fraction=coal.min_output_fraction)
    after={};availability={}
    for s in scenarios:
        T=len(s.load_mw[province])
        if policy=='dispatch_relaxation':capacity=coal.existing_mw
        else:
            residual=np.array(s.load_mw[province],float).copy()
            # The identical historical residual-load heuristic, excluding AI.
            for g in generators:
                if g.node==province and g.name in {'onwind','offwind','solar','hydro','nuclear'}:
                    profile=np.array(g.availability.get(s.name,np.ones(T)),float)
                    residual-=g.existing_mw*profile
            capacity=min(coal.existing_mw,max(0.,float(residual.max())/.85))
        after[s.name]=capacity
        availability[s.name]=np.full(T,capacity/coal.existing_mw if coal.existing_mw else 0.)
    minimum=0. if policy=='dispatch_relaxation' else coal.min_output_fraction
    replacement=replace(coal,availability=availability,min_output_fraction=minimum)
    result=[replacement if g.name==coal.name and g.node==province else g for g in generators]
    return result,dict(policy=policy,has_compute=has_compute,coal_upper_mw=after,
                       historical_coal_upper_mw=before,minimum_output_fraction=minimum,
                       evidence='residual-load reference correction' if policy=='independent_reference' else
                                'full existing coal available with zero minimum output; dispatch relaxation, not realistic commitment')
