r"""INVARIANT COLLAPSE — thrust is not f(geometry); it is f(g(h(D,n,V))). Show it, in its invariant space.

The claim: thrust looks like a messy 3-variable function T(D, n, V), but it is really
    T = rho * n^2 * D^4 * Ct(J),   J = V/(nD)
- h: (D,n,V) -> J           (advance ratio - the real operating variable)
- g: J -> Ct(J)             (ONE curve - the blade shape's signature)
- f: Ct -> thrust = rho n^2 D^4 Ct   (pure dimensional scaling)

So the true function is the 1-D curve Ct(J). In (D,n,V) space thrust spans orders of magnitude and looks
3-dimensional; in (J, Ct) space it COLLAPSES to a single curve - the function seen in its invariant space,
where it is simple and solvable. The invariant coordinates (Ct, J) are found by dimensional analysis (given
the variables' dimensions), not asserted; the collapse is then the data confirming the composition.

Honest: this uses a fixed blade shape and ignores the induced velocity and Reynolds number, so the collapse
is exact by dynamic similarity. Real props have a mild Re dependence -> Ct = Ct(J, Re), a surface not a
perfect curve. Dimensional analysis gives the GROUPS (the scaling); the CURVE Ct(J) still needs the physics.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import dimanalysis

RHO, A0, CD0, KD = 1.225, 5.7, 0.02, 0.02
PD = 0.6                    # fixed pitch-to-diameter (the SHAPE is dimensionless-fixed for all sizes)


def thrust(D, rpm, V, N=24, n_blades=2):
    """Blade-element thrust in forward flight for a FIXED blade shape (induced velocity ignored - flagged)."""
    R = D / 2
    n = rpm / 60.0
    Omega = rpm * 2 * math.pi / 60.0
    T = 0.0
    dr = (R - 0.15 * R) / (N - 1)
    for i in range(N):
        r = 0.15 * R + i * dr
        x = r / R
        theta = math.atan(PD / (math.pi * x))            # geometric twist from fixed P/D
        c = 0.10 * R * (1 - 0.5 * x)                      # taper, fraction of R (scales with D)
        phi = math.atan2(V, Omega * r)
        W = math.hypot(V, Omega * r)
        Cl = max(-1.2, min(1.2, A0 * (theta - phi)))
        Cd = CD0 + KD * Cl * Cl
        T += 0.5 * RHO * n_blades * c * W * W * (Cl * math.cos(phi) - Cd * math.sin(phi)) * dr
    return T


def main():
    print("=" * 84)
    print("INVARIANT COLLAPSE  -  thrust as f(g(h(D,n,V))), constructed in its invariant space")
    print("=" * 84)

    # [1] the invariant coordinates, from dimensional analysis (given the variables' dimensions)
    law, groups = dimanalysis.derive("thrust", ["density", "angular_speed", "diameter", "velocity"])
    print(f"\n[1] invariant coordinates from dimensional analysis (Buckingham-Pi):")
    print(f"    {law}")
    print("    => two groups: Ct = thrust/(rho n^2 D^4)   and   J = V/(n D).  These are the invariant space.")

    # [2] the SAME J across very different (D, rpm): does Ct collapse while thrust does not?
    print("\n[2] evaluate thrust at MATCHED advance ratio J across different sizes/speeds:")
    for J in (0.0, 0.2, 0.4, 0.6):
        print(f"\n  J = {J}:")
        print(f"    {'D(m)':>5} {'rpm':>6} {'V(m/s)':>7} {'thrust(N)':>10} {'Ct':>8}")
        cts = []
        for D, rpm in [(0.2, 7000), (0.3, 5000), (0.4, 3500), (0.5, 2500)]:
            n = rpm / 60.0
            V = J * n * D
            T = thrust(D, rpm, V)
            Ct = T / (RHO * n ** 2 * D ** 4)
            cts.append(Ct)
            print(f"    {D:>5.2f} {rpm:>6.0f} {V:>7.1f} {T:>10.2f} {Ct:>8.4f}")
        spread = (max(cts) - min(cts)) / (sum(cts) / len(cts)) if cts else 0
        print(f"    -> thrust spans {min(T for T in [thrust(D,rpm,J*rpm/60*D) for D,rpm in [(0.2,7000),(0.5,2500)]]):.1f}"
              f"..{max(T for T in [thrust(D,rpm,J*rpm/60*D) for D,rpm in [(0.2,7000),(0.5,2500)]]):.0f} N, "
              f"but Ct varies only {100*spread:.1f}% -> COLLAPSED onto one value.")

    print("\n" + "-" * 84)
    print("READING IT: thrust across a 4-in to 20-in propeller and 2500-7000 rpm spans orders of magnitude,")
    print("yet at the SAME advance ratio J every one has the SAME Ct. So thrust is NOT a function of the")
    print("geometry (D) or speed (n,V) separately - it is the single curve Ct(J), scaled by rho n^2 D^4.")
    print("That curve IS the function in its invariant space: 1-D, fully seeable, solvable once for all sizes.")
    print("This is f(g(h(D,n,V))): h -> J, g -> Ct(J), f -> the scaling. dia/pitch live inside h and the shape.")
    print("\nHONEST BOUNDS: fixed blade shape, induced velocity & Reynolds ignored -> the collapse is exact by")
    print("dynamic similarity. Add Re and Ct = Ct(J, Re): a surface, not a perfect curve (the drag-vs-viscosity")
    print("lesson again). Dimensional analysis found the GROUPS mechanically; the CURVE Ct(J) still needs the")
    print("physics/data - and DISCOVERING a NONLINEAR intermediate g from data alone (no given dimensions) is")
    print("the piece still unbuilt (latent-coordinate / autoencoder+SINDy territory).")


if __name__ == "__main__":
    main()
