r"""(d) objective <-> physics: each requirement is a FUNCTIONAL over the field solution.

A functional names WHAT it measures, WHICH fields it reads, and HOW (the evaluator). Power/energy terms
are bond-graph balances (endurance = stored energy in the electrical C-element / power dissipated by the
flow R-element). This replaces the hand-listed objective strings with an explicit, inspectable map.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

from uav import G                       # noqa: E402

RHO, FM = 1.225, 0.70


def _hover_power(mass, n, R):
    A = n * math.pi * R * R
    return (mass * G) ** 1.5 / (FM * math.sqrt(2 * RHO * A)) if A > 0 else 1e9


# name -> (fields it reads, evaluator(system, bus, cap) -> value, unit)
def _thrust(sys, bus, cap):     return cap["thrust"]
def _a_max_g(sys, bus, cap):    return cap["a_max"] / G
def _v_max(sys, bus, cap):      return cap["v_max"]


def _endurance_min(sys, bus, cap):
    prop = sys.by_name()["propulsion"]
    n, R = prop.params["n_rotors"], prop.params["D_in"] * 0.0254 / 2
    P = _hover_power(cap["mass"], n, R)                 # flow R-element dissipation
    E = bus.get("usable_energy", 0.0)                   # electrical C-element storage
    return (E / P) / 60.0 if P > 0 else 0.0


REGISTRY = {
    "thrust":        {"fields": ["flow"],              "unit": "N",    "fn": _thrust},
    "a_max_g":       {"fields": ["flow", "rigid-body"], "unit": "g",    "fn": _a_max_g},
    "v_max":         {"fields": ["flow"],              "unit": "m/s",  "fn": _v_max},
    "endurance_min": {"fields": ["electrical", "flow"], "unit": "min",  "fn": _endurance_min},
}

MISSION_TERMS = {"a_req": "a_max_g", "v_req": "v_max", "endur_req": "endurance_min"}


def evaluate(system, bus, cap, mission):
    values = {name: spec["fn"](system, bus, cap) for name, spec in REGISTRY.items()}
    checks = []
    allmet = True
    for req_key, term in MISSION_TERMS.items():
        have, need = values[term], mission[req_key]
        ok = have >= need - 1e-6
        allmet &= ok
        checks.append((term, have, need, REGISTRY[term]["unit"], REGISTRY[term]["fields"], ok))
    return {"values": values, "checks": checks, "met": allmet}
