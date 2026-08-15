"""The coupled fixed-point solver — spec section 2.

Given a physical config it resolves the whole platform to consistency: the powertrain (battery sag <->
motor <-> prop) is solved at each throttle, its static thrust sets TWR and the maneuver load factor, the
structure is sized for that load (adding mass & inertia), the new mass changes TWR... iterate until the
mass stops moving. Then it reads off the capability envelope the mission cares about.

This REPLACES the first-order drone.py. v_max/a_max are no longer knobs or one-line formulas — they fall
out of BEMT + a real motor + a sagging battery + a load-sized structure.

Speed: BEMT is tabulated once per config (PropTable); every bisection then interpolates.

    st = solve(Config(...))   ->  PlatformState(mass, TWR, a_max, v_max, endurance, inertia, ...)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import prop
import aero
from motor import Motor, solve as motor_solve
from battery import Battery
import structure

G = 9.80665
IN2M = 0.0254

MOTOR_KG_PER_A = 0.0035     # motor mass per amp of thermal rating (catalog ~2-4 g/A)
MOTOR_R_COEF = 1.8          # winding resistance Rm = coef / I_max
MOTOR_I0 = 1.0
AVIONICS_KG = 0.10


class PropTable:
    """BEMT thrust/torque tabulated on an (rpm, V_axial) grid, then bilinear-interpolated — the solver
    hits the prop thousands of times at one geometry, so tabulating turns ~10 s into a few dozen BEMT calls."""

    def __init__(self, D_in, pitch_in, n_blades, rpm_max, v_max=70.0, n_rpm=24, n_v=8):
        self.rpm = [rpm_max * i / (n_rpm - 1) for i in range(n_rpm)]
        self.V = [v_max * j / (n_v - 1) for j in range(n_v)]
        self.T = [[0.0] * n_v for _ in range(n_rpm)]
        self.Q = [[0.0] * n_v for _ in range(n_rpm)]
        for i, r in enumerate(self.rpm):
            for j, v in enumerate(self.V):
                t, q = prop.thrust_torque(D_in, pitch_in, n_blades, r, v)
                self.T[i][j], self.Q[i][j] = t, q

    def _interp(self, grid, rpm, V):
        rs, vs = self.rpm, self.V
        rpm = max(rs[0], min(rs[-1], rpm)); V = max(vs[0], min(vs[-1], V))
        i = 0
        while i < len(rs) - 2 and rs[i + 1] < rpm: i += 1
        j = 0
        while j < len(vs) - 2 and vs[j + 1] < V: j += 1
        tr = (rpm - rs[i]) / (rs[i + 1] - rs[i] + 1e-9)
        tv = (V - vs[j]) / (vs[j + 1] - vs[j] + 1e-9)
        a = grid[i][j] * (1 - tv) + grid[i][j + 1] * tv
        b = grid[i + 1][j] * (1 - tv) + grid[i + 1][j + 1] * tv
        return a * (1 - tr) + b * tr

    def thrust(self, rpm, V=0.0): return self._interp(self.T, rpm, V)
    def torque(self, rpm, V=0.0): return self._interp(self.Q, rpm, V)


@dataclass
class Config:
    D_in: float
    pitch_in: float
    Kv: float
    I_max: float            # motor thermal current [A] -> sets motor size
    S: float
    cap_mAh: float
    C_rate: float
    L_arm: float
    N_rotors: int = 4
    n_blades: int = 2
    payload_kg: float = 0.5


@dataclass
class PlatformState:
    mass: float
    T_rotor: float
    TWR: float
    a_max: float
    v_max: float
    endurance_s: float
    Izz: float
    Ixx: float
    hover_throttle: float
    converged: bool
    masses: dict


def _motor_of(cfg, batt):
    I_eff = min(cfg.I_max, batt.I_burst / cfg.N_rotors)
    return Motor(Kv=cfg.Kv, Rm=MOTOR_R_COEF / cfg.I_max, I0=MOTOR_I0, I_max=I_eff)


def _powertrain(cfg, batt, motor, table, throttle, V_axial):
    """battery-sag <-> motor-prop at a throttle. Returns (T_rotor, op, I_total)."""
    V_bus = batt.V_oc
    op = None
    for _ in range(12):
        op = motor_solve(V_bus, motor, lambda rpm: table.torque(rpm, V_axial), throttle)
        V_new = batt.v_bus(cfg.N_rotors * op.current)
        if abs(V_new - V_bus) < 0.05:
            break
        V_bus = 0.6 * V_bus + 0.4 * V_new
    return table.thrust(op.rpm, V_axial), op, cfg.N_rotors * op.current


def _hover(cfg, batt, motor, table, weight):
    lo, hi = 0.0, 1.0
    for _ in range(20):
        th = 0.5 * (lo + hi)
        T, _, _ = _powertrain(cfg, batt, motor, table, th, 0.0)
        if cfg.N_rotors * T > weight: hi = th
        else: lo = th
    th = 0.5 * (lo + hi)
    _, op, _ = _powertrain(cfg, batt, motor, table, th, 0.0)
    return th, op.P_elec * cfg.N_rotors


def _v_max(cfg, batt, motor, table, mass):
    W = mass * G
    def excess_minus_drag(V):
        T, _, _ = _powertrain(cfg, batt, motor, table, 1.0, V)
        Ttot = cfg.N_rotors * T
        F_fwd = math.sqrt(max(Ttot * Ttot - W * W, 0.0))
        return F_fwd - aero.drag(V, cfg.N_rotors, cfg.L_arm, cfg.D_in)
    if excess_minus_drag(1.0) <= 0:
        return 0.0
    lo, hi = 1.0, 5.0
    while hi < 120 and excess_minus_drag(hi) > 0:
        hi *= 1.5
    for _ in range(22):
        mid = 0.5 * (lo + hi)
        if excess_minus_drag(mid) > 0: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)


def solve(cfg: Config) -> PlatformState:
    batt = Battery(cfg.S, cfg.cap_mAh, cfg.C_rate)
    motor = _motor_of(cfg, batt)
    rpm_max = cfg.Kv * batt.V_oc * 1.05
    table = PropTable(cfg.D_in, cfg.pitch_in, cfg.n_blades, rpm_max)

    m_batt = batt.mass
    m_motor_each = MOTOR_KG_PER_A * cfg.I_max
    m_motors = cfg.N_rotors * m_motor_each
    m_prop_each = 0.0008 * cfg.D_in ** 2
    m_props = cfg.N_rotors * m_prop_each
    fixed = m_batt + m_motors + m_props + cfg.payload_kg + AVIONICS_KG

    T_rotor, op, I_total = _powertrain(cfg, batt, motor, table, 1.0, 0.0)
    T_total = cfg.N_rotors * T_rotor

    mass = fixed + 0.8
    st = None
    conv = False
    for _ in range(20):
        TWR = T_total / (mass * G)
        n_g = max(TWR, 1.0)
        comps = {"motor": m_motor_each, "prop": m_prop_each, "battery": m_batt, "payload": cfg.payload_kg}
        st = structure.solve(T_rotor, cfg.N_rotors, cfg.L_arm, n_g, comps)
        m_new = fixed + st.mass
        if abs(m_new - mass) < 0.005:
            conv = True; mass = m_new; break
        mass = 0.5 * mass + 0.5 * m_new

    TWR = T_total / (mass * G)
    a_max = G * math.sqrt(max(TWR * TWR - 1.0, 0.0))
    v_max = _v_max(cfg, batt, motor, table, mass)
    hov_th, P_hover = _hover(cfg, batt, motor, table, mass * G)
    endurance = batt.usable_J / P_hover if P_hover > 1 else 0.0

    masses = {"battery": m_batt, "motors": m_motors, "props": m_props,
              "structure": st.mass, "payload": cfg.payload_kg, "avionics": AVIONICS_KG}
    return PlatformState(mass, T_rotor, TWR, a_max, v_max, endurance,
                         st.Izz, st.Ixx, hov_th, conv, masses)


if __name__ == "__main__":
    import time
    print("Coupled solver (BEMT-tabulated):\n")
    cfgs = [
        ("small/fast", Config(D_in=9,  pitch_in=5,  Kv=420, I_max=35, S=6,  cap_mAh=3000, C_rate=80, L_arm=0.18)),
        ("mid",        Config(D_in=13, pitch_in=6,  Kv=300, I_max=45, S=6,  cap_mAh=5000, C_rate=60, L_arm=0.30)),
        ("big/agile",  Config(D_in=18, pitch_in=10, Kv=190, I_max=60, S=10, cap_mAh=8000, C_rate=45, L_arm=0.45)),
        ("hi-pitch",   Config(D_in=15, pitch_in=13, Kv=350, I_max=55, S=10, cap_mAh=6000, C_rate=60, L_arm=0.35)),
    ]
    t0 = time.time()
    for name, c in cfgs:
        s = solve(c)
        print(f"{name:11s} mass={s.mass:4.2f}kg TWR={s.TWR:4.2f} a_max={s.a_max/G:4.2f}g "
              f"v_max={s.v_max:4.1f} endur={s.endurance_s:4.0f}s conv={s.converged}")
    print(f"\n{(time.time()-t0)/len(cfgs)*1000:.0f} ms per solve")
