r"""BLADE DESIGN — physics field -> geometry. The DECODE step that closes the pipeline.

thrust_field.py gave the optimal induced-flow FIELD (uniform loading) for a target thrust. This inverts
the physics to the SHAPE that produces it: the blade chord c(r) and twist theta(r) along the span.

Geometry <-> physics interaction is blade-element + momentum, per annulus (hover):
  inflow angle  phi(r) = atan(v_i / (Omega r))          # the flow the geometry must meet
  relative wind W(r)   = hypot(v_i, Omega r)
  momentum loading      dT/dr = 4*pi*rho*r*v_i^2         # what the field demands
  blade-element loading dT/dr = B * 0.5*rho*W^2 * c * Cl(alpha) * cos(phi)
INVERSE (design): pick an efficient section angle-of-attack alpha, then
  c(r)     = 8*pi*r*v_i^2 / (B * W^2 * Cl * cos(phi))    # chord that carries the required loading
  theta(r) = phi(r) + alpha                              # geometric twist = inflow + AoA
FORWARD (validate): run BEMT with that geometry, solve v_i per annulus, integrate -> thrust ~ target.

Then loft the (r, chord, twist) stations into a definite 3D shape (STL). Blade design now comes from the
pipeline: intent (thrust) -> field -> geometry -> shape, forward-checked against the physics.
"""
from __future__ import annotations

import math
import os

import numpy as np

RHO = 1.225
A0 = 5.7                      # lift-curve slope (per rad)
ALPHA = math.radians(5.0)     # efficient section angle of attack
CL = A0 * ALPHA


def design(target_thrust, rpm, R_tip, R_hub=None, n_blades=2, N=24):
    """Inverse design: target thrust -> chord & twist distributions from the optimal (uniform) field."""
    R_hub = R_hub or 0.15 * R_tip
    Omega = rpm * 2 * math.pi / 60.0
    r = np.linspace(R_hub, R_tip, N)
    A = math.pi * (R_tip ** 2 - R_hub ** 2)
    v_i = math.sqrt(target_thrust / (2 * RHO * A))            # uniform induced velocity (Betz optimum)
    Ur = Omega * r
    phi = np.arctan2(v_i, Ur)
    W = np.hypot(v_i, Ur)
    chord = 8 * math.pi * r * v_i ** 2 / (n_blades * W ** 2 * CL * np.cos(phi))
    twist = phi + ALPHA
    return dict(r=r, chord=chord, twist=twist, v_i=v_i, rpm=rpm, Omega=Omega,
                R_tip=R_tip, R_hub=R_hub, n_blades=n_blades)


def forward_bemt(geom):
    """Validate: given the designed geometry, solve v_i per annulus (BE=momentum) and integrate thrust."""
    r, c, th = geom["r"], geom["chord"], geom["twist"]
    Omega, B = geom["Omega"], geom["n_blades"]
    dr = r[1] - r[0]
    T = 0.0
    for i in range(len(r)):
        Ur = Omega * r[i]

        def resid(v):
            phi = math.atan2(v, Ur)
            alpha = th[i] - phi
            W = math.hypot(v, Ur)
            dT_be = B * 0.5 * RHO * W * W * c[i] * (A0 * alpha) * math.cos(phi)
            dT_mom = 4 * math.pi * RHO * r[i] * v * v
            return dT_be - dT_mom
        lo, hi = 1e-4, 60.0
        if resid(lo) * resid(hi) > 0:
            v = 0.0
        else:
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                lo, hi = (mid, hi) if resid(lo) * resid(mid) > 0 else (lo, mid)
            v = 0.5 * (lo + hi)
        T += 4 * math.pi * RHO * r[i] * v * v * dr
    return T


def design_iterate(target_thrust, rpm, R_tip, tol=0.003, max_it=15, **kw):
    """ITERATE the geometry until the forward-solved thrust hits the target. The inverse design seeds it;
    then scale the chord (the loading knob) by target/forward each step until they agree."""
    geom = design(target_thrust, rpm, R_tip, **kw)
    hist = []
    for _ in range(max_it):
        T = forward_bemt(geom)
        hist.append(T)
        if abs(T - target_thrust) / target_thrust < tol:
            break
        geom["chord"] = geom["chord"] * (target_thrust / T)      # geometry moves to meet the thrust
    geom["thrust_forward"] = forward_bemt(geom)
    geom["hist"] = hist
    return geom


