r"""QUADCOPTER, from parts -> Layer II (architecture) -> Layer III (physics) -> V1, V2, V3.

The 7-part spec (roles), and how each maps to a modeled subsystem:

    part          role         subsystem     note
    ----          ----         ---------     ----
    Pixhawk       controller   payload       avionics mass + bus draw (control law not sized here)
    Battery       powertrain   energy        pack energy / voltage / burst current
    ESC           powertrain   propulsion \
    Motor         powertrain   propulsion  }  the ESC->motor->propeller chain is ONE validated model
    Propeller     powertrain   propulsion /   (propulsion_model: bundled electromechanics + BEMT)
    Airframe      structures   structure     arms (bending) + frame (axial)
    Camera        seeker       seeker        EO detection range / FOV / track rate

Layer II is DISCOVERED from the parts' ports (bondgraph.infer_system), not written down.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import parts as P
import bondgraph
import diagnose
import physics_adapt
import v3c
from solve import solve
from uav import capabilities, G

CFG = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, C_rate=25,
           L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0,
           focal_length_mm=38.0, pixel_pitch_um=3.0, n_pixels=1920, frame_rate_hz=60.0)
MISSION = dict(a_req=5.0, v_req=26.0, endur_req=16.0, detect_range_m=2500.0, search_halfangle_deg=30.0)


def _cap(cfg):
    return diagnose.caps_of(cfg)


def main():
    print("=" * 84)
    print("QUADCOPTER  -  parts -> Layer II -> Layer III -> V1, V2, V3")
    print("=" * 84)

    # ---------- the parts (hardware) ----------
    parts = P.quad_parts(CFG)
    print(f"\nPARTS (hardware, {len(parts)} placed objects; ports are the substrate):")
    for p in parts:
        outs = [q for pt in p.ports if pt.direction == "out" for q in pt.quantities]
        ins = [q for pt in p.ports if pt.direction == "in" for q in pt.quantities]
        print(f"   {p.name:9s} [{p.role:11s}] out={outs} in={ins}")

    # ---------- LAYER II: architecture, discovered from ports ----------
    system, meta = bondgraph.infer_system(parts, CFG)
    print(f"\nLAYER II  -  architecture DISCOVERED from the ports (n_rotors={meta['n_rotors']}):")
    def show(sub, indent="   "):
        print(f"{indent}{sub.name:11s} func={sub.function:16s} "
              f"provides={sub.provides}  requires={sub.requires}")
        for ch in getattr(sub, "children", []) or []:
            show(ch, indent + "     - ")
    for s in system.subsystems:
        show(s)
    print("   bonds (the couplings = the physics edges):")
    for b in bondgraph.describe_bonds(meta):
        print(f"     {b}")

    # ---------- LAYER III: physics fields ----------
    bus = solve(system, seed={"current": 0.0, "total_mass": 4.0})
    cap = capabilities(system, bus)
    fields = bondgraph.to_fields(system, bus, cap, meta)
    print("\nLAYER III  -  physics EXTRACTED (one field per subsystem, BCs from the bonds):")
    for f in fields:
        print(f"   [{f['field']:10s}] from {f['from']:10s} node={f['node']}")
        print(f"        region: {f['region']}")
        print(f"        reduced: {f['reduced']}   backend: {f['backend']}   drives: {f['drives']}")

    base = _cap(CFG)
    def line(tag, caps, extra=""):
        print(f"   {tag:24s} a_max {caps['a_max_g']:.2f}g | v_max {caps['v_max']:.1f} | "
              f"endur {caps['endurance_min']:.0f}min | mass {caps['mass']:.2f}kg {extra}")

    met0 = all(base[m] >= MISSION[r] for m, r in
               [("a_max_g", "a_req"), ("v_max", "v_req"), ("endurance_min", "endur_req")])
    print("\n" + "-" * 84)
    print(f"MISSION: a>={MISSION['a_req']}g  v>={MISSION['v_req']}m/s  endur>={MISSION['endur_req']}min  "
          f"detect>={MISSION['detect_range_m']:.0f}m / {2*MISSION['search_halfangle_deg']:.0f}deg cone")
    line("baseline 4-rotor", base, f"-> {'MET' if met0 else 'UNMET'}")

    # ---------- V1: tune param values (null-space repair) ----------
    c1, met1, ex1, _h, i1 = diagnose.repair(CFG, MISSION)
    changed = ", ".join(k for k in diagnose.PARAMS if abs(c1[k] - CFG[k]) > 1e-3 * max(abs(CFG[k]), 1))
    print("\nV1  (tune PARAM VALUES, fixed 4-rotor):")
    line("V1 result", _cap(c1), f"-> {'MET' if met1 else 'UNMET'}  (changed: {changed})")

    # ---------- V2: rearrange structure (rotor count) ----------
    best, _cands, rule = physics_adapt.adapt(CFG, {k: MISSION[k] for k in ("a_req", "v_req", "endur_req")})
    print(f"\nV2  (also REARRANGE structure - rotor count; {rule}):")
    line(f"V2 result ({best['n']} rotors)", best["caps"], f"-> {'MET' if best['feasible'] else 'UNMET'}")

    # ---------- V3: abstraction / meta-requirement ----------
    d = v3c.meta_requirements(best["cfg"], dict(MISSION, max_revisit_s=1.5))
    print("\nV3  (abstraction / meta-requirement on the resolved design):")
    print(f"   verdict: {d['verdict']}")
    for dd in d.get("confirmed", []) + d.get("model_gaps", []):
        print(f"     {dd['status']}: {dd['name']}  ->  {dd.get('missing_dof','')}")

    print("\n" + "=" * 84)
    print("RESULT: 7 parts -> discovered architecture -> extracted physics -> V1 tunes it, V2 beats it")
    print("with a count change, V3 finds the seeker etendue wall (a missing scan dimension). Fixed topology.")


if __name__ == "__main__":
    main()
