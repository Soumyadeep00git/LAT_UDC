r"""V3 generative core — SPATIAL field version (Step 1).

Reshapes the actual 2-D actuator field over the airframe planform on a grid, honoring real SPATIAL
constraints (central payload keep-out + the seeker's clear forward cone), then re-embodies the reshaped
field into a physical layout. This is stronger than the scalar-area version: the field is sculpted in
space and routes AROUND forbidden zones, so the re-embodied form is spatially specific (asymmetric),
not just "more area".

Essence kept: momentum theory, per cell  P = sum d^1.5 * a / (FM*sqrt(2*rho)).  Embodiment (discrete
rotors) dissolved into d(x,y); optimum of min sum d^1.5 s.t. sum d*a = T is uniform d over the feasible
support -> fill every allowed cell at the lowest possible loading.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

from uav import build_uav, capabilities, G, IN2M
from solve import solve

RHO, FM = 1.225, 0.70
FRONT_CONE_DEG = 35.0        # seeker needs a clear forward field of view -> no actuator/downwash here


def _grid(cfg, N=25):
    n = int(cfg["n_rotors"]); R_rot = cfg["D_in"] * IN2M / 2; L = cfg["L_arm"]
    R_frame = L + R_rot; R_hub = max(0.04, 0.28 * L)
    xs = np.linspace(-R_frame, R_frame, N)
    X, Y = np.meshgrid(xs, xs)
    r = np.hypot(X, Y); ang = np.degrees(np.arctan2(Y, X))
    a_cell = (2 * R_frame / (N - 1)) ** 2
    annulus = (r >= R_hub) & (r <= R_frame)
    front_cone = (np.abs(ang) <= FRONT_CONE_DEG)                 # +x is "forward" (seeker look direction)
    feasible = annulus & ~front_cone
    return dict(n=n, R_rot=R_rot, R_frame=R_frame, R_hub=R_hub, X=X, Y=Y, r=r, ang=ang,
                a_cell=a_cell, annulus=annulus, feasible=feasible, N=N,
                A_used=n * math.pi * R_rot ** 2, A_feas=float(feasible.sum()) * a_cell)


def reduce_field(g, cfg):
    """The discrete rotors as a field: disk-loading blobs at the 45..315 deg rotor positions."""
    d = np.zeros_like(g["r"])
    n, L, R = g["n"], cfg["L_arm"], g["R_rot"]
    for i in range(n):
        a = math.radians(45 + i * 360 / n)
        cx, cy = L * math.cos(a), L * math.sin(a)
        d[np.hypot(g["X"] - cx, g["Y"] - cy) <= R] = 1.0
    return d


def reshape_field(g, T_req):
    """Uniform loading over the feasible support (the momentum optimum), embodiment gone."""
    d = np.zeros_like(g["r"])
    d[g["feasible"]] = T_req / g["A_feas"] if g["A_feas"] > 0 else 0.0
    return d


def _power(T, A):
    return T ** 1.5 / (FM * math.sqrt(2 * RHO * A)) if A > 0 else 1e9


def re_embody(g, k=None):
    """Cluster the feasible field into k rotors placed in the allowed sectors (front kept clear).
    Returns positions + sizes — a spatially specific, asymmetric layout."""
    lo, hi = FRONT_CONE_DEG, 360 - FRONT_CONE_DEG              # allowed angular span (rear/sides)
    span = hi - lo
    if k is None:
        k = max(3, int(round(g["A_feas"] / (math.pi * g["R_rot"] ** 2))))
    r_m = 0.5 * (g["R_hub"] + g["R_frame"])
    angs = [lo + span * (i + 0.5) / k for i in range(k)]
    D_eq = 2 * math.sqrt(g["A_feas"] / (k * math.pi))
    pos = [(round(r_m * math.cos(math.radians(a)), 3), round(r_m * math.sin(math.radians(a)), 3)) for a in angs]
    return dict(k=k, D_in=D_eq / IN2M, positions=pos, note="front cone kept clear for the seeker")


def _heat(g, d, title):
    ramp = " .:-=+*#%@"
    dmax = d.max() if d.max() > 0 else 1.0
    print(f"  {title}")
    for j in range(g["N"] - 1, -1, -2):
        row = "    "
        for i in range(0, g["N"], 1):
            row += ramp[min(len(ramp) - 1, int(d[j, i] / dmax * (len(ramp) - 1)))]
        print(row)


def demo():
    cfg = dict(D_in=12, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0)
    sysm = build_uav(cfg); bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    cap = capabilities(sysm, bus); T = cap["mass"] * G; E_J = bus.get("usable_energy", 0.0)
    g = _grid(cfg)

    print("V3 SPATIAL FIELD — reshape the whole 2-D actuator field around real keep-outs\n")
    print(f"  planform annulus R {g['R_hub']:.2f}..{g['R_frame']:.2f} m; forward {FRONT_CONE_DEG:.0f} deg "
          f"cone kept clear for the seeker")
    print(f"  A_used (4 rotors) {g['A_used']:.3f} m^2  |  A_feasible (annulus - cone) {g['A_feas']:.3f} m^2\n")

    d0 = reduce_field(g, cfg)
    _heat(g, d0, "[1] REDUCE — the discrete quad as a field (4 blobs):")
    d1 = reshape_field(g, T)
    _heat(g, d1, "[2] MODIFY — momentum-optimal field (fills the feasible support, avoids the front cone):")

    e0 = E_J / _power(T, g["A_used"]) / 60.0
    e1 = E_J / _power(T, g["A_feas"]) / 60.0
    print(f"\n  endurance: discrete {e0:.1f} min -> spatial field {e1:.1f} min  (x{e1/e0:.2f})")

    emb = re_embody(g)
    print(f"\n[3] RE-EMBODY — {emb['k']} rotors of ~{emb['D_in']:.1f} in in the allowed sectors "
          f"({emb['note']}):")
    print(f"    positions (m): {emb['positions']}")
    print(f"\n-> a spatially specific, ASYMMETRIC layout the front-clear seeker requires — generated from")
    print(f"   the field, not selectable from a rotor-count menu. Essence kept, embodiment regenerated.")
    print(f"\nHONEST: momentum-theory per-cell + uniform-fill optimum + sector re-embodiment. The deep")
    print(f"   version couples a real CFD field solve and a manufacturable-layout synthesis.")


if __name__ == "__main__":
    demo()
