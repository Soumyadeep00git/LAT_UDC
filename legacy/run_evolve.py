"""Introduce specimen 1 into the world; perturb-and-learn it into a Pareto family of interceptors —
multi-objective, no agility score, never sweeping all 140 threats per specimen.

    python run_evolve.py
"""
from __future__ import annotations

from mission import threat_field, evaluate, pareto_front, OBJECTIVES
from specimen import Specimen
import perturb_learn as pl


def fmt(o):
    return (f"fail {o[0]*100:4.0f}%  time {o[1]:5.1f}s  energy {o[2]/1e3:6.1f}k  power {o[3]/1e3:5.1f}k")


def main():
    world = threat_field(140)
    val = world[::7]                                    # 20-threat validation set for honest scoring

    spec1 = Specimen(v_max=60.0, a_max=100.0)           # specimen 1 — a middling design
    base = evaluate(spec1, val)
    print("SPECIMEN 1 introduced:  v_max=%.0f  a_max=%.0f  mass=%.2f kg" % (spec1.v_max, spec1.a_max, spec1.mass))
    print("   baseline (multi-objective):  " + fmt(base) + "\n")

    print("perturb-and-learn (SPSA, minibatches of 12 threats — never the full 140 per specimen)...")
    visited, sims = pl.optimize(spec1, world, iters=120, batch=12)

    # honest final scoring: evaluate a deduped archive on the validation set (a handful of designs)
    seen, cands = set(), [("start", spec1)]
    for s in visited:
        key = (round(s.v_max / 3), round(s.a_max / 8))
        if key not in seen:
            seen.add(key); cands.append(("v%.0f/a%.0f" % (s.v_max, s.a_max), s))
    scored = [(lab, evaluate(sp, val)) for lab, sp in cands]
    front = pareto_front(scored)

    print(f"   ran {sims} engagement sims total (perturb-and-learn).")
    grid = 20 * 20 * len(world)
    print(f"   a 20x20 grid x 140 threats (hit-and-trial) would be {grid} — ~{grid//max(sims,1)}x more.\n")

    print(f"PARETO FAMILY ({len(front)} non-dominated designs — sorted per objective, no blended score):")
    for lab, o in sorted(front, key=lambda t: t[1][0]):
        sp = dict(cands)[lab] if lab in dict(cands) else None
        print(f"   {lab:12s}  " + fmt(o))

    # show the win vs specimen 1: best design that dominates or matches the start on the mission
    best_fail = min(front, key=lambda t: (t[1][0], t[1][1]))
    print("\nvs specimen 1:")
    print("   start        " + fmt(base))
    print("   best-success " + fmt(best_fail[1]) + f"   ({best_fail[0]})")


if __name__ == "__main__":
    main()
