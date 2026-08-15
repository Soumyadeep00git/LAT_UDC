"""A specimen — an interceptor design. Small, continuous parameter vector, with PHYSICS COUPLING so
agility is not free: a bigger a_max / v_max means more mass and more power draw. That coupling is
what makes the objectives genuinely trade off (fast/agile vs light/efficient), so there is a real
Pareto surface for perturb-and-learn to explore — no hand-picked agility weights anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

# design knobs and their allowed box (the world's physical limits, not preferences)
BOUNDS = {
    "v_max": (30.0, 120.0),    # m/s   top speed
    "a_max": (30.0, 300.0),    # m/s^2 lateral-accel authority (~3g .. 30g)
}


@dataclass
class Specimen:
    v_max: float
    a_max: float

    # --- derived physics (coupling: capability costs mass) ---
    @property
    def mass(self) -> float:
        # heavier to fly faster and pull harder: a light base + terms in v_max^2 (structure) and a_max (motors)
        return 1.5 + 4e-4 * self.v_max ** 2 + 6e-3 * self.a_max

    def vector(self):
        return [self.v_max, self.a_max]

    @staticmethod
    def from_vector(x):
        return Specimen(v_max=x[0], a_max=x[1])

    def clamped(self) -> "Specimen":
        v = min(max(self.v_max, BOUNDS["v_max"][0]), BOUNDS["v_max"][1])
        a = min(max(self.a_max, BOUNDS["a_max"][0]), BOUNDS["a_max"][1])
        return replace(self, v_max=v, a_max=a)


KEYS = list(BOUNDS.keys())
SCALE = [BOUNDS[k][1] - BOUNDS[k][0] for k in KEYS]     # per-dim scale for perturbation steps
