r"""ARM FIELD — the essence->decode pattern, ported from the rotor to a STRUCTURE (a different domain).

The rotor: optimize the loading FIELD (thrust_field -> uniform/Betz), decode to blade geometry (blade_design).
The arm: same shape, different physics. The essence of a bending member is the SECTION-MODULUS FIELD along
its span. A tip-loaded cantilever carries bending moment M(x) = T*(L-x); to carry it at the allowable stress
with least material, each station needs section modulus Z(x) = M(x)/sigma - and the least-mass beam sets
Z(x) EXACTLY there (a fully-stressed design; the calculus-of-variations optimum for this determinate beam).
Then DECODE: pick a tube taper OD(x) that realizes Z(x). Forward-validate: stress ratio ~ 1 everywhere.

Essence = the section field (grounded in beam bending); embodiment = the tube taper. dia/pitch of the rotor
had their analog here in OD/wall of the tube; the field is the thing optimized, the geometry is decoded.
"""
from __future__ import annotations

import math
import sys

import numpy as np

RHO_CF = 1600.0          # carbon-fibre tube density (kg/m^3)
SIGMA_ALLOW = 350e6      # allowable bending stress (Pa), with margin
WALL = 1.0e-3            # tube wall thickness (m) - fixed here; OD is the decoded taper
R_MIN = 3.0e-3           # minimum tube radius (manufacturing / handling floor)


def essence(T_tip, L, N=24):
    """The section-modulus FIELD: Z(x) = M(x)/sigma for a fully-stressed tip-loaded cantilever."""
    x = np.linspace(0, L, N)
    M = T_tip * (L - x)                       # bending moment, tip load
    Z_req = M / SIGMA_ALLOW                    # required section modulus (the fully-stressed optimum)
    return x, M, Z_req


def decode(x, Z_req):
    """Decode the section field to a tube taper OD(x) (thin wall: Z ~ pi R^2 t)."""
    R = np.sqrt(np.maximum(Z_req, 1e-30) / (math.pi * WALL))
    R = np.maximum(R, R_MIN)                   # honest floor
    OD = 2 * R
    area = 2 * math.pi * R * WALL              # thin-wall annulus area
    return OD, R, area


def mass_of(x, area):
    integral = float(np.sum((area[:-1] + area[1:]) / 2 * np.diff(x)))     # trapezoid (numpy-version-safe)
    return RHO_CF * integral


def forward_stress_ratio(x, M, R):
    """Validate: realized section modulus Z = pi R^2 t -> stress M/Z, ratio to allowable."""
    Z = math.pi * R ** 2 * WALL
    sigma = M / np.maximum(Z, 1e-30)
    return sigma / SIGMA_ALLOW


def trace(T_tip=60.0, L=0.30):
    """Show the reasoning station by station: load -> moment -> strength needed -> invert to a tube ->
    floor decision -> verify. This is the tool's actual work, with the arithmetic exposed."""
    print("=" * 84)
    print("ARM ESSENCE-SOLVE  -  thinking process, step by step")
    print("=" * 84)
    print(f"GIVEN: tip load {T_tip:.0f} N | arm {L*100:.0f} cm | carbon limit {SIGMA_ALLOW/1e6:.0f} MPa | "
          f"wall {WALL*1e3:.1f} mm | min radius {R_MIN*1e3:.0f} mm")
    print("\nFor each station x along the arm (root -> tip), the tool reasons:")
    for x in (0.0, 0.075, 0.15, 0.225, 0.30):
        M = T_tip * (L - x)
        Z = M / SIGMA_ALLOW
        R_ideal = math.sqrt(Z / (math.pi * WALL)) if Z > 0 else 0.0
        floored = R_ideal < R_MIN
        R = max(R_ideal, R_MIN)
        Zr = math.pi * R ** 2 * WALL
        ratio = (M / Zr) / SIGMA_ALLOW if Zr > 0 else 0.0
        print(f"\n  x = {x:.3f} m  ({x/L*100:.0f}% out):")
        print(f"    1. bending moment    M = {T_tip:.0f} x ({L:.2f}-{x:.3f}) = {M:5.2f} N-m        [statics: load x lever to tip]")
        print(f"    2. strength needed   Z = M / limit = {M:5.2f}/{SIGMA_ALLOW/1e6:.0f}e6 = {Z:.2e} m^3   [keep stress <= limit]")
        print(f"    3. invert the tube   R = sqrt(Z/(pi t)) = {R_ideal*1e3:5.2f} mm  ->  OD {2*R_ideal*1e3:5.1f} mm  [thin-wall: Z=pi R^2 t]")
        if floored:
            print(f"    4. floor DECISION    {R_ideal*1e3:.2f} mm < {R_MIN*1e3:.0f} mm min  ->  raise R to {R_MIN*1e3:.0f} mm (OD {2*R*1e3:.1f})  [manufacturing floor OVERRIDES the essence]")
        else:
            print(f"    4. floor check       {R_ideal*1e3:.2f} mm >= {R_MIN*1e3:.0f} mm min  ->  keep")
        verdict = "fully stressed (ideal)" if abs(ratio - 1) < 0.05 else \
                  ("over-built by the floor (honest: not fully stressed here)" if floored else "under limit")
        print(f"    5. verify stress     sigma/limit = {ratio:.2f}   [{verdict}]")

    # the mass reasoning
    x = np.linspace(0, L, 40)
    M = T_tip * (L - x)
    R = np.maximum(np.sqrt(np.maximum(M / SIGMA_ALLOW, 0) / (math.pi * WALL)), R_MIN)
    area = 2 * math.pi * R * WALL
    m_opt = mass_of(x, area)
    m_const = RHO_CF * (2 * math.pi * float(R[0]) * WALL) * L
    print("\n  THEN, over the whole span:")
    print(f"    6. integrate mass    sum(density x area x dx) = {m_opt*1e3:.1f} g")
    print(f"    7. compare to naive  constant tube at root OD = {m_const*1e3:.1f} g  ->  taper is {100*(1-m_opt/m_const):.0f}% lighter")
    print("\n  CONCLUSION: fat where the bending is (root), thin where it isn't (tip), floored where the")
    print("  minimum radius wins. Every step is statics + one geometry inversion - no assumed tube.")


