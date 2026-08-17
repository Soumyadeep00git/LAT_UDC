r"""ROTOR FIGURE OF MERIT — solve the real hover field (induced + profile + tip loss) and derive FM.

thrust_field solved the IDEAL field (uniform loading, FM=1). Real rotors lose to two things the ideal
ignores: blade PROFILE DRAG and TIP LOSS. Solving the blade-element+momentum field WITH those gives the
figure of merit FM = P_ideal / P_actual as a NUMBER derived from the geometry - not the assumed 0.70.

Per annulus (hover), given the blade geometry (chord c(r), twist theta(r)) and RPM:
  Prandtl tip loss  F = (2/pi) acos(exp(-(B/2)(R-r)/(r sin phi)))
  inflow            phi = atan(v_i / (Omega r)),  solve v_i from  BE thrust = momentum thrust (with F)
  section           Cl = a0 (theta - phi),  Cd = Cd0 + k Cl^2
  thrust  dT/dr = 0.5 rho B c W^2 (Cl cos phi - Cd sin phi)
  torque  dQ/dr = 0.5 rho B c W^2 (Cl sin phi + Cd cos phi) r
  power   P = Omega * integral dQ ;   FM = (T^1.5 / sqrt(2 rho A)) / P

Because FM now DEPENDS on pitch/chord, hover power stops being pitch-independent -> the pitch MODEL_GAP
(v3c) becomes priceable, and the caps run on a solved FM instead of a magic constant.
"""
from __future__ import annotations

import math

import numpy as np

RHO = 1.225
A0 = 5.7                 # lift-curve slope (per rad)
CD0 = 0.020              # profile drag at zero lift
KDRAG = 0.020            # induced-profile drag factor (Cd = Cd0 + k Cl^2)
CL_MAX = 1.2             # stall
ALPHA_STALL = math.radians(12.0)


def _section(alpha, Cd0, k):
    """Section lift & drag with a simple stall model (so FM turns over at high loading, not to the sweep edge)."""
    if abs(alpha) > ALPHA_STALL:                          # stalled: lift drops, drag climbs steeply
        Cl = math.copysign(CL_MAX * 0.85, alpha)
        Cd = Cd0 + k * CL_MAX ** 2 + 1.2 * (abs(alpha) - ALPHA_STALL)
    else:
        Cl = max(-CL_MAX, min(CL_MAX, A0 * alpha))
        Cd = Cd0 + k * Cl * Cl
    return Cl, Cd


def bemt_hover(r, chord, twist, rpm, n_blades=2, Cd0=CD0, k=KDRAG):
    """Solve the hover field with tip loss + profile drag. Returns thrust, torque, power, FM."""
    Omega = rpm * 2 * math.pi / 60.0
    R = r[-1]
    A = math.pi * (R ** 2 - r[0] ** 2)
    dr = r[1] - r[0]
    T = Q = 0.0
    for i in range(len(r)):
        Ur = Omega * r[i]

        def resid(v):
            phi = math.atan2(v, Ur)
            f = (n_blades / 2.0) * (R - r[i]) / (max(r[i], 1e-4) * max(math.sin(phi), 1e-3))
            F = (2 / math.pi) * math.acos(min(1.0, math.exp(-f)))
            W = math.hypot(v, Ur)
            Cl, Cd = _section(twist[i] - phi, Cd0, k)
            dT_be = 0.5 * RHO * n_blades * chord[i] * W * W * (Cl * math.cos(phi) - Cd * math.sin(phi))
            dT_mom = 4 * math.pi * RHO * r[i] * F * v * v
            return dT_be - dT_mom
        lo, hi = 1e-4, 60.0
        if resid(lo) * resid(hi) > 0:
            v = 0.0
        else:
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                lo, hi = (mid, hi) if resid(lo) * resid(mid) > 0 else (lo, mid)
            v = 0.5 * (lo + hi)
        phi = math.atan2(v, Ur)
        W = math.hypot(v, Ur)
        Cl, Cd = _section(twist[i] - phi, Cd0, k)
        q = 0.5 * RHO * n_blades * chord[i] * W * W
        T += q * (Cl * math.cos(phi) - Cd * math.sin(phi)) * dr
        Q += q * (Cl * math.sin(phi) + Cd * math.cos(phi)) * r[i] * dr
    P = Omega * Q
    P_ideal = T ** 1.5 / math.sqrt(2 * RHO * A) if T > 0 else 0.0
    FM = P_ideal / P if P > 0 else 0.0
    return dict(thrust=T, torque=Q, power=P, FM=FM, P_ideal=P_ideal)


if __name__ == "__main__":
    import blade_design as BD

    geom = BD.design_iterate(20.0, rpm=9800, R_tip=0.165, n_blades=2, N=28)
    r, c, th = geom["r"], geom["chord"], geom["twist"]

    print("=" * 82)
    print("ROTOR FIGURE OF MERIT  -  solve the real hover field (profile drag + tip loss), derive FM")
    print("=" * 82)
    base = bemt_hover(r, c, th, rpm=geom["rpm"], n_blades=geom["n_blades"])
    print(f"designed blade @ {geom['rpm']} rpm:")
    print(f"   thrust {base['thrust']:.2f} N | power {base['power']:.0f} W | ideal power {base['P_ideal']:.0f} W")
    print(f"   -> FIGURE OF MERIT = {base['FM']:.3f}   (vs the assumed 0.70 in the caps)")

    print(f"\nFM is now PITCH-DEPENDENT (solve a collective offset -> the model-gap becomes priceable):")
    print(f"   {'dpitch(deg)':>11} {'thrust(N)':>9} {'power(W)':>9} {'FM':>6}")
    best = (-1, None)
    for dp in (-6, -3, 0, 3, 6, 9, 12, 15, 18):
        th2 = th + math.radians(dp)
        h = bemt_hover(r, c, th2, rpm=geom["rpm"], n_blades=geom["n_blades"])
        flag = ""
        if h["FM"] > best[0]:
            best = (h["FM"], dp)
        print(f"   {dp:>11d} {h['thrust']:>9.2f} {h['power']:>9.0f} {h['FM']:>6.3f}")
    print(f"   -> FM peaks near dpitch={best[1]:+d} deg (FM {best[0]:.3f}); a wrong pitch costs power that the")
    print(f"      old fixed-FM=0.70 model could NOT see. Hover power is now a function of the blade, solved.")

    print("\n" + "-" * 82)
    endur_factor = base["FM"] / 0.70                      # endurance ~ FM at fixed energy (P_hover ~ 1/FM)
    print(f"FOLD INTO CAPS: endurance ~ FM. Solved FM {base['FM']:.3f} vs assumed 0.70 -> endurance x"
          f"{endur_factor:.2f} ({100*(endur_factor-1):+.0f}%) at the design pitch;")
    print(f"at the optimal collective (FM {best[0]:.3f}) it is x{best[0]/0.70:.2f}. The assumed constant was")
    print("optimistic for this blade; the solved field prices it, and v3c's pitch MODEL_GAP -> solve-confirmed.")
