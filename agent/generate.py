"""GENERATION — the inverse step: from the required PROPERTY set, synthesize the minimal config that
provides every property, bounded by a radicality budget. segregate -> correlate -> generate.

The core judgment you asked for: "X comes with Y and Z, but if you need only Y, define what produces
only Y." A component is a bundle of properties; the mission needs PROPERTIES. So:
  - SEGREGATE the mission into required properties (thrust, energy storage, load bearing).
  - CORRELATE which properties actually drive the metric (keep the necessary ones).
  - GENERATE a minimum-cost COVER of those properties by providers — where a single provider may cover
    MULTIPLE properties (a structural battery IS the airframe), collapsing redundancy into one embedded
    entity. Fusing two properties is a graph CROSSING; its radicality = the graph distance between the
    two properties' physics, so exotic fusions are only allowed once the radius budget is large enough.

This is where y stops being bounded by the class of x: at radius 0 you get the conventional 3-part
platform; raise the radius and the generator fuses parts the component-world keeps separate.
"""
import math
import os
import sys
from itertools import combinations

import radicality as R

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "physics"))
import platform_solve as PS

# property -> the physics-graph node that provides it (so fusion radicality is graph-derived).
# Anchored in the mega archive; distances are deeper now (thrust<->energy=8, thrust<->load=5, energy<->load=8).
ANCHOR = {
    "thrust":        "rotorcraft_bemt.rotor_thrust",
    "energy_storage": "electrochemistry_batteries.pack_energy",
    "load_bearing":  "solid_mechanics.beam_bending_stress",
}

# PHYSICS-DERIVED provider masses: solve a nominal interceptor on the hi-fi coupled solver (BEMT + motor
# + sagging battery + load-sized structure) and read the real component masses. No more hand-picked kg —
# Arch-2's generator is now costed by Arch-1's physics. (Fusion discount below is still heuristic.)
_NOM = PS.solve(PS.Config(D_in=13, pitch_in=6, Kv=300, I_max=45, S=6, cap_mAh=5000, C_rate=60, L_arm=0.30))
BASELINE_MASS = {
    "thrust":        round(_NOM.masses["motors"] + _NOM.masses["props"], 2),
    "energy_storage": round(_NOM.masses["battery"], 2),
    "load_bearing":  round(_NOM.masses["structure"], 2),
}
# Integration saving is NOT a flat discount: it is how much the lighter function's mass a perfectly
# integrated entity can shed, and that decays with the GRAPH DISTANCE between the two functions —
# mechanically-related functions (a boom that carries thrust AND bending) integrate well; functions from
# distant physics (a structural battery: electrochemistry AND load) barely do. So savings ~ exp(-distance).
SHARE_MAX = 0.5                  # max fraction of the lighter function's mass a fusion can shed
SHARE_SCALE = 4.0               # graph-distance over which integration savings decay
FUSED_NAME = {
    frozenset({"energy_storage", "load_bearing"}): "structural_battery (pack IS the airframe)",
    frozenset({"thrust", "load_bearing"}): "structural_rotor (boom IS the load path)",
    frozenset({"thrust", "energy_storage"}): "energetic_rotor (fuel flows through the propulsor)",
}


def fusion_radicality(props):
    ds = [R.distance(ANCHOR[a], ANCHOR[b]) for a, b in combinations(sorted(props), 2)]
    return max(ds) if ds else 0


def fused_mass(props):
    """Mass of one integrated entity: sum of functions minus what integration sheds, where the saving
    decays with the graph distance between the functions (closer physics -> better integration)."""
    ms = [BASELINE_MASS[p] for p in props]
    d = fusion_radicality(props)
    share = SHARE_MAX * math.exp(-d / SHARE_SCALE)
    return round(sum(ms) - min(ms) * share, 3)


def build_providers():
    provs = [{"name": p, "provides": frozenset({p}), "mass": BASELINE_MASS[p], "radicality": 0}
             for p in ANCHOR]                                    # baseline single-property units
    for combo in [{"energy_storage", "load_bearing"}, {"thrust", "load_bearing"},
                  {"thrust", "energy_storage"}]:                 # candidate fusions
        fs = frozenset(combo)
        provs.append({"name": FUSED_NAME[fs], "provides": fs,
                      "mass": fused_mass(combo), "radicality": fusion_radicality(combo)})
    return provs


def generate(required, radius):
    """Minimum-mass cover of `required` using providers within the radicality budget."""
    avail = [p for p in build_providers() if p["radicality"] <= radius]
    best = None
    for k in range(1, len(avail) + 1):
        for subset in combinations(avail, k):
            covered = frozenset().union(*[s["provides"] for s in subset])
            if required <= covered:
                mass = sum(s["mass"] for s in subset)
                if best is None or mass < best[1]:
                    best = (subset, mass)
    return best


if __name__ == "__main__":
    required = frozenset({"thrust", "energy_storage", "load_bearing"})
    print("physics-derived provider masses (from the hi-fi coupled solver):", BASELINE_MASS, "\n")
    print("SEGREGATE  mission -> required properties:", sorted(required))
    print("CORRELATE  all three drive the metric (thrust=agility/speed, energy=endurance, load=survive g)\n")
    print("GENERATE   minimum-mass cover as the radicality budget opens up:\n")
    for radius in (0, 5, 8):
        subset, mass = generate(required, radius)
        parts = [s["name"] for s in subset]
        fused = [s for s in subset if len(s["provides"]) > 1]
        print(f"  radius {radius}:  {len(subset)} parts, {mass:.2f} kg")
        for s in subset:
            tag = f"  [FUSION r={s['radicality']}]" if len(s["provides"]) > 1 else ""
            print(f"       - {s['name']}  covers {sorted(s['provides'])}{tag}")
        if fused:
            print(f"       -> crossed a boundary: {fused[0]['name']} fuses "
                  f"{sorted(fused[0]['provides'])} that the component-world keeps separate.")
        print()