def to_stl(geom, path, M=20, thick=0.09):
    """Loft the (r, chord, twist) stations into a blade surface (point cloud -> definite shape), ASCII STL."""
    r, c, th = geom["r"], geom["chord"], geom["twist"]
    secs = []
    for i in range(len(r)):
        u = np.linspace(-c[i] / 4, 3 * c[i] / 4, M)          # chordwise, quarter-chord at origin
        xf = (u + c[i] / 4) / c[i]                            # 0..1 along chord
        yt = thick * c[i] * np.sqrt(np.clip(xf * (1 - xf), 0, None))
        top = [(uu * math.cos(th[i]) - wt * math.sin(th[i]), r[i], uu * math.sin(th[i]) + wt * math.cos(th[i]))
               for uu, wt in zip(u, yt)]
        bot = [(uu * math.cos(th[i]) + wt * math.sin(th[i]), r[i], uu * math.sin(th[i]) - wt * math.cos(th[i]))
               for uu, wt in zip(u, yt)]
        secs.append([*top, *bot[::-1]])                       # closed loop
    tris = []
    for i in range(len(secs) - 1):                            # loft between adjacent sections
        a, b = secs[i], secs[i + 1]
        for j in range(len(a)):
            k = (j + 1) % len(a)
            tris.append((a[j], a[k], b[j]))
            tris.append((a[k], b[k], b[j]))
    with open(path, "w") as f:
        f.write("solid blade\n")
        for t in tris:
            f.write(" facet normal 0 0 0\n  outer loop\n")
            for v in t:
                f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("  endloop\n endfacet\n")
        f.write("endsolid blade\n")
    return len(tris)


if __name__ == "__main__":
    T_target = 20.0
    geom = design_iterate(T_target, rpm=9800, R_tip=0.165, n_blades=2)

    print("=" * 82)
    print("BLADE DESIGN  -  physics field -> geometry (the DECODE step that closes the pipeline)")
    print("=" * 82)
    print(f"intent: {T_target:.1f} N thrust @ {geom['rpm']} rpm, R {geom['R_tip']*1000:.0f} mm, "
          f"{geom['n_blades']} blades  ->  optimal field v_i = {geom['v_i']:.2f} m/s (uniform)")

    print(f"\nITERATE geometry until forward thrust = target:")
    for k, T in enumerate(geom["hist"]):
        print(f"   step {k}: forward thrust {T:.2f} N   (err {100*(T-T_target)/T_target:+.1f}%)")
    print(f"   converged: {geom['thrust_forward']:.2f} N  vs target {T_target:.1f} N  "
          f"(rel err {abs(geom['thrust_forward']-T_target)/T_target:.1e})")

    print(f"\nDESIGNED geometry (chord & twist along the span):")
    print(f"   {'r/R':>5} {'chord(mm)':>10} {'twist(deg)':>11}")
    for i in (0, len(geom['r'])//4, len(geom['r'])//2, 3*len(geom['r'])//4, -1):
        print(f"   {geom['r'][i]/geom['R_tip']:>5.2f} {geom['chord'][i]*1000:>10.1f} "
              f"{math.degrees(geom['twist'][i]):>11.1f}")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build_blade")
    os.makedirs(out, exist_ok=True)
    stl = os.path.join(out, "blade.stl")
    n_tri = to_stl(geom, stl)
    print(f"\nSHAPE: lofted {len(geom['r'])} sections -> {n_tri} triangles -> {os.path.relpath(stl)}")

    print("\n" + "-" * 82)
    print("PIPELINE CLOSED: intent (thrust) -> optimal field -> blade geometry (chord+twist) -> definite")
    print("shape (STL), forward-checked against the physics. Blade design now comes from the pipeline.")
