r"""V3c — a GENERIC, PROGRAMMABLE, UNIFORM meta-requirement DIAGNOSTIC.

V3c only diagnoses. It answers one question about a failed/limited design: is this a bad VALUE (V1's job),
a bad STRUCTURE (V2's job), or is the design MISSING A DEGREE OF FREEDOM — an axis no value or count can add?

There is ONE algorithm. It is not three hand-written domain checks. A domain is added as DATA: a
`TradeInvariant` record grounded in a library node, declaring
  - engaged(cfg, mission)      when this trade is even relevant to the mission,
  - grid(ctx)                  the design's CURRENT free configuration space (its value levers), sampled,
  - constraints                individually-satisfiable mission demands, each a predicate over a config
                               point that returns True / False / None (None = the reduced model cannot
                               PRICE this demand),
  - conflict_axis              for a mutually-exclusive constraint pair, the missing DEGREE OF FREEDOM.

The uniform engine (`diagnose_invariant`) then runs the SAME steps for every domain:
  1. is the trade engaged? if not, skip.
  2. sample the current free configuration space (the value option, honestly bounded by catalogue limits).
  3. evaluate every mission constraint at every configuration point (using the REAL solve where the model
     can price it).
  4. if some single configuration satisfies ALL priceable constraints  -> NO WALL (a value fixes it).
  5. else if a PAIR of constraints is each satisfiable alone but NEVER together -> CONFLICT: the design is
     missing the axis named for that pair. This is a confirmed missing dimension.
  6. if a constraint is UNPRICEABLE (None everywhere) -> MODEL_GAP: the trade is real but the current
     model cannot score it; honest, not overclaimed.

The engine has no domain knowledge. The physics lives entirely in the data records (grounded closures).
That is the honest line: the ALGORITHM is generic and uniform; the per-domain physics is declared DATA,
exactly as in V3d (the law FORM is generic; the constant is empirical).
"""
from __future__ import annotations

import itertools
import math
import os
import sys
from dataclasses import dataclass
from typing import Callable

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
N_DET = 2.0
# empirical Ragone frontier (the irreducible constant, like V3d's C): (specific power W/kg, specific energy Wh/kg)
_RAGONE = [(300.0, 260.0), (750.0, 250.0), (2000.0, 200.0), (4000.0, 180.0),
           (6000.0, 150.0), (9000.0, 60.0), (12000.0, 7.0)]


def _ground(node_id):
    if _lib is None or node_id not in _lib.A.ARCHIVE:
        return {"node": node_id, "in_library": False}
    return {"node": node_id, "in_library": True,
            "descent_depth": max((d for _, _, d in _lib.descent(node_id)), default=0)}


def operating_point(cfg):
    """The real solved hover operating point + pack figures — shared context the closures read."""
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
    return {"rpm_hover": op.rpm, "D_m": D_m, "D_in": prop.params["D_in"], "n": n, "V": V,
            "I_max": cfg["I_max"], "P_hover": P_hover, "pack_mass": pack_mass}


# ====================================================================== the uniform data record
@dataclass
class TradeInvariant:
    key: str
    name: str
    subsystem: str
    node: str                                   # library node it is grounded in
    engaged: Callable                           # (cfg, mission) -> bool
    context: Callable                           # (cfg, mission, best_design) -> ctx dict
    grid: Callable                              # (ctx) -> list[dict]  (the design's free config space)
    constraints: list                           # [(name, fn(point, ctx) -> bool|None, demand_text)]
    conflict_axis: dict                         # frozenset({c1, c2}) -> "missing DOF text"


