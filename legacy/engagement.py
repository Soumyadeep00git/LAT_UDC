"""The world: one interceptor specimen versus one threat, point-mass, 2-D. Dynamics assumed fine.

A threat flies in a straight line toward the defended point (origin) at speed vT from range R0 and
bearing. The interceptor launches from the origin and homes with proportional navigation, capped by
its own lateral-accel authority a_max and top speed v_max. We integrate forward and report the
outcomes the MISSION cares about — not a pass/fail bit, but a vector:

    intercepted (bool), time (s), energy (J-ish), peak_power (W-ish), miss (m)

Energy/power are charged against the accel actually commanded, so agility is not free — that is what
creates the real multi-objective trade the optimizer must navigate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Outcome:
    intercepted: bool
    time: float
    energy: float
    peak_power: float
    miss: float


def simulate(spec, threat, dt: float = 0.02, t_max: float = 40.0, lethal: float = 3.0) -> Outcome:
    """spec: has v_max [m/s], a_max [m/s^2], mass [kg]. threat: vT, R0, bearing_rad, arrive_r.

    We do NOT stop at first contact; we integrate through the closest point of approach (CPA) so `miss`
    is the TRUE smallest distance achieved — that is the accuracy signal. intercepted = miss <= lethal.
    """
    tx = threat.R0 * math.cos(threat.bearing_rad)
    ty = threat.R0 * math.sin(threat.bearing_rad)
    ix, iy = 0.0, 0.0
    d0 = math.hypot(tx, ty) or 1.0
    ivx, ivy = spec.v_max * tx / d0, spec.v_max * ty / d0    # launch aimed at the threat

    energy, peak_power, t = 0.0, 0.0, 0.0
    best_miss = d0
    prev_rng = None
    TERMINAL = 40.0                                          # only look for CPA in the endgame
    steps = int(t_max / dt)
    for _ in range(steps):
        # THREAT motion: closes on the origin at vT, but WEAVES (evasive) — a lateral velocity
        # oscillation. Tracking the weave is what demands real lateral-accel authority and burns
        # energy; a weak specimen can't null the induced LOS rate and misses.
        d = math.hypot(tx, ty) or 1.0
        hx, hy = -tx / d, -ty / d                            # heading toward origin
        px, py = -hy, hx                                     # left-normal
        lat = threat.weave_amp * math.sin(2.0 * math.pi * t / threat.weave_period)
        tvx, tvy = threat.vT * hx + lat * px, threat.vT * hy + lat * py

        rx, ry = tx - ix, ty - iy
        rng = math.hypot(rx, ry)
        best_miss = min(best_miss, rng)
        # CPA: in the endgame, once the range starts growing again we have passed the target -> stop
        if prev_rng is not None and rng > prev_rng and prev_rng < TERMINAL:
            break
        prev_rng = rng
        if d < threat.arrive_r:                             # leaker reached the asset -> failed
            break

        vrx, vry = tvx - ivx, tvy - ivy
        los_rate = (rx * vry - ry * vrx) / (rng * rng + 1e-9)
        closing = -(rx * vrx + ry * vry) / (rng + 1e-9)
        a_cmd = 4.0 * max(closing, 0.0) * los_rate
        a_cmd = max(-spec.a_max, min(spec.a_max, a_cmd))
        isp = math.hypot(ivx, ivy) or 1.0
        nx, ny = -ivy / isp, ivx / isp
        ivx += a_cmd * nx * dt
        ivy += a_cmd * ny * dt
        isp = math.hypot(ivx, ivy) or 1.0
        ivx, ivy = ivx / isp * spec.v_max, ivy / isp * spec.v_max
        ix += ivx * dt
        iy += ivy * dt
        tx += tvx * dt
        ty += tvy * dt
        power = spec.mass * abs(a_cmd) * spec.v_max
        peak_power = max(peak_power, power)
        energy += power * dt
        t += dt
    return Outcome(best_miss <= lethal, t, energy, peak_power, best_miss)
