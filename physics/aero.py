"""Aero model — body drag and forward-flight trim (2-D level).

For the 2-D engagement this stays deliberately at drag + trim; the full 6-DOF force/moment coefficient
tables belong to the dynamics build (spec section 6). In forward flight the platform tilts by theta so
the thrust's horizontal component overcomes drag while its vertical component holds weight:
    T sin(theta) = drag(V),   T cos(theta) = W
so the top speed is where the available forward thrust equals drag at that speed (and the prop's own
thrust is falling with airspeed via the BEMT advance ratio).
"""
from __future__ import annotations

import math

RHO0 = 1.225
CD_BODY = 0.8           # bluff-ish multirotor drag coefficient
IN2M = 0.0254


def frontal_area(N_rotors, L, D_in, payload_area=0.015):
    """Estimated frontal area [m^2]: central body + exposed arms/booms."""
    d_arm = 2 * max(0.008, 0.035 * L)
    arms = N_rotors * (L * d_arm) * 0.5              # arms are partly edge-on
    return payload_area + arms + 0.01


def drag(V, N_rotors, L, D_in, rho=RHO0):
    A = frontal_area(N_rotors, L, D_in)
    return 0.5 * rho * V * V * CD_BODY * A


def trim_tilt(V, weight, N_rotors, L, D_in, rho=RHO0):
    """Tilt angle [rad] and thrust required to hold level flight at speed V."""
    d = drag(V, N_rotors, L, D_in, rho)
    theta = math.atan2(d, weight)
    T_req = math.hypot(d, weight)
    return theta, T_req


if __name__ == "__main__":
    print("Aero check (drag vs speed for a quad, L=0.3, 13in):")
    for V in [10, 20, 30, 40, 50]:
        d = drag(V, 4, 0.3, 13)
        th, Treq = trim_tilt(V, 5 * 9.81, 4, 0.3, 13)
        print(f"  V={V:2d} m/s:  drag={d:5.1f} N  tilt={math.degrees(th):4.1f} deg  T_req={Treq:5.1f} N")
