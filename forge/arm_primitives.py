r"""ARM FROM PRIMITIVES — give it only the GENERIC discipline equations, let it work its way up.

Last time I hand-posed the frame (round tube, FIXED wall, YIELD only) and it optimized inside it - and I
noted it was blind to buckling. This removes the frame: both OD and wall are FREE, and the tool is given
the generic primitives of the discipline as competing constraints:

    bending stress   sigma = M / Z            (Z from the section)      -> must stay under yield
    local buckling   sigma_cr = 0.6 E t / D    (thin-cylinder in bending) -> must stay under buckling
    mass             m = rho A L                                        -> the objective to minimize

It then searches the free (OD, wall) space for least mass. The question: does it work up to a good design
on its own, and does it UNPACK a dimension we didn't privilege - i.e. does buckling emerge as the governing
physics when the optimizer drives the design into that regime?
"""
from __future__ import annotations

import math

import numpy as np

E = 70e9            # carbon-fibre modulus (Pa), conservative
SIGMA_Y = 350e6     # yield / strength (Pa)
RHO = 1600.0        # density (kg/m^3)
C_BUCK = 0.6        # thin-cylinder bending buckling coefficient: sigma_cr = C E t / (D/2) = 0.6 E t/D
L = 0.30            # arm length (m)
T_TIP = 60.0        # tip load (N)
M = T_TIP * L       # root bending moment


def section(D, t):
    ID = D - 2 * t
    if ID <= 0:
        return None
    I = math.pi / 64 * (D ** 4 - ID ** 4)
    A = math.pi / 4 * (D ** 2 - ID ** 2)
    Z = I / (D / 2)
    return I, A, Z


def evaluate(D, t):
    s = section(D, t)
    if not s:
        return None
    I, A, Z = s
    sigma = M / Z
    sigma_cr = C_BUCK * E * t / D
    return dict(D=D, t=t, mass=RHO * A * L, sigma=sigma, sigma_cr=sigma_cr,
                yield_ok=sigma <= SIGMA_Y, buckle_ok=sigma <= sigma_cr)


def optimize(constraints):
    """Least-mass (D,t) over the free space subject to the given constraint set."""
    best = None
    for D in np.arange(0.006, 0.040, 0.0005):
        for t in np.arange(0.0001, 0.004, 0.00005):     # allow genuinely thin walls (down to 0.1 mm)
            e = evaluate(D, t)
            if not e:
                continue
            if "yield" in constraints and not e["yield_ok"]:
                continue
            if "buckle" in constraints and not e["buckle_ok"]:
                continue
            if best is None or e["mass"] < best["mass"]:
                best = e
    return best


def _binding(e):
    b = []
    if e["sigma"] >= 0.97 * SIGMA_Y:
        b.append("yield")
    if e["sigma"] >= 0.97 * e["sigma_cr"]:
        b.append("buckling")
    return b or ["a bound (D/t limit)"]


if __name__ == "__main__":
    print("=" * 84)
    print("ARM FROM PRIMITIVES  -  generic discipline equations, OD & wall free; does it work up?")
    print("=" * 84)
    print(f"given: load {T_TIP:.0f} N, arm {L*100:.0f} cm | primitives: bending stress, local buckling, mass")
    print(f"       E {E/1e9:.0f} GPa, yield {SIGMA_Y/1e6:.0f} MPa, buckling sigma_cr = {C_BUCK} E t/D")

    ya = optimize({"yield"})
    print(f"\n[A] with ONLY the yield primitive (the frame I hand-posed last time):")
    print(f"    optimum: OD {ya['D']*1e3:.1f} mm, wall {ya['t']*1e3:.2f} mm  ->  mass {ya['mass']*1e3:.1f} g")
    print(f"    stress {ya['sigma']/1e6:.0f} MPa (yield {SIGMA_Y/1e6:.0f})  binding: {_binding(ya)}")
    print(f"    ...now CHECK buckling on it: sigma_cr = {ya['sigma_cr']/1e6:.0f} MPa  ->  "
          f"{'SAFE' if ya['buckle_ok'] else 'IT BUCKLES (unsafe!) - the blind spot'}")

    yb = optimize({"yield", "buckle"})
    print(f"\n[B] with the yield AND buckling primitives (frame removed - it must respect both):")
    print(f"    optimum: OD {yb['D']*1e3:.1f} mm, wall {yb['t']*1e3:.2f} mm  ->  mass {yb['mass']*1e3:.1f} g")
    print(f"    stress {yb['sigma']/1e6:.0f} MPa | buckling limit {yb['sigma_cr']/1e6:.0f} MPa  "
          f"binding: {_binding(yb)}")

    print("\n" + "-" * 84)
    # read the DATA, don't assert: did buckling actually unpack?
    shifted = (round(yb["D"], 4) != round(ya["D"], 4)) or (round(yb["t"], 5) != round(ya["t"], 5))
    unpacked = (not ya["buckle_ok"]) and shifted
    if unpacked:
        margin = (yb["sigma_cr"] - yb["sigma"]) / 1e6
        print("UNPACKED A DIMENSION (confirmed by the run): the yield-only optimum "
              f"({ya['D']*1e3:.1f}mm x {ya['t']*1e3:.2f}mm wall) BUCKLES (sigma {ya['sigma']/1e6:.0f} > "
              f"cr {ya['sigma_cr']/1e6:.0f} MPa).")
        print(f"  Buckling FORBIDS that thin-wall region, so the optimizer works up to a DIFFERENT design "
              f"({yb['D']*1e3:.1f}mm x {yb['t']*1e3:.2f}mm): smaller, thicker-walled,")
        print(f"  now buckling-safe (margin +{margin:.0f} MPa) and {'+'.join(_binding(yb))}-limited. Buckling didn't END")
        print(f"  UP binding - it RESHAPED the optimum by ruling out the unsafe corner. Cost: {yb['mass']*1e3:.1f} g safe "
              f"vs {ya['mass']*1e3:.1f} g unsafe.")
    elif ya["buckle_ok"]:
        print("NO NEW DIMENSION UNPACKED HERE (honest): the yield-only optimum is ALREADY buckling-safe")
        print(f"  (sigma {ya['sigma']/1e6:.0f} < cr {ya['sigma_cr']/1e6:.0f} MPa), so adding the buckling primitive")
        print("  changed nothing. The optimum simply never entered buckling's regime. Nothing to unpack.")
    else:
        print("The yield-only optimum violates buckling but the buckling-feasible optimum is the same point -")
        print("  a boundary case; not a clean unpacking.")

    print("\nWHEN DOES IT UNPACK A NEW DIMENSION?")
    print("  The moment the objective drives the design into a regime where a primitive it HOLDS becomes")
    print("  binding. Here: min-mass pushed the wall thin, thin walls buckle, and the buckling primitive")
    print("  was present to catch it - so buckling 'unpacked' from slack to governing, on its own.")
    print("  IT CANNOT unpack a dimension whose primitive it does NOT have - that needs new physics added")
    print("  (the residual detector only HINTS one exists from data; naming/adding it is still grounding).")
    print("  So: it unpacks the LATENT dimensions of the equations it's given; a truly new one is the frontier.")
