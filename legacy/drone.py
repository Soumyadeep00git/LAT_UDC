"""A DRONE, broken into buildable features, with a first-order physics model mapping features ->
dynamics. This replaces the abstract (v_max, a_max) knob: those are now DERIVED from real hardware.

FEATURES (the design vector we perturb) — a quad (N=4):
    D_in      prop diameter   [in]
    pitch_in  prop pitch      [in]
    Kv        motor constant  [rpm/V]
    S         battery cells   (voltage = 3.7 S)
    cap_mAh   battery capacity[mAh]
    L_arm     arm length c->motor [m]      (<= 1.0 m, your constraint)

PHYSICS (textbook first-order, calibrated to the real catalog's ranges — NOT a replica of the legacy
axial-inflow model, which we found simple theory can't reproduce; this is a self-consistent model):
    voltage      V   = 3.7 S
    loaded rpm   n   = ETA_RPM * Kv V / 60          [rev/s]   (prop loads motor below no-load)
    prop thrust  T   = Ct rho n^2 D_m^4  per rotor  (blade-element form; Ct rises with pitch/D)
    thrust total     = N T
    TWR          = N T / (m g)
    a_max        = g sqrt(TWR^2 - 1)                 EXACT relation verified in the catalog
    v_max        = min(pitch-speed limit, drag-limited top speed)
    mass         = battery(400 Wh/kg) + motors + props + esc + arms + shell + misc + payload

Every constant below is documented and chosen so a mid design lands in the catalog envelope
(v_max ~20-50 m/s, a_max ~2-5 g, mass ~4-13 kg, T_rotor ~27-84 N).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

G = 9.80665
RHO = 1.225                     # air density [kg/m^3]
N_ROTORS = 4
IN2M = 0.0254

# --- calibrated constants ---
ETA_RPM = 0.75                  # loaded rpm as fraction of no-load (prop drags the motor down)
ETA_PITCH = 0.85               # fraction of geometric pitch speed actually reached (slip)
ETA_MOTOR = 0.72                # electrical -> mechanical efficiency
C_BURST = 60.0                  # battery burst discharge C-rate (documented; a power limiter)
CD_BODY = 0.6                   # drag coefficient of the airframe
WH_PER_KG = 400.0              # battery energy density [Wh/kg]  (your constraint)
PAYLOAD_KG = 0.5                # seeker + proximity warhead (documented; adjustable)
MOTOR_KW_PER_KG = 4.0          # CUSTOM motor power density: a designed motor, not a catalog part.
                                # its power costs mass, so bigger thrust self-limits against the 6 kg budget.

# feature box — BOUNDED TO THE REAL CATALOG (all_candidates.csv observed min/max). P_motor range comes
# from real motor masses (52-351 g) at 4 kW/kg. Everything here is a buildable off-the-shelf part.
BOUNDS = {
    "D_in":     (7.5, 28.0),
    "pitch_in": (2.5, 20.0),
    "Kv":       (85.0, 450.0),
    "S":        (3.0, 12.0),
    "cap_mAh":  (1300.0, 16000.0),
    "L_arm":    (0.12, 1.00),
    "P_motor":  (0.21, 1.40),
}
KEYS = list(BOUNDS.keys())


@dataclass
class Drone:
    D_in: float
    pitch_in: float
    Kv: float
    S: float
    cap_mAh: float
    L_arm: float
    P_motor: float = 1.0            # custom mechanical power per rotor [kW]

    # ---------- physics ----------
    def _ct(self):
        pr = self.pitch_in / self.D_in
        return 0.10 + 0.06 * pr                      # thrust coeff rises modestly with pitch/D

    def _cp(self):
        pr = self.pitch_in / self.D_in
        return 0.045 + 0.06 * pr                     # power coeff rises with pitch/D

    def rev_per_s(self):
        """Loaded rev/s, capped by the LESSER of no-load rpm and what the battery power can spin.

        Without the power cap, blade-element thrust ~ (Kv V)^2 runs away past any real motor. The prop
        shaft power Cp rho n^3 D^5 must be <= the burst electrical power the pack can deliver, which is
        what actually bounds thrust to catalog-realistic values."""
        V = 3.7 * self.S
        n_noload = ETA_RPM * self.Kv * V / 60.0
        P_batt = ETA_MOTOR * V * (C_BURST * self.cap_mAh / 1000.0) / N_ROTORS   # battery-supplied, per rotor
        P_motor = self.P_motor * 1000.0                       # custom motor mech limit, per rotor [W]
        P_rotor = min(P_batt, P_motor)                        # whichever gives out first
        D_m = self.D_in * IN2M
        n_power = (P_rotor / (self._cp() * RHO * D_m ** 5)) ** (1.0 / 3.0)
        return min(n_noload, n_power)

    def thrust_per_rotor(self):
        n = self.rev_per_s()
        D_m = self.D_in * IN2M
        return self._ct() * RHO * n * n * D_m ** 4   # [N]

    @property
    def voltage(self):
        return 3.7 * self.S

    @property
    def energy_Wh(self):
        return self.voltage * self.cap_mAh / 1000.0

    @property
    def mass(self):
        m_batt = self.energy_Wh / WH_PER_KG
        m_motors = N_ROTORS * (self.P_motor / MOTOR_KW_PER_KG)   # custom motor mass = power / density
        m_props = N_ROTORS * (0.0008 * self.D_in ** 2)
        m_esc = N_ROTORS * 0.017
        m_arms = N_ROTORS * (0.05 + 0.25 * self.L_arm)
        sub = m_batt + m_motors + m_props + m_esc + m_arms
        m_shell = 0.4 + 0.10 * sub
        m_misc = 0.05 * sub
        return m_batt + m_motors + m_props + m_esc + m_arms + m_shell + m_misc + PAYLOAD_KG

    @property
    def TWR(self):
        return N_ROTORS * self.thrust_per_rotor() / (self.mass * G)

    @property
    def a_max(self):
        twr = self.TWR
        return G * math.sqrt(max(twr * twr - 1.0, 0.0))     # lateral accel at full-thrust tilt

    @property
    def v_max(self):
        n = self.rev_per_s()
        v_pitch = self.pitch_in * IN2M * n * ETA_PITCH       # can't outrun the prop's pitch speed
        T = N_ROTORS * self.thrust_per_rotor()
        mg = self.mass * G
        F_fwd = math.sqrt(max(T * T - mg * mg, 0.0))         # forward force at max tilt
        A_front = 0.02 + 0.05 * self.L_arm                   # frontal area [m^2]
        v_drag = math.sqrt(2.0 * F_fwd / (RHO * CD_BODY * A_front)) if F_fwd > 0 else 0.0
        return min(v_pitch, v_drag)

    @property
    def usable_energy_J(self):
        return self.energy_Wh * 3600.0 * 0.85                # 85% usable depth of discharge

    # ---------- constraints ----------
    def min_arm(self):
        # props must not overlap on a quad-X: arm >= (prop radius)/sin(45)
        return (self.D_in * IN2M / 2.0) / math.sin(math.radians(45))

    def arm_ok(self):
        return self.L_arm >= self.min_arm()

    def repaired(self):
        """Raise the arm to the shortest length the prop allows (no penalty cliff). Arm length is a
        dependent variable — you never build it shorter than clearance nor longer than needed."""
        return replace(self, L_arm=min(max(self.L_arm, self.min_arm()), BOUNDS["L_arm"][1]))

    def feasible_build(self):
        return self.min_arm() <= BOUNDS["L_arm"][1] and self.mass > 0 and self.a_max > 0

    # ---------- bridge to the engagement (duck-types as a Specimen) ----------
    def specimen(self):
        return _Spec(self.v_max, self.a_max, self.mass)

    def vector(self):
        return [getattr(self, k) for k in KEYS]

    @staticmethod
    def from_vector(x):
        return Drone(*x)

    def clamped(self):
        d = {k: min(max(getattr(self, k), BOUNDS[k][0]), BOUNDS[k][1]) for k in KEYS}
        return replace(self, **d)

    def spec_sheet(self):
        m_motor_g = (self.P_motor / MOTOR_KW_PER_KG) * 1000.0
        return (f"prop {self.D_in:.1f}x{self.pitch_in:.1f} in | Kv {self.Kv:.0f} | "
                f"custom motor {self.P_motor:.1f}kW ({m_motor_g:.0f}g) | "
                f"{self.S:.0f}S {self.cap_mAh:.0f}mAh ({self.energy_Wh:.0f}Wh) | arm {self.L_arm*100:.0f}cm\n"
                f"     mass {self.mass:.2f} kg | TWR {self.TWR:.2f} | a_max {self.a_max/G:.2f} g "
                f"({self.a_max:.0f} m/s^2) | v_max {self.v_max:.1f} m/s | T/rotor {self.thrust_per_rotor():.0f} N")


@dataclass
class _Spec:
    v_max: float
    a_max: float
    mass: float


if __name__ == "__main__":
    print("Calibration check — do feature choices land in the real catalog envelope?\n")
    tests = [
        ("small/fast", Drone(9, 5, 900, 6, 3000, 0.20, 0.8)),
        ("mid",        Drone(13, 6, 600, 6, 5000, 0.30, 1.2)),
        ("big/heavy",  Drone(18, 8, 450, 8, 8000, 0.45, 2.5)),
        ("high-volt",  Drone(15, 7, 500, 12, 6000, 0.40, 3.0)),
    ]
    print("catalog envelope: v_max 20-49 m/s | a_max 2.3-4.6 g | mass 4.3-13.6 kg | T/rotor 27-84 N\n")
    for name, dr in tests:
        ok = "OK" if dr.feasible_build() else "ARM-CLASH"
        print(f"{name:10s} [{ok}]  {dr.spec_sheet()}")
