r"""Ducted-annular propulsor — the manufacturable model for V3's transcendent form.

This is the embodiment V3 kept IMAGINING but could not BUILD. A continuous ducted ring fills the airframe
planform annulus, so its effective disk area is the whole annulus (not the sum of discrete rotor circles),
and a shroud recovers tip losses (higher figure of merit). It pays for that with duct structural mass.

Momentum theory (the invariant): hover P = W^1.5 / (FM_duct * sqrt(2 rho A)); inverted for max thrust from
available power, T = (P * FM_duct * sqrt(2 rho A))^(2/3). Larger A -> less hover power AND more thrust per
watt. The tradeoff vs discrete rotors is area-benefit vs duct-mass — so the ring WINS when the planform is
area-limited (which is exactly when V3's field reshape said "fill the annulus").
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

from battery import Battery
from platform_solve import MOTOR_KG_PER_A
import aero

G, RHO, IN2M = 9.80665, 1.225, 0.0254
FM_DUCT = 0.80          # ducted fans recover tip loss -> higher figure of merit than open rotors (~0.70)
ETA = 0.75             # electrical -> mechanical efficiency


def _vmax(T_max, W, L, D_in):
    F = math.sqrt(max(T_max * T_max - W * W, 0.0))
    if F - aero.drag(1.0, 1, L, D_in) <= 0:
        return 0.0
    lo, hi = 1.0, 5.0
    while hi < 150 and (F - aero.drag(hi, 1, L, D_in)) > 0:
        hi *= 1.5
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if (F - aero.drag(mid, 1, L, D_in)) > 0 else (lo, mid)
    return 0.5 * (lo + hi)


DUCT_STATIC_GAIN = 1.15     # a shroud recovers slipstream -> modest static-thrust gain (well-attested)


def ducted_ring_caps(cfg, quad_thrust, quad_vmax):
    """Ducted-annular embodiment. Thrust is GROUNDED in the validated BEMT rotor thrust (quad_thrust) plus
    a modest duct static gain — NOT unconstrained momentum theory. The ring's only honest edge is
    EFFICIENCY: it fills the planform annulus, so its effective disk area is larger -> lower hover power ->
    more endurance. v_max is inherited from the validated forward model (ducted forward flight is
    approximate — flagged as a deficit)."""
    b = Battery(int(cfg["S"]), cfg["cap_mAh"], cfg["C_rate"], wh_per_kg=cfg.get("wh_per_kg", 400.0))
    L = cfg["L_arm"]
    R_frame = L + 0.15
    R_hub = max(0.05, 0.30 * L)
    A = math.pi * (R_frame ** 2 - R_hub ** 2)
    r_m = 0.5 * (R_frame + R_hub); circ = 2 * math.pi * r_m
    duct_mass = 2.0 * circ * 0.04
    m_motor = MOTOR_KG_PER_A * cfg["I_max"] * cfg["n_rotors"]     # same power class as the quad
    m_fan = 0.05 * circ
    m_frame = 0.25 + 0.20 * L
    mass = b.mass + duct_mass + m_motor + m_fan + m_frame + cfg.get("payload", 0.6)
    W = mass * G
    T_max = quad_thrust * DUCT_STATIC_GAIN                        # grounded thrust, modest duct benefit
    twr = T_max / W
    a_max = G * math.sqrt(max(twr * twr - 1.0, 0.0))
    P_hover = W ** 1.5 / (FM_DUCT * math.sqrt(2 * RHO * A))       # the ring's edge: larger A, higher FM
    endurance = b.usable_J / P_hover / 60.0
    return {"a_max_g": a_max / G, "v_max": quad_vmax, "endurance_min": endurance, "mass": mass,
            "TWR": twr, "A_eff": A, "duct_mass": duct_mass, "validated": False,
            "_deficit": ("UNVALIDATED: duct mass underestimated, forward-thrust decay + tip-Mach/torque "
                         "limits not modelled, and ducts trade hover efficiency for compact static thrust "
                         "(a large OPEN rotor is more hover-efficient — that form is within V2's reach). "
                         "Trust needs CFD or constrained duct physics.")}


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    from uav import build_uav, capabilities, G as _G
    from solve import solve
    cfg = dict(D_in=12, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0)
    d = build_uav(cfg); c = capabilities(d, solve(d, seed={"current": 0.0, "total_mass": 4.0}))
    r = ducted_ring_caps(cfg, c["thrust"], c["v_max"])
    print("DUCTED-ANNULAR RING vs DISCRETE QUAD (same airframe + battery)\n")
    print(f"  discrete quad : a_max {c['a_max']/_G:.2f} g | v_max {c['v_max']:.1f} | "
          f"endur {c['endurance']/60:.1f} min | mass {c['mass']:.2f} kg")
    print(f"  ducted ring   : a_max {r['a_max_g']:.2f} g | v_max {r['v_max']:.1f} | "
          f"endur {r['endurance_min']:.1f} min | mass {r['mass']:.2f} kg  "
          f"(A_eff {r['A_eff']:.2f} m^2, duct +{r['duct_mass']:.2f} kg)")
    print(f"\n  ring uses the full planform annulus -> {r['endurance_min']/(c['endurance']/60):.2f}x endurance, "
          f"{r['a_max_g']/(c['a_max']/_G):.2f}x a_max — the transcendent form, now buildable.")
