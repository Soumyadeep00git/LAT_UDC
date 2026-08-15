"""BLDC motor model — solved to equilibrium against the prop.

A motor at bus voltage V spins up until its torque equals the prop's torque demand. Two equations:
    torque:   tau = Kt (I - I0)            Kt = 60/(2 pi Kv)   [N.m/A]
    voltage:  V = I Rm + omega/Kv_rad      back-EMF rises with rpm
At steady state motor torque = prop torque Q(rpm). Given V and the prop's Q(rpm) curve we root-find the
rpm where the voltage equation closes. Current is then capped at the thermal limit I_max (if hit, the
motor is current-limited and we back off throttle to sit exactly at I_max).

    op = solve(V_bus, motor, torque_fn)   # torque_fn(rpm) -> prop shaft torque [N.m]
    -> OperatingPoint(rpm, current, P_elec, P_mech, eta, limited)
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Motor:
    Kv: float           # rpm/V
    Rm: float           # winding resistance [ohm]
    I0: float           # no-load current [A]
    I_max: float        # thermal current limit [A]

    @property
    def Kt(self):
        return 60.0 / (2.0 * math.pi * self.Kv)     # N.m per A


@dataclass
class OperatingPoint:
    rpm: float
    current: float
    P_elec: float
    P_mech: float
    eta: float
    limited: bool       # True if the thermal current limit bound the solution


def _voltage_residual(rpm, V, m: Motor, torque_fn):
    """V_required(rpm) - V. Zero at the operating point."""
    Q = torque_fn(rpm)
    I = Q / m.Kt + m.I0
    return I * m.Rm + rpm / m.Kv - V, I, Q


def solve(V_bus, m: Motor, torque_fn, throttle=1.0):
    """Root-find the equilibrium rpm at effective voltage throttle*V_bus, then apply the thermal cap."""
    V = throttle * V_bus
    hi = m.Kv * V                                    # no-load rpm (upper bracket)
    lo = 0.0
    # residual is monotincreasing in rpm (both I*Rm via Q and back-EMF grow) -> bisection
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        res, I, Q = _voltage_residual(mid, V, m, torque_fn)
        if res > 0:
            hi = mid
        else:
            lo = mid
    rpm = 0.5 * (lo + hi)
    _, I, Q = _voltage_residual(rpm, V, m, torque_fn)

    limited = False
    if I > m.I_max:                                  # thermal cap: back off throttle to sit at I_max
        limited = True
        # find throttle where current == I_max
        tlo, thi = 0.0, throttle
        for _ in range(30):
            tm = 0.5 * (tlo + thi)
            Vt = tm * V_bus
            hh, ll = m.Kv * Vt, 0.0
            for _ in range(30):
                md = 0.5 * (hh + ll)
                r, _, _ = _voltage_residual(md, Vt, m, torque_fn)
                if r > 0: hh = md
                else: ll = md
            rr = 0.5 * (hh + ll)
            _, Ii, _ = _voltage_residual(rr, Vt, m, torque_fn)
            if Ii > m.I_max: thi = tm
            else: tlo = tm
        Vt = 0.5 * (tlo + thi) * V_bus
        hh, ll = m.Kv * Vt, 0.0
        for _ in range(40):
            md = 0.5 * (hh + ll)
            r, _, _ = _voltage_residual(md, Vt, m, torque_fn)
            if r > 0: hh = md
            else: ll = md
        rpm = 0.5 * (hh + ll)
        _, I, Q = _voltage_residual(rpm, Vt, m, torque_fn)
        V = Vt

    omega = rpm * 2.0 * math.pi / 60.0
    P_mech = Q * omega
    P_elec = V * I
    eta = P_mech / P_elec if P_elec > 1e-6 else 0.0
    return OperatingPoint(rpm, I, P_elec, P_mech, eta, limited)


if __name__ == "__main__":
    from prop import thrust_torque

    print("Motor-prop equilibrium check:")
    # a mid custom motor: Kv 350, low resistance, 60A thermal
    m = Motor(Kv=350, Rm=0.03, I0=1.0, I_max=60.0)
    for S, D, P in [(6, 13, 6), (10, 15, 8), (12, 18, 10)]:
        V = 3.7 * S
        op = solve(V, m, lambda rpm: thrust_torque(D, P, 2, rpm)[1])
        T, Q = thrust_torque(D, P, 2, op.rpm)
        tag = " [I-LIMITED]" if op.limited else ""
        print(f"  {S}S {D}x{P}: rpm={op.rpm:5.0f}  I={op.current:4.0f}A  "
              f"T={T:5.1f}N  P_elec={op.P_elec/1000:4.2f}kW  eta={op.eta*100:2.0f}%{tag}")
