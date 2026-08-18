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
    main()
