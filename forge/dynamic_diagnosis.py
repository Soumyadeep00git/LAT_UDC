r"""DYNAMIC missing-dimension diagnosis - field.py's logic, carried into the TIME domain.

field.py (the steady field layer) diagnoses a MISSING DEGREE OF FREEDOM like this: two imposed
DEMANDS are each satisfiable ALONE but not jointly; the binding law between them cannot be relaxed by
tuning an existing value, only by ADDING AN AXIS (a new free param). That is a statement about a steady
algebraic field.

This module makes the SAME statement about a system that evolves in TIME, and proves it with REAL
trajectories from OpenModelica (via forge/modelica_backend.py - a mature DASSL/IDA integrator, not a
hand-rolled one). See [[field-layer]].

The case (a 2nd-order closed-loop plant, m*x'' = k*(r-x) - c*x'):
  - AVAILABLE AXIS : k  (proportional stiffness / gain)  - a free param we may tune.
  - PLANT CONSTANT : c  (damping) is present but FIXED and small - it is a plant property, not a
                     control axis (the analogue of field.py's immutable LAW linkage).
  - DEMAND A       : respond quickly   - rise to 90% of the setpoint within T_rise.
  - DEMAND B       : do not overshoot  - peak overshoot <= Mp_max.

Tuning k trades one demand against the other: high k -> fast rise but large overshoot; low k -> small
overshoot but sluggish. Each demand is reachable ALONE by some k; NO single k meets both. The binding
invariant is the fixed damping. Relaxing it means PROMOTING c to a free axis (adding a rate/damping
degree of freedom) - the time-domain version of field.py's relax_with_new_dof. Re-simulate: both met.

Every number printed below comes from a real solve. Honest status: CONFIRMED (solver-proven) means the
trajectories themselves showed the disjoint feasibility and the fix; MODEL-GAP means they did not and
the hypothesis was not borne out.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass

import numpy as np

from modelica_backend import second_order_plant, simulate

try:
    from scipy.integrate import solve_ivp
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False


# ---------------------------------------------------------------- demands (in time)
T_RISE = 2.0       # s   - demand A: reach 90% of setpoint by this time
MP_MAX = 20.0      # %   - demand B: peak overshoot at most this
SETPOINT = 1.0
C_FIXED = 0.4      # fixed plant damping (small) - NOT a control axis in the base structure
STOP = 12.0
INTERVALS = 1200


@dataclass
class Metrics:
    k: float
    c: float
    rise90: float      # s (inf if never reaches 90%)
    overshoot: float   # %
    backend: str       # which solver produced this trajectory


def _metrics_from(t, x, k, c, backend):
    r = SETPOINT
    peak = float(np.max(x))
    overshoot = max(0.0, (peak - r) / r * 100.0)
    idx = np.where(x >= 0.9 * r)[0]
    rise = float(t[idx[0]]) if idx.size else float("inf")
    return Metrics(k, c, rise, overshoot, backend)


def _scipy_run(k, c):
    """LABELED FALLBACK ONLY. Mature integrator (scipy/LSODA), used if OpenModelica is unavailable."""
    def rhs(_t, y):
        x, v = y
        return [v, (k * (SETPOINT - x) - c * v)]
    sol = solve_ivp(rhs, (0.0, STOP), [0.0, 0.0], method="LSODA",
                    t_eval=np.linspace(0.0, STOP, INTERVALS + 1), rtol=1e-8, atol=1e-10)
    return sol.t, sol.y[0]


def run_case(k, c, case_root):
    """Simulate one (k, c) plant. OpenModelica first; scipy fallback only if that truly fails."""
    case = os.path.join(case_root, f"k{k:g}_c{c:g}".replace(".", "p"))
    sysd = second_order_plant(k=k, c=c, setpoint=SETPOINT)
    tr = simulate(sysd, case, stop_time=STOP, intervals=INTERVALS)
    if tr.ok:
        return _metrics_from(tr.t, tr.col("x"), k, c, "OpenModelica")
    if _HAVE_SCIPY:
        t, x = _scipy_run(k, c)
        return _metrics_from(t, x, k, c, "scipy-FALLBACK")
    raise RuntimeError(f"no backend produced a trajectory for k={k}, c={c}: {tr.reason}")


def main():
    root = os.path.join(tempfile.gettempdir(), "dyn_diag")
    os.makedirs(root, exist_ok=True)

    print("=" * 78)
    print("DYNAMIC MISSING-DIMENSION DIAGNOSIS  (field.py's logic, in the TIME domain)")
    print("=" * 78)
    print("Plant : m*x'' = k*(r - x) - c*x'   (m=1, r=%.1f, released from rest)" % SETPOINT)
    print("Axis  : k (stiffness/gain) is the ONLY free control axis.")
    print("        c (damping) is a FIXED plant property, c = %.2f  (the immutable 'law')." % C_FIXED)
    print("Demands: A) rise to 90%% within %.1f s   B) peak overshoot <= %.0f%%" % (T_RISE, MP_MAX))
    print("-" * 78)

    # --- 1. sweep the single available axis k (real trajectories) --------------------------------
    k_sweep = [0.1, 0.2, 0.4, 0.8, 1.5, 3.0, 6.0, 12.0]
    print("Sweeping k with c fixed = %.2f  (every row is a real solve):" % C_FIXED)
    print("   %-8s %-14s %-8s %-12s %-8s %-8s" % ("k", "backend", "rise90", "overshoot", "A ok?", "B ok?"))
    rows = []
    backends = set()
    for k in k_sweep:
        m = run_case(k, C_FIXED, root)
        backends.add(m.backend)
        a_ok = m.rise90 <= T_RISE
        b_ok = m.overshoot <= MP_MAX
        rows.append((m, a_ok, b_ok))
        rise_s = "%.3f" % m.rise90 if np.isfinite(m.rise90) else "never"
        print("   %-8g %-14s %-8s %-12s %-8s %-8s"
              % (k, m.backend, rise_s, "%.1f%%" % m.overshoot, "YES" if a_ok else "no",
                 "YES" if b_ok else "no"))

    feasible_A = [r[0].k for r in rows if r[1]]
    feasible_B = [r[0].k for r in rows if r[2]]
    joint = [r[0].k for r in rows if r[1] and r[2]]
    print("-" * 78)
    print("Demand A (fast rise) reachable alone at k in: %s" % (feasible_A or "NONE"))
    print("Demand B (low overshoot) reachable alone at k in: %s" % (feasible_B or "NONE"))
    print("Both A and B at the SAME k: %s" % (joint or "NONE - disjoint over the swept axis"))

    # --- 2. classify, mirroring field.py.diagnose ------------------------------------------------
    each_alone = bool(feasible_A) and bool(feasible_B)
    conflict = each_alone and not joint
    print("-" * 78)
    if conflict:
        print("READING: each demand is satisfiable ALONE but NOT jointly by tuning k.")
        print("         Same shape as field.py MISSING_DOF: the structure is missing a DEGREE OF")
        print("         FREEDOM. The binding invariant is the fixed damping c (the plant 'law').")
        print("         It cannot be relaxed by tuning k - only by ADDING AN AXIS: a damping / rate DOF.")
    elif joint:
        print("READING: a single k already meets both demands - no missing dimension here.")
        print("STATUS: MODEL-GAP (the posed conflict did not materialise on real trajectories).")
        return
    else:
        print("READING: a demand is unreachable even alone over the swept axis - a different defect.")
        print("STATUS: MODEL-GAP (not the each-alone-but-not-jointly signature).")
        return

    # --- 3. relax: PROMOTE damping to a free axis and re-simulate (real trajectories) ------------
    # Pick the fastest-rising k (satisfies A) and search the NEW axis c to also satisfy B.
    k_fast = max(feasible_A)
    print("-" * 78)
    print("RELAX: add the damping/rate axis c as a free DOF; hold k = %g (fast rise, meets A)." % k_fast)
    print("       Search c for the smallest value that also meets B (real solves):")
    print("   %-8s %-14s %-8s %-12s %-8s %-8s" % ("c", "backend", "rise90", "overshoot", "A ok?", "B ok?"))
    fixed_point = None
    for c in [0.4, 0.8, 1.2, 1.8, 2.4, 3.2, 4.2]:
        m = run_case(k_fast, c, root)
        backends.add(m.backend)
        a_ok = m.rise90 <= T_RISE
        b_ok = m.overshoot <= MP_MAX
        rise_s = "%.3f" % m.rise90 if np.isfinite(m.rise90) else "never"
        print("   %-8g %-14s %-8s %-12s %-8s %-8s"
              % (c, m.backend, rise_s, "%.1f%%" % m.overshoot, "YES" if a_ok else "no",
                 "YES" if b_ok else "no"))
        if a_ok and b_ok:
            fixed_point = m
            break

    print("=" * 78)
    solver_proven = "OpenModelica" in backends and all(b != "scipy-FALLBACK" for b in backends)
    backend_note = ("OpenModelica (omc, WSL) - mature DASSL integrator"
                    if backends == {"OpenModelica"} else
                    "MIXED / FALLBACK: %s" % sorted(backends))
    if fixed_point is not None:
        print("RESULT: with the added damping axis, k=%g AND c=%g meet BOTH demands:"
              % (fixed_point.k, fixed_point.c))
        print("        rise90 = %.3f s (<= %.1f)   overshoot = %.1f%% (<= %.0f%%)"
              % (fixed_point.rise90, T_RISE, fixed_point.overshoot, MP_MAX))
        print("        Adding one axis turned an over-determined time-domain conflict into a")
        print("        solvable one - exactly field.py.relax_with_new_dof, now proven over time.")
        if solver_proven:
            print("STATUS: CONFIRMED (solver-proven). Backend: %s." % backend_note)
        else:
            print("STATUS: CONFIRMED via %s. NOTE: at least one row used the LABELED FALLBACK;" % backend_note)
            print("        OpenModelica wiring is the intended primary path.")
    else:
        print("RESULT: even with the added damping axis, no c met both demands at k=%g." % k_fast)
        print("STATUS: MODEL-GAP (the added axis did not resolve the conflict as hypothesised).")
    print("=" * 78)


if __name__ == "__main__":
    main()
