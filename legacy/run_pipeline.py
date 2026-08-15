"""THE WHOLE PIPELINE — run it.

  0. MISSION -> required capability envelope (what winning actually demands).
  1. ARCHITECTURE 1  (config -> result): search real, buildable quads on the high-fidelity coupled
     solver; report the best drone AND the capability WALL its class hits.
  2. ARCHITECTURE 2  (capability -> platform): stop treating components as sacred. For each capability
     the mission needs, name the HARD invariant (honor) vs the SOFT component convention (cross), size
     an invariant-bounded provider, and show the capability the quad CLASS could not reach but a
     boundary-crossing platform can. y stops being bounded by the class of x.

    python run_pipeline.py
"""
from __future__ import annotations

import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "physics"))

from platform_solve import Config, solve, G
from mission import threat_field
from intercept import assess
import capability as cap


class Spec:
    def __init__(self, v_max, a_max, mass):
        self.v_max = v_max; self.a_max = a_max; self.mass = mass


# ----------------------------------------------------------- 0. required envelope from the mission
def required_envelope(world, target_win=0.80):
    """Grid (v, a); find the least-demanding capability point that still defeats target_win of threats."""
    best = None
    for a_g in [3, 4, 5, 6, 7, 8, 10, 12]:
        for v in [25, 35, 45, 55, 70, 90]:
            _, fr, _, _ = assess(Spec(v, a_g * G, 4.0), world)
            win = 1 - fr
            if win >= target_win:
                demand = a_g + v / 20.0                     # cheaper = less agility + less speed
                if best is None or demand < best[0]:
                    best = (demand, v, a_g, win)
    return best


# ----------------------------------------------------------- 1. Architecture 1
def architecture_1(world, n=160, seed=0):
    rng = random.Random(seed)
    B = {"D_in": (7.5, 28), "pitch_in": (2.5, 20), "Kv": (85, 450), "I_max": (20, 90),
         "S": (3, 12), "cap_mAh": (1300, 16000), "C_rate": (25, 130), "L_arm": (0.12, 1.0)}
    best = None
    max_a = max_v = 0.0
    for _ in range(n):
        c = Config(D_in=rng.uniform(*B["D_in"]), pitch_in=rng.uniform(*B["pitch_in"]),
                   Kv=rng.uniform(*B["Kv"]), I_max=rng.uniform(*B["I_max"]), S=rng.uniform(*B["S"]),
                   cap_mAh=rng.uniform(*B["cap_mAh"]), C_rate=rng.uniform(*B["C_rate"]),
                   L_arm=rng.uniform(*B["L_arm"]))
        st = solve(c)
        if not st.converged or st.mass > 6.0 or st.TWR < 1.3:
            continue
        max_a = max(max_a, st.a_max / G); max_v = max(max_v, st.v_max)
        _, fr, miss, en = assess(Spec(st.v_max, st.a_max, st.mass), world)
        win = 1 - fr
        if best is None or win > best[0]:
            best = (win, c, st, miss)
    return best, max_a, max_v


