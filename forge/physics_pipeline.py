r"""PHYSICS PIPELINE — the single front door wiring this session's physics-layer functions into one flow.

(Distinct from pipeline.py, the older full ENCODE/DECODE+CAD loop. This is the physics-resolution spine.)

    cfg + mission
        |
        v
  [1] uav_seeker_pack.solve_uav_seeker  -> capabilities FROM the linked laws (cross-checked vs uav.py)
        |
        v
  [2] resolve.resolve                    -> best design (max worst-case margin) + reachable envelope + wall
        |
        v
  [3] v3c.meta_requirements              -> confirm the wall structurally (missing dimension, if any)

One call, the whole physics layer: solve -> resolve -> diagnose. No topology generated.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import uav_seeker_pack as pack
import resolve as R
import v3c
from uav import G


def run(cfg, mission):
    out = {}

    # [1] SOLVE the linked physics (and check it against the trusted model)
    sol, cap, laws = pack.solve_uav_seeker(cfg)
    checks = [("mass", sol.values["total_mass"], cap["mass"]),
              ("a_max_g", sol.values["a_max"] / G, cap["a_max"] / G),
              ("endurance_min", sol.values["endurance"] / 60, cap["endurance"] / 60),
              ("detection_m", sol.values["detection_range"], cap["detection_range"])]
    out["solve"] = {"status": sol.status, "residual": sol.residual, "n_laws": len(laws),
                    "worst_rel": max(abs(a - b) / max(abs(b), 1e-9) for _, a, b in checks)}

    # [2] RESOLVE the best design + envelope + wall
    out["resolve"] = R.resolve(cfg, mission)

    # [3] DIAGNOSE: confirm the binding wall structurally
    best_cfg = dict(out["resolve"]["cfg"])
    seeker_mission = dict(mission, max_revisit_s=1.5)
    out["diagnose"] = v3c.meta_requirements(best_cfg, seeker_mission)
    return out


if __name__ == "__main__":
    cfg = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, C_rate=25,
               L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0,
               focal_length_mm=38.0, pixel_pitch_um=3.0, n_pixels=1920, frame_rate_hz=60.0)
    mission = dict(a_req=5.0, v_req=26.0, endur_req=16.0, detect_range_m=2500.0, search_halfangle_deg=30.0)

    o = run(cfg, mission)
    s, r, d = o["solve"], o["resolve"], o["diagnose"]
    c, caps = r["cfg"], r["caps"]

    print("=" * 84)
    print("PHYSICS PIPELINE  -  solve -> resolve -> diagnose, wired end to end (fixed topology)")
    print("=" * 84)

    print(f"\n[1] SOLVE (linked physics): status={s['status']}  {s['n_laws']} laws  residual {s['residual']:.1e}")
    print(f"    cross-check vs uav.py: worst rel err {s['worst_rel']:.1e}  -> "
          f"{'MATCH' if s['worst_rel'] < 1e-3 else 'MISMATCH'}")

    print(f"\n[2] RESOLVE ({r['rule']}): best design the physics reaches")
    print(f"    {c['n_rotors']} rotors, D {c['D_in']:.1f}in, pitch {c['pitch_in']:.1f}, {c['S']:.1f}S {c['cap_mAh']:.0f}mAh")
    print(f"    a_max {caps['a_max_g']:.2f}g | v_max {caps['v_max']:.1f} | endur {caps['endurance_min']:.0f}min | mass {caps['mass']:.2f}kg")
    print(f"    worst-case margin {r['worst']:+.2f}  binding: {r['binding'].upper()}")

    print(f"\n[3] DIAGNOSE: verdict = {d['verdict']}")
    for dd in d.get("confirmed", []) + d.get("model_gaps", []):
        print(f"    {dd['status']}: {dd['name']} -> {dd.get('missing_dof','')}")

    print("\n" + "-" * 84)
    print(f"ONE LINE: physics resolves this topology to a {caps['a_max_g']:.1f}g / {caps['endurance_min']:.0f}-min design,")
    print(f"          matches the trusted model to {s['worst_rel']:.0e}, and names its ceiling: the {r['binding']}.")
