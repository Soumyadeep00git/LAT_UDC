"""The agent, re-pointed onto the SYSTEM GRAPH.

It walks the system structurally and does three things, all through the graph:
  GROUND    each subsystem's function to the physics library (+ its descent to fundamentals).
  SCOPE     per subsystem, the mechanism crossings radicality permits within a budget.
  OPTIMIZE  the whole system through the coupled solve toward a mission — naively (tune params) AND
            physics-lensed (swap a subsystem's mechanism within the radicality budget, keep the best).

Every capability we built now attaches to one object: grounding, radicality, the coupled evaluator.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "physics"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

import library
import radicality
from solve import solve
from uav import build_uav, capabilities, G

def ground_system(system, radius=6):
    """Ground each subsystem's function to the library, CONTEXT-AWARE (the subsystem declares the physics
    variables its model exposes, so a polysemous quantity binds to the right mechanism), and RECURSE into
    children. Function names are CANONICAL (enforced), so grounding is a direct canonical lookup — no
    per-function canon table needed."""
    out = []
    def walk(s, depth):
        nid = library.ground_quantity(s.function, s.physics_vars)
        if nid is None:
            out.append((depth, s.name, s.function, None, [], []))
        else:
            descent = [d for d, _, _ in library.descent(nid)][:4]
            alts = radicality.alternatives(s.function, nid, radius)[:5]
            out.append((depth, s.name, s.function, nid, descent, alts))
        for c in s.children:
            walk(c, depth + 1)
    for s in system.subsystems:
        walk(s, 0)
    return out


def evaluate(cfg, mission, mechanism="rotor"):
    sysm = build_uav(cfg, propulsion_mechanism=mechanism)
    bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    cap = capabilities(sysm, bus)
    a, v, m = cap["a_max"] / G, cap["v_max"], cap["mass"]
    penalty = 10.0 * max(0.0, mission["a_req"] - a) + 0.3 * max(0.0, mission["v_req"] - v)
    return m + penalty, cap, (penalty < 1e-6)


def optimize(mission, start, bounds, mechanism="rotor", iters=30):
    """Coordinate hill-climb of the system params through the coupled solve (for a fixed mechanism)."""
    cfg = dict(start)
    best, cap, ok = evaluate(cfg, mission, mechanism)
    step = {k: (hi - lo) * 0.15 for k, (lo, hi) in bounds.items()}
    for _ in range(iters):
        improved = False
        for k, (lo, hi) in bounds.items():
            for d in (+1, -1):
                trial = dict(cfg); trial[k] = min(hi, max(lo, cfg[k] + d * step[k]))
                sc, c2, ok2 = evaluate(trial, mission, mechanism)
                if sc < best:
                    cfg, best, cap, ok = trial, sc, c2, ok2; improved = True
        if not improved:
            for k in step: step[k] *= 0.5
    return cfg, cap, ok, best


def optimize_physics_lensed(mission, start, bounds, radius=2):
    """Try each propulsion MECHANISM reachable within the radicality budget, optimize params for each, and
    keep the best. This is the naive->physics-lensed step: the agent doesn't just tune, it swaps mechanism."""
    base = build_uav(start)
    prop = base.by_name()["propulsion"]
    home = prop.mechanisms["rotor"][1]
    results = []
    for mech, (_, node) in prop.mechanisms.items():
        d = radicality.distance(home, node) if node else 99
        if d > radius:
            results.append((mech, d, None, None, False, "beyond radicality budget"))
            continue
        cfg, cap, ok, score = optimize(mission, start, bounds, mechanism=mech)
        results.append((mech, d, cfg, cap, ok, score))
    winners = [r for r in results if r[3] is not None and r[4]]     # mission met
    best = min(winners, key=lambda r: r[3]["mass"]) if winners else \
           min((r for r in results if r[3] is not None), key=lambda r: r[5])
    return best, results


def main():
    mission = {"a_req": 5.0, "v_req": 30.0}       # >=5 g agility, >=30 m/s, at minimum mass
    start = dict(D_in=13, pitch_in=8, Kv=350, I_max=45, S=8, cap_mAh=6000, C_rate=60, L_arm=0.30)
    bounds = dict(D_in=(8, 22), pitch_in=(4, 14), Kv=(150, 450), I_max=(20, 90),
                  S=(4, 12), cap_mAh=(2000, 16000), L_arm=(0.15, 0.6))

    sysm = build_uav(start)
    print(sysm.describe())

    print("\nGROUND each subsystem's function + permitted crossings (radius 6):")
    for depth, name, func, nid, descent, alts in ground_system(sysm):
        pad = "  " + "    " * depth
        if nid is None:
            print(f"{pad}[{name}] '{func}' -> not in library (no physics claim)")
            continue
        print(f"{pad}[{name}] '{func}' -> [{nid}]")
        print(f"{pad}    rests on: {' <- '.join(descent)}")
        if alts:
            print(f"{pad}    crossings: " + ", ".join(f"{a} (d={d})" for a, d in alts[:3]))

    print(f"\nMISSION: a_max >= {mission['a_req']} g, v_max >= {mission['v_req']} m/s, at minimum mass")
    print("OPTIMIZE — physics-lensed: try each propulsion mechanism within the radicality budget...\n")
    (best_mech, bd, bcfg, bcap, bok, _), results = optimize_physics_lensed(mission, start, bounds, radius=2)
    for mech, d, cfg, cap, ok, extra in results:
        if cap is None:
            print(f"  mechanism '{mech}' (d={d}): {extra}")
        else:
            tag = "  <-- chosen" if mech == best_mech else ""
            print(f"  mechanism '{mech}' (d={d}): mass {cap['mass']:.2f} kg | a_max {cap['a_max']/G:.2f} g | "
                  f"v_max {cap['v_max']:.1f} m/s | mission {'MET' if ok else 'missed'}{tag}")
    print(f"\n  DESIGN: propulsion = {best_mech}, "
          + ", ".join(f"{k}={v:.0f}" if k != "L_arm" else f"{k}={v:.2f}" for k, v in bcfg.items()))
    print(f"  -> mass {bcap['mass']:.2f} kg | a_max {bcap['a_max']/G:.2f} g | v_max {bcap['v_max']:.1f} m/s")


if __name__ == "__main__":
    main()
