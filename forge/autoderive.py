r"""AUTO-DERIVE + SELF-VERIFY — how much of the library can dimensional analysis actually recover?

For each node the archive already records the law's variable exponents (`requires`). For a genuine
dimensioned monomial those exponents are FORCED by dimensional homogeneity, so we can test auto-generation
honestly, with no external reference:

  run Buckingham-Pi on [quantity] + its required variables (from a dimension table keyed to the library's
  OWN names). If it yields exactly one dimensionless group, read off the exponents dimensional analysis
  predicts, and compare them to the exponents the library recorded.

  match      -> the form is auto-derivable AND correct (units alone recover the law)
  mismatch   -> units give a different monomial than the recorded law (the law is not a pure dimensioned
                monomial, or the recorded exponents carry a dimensionless factor units can't see)
  ambiguous  -> more than one Pi group: units underdetermine the form (the drag-with-viscosity case)
  no-group   -> dimensionally inconsistent set as written
  undimensioned -> a variable is not in the dimension table (coverage gap, not a verdict)

This measures the REAL auto-fill ceiling on this library. Base dims: M L T I(current) Th(temp) N(amount).
"""
from __future__ import annotations

import os
import sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import library as L
from vocabulary import canonical
from dimanalysis import _nullspace, _ints

# ----- dimension table, keyed to the library's own variable/quantity names.  [M, L, T, I, Th, N] -----
Z = (0, 0, 0, 0, 0, 0)
DIM = {
    # kinematics / geometry
    "length": (0, 1, 0, 0, 0, 0), "diameter": (0, 1, 0, 0, 0, 0), "wavelength": (0, 1, 0, 0, 0, 0),
    "amplitude": (0, 1, 0, 0, 0, 0), "span": (0, 1, 0, 0, 0, 0), "chord": (0, 1, 0, 0, 0, 0),
    "displacement": (0, 1, 0, 0, 0, 0), "radius": (0, 1, 0, 0, 0, 0),
    "area": (0, 2, 0, 0, 0, 0), "disk_area": (0, 2, 0, 0, 0, 0), "wing_area": (0, 2, 0, 0, 0, 0),
    "volume": (0, 3, 0, 0, 0, 0), "second_moment_of_area": (0, 4, 0, 0, 0, 0),
    "time": (0, 0, 1, 0, 0, 0), "period": (0, 0, 1, 0, 0, 0),
    "velocity": (0, 1, -1, 0, 0, 0), "flight_velocity": (0, 1, -1, 0, 0, 0),
    "closing_velocity": (0, 1, -1, 0, 0, 0), "exhaust_velocity": (0, 1, -1, 0, 0, 0),
    "induced_velocity": (0, 1, -1, 0, 0, 0), "climb_velocity": (0, 1, -1, 0, 0, 0),
    "speed_of_sound": (0, 1, -1, 0, 0, 0), "acceleration": (0, 1, -2, 0, 0, 0),
    "gravity": (0, 1, -2, 0, 0, 0),
    "angular_velocity": (0, 0, -1, 0, 0, 0), "angular_speed": (0, 0, -1, 0, 0, 0),
    "frequency": (0, 0, -1, 0, 0, 0), "bandwidth": (0, 0, -1, 0, 0, 0),
    "switching_frequency": (0, 0, -1, 0, 0, 0),
    # dynamics
    "mass": (1, 0, 0, 0, 0, 0), "molecular_mass": (1, 0, 0, 0, 0, 0),
    "density": (1, -3, 0, 0, 0, 0), "air_density": (1, -3, 0, 0, 0, 0),
    "force": (1, 1, -2, 0, 0, 0), "thrust": (1, 1, -2, 0, 0, 0), "drag": (1, 1, -2, 0, 0, 0),
    "weight": (1, 1, -2, 0, 0, 0), "lift": (1, 1, -2, 0, 0, 0),
    "pressure": (1, -1, -2, 0, 0, 0), "static_pressure": (1, -1, -2, 0, 0, 0),
    "stress": (1, -1, -2, 0, 0, 0), "youngs_modulus": (1, -1, -2, 0, 0, 0),
    "bulk_modulus": (1, -1, -2, 0, 0, 0), "shear_modulus": (1, -1, -2, 0, 0, 0),
    "energy": (1, 2, -2, 0, 0, 0), "work": (1, 2, -2, 0, 0, 0), "torque": (1, 2, -2, 0, 0, 0),
    "heat": (1, 2, -2, 0, 0, 0), "power": (1, 2, -3, 0, 0, 0),
    "momentum": (1, 1, -1, 0, 0, 0), "impulse": (1, 1, -1, 0, 0, 0),
    "viscosity": (1, -1, -1, 0, 0, 0), "dynamic_viscosity": (1, -1, -1, 0, 0, 0),
    "kinematic_viscosity": (0, 2, -1, 0, 0, 0), "mass_flow_rate": (1, 0, -1, 0, 0, 0),
    "moment_of_inertia": (1, 2, 0, 0, 0, 0), "surface_tension": (1, 0, -2, 0, 0, 0),
    "specific_energy": (0, 2, -2, 0, 0, 0), "specific_impulse": (0, 0, 1, 0, 0, 0),
    "damping_coefficient": (1, 0, -1, 0, 0, 0), "stiffness": (1, 0, -2, 0, 0, 0),
    # electrical  (I = current)
    "current": (0, 0, 0, 1, 0, 0), "charge": (0, 0, 1, 1, 0, 0),
    "voltage": (1, 2, -3, -1, 0, 0), "back_emf": (1, 2, -3, -1, 0, 0),
    "resistance": (1, 2, -3, -2, 0, 0), "capacitance": (-1, -2, 4, 2, 0, 0),
    "inductance": (1, 2, -2, -2, 0, 0), "permittivity": (-1, -3, 4, 2, 0, 0),
    "permeability": (1, 1, -2, -2, 0, 0), "magnetic_field": (1, 0, -2, -1, 0, 0),
    "electric_field": (1, 1, -3, -1, 0, 0), "magnetic_flux": (1, 2, -2, -1, 0, 0),
    # thermal (Th = temperature)
    "temperature": (0, 0, 0, 0, 1, 0), "absolute_temperature": (0, 0, 0, 0, 1, 0),
    "entropy": (1, 2, -2, 0, -1, 0), "thermal_conductivity": (1, 1, -3, 0, -1, 0),
    "specific_heat": (0, 2, -2, 0, -1, 0), "thermal_resistance": (-1, -2, 3, 0, 1, 0),
    # amount
    "molar_mass": (1, 0, 0, 0, 0, -1), "number_density": (0, -3, 0, 0, 0, 0),
    # dimensionless (explicitly)
    "mach_number": Z, "upstream_mach_number": Z, "reynolds_number": Z, "damping_ratio": Z,
    "specific_heat_ratio": Z, "gamma": Z, "aspect_ratio": Z, "angle_of_attack": Z, "camber": Z,
    "efficiency": Z, "drag_coefficient": Z, "lift_coefficient": Z, "section_lift_coefficient": Z,
    "poisson_ratio": Z, "solidity": Z, "prandtl_number": Z, "strouhal_number": Z, "friction_coefficient": Z,
    "power_factor": Z, "quality_factor": Z, "duty_cycle": Z,
}
NB = 6