# ====================================================================== the ONE engine
def diagnose_invariant(inv, cfg, mission, best_design):
    if not inv.engaged(cfg, mission):
        return {"key": inv.key, "name": inv.name, "engaged": False}

    ctx = inv.context(cfg, mission, best_design)
    grid = inv.grid(ctx)
    cnames = [c[0] for c in inv.constraints]
    fns = {c[0]: c[1] for c in inv.constraints}
    demand_txt = {c[0]: c[2] for c in inv.constraints}

    evals = [(pt, {c: fns[c](pt, ctx) for c in cnames}) for pt in grid]
    priceable = [c for c in cnames if any(r[c] is not None for _, r in evals)]
    unpriceable = [c for c in cnames if c not in priceable]

    def met(c):
        return [pt for pt, r in evals if r[c] is True]

    evidence = {c: f"{len(met(c))}/{len(grid)} configs satisfy it" for c in priceable}

    # step 4 — does any single configuration satisfy ALL priceable constraints?
    if not unpriceable:
        joint = [pt for pt, r in evals if all(r[c] for c in cnames)]
        if joint:
            return {"key": inv.key, "name": inv.name, "engaged": True, "status": "no_wall",
                    "subsystem": inv.subsystem, "evidence": evidence,
                    "why": "a single configuration satisfies every constraint — a VALUE fix, no new axis",
                    "example_config": joint[0]}
        # step 4b — a constraint met by NO configuration is an absolute limit of this embodiment class,
        # not a trade a new axis would relax (adding a scan/hybrid DOF cannot store energy that no cell has)
        zero = [c for c in priceable if not met(c)]
        if zero:
            return {"key": inv.key, "name": inv.name, "engaged": True, "status": "ABSOLUTE_LIMIT",
                    "subsystem": inv.subsystem, "grounded": _ground(inv.node), "infeasible": zero,
                    "evidence": evidence,
                    "why": f"constraint(s) {zero} are unmet by EVERY configuration of the current embodiment "
                           f"— an absolute limit of this class, not a trade a new axis would relax"}
        # step 5 — a mutually-exclusive pair, each satisfiable alone, never together
        for a, b in itertools.combinations(priceable, 2):
            both = [pt for pt, r in evals if r[a] and r[b]]
            if met(a) and met(b) and not both:
                return {"key": inv.key, "name": inv.name, "engaged": True, "status": "CONFLICT",
                        "subsystem": inv.subsystem, "grounded": _ground(inv.node),
                        "conflict_pair": (a, b),
                        "demands": (demand_txt[a], demand_txt[b]),
                        "evidence": {a: evidence[a], b: evidence[b], "jointly": "0 configs satisfy both"},
                        "missing_dof": inv.conflict_axis.get(frozenset((a, b)), "a new degree of freedom"),
                        "why": "each demand is reachable alone but no single configuration reaches both"}
        return {"key": inv.key, "name": inv.name, "engaged": True, "status": "no_conflict",
                "subsystem": inv.subsystem, "evidence": evidence}

    # step 6 — an unpriceable constraint: real trade the model cannot score
    up = unpriceable[0]
    partner = next((c for c in priceable), None)
    pair = frozenset([up, partner]) if partner else frozenset([up])
    return {"key": inv.key, "name": inv.name, "engaged": True, "status": "MODEL_GAP",
            "subsystem": inv.subsystem, "grounded": _ground(inv.node),
            "conflict_pair": (up, partner) if partner else (up,),
            "unpriceable": up,
            "missing_dof": inv.conflict_axis.get(pair, "a new degree of freedom"),
            "why": f"constraint '{up}' is unpriceable in the reduced model, so the conflict cannot be "
                   f"confirmed by the solve - the trade is real but the model lacks the fidelity to score it",
            "evidence": evidence}


# ====================================================================== the DATA: three grounded specs
# ---- optics: detection resolution vs instantaneous coverage on a fixed sensor (space-bandwidth) ----
def _seeker_engaged(cfg, m):
    return sum(k in m for k in ("detect_range_m", "search_halfangle_deg")) >= 2


def _seeker_ctx(cfg, m, best):
    th = math.radians(m["search_halfangle_deg"])
    return {"R": m["detect_range_m"], "omega_req": 2 * math.pi * (1 - math.cos(th)),
            "pp": cfg.get("pixel_pitch_um", SEEKER_DEFAULTS["pixel_pitch_um"]) * 1e-6, "target": SEEKER_TARGET_M}


def _seeker_grid(ctx):                                   # the seeker's real value levers (catalogue)
    return [{"focal_mm": f, "n_pixels": n}
            for f in (8, 16, 25, 50, 100, 200) for n in (640, 1280, 1920, 3840, 8192)]


def _seeker_detect(pt, ctx):
    ifov = ctx["pp"] / (pt["focal_mm"] / 1000.0)
    return ctx["target"] / (N_DET * ifov) >= ctx["R"]


def _seeker_coverage(pt, ctx):
    ifov = ctx["pp"] / (pt["focal_mm"] / 1000.0)
    return (pt["n_pixels"] * ifov) ** 2 >= ctx["omega_req"]


# ---- electrochemistry: specific energy vs specific power on a single chemistry (Ragone) ----
def _bat_engaged(cfg, m):
    return m.get("a_req", 0) >= 4.0 and m.get("endur_req", 0) >= 20.0


