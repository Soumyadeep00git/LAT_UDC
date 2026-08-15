r"""End-to-end headless prototype of the ENCODE chain, replacing the hardcoded transitions:

    (a) parts.quad_parts        hardware = placed parts with typed ports
    (b) bondgraph.infer_system  parts -> system graph  (topology DISCOVERED from ports, not hardcoded)
    (c) bondgraph.to_fields     system -> physics fields (domain law + region + BCs from the bonds)
    (d) objectives.evaluate     objective = functionals over the fields

Then a CONSISTENCY CHECK: the inferred system must reproduce the hand-written build_uav baseline (same
solve, same capabilities) to prove the inference is correct and stable — not a parallel invention.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

import parts as P
import bondgraph as BG
import objectives as OBJ
from solve import solve
from uav import build_uav, capabilities, G

SEED = {"current": 0.0, "total_mass": 4.0}


def run(cfg, mission):
    print("=" * 74)
    print("(a) HARDWARE — placed parts with typed ports")
    parts = P.quad_parts(cfg)
    roles = {}
    for pt in parts:
        roles[pt.role] = roles.get(pt.role, 0) + 1
    print("    " + ", ".join(f"{k}×{v}" for k, v in roles.items()))

    print("\n(b) SYSTEM — discovered from the ports (bond graph)")
    system, meta = BG.infer_system(parts, cfg)
    print(f"    inferred n_rotors = {meta['n_rotors']}")
    for b in BG.describe_bonds(meta):
        print("    " + b)
    print("    subsystems:")
    for s in system.subsystems:
        for leaf in ([s] if not s.children else s.children):
            print(f"      {leaf.name:11s} '{leaf.function}'  <- {leaf.mechanism} [{leaf.node}]")

    bus = solve(system, seed=dict(SEED))
    cap = capabilities(system, bus)

    print("\n(c) PHYSICS — fields populated from the graph")
    for f in BG.to_fields(system, bus, cap, meta):
        print(f"    {f['field']:10s} <-{f['from']:10s} [{f['backend']}]  {f['region']}")
        print(f"        node {f['node']}  reduced={f['reduced']}")

    print("\n(d) OBJECTIVE — functionals over the fields")
    res = OBJ.evaluate(system, bus, cap, mission)
    for term, have, need, unit, fields, ok in res["checks"]:
        print(f"    {term:14s} {have:7.2f}/{need:<5.0f} {unit:4s}  reads {fields}  {'MET' if ok else 'MISS'}")
    print(f"    -> {'ALL MET' if res['met'] else 'NOT MET'}")

    print("\nCONSISTENCY CHECK — inferred system vs hand-written build_uav baseline")
    base = build_uav(cfg)
    cb = capabilities(base, solve(base, seed=dict(SEED)))
    keys = ["mass", "thrust", "a_max", "v_max", "endurance", "struct_mass"]
    worst = 0.0
    for k in keys:
        a, b = cap[k], cb[k]
        rel = abs(a - b) / max(abs(b), 1e-9)
        worst = max(worst, rel)
        print(f"    {k:11s} inferred {a:10.4f}   baseline {b:10.4f}   rel {rel:.2e}")
    ok = worst < 1e-6
    print(f"    -> {'PASS' if ok else 'FAIL'} (worst rel err {worst:.2e}) — "
          f"inference {'reproduces' if ok else 'DIVERGES from'} the baseline")
    print("=" * 74)
    return ok


if __name__ == "__main__":
    cfg = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)
    mission = {"a_req": 3.0, "v_req": 18.0, "endur_req": 25.0}
    ok = run(cfg, mission)
    sys.exit(0 if ok else 1)
