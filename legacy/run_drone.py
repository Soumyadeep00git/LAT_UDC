"""The full grounded pipeline, on real drone features:

  1. CHOOSE an initial drone, report its spec sheet.
  2. SOLVE the intercept scenario with it (140-threat field).
  3. PERTURB each feature +/- and LEARN how each contributes to performance.
  4. OPTIMIZE the features (perturb-and-learn / SPSA) under mass <= 6 kg -> the optimal drone.
  5. Report the optimal drone's spec sheet and validate on the full field.

Objective is the defined intercept problem: intercept EVERY target, then best accuracy at least energy.
No agility score. v_max / a_max come from drone.py's physics, not knobs.

    python run_drone.py
"""
from __future__ import annotations

import random
from dataclasses import replace

from drone import Drone, KEYS, BOUNDS, G
from mission import threat_field
from engagement import simulate
from intercept import MISS_REF, E_REF

MASS_CAP = 6.0


def cost(drone, threats, w_e=0.3):
    """(J, fail_rate, mean_hit_miss, mean_energy) — arm auto-repaired, over-mass gated.

    J descends MEAN MISS over ALL threats (leakers included, capped) — the CONTINUOUS signal under the
    integer win-count, so perturb-and-learn always has a gradient (win-rate alone is a plateau on a
    minibatch). Energy is a light secondary term. This is the max-margin fix: rank by margin, not count.
    """
    drone = drone.repaired()
    if drone.mass > MASS_CAP:
        return 20.0 + 5.0 * (drone.mass - MASS_CAP), 1.0, float("nan"), float("nan")
    all_miss, hit_miss, energies, fails = [], [], [], 0
    for th in threats:
        o = simulate(drone.specimen(), th)
        all_miss.append(min(o.miss, 100.0))
        if o.intercepted:
            hit_miss.append(o.miss); energies.append(o.energy)
        else:
            fails += 1
    n = len(threats)
    mean_all = sum(all_miss) / n
    mean_hit = sum(hit_miss) / len(hit_miss) if hit_miss else float("nan")
    mean_e = sum(energies) / len(energies) if energies else E_REF
    J = mean_all / MISS_REF + w_e * mean_e / E_REF
    return J, fails / n, mean_hit, mean_e


def _fmt_perf(fr, miss, en):
    if fr != fr:  # nan
        return "infeasible"
    return f"win {(1-fr)*100:3.0f}%  miss {miss:5.2f}m  energy {en/1e3:5.1f}k"


# ------------------------------------------------------------------ 3. sensitivity
def sensitivity(drone, threats, frac=0.08):
    base = cost(drone, threats)
    print(f"\n3) FEATURE SENSITIVITY  (perturb each +/-{frac*100:.0f}% of its range, watch performance):")
    print(f"   {'feature':9s} {'-> effect on dynamics':38s} {'-> effect on mission'}")
    for k in KEYS:
        lo, hi = BOUNDS[k]; val = getattr(drone, k); step = frac * (hi - lo)
        dp = replace(drone, **{k: min(hi, val + step)}).clamped().repaired()
        dm = replace(drone, **{k: max(lo, val - step)}).clamped().repaired()
        Jp, frp, mp, ep = cost(dp, threats)
        Jm, frm, mm, em = cost(dm, threats)
        dvmax = dp.v_max - dm.v_max
        damax = (dp.a_max - dm.a_max) / G
        dmass = dp.mass - dm.mass
        dJ = Jp - Jm
        arrow = "improves" if dJ < 0 else "worsens " if dJ > 0 else "flat    "
        print(f"   {k:9s} dv_max {dvmax:+5.1f}  da_max {damax:+5.2f}g  dmass {dmass:+5.2f}kg  |  "
              f"raising it {arrow} (dJ {dJ:+.3f})")
    return base


# ------------------------------------------------------------------ 4. optimize features
# arm length & energy density are HARD constraints (your bounds) — never expanded. The rest are just
# our search box; if the optimum pins against one and still wants out, the box was the limit, not physics.
NO_EXPAND = {"L_arm"}
# bounds now ARE the catalog, so nothing may expand past them — every max is the buildable frontier.
CATALOG_MAX = {"D_in": 28, "pitch_in": 20, "Kv": 450, "S": 12, "cap_mAh": 16000, "P_motor": 1.40}


def optimize(start, world, bounds, iters=160, batch=18, a0=0.12, c0=0.10, w_e=0.3, seed=1):
    rng = random.Random(seed)
    lo = [bounds[k][0] for k in KEYS]; hi = [bounds[k][1] for k in KEYS]

    def spec(z):
        x = [lo[i] + max(0.0, min(1.0, z[i])) * (hi[i] - lo[i]) for i in range(len(z))]
        return Drone.from_vector(x)

    z = [(getattr(start, k) - lo[i]) / (hi[i] - lo[i]) for i, k in enumerate(KEYS)]
    z = [max(0.0, min(1.0, zi)) for zi in z]
    visited, sims = [], 0
    for k in range(1, iters + 1):
        mb = rng.sample(world, min(batch, len(world)))
        a = a0 / (k ** 0.602); c = c0 / (k ** 0.101)
        d = [1.0 if rng.random() < 0.5 else -1.0 for _ in z]
        zp = [max(0.0, min(1.0, z[i] + c * d[i])) for i in range(len(z))]
        zm = [max(0.0, min(1.0, z[i] - c * d[i])) for i in range(len(z))]
        jp = cost(spec(zp), mb, w_e)[0]
        jm = cost(spec(zm), mb, w_e)[0]
        sims += 2 * len(mb)
        g = [(jp - jm) / (2.0 * c * d[i]) for i in range(len(z))]
        z = [max(0.0, min(1.0, z[i] - a * g[i])) for i in range(len(z))]
        visited.append(spec(z))
    seen, cands = set(), [start]
    for s in visited:
        key = tuple(round(getattr(s, kk), 1) for kk in KEYS)
        if key not in seen:
            seen.add(key); cands.append(s)
    scored = [(s, cost(s, world, w_e)) for s in cands]
    scored.sort(key=lambda t: t[1][0])
    return scored[0], sims


