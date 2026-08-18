r"""RESIDUAL DETECTOR — find a HIDDEN dimension from data, not from a pre-encoded invariant.

The honest replacement for the hand-loaded v3c. A reduced model omits variables the true physics has.
Where it's wrong, it's wrong in a STRUCTURED way, and that structure is the fingerprint of the missing
variable. So: sample designs, take the residual between the reduced model and a higher-fidelity solve, and
ask three questions - is it structured (or just noise)? how many variables does it depend on? which ones?

Concrete instance: the pipeline's hover model uses a CONSTANT figure of merit FM = 0.70. The higher-fidelity
rotor_fm solves the real FM from the blade field. The residual FM_real - 0.70, swept over designs, should
reveal that FM secretly depends on pitch and rpm (loading / tip speed) - a dimension the constant omits.

MANDATE: it must state what it cannot do, and it must REFUSE to claim a hidden dimension when the residual
is unstructured. A negative control (pure noise) checks exactly that.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

import rotor_fm

FM_REDUCED = 0.70                         # the constant the reduced model assumes
VARS = ["D_in", "pitch_in", "rpm"]
rng = np.random.default_rng(7)


def fm_real(D_in, pitch_in, rpm, N=22, n_blades=2):
    """Higher-fidelity FM: build a geometric-pitch blade from (D, pitch) and solve the hover field."""
    R = D_in * 0.0254 / 2
    r = np.linspace(0.15 * R, R, N)
    pitch_m = pitch_in * 0.0254
    twist = np.arctan2(pitch_m, 2 * math.pi * r)         # geometric twist from pitch
    chord = 0.10 * R * (1 - 0.5 * r / R)                 # a simple taper
    return rotor_fm.bemt_hover(r, chord, twist, rpm, n_blades=n_blades)["FM"]


def _basis(Xl):
    """linear + quadratic in the log-variables (enough to catch a peaked/stall dependence)."""
    cols = [np.ones(len(Xl))]
    cols += [Xl[:, i] for i in range(Xl.shape[1])]
    cols += [Xl[:, i] ** 2 for i in range(Xl.shape[1])]
    return np.column_stack(cols)


def _analyze(X, res):
    """Cross-validated: fit on half, score on the held-out half. Real structure generalizes; noise does not.
    That test R^2 is what separates a hidden dimension from noise - the ambiguity a single-fit R^2 can't."""
    Xl = np.log(np.array(X))
    res = np.array(res)
    n = len(res)
    idx = rng.permutation(n); tr, te = idx[: n // 2], idx[n // 2:]
    B = _basis(Xl)
    coef, *_ = np.linalg.lstsq(B[tr], res[tr], rcond=None)
    pred = B[te] @ coef
    ss_res = float(np.sum((res[te] - pred) ** 2))
    ss_tot = float(np.sum((res[te] - res[tr].mean()) ** 2))
    test_R2 = 1 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    coef_f, *_ = np.linalg.lstsq(B, res, rcond=None)                    # full fit for attribution
    d = Xl.shape[1]
    contrib = {VARS[i]: (abs(coef_f[1 + i]) + abs(coef_f[1 + d + i])) * float(np.std(Xl[:, i])) for i in range(d)}
    return dict(res_std=float(res.std()), res_mean=float(res.mean()), test_R2=float(test_R2), contrib=contrib)


def detect(samples):
    X, res = [], []
    for (D, p, rpm) in samples:
        fm = fm_real(D, p, rpm)
        if 0.05 < fm < 1.0:
            X.append([D, p, rpm]); res.append(fm - FM_REDUCED)
    return X, res, _analyze(X, res)


def verdict(a, sig_std=0.03, sig_R2=0.4):
    if a["res_std"] < sig_std:
        return "NO HIDDEN DIMENSION", "residual is negligible - the reduced model is adequate here."
    if a["test_R2"] >= sig_R2:
        top = sorted(a["contrib"].items(), key=lambda t: -t[1])
        who = ", ".join(f"{k}" for k, _ in top[:2])
        return "HIDDEN DIMENSION FOUND", (f"residual is structured AND generalizes (held-out R^2={a['test_R2']:.2f}); "
                                          f"it depends mainly on [{who}] - a dependence FM=0.70 omits.")
    return "STRUCTURE DOES NOT GENERALIZE", (f"residual is large (std {a['res_std']:.2f}) but does NOT predict "
                                             f"held-out data (test R^2={a['test_R2']:.2f}). Cannot claim a hidden "
                                             f"dimension: this is noise, or a variable I never varied, or a "
                                             f"dependence beyond this basis - and from one residual I cannot tell which.")


def main():
    print("=" * 84)
    print("RESIDUAL DETECTOR  -  find a hidden dimension from data (reduced FM=0.70 vs solved FM)")
    print("=" * 84)

    samples = [(rng.uniform(10, 20), rng.uniform(4, 12), rng.uniform(4000, 12000)) for _ in range(120)]
    X, res, a = detect(samples)
    tag, why = verdict(a)
    print(f"\n[POSITIVE] {len(X)} designs sampled. residual FM_real - 0.70:")
    print(f"   mean {a['res_mean']:+.3f}  std {a['res_std']:.3f}  held-out R^2={a['test_R2']:.2f}")
    print(f"   per-variable dependence: { {k: round(v,3) for k,v in a['contrib'].items()} }")
    print(f"   => {tag}: {why}")
    if tag == "HIDDEN DIMENSION FOUND":
        print("      grounding (human): pitch & rpm combine into blade loading / advance ratio - the axis the")
        print("      constant FM throws away. Discovered from the residual, NOT from a pre-encoded invariant.")

    # NEGATIVE CONTROL: noise of the SAME SIZE as the real residual -> passes the size gate, must be caught
    # by cross-validation (it can't predict held-out data). The detector MUST refuse to claim a dimension.
    noise = list(rng.normal(0, a["res_std"], size=len(X)))
    an = _analyze(X, noise)
    tagn, whyn = verdict(an)
    print(f"\n[NEGATIVE CONTROL] residual replaced with noise of the SAME std ({an['res_std']:.3f}):")
    print(f"   held-out R^2={an['test_R2']:.2f}   => {tagn}: {whyn}")

    print("\n" + "-" * 84)
    print("WHAT THIS TOOL CAN vs CANNOT DO (the point, not an afterthought):")
    print("  CAN:    detect whether a residual is structured AND generalizes (held-out R^2); rank which of")
    print("          the varied variables carry it; and REFUSE a dimension when it's noise (control: R^2<0).")
    print("  CANNOT: see a hidden variable it never VARIED (unexcited = invisible); distinguish - from ONE")
    print("          residual - noise from a real-but-unmodelled variable when it fails to generalize (it")
    print("          says 'does not generalize' rather than guessing); prove CAUSATION (correlation only -")
    print("          needs intervention); identify a dependence beyond its basis (linear+quadratic here); or")
    print("          work without a higher-fidelity reference to take the residual against.")


if __name__ == "__main__":
    main()
