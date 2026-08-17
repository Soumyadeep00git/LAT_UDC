r"""INTERCEPT-OPTIMIZE — the physics optimizer maximizing INTERCEPTION (the engagement metric).

(Distinct from codesign.py, the older subsystem coordinate-descent. This optimizes the MISSION objective.)

The loop the whole pipeline was building toward:

    search DESIGN  ->  physics (caps_of)  ->  caps (v_max, a_max)  ->  engagement  ->  interception %
         ^-------------------------------  maximize interception  --------------------------|

Interception (at 300 m sensing) is kinematics-bound, so it WANTS high v_max / a_max - but those cost mass
and endurance. So the honest objective is: MAXIMIZE interception SUBJECT TO endurance >= a floor. We trace
that trade (the co-design frontier): the best design, and its interception, at each endurance floor.

Dumb targets (scenarios 1 & 2). Outer = this design search; inner = the engagement eval. The smart-evader
game (scenario 3) is the deferred inner policy optimizer - it slots into the same interface.
"""
from __future__ import annotations

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import diagnose
import engagement

random.seed(7)

FIXED = dict(C_rate=25, payload=0.6, wh_per_kg=300.0,
             focal_length_mm=38.0, pixel_pitch_um=3.0, n_pixels=1920, frame_rate_hz=60.0)
# ONE sweep for search AND reporting (consistency); the % is relative to this threat-speed distribution.
SWEEP = dict(scenario="straight_line", n_speed=9, n_head=16, t_max=20.0, dt=0.10)
MASS_CAP = 4.5     # buildability - forces the interception-vs-endurance trade to be real


def _sample():
    cfg = {k: random.uniform(*diagnose.BOUNDS[k]) for k in diagnose.PARAMS}
    cfg["n_rotors"] = random.choice([3, 4, 6, 8])
    cfg.update(FIXED)
    return cfg


def evaluate(cfg):
    caps = diagnose.caps_of(cfg)                              # physics: design -> capabilities
    frac, _ = engagement.max_interception(caps, **SWEEP)     # engagement: caps -> interception
    return caps, frac


def search(pool=60):
    designs = []
    for _ in range(pool):
        cfg = _sample()
        try:
            caps, frac = evaluate(cfg)
        except Exception:
            continue
        designs.append({"cfg": cfg, "caps": caps, "intercept": frac})
    return designs


if __name__ == "__main__":
    base = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, L_arm=0.30, n_rotors=4, **FIXED)
    base_caps, base_frac = evaluate(base)

    print("=" * 84)
    print("INTERCEPT-OPTIMIZE  -  physics optimizer MAXIMIZING interception (dumb targets, 300 m sensing)")
    print("=" * 84)
    print(f"baseline: v_max {base_caps['v_max']:.1f} | a_max {base_caps['a_max_g']:.1f}g | "
          f"endur {base_caps['endurance_min']:.0f}min | intercept {100*base_frac:.0f}%")

    designs = [d for d in search(pool=60) if d["caps"]["mass"] <= MASS_CAP]     # buildable only
    print(f"\nsearched designs (buildable, mass<={MASS_CAP}kg): {len(designs)}")
    print(f"INTERCEPTION-vs-ENDURANCE frontier (max intercept @ each endurance floor; same sweep as search):")
    print(f"   {'endur floor':>11} | {'intercept':>9} | best design (v_max, a_max, endur, mass, N)")
    best_overall = None
    for floor in (10, 16, 22, 28, 34):
        feas = [d for d in designs if d["caps"]["endurance_min"] >= floor]
        if not feas:
            print(f"   {floor:>9}min | {'--':>9} | (none buildable)")
            continue
        b = max(feas, key=lambda d: d["intercept"])
        c = b["caps"]
        print(f"   {floor:>9}min | {100*b['intercept']:>8.0f}% | v_max {c['v_max']:.1f} m/s, a_max {c['a_max_g']:.1f}g, "
              f"endur {c['endurance_min']:.0f}min, mass {c['mass']:.2f}kg, {b['cfg']['n_rotors']} rotors")
        if best_overall is None or b["intercept"] > best_overall["intercept"]:
            best_overall = b

    bc = best_overall["caps"]
    print(f"\nBEST for interception (buildable): v_max {bc['v_max']:.1f} m/s, a_max {bc['a_max_g']:.1f}g, "
          f"endur {bc['endurance_min']:.0f}min, mass {bc['mass']:.2f}kg")
    print(f"   interception {100*best_overall['intercept']:.0f}%  vs baseline {100*base_frac:.0f}%  "
          f"(baseline v_max {base_caps['v_max']:.1f})  [same sweep, apples-to-apples]")

    print("\n" + "-" * 84)
    print("The physics now optimizes the MISSION, not thresholds: it drives v_max/a_max up (that is what")
    print("catches more threats) against the mass cap and endurance floor. Interception is the objective;")
    print("the frontier is the honest trade the physics permits. (% is relative to the assumed threat set.)")
    print("Smart evaders would swap the inner engagement eval for the deferred game solver.")
