r"""Our own 6-DOF Flight Dynamics Model — the specimen's dynamics, driven by OUR physics.

This is layer-6 (Dynamics) made real: a rigid-body integrator whose mass, inertia and per-motor
thrust/torque come from the forge engine (the same physics the pipeline designs against). It is
standalone and unit-testable (hover equilibrium, control response); the ArduPilot SITL JSON bridge wraps
this core so `arducopter --model JSON` flies THIS specimen instead of a generic quad.

Frames: NED world, FRD body (x fwd, y right, z down). Attitude = scalar-first quaternion [w,x,y,z].
Thrust acts along body -z (up). Reduced models feed it; CFD/FEA refine the coefficients (CdA, thrust).
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

from uav import build_uav, capabilities, G          # noqa: E402
from solve import solve                              # noqa: E402

RHO = 1.225


def quat_to_R(q):
    w, x, y, z = q
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y)],
        [2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x)],
        [2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y)]])


def quat_mul(a, b):
    aw, ax, ay, az = a; bw, bx, by, bz = b
    return np.array([aw*bw-ax*bx-ay*by-az*bz,
                     aw*bx+ax*bw+ay*bz-az*by,
                     aw*by-ax*bz+ay*bw+az*bx,
                     aw*bz+ax*by-ay*bx+az*bw])


def mass_properties(cfg, mech="rotor", CdA=0.02):
    """Mass, inertia tensor (diagonal), motor geometry and per-motor max thrust — from the forge engine."""
    sysm = build_uav(cfg, propulsion_mechanism=mech)
    bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    cap = capabilities(sysm, bus)
    bd = {s.name: s.state.get("mass", 0.0) for s in sysm.subsystems}
    n = int(cfg["n_rotors"]); L = cfg["L_arm"]
    m_motor = max(bd.get("propulsion", 0.3) / n, 0.02)
    m_ctr = bd.get("energy", 0.3) + bd.get("structure", 0.4)
    m_pay = bd.get("payload", cfg.get("payload", 0.6))
    ang = [math.radians(45 + i * 360 / n) for i in range(n)]
    pos = [(L*math.cos(a), L*math.sin(a), 0.0) for a in ang]     # FRD motor positions
    Ixx = Iyy = Izz = 0.0
    for (x, y, z) in pos:
        Ixx += m_motor*(y*y+z*z); Iyy += m_motor*(x*x+z*z); Izz += m_motor*(x*x+y*y)
    rc = max(0.05, 0.28*L)                                       # central body as a lumped disk
    Ixx += m_ctr*rc*rc/4; Iyy += m_ctr*rc*rc/4; Izz += m_ctr*rc*rc/2
    px, pz = rc*1.1, -0.05                                       # seeker payload, forward + below
    Ixx += m_pay*pz*pz; Iyy += m_pay*(px*px+pz*pz); Izz += m_pay*px*px
    return {"mass": cap["mass"], "I": np.array([Ixx, Iyy, Izz]), "pos": pos, "ang": ang,
            "T_max_motor": cap["thrust"]/n, "CdA": CdA, "thrust_full": cap["thrust"]}


class FDM:
    def __init__(self, cfg, mech="rotor", CdA=0.02):
        p = mass_properties(cfg, mech, CdA)
        self.m = p["mass"]; self.I = p["I"]; self.pos = p["pos"]
        self.T_max = p["T_max_motor"]; self.CdA = p["CdA"]
        self.n = len(self.pos)
        self.spin = [(+1 if i % 2 == 0 else -1) for i in range(self.n)]   # yaw reaction sign
        self.kq = 0.02                                          # torque/thrust arm (m), effective
        self.reset()

    def reset(self):
        self.pos_ned = np.zeros(3)
        self.vel_ned = np.zeros(3)
        self.q = np.array([1.0, 0, 0, 0])
        self.omega = np.zeros(3)
        self.a_ned = np.array([0, 0, 0.0])
        self.t = 0.0

    def hover_throttle(self):
        return math.sqrt((self.m*G/self.n) / self.T_max)

    def _fm(self, u):
        u = np.clip(np.asarray(u, float), 0, 1)
        T = self.T_max * u**2                                    # rotor thrust ~ rpm^2 ~ throttle^2
        Fz = -float(np.sum(T))                                   # body up = -z
        Mx = -sum(self.pos[i][1]*T[i] for i in range(self.n))
        My = sum(self.pos[i][0]*T[i] for i in range(self.n))
        Mz = sum(self.spin[i]*self.kq*T[i] for i in range(self.n))
        return np.array([0, 0, Fz]), np.array([Mx, My, Mz])

    def step(self, u, dt):
        R = quat_to_R(self.q)                                    # body -> NED
        Fb, M = self._fm(u)
        vb = R.T @ self.vel_ned                                  # drag in body frame
        Fb = Fb - 0.5*RHO*self.CdA*np.abs(vb)*vb
        self.a_ned = R @ (Fb/self.m) + np.array([0, 0, G])       # gravity +z (down)
        self.vel_ned = self.vel_ned + self.a_ned*dt
        self.pos_ned = self.pos_ned + self.vel_ned*dt
        wdot = (M - np.cross(self.omega, self.I*self.omega)) / self.I
        self.omega = self.omega + wdot*dt
        self.q = self.q + 0.5*quat_mul(self.q, np.array([0, *self.omega]))*dt
        self.q = self.q / np.linalg.norm(self.q)
        self.t += dt

    def euler_deg(self):
        w, x, y, z = self.q
        roll = math.atan2(2*(w*x+y*z), 1-2*(x*x+y*y))
        pitch = math.asin(max(-1, min(1, 2*(w*y-z*x))))
        yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
        return np.degrees([roll, pitch, yaw])

    def imu(self):
        """Body-frame gyro + accelerometer (specific force) — what the JSON bridge sends to SITL."""
        R = quat_to_R(self.q)
        accel_body = R.T @ (self.a_ned - np.array([0, 0, G]))
        return self.omega.copy(), accel_body


# ------------------------------------------------------------------ standalone verification
if __name__ == "__main__":
    cfg = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)
    fdm = FDM(cfg, CdA=0.0115)     # CdA from the CFD run
    uh = fdm.hover_throttle()
    print(f"mass {fdm.m:.2f} kg | inertia Ixx,Iyy,Izz = {fdm.I.round(4)} kg·m^2 | "
          f"T_max/motor {fdm.T_max:.1f} N | hover throttle {uh:.3f}")

    # Test A: hover hold — level attitude, altitude steady
    fdm.reset()
    for _ in range(600):
        fdm.step([uh]*4, 0.004)
    r, p, y = fdm.euler_deg()
    print(f"\n[A] hover 2.4s: altitude {-fdm.pos_ned[2]:+.3f} m | vz {-fdm.vel_ned[2]:+.3f} m/s | "
          f"roll {r:+.2f} pitch {p:+.2f} deg  -> {'STABLE' if abs(fdm.pos_ned[2])<0.3 and abs(r)<1 else 'DRIFT'}")

    # Test B: roll command — differential throttle across y should produce a roll rate of the right sign
    fdm.reset()
    u = [uh*(1.15 if fdm.pos[i][1] < 0 else 0.85) for i in range(4)]   # more thrust on y<0 -> +roll
    for _ in range(60):
        fdm.step(u, 0.004)
    print(f"[B] roll cmd 0.24s: p={fdm.omega[0]:+.2f} rad/s roll_rate, roll angle {fdm.euler_deg()[0]:+.1f} deg "
          f"-> {'RESPONDS (+roll)' if fdm.omega[0] > 0.1 else 'no/!wrong response'}")

    # Test C: climb — throttle above hover climbs
    fdm.reset()
    for _ in range(250):
        fdm.step([uh*1.1]*4, 0.004)
    print(f"[C] +10% throttle 1s: climb {-fdm.pos_ned[2]:+.2f} m -> {'CLIMBS' if -fdm.pos_ned[2] > 0.1 else 'no'}")
