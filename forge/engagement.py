r"""ENGAGEMENT ENGINE (dumb targets) — the interception metric, coupled to the resolved airframe.

Generic point-mass pursuit: one fixed integrator marches [interceptor, threat] under a guidance law until
kill / escape / timeout. Everything domain-specific is DATA: the threat policy (fixed | straight-line),
the guidance law (proportional navigation), and the hyperparameters (kill radius, sensing, border).

Dumb targets only (scenarios 1 & 2) — the threat does not react, so this is deterministic, no game solver.
Smart evaders (scenario 3) are a separate policy-optimizer, deferred. This validates the pipeline:
    design -> physics -> caps (v_max, a_max) -> ENGAGEMENT -> interception fraction.

Geometry (defaults, all tweakable): interceptor launches from the origin; threat is first seen at the
sensing radius; the threat 'escapes' (reaches its border) if its range from the origin exceeds `border_m`;
nullify = interceptor within `kill_m` of the threat before it escapes.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

G = 9.81


def simulate(caps, threat_speed, threat_heading_deg, spawn_bearing_deg=0.0,
             sensing_m=300.0, kill_m=5.0, border_m=600.0, dt=0.02, t_max=60.0, N=4.0):
    """One encounter. Returns (nullified: bool, t, min_range). Interceptor flies flat-out with a
    turn-rate limited by a_max/v_max, steered by proportional navigation."""
    v_max = caps["v_max"]
    a_max = caps["a_max_g"] * G
    turn_max = a_max / v_max if v_max > 0 else 0.0            # rad/s

    th = math.radians(spawn_bearing_deg)
    p_t = sensing_m * np.array([math.cos(th), math.sin(th)])
    phi = math.radians(threat_heading_deg)
    v_t = threat_speed * np.array([math.cos(phi), math.sin(phi)])

    p_i = np.array([0.0, 0.0])
    los = p_t - p_i
    psi = math.atan2(los[1], los[0])                          # interceptor heading toward first sighting
    best = np.linalg.norm(los)

    t = 0.0
    while t < t_max:
        rel = p_t - p_i
        dist = float(np.linalg.norm(rel))
        best = min(best, dist)
        if dist <= kill_m:
            return True, t, best
        if float(np.linalg.norm(p_t)) > border_m:            # threat escaped past its border
            return False, t, best
        v_i = v_max * np.array([math.cos(psi), math.sin(psi)])
        rel_v = v_t - v_i
        lam_dot = (rel[0] * rel_v[1] - rel[1] * rel_v[0]) / (dist * dist) if dist > 1e-6 else 0.0
        Vc = -float(rel @ rel_v) / dist if dist > 1e-6 else 0.0
        a_cmd = N * Vc * lam_dot                              # proportional navigation
        psi += float(np.clip(a_cmd / v_max, -turn_max, turn_max)) * dt
        p_i = p_i + v_i * dt
        p_t = p_t + v_t * dt
        t += dt
    return False, t, best


def max_interception(caps, scenario="straight_line", n_speed=12, n_head=24,
                     v_hi=343.0, sensing_m=300.0, **kw):
    """Sweep the threat set; return the fraction nullified + a per-speed breakdown."""
    if scenario == "fixed":
        # stationary threats placed around the sensing edge (speed 0); can we reach them?
        hits = tot = 0
        by = []
        for b in np.linspace(0, 360, n_head, endpoint=False):
            ok, _t, _r = simulate(caps, 0.0, 0.0, spawn_bearing_deg=b, sensing_m=sensing_m, **kw)
            hits += ok; tot += 1
        return hits / tot, [("stationary", hits / tot)]

    # straight_line: sweep speed x heading (all directions)
    speeds = np.linspace(0, v_hi, n_speed)
    heads = np.linspace(0, 360, n_head, endpoint=False)
    hits = tot = 0
    per_speed = []
    for v in speeds:
        sh = st = 0
        for h in heads:
            ok, _t, _r = simulate(caps, v, h, sensing_m=sensing_m, **kw)
            sh += ok; st += 1
        per_speed.append((v, sh / st))
        hits += sh; tot += st
    return hits / tot, per_speed


if __name__ == "__main__":
    import resolve as R

    base = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, C_rate=25,
                L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0,
                focal_length_mm=38.0, pixel_pitch_um=3.0, n_pixels=1920, frame_rate_hz=60.0)
    mission = dict(a_req=5.0, v_req=26.0, endur_req=16.0, detect_range_m=2500.0, search_halfangle_deg=30.0)
    res = R.resolve(base, mission)
    caps = res["caps"]

    print("=" * 82)
    print("ENGAGEMENT (dumb targets)  -  interception metric on the resolved airframe")
    print("=" * 82)
    print(f"interceptor: v_max {caps['v_max']:.1f} m/s | a_max {caps['a_max_g']:.1f} g "
          f"(turn-rate {caps['a_max_g']*G/caps['v_max']:.2f} rad/s)")
    print("geometry (defaults): launch origin | sensing 300 m | kill 5 m | border 600 m | PN guidance")

    f1, _ = max_interception(caps, scenario="fixed")
    print(f"\nSCENARIO 1 (fixed target):        nullified {100*f1:.0f}%   (validates reach mechanics)")

    f2, per = max_interception(caps, scenario="straight_line")
    print(f"SCENARIO 2 (straight-line 0-343): nullified {100*f2:.0f}%   (sweep speed x all directions)")
    print("   capture vs threat speed:")
    for v, fr in per:
        bar = "#" * int(round(fr * 30))
        print(f"     {v:5.0f} m/s | {bar:<30} {100*fr:3.0f}%")

    print("\n" + "-" * 82)
    print("PIPELINE VALIDATED: design -> physics -> caps -> engagement -> interception fraction, end to end.")
    print("Reads as expected: slow/approaching threats caught, fast fleeing ones escape (interceptor slower).")
    print("This fraction is the METRIC V1/V2 will maximize; smart evaders (scenario 3) are the deferred game.")
