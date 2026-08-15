"""Bounded co-design — coordinate descent with PER-SUBSYSTEM search control.

Two knobs, read straight off each subsystem (requirements flowdown):
  radicality_budget  — how far THIS subsystem may cross mechanisms (0 = pinned). Attention: where to look.
  owns               — the performance term THIS subsystem is responsible for. Responsibility: what to optimize.

The optimizer sweeps subsystems; for each, it varies only ITS parameters and (within ITS budget) ITS
mechanism to improve ITS owned term, re-solving the coupled whole and honoring the global mass cap. So
creativity is localized where you pointed it and every subsystem has a job — the search stays tangible
instead of diverging into an alien global optimum. Pin the frame (budget 0), free the propulsion
(budget 2): the crossing happens exactly where allowed, the rest stays recognizable.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "physics"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

import radicality
from solve import solve
from uav import build_uav, capabilities, G

# which design parameter belongs to which subsystem (unambiguous ownership)
PARAM_OWNER = {"D_in": "propulsion", "pitch_in": "propulsion", "Kv": "propulsion", "I_max": "propulsion",
               "S": "energy", "cap_mAh": "energy", "L_arm": "arm"}
SWEEP_ORDER = ["propulsion", "energy", "arm"]


def evaluate(cfg, mech):
    sysm = build_uav(cfg, propulsion_mechanism=mech)
    return sysm, capabilities(sysm, solve(sysm, seed={"current": 0.0, "total_mass": 4.0}))


def local_objective(sub, caps, mission):
    """Each subsystem drives its OWNED term by moving its own parameters, but ALL mission floors are
    SHARED HARD CONSTRAINTS — no subsystem may buy its win by starving another's floor (e.g. energy
    shrinking the battery until propulsion loses the voltage it needs for a_max). Once the floors are met,
    each trims the cost it owns. Ownership comes from WHICH params each subsystem moves + WHICH cost it trims."""
    a, e, m = caps["a_max"] / G, caps["endurance"] / 60.0, caps["mass"]
    hard = 1000.0 * (max(0.0, m - mission["mass_cap"])
                     + max(0.0, mission["a_req"] - a)
                     + max(0.0, mission["endur_req"] - e))     # shared floors, respected by everyone
    trim = caps["struct_mass"] if sub == "arm" else 0.3 * m    # the owner's own cost to shave
    return hard + trim


def mechanisms_within_budget(sub_obj, budget):
    """Mechanisms this subsystem may use: its current one plus any within its radicality budget."""
    cur = sub_obj.node
    out = []
    for name, (_, node) in sub_obj.mechanisms.items():
        d = 0 if name == sub_obj.mechanism else (radicality.distance(cur, node) if cur and node else 99)
        if d <= budget:
            out.append((name, d))
    return out


def _local_hillclimb(cfg, mech, tunable, bounds, sub, mission, iters=8):
    cfg = dict(cfg)
    _, caps = evaluate(cfg, mech)
    best = local_objective(sub, caps, mission)
    step = {p: (bounds[p][1] - bounds[p][0]) * 0.15 for p in tunable}
    for _ in range(iters):
        improved = False
        for p in tunable:
            lo, hi = bounds[p]
            for d in (+1, -1):
                t = dict(cfg); t[p] = min(hi, max(lo, cfg[p] + d * step[p]))
                _, c2 = evaluate(t, mech)
                o = local_objective(sub, c2, mission)
                if o < best:
                    cfg, best = t, o; improved = True
        if not improved:
            for p in step: step[p] *= 0.5
    return cfg, best


def codesign(cfg, mission, bounds, sweeps=3):
    tmpl = build_uav(cfg)
    subs = {s.name: s for s in tmpl.subsystems}
    subs["arm"] = next(c for c in subs["structure"].children if c.name == "arm")
    cfg = dict(cfg)
    active_mech = tmpl.by_name()["propulsion"].mechanism
    crossed = {}
    for _ in range(sweeps):
        for sub in SWEEP_ORDER:
            tunable = [p for p in bounds if PARAM_OWNER.get(p) == sub]
            budget = subs[sub].radicality_budget
            mech_opts = mechanisms_within_budget(subs[sub], budget) if sub == "propulsion" else [(active_mech, 0)]
            best_cfg, best_mech = dict(cfg), active_mech
            _, caps0 = evaluate(cfg, active_mech)
            best_obj = local_objective(sub, caps0, mission)
            for mname, d in mech_opts:
                use = mname if sub == "propulsion" else active_mech
                c2, o2 = _local_hillclimb(cfg, use, tunable, bounds, sub, mission)
                if o2 < best_obj - 1e-9:
                    best_obj, best_cfg, best_mech = o2, c2, use
            cfg = best_cfg
            if sub == "propulsion":
                crossed[sub] = (best_mech != active_mech) or crossed.get(sub, False)
                active_mech = best_mech
    sysm, caps = evaluate(cfg, active_mech)
    return {"cfg": cfg, "propulsion_mechanism": active_mech, "caps": caps, "subs": subs, "crossed": crossed}


if __name__ == "__main__":
    mission = {"a_req": 6.0, "endur_req": 8.0, "mass_cap": 6.0}   # >=6 g, >=8 min loiter, <=6 kg
    start = dict(D_in=13, pitch_in=8, Kv=350, I_max=45, S=8, cap_mAh=6000, C_rate=60, L_arm=0.30)
    bounds = dict(D_in=(8, 22), pitch_in=(4, 14), Kv=(150, 450), I_max=(20, 90),
                  S=(4, 12), cap_mAh=(2000, 16000), L_arm=(0.15, 0.6))

    print("PER-SUBSYSTEM SEARCH CONTROL (requirements flowdown):")
    tmpl = build_uav(start)
    allsubs = list(tmpl.subsystems) + tmpl.by_name()["structure"].children
    for s in allsubs:
        print(f"  [{s.name:10s}] owns {s.owns or '-'} | radicality budget {s.radicality_budget}"
              + ("  (pinned)" if s.radicality_budget == 0 else "  (may cross)"))

    print(f"\nMISSION: a_max >= {mission['a_req']} g, endurance >= {mission['endur_req']} min, mass <= {mission['mass_cap']} kg")
    print("CO-DESIGN — coordinate descent, each subsystem optimizing only its owned term within its budget...\n")
    r = codesign(start, mission, bounds)
    c = r["caps"]
    print(f"  propulsion mechanism: {r['propulsion_mechanism']}"
          + ("  (CROSSED rotor->ducted_fan, allowed by its budget)" if r["crossed"].get("propulsion") else "  (stayed rotor)"))
    print(f"  frame: never a candidate (budget 0) — untouched, recognizable")
    print(f"\n  RESULT  mass {c['mass']:.2f} kg | a_max {c['a_max']/G:.2f} g | "
          f"v_max {c['v_max']:.1f} m/s | endurance {c['endurance']/60:.1f} min")
    print(f"  owned terms met: a_max>={mission['a_req']}g {'OK' if c['a_max']/G >= mission['a_req']-0.05 else 'no'}"
          f" | endurance>={mission['endur_req']}min {'OK' if c['endurance']/60 >= mission['endur_req']-0.1 else 'no'}"
          f" | mass<={mission['mass_cap']}kg {'OK' if c['mass'] <= mission['mass_cap']+1e-6 else 'no'}")