def optimize_adaptive(start, world, expand_frac=0.5, max_rounds=6, tol=0.02, w_e=0.3):
    """Optimize; whenever the optimum pins a bound AND still wants out, grow that bound 50% and re-run.
    A real limit (mass cap) stops it naturally: pushing further just triggers the over-mass penalty, so
    the optimum stops moving toward the new frontier and we halt."""
    bounds = {k: list(BOUNDS[k]) for k in KEYS}
    # warm start: scatter random feasible drones and begin SPSA from the best. With 7 coupled features
    # a single fixed start lands in a weak basin; a cheap scatter finds the right neighbourhood first.
    srng = random.Random(7)
    lo = [bounds[k][0] for k in KEYS]; hi = [bounds[k][1] for k in KEYS]
    N_SCATTER = 250
    scatter = [start]
    for _ in range(N_SCATTER):
        x = [srng.uniform(lo[i], hi[i]) for i in range(len(KEYS))]
        scatter.append(Drone.from_vector(x).repaired())
    scored = sorted(((cost(d, world, w_e)[0], d) for d in scatter), key=lambda t: t[0])
    start = scored[0][1]                     # best of the scatter -> SPSA polishes from here
    (best, stats), sims_tot = optimize(start, world, bounds, w_e=w_e)
    sims_tot += N_SCATTER * len(world)
    for r in range(max_rounds):
        pinned = []
        for k in KEYS:
            if k in NO_EXPAND:
                continue
            lo, hi = bounds[k]; zt = (getattr(best, k) - lo) / (hi - lo)
            if zt > 1 - tol:
                pinned.append((k, "hi"))
            elif zt < tol:
                pinned.append((k, "lo"))
        if not pinned:
            print(f"   round {r}: optimum is interior — no bound is binding. Done.")
            break
        expanded_any = False
        for k, side in pinned:
            lo, hi = bounds[k]; span = hi - lo
            if side == "hi":
                cap = CATALOG_MAX.get(k, float("inf"))     # stay buildable: never past the catalog frontier
                if hi >= cap - 1e-9:
                    print(f"   round {r}: {k} pinned at HI {hi:.0f} = buildable frontier ({cap:.0f}) — holding, not extrapolating.")
                    continue
                bounds[k][1] = min(hi + expand_frac * span, cap)
                print(f"   round {r}: {k} pinned at HI {hi:.0f} & pulling -> expand to {bounds[k][1]:.0f} (frontier {cap:.0f})")
                expanded_any = True
            else:
                bounds[k][0] = max(0.0, lo - expand_frac * span)
                print(f"   round {r}: {k} pinned at LO {lo:.0f} & pulling -> expand to {bounds[k][0]:.0f}")
                expanded_any = True
        if not expanded_any:
            print(f"   round {r}: every pinned bound is at the buildable frontier — staying bounded. Done.")
            break
        prev = best
        (best, stats), s = optimize(prev, world, bounds, w_e=w_e); sims_tot += s
        used = any((side == "hi" and getattr(best, k) > getattr(prev, k) * 1.001) or
                   (side == "lo" and getattr(best, k) < getattr(prev, k) * 0.999)
                   for k, side in pinned)
        if not used:
            print(f"   round {r}: expanded, but optimum did NOT move into the new room -> a real limit "
                  f"(mass/physics) binds, not the box. Done.")
            break
    return (best, stats), bounds, sims_tot


def main():
    world = threat_field(140)

    print("=" * 78)
    initial = Drone(D_in=13, pitch_in=6, Kv=300, S=6, cap_mAh=5000, L_arm=0.30, P_motor=1.0)
    print("1) INITIAL DRONE")
    print("   " + initial.spec_sheet())

    print("\n2) SOLVE the intercept scenario (140 threats):")
    J, fr, miss, en = cost(initial, world)
    print("   " + _fmt_perf(fr, miss, en) + f"   (cost J {J:.3f})")

    sensitivity(initial, world)

    print("\n4) OPTIMIZE for MAX INTERCEPTION under mass <= 6 kg (catalog-bounded features)...")
    (best, (Jb, frb, mb_, eb)), final_bounds, sims = optimize_adaptive(initial, world, w_e=0.0)
    print(f"   searched with {sims} minibatch sims + full-field validation.")
    grew = [k for k in KEYS if tuple(final_bounds[k]) != BOUNDS[k]]
    if grew:
        print("   bounds that grew: " + ", ".join(
            f"{k} {BOUNDS[k][0]:.0f}-{BOUNDS[k][1]:.0f} -> {final_bounds[k][0]:.0f}-{final_bounds[k][1]:.0f}"
            for k in grew))

    print("\n5) OPTIMAL DRONE")
    print("   " + best.spec_sheet())
    print("   scenario: " + _fmt_perf(frb, mb_, eb) + f"   (cost J {Jb:.3f})")

    print("\n" + "-" * 78)
    print("INITIAL vs OPTIMAL:")
    print(f"   initial  {initial.spec_sheet().splitlines()[0]}")
    print(f"            {_fmt_perf(fr, miss, en)}  mass {initial.mass:.2f}kg")
    print(f"   optimal  {best.spec_sheet().splitlines()[0]}")
    print(f"            {_fmt_perf(frb, mb_, eb)}  mass {best.mass:.2f}kg")


if __name__ == "__main__":
    main()
