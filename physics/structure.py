"""Structures model — arm/frame mass and the inertia tensor, sized by the maneuver loads.

Each arm is a carbon cantilever tube carrying its rotor's thrust at the tip. Under a maneuver of load
factor n_g the effective tip load is T*(1+n_g), giving a root bending moment M = T*(1+n_g)*L. We size the
tube wall so bending stress stays under the allowable (with a safety factor covering stiffness/fatigue),
then add motor mounts and a central frame. This is THE structural coupling: demanding more agility (n_g)
thickens the arms -> more mass & inertia -> less agility. The solver closes that loop.

Also returns the inertia tensor from the mass layout (motors/props at radius L, battery/payload central) —
the quantity that sets real 6-DOF turn-rate later.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

RHO_C = 1600.0          # carbon composite density [kg/m^3]
SIGMA_ALLOW = 350e6     # design bending stress [Pa]
SF = 4.0                # safety factor (covers stiffness/vibration/fatigue, not just yield)
MOUNT_KG = 0.05         # motor mount + hub per arm
FRAME0 = 0.15           # base center-frame mass
K_FRAME = 0.0010        # frame growth with total thrust [kg per N]


@dataclass
class StructResult:
    mass: float
    Ixx: float
    Iyy: float
    Izz: float


def arm_mass(T_rotor, L, n_g):
    """Mass of one carbon-tube arm sized for the maneuver bending load [kg]."""
    ro = max(0.008, 0.035 * L)                       # tube outer radius (min 8 mm)
    M = T_rotor * (1.0 + n_g) * L                     # root bending moment
    Z = M / SIGMA_ALLOW                               # required section modulus
    t = Z / (math.pi * ro * ro + 1e-12)               # thin-wall thickness for that modulus
    t = max(t, 0.0004)                                # min manufacturable wall 0.4 mm
    m_tube = RHO_C * (2.0 * math.pi * ro * t) * L
    return SF_wall(m_tube) + MOUNT_KG


def SF_wall(m):
    return SF * m


def solve(T_rotor, N_rotors, L, n_g, comp_masses):
    """comp_masses: dict with per-item masses {motor, prop, battery, payload, avionics}. Returns mass+inertia."""
    m_arms = N_rotors * arm_mass(T_rotor, L, n_g)
    m_frame = FRAME0 + K_FRAME * N_rotors * T_rotor
    m_struct = m_arms + m_frame

    # inertia: motors+props at radius L; battery/payload/avionics near center (r_c); arms as rods
    m_end = comp_masses.get("motor", 0.0) + comp_masses.get("prop", 0.0)
    r_c = 0.06
    m_center = comp_masses.get("battery", 0.0) + comp_masses.get("payload", 0.0) + comp_masses.get("avionics", 0.0)
    m_arm_each = arm_mass(T_rotor, L, n_g)
    Izz = N_rotors * m_end * L * L + m_center * r_c * r_c + N_rotors * m_arm_each * L * L / 3.0
    Ixx = 0.5 * Izz                                   # planar quad: roll/pitch ~ half of yaw
    Iyy = Ixx
    return StructResult(m_struct, Ixx, Iyy, Izz)


if __name__ == "__main__":
    print("Structure check (arm mass grows with maneuver load n_g):")
    comps = {"motor": 0.15, "prop": 0.05, "battery": 0.5, "payload": 0.5}
    for T, L, ng in [(50, 0.30, 1), (50, 0.30, 5), (80, 0.45, 5)]:
        r = solve(T, 4, L, ng, comps)
        print(f"  T={T}N L={L*100:.0f}cm n_g={ng}:  m_struct={r.mass:4.2f}kg  "
              f"Izz={r.Izz*1000:5.1f} g.m^2  Ixx={r.Ixx*1000:5.1f}")
