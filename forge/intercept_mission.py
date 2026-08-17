r"""INTERCEPT MISSION — the coherent front door: a THREAT SPEC drives the whole pipeline.

You say "an interceptor for a 100 m/s target." This wires that spec straight through:
    threat speed  ->  engagement model  ->  the interception objective  ->  V1/V2 design search
                  ->  best airframe  ->  interception % vs the target  ->  the binding wall
No hand-set a_req/v_req thresholds - the mission IS "nullify this threat", and the physics answers.

It is explicit about SCOPE - what the pipeline optimizes for and what it deliberately does not model - so
the answer is never mistaken for more than it is.
"""
from __future__ import annotations

import math
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import diagnose
import engagement

random.seed(11)
FIXED = dict(C_rate=25, payload=0.6, wh_per_kg=300.0,
             focal_length_mm=38.0, pixel_pitch_um=3.0, n_pixels=1920, frame_rate_hz=60.0)

FOCUSES_ON = [
    "v_max, a_max, turn-rate (a_max/v_max), endurance, mass  <- V1 values + V2 rotor count",
    "the interception KINEMATICS vs the threat set (point-mass pursuit, proportional navigation)",
    "the seeker sensing radius (a hyperparameter here, 300 m) as the engagement start range",
]
IGNORES = [
    "threat EVASION (dumb targets only: fixed / straight-line; the smart-evader game is deferred)",
    "guidance/autopilot realism, control-loop stability, latency",
    "flight dynamics beyond point-mass; wind, gusts, aeroelasticity",
    "structures/thermal beyond total mass; cost, manufacturability",
    "TOPOLOGY change (the airframe stays a quad; it cannot invent a jet/rocket to go faster)",
]


def intercept_fraction_at(caps, speed, n_head=20, **kw):
    """Fraction of all-direction straight-line threats at this speed the design nullifies."""
    if caps["v_max"] <= 0:
        return 0.0
    hits = sum(engagement.simulate(caps, speed, float(h), **kw)[0]
               for h in np.linspace(0, 360, n_head, endpoint=False))
    return hits / n_head


def design_for_threat(threat_speed, base=None, pool=45, endurance_floor=12.0, mass_cap=4.5,
                      sensing_m=300.0, kill_m=5.0, border_m=600.0):
    kw = dict(sensing_m=sensing_m, kill_m=kill_m, border_m=border_m, t_max=25.0, dt=0.1)
    base = base or dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, L_arm=0.30,
                        n_rotors=4, **FIXED)
    base_caps = diagnose.caps_of(base)
    base_frac = intercept_fraction_at(base_caps, threat_speed, **kw)

    designs = []
    for _ in range(pool):
        cfg = {k: random.uniform(*diagnose.BOUNDS[k]) for k in diagnose.PARAMS}
        cfg["n_rotors"] = random.choice([3, 4, 6, 8]); cfg.update(FIXED)
        try:
            caps = diagnose.caps_of(cfg)
        except Exception:
            continue
        if caps["mass"] > mass_cap or caps["endurance_min"] < endurance_floor:
            continue
        designs.append((cfg, caps, intercept_fraction_at(caps, threat_speed, **kw)))
    if not designs:
        return dict(threat_speed=threat_speed, base=base_caps, base_frac=base_frac, best=None)
    cfg, caps, frac = max(designs, key=lambda d: d[2])
    return dict(threat_speed=threat_speed, base=base_caps, base_frac=base_frac,
                cfg=cfg, caps=caps, frac=frac, n=len(designs))


def wall(caps, threat_speed, frac):
    if caps["v_max"] < threat_speed:
        return (f"v_max ({caps['v_max']:.0f} m/s) < threat ({threat_speed:.0f} m/s): tail-chase is "
                f"impossible; only near head-on closes. This is a KINEMATIC / TOPOLOGY wall - a quad is the "
                f"wrong platform class to catch a {threat_speed:.0f} m/s target. Breaking it needs a faster "
                f"class (see v3_leashless: jet/rocket), which is realization, deliberately out of scope.")
    return "the airframe can out-run the threat; interception is limited by geometry/turn-rate, not v_max."


def report(threat_speed, **kw):
    r = design_for_threat(threat_speed, **kw)
    print("=" * 84)
    print(f"INTERCEPT MISSION  -  spec: an interceptor for a {threat_speed:.0f} m/s target")
    print("=" * 84)
    print("THE PIPELINE FOCUSES ON:")
    for s in FOCUSES_ON:
        print("   + " + s)
    print("IT DOES NOT MODEL (out of scope, by design):")
    for s in IGNORES:
        print("   - " + s)

    b = r["base"]
    print(f"\nbaseline quad: v_max {b['v_max']:.0f} | a_max {b['a_max_g']:.1f}g | endur {b['endurance_min']:.0f}min"
          f"  ->  intercepts {100*r['base_frac']:.0f}% of {threat_speed:.0f} m/s threats (all directions)")
    if not r.get("cfg"):
        print("no buildable design in the search met the endurance/mass constraints.")
        return r
    c = r["caps"]
    print(f"\nBEST design the physics found (searched {r['n']} buildable):")
    print(f"   {r['cfg']['n_rotors']} rotors, D {r['cfg']['D_in']:.1f}in, pitch {r['cfg']['pitch_in']:.1f}, "
          f"{r['cfg']['S']:.1f}S {r['cfg']['cap_mAh']:.0f}mAh")
    print(f"   v_max {c['v_max']:.0f} m/s | a_max {c['a_max_g']:.1f}g | endur {c['endurance_min']:.0f}min | "
          f"mass {c['mass']:.2f}kg")
    print(f"   ==> INTERCEPTS {100*r['frac']:.0f}% of {threat_speed:.0f} m/s targets (all directions)")
    print(f"\nBINDING WALL: {wall(c, threat_speed, r['frac'])}")
    return r


if __name__ == "__main__":
    speed = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0
    report(speed)
