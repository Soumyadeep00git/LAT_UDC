r"""Dimensional-analysis kernel (Buckingham-Pi) — derive the FORM of physical laws from units alone.

No library of named laws. Given the variables of a problem and their dimensions [M, L, T], this finds the
dimensionless groups (the null space of the dimensional matrix) and rearranges them into the governing
relation. Single group -> a law up to a constant; extra groups -> a law up to an unknown function of them.

This is "physics without the library": the relation is derived from first principles (dimensional
homogeneity), and any candidate that isn't dimensionally consistent simply has no null vector -> rejected.
Honest boundary: dimensional analysis gives the STRUCTURE (scaling), never the numeric constant/function.
"""
from __future__ import annotations

from fractions import Fraction as Fr
from math import gcd

BASE = ("M", "L", "T")
DIM = {
    "thrust": (1, 1, -2), "drag": (1, 1, -2), "force": (1, 1, -2), "weight": (1, 1, -2),
    "density": (1, -3, 0), "diameter": (0, 1, 0), "length": (0, 1, 0), "area": (0, 2, 0),
    "angular_speed": (0, 0, -1), "velocity": (0, 1, -1), "power": (1, 2, -3),
    "viscosity": (1, -1, -1), "gravity": (0, 1, -2),
}


def _nullspace(A):
    """Rational null space of matrix A (list of rows). Returns basis vectors (lists of Fraction)."""
    A = [[Fr(x) for x in row] for row in A]
    rows, cols = len(A), len(A[0])
    pivots, r = [], 0
    for c in range(cols):
        piv = next((i for i in range(r, rows) if A[i][c] != 0), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        A[r] = [x / A[r][c] for x in A[r]]
        for i in range(rows):
            if i != r and A[i][c] != 0:
                f = A[i][c]
                A[i] = [a - f * b for a, b in zip(A[i], A[r])]
        pivots.append(c); r += 1
    free = [c for c in range(cols) if c not in pivots]
    basis = []
    for fc in free:
        v = [Fr(0)] * cols
        v[fc] = Fr(1)
        for pi, pc in enumerate(pivots):
            v[pc] = -A[pi][fc]
        basis.append(v)
    return basis


def _ints(v):
    """Scale a rational vector to the smallest integer vector."""
    den = 1
    for x in v:
        den = den * x.denominator // gcd(den, x.denominator)
    w = [int(x * den) for x in v]
    g = 0
    for x in w:
        g = gcd(g, abs(x))
    return [x // g for x in w] if g else w


def pi_groups(variables):
    A = [[DIM[var][d] for var in variables] for d in range(len(BASE))]
    return [_ints(v) for v in _nullspace(A)]


def _fmt(variables, exps):
    num = [f"{v}^{e}" if e != 1 else v for v, e in zip(variables, exps) if e > 0]
    den = [f"{v}^{-e}" if e != -1 else v for v, e in zip(variables, exps) if e < 0]
    s = "*".join(num) or "1"
    return s + (" / (" + "*".join(den) + ")" if den else "")


def derive(target, others):
    variables = [target] + list(others)
    groups = pi_groups(variables)
    tg = next((g for g in groups if g[0] != 0), None)
    if tg is None:
        return None, groups
    a = tg[0]
    rhs = []
    for v, e in zip(others, tg[1:]):
        p = Fr(-e, a)
        if p != 0:
            rhs.append(f"{v}^{p}" if p != 1 else v)
    extra = [g for g in groups if g is not tg]
    law = f"{target} = C * " + ("*".join(rhs) or "1")
    if extra:
        law += "  * f(" + ", ".join(_fmt(variables, g) for g in extra) + ")"
    return law, groups


def _demo(title, target, others):
    law, groups = derive(target, others)
    print(f"\n  {title}")
    print(f"    variables: {[target] + list(others)}")
    print(f"    Pi groups: {[_fmt([target]+list(others), g) for g in groups]}")
    print(f"    => {law}")


if __name__ == "__main__":
    print("DIMENSIONAL-ANALYSIS KERNEL — deriving laws from UNITS ALONE (no library)\n")
    _demo("rotor thrust", "thrust", ["density", "diameter", "angular_speed"])
    _demo("aerodynamic drag", "drag", ["density", "velocity", "area"])
    _demo("hover power (momentum theory)", "power", ["weight", "density", "area"])
    _demo("drag with viscosity (2 groups: drag = C*rho v^2 L^2 * f(a Reynolds-type group))",
          "drag", ["density", "velocity", "length", "viscosity"])
    print("\n  Every single-group law the library hard-codes, re-derived from dimensions. Honest boundaries:")
    print("  (1) the constant C and any f(...) of extra groups is NOT set by dimensions (needs theory/CFD);")
    print("  (2) the multi-group BASIS isn't unique — it found a valid 2nd group but not the canonical")
    print("      Reynolds isolation (picking the 'named' basis is an extra recognition step).")
