"""Fixed-capacity thermal-unit commitment constraints for the coupled grid model.

Input times are integer dispatch steps; ramps are MW/hour, transition limits MW.
Availability is an anticipated derating/outage schedule, not an unanticipated trip
model. Minimum-time obligations extending past the horizon are returned, not
claimed fulfilled. A subsequent horizon must inherit the reported terminal state.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class ThermalCommitment:
    generator: str
    min_up_steps: int = 1
    min_down_steps: int = 1
    startup_cost: float = 0.
    shutdown_cost: float = 0.
    no_load_cost_per_hour: float = 0.
    ramp_up_mw_per_hour: float = 1e9
    ramp_down_mw_per_hour: float = 1e9
    startup_limit_mw: float = 1e9
    shutdown_limit_mw: float = 1e9
    initial_on: bool = False
    initial_dispatch_mw: float = 0.
    initial_duration_steps: int = 1


def validate(control, generator):
    if generator.max_new_mw != 0:
        raise ValueError('Committable units require fixed installed capacity')
    if generator.existing_mw <= 0:
        raise ValueError('Committable capacity must be positive')
    for value in (control.min_up_steps, control.min_down_steps, control.initial_duration_steps):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError('Commitment durations must be positive integer steps')
    if not isinstance(control.initial_on, (bool, np.bool_)):
        raise ValueError('Initial commitment must be an explicit boolean')
    for value in (control.startup_cost, control.shutdown_cost, control.no_load_cost_per_hour,
                  control.ramp_up_mw_per_hour, control.ramp_down_mw_per_hour,
                  control.startup_limit_mw, control.shutdown_limit_mw, control.initial_dispatch_mw):
        if not np.isfinite(value) or value < 0:
            raise ValueError('Invalid commitment cost or power parameter')
    lower = generator.existing_mw * generator.min_output_fraction
    if control.initial_on:
        if not lower <= control.initial_dispatch_mw <= generator.existing_mw:
            raise ValueError('Initial dispatch outside online unit limits')
    elif control.initial_dispatch_mw != 0:
        raise ValueError('Offline unit cannot have positive initial dispatch')


def add_constraints(matrix, generator, power, control, scenario, dt, probability, availability):
    T = len(power)
    cap = generator.existing_mw
    ramp_up = min(dt * control.ramp_up_mw_per_hour, cap)
    ramp_down = min(dt * control.ramp_down_mw_per_hour, cap)
    startup_limit = min(control.startup_limit_mw, cap)
    shutdown_limit = min(control.shutdown_limit_mw, cap)
    on = [matrix.var(('unit_on', scenario, generator.name, t),
                     probability * dt * control.no_load_cost_per_hour,
                     upper=1, binary=True) for t in range(T)]
    start = [matrix.var(('unit_start', scenario, generator.name, t),
                        probability * control.startup_cost, upper=1, binary=True) for t in range(T)]
    stop = [matrix.var(('unit_stop', scenario, generator.name, t),
                       probability * control.shutdown_cost, upper=1, binary=True) for t in range(T)]
    required = control.min_up_steps if control.initial_on else control.min_down_steps
    remaining = max(0, required - control.initial_duration_steps)
    for t in range(T):
        transition = {on[t]: 1, start[t]: -1, stop[t]: 1}
        if t:
            transition[on[t - 1]] = -1
        matrix.equal(transition, int(control.initial_on) if t == 0 else 0,
                     ('unit_transition', scenario, generator.name, t))
        matrix.upper({start[t]: 1, stop[t]: 1}, 1)
        matrix.upper({power[t]: 1, on[t]: -generator.existing_mw * availability[t]}, 0)
        matrix.upper({power[t]: -1, on[t]: generator.existing_mw * generator.min_output_fraction}, 0)
        if availability[t] == 0:
            matrix.upper({on[t]: 1}, 0)
        if t < remaining:
            matrix.equal({on[t]: 1}, int(control.initial_on),
                         ('initial_unit_obligation', scenario, generator.name, t))
        up = {start[k]: 1 for k in range(max(0, t - control.min_up_steps + 1), t + 1)}
        up[on[t]] = -1
        matrix.upper(up, 0)
        down = {stop[k]: 1 for k in range(max(0, t - control.min_down_steps + 1), t + 1)}
        down[on[t]] = 1
        matrix.upper(down, 1)
        rise = {power[t]: 1, start[t]: -startup_limit}
        fall = {power[t]: -1, on[t]: -ramp_down,
                stop[t]: -shutdown_limit}
        if t:
            rise[power[t - 1]] = -1
            rise[on[t - 1]] = -ramp_up
            fall[power[t - 1]] = 1
        matrix.upper(rise, control.initial_dispatch_mw + ramp_up * int(control.initial_on) if t == 0 else 0)
        matrix.upper(fall, -control.initial_dispatch_mw if t == 0 else 0)
    return {'on': on, 'startup': start, 'shutdown': stop}


def terminal_state(control, dispatch, on):
    states = np.rint(on).astype(int)
    last = int(states[-1]); run = 0
    for value in states[::-1]:
        if value != last:
            break
        run += 1
    if run == len(states) and last == int(control.initial_on):
        run += control.initial_duration_steps
    minimum = control.min_up_steps if last else control.min_down_steps
    return dict(on=bool(last), dispatch_mw=float(dispatch[-1]), duration_steps=run,
                remaining_minimum_time_steps=max(0, minimum - run))