def _bat_ctx(cfg, m, best):
    op = operating_point(best)
    pm = op["pack_mass"] or 1e9
    return {"e_need": op["P_hover"] * (m["endur_req"] * 60.0) / 3600.0 / pm,
            "p_need": (op["n"] * op["V"] * op["I_max"]) / pm}


def _bat_grid(ctx):                                      # the chemistry choice = a point on the frontier
    return [{"p": p, "e": e} for (p, e) in _RAGONE]


def _bat_energy(pt, ctx):
    return pt["e"] >= ctx["e_need"]


def _bat_power(pt, ctx):
    return pt["p"] >= ctx["p_need"]


# ---- aerodynamics: efficient hover vs efficient dash on a single fixed pitch (advance ratio) ----
def _pitch_engaged(cfg, m):
    return m.get("v_req", 0) >= 30.0 and m.get("endur_req", 0) >= 8.0


def _pitch_ctx(cfg, m, best):
    return {"best": best, "v_req": m["v_req"]}


def _pitch_grid(ctx):                                    # the single fixed-pitch value lever
    return [{"pitch_in": p} for p in (5, 7, 9, 11, 13)]


def _pitch_dash(pt, ctx):                                # priceable: v_max is a real solve output
    return diagnose.caps_of(dict(ctx["best"], pitch_in=pt["pitch_in"]))["v_max"] >= ctx["v_req"]


def _pitch_hover_eff(pt, ctx):                           # UNPRICEABLE: momentum-theory hover power is
    return None                                          # pitch-independent, so the solve cannot score it


REGISTRY = [
    TradeInvariant(
        key="seeker", name="seeker space-bandwidth (etendue)", subsystem="seeker",
        node="optics.space_bandwidth_product", engaged=_seeker_engaged, context=_seeker_ctx,
        grid=_seeker_grid,
        constraints=[("detect", _seeker_detect, "detect the target at the required range (needs fine IFOV)"),
                     ("coverage", _seeker_coverage, "cover the search cone instantaneously (needs wide FOV)")],
        conflict_axis={frozenset(("detect", "coverage")):
                       "ADD A TEMPORAL / SCAN DEGREE OF FREEDOM (coverage accumulates over time)"}),
    TradeInvariant(
        key="battery", name="battery Ragone (energy vs power)", subsystem="energy",
        node="electrochemistry_batteries.ragone_tradeoff", engaged=_bat_engaged, context=_bat_ctx,
        grid=_bat_grid,
        constraints=[("energy", _bat_energy, "store enough Wh/kg for the endurance"),
                     ("power", _bat_power, "deliver enough W/kg for the burst")],
        conflict_axis={frozenset(("energy", "power")):
                       "ADD A SECOND ENERGY DOMAIN (energy channel || power channel) decoupling energy from power"}),
    TradeInvariant(
        key="pitch", name="propeller advance-ratio efficiency", subsystem="propulsion",
        node="aerodynamics.propeller_advance_efficiency", engaged=_pitch_engaged, context=_pitch_ctx,
        grid=_pitch_grid,
        constraints=[("dash", _pitch_dash, "reach the dash speed (wants high pitch / high advance ratio)"),
                     ("hover_eff", _pitch_hover_eff, "stay hover-efficient (wants low pitch / low advance ratio)")],
        conflict_axis={frozenset(("dash", "hover_eff")):
                       "ADD A PITCH-ACTUATION DEGREE OF FREEDOM (pitch as a function of flight state)"}),
]


# ====================================================================== the escalation wrapper
def meta_requirements(cfg, mission):
    """Diagnosis only: run V1 (value) + V2 (structure) for the gate, then the uniform engine over REGISTRY."""
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
    diagnoses = [diagnose_invariant(inv, cfg, mission, best_design) for inv in REGISTRY]
    out["diagnoses"] = diagnoses
    out["confirmed"] = [d for d in diagnoses if d.get("status") == "CONFLICT"]
    out["model_gaps"] = [d for d in diagnoses if d.get("status") == "MODEL_GAP"]

    if out["confirmed"]:
        out["verdict"] = "MISSING DIMENSION (confirmed by the solve)"
    elif airframe and v1_met:
        out["verdict"] = "value sufficed (V1)"
    elif airframe and v2_feasible:
        out["verdict"] = "structure sufficed (V2)"
    elif airframe:
        out["verdict"] = "unresolved (no confirmed conflict; deeper escalation needed)"
    else:
        out["verdict"] = "no airframe mission posed"
    return out


if __name__ == "__main__":
    import v3c_demo
    v3c_demo.main()