def dim_of(name):
    return DIM.get(name) or DIM.get(canonical(name))


def analyze(node):
    q = node.quantity
    vars_ = list(node.requires)
    names = [q] + vars_
    dims = [dim_of(n) for n in names]
    if any(d is None for d in dims):
        return "undimensioned", None
    A = [[dims[j][d] for j in range(len(names))] for d in range(NB)]
    groups = _nullspace(A)
    tgs = [_ints(g) for g in groups]
    tgs_t = [g for g in tgs if g[0] != 0]           # groups involving the target
    if not tgs_t:
        return "no_group", None
    if len(tgs) > 1:
        return "ambiguous", None
    tg = tgs_t[0]
    a = Fr(tg[0])
    derived = {vars_[i]: Fr(-tg[i + 1], a) for i in range(len(vars_))}
    recorded = {v: Fr(node.requires[v]) for v in vars_}
    return ("match" if derived == recorded else "mismatch"), (derived, recorded)


if __name__ == "__main__":
    A = L.A.ARCHIVE
    from collections import Counter
    tally = Counter()
    examples = {"match": [], "mismatch": [], "ambiguous": []}
    for nid, n in A.items():
        verdict, detail = analyze(n)
        tally[verdict] += 1
        if verdict in examples and len(examples[verdict]) < 4:
            examples[verdict].append((nid, detail))

    tot = len(A)
    print("=" * 84)
    print("AUTO-DERIVE + SELF-VERIFY  -  can dimensional analysis recover the library's recorded laws?")
    print("=" * 84)
    dimd = tot - tally["undimensioned"]
    print(f"  {tot} nodes | dimension-table coverage: {dimd} ({100*dimd//tot}%)  "
          f"[undimensioned {tally['undimensioned']} = table gaps, not verdicts]")
    print(f"\n  Of the {dimd} dimensioned nodes:")
    for k in ("match", "mismatch", "ambiguous", "no_group"):
        pct = 100 * tally[k] // dimd if dimd else 0
        print(f"    {k:10s} {tally[k]:5d}  ({pct}%)")
    print(f"\n  => AUTO-FILL CEILING (verified by the library's own exponents): "
          f"{tally['match']} nodes = {100*tally['match']//dimd if dimd else 0}% of dimensioned, "
          f"{100*tally['match']//tot}% of all.")

    print("\n  matched (units recover the recorded law):")
    for nid, (d, r) in examples["match"]:
        print(f"    {nid}")
    print("\n  mismatched (recorded law is NOT a pure dimensioned monomial):")
    for nid, (d, r) in examples["mismatch"]:
        print(f"    {nid}: units->{ {k:str(v) for k,v in d.items()} }  recorded->{ {k:str(v) for k,v in r.items()} }")
    print("\n  ambiguous (>1 Pi group: units underdetermine -> generator must ABSTAIN):")
    for nid, _ in examples["ambiguous"]:
        print(f"    {nid}")
    print("\n  HONEST READ: 'match' is the only class safe to auto-fill; 'mismatch'/'ambiguous' must be")
    print("  curated or wrapped, and 'undimensioned' just needs the table extended. This is the real ceiling.")
