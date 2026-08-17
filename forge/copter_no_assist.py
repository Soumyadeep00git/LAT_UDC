r"""COPTER, NO ASSIST — honor the USER's inputs, remove CLAUDE's thinking-assists. See what the tool does alone.

HONORED (the user's inputs, untouched):
  - the 7-part quadcopter hardware
  - the intent: an interceptor for a threat at THREAT_SPEED m/s
  - the user's hyperparameters: sensing radius, kill radius

REMOVED (assists I - Claude - had injected and dressed up as the tool reasoning):
  - the invented seeker requirement (the 2500 m detection, the 60-deg search cone) -> I made those up
  - v3c's hand-encoded trade-invariants (etendue / Ragone / pitch) -> I chose what dimensions to look for
  - the pre-loaded conclusions ("missing dimension = a scan DOF", "needs a jet/rocket") -> my interpretation
  - my interpretive verdict prose

So this run uses ONLY the mechanical operators - resolve capabilities, V1/V2 optimize, run the kinematic
engagement - and then STOPS wherever thinking (not computation) was required. The point is to see the honest
line between what the tool computes and what was me.
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

random.seed(3)

# --- USER INPUTS (honored) ---
HARDWARE = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, C_rate=25,
                L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0,
                focal_length_mm=38.0, pixel_pitch_um=3.0, n_pixels=1920, frame_rate_hz=60.0)
THREAT_SPEED = 100.0          # user's spec: intercept a 100 m/s target
SENSING_M = 300.0             # user's hyperparameter
KILL_M = 5.0                  # user's hyperparameter
FIXED = {k: HARDWARE[k] for k in ("C_rate", "payload", "wh_per_kg",
                                  "focal_length_mm", "pixel_pitch_um", "n_pixels", "frame_rate_hz")}


def intercept_frac(caps, speed, n_head=20):
    if caps["v_max"] <= 0:
        return 0.0
    kw = dict(sensing_m=SENSING_M, kill_m=KILL_M, border_m=2 * SENSING_M, t_max=25.0, dt=0.1)
    return sum(engagement.simulate(caps, speed, float(h), **kw)[0]
               for h in np.linspace(0, 360, n_head, endpoint=False)) / n_head


def main():
    print("=" * 84)
    print(f"COPTER, NO ASSIST  -  user's inputs honored, Claude's thinking-assists removed")
    print("=" * 84)
    print(f"HONORED (yours): 7-part quad | intercept a {THREAT_SPEED:.0f} m/s target | sensing {SENSING_M:.0f} m "
          f"| kill {KILL_M:.0f} m")
    print("REMOVED (mine):  the invented 60-deg cone / 2500 m detection, v3c's hand-encoded invariants,")
    print("                 the pre-loaded 'missing dimension' answers, and my verdict prose.")

    # --- purely mechanical: resolve + optimize the airframe for the user's objective, run the engagement ---
    base = diagnose.caps_of(HARDWARE)
    print(f"\n[compute] baseline copter: v_max {base['v_max']:.0f} | a_max {base['a_max_g']:.1f}g | "
          f"endur {base['endurance_min']:.0f}min  ->  intercepts {100*intercept_frac(base, THREAT_SPEED):.0f}% "
          f"of {THREAT_SPEED:.0f} m/s threats")

    best = None
    for _ in range(40):
        cfg = {k: random.uniform(*diagnose.BOUNDS[k]) for k in diagnose.PARAMS}
        cfg["n_rotors"] = random.choice([3, 4, 6, 8]); cfg.update(FIXED)
        try:
            caps = diagnose.caps_of(cfg)
        except Exception:
            continue
        if caps["mass"] > 4.5:
            continue
        f = intercept_frac(caps, THREAT_SPEED)
        if best is None or f > best[2]:
            best = (cfg, caps, f)
    cfg, caps, f = best
    print(f"[compute] V1/V2 optimized for the objective: v_max {caps['v_max']:.0f} | a_max {caps['a_max_g']:.1f}g "
          f"| endur {caps['endurance_min']:.0f}min  ->  intercepts {100*f:.0f}%")

    # raw mechanical outcome by threat heading (no interpretation)
    kw = dict(sensing_m=SENSING_M, kill_m=KILL_M, border_m=2 * SENSING_M, t_max=25.0, dt=0.1)
    caught = [round(math.degrees(0) + h) for h in []]  # placeholder
    hits = [int(engagement.simulate(caps, THREAT_SPEED, float(h), **kw)[0]) for h in range(0, 360, 30)]
    print(f"[compute] raw outcome vs heading (0..330 deg, step 30): {hits}   (1=caught, 0=escaped)")

    print("\n" + "-" * 84)
    print("WHERE THE TOOL STOPS (this is the honest line):")
    print(f"  The tool COMPUTED: the best copter it can build intercepts {100*f:.0f}% of {THREAT_SPEED:.0f} m/s")
    print("  threats; most headings escape. That is a NUMBER and a raw fact, produced unaided.")
    print("  It did NOT, on its own:")
    print("    - explain WHY in capability terms ('it can't stay with the target') - that reframing was me;")
    print("    - propose a MISSING DIMENSION (a scan/tracking DOF) - that needed my hand-encoded invariant;")
    print("    - suggest a different platform class (jet/rocket) - that was my interpretation;")
    print("    - question whether a 60-deg cone was even the right requirement - I invented that.")
    print("  Unaided, the tool RESOLVES and OPTIMIZES and REPORTS. The thinking on top was mine.")


if __name__ == "__main__":
    main()
