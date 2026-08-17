r"""INTRINSIC SPACE — stop optimizing the given knobs; find the coordinates the problem actually has.

Sloppy-model / information-geometry analysis (Sethna/Transtrum) on OUR real design model. We build the
log-log sensitivity Jacobian  J[i,k] = d ln(output_i) / d ln(param_k)  of the capabilities w.r.t. the design
params by finite-differencing the real coupled solve, form the Fisher information matrix M = J^T J, and
eigendecompose it. The eigenvalues are the STIFF..SLOPPY spectrum; each eigenvector is a COMBINATION of the
raw knobs. Big eigenvalue = a direction the outcome really moves along (a real coordinate, and in log-space
it reads as a power-law group of the knobs). Tiny eigenvalue = a sloppy direction you can wiggle for free.

The point: the nominal 7-knob box is not the real optimization space. This prints the intrinsic one.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import diagnose

PARAMS = diagnose.PARAMS                                  # D_in, pitch_in, Kv, I_max, S, cap_mAh, L_arm
OUTPUTS = ["a_max_g", "v_max", "endurance_min"]          # the capabilities we design for


def loglog_jacobian(cfg, eps=0.03):
    f0 = diagnose.caps_of(cfg)
    base = np.array([f0[o] for o in OUTPUTS], float)
    J = np.zeros((len(OUTPUTS), len(PARAMS)))
    for k, p in enumerate(PARAMS):
        c = dict(cfg); c[p] = cfg[p] * (1 + eps)
        fk = np.array([diagnose.caps_of(c)[o] for o in OUTPUTS], float)
        J[:, k] = (np.log(fk) - np.log(base)) / math.log(1 + eps)     # d ln(out)/d ln(param)
    return J


def _fmt_vector(vec, params, thresh=0.25):
    """Read a log-space eigenvector as a power-law combination of the knobs (dominant terms)."""
    terms = sorted(zip(params, vec), key=lambda t: -abs(t[1]))
    parts = [f"{p}^{c:+.2f}" for p, c in terms if abs(c) >= thresh]
    return "  *  ".join(parts) if parts else "(spread thin over all knobs)"


def main():
    cfg = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, C_rate=25,
               L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0)
    J = loglog_jacobian(cfg)
    M = J.T @ J                                            # Fisher information matrix (7x7)
    w, V = np.linalg.eigh(M)                               # ascending
    order = np.argsort(w)[::-1]
    w, V = w[order], V[:, order]
    wn = w / w[0]                                          # normalized to the stiffest

    print("=" * 84)
    print("INTRINSIC SPACE  -  the coordinates the design problem actually has (sloppy-model analysis)")
    print("=" * 84)
    print(f"model: caps_of(cfg) -> {OUTPUTS}   knobs: {PARAMS}")
    print(f"\nSTIFFNESS SPECTRUM (eigenvalues of J^T J, normalized to the stiffest):")
    for i, e in enumerate(wn):
        bar = "#" * max(0, int(30 + 5 * math.log10(max(e, 1e-30))))
        print(f"   dir {i+1}:  {e:10.2e}  {bar}")
    stiff = int(np.sum(wn > 1e-3))
    print(f"\n   sloppiness: stiffest/sloppiest = {w[0]/max(w[-1],1e-30):.1e}  (spans "
          f"{math.log10(w[0]/max(w[-1],1e-30)):.0f} orders)")
    print(f"   EFFECTIVE DIMENSION: ~{stiff} stiff direction(s) out of {len(PARAMS)} nominal knobs.")

    print(f"\nTHE REAL COORDINATES (stiff eigenvectors = combinations of the knobs that actually move the design):")
    for i in range(min(stiff, 3)):
        print(f"   [stiff {i+1}, weight {wn[i]:.2f}]  ~  {_fmt_vector(V[:, i], PARAMS)}")

    print(f"\nSLOPPY DIRECTIONS (wiggle these combinations for free - the optimizer wastes effort here):")
    for i in range(len(PARAMS) - 1, len(PARAMS) - 3, -1):
        print(f"   [sloppy, weight {wn[i]:.1e}]  ~  {_fmt_vector(V[:, i], PARAMS)}")

    print("\n" + "-" * 84)
    print("WHAT THIS PRODUCED: the nominal optimizer space is 7 knobs; the REAL space is ~"
          f"{stiff} stiff combination(s).")
    print("Optimizing D_in and pitch_in separately is optimizing in raw knob-space; the physics moves along")
    print("these power-law COMBINATIONS instead. That is the 'more real space' - discovered, not assumed.")
    print("Honest bound: this is the LOCAL geometry at one operating point; the stiff set is what the")
    print("evidence at this point reveals, and naming each combination's physical meaning is still grounding.")


if __name__ == "__main__":
    main()
