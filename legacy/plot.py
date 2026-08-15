"""Plots for the intercept problem: the design-space landscape, the accuracy/energy trade, and where
best_specimen() lands. Renders the REAL full-field response over a design grid (no surrogate here) so
the maps are ground truth.

    python plot.py     ->  writes landscape.png, tradeoff.png
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from specimen import Specimen, BOUNDS
from mission import threat_field
from intercept import assess, best_specimen, MISS_REF, E_REF

NV, NA = 22, 22


def main():
    world = threat_field(140)
    vs = np.linspace(*BOUNDS["v_max"], NV)
    as_ = np.linspace(*BOUNDS["a_max"], NA)

    fail = np.zeros((NA, NV)); miss = np.full((NA, NV), np.nan)
    energy = np.full((NA, NV), np.nan); Jm = np.full((NA, NV), np.nan)
    print(f"evaluating {NV*NA} designs x 140 threats for the landscape...")
    for ia, a in enumerate(as_):
        for iv, v in enumerate(vs):
            J, fr, ms, en = assess(Specimen(v, a), world)
            fail[ia, iv] = fr
            if fr == 0.0:
                miss[ia, iv] = ms; energy[ia, iv] = en; Jm[ia, iv] = J

    print("running best_specimen (perturb-and-learn)...")
    spec, (J, fr, ms, en) = best_specimen(world)
    traj = spec._visited
    tv = [s.v_max for s in traj]; ta = [s.a_max for s in traj]

    ext = [vs[0], vs[-1], as_[0], as_[-1]]

    # -------- figure 1: the landscape --------
    fig, ax = plt.subplots(1, 3, figsize=(16, 5))
    for a in ax:
        a.set_xlabel("v_max  [m/s]"); a.set_ylabel("a_max  [m/s$^2$]")

    im0 = ax[0].imshow(fail * 100, origin="lower", extent=ext, aspect="auto", cmap="RdYlGn_r")
    ax[0].contour(vs, as_, fail, levels=[1e-9], colors="k", linewidths=2)  # the "works" boundary
    ax[0].set_title("leak rate %  (green = intercepts every target)")
    fig.colorbar(im0, ax=ax[0])

    im1 = ax[1].imshow(miss, origin="lower", extent=ext, aspect="auto", cmap="viridis_r")
    ax[1].set_title("accuracy: mean miss [m]  (feasible region only)")
    fig.colorbar(im1, ax=ax[1])

    im2 = ax[2].imshow(energy / 1e3, origin="lower", extent=ext, aspect="auto", cmap="magma_r")
    ax[2].set_title("mean energy [k]  (feasible region only)")
    fig.colorbar(im2, ax=ax[2])

    for a in ax:
        a.plot(tv, ta, "-", color="deepskyblue", lw=1.0, alpha=0.7)
        a.scatter(tv, ta, s=8, c="deepskyblue", alpha=0.5, label="perturb path")
        a.scatter([spec.v_max], [spec.a_max], s=220, marker="*", c="white",
                  edgecolors="k", linewidths=1.5, zorder=5, label="best_specimen")
    ax[0].legend(loc="upper right", fontsize=8)
    fig.suptitle("Design-space landscape (real full-field response) + perturb-and-learn path", y=1.02)
    fig.tight_layout()
    fig.savefig("landscape.png", dpi=120, bbox_inches="tight")

    # -------- figure 2: accuracy vs energy trade --------
    fig2, ax2 = plt.subplots(figsize=(7, 6))
    feas = ~np.isnan(miss)
    mm = miss[feas]; ee = energy[feas] / 1e3
    ax2.scatter(mm, ee, s=18, c="gray", alpha=0.5, label="feasible designs")
    # Pareto front (minimize both miss and energy)
    pts = sorted(zip(mm, ee))
    front, best_e = [], np.inf
    for m, e in pts:
        if e < best_e - 1e-9:
            front.append((m, e)); best_e = e
    if front:
        fx, fy = zip(*front)
        ax2.plot(fx, fy, "-o", color="crimson", ms=4, label="Pareto front")
    ax2.scatter([ms], [en / 1e3], s=240, marker="*", c="gold", edgecolors="k",
                linewidths=1.5, zorder=5, label="best_specimen")
    ax2.set_xlabel("mean miss  [m]   (accuracy — lower better)")
    ax2.set_ylabel("mean energy  [k]   (lower better)")
    ax2.set_title("Accuracy vs energy over designs that intercept every target")
    ax2.legend()
    fig2.tight_layout()
    fig2.savefig("tradeoff.png", dpi=120, bbox_inches="tight")

    print(f"\nbest_specimen: v{spec.v_max:.1f}/a{spec.a_max:.1f}  miss {ms:.2f} m  energy {en/1e3:.1f} k")
    print("wrote  landscape.png  tradeoff.png")


if __name__ == "__main__":
    main()
