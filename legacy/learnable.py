"""THE LEARNABLE — learn, from threat scenarios, what design features a specimen needs to win.

The old sizing code brute-forced a_req(scenario, v) by sweeping. Here we LEARN the win surface from a
modest sample of engagements, then read two things straight off the model:

  1. GLOBAL feature importance  — across all threats, which levers decide winning (standardized coefs).
  2. PER-THREAT feature need     — for THIS threat, at the CURRENT design, does raising v_max or a_max
                                   raise P(win) more? i.e. does the threat demand SPEED or AGILITY?

The model is logistic regression on physics-motivated features, fit by plain gradient descent (numpy
only, no sklearn). It is deliberately interpretable: its coefficients ARE the answer to "what feature
does winning need." Once trained it also REPLACES the simulator for design search — predict P(win) on
a fine design grid over the whole field with zero new sims, pick the max, validate once. That is how we
avoid running 140 scenarios per specimen.
"""
from __future__ import annotations

import math
import random

import numpy as np

from specimen import Specimen, BOUNDS
from engagement import simulate
from mission import Threat

# feature names, in column order. speed_margin / a_weave / agility_margin are physics-motivated;
# 'and' is the conjunction term (you must have BOTH reach AND track), which a linear model needs to
# express the corner-shaped win region.
FEATS = ["v_max", "a_max", "vT", "R0", "weave_amp",
         "speed_margin", "a_weave", "agility_margin", "reach_AND_track"]

_LO_V, _HI_V = BOUNDS["v_max"]
_LO_A, _HI_A = BOUNDS["a_max"]
_RANGE_V, _RANGE_A = _HI_V - _LO_V, _HI_A - _LO_A


def build_X(vmax, amax, vT, R0, wamp, wper):
    """Feature matrix (n, len(FEATS)) from raw arrays. Vectorized so the surrogate is cheap to query."""
    vmax = np.asarray(vmax, float); amax = np.asarray(amax, float)
    vT = np.asarray(vT, float); R0 = np.asarray(R0, float)
    wamp = np.asarray(wamp, float); wper = np.asarray(wper, float)
    speed_margin = vmax - vT                          # can I close the gap?
    a_weave = wamp * 2.0 * np.pi / wper               # lateral accel the threat's weave demands
    agility_margin = amax - a_weave                   # can I null the weave?
    conj = speed_margin * agility_margin / 100.0      # need BOTH -> product
    return np.stack([vmax, amax, vT, R0, wamp,
                     speed_margin, a_weave, agility_margin, conj], axis=-1)


def sample_dataset(n=2000, seed=0):
    """Random (specimen, threat) pairs -> (X, win labels, raw rows). One engagement sim each."""
    rng = random.Random(seed)
    raw, y = [], []
    for _ in range(n):
        vmax = rng.uniform(_LO_V, _HI_V); amax = rng.uniform(_LO_A, _HI_A)
        vT = rng.uniform(40, 130); R0 = rng.uniform(500, 1600)
        wamp = rng.uniform(5, 45); wper = rng.uniform(1.5, 4.0)
        bear = rng.uniform(0, 2 * math.pi)
        o = simulate(Specimen(vmax, amax), Threat(vT, R0, bear, weave_amp=wamp, weave_period=wper))
        raw.append((vmax, amax, vT, R0, wamp, wper))
        y.append(1.0 if o.intercepted else 0.0)
    raw = np.array(raw)
    X = build_X(raw[:, 0], raw[:, 1], raw[:, 2], raw[:, 3], raw[:, 4], raw[:, 5])
    return X, np.array(y), raw


class WinModel:
    """Logistic regression on standardized features, fit by gradient descent."""

    def fit(self, X, y, iters=6000, lr=0.5, l2=1e-3):
        self.mu = X.mean(0); self.sd = X.std(0) + 1e-9
        Z = np.hstack([np.ones((len(X), 1)), (X - self.mu) / self.sd])
        w = np.zeros(Z.shape[1])
        for _ in range(iters):
            p = 1.0 / (1.0 + np.exp(-Z @ w))
            reg = l2 * np.concatenate([[0.0], w[1:]])
            w -= lr * (Z.T @ (p - y) / len(y) + reg)
        self.w = w
        return self

    def proba(self, X):
        Z = np.hstack([np.ones((len(X), 1)), (X - self.mu) / self.sd])
        return 1.0 / (1.0 + np.exp(-Z @ self.w))

    def importance(self):
        """Standardized-coefficient magnitude per feature -> global 'what decides winning'."""
        return sorted(zip(FEATS, self.w[1:]), key=lambda t: -abs(t[1]))


def feature_need(model, threat, spec, eps_v=2.0, eps_a=5.0):
    """At the CURRENT design `spec`, which lever raises P(win) more for THIS threat?

    Returns (dP per full v_max travel, dP per full a_max travel, label). Scaling each finite-difference
    by the lever's full range makes speed and agility comparable, so the larger one is the binding need.
    """
    def p(v, a):
        X = build_X([v], [a], [threat.vT], [threat.R0], [threat.weave_amp], [threat.weave_period])
        return float(model.proba(X)[0])
    dv = (p(spec.v_max + eps_v, spec.a_max) - p(spec.v_max - eps_v, spec.a_max)) / (2 * eps_v)
    da = (p(spec.v_max, spec.a_max + eps_a) - p(spec.v_max, spec.a_max - eps_a)) / (2 * eps_a)
    sv, sa = dv * _RANGE_V, da * _RANGE_A            # sensitivity over the whole lever travel
    label = "speed" if sv >= sa else "agility"
    return sv, sa, label


def best_design_by_surrogate(model, threats, n=41):
    """Grid the design box, predict mean P(win) over the whole threat field with the surrogate (NO new
    sims), return the max-win design. This is the 'never run 140 per specimen' payoff."""
    vs = np.linspace(_LO_V, _HI_V, n)
    as_ = np.linspace(_LO_A, _HI_A, n)
    vT = np.array([t.vT for t in threats]); R0 = np.array([t.R0 for t in threats])
    wamp = np.array([t.weave_amp for t in threats]); wper = np.array([t.weave_period for t in threats])
    best, best_p = None, -1.0
    for v in vs:
        for a in as_:
            X = build_X(np.full(len(threats), v), np.full(len(threats), a), vT, R0, wamp, wper)
            pm = float(model.proba(X).mean())
            if pm > best_p:
                best_p, best = pm, (v, a)
    return Specimen(best[0], best[1]), best_p
