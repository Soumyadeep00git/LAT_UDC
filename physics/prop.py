"""BEMT prop model — blade-element momentum theory.

The blade is cut into radial strips. Each strip is a little wing at local pitch angle beta(r) seeing a
relative wind from rotation (Omega*r) plus axial flow (freestream V + induced v_i). We solve the induced
velocity at each strip by balancing the blade-element thrust against the axial-momentum thrust
(the "momentum" half of BEMT), with a Prandtl tip-loss factor. Integrate the strips -> total thrust T
and torque Q at a given (Omega, V).

AIRFOIL POLAR IS ANALYTIC (we have no measured polars): thin-airfoil lift slope with a smooth stall,
quadratic drag with a post-stall flat-plate rise. So this is the BEMT *method* with approximate airfoil
*inputs* — honest about which is which. Constants are calibrated so a mid prop lands in the catalog's
27-84 N/rotor envelope.

    T, Q = thrust_torque(D_in, pitch_in, n_blades, rpm, V_axial, rho)
"""
from __future__ import annotations

import math

RHO0 = 1.225
IN2M = 0.0254

# --- analytic airfoil polar (per-strip 2-D section) ---
CL_ALPHA = 5.9          # lift-curve slope [1/rad] (~2*pi with 3-D/thickness correction)
ALPHA0 = math.radians(-2.0)   # zero-lift angle (cambered)
CL_MAX = 1.25           # stall ceiling
CD0 = 0.020             # profile drag floor
CD_K = 0.030            # induced-ish drag factor (Cd = CD0 + CD_K*Cl^2)
CD_STALL = 1.3          # post-stall flat-plate drag

# --- blade geometry defaults (a representative tapered prop) ---
SOLIDITY = 0.11         # blade area / disk area — sets chord from D and blade count
N_STRIPS = 10
HUB_FRAC = 0.15         # inboard cutout
N_INFLOW = 12           # inflow fixed-point iterations per strip


def _cl_cd(alpha):
    """Analytic section lift/drag vs angle of attack [rad]."""
    a = alpha - ALPHA0
    cl_lin = CL_ALPHA * a
    if abs(cl_lin) <= CL_MAX:
        cl = cl_lin
        cd = CD0 + CD_K * cl * cl
    else:                                   # stalled — cap lift, flat-plate drag ramps in
        cl = math.copysign(CL_MAX, cl_lin)
        over = min(abs(a) - CL_MAX / CL_ALPHA, math.radians(30))
        cd = CD0 + CD_K * CL_MAX ** 2 + CD_STALL * math.sin(over) ** 2
    return cl, cd


def thrust_torque(D_in, pitch_in, n_blades, rpm, V_axial=0.0, rho=RHO0):
    """Total rotor thrust [N] and shaft torque [N.m] at (rpm, axial airspeed)."""
    R = D_in * IN2M / 2.0
    P = pitch_in * IN2M
    Omega = rpm * 2.0 * math.pi / 60.0
    if Omega <= 0 or R <= 0:
        return 0.0, 0.0
    chord = SOLIDITY * math.pi * R / max(n_blades, 1)     # constant-chord approx from solidity
    dr = R * (1.0 - HUB_FRAC) / N_STRIPS
    T = 0.0
    Q = 0.0
    for i in range(N_STRIPS):
        r = R * HUB_FRAC + (i + 0.5) * dr
        beta = math.atan2(P, 2.0 * math.pi * r)           # geometric pitch angle at this radius
        Ut = Omega * r                                     # tangential speed
        # solve induced axial velocity v_i by BE<->momentum balance (fixed-point)
        vi = 2.0
        for _ in range(N_INFLOW):
            Ua = V_axial + vi
            phi = math.atan2(Ua, Ut)
            W2 = Ua * Ua + Ut * Ut
            alpha = beta - phi
            cl, cd = _cl_cd(alpha)
            # Prandtl tip loss
            f = (n_blades / 2.0) * (R - r) / (r * math.sin(phi) + 1e-6)
            F = (2.0 / math.pi) * math.acos(math.exp(-abs(f))) if f > 1e-6 else 1.0
            F = max(F, 1e-3)
            dT_be = 0.5 * rho * W2 * chord * n_blades * (cl * math.cos(phi) - cd * math.sin(phi))
            # momentum vs blade-element are both PER UNIT LENGTH here (no dr): dT/dr = 4 pi r rho Ua vi F
            denom = 4.0 * math.pi * r * rho * max(Ua, 1e-3) * F
            vi_new = dT_be / (denom + 1e-9)               # vi = (dT_be/dr) / (4 pi r rho Ua F)
            vi = 0.7 * vi + 0.3 * max(vi_new, 0.0)
        Ua = V_axial + vi
        phi = math.atan2(Ua, Ut)
        W2 = Ua * Ua + Ut * Ut
        alpha = beta - phi
        cl, cd = _cl_cd(alpha)
        dL = 0.5 * rho * W2 * chord * cl
        dD = 0.5 * rho * W2 * chord * cd
        dT = n_blades * (dL * math.cos(phi) - dD * math.sin(phi)) * dr
        dQ = n_blades * (dL * math.sin(phi) + dD * math.cos(phi)) * r * dr
        T += dT
        Q += dQ
    return max(T, 0.0), max(Q, 0.0)


def shaft_power(D_in, pitch_in, n_blades, rpm, V_axial=0.0, rho=RHO0):
    _, Q = thrust_torque(D_in, pitch_in, n_blades, rpm, V_axial, rho)
    return Q * rpm * 2.0 * math.pi / 60.0


if __name__ == "__main__":
    print("BEMT prop check (catalog rotor thrust 27-84 N):")
    for D, P, rpm in [(13, 6, 6000), (15, 8, 5000), (18, 10, 4000), (22, 12, 3200), (9, 5, 9000)]:
        T, Q = thrust_torque(D, P, 2, rpm)
        Pw = Q * rpm * 2 * math.pi / 60.0
        FM = (T ** 1.5 / math.sqrt(2 * RHO0 * math.pi * (D * IN2M / 2) ** 2)) / (Pw + 1e-9)
        print(f"  {D}x{P} @ {rpm}rpm:  T={T:5.1f} N  Q={Q:4.2f} Nm  P={Pw/1000:4.2f} kW  FM={FM:.2f}")
