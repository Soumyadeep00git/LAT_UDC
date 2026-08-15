"""Missions, threats, and MULTI-OBJECTIVE scoring — NOT a binary pass/fail count.

A threat is a scenario. A mission is a distribution of threats + a set of objectives to minimize:
  fail_rate   fraction of threats NOT intercepted   (mission success)
  time        mean time-to-intercept                (minimum-time mission)
  energy      mean energy spent                     (minimum-energy mission)
  peak_power  worst instantaneous power             (minimum-power mission)

A specimen is scored as a VECTOR of these, and specimens are Pareto-sorted — sorted on each
objective, no single blended number, no agility score. Different mission TYPES just weight/select
which objectives matter; the specimen's true behaviour comes from the engagement, not a proxy.

Crucially: a specimen is NEVER run against all threats. `evaluate` takes a small MINIBATCH of
scenarios (the first 'learnable' — cheap, stochastic estimate), and the surrogate (later) predicts
the rest. Bogus to sweep 140 per specimen.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from engagement import simulate

OBJECTIVES = ["fail_rate", "time", "energy", "peak_power"]     # all MINIMIZED


@dataclass
class Threat:
    vT: float
    R0: float
    bearing_rad: float
    weave_amp: float = 0.0        # m/s lateral weave amplitude (evasion)
    weave_period: float = 3.0     # s
    arrive_r: float = 5.0


def threat_field(n: int = 140, seed: int = 0) -> List[Threat]:
    """A deterministic spread of threats (speed x range x bearing x evasion) — the 'world'.

    The weave is the teeth: a slow specimen can't close before a fast threat arrives (fail_rate),
    and a low-a_max specimen can't null the weave's LOS rate (miss -> fail), while tracking it at all
    costs energy/power. That is what makes the four objectives genuinely trade off.
    """
    out = []
    for i in range(n):
        vT = 40.0 + (i * 53 % 90)                    # 40..130 m/s
        R0 = 500.0 + (i * 91 % 1100)                 # 500..1600 m
        bear = (i * 137 % 360) * math.pi / 180.0
        amp = 5.0 + (i * 29 % 40)                     # 5..45 m/s weave
        per = 1.5 + (i * 17 % 25) / 10.0              # 1.5..4.0 s
        # arrive_r is the ASSET keep-out (50 m) >> kill radius (3 m): the interceptor must kill at
        # stand-off. A threat that penetrates this bubble is a leaker, so an immobile drone fails all.
        out.append(Threat(vT, R0, bear, weave_amp=amp, weave_period=per, arrive_r=50.0))
    return out


def evaluate(spec, threats: List[Threat]) -> List[float]:
    """Multi-objective score vector over a (mini)batch of threats — all objectives MINIMIZED."""
    fails, times, energies, powers = 0, [], [], []
    for th in threats:
        o = simulate(spec, th)
        if o.intercepted:
            times.append(o.time); energies.append(o.energy); powers.append(o.peak_power)
        else:
            fails += 1
    n = len(threats)
    fail_rate = fails / n
    # if it intercepts nothing, penalize the performance objectives with a large finite value
    def m(xs, big):
        return sum(xs) / len(xs) if xs else big
    return [fail_rate, m(times, 40.0), m(energies, 5e5), m(powers, 5e4)]


def dominates(a: List[float], b: List[float]) -> bool:
    """a Pareto-dominates b (all objectives minimized): a <= b everywhere, < somewhere."""
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def pareto_front(items):
    """items: list of (label, objective_vector). Return the non-dominated ones."""
    front = []
    for i, (li, oi) in enumerate(items):
        if not any(dominates(oj, oi) for j, (lj, oj) in enumerate(items) if j != i):
            front.append((li, oi))
    return front
