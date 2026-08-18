r"""COMPONENT SOLVE — one uniform engine, one spec per component; the descent pipeline repeated for all.

The arm demo showed the shape: free design variables + the discipline's generic equations as competing
constraints + an objective -> optimize -> the governing (unpacked) dimension falls out. That shape is the
SAME for every component. So this is one engine (grid search + data-driven binding/unpacking), and each
component is DATA: its free variables, its primitive equations, its objective, and which reduced set to
compare against. Extending the equation set = adding primitives to a spec, not new engine code.

It solves each with a REDUCED primitive set and the FULL set, and REPORTS - from the numbers, not asserted -
whether the full set unpacks a governing dimension the reduced one was blind to.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class Primitive:
    name: str
    margin: Callable          # (vars) -> normalized slack; >=0 feasible, ~0 binding
    what: str

    def ok(self, v):
        return self.margin(v) >= -1e-9


@dataclass
class Component:
    name: str
    free: dict                # var -> (lo, hi)
    primitives: list
    objective: Callable       # (vars) -> value to MINIMIZE
    obj_name: str
    reduced: list             # names of the reduced primitive set
    escape: str               # what an unmet/unpacked dimension means physically


def _grid(free, n=15):
    axes = [[(k, lo + (hi - lo) * i / (n - 1)) for i in range(n)] for k, (lo, hi) in free.items()]
    for combo in itertools.product(*axes):
        yield dict(combo)


def solve(comp, active):
    prims = [p for p in comp.primitives if p.name in active]
    best = None
    for v in _grid(comp.free):
        if all(p.ok(v) for p in prims):
            o = comp.objective(v)
            if best is None or o < best[1]:
                best = (v, o)
    if best is None:
        return None
    v, o = best
    binding = [p.name for p in prims if abs(p.margin(v)) < 0.05]
    return dict(vars=v, obj=o, binding=binding)


def report(comp):
    print("\n" + "=" * 84)
    print(f"COMPONENT: {comp.name}   (objective: minimize {comp.obj_name})")
    print(f"  free vars : {list(comp.free)}")
    print(f"  primitives: {[p.name for p in comp.primitives]}   reduced set: {comp.reduced}")
    red = solve(comp, comp.reduced)
    full = solve(comp, [p.name for p in comp.primitives])

    if red is None:
        print("  reduced set is already infeasible - nothing to compare."); return
    vs = "  ".join(f"{k}={red['vars'][k]:.4g}" for k in comp.free)
    print(f"\n  [reduced] optimum: {vs}   {comp.obj_name}={red['obj']:.4g}   binding={red['binding']}")

    extra = [p for p in comp.primitives if p.name not in comp.reduced]
    violated = [p.name for p in extra if not p.ok(red["vars"])]

    if full is None:
        print(f"  [full]    INFEASIBLE - no single-component design satisfies {[p.name for p in comp.primitives]}.")
        print(f"  => UNPACKS A MISSING DIMENSION: {comp.escape}")
        return
    vs2 = "  ".join(f"{k}={full['vars'][k]:.4g}" for k in comp.free)
    print(f"  [full]    optimum: {vs2}   {comp.obj_name}={full['obj']:.4g}   binding={full['binding']}")

    shifted = abs(full["obj"] - red["obj"]) / max(abs(red["obj"]), 1e-9) > 0.02
    if violated and shifted:
        print(f"  => UNPACKED: the reduced optimum VIOLATES {violated}; the full set reshapes the design")
        print(f"     ({comp.obj_name} {red['obj']:.3g} -> {full['obj']:.3g}). Governing physics: {full['binding'] or violated}.")
    elif not violated:
        print("  => NO NEW DIMENSION: the reduced optimum already satisfies the full set (nothing to unpack).")
    else:
        print(f"  => boundary: reduced violates {violated} but the full optimum is ~unchanged.")


# ==================================================================== the specs (one per component)
# ---- STRUCTURE: the arm (yield vs buckling vs deflection) ----
def _arm():
    E, SY, RHO, M, L = 70e9, 350e6, 1600.0, 18.0, 0.30

    def sec(v):
        D, t = v["D"], v["t"]; ID = D - 2 * t
        if ID <= 0:
            return None
        I = math.pi / 64 * (D ** 4 - ID ** 4); A = math.pi / 4 * (D ** 2 - ID ** 2); Z = I / (D / 2)
        return I, A, Z

    def yield_m(v):
        s = sec(v);  return -9 if not s else (SY - M / s[2]) / SY
    def buckle_m(v):
        s = sec(v);  return -9 if not s else (0.6 * E * v["t"] / v["D"] - M / s[2]) / SY
    def defl_m(v):
        s = sec(v);  return -9 if not s else (0.015 - M * L / (3 * E * s[0])) / 0.015
    def mass(v):
        s = sec(v);  return 1e9 if not s else RHO * s[1] * L

    return Component("arm (structure)", {"D": (0.006, 0.040), "t": (0.0001, 0.004)},
                     [Primitive("yield", yield_m, "bending stress <= strength"),
                      Primitive("buckling", buckle_m, "thin-wall shell buckling"),
                      Primitive("deflection", defl_m, "tip deflection <= L/20")],
                     mass, "mass(kg)", ["yield"], "n/a (all failure modes are in the equation set)")


# ---- ENERGY: the battery (energy vs power on the Ragone frontier) ----
def _battery():
    E_REQ, P_REQ = 150.0, 2500.0                       # Wh, W
    ep = [(7, 12000), (60, 9000), (150, 6000), (180, 4000), (200, 2000), (250, 750), (260, 300)]
    e_ax = [a for a, _ in ep]; p_ax = [b for _, b in ep]

    def p_of_e(e):
        return float(np.interp(e, e_ax, p_ax))

    def energy_m(v):
        return (v["e"] * v["mass"] - E_REQ) / E_REQ
    def power_m(v):
        return (p_of_e(v["e"]) * v["mass"] - P_REQ) / P_REQ

    return Component("battery (energy)", {"e": (7, 260), "mass": (0.2, 3.0)},
                     [Primitive("energy", energy_m, "stored Wh/kg x mass >= energy needed"),
                      Primitive("power", power_m, "deliverable W/kg x mass >= burst power")],
                     lambda v: v["mass"], "mass(kg)", ["energy"],
                     "a 2nd energy domain (hybrid: energy cells || power cells / supercap)")


# ---- OPTICS: the seeker (detection resolution vs instantaneous coverage) ----
def _seeker():
    PP, TGT, R_REQ, CONE = 3e-6, 0.35, 1500.0, math.radians(40)

    def ifov(v):
        return PP / (v["focal_mm"] / 1000.0)
    def detect_m(v):
        return (TGT / (2 * ifov(v)) - R_REQ) / R_REQ
    def cover_m(v):
        return (v["npx"] * ifov(v) - CONE) / CONE

    return Component("seeker (optics)", {"focal_mm": (5, 80), "npx": (500, 10000)},
                     [Primitive("detect", detect_m, "detect target at range (fine IFOV)"),
                      Primitive("coverage", cover_m, "cover the search cone (wide FOV)")],
                     lambda v: v["npx"], "pixels", ["detect"],
                     "a temporal scan DOF (coverage over time), or a bigger array than the catalogue allows")


if __name__ == "__main__":
    print("=" * 84)
    print("COMPONENT SOLVE  -  the descent pipeline, one engine, repeated across components")
    print("=" * 84)
    for c in (_arm(), _battery(), _seeker()):
        report(c)

    print("\n" + "-" * 84)
    print("READING IT: one engine solved three different disciplines (structures, energy, optics) from their")
    print("generic primitives, each unpacking its governing dimension FROM THE NUMBERS (not asserted):")
    print("  arm     -> the yield-only optimum violates BOTH buckling and deflection; DEFLECTION governs")
    print("             here (binds hardest), tripling the mass. (Note: which one governs is data-driven -")
    print("             I expected buckling; the run said deflection. That's the point.)")
    print("  battery -> POWER forces a heavier, lower-energy cell (0.6 -> 0.8 kg); both energy & power bind.")
    print("  seeker  -> COVERAGE (etendue) forces the pixel count up ~13x (500 -> 6607).")
    print("Extending to motor / ESC / rotor = adding their primitive specs, no engine change.")
    print("\nHONEST BOUNDS: the per-component physics here is REDUCED (single load case, thin-wall shell")
    print("buckling coefficient, a Ragone interpolation, small-angle optics) and each is flagged; a real")
    print("solve needs the full disciplinary models. And it only unpacks dimensions whose PRIMITIVE is in the")
    print("spec - a failure mode left out of the equation set stays invisible (that is the frontier).")
