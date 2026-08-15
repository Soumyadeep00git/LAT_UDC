"""Perturb-and-learn, not hit-and-trial — SPSA (Simultaneous Perturbation Stochastic Approximation).

Each step: nudge the WHOLE design by a random +/-1 vector, evaluate the objective at design+nudge and
design-nudge, and read the gradient straight off the difference — TWO evaluations gives a gradient in
any number of dimensions, no grid. Step downhill. Because it is multi-objective, the objective weights
are RE-DRAWN each step, so the walk sweeps the Pareto front instead of collapsing to one point; every
design it visits is archived, and the non-dominated ones are the result.

And it never sweeps all threats: each evaluation uses a small MINIBATCH of scenarios (a cheap,
stochastic estimate). That is the first 'learnable' — the full surrogate that predicts unseen
scenarios is the next layer.
"""
from __future__ import annotations

import random
from typing import List

from specimen import Specimen, KEYS, BOUNDS
from mission import evaluate, OBJECTIVES

REF = {"fail_rate": 1.0, "time": 40.0, "energy": 5e5, "peak_power": 5e4}   # per-objective scale
_refv = [REF[o] for o in OBJECTIVES]
_lo = [BOUNDS[k][0] for k in KEYS]
_hi = [BOUNDS[k][1] for k in KEYS]


def _spec(z) -> Specimen:                                    # z in [0,1]^d -> a Specimen
    x = [_lo[i] + max(0.0, min(1.0, z[i])) * (_hi[i] - _lo[i]) for i in range(len(z))]
    return Specimen.from_vector(x)


def _scalar(objvec, w) -> float:
    return sum(w[i] * objvec[i] / _refv[i] for i in range(len(objvec)))


def optimize(spec0: Specimen, threats, iters: int = 80, batch: int = 12,
             a0: float = 0.12, c0: float = 0.12, seed: int = 1):
    """Perturb-and-learn from spec0. Returns (visited specimens, total engagement sims run)."""
    rng = random.Random(seed)
    z = [(getattr(spec0, k) - _lo[i]) / (_hi[i] - _lo[i]) for i, k in enumerate(KEYS)]
    z = [max(0.0, min(1.0, zi)) for zi in z]
    visited: List[Specimen] = []
    sims = 0
    for k in range(1, iters + 1):
        mb = rng.sample(threats, min(batch, len(threats)))          # minibatch — NOT all 140
        w = [rng.random() for _ in OBJECTIVES]
        s = sum(w) or 1.0
        w = [x / s for x in w]                                       # random-weight scalarization
        a = a0 / (k ** 0.602)
        c = c0 / (k ** 0.101)
        d = [1.0 if rng.random() < 0.5 else -1.0 for _ in z]         # +/-1 perturbation directions
        zp = [max(0.0, min(1.0, z[i] + c * d[i])) for i in range(len(z))]
        zm = [max(0.0, min(1.0, z[i] - c * d[i])) for i in range(len(z))]
        jp = _scalar(evaluate(_spec(zp), mb), w)
        jm = _scalar(evaluate(_spec(zm), mb), w)
        sims += 2 * len(mb)
        g = [(jp - jm) / (2.0 * c * d[i]) for i in range(len(z))]    # SPSA gradient estimate
        z = [max(0.0, min(1.0, z[i] - a * g[i])) for i in range(len(z))]
        visited.append(_spec(z))
    return visited, sims
