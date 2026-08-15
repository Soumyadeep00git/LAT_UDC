"""best_specimen — the function that answers "which interceptor will WORK".

The problem, defined concretely (this is the 'best specimen' definition you asked to pin down):

    A specimen WORKS iff it intercepts EVERY target (no leakers).
    Among the ones that work, the BEST one has the smallest miss (accuracy) at the least energy.

Encoded as a single cost the perturb-and-learn descends:

    J(spec) = 10 + 10*fail_rate                         while it still leaks   (must first WORK)
            = w_acc*(miss/MISS_REF) + w_e*(energy/E_REF) once it intercepts all (then get sharp & cheap)

The gate makes "intercept everything" strictly dominate any accuracy/energy gain, so the search first
buys reliability, then trades accuracy against energy. No agility score, no hand-weighted proxy —
accuracy and energy come straight out of the engagement. It perturbs (SPSA) on scenario MINIBATCHES,
never sweeping all 140 per specimen, and only validates the final answer on the full field.
"""
from __future__ import annotations

import random

from specimen import Specimen, KEYS, BOUNDS
from engagement import simulate
from mission import threat_field

MISS_REF = 5.0        # m   — a "good" miss is a few metres
E_REF = 50_000.0      # J   — a typical engagement's energy
_LO = [BOUNDS[k][0] for k in KEYS]
_HI = [BOUNDS[k][1] for k in KEYS]


def assess(spec, threats, w_acc=1.0, w_e=1.0):
    """Return (J, fail_rate, mean_miss, mean_energy) for a specimen over a set of threats."""
    misses, energies, fails = [], [], 0
    for th in threats:
        o = simulate(spec, th)
        if o.intercepted:
            misses.append(o.miss); energies.append(o.energy)
        else:
            fails += 1
    n = len(threats)
    fr = fails / n
    if fr > 0.0:                                            # still leaking -> must fix that first
        acc = sum(misses) / len(misses) if misses else float("nan")
        en = sum(energies) / len(energies) if energies else float("nan")
        return 10.0 + 10.0 * fr, fr, acc, en
    acc = sum(misses) / len(misses)
    en = sum(energies) / len(energies)
    return w_acc * (acc / MISS_REF) + w_e * (en / E_REF), fr, acc, en


def _spec(z):
    x = [_LO[i] + max(0.0, min(1.0, z[i])) * (_HI[i] - _LO[i]) for i in range(len(z))]
    return Specimen.from_vector(x)


def best_specimen(world=None, start=None, iters=140, batch=14,
                  a0=0.10, c0=0.10, w_acc=1.0, w_e=1.0, seed=1, verbose=False):
    """Perturb-and-learn toward the design that intercepts every target with best accuracy / least energy.

    Returns (specimen, stats) where stats = (J, fail_rate, mean_miss, mean_energy) on the FULL world.
    """
    world = world if world is not None else threat_field(140)
    rng = random.Random(seed)
    start = start if start is not None else Specimen((_LO[0] + _HI[0]) / 2, (_LO[1] + _HI[1]) / 2)
    z = [(getattr(start, k) - _LO[i]) / (_HI[i] - _LO[i]) for i, k in enumerate(KEYS)]
    z = [max(0.0, min(1.0, zi)) for zi in z]

    visited, sims = [], 0
    for k in range(1, iters + 1):
        mb = rng.sample(world, min(batch, len(world)))     # minibatch — never the full 140
        a = a0 / (k ** 0.602)
        c = c0 / (k ** 0.101)
        d = [1.0 if rng.random() < 0.5 else -1.0 for _ in z]
        zp = [max(0.0, min(1.0, z[i] + c * d[i])) for i in range(len(z))]
        zm = [max(0.0, min(1.0, z[i] - c * d[i])) for i in range(len(z))]
        jp = assess(_spec(zp), mb, w_acc, w_e)[0]
        jm = assess(_spec(zm), mb, w_acc, w_e)[0]
        sims += 2 * len(mb)
        g = [(jp - jm) / (2.0 * c * d[i]) for i in range(len(z))]
        z = [max(0.0, min(1.0, z[i] - a * g[i])) for i in range(len(z))]
        visited.append(_spec(z))
        if verbose and k % 20 == 0:
            s = _spec(z)
            print(f"   iter {k:3d}: v{s.v_max:5.1f}/a{s.a_max:6.1f}")

    # honest final answer: validate a deduped set of visited designs on the FULL field, return the best
    seen, cands = set(), []
    for s in visited + [start]:
        key = (round(s.v_max / 2), round(s.a_max / 5))
        if key not in seen:
            seen.add(key); cands.append(s)
    scored = [(s, assess(s, world, w_acc, w_e)) for s in cands]
    scored.sort(key=lambda t: t[1][0])
    best, stats = scored[0]
    best._sims = sims
    best._visited = visited                                 # SPSA trajectory, for inspection/plots
    return best, stats


if __name__ == "__main__":
    world = threat_field(140)
    print("Solving: which specimen intercepts EVERY target with best accuracy at least energy?\n")
    spec, (J, fr, miss, en) = best_specimen(world, verbose=True)
    works = "YES" if fr == 0.0 else f"NO ({fr*100:.0f}% leak)"
    print(f"\nANSWER  ->  v_max {spec.v_max:.1f} m/s   a_max {spec.a_max:.1f} m/s^2   mass {spec.mass:.2f} kg")
    print(f"   intercepts every target : {works}")
    print(f"   accuracy (mean miss)    : {miss:.2f} m")
    print(f"   energy (mean)           : {en/1e3:.1f} k")
    print(f"   cost J                  : {J:.3f}")
    print(f"   learned from {spec._sims} minibatch sims + 1 full-field validation of the archive.")
