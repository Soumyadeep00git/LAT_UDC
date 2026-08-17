r"""V3c — the GENERAL meta-requirement engine (a conservation-wall detector).

A meta-requirement is not a bad value (V1 fixes those) and not a bad structure (V2 fixes those). It is a
CONSERVED-BUDGET CONFLICT: the mission demands two capabilities that trade on an invariant fixed by the
current embodiment, so NO value and NO count can satisfy both at once. The only resolution is to add a
DEGREE OF FREEDOM the design does not have — a new axis that lets it sweep the trade instead of sitting at
one point on it.

This engine is domain-general and it is HONEST about how strongly each wall is established. Every wall it
reports carries a status:

  META_CONFIRMED   the real solve proves value+structure are exhausted and a grounded conserved budget is
                   over-saturated (seeker etendue; battery Ragone). This is a proven missing dimension.
  META_MODEL_GAP   the conserved trade is real physics, but the current reduced model cannot PRICE it, so
                   V1 meets the thresholds without ever seeing the conflict (fixed-pitch hover/dash: the
                   endurance model uses momentum-theory hover power, which is pitch-independent). The honest
                   output is: the design is missing an axis AND the model is missing the fidelity to score
                   it. Confirming it needs a higher-fidelity model.
  (no wall)        a value (V1) or structure (V2) already suffices — no new dimension is needed.

Nothing is hand-flagged. Give it a design and a mission; it runs the real V1/V2 and decides.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import diagnose
import physics_adapt
from uav import (build_uav, capabilities, motor_solve, G, IN2M, FM_HOVER, RHO_AIR,
                 SEEKER_DEFAULTS, SEEKER_TARGET_M)
from solve import solve

try:
    import library as _lib
except Exception:
    _lib = None

SEED = {"current": 0.0, "total_mass": 4.0}
PIXELS_MAX = 8192          # catalogue ceiling on the pure-VALUE option for the detector array
N_DET = 2.0               # Johnson detection pixels-on-target

# Ragone frontier (specific power W/kg -> max specific energy Wh/kg): Li-ion energy cell 250 @ 750,
# LiPo 180 @ 4000, power cell 150 @ 6000, supercapacitor 7 @ 12000.
_RAGONE = [(300.0, 260.0), (750.0, 250.0), (2000.0, 200.0), (4000.0, 180.0),
           (6000.0, 150.0), (9000.0, 60.0), (12000.0, 7.0)]


def _ground(node_id):
    if _lib is None or node_id not in _lib.A.ARCHIVE:
        return {"node": node_id, "in_library": False}
    return {"node": node_id, "in_library": True,
            "descent_depth": max((d for _, _, d in _lib.descent(node_id)), default=0)}


def ragone_max_energy(sp_wkg):
    pts = _RAGONE
    if sp_wkg <= pts[0][0]:
        return pts[0][1]
    if sp_wkg >= pts[-1][0]:
        return pts[-1][1]
    for (p0, e0), (p1, e1) in zip(pts, pts[1:]):
        if p0 <= sp_wkg <= p1:
            return e0 + (sp_wkg - p0) / (p1 - p0) * (e1 - e0)
    return pts[-1][1]


def operating_point(cfg):
    """The real solved hover operating point + pack figures — the numbers the invariants reason over."""
    sysm = build_uav(cfg)
    bus = solve(sysm, seed=dict(SEED))
    cap = capabilities(sysm, bus)
    prop = sysm.by_name()["propulsion"]
    table, motor, V = prop.state["_table"], prop.state["_motor"], prop.state["_V"]
    op = motor_solve(V, motor, lambda rpm: table.torque(rpm, 0.0), 1.0)
    n = prop.params["n_rotors"]
    D_m = prop.params["D_in"] * IN2M
    mass = bus["total_mass"]
    A_total = n * math.pi * (D_m / 2.0) ** 2
    P_hover = (mass * G) ** 1.5 / (FM_HOVER * math.sqrt(2 * RHO_AIR * A_total)) if A_total > 0 else 1e9
    whkg = cfg.get("wh_per_kg", 400.0)
    pack_wh = bus.get("usable_energy", 0.0) / 3600.0 / 0.85
    pack_mass = pack_wh / whkg if whkg > 0 else 0.0
    return {"caps": {"a_max_g": cap["a_max"] / G, "v_max": cap["v_max"],
                     "endurance_min": cap["endurance"] / 60.0, "mass": mass},
            "rpm_hover": op.rpm, "D_m": D_m, "D_in": prop.params["D_in"], "pitch_in": cfg["pitch_in"],
            "n": n, "V": V, "I_max": cfg["I_max"], "P_hover": P_hover, "whkg": whkg,
            "pack_wh": pack_wh, "pack_mass": pack_mass}


# ------------------------------------------------------------------ invariant 1: seeker (etendue / SBP)
def invariant_seeker(cfg, mission, best_design, solve_exhausted):
    need = {k: mission[k] for k in ("detect_range_m", "search_halfangle_deg", "max_revisit_s") if k in mission}
    if len(need) < 2:
        return {"engaged": False, "name": "seeker space-bandwidth (etendue)"}
    R = need["detect_range_m"]
    th = math.radians(need["search_halfangle_deg"])
    omega_req = 2 * math.pi * (1 - math.cos(th))
    frame_hz = cfg.get("frame_rate_hz", SEEKER_DEFAULTS["frame_rate_hz"])
    ifov_need = SEEKER_TARGET_M / (N_DET * R)

    def coverage(npx):
        return (npx * ifov_need) ** 2

    cov0, cov_max = coverage(cfg.get("n_pixels", SEEKER_DEFAULTS["n_pixels"])), coverage(PIXELS_MAX)
    if cov0 >= omega_req:
        return {"engaged": True, "status": "no wall", "name": "seeker space-bandwidth (etendue)",
                "local_fix": "the current sensor already covers the region at detection resolution"}
    if cov_max >= omega_req:                                    # a VALUE (more pixels) still resolves it
        need_px = math.sqrt(omega_req) / ifov_need
        return {"engaged": True, "status": "no wall", "name": "seeker space-bandwidth (etendue)",
                "subsystem": "seeker",
                "local_fix": f"raise n_pixels to ~{need_px:.0f} (<= {PIXELS_MAX}) — a VALUE fix, no new DOF"}
    tiles = omega_req / cov_max
    tau = tiles / frame_hz
    return {
        "engaged": True, "status": "META_CONFIRMED", "name": "seeker space-bandwidth (etendue)",
        "subsystem": "seeker", "grounded": _ground("optics.space_bandwidth_product"),
        "confirmed_by": "solve (optics): even at the pixel ceiling the static field of view < search cone",
        "budget": f"SBP = n_pixels (<= {PIXELS_MAX}) fixes resolution x instantaneous coverage",
        "demand": (f"detect {R:.0f} m needs IFOV {ifov_need*1e3:.3f} mrad; the {2*need['search_halfangle_deg']:.0f} "
                   f"deg cone is {omega_req:.2f} sr, but even {PIXELS_MAX} px cover only {cov_max:.3f} sr at once"),
        "missing_dof": "ADD A TEMPORAL / SCAN DEGREE OF FREEDOM (angular motion over time)",
        "quantify": f"cover {omega_req:.2f} sr in {tiles:.0f} looks -> revisit {tau:.2f} s "
                    f"(need <= {need['max_revisit_s']} s: {'OK' if tau <= need['max_revisit_s'] else 'needs faster scan/frame'})",
        "hardware": "gimbal | rotating mount | electronic beam-steering  (architecture picks; physics only asks for motion)",
    }


# ------------------------------------------------------------------ invariant 2: battery (Ragone)
def invariant_ragone(cfg, mission, best_design, solve_exhausted):
    if "endur_req" not in mission or "a_req" not in mission:
        return {"engaged": False, "name": "battery Ragone (energy vs power)"}
    if not (mission["a_req"] >= 4.0 and mission["endur_req"] >= 20.0):
        return {"engaged": False, "name": "battery Ragone (energy vs power)"}
    if not solve_exhausted:
        return {"engaged": True, "status": "no wall", "name": "battery Ragone (energy vs power)",
                "subsystem": "energy", "local_fix": "V1/V2 met the mission — one chemistry suffices"}
    op = operating_point(best_design)
    if op["pack_mass"] <= 0:
        return {"engaged": False, "name": "battery Ragone (energy vs power)"}
    burst_W = op["n"] * op["V"] * op["I_max"]
    sp_demand = burst_W / op["pack_mass"]
    e_need = op["P_hover"] * (mission["endur_req"] * 60.0) / 3600.0 / op["pack_mass"]
    e_frontier = ragone_max_energy(sp_demand)
    if e_need <= e_frontier:
        return {"engaged": True, "status": "no wall", "name": "battery Ragone (energy vs power)",
                "subsystem": "energy",
                "local_fix": f"one chemistry gives {e_frontier:.0f} Wh/kg at {sp_demand:.0f} W/kg >= {e_need:.0f} needed"}
    return {
        "engaged": True, "status": "META_CONFIRMED", "name": "battery Ragone (energy vs power)",
        "subsystem": "energy", "grounded": _ground("electrochemistry_batteries.ragone_tradeoff"),
        "confirmed_by": "solve (V1 exhausted + V2 infeasible; Ragone frontier over-saturated)",
        "budget": "one chemistry = one point on the Ragone frontier; energy and power trade",
        "demand": (f"burst needs {sp_demand:.0f} W/kg; the frontier gives only {e_frontier:.0f} Wh/kg there, "
                   f"but endurance needs {e_need:.0f} Wh/kg from the same pack"),
        "missing_dof": "ADD A SECOND ENERGY DOMAIN (energy channel || power channel) decoupling energy from power",
        "quantify": "energy cells (~250 Wh/kg) for cruise + power cells/supercap (~6000 W/kg) for burst; "
                    "one pack cannot be both",
        "hardware": "hybrid pack | supercapacitor buffer | dual-chemistry bus  (architecture picks; physics asks to split energy from power)",
    }


# ------------------------------------------------------------------ invariant 3: rotor (advance-ratio / pitch)
def invariant_pitch(cfg, mission, best_design, solve_exhausted):
    if "v_req" not in mission or "endur_req" not in mission:
        return {"engaged": False, "name": "propeller advance-ratio efficiency"}
    if not (mission["v_req"] >= 30.0 and mission["endur_req"] >= 8.0):
        return {"engaged": False, "name": "propeller advance-ratio efficiency"}
    op = operating_point(best_design)
    rps = op["rpm_hover"] / 60.0
    if rps <= 0 or op["D_m"] <= 0:
        return {"engaged": False, "name": "propeller advance-ratio efficiency"}
    J_dash = mission["v_req"] / (rps * op["D_m"])
    J_hover = 0.12
    pitch_dash = (J_dash / 0.8) * op["D_in"]
    pitch_hover = (J_hover / 0.8) * op["D_in"]
    spread = pitch_dash - pitch_hover
    if spread <= 2.0:
        return {"engaged": True, "status": "no wall", "name": "propeller advance-ratio efficiency",
                "subsystem": "propulsion", "local_fix": f"one pitch spans hover<->dash within {spread:.1f} in"}
    # real trade, but the reduced model computes hover power from momentum theory (pitch-independent),
    # so it never prices the hover-efficiency loss -> V1 meets the thresholds without seeing the conflict.
    return {
        "engaged": True, "status": "META_MODEL_GAP", "name": "propeller advance-ratio efficiency",
        "subsystem": "propulsion", "grounded": _ground("aerodynamics.propeller_advance_efficiency"),
        "confirmed_by": "UNPRICED by the reduced model: capabilities() hover power = momentum theory "
                        "(fixed figure-of-merit), independent of pitch - the conflict is invisible to the solve",
        "budget": "a fixed pitch peaks at one advance ratio J* ~ 0.8*(P/D); one value, one peak",
        "demand": (f"hover wants J~{J_hover:.2f} (pitch ~{pitch_hover:.1f} in); dash at {mission['v_req']:.0f} m/s "
                   f"wants J~{J_dash:.2f} (pitch ~{pitch_dash:.1f} in) at {op['rpm_hover']:.0f} rpm"),
        "missing_dof": "ADD A PITCH-ACTUATION DEGREE OF FREEDOM (pitch as a function of flight state)",
        "quantify": f"a single pitch must span {spread:.1f} in between the two efficient points; variable pitch "
                    f"tracks J. (To SCORE this, endurance needs a pitch-aware/BEMT efficiency model.)",
        "hardware": "variable-pitch hub | swashplate (collective) | tilt  (architecture picks; physics asks for pitch motion)",
    }


INVARIANTS = [invariant_seeker, invariant_ragone, invariant_pitch]


def meta_requirements(cfg, mission):
    """Full escalation: V1 (value) -> V2 (structure) -> V3c (missing dimension). Returns the verdict."""
    out = {"mission": mission}
    airframe = any(k in mission for k in ("a_req", "v_req", "endur_req"))
    v1_met = v2_feasible = False
    best_design = cfg
    if airframe:
        c1, v1_met, ex1, _h, i1 = diagnose.repair(cfg, mission)
        out["V1"] = {"met": v1_met, "exhausted": ex1, "failing": i1.get("failing")}
        if not v1_met:
            best, _c, rule = physics_adapt.adapt(cfg, mission)
            v2_feasible = best["feasible"]
            best_design = best["cfg"]
            out["V2"] = {"feasible": v2_feasible, "n_rotors": best["n"], "rule": rule}
        else:
            best_design = c1
    solve_exhausted = airframe and (not v1_met) and (not v2_feasible)

    walls = [inv(cfg, mission, best_design, solve_exhausted) for inv in INVARIANTS]
    out["walls"] = walls
    out["confirmed"] = [w for w in walls if w.get("status") == "META_CONFIRMED"]
    out["model_gaps"] = [w for w in walls if w.get("status") == "META_MODEL_GAP"]

    if out["confirmed"]:
        out["resolved_by"] = "V3c (missing dimension) - CONFIRMED"
    elif airframe and v1_met:
        out["resolved_by"] = "V1 (value)"
    elif airframe and v2_feasible:
        out["resolved_by"] = "V2 (structure)"
    elif airframe:
        out["resolved_by"] = "unresolved (no confirmed trade-invariant; deeper escalation needed)"
    else:
        out["resolved_by"] = "no airframe mission posed"
    return out


if __name__ == "__main__":
    import v3c_demo
    v3c_demo.main()
