r"""Diagnose-and-repair on the signal-flow graph — the unified optimizer, pure math (no hand-lists).

The coupled solve is a map  p -> y  (design params -> capability metrics). A mission is a set of
constraints  g_k(p) = have_k - req_k >= 0. When the current design fails some g_fail < 0 we do NOT try a
menu of alternatives. We do the mathematics:

  1. ROOT CAUSE   J_ki = d g_k / d p_i, assembled by finite-differencing the REAL solve (in normalized
                  param space so scales are comparable). Rank params by |d g_fail / d p_i|: that is the
                  lever that failed the mission — a number, not a guess.
  2. MOVABILITY   a param is immovable if it is pinned at its bound in the helping direction (a catalogue
                  limit). Otherwise it is movable.
  3. REPAIR       step the failing metric uphill WITHOUT breaking any satisfied requirement: project the
                  failing gradient onto the null space of the constraints the raw step would violate,
                        P = I - A^T (A A^T)^+ A ,   d = P * grad(g_fail),
                  clip to movable bounds, re-solve, re-linearize. Naive opt is the special case A = {} (P=I).
  4. ESCALATE     if ||d|| ~ 0 the failing gradient lies in the span of the binding constraints: no movable
                  parameter can improve the failing metric without breaking another -> parametric repair is
                  PROVABLY exhausted. Only then is a structural/mechanism change warranted.

Everything below runs on the real forge engine — the numbers are the engine's numbers.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

from uav import build_uav, capabilities, G   # noqa: E402
from solve import solve                       # noqa: E402

# design params the optimizer may move — EXACTLY the controllable design sliders.
# (payload, C_rate and n_rotors are held fixed: mission/pack constraints, not free design levers.)
PARAMS = ["D_in", "pitch_in", "Kv", "I_max", "S", "cap_mAh", "L_arm"]
BOUNDS = {"D_in": (8, 22), "pitch_in": (4, 14), "Kv": (150, 450), "I_max": (20, 90),
          "S": (4, 12), "cap_mAh": (2000, 16000), "L_arm": (0.15, 0.60)}
# which subsystem each lever belongs to (for the app's highlight)
OWNER = {"D_in": "propulsion", "pitch_in": "propulsion", "Kv": "propulsion", "I_max": "propulsion",
         "S": "energy", "cap_mAh": "energy", "L_arm": "structure"}
METRICS = ["a_max_g", "v_max", "endurance_min"]      # the constrained capabilities


def caps_of(cfg, mechanism="rotor"):
    sysm = build_uav(cfg, propulsion_mechanism=mechanism)
    bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    c = capabilities(sysm, bus)
    return {"a_max_g": c["a_max"] / G, "v_max": c["v_max"],
            "endurance_min": c["endurance"] / 60.0, "mass": c["mass"]}


def _norm(cfg):
    return np.array([(cfg[k] - BOUNDS[k][0]) / (BOUNDS[k][1] - BOUNDS[k][0]) for k in PARAMS])


def _denorm(x):
    cfg = {}
    for k, xi in zip(PARAMS, x):
        lo, hi = BOUNDS[k]
        cfg[k] = lo + float(np.clip(xi, 0, 1)) * (hi - lo)
    return cfg


def _cfg_from(base, x):
    cfg = dict(base)
    cfg.update(_denorm(x))
    return cfg


def jacobian(base, x, eps=0.02, mechanism="rotor"):
    """Forward-difference Jacobian J[metric][i] = d metric / d x_i over the real solve (normalized space)."""
    f0 = caps_of(_cfg_from(base, x), mechanism)
    J = {m: np.zeros(len(PARAMS)) for m in METRICS}
    for i in range(len(PARAMS)):
        xp = x.copy()
        step = eps if x[i] + eps <= 1.0 else -eps            # stay inside the box
        xp[i] = np.clip(x[i] + step, 0, 1)
        fp = caps_of(_cfg_from(base, xp), mechanism)
        for m in METRICS:
            J[m][i] = (fp[m] - f0[m]) / step
    return J, f0


def _reqs(mission):
    return {"a_max_g": mission["a_req"], "v_max": mission["v_req"], "endurance_min": mission["endur_req"]}


def diagnose(base, mission, mechanism="rotor"):
    """One-shot root-cause + movability + the proposed null-space repair direction (no iteration)."""
    reqs = _reqs(mission)
    x = _norm(base)
    J, f0 = jacobian(base, x, mechanism=mechanism)
    gaps = {m: f0[m] - reqs[m] for m in METRICS}
    fails = [m for m in METRICS if gaps[m] < -1e-6]
    fm = min(METRICS, key=lambda m: gaps[m] / max(reqs[m], 1e-6)) if fails else None

    levers = []
    if fm:
        g = J[fm]
        rng = {k: BOUNDS[k][1] - BOUNDS[k][0] for k in PARAMS}
        for i, k in enumerate(PARAMS):
            help_dir = 1 if g[i] > 0 else -1                  # direction that RAISES the failing metric
            at_bound = (help_dir > 0 and x[i] > 0.999) or (help_dir < 0 and x[i] < 0.001)
            levers.append({
                "param": k, "owner": OWNER[k],
                "dmetric_dparam": g[i] / rng[k],              # per real unit
                "sensitivity": abs(g[i]),                     # normalized (comparable)
                "help_dir": "+" if help_dir > 0 else "-",
                "movable": (not at_bound),
                "value": base[k],
            })
        levers.sort(key=lambda d: -d["sensitivity"])

    step_dir = _repair_direction(J, gaps, reqs, fm) if fm else None
    return {
        "caps": f0, "gaps": gaps, "reqs": reqs,
        "failing": fm, "all_fails": fails, "levers": levers,
        "repair_dir": step_dir,
    }


def _repair_direction(J, gaps, reqs, fm, step=0.06, margin=0.02):
    """Null-space repair direction: raise g_fail while holding the constraints the raw step would break."""
    n = len(PARAMS)
    grad = J[fm].copy()
    nrm = np.linalg.norm(grad)
    if nrm < 1e-9:
        return {"dir": np.zeros(n), "exhausted": True, "held": [], "reason": "failing metric insensitive to every param"}
    raw = grad / nrm
    # which satisfied constraints would the raw step push below requirement?
    held = []
    for m in METRICS:
        if m == fm:
            continue
        predicted = float(J[m] @ (step * raw))                # first-order change from the step
        margin_norm = margin * max(reqs[m], 1e-6)
        if gaps[m] + predicted < margin_norm:                 # would breach (or crowd) this requirement
            held.append(m)
    if held:
        A = np.array([J[m] for m in held])
        P = np.eye(n) - A.T @ np.linalg.pinv(A @ A.T) @ A
        d = P @ grad
    else:
        d = grad
    dn = np.linalg.norm(d)
    if dn < 1e-6:
        return {"dir": np.zeros(n), "exhausted": True, "held": held,
                "reason": "no movable param raises the failing metric without breaking a binding requirement"}
    return {"dir": d / dn, "exhausted": False, "held": held, "reason": ""}


def repair(base, mission, mechanism="rotor", max_iter=40, step=0.06):
    """Iterate the null-space repair until the mission is met or repair is provably exhausted.
    Returns (cfg, met, exhausted, history, info)."""
    reqs = _reqs(mission)
    x = _norm(base)
    history = []
    exhausted = False
    info = {}
    for it in range(max_iter):
        J, f0 = jacobian(base, x, mechanism=mechanism)
        gaps = {m: f0[m] - reqs[m] for m in METRICS}
        history.append({"iter": it, **{m: f0[m] for m in METRICS}, "mass": f0["mass"]})
        fails = [m for m in METRICS if gaps[m] < -1e-6]
        if not fails:
            return _cfg_from(base, x), True, False, history, {"iters": it, "held": info.get("held", [])}
        fm = min(METRICS, key=lambda m: gaps[m] / max(reqs[m], 1e-6))
        rd = _repair_direction(J, gaps, reqs, fm, step=step)
        info = {"failing": fm, "held": rd["held"], "reason": rd["reason"]}
        if rd["exhausted"]:
            exhausted = True
            break
        # line search along the null-space direction: accept if the failing metric improves
        d = rd["dir"]
        accepted = False
        s = step
        for _ in range(5):
            xn = np.clip(x + s * d, 0, 1)
            fn = caps_of(_cfg_from(base, xn), mechanism)
            if fn[fm] - reqs[fm] > gaps[fm] + 1e-9:            # failing metric got better
                x = xn
                accepted = True
                break
            s *= 0.5
        if not accepted:
            exhausted = True
            info["reason"] = info["reason"] or "step could not improve the failing metric within bounds"
            break
    cfg = _cfg_from(base, x)
    caps = caps_of(cfg, mechanism)
    met = all(caps[m] >= reqs[m] - 1e-6 for m in METRICS)
    return cfg, met, exhausted, history, info


# --------------------------------------------------------------- structural escalation (quad -> wing)
RHO, FM_H, ETA = 1.225, 0.70, 0.70


def wing_alternative(cfg, mission, cruise_v=20.0, LD=13.0, CL=0.9, Cd0=0.025, wing_kg_per_m2=1.8):
    """When parametric repair is exhausted on ENDURANCE, evaluate a fixed wing on the SAME battery+payload.
    Aerodynamic lift in forward flight: sustain power = cruise drag power (W/(L/D)+parasitic)*v/eta << hover.
    Returns the wing capability + whether it meets endurance (physics decides, no hand-picking)."""
    sysm = build_uav(cfg)
    bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    Wh = bus.get("usable_energy", 0.0) / 3600.0
    # iterate mass<->wing (wing mass depends on weight it must lift)
    m = bus["total_mass"]
    for _ in range(30):
        W = m * G
        A_w = 2 * W / (RHO * cruise_v ** 2 * CL)
        drag = W / LD + 0.5 * RHO * cruise_v ** 2 * Cd0 * A_w
        wing_mass = wing_kg_per_m2 * A_w + 0.15
        # replace the rotor/arm/frame support mass with the wing's, keep energy+payload
        m_new = (sysm.by_name()["energy"].state.get("mass", 0.0)
                 + cfg.get("payload", 0.6) + wing_mass)
        if abs(m_new - m) < 1e-4:
            m = m_new
            break
        m = m_new
    W = m * G
    A_w = 2 * W / (RHO * cruise_v ** 2 * CL)
    drag = W / LD + 0.5 * RHO * cruise_v ** 2 * Cd0 * A_w
    P_cruise = drag * cruise_v / ETA
    endurance_min = (Wh * 3600.0 * 0.85) / P_cruise / 60.0 if P_cruise > 0 else 0.0
    span = (A_w * 6.0) ** 0.5            # assume AR ~ 6 -> span = sqrt(A*AR)
    chord = A_w / span if span else 0.1
    return {"endurance_min": endurance_min, "mass": m, "wing_area": A_w, "span": span,
            "chord": chord, "cruise_v": cruise_v, "hover_capable": False,
            "meets_endurance": endurance_min >= mission["endur_req"]}


# --------------------------------------------------------------- headless self-test
if __name__ == "__main__":
    base = dict(D_in=13, pitch_in=6, Kv=300, I_max=45, S=6, cap_mAh=5000,
                C_rate=60, L_arm=0.30, payload=0.6, n_rotors=4)

    print("=" * 74)
    print("CASE 1 — mission the quad fails on AGILITY (parametric repair should fix it)")
    mission = {"a_req": 6.0, "v_req": 10.0, "endur_req": 15.0}
    d = diagnose(base, mission)
    print(f"  start: a_max {d['caps']['a_max_g']:.2f} g | v_max {d['caps']['v_max']:.1f} | "
          f"endur {d['caps']['endurance_min']:.1f} min | mass {d['caps']['mass']:.2f} kg")
    print(f"  FAILING METRIC: {d['failing']}   (need {mission['a_req']} g)")
    print("  root-cause levers (ranked by sensitivity of the failing metric):")
    for L in d["levers"][:5]:
        print(f"    {L['param']:8s} [{L['owner']:10s}] push {L['help_dir']}  "
              f"sens={L['sensitivity']:.3f}  {'movable' if L['movable'] else 'IMMOVABLE (at bound)'}")
    print(f"  hold (must not break): {d['repair_dir']['held']}")
    cfg, met, ex, hist, info = repair(base, mission)
    caps = caps_of(cfg)
    print(f"  REPAIR -> met={met} exhausted={ex} iters={len(hist)-1}")
    print(f"    a_max {caps['a_max_g']:.2f} g | v_max {caps['v_max']:.1f} | endur {caps['endurance_min']:.1f} min | mass {caps['mass']:.2f} kg")
    print(f"    changed: " + ", ".join(f"{k} {base[k]:.0f}->{cfg[k]:.1f}" for k in PARAMS if abs(cfg[k]-base[k]) > 1e-3*max(abs(base[k]),1)))

    print("=" * 74)
    print("CASE 2 — mission the quad CANNOT meet parametrically: 200 min endurance (should ESCALATE)")
    mission2 = {"a_req": 1.5, "v_req": 8.0, "endur_req": 200.0}
    cfg2, met2, ex2, hist2, info2 = repair(base, mission2)
    caps2 = caps_of(cfg2)
    print(f"  REPAIR -> met={met2} exhausted={ex2}  (best endurance {caps2['endurance_min']:.1f} min, need {mission2['endur_req']:.0f})")
    print(f"  reason: {info2.get('reason','')}")
    if not met2:
        w = wing_alternative(cfg2, mission2)
        print(f"  ESCALATE to fixed wing (physics, same battery+payload):")
        print(f"    wing endurance {w['endurance_min']:.1f} min | span {w['span']*100:.0f} cm | "
              f"area {w['wing_area']*1e4:.0f} cm^2 | mass {w['mass']:.2f} kg | meets={w['meets_endurance']}")
