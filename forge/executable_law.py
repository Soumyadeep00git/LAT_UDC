r"""EXECUTABLE LAW — the missing piece that turns the library from an encyclopedia into a computable network.

A sanctuary node today is PROSE + a variable list: you can read it, you cannot run it. An executable Law
adds the one thing missing — a runnable relation — while keeping the grounding (the node id + the prose,
for validation/descent). Its inputs are tagged so the dataflow can CLOSE: a variable is either
  - "base"    : a designatable input (a design param, a material constant, the environment), or
  - "derived" : produced by ANOTHER law's `quantity` (so laws chain, output -> input).

`to_linkage()` drops a Law straight into the field layer, so a set of closed laws assembles into a
`field.Structure` and SOLVES. That is a design quantity computed FROM the laws — not from uav.py.
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field as dcf
from typing import Callable

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import field


@dataclass
class Law:
    node: str                       # grounding: the sanctuary node id this law realizes
    quantity: str                   # the canonical quantity it PRODUCES (its output)
    inputs: dict                    # var_name -> "base" | "derived"
    residual: Callable              # (assignment dict) -> ~O(1) residual: the EXECUTABLE relation
    prose: str = ""                 # kept for provenance / descent / validation

    def variables(self):
        return [self.quantity] + list(self.inputs)

    def to_linkage(self):
        return field.Linkage("law:" + self.quantity, self.variables(), self.residual, kind="law", node=self.node)

    def evaluate(self, assignment):
        """Run the law: given every OTHER variable, this is the residual (0 when satisfied)."""
        return self.residual(assignment)


def assemble(laws, base_inputs, scales=None):
    """Build a field.Structure from a set of executable laws + the base inputs (knowns)."""
    s = field.Structure()
    scales = scales or {}
    names = set()
    for L in laws:
        names.update(L.variables())
    for n in names:
        s.add_param(n, scale=scales.get(n, abs(base_inputs.get(n, 1.0)) or 1.0))
    for L in laws:
        s.linkages.append(L.to_linkage())
    return s, dict(base_inputs)


# ============================================================ a SIMPLE executable law (one), grounded
WEIGHT = Law(
    node="classical_mechanics.newtons_second_law",
    quantity="weight",
    inputs={"mass": "base", "g": "base"},
    residual=lambda a: a["weight"] / (a["mass"] * a["g"]) - 1,
    prose="Weight is mass times gravitational acceleration, W = m g.",
)

# ============================================================ a CLOSED slice: endurance from the laws
DISK_AREA = Law(
    node="geometry_math.circle_area",
    quantity="disk_area",
    inputs={"n_rotors": "base", "rotor_diameter": "base"},
    residual=lambda a: a["disk_area"] / (a["n_rotors"] * math.pi * (a["rotor_diameter"] / 2) ** 2) - 1,
    prose="Total actuator-disk area = n rotors each of area pi (D/2)^2.",
)
HOVER_POWER = Law(
    node="rotorcraft_bemt.actuator_disk_momentum",
    quantity="hover_power",
    inputs={"weight": "derived", "air_density": "base", "disk_area": "derived", "figure_of_merit": "base"},
    residual=lambda a: a["hover_power"] / (a["weight"] ** 1.5
                                           / (a["figure_of_merit"] * math.sqrt(2 * a["air_density"] * a["disk_area"]))) - 1,
    prose="Momentum-theory hover power P = W^1.5 / (FM sqrt(2 rho A)).",
)
USABLE_ENERGY = Law(
    node="electrochemistry_batteries.pack_energy",
    quantity="usable_energy",
    inputs={"pack_wh": "base", "usable_fraction": "base"},
    residual=lambda a: a["usable_energy"] / (3600.0 * a["pack_wh"] * a["usable_fraction"]) - 1,
    prose="Usable pack energy (J) = 3600 * pack_Wh * usable_fraction.",
)
ENDURANCE = Law(
    node="electrochemistry_batteries.pack_energy",
    quantity="endurance",
    inputs={"usable_energy": "derived", "hover_power": "derived"},
    residual=lambda a: a["endurance"] / (a["usable_energy"] / a["hover_power"]) - 1,
    prose="Hover endurance (s) = usable energy / hover power (a bond-graph balance).",
)

ENDURANCE_SLICE = [WEIGHT, DISK_AREA, HOVER_POWER, USABLE_ENERGY, ENDURANCE]


def _ground_check(laws):
    """For each law: is its node a real sanctuary node, and is its quantity physics or math?"""
    try:
        import library as L
        out = []
        for lw in laws:
            out.append((lw.node, lw.node in L.A.ARCHIVE, L.classify(lw.quantity)))
        return out
    except Exception:
        return []


if __name__ == "__main__":
    print("=" * 80)
    print("EXECUTABLE LAW  -  one prose law made runnable, then a closed slice that SOLVES")
    print("=" * 80)

    # (1) a single executable law actually runs
    a = {"mass": 3.0, "g": 9.81, "weight": 29.43}
    print("\n1. ONE law, executed (not prose):")
    print(f"   {WEIGHT.prose}")
    print(f"   residual at W=29.43, m=3.0, g=9.81 : {WEIGHT.evaluate(a):.2e}  (0 => satisfied)")
    print(f"   grounded node: {WEIGHT.node}")

    # (2) the closed slice: base inputs -> solve every derived quantity -> a DESIGN NUMBER
    base = {"mass": 3.0, "g": 9.81, "n_rotors": 4, "rotor_diameter": 0.33,
            "air_density": 1.225, "figure_of_merit": 0.70, "pack_wh": 133.2, "usable_fraction": 0.85}
    scales = {"weight": 30, "disk_area": 0.3, "hover_power": 250, "usable_energy": 4e5, "endurance": 1600}
    s, knowns = assemble(ENDURANCE_SLICE, base, scales)
    r = field.solve_field(s, knowns, seed=scales)
    v = r.values
    print("\n2. CLOSED SLICE (5 executable laws), solved by the field layer:")
    print(f"   status={r.status}  residual={r.residual:.1e}")
    print(f"   weight        = {v['weight']:.2f} N")
    print(f"   disk_area     = {v['disk_area']:.3f} m^2")
    print(f"   hover_power   = {v['hover_power']:.1f} W")
    print(f"   usable_energy = {v['usable_energy']:.0f} J")
    print(f"   ENDURANCE     = {v['endurance']:.0f} s = {v['endurance']/60:.1f} min")
    # hand check
    W = 3.0 * 9.81
    A = 4 * math.pi * (0.33 / 2) ** 2
    P = W ** 1.5 / (0.70 * math.sqrt(2 * 1.225 * A))
    E = 3600 * 133.2 * 0.85
    print(f"   hand check    : {E/P:.0f} s = {E/P/60:.1f} min")

    # (3) grounding: these laws point at real sanctuary nodes
    print("\n3. grounding (each law -> a sanctuary node; gaps shown honestly):")
    for node, ok, track in _ground_check(ENDURANCE_SLICE):
        note = "" if ok else "  (MISSING producer node - an orphan to ADD; exactly the 77% gap from the audit)"
        print(f"   {node:45s} in_library={ok}  track={track}{note}")

    print("\n" + "=" * 80)
    print("READING IT")
    print("  A law now carries a RUNNABLE relation, not prose. Five of them, with inputs tagged base vs")
    print("  derived so the dataflow CLOSES, assemble into the field layer and solve for endurance -")
    print("  a design number produced FROM the laws, grounded in the sanctuary, with uav.py never touched.")
    print("  This is the one-slice proof that the library can be made computable.")