def main():
    T_rotor, n_g, L = 20.0, 3.0, 0.30         # 20 N per rotor, 3 g maneuver, 0.30 m arm
    T_tip = T_rotor * n_g

    print("=" * 82)
    print("ARM FIELD  -  essence->decode for a STRUCTURE (optimize the section field, decode a taper)")
    print("=" * 82)
    print(f"load: {T_tip:.0f} N at the tip ({T_rotor:.0f} N x {n_g:.0f} g), arm L {L*100:.0f} cm, "
          f"carbon tube wall {WALL*1e3:.1f} mm, allowable {SIGMA_ALLOW/1e6:.0f} MPa")

    x, M, Z_req = essence(T_tip, L)
    OD, R, area = decode(x, Z_req)
    m_opt = mass_of(x, area)
    ratio = forward_stress_ratio(x, M, R)

    print("\nDESIGNED taper (optimized section field, decoded to a tube):")
    print(f"   {'x/L':>5} {'moment(Nm)':>11} {'OD(mm)':>7} {'stress/allow':>13}")
    for i in (0, len(x) // 4, len(x) // 2, 3 * len(x) // 4, -1):
        print(f"   {x[i]/L:>5.2f} {M[i]:>11.2f} {OD[i]*1e3:>7.1f} {ratio[i]:>13.2f}")

    # honest read of the validation: fully stressed EXCEPT where the R_min floor takes over (tip)
    at_floor = R <= R_MIN + 1e-9
    print(f"\nFORWARD-VALIDATE: stress/allowable is ~1.0 where the beam is fully stressed; it drops below 1")
    print(f"   only near the tip where the R_min floor ({R_MIN*1e3:.0f} mm) takes over ({int(at_floor.sum())}/{len(x)} stations).")

    # compare to a constant-section beam sized for the ROOT (the naive, un-optimized choice)
    R_root = float(R[0])
    m_const = RHO_CF * (2 * math.pi * R_root * WALL) * L
    print(f"\nMASS: optimized taper {m_opt*1e3:.1f} g  vs  constant-section (root OD everywhere) {m_const*1e3:.1f} g")
    print(f"   -> {100*(1-m_opt/m_const):.0f}% lighter, for the SAME strength. The field optimization bought that.")

    print("\n" + "-" * 82)
    print("Same pattern as the rotor, different domain: optimize the ESSENCE field (section modulus, grounded")
    print("in beam bending), decode to EMBODIMENT (a tube taper), forward-validate (fully stressed).")
    print("\nWHAT THIS CAN vs CANNOT DO:")
    print("  CAN:    solve the least-mass section field for a determinate tip-loaded cantilever and decode a")
    print("          real taper that is fully stressed, with a quantified mass saving vs the naive beam.")
    print("  CANNOT: handle buckling, shear, stress concentrations, joints/lugs, or fatigue/dynamic loads")
    print("          (none modelled); guarantee global optimality for statically-INDETERMINATE structures")
    print("          (fully-stressed = optimal only for this determinate case); or pick the wall/material")
    print("          (fixed here - co-optimizing wall+OD+material is a bigger search, not done).")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "trace":
        trace()
    else:
        main()