# ----------------------------------------------------------- 2. Architecture 2
def architecture_2(v_req, a_req_g, quad_max_v, quad_max_a):
    endur = 600.0
    ref_mass = 5.0
    W = ref_mass * G
    A_quad = cap.quad_disk_area(22)
    print("\n2) ARCHITECTURE 2  — capability, not component.  The boundary ledger:\n")

    # ENERGY capability (from a feasible hover, not the runaway high-g case)
    P_hov = cap.hover_power(ref_mass, A_quad)
    E_Wh = P_hov * endur / 3600.0
    m_E = E_Wh / cap.WH_PER_KG
    e_bind = "no" if m_E < 0.5 else "yes"
    print(f"   ENERGY   {endur/60:.0f}-min loiter = {E_Wh:.0f} Wh. HARD boundary: <= {cap.WH_PER_KG:.0f} Wh/kg "
          f"(chemistry). provider {m_E:.2f} kg. binding: {e_bind}")
    print(f"            -> 'a PACK' is SOFT; at 400 Wh/kg energy is nearly free. Not your problem.")

    # AGILITY capability — structure/material bound
    a_bind = "YES" if a_req_g > quad_max_a + 0.2 else "no"
    print(f"   AGILITY  need {a_req_g:.0f} g; quad class reaches {quad_max_a:.1f} g. HARD boundary: "
          f"momentum (power) AND material sigma (structure). binding: {a_bind}")
    print(f"            -> disk area is SOFT but does NOT relax structure; the g-load mass is material-bound.")

    # SPEED capability — the crossable one: power to HOLD v_req two ways
    P_rot = cap.cruise_power(v_req, W, "rotor")
    P_wing = cap.cruise_power(v_req, W, "wing")
    s_bind = "YES" if v_req > quad_max_v + 3 else "no"
    print(f"   SPEED    need {v_req:.0f} m/s; quad class reaches {quad_max_v:.0f} m/s. HARD boundary: "
          f"lift=weight, thrust=drag. binding: {s_bind}")
    print(f"            -> 'thrust from ROTORS' is SOFT. hold {v_req:.0f} m/s:  rotor {P_rot/1000:.1f} kW "
          f"vs wing {P_wing/1000:.2f} kW  ({P_rot/max(P_wing,1):.0f}x less by crossing to a lift surface).")

    print("\n   VERDICT — which boundary actually binds this mission?")
    if a_bind == "YES":
        print(f"     The wall is AGILITY ({a_req_g:.0f} g needed, class tops out at {quad_max_a:.1f} g).")
        print(f"     That boundary is MATERIAL (specific strength) — a HARD one. Crossing rotor->wing buys")
        print(f"     SPEED, which is NOT the bottleneck here, so it would NOT raise win.")
        print(f"     To exceed the wall you must cross the MATERIAL boundary (higher sigma/rho structure)")
        print(f"     or the MISSION-GEOMETRY boundary (an intercept that needs less than {a_req_g:.0f} g).")
    elif s_bind == "YES":
        print(f"     The wall is SPEED, and it is CROSSABLE: cross rotor->wing and y escapes the class.")
    else:
        print(f"     The class already meets the envelope; no boundary needs crossing.")


def main():
    world = threat_field(140)
    print("0) MISSION -> required capability envelope")
    env = required_envelope(world, target_win=0.80)
    if env:
        _, v_req, a_req_g, win = env
        print(f"   to defeat >=80% of threats: v_req ~ {v_req} m/s, a_req ~ {a_req_g} g "
              f"(achieves {win*100:.0f}%)\n")
    else:
        v_req, a_req_g = 70, 8
        print("   >=80% not reachable in the gridded envelope; using v_req 70, a_req 8 g as the target.\n")

    print("1) ARCHITECTURE 1  — best buildable quad on the coupled hi-fi solver ...")
    t0 = time.time()
    (best, max_a, max_v) = architecture_1(world)
    if best:
        win, c, st, miss = best
        print(f"   BEST QUAD: {c.D_in:.0f}x{c.pitch_in:.0f} Kv{c.Kv:.0f} {c.S:.0f}S {c.cap_mAh:.0f}mAh "
              f"L{c.L_arm*100:.0f}cm I_max{c.I_max:.0f}A")
        print(f"     mass {st.mass:.2f}kg | a_max {st.a_max/G:.2f}g | v_max {st.v_max:.1f} | "
              f"endur {st.endurance_s/60:.1f}min  ->  win {win*100:.0f}%")
        print(f"   CLASS WALL: no converged quad exceeded a_max {max_a:.1f} g or v_max {max_v:.0f} m/s "
              f"({time.time()-t0:.0f}s search)")

    architecture_2(v_req, a_req_g, max_v, max_a)


if __name__ == "__main__":
    main()
