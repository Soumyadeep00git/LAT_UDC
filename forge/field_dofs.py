r"""Emergent design DOFs — read each field's governing law and let its shaping handles emerge, typed.

We do NOT hardcode "the design params are dia, pitch, Kv, ...". Instead, for each field we ask the physics
library what its law depends on (`node.requires`) and classify every quantity by category:

    geometry     shape / size handles          (design-controllable)
    material     constitutive / chemistry       (design-controllable)  <- the V3 handles
    boundary     operating condition            (set by mission/control, not design)
    coupled      solved from the field/others   (not a knob)
    environment  fixed constant                 (not a knob)

The controllable set (geometry + material) is the emergent design-DOF list — different per field, derived
from the laws, and explainable (every DOF is a named quantity a real law needs). Classification is a
CURATED table (namespace discipline: no fuzzy matching); unknown quantities are flagged, not guessed.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import library
import bondgraph
import parts as P
import diagnose
from vocabulary import canonical

# curated quantity -> category (built from the actual law inputs of the quad's fields)
CATEGORY = {
    # geometry (shape/size)
    "disk_area": "geometry", "pack_mass": "geometry", "fiber_distance": "geometry",
    "second_moment_of_area": "geometry", "cross_section_area": "geometry",
    # material / constitutive  (the reshape-the-medium handles)
    "specific_energy": "material", "usable_capacity_fraction": "material",
    # environment (fixed)
    "air_density": "environment",
    # boundary / operating condition (mission/control sets it)
    "climb_velocity": "boundary",
    # coupled (produced by the solve / a deeper law)
    "induced_velocity": "coupled", "bending_moment": "coupled", "internal_force": "coupled",
}
DESIGN = {"geometry", "material"}       # controllable shaping categories

# which hand-typed param each emergent geometry/material handle corresponds to (for the comparison)
MAP_TO_HAND = {
    "disk_area": "D_in (+ n_rotors)", "pack_mass": "S, cap_mAh",
    "specific_energy": "-- NONE (battery chemistry: a new V3 material handle)",
    "usable_capacity_fraction": "-- NONE (BMS / depth-of-discharge)",
    "fiber_distance": "-- NONE (arm section OD)", "second_moment_of_area": "-- NONE (arm OD + wall)",
    "cross_section_area": "-- NONE (frame section)",
}


def extract(system):
    out = []
    for top in system.subsystems:
        for leaf in ([top] if not top.children else top.children):
            nid = leaf.node
            if not nid:
                continue
            node = library.node(nid)
            reqs = list(getattr(node, "requires", {}).keys()) if node else []
            dofs = []
            for q in reqs:
                cat = CATEGORY.get(canonical(q), CATEGORY.get(q, "unclassified"))
                dofs.append({"quantity": q, "category": cat, "controllable": cat in DESIGN})
            out.append({"field": leaf.name, "node": nid, "dofs": dofs})
    return out


def emergent_params(system):
    seen, params = set(), []
    for f in extract(system):
        for d in f["dofs"]:
            if d["controllable"] and d["quantity"] not in seen:
                seen.add(d["quantity"])
                params.append((d["quantity"], d["category"], f["field"]))
    return params


if __name__ == "__main__":
    cfg = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)
    system, meta = bondgraph.infer_system(P.quad_parts(cfg), cfg)

    print("DESIGN DOFs EMERGING FROM THE PHYSICS LAWS (not hand-typed)\n")
    for f in extract(system):
        print(f"  [{f['field']}]  {f['node']}")
        for d in f["dofs"]:
            tag = "DESIGN-DOF" if d["controllable"] else d["category"]
            flag = "  <-- unclassified!" if d["category"] == "unclassified" else ""
            print(f"       {d['quantity']:24s} {tag}{flag}")
        print()

    em = emergent_params(system)
    print("EMERGENT controllable design DOFs (geometry + material):")
    for q, cat, field in em:
        print(f"    {q:24s} [{cat:8s}] from {field:10s}  ~  hand param: {MAP_TO_HAND.get(q, '?')}")

    print(f"\nHAND-TYPED params (diagnose.PARAMS): {diagnose.PARAMS}")
    print("\nWHAT THE LAWS REVEAL:")
    print("  + NEW handles the hand-list never had: specific_energy (chemistry), section geometry")
    print("    (fiber_distance / second_moment_of_area / cross_section_area), usable_capacity_fraction.")
    print("  - pitch_in, Kv, I_max are NOT direct inputs of these laws at this fidelity -- they set the")
    print("    powertrain operating point, i.e. they live inside the COUPLED 'induced_velocity'.")
    print("    To expose them you DESCEND to the deeper blade-element law -- the V3 'get inside the field' move:")
    desc = library.descent("rotorcraft_bemt.rotor_thrust")
    print("    descent(rotor_thrust): " + " -> ".join(d[0].split(".")[-1] for d in desc[:5]))
