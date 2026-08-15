"""4a — question the equation itself.

Every law in the library is a SPECIAL CASE under assumptions: Bernoulli assumes incompressible + inviscid;
beam bending assumes small deflection + linear-elastic; momentum theory assumes low tip Mach + uniform
inflow. Today the agent checks "does the model obey the law." This module adds the deeper question:
"is this law even VALID in the current regime — and if not, may I MOVE UP to the more general law?"

Each law carries a LawCard: its assumptions, each with a checkable VALIDITY predicate on the operating
regime, a rough ERROR if pushed past it, and the more-general law you reach by RELAXING it. Moving up the
special-case ladder is radicality on a second axis: radicality = how many assumptions you relax to get
there. Deterministic, zero-LLM — the question comes from a fixed template.

This is a prototype over a handful of laws; annotating the whole library is the scale-up (as with the
library itself). The MECHANISM is the point.
"""
from __future__ import annotations

import math
import operator
import re
from dataclasses import dataclass
from typing import Callable


@dataclass
class Assumption:
    name: str
    holds: Callable            # regime dict -> bool
    error: Callable            # regime dict -> relative error if the assumption is pushed
    relax_to: str              # the more-general law reached by relaxing this assumption
    why: str


@dataclass
class LawCard:
    node: str
    law: str
    assumptions: list


# ---- compile agent-emitted structured specs into checkable predicates (deterministic, sandboxed) ----
_OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}

def _mk_holds(var, valid_when):
    m = re.match(r"\s*(<=|>=|<|>)\s*([-\d.eE+]+)", valid_when or "")
    if not m:
        return lambda r: None
    fn, num = _OPS[m.group(1)], float(m.group(2))
    def holds(r):
        if var not in r:
            return None                                   # can't check -> don't raise a false question
        try:
            return fn(float(r[var]), num)
        except (TypeError, ValueError):
            return None
    return holds

def _mk_error(var, expr):
    def err(r):
        try:
            env = {"__builtins__": {}}
            local = {var: float(r.get(var, 0.0)), "sqrt": math.sqrt, "abs": abs,
                     "log": math.log, "exp": math.exp, "pi": math.pi}
            return abs(float(eval(expr, env, local)))     # expr is a numeric formula in the regime var
        except Exception:
            return 0.1
    return err

def _load_generated():
    try:
        from assumption_cards import CARDS as GEN
    except ImportError:
        return {}
    out = {}
    for nid, c in GEN.items():
        asms = [Assumption(a["name"], _mk_holds(a["regime_variable"], a["valid_when"]),
                           _mk_error(a["regime_variable"], a["error_when_violated"]),
                           a["generalizes_to"], a["why"]) for a in c["assumptions"]]
        out[nid] = LawCard(nid, c["law"], asms)
    return out


HAND_CARDS = {
    "rotorcraft_bemt.actuator_disk_momentum": LawCard(
        "rotorcraft_bemt.actuator_disk_momentum", "T = 2 rho A v_i^2  (actuator-disk momentum theory)",
        [Assumption("incompressible", lambda r: r.get("tip_mach", 0) < 0.30,
                    lambda r: 0.6 * r.get("tip_mach", 0) ** 2, "compressible_actuator_disk",
                    "blade-tip Mach must stay low or density changes across the disk"),
         Assumption("no_tip_loss", lambda r: r.get("blade_aspect", 10) > 6.0,
                    lambda r: 0.08, "prandtl_tip_loss_model", "finite blades leak flow at the tip"),
         Assumption("quasi_steady", lambda r: r.get("reduced_freq", 0) < 0.05,
                    lambda r: 0.1, "unsteady_bemt", "fast pitch/flap makes inflow unsteady")]),
    "fluid_dynamics.bernoulli": LawCard(
        "fluid_dynamics.bernoulli", "p + 1/2 rho v^2 = const  (Bernoulli)",
        [Assumption("incompressible", lambda r: r.get("mach", 0) < 0.30,
                    lambda r: 0.5 * r.get("mach", 0) ** 2, "compressible_flow_energy_eqn",
                    "density constant only at low Mach"),
         Assumption("inviscid", lambda r: r.get("reynolds", 1e6) > 1e4,
                    lambda r: 3.0 / max(r.get("reynolds", 1e6) ** 0.5, 1), "navier_stokes",
                    "viscosity matters at low Reynolds")]),
    "solid_mechanics.beam_bending_stress": LawCard(
        "solid_mechanics.beam_bending_stress", "sigma = M c / I  (Euler-Bernoulli beam)",
        [Assumption("small_deflection", lambda r: r.get("deflection_ratio", 0) < 0.10,
                    lambda r: r.get("deflection_ratio", 0), "large_deflection_beam",
                    "geometry changes once the beam bends far"),
         Assumption("linear_elastic", lambda r: r.get("stress_ratio", 0) < 1.0,
                    lambda r: max(0.0, r.get("stress_ratio", 0) - 1.0), "elastoplastic_beam",
                    "past yield the material is nonlinear")]),
    "thermodynamics.ideal_gas_law": LawCard(
        "thermodynamics.ideal_gas_law", "pV = n R T  (ideal gas)",
        [Assumption("dilute", lambda r: r.get("reduced_pressure", 0) < 0.5,
                    lambda r: 0.3 * r.get("reduced_pressure", 0), "van_der_waals",
                    "molecular volume & attraction matter when dense")]),
}

# the full annotation set: agent-generated cards, with validated hand cards taking precedence on overlap
CARDS = {**_load_generated(), **HAND_CARDS}


def question_law(node, regime):
    """Return the assumptions VIOLATED by this regime, each with the generalization to move up to."""
    card = CARDS.get(node)
    if not card:
        return None, []
    violated = []
    for a in card.assumptions:
        if not a.holds(regime):
            violated.append({"assumption": a.name, "error": a.error(regime),
                             "move_up_to": a.relax_to, "radicality": 1, "why": a.why})
    return card, violated


def phrase(card, v):
    return (f"Q  '{card.node.split('.')[-1]}' is {card.law}, which ASSUMES {v['assumption']} "
            f"({v['why']}). In this regime that assumption is VIOLATED (~{v['error']*100:.0f}% error). "
            f"May I move up to [{v['move_up_to']}] — relaxing {v['assumption']}, radicality {v['radicality']}?")


if __name__ == "__main__":
    print("QUESTION THE EQUATION — does each law hold in its regime?\n")
    scenarios = [
        ("fast rotor (tip Mach 0.55)", "rotorcraft_bemt.actuator_disk_momentum",
         {"tip_mach": 0.55, "blade_aspect": 8, "reduced_freq": 0.02}),
        ("heavily loaded thin arm", "solid_mechanics.beam_bending_stress",
         {"deflection_ratio": 0.15, "stress_ratio": 0.7}),
        ("low-speed wing section", "fluid_dynamics.bernoulli",
         {"mach": 0.12, "reynolds": 4e5}),
        ("sea-level air (nominal)", "thermodynamics.ideal_gas_law",
         {"reduced_pressure": 0.03}),
    ]
    for name, node, regime in scenarios:
        card, viol = question_law(node, regime)
        print(f"[{name}]  regime {regime}")
        if not viol:
            print("   all assumptions hold — the law is valid here; use as-is.\n")
            continue
        for v in viol:
            print("   " + phrase(card, v))
        print()
