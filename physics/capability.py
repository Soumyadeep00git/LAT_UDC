"""ARCHITECTURE 2 — decouple the capability from the component.

The tool does not reason about "a battery" or "a prop". It reasons about CAPABILITIES a mission demands
(store energy, deliver power, make thrust, carry a load) and PROVIDERS that each honor one hard physical
invariant and cost mass. The question it asks at every boundary:

    is this boundary PHYSICS (honor it) or CONVENTION (cross it)?

HARD boundaries (invariants — cannot be crossed without new physics):
  energy   : specific energy <= rho_E            (chemistry ceiling, here 400 Wh/kg)
  thrust   : T <= FM * (2 rho_air A)^(1/2) P^(1/2)... momentum theory (disk area A, power P)
  power    : delivered power costs mass ~ P / power_density   (converter/material)
  structure: stress <= sigma_allow                (material strength)

SOFT boundaries (component conventions — the tool is free to cross):
  "energy lives in a LiPo pack"      -> any store at rho_E; the PACK is not sacred, the DENSITY is
  "thrust comes from a prop on an arm"-> the DISK AREA is free; bigger/ducted/more disks are allowed
  "it is a quad (4 rotors)"          -> rotor count / topology free

Given the capabilities the mission needs, allocate min-mass providers. Crossing a soft boundary (e.g.
letting disk area grow past what an arm-mounted prop allows) can PROVIDE a capability the component class
could not — so the output y stops being bounded by the class of x.
"""
from __future__ import annotations

import math

G = 9.80665
RHO_AIR = 1.225

# --- hard invariants ---
WH_PER_KG = 400.0        # energy density ceiling  [Wh/kg]   HARD
FM = 0.70                # momentum-theory figure of merit
POWER_DENSITY = 4000.0   # deliverable power per mass [W/kg] HARD-ish (converter/material)
SIGMA_SPEC = 218750.0    # specific strength sigma/rho [N.m/kg] HARD (carbon)
K_DISK = 0.9             # areal mass of a thrust disk (blades+hub) [kg/m^2]
PAYLOAD = 0.5            # seeker + warhead


def hover_power(mass, A):
    """Momentum-theory power to hover with total disk area A."""
    return (mass * G) ** 1.5 / (FM * math.sqrt(2.0 * RHO_AIR * A))


def thrust_power(T, A):
    """Momentum-theory power to make thrust T through disk area A."""
    return T ** 1.5 / (FM * math.sqrt(2.0 * RHO_AIR * A))


def allocate(a_req, endur_s, A, L, cruise_power=0.0):
    """Min info needed: required agility a_req [m/s^2], loiter endurance, disk area A, moment arm L.
    Solve the mass fixed point (thrust to pull a_req depends on mass, which depends on the providers)."""
    mass = 3.0
    conv = False
    for _ in range(120):
        T = mass * math.sqrt(a_req * a_req + G * G)     # thrust to pull a_req while holding weight
        n_g = T / (mass * G)
        P_size = thrust_power(T, A) + cruise_power        # sizing power (peak maneuver)
        P_hover = hover_power(mass, A)
        E_Wh = P_hover * endur_s / 3600.0
        m_E = E_Wh / WH_PER_KG                             # energy provider
        m_P = P_size / POWER_DENSITY                       # power provider
        m_disk = K_DISK * A                               # thrust-surface provider
        m_struct = 0.25 + 0.004 * T * (1.0 + n_g) * L     # structure provider (material invariant)
        m_new = m_E + m_P + m_disk + m_struct + PAYLOAD
        if m_new > 200.0 or not math.isfinite(m_new):     # mass runs away -> class can't provide it
            return {"mass": math.inf, "feasible": False, "A": A}
        if abs(m_new - mass) < 1e-3:
            mass = m_new; conv = True; break
        mass = 0.6 * mass + 0.4 * m_new
    if not conv:
        return {"mass": math.inf, "feasible": False, "A": A}
    return {"mass": mass, "feasible": True, "T": T, "P_size": P_size, "E_Wh": E_Wh, "A": A,
            "m_E": m_E, "m_P": m_P, "m_disk": m_disk, "m_struct": m_struct}


def min_mass_over_disk(a_req, endur_s, L, A_lo, A_hi, n=60):
    """Provide the capability at least mass by choosing disk area A in [A_lo, A_hi] (golden-ish scan)."""
    best = None
    for i in range(n):
        A = A_lo * (A_hi / A_lo) ** (i / (n - 1))
        r = allocate(a_req, endur_s, A, L)
        if r.get("feasible") and (best is None or r["mass"] < best["mass"]):
            best = r
    return best


def quad_disk_area(D_in, N=4):
    """Disk area a conventional arm-mounted quad can present (soft-boundary DEFAULT)."""
    R = D_in * 0.0254 / 2.0
    return N * math.pi * R * R


# --- forward-flight capability: "sustain speed v" — provided two ways, the class-crossing lever ---
CD_QUAD = 0.8            # bluff multirotor drag coefficient
LD_WING = 12.0          # lift-to-drag of a modest wing (the crossed provider)
ETA_PROP = 0.7          # forward-flight propulsive efficiency


def cruise_power(v, weight, mode, frontal_A=0.05):
    """Power to hold level flight at speed v [W]. mode='rotor' (drag on a bluff body you must thrust
    against) or 'wing' (lift carries weight; you only push against induced+parasite drag, L/D)."""
    if mode == "rotor":
        drag = 0.5 * RHO_AIR * v * v * CD_QUAD * frontal_A
        thrust = math.hypot(drag, weight)          # must vector thrust to both hold weight and push
        return thrust * v / ETA_PROP
    else:  # wing
        drag = weight / LD_WING + 0.5 * RHO_AIR * v * v * 0.02 * frontal_A
        return drag * v / ETA_PROP


def max_speed(P_avail, weight, mode, frontal_A=0.05):
    lo, hi = 1.0, 5.0
    while hi < 300 and cruise_power(hi, weight, mode, frontal_A) < P_avail:
        hi *= 1.4
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if cruise_power(mid, weight, mode, frontal_A) < P_avail:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


if __name__ == "__main__":
    a_req = 4.0 * G          # feasible agility
    endur = 600.0            # 10 min loiter
    print(f"Provide a_req = {a_req/G:.0f} g + {endur/60:.0f} min loiter:\n")
    default = allocate(a_req, endur, quad_disk_area(18), 0.45)   # arm-mounted 18in quad
    crossed = min_mass_over_disk(a_req, endur, 0.45, 0.3, 8.0)
    for lbl, r in [("DEFAULT 18in quad", default), ("CROSSED free disk", crossed)]:
        if not r or not r.get("feasible"):
            print(f"  {lbl}: INFEASIBLE"); continue
        print(f"  {lbl}: A={r['A']:.2f}m^2  mass={r['mass']:.2f}kg  "
              f"[energy {r['m_E']:.2f} | power {r['m_P']:.2f} | disk {r['m_disk']:.2f} | "
              f"struct {r['m_struct']:.2f} | pay {PAYLOAD}]  P={r['P_size']/1000:.1f}kW")
