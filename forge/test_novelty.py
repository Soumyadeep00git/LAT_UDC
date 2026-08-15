"""THE NOVELTY TEST — will the physics produce a fixed wing from a quad, unprompted?

Not rigged: 'stay aloft' (weight_support) has TWO mechanisms, each with honest physics —
  rotor_lift : hold weight by rotor thrust. CAN hover. Sustain power = momentum-theory hover power (high).
  wing_lift  : hold weight by aerodynamic lift in forward flight. CANNOT hover. Sustain power = cruise
               drag power = W/(L/D)*v (low). Costs wing mass.
Both are in the library; the agent SELECTS by which meets the mission at least mass. To prove it isn't
biased to the wing, we run TWO missions:
  A) must HOVER, modest endurance   -> a wing physically cannot hover, so it must stay a quad
  B) long ENDURANCE, forward flight -> a quad physically cannot last that long, so it must cross to a wing

If the same code returns a quad for A and a fixed wing for B, the PLATFORM CLASS was chosen by physics,
not by me. Honest ceiling: the wing law is in the library — this is composition-level novelty (new to the
user), not invention of unencoded physics.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

import radicality
from system import Subsystem, System
from solve import solve

RHO, G, FM, ETA = 1.225, 9.80665, 0.70, 0.70


def energy_model(params, inp):
    return {"usable_energy": params["Wh"] * 3600 * 0.85, "mass": params["Wh"] / 200.0}   # 200 Wh/kg


def rotor_lift_model(params, inp):
    m = inp.get("total_mass") or 2.0
    W = m * G
    A = params["n_rotors"] * math.pi * params["rotor_R"] ** 2
    P_hover = W ** 1.5 / (FM * math.sqrt(2 * RHO * A))
    mass = 0.6 + 0.04 * (P_hover / 100.0)                    # rotors + motors sized to hover
    return {"sustain_power": P_hover, "hover_capable": 1.0, "mass": mass}


def wing_lift_model(params, inp):
    m = inp.get("total_mass") or 2.0
    W = m * G
    v, LD = params["cruise_v"], params["LD"]
    A_w = 2 * W / (RHO * v * v * params["CL"])               # wing area for L = W at cruise
    drag = W / LD + 0.5 * RHO * v * v * params["Cd0"] * A_w
    P_cruise = drag * v / ETA
    mass = params["wing_kg_per_m2"] * A_w + 0.15             # wing + small pusher
    return {"sustain_power": P_cruise, "hover_capable": 0.0, "mass": mass}


WEIGHT_PARAMS = dict(n_rotors=4, rotor_R=0.14, cruise_v=20.0, LD=13.0, CL=0.9, Cd0=0.025, wing_kg_per_m2=1.8)
ROTOR_NODE, WING_NODE = "rotorcraft_bemt.rotor_thrust", "aerodynamics.lifting_line_theory"


def build(Wh, payload, mech):
    energy = Subsystem("energy", "stored_energy", provides=["usable_energy"], params={"Wh": Wh},
                       mechanisms={"battery": (energy_model, "electrochemistry_batteries.pack_energy")}, mechanism="battery")
    weight = Subsystem("weight_support", "lift", provides=["sustain_power", "hover_capable"],
                       params=WEIGHT_PARAMS,
                       mechanisms={"rotor_lift": (rotor_lift_model, ROTOR_NODE),
                                   "wing_lift": (wing_lift_model, WING_NODE)},
                       mechanism=mech, radicality_budget=9, owns=["endurance"])
    payload_s = Subsystem("payload", "mass", params={"mass": payload},
                          mechanisms={"fixed": (lambda p, i: {"mass": p["mass"]}, None)}, mechanism="fixed")
    return System("LoiterPlatform", [energy, weight, payload_s])


def evaluate(Wh, payload, mech):
    s = build(Wh, payload, mech)
    bus = solve(s, seed={"total_mass": 2.0})
    P = s.by_name()["weight_support"].state["sustain_power"]
    endurance = (bus.get("usable_energy", 0.0) / P / 60.0) if P > 0 else 0.0
    hover = s.by_name()["weight_support"].state["hover_capable"] > 0.5
    return {"endurance_min": endurance, "mass": bus["total_mass"], "hover": hover}


def choose(Wh, payload, mission):
    """Select the weight-support mechanism: must satisfy hover (if required) + endurance + mass; min mass wins."""
    out = {}
    for mech in ("rotor_lift", "wing_lift"):
        r = evaluate(Wh, payload, mech)
        ok = (r["endurance_min"] >= mission["endur_req"] and r["mass"] <= mission["mass_cap"]
              and (r["hover"] or not mission["hover_required"]))
        out[mech] = {**r, "meets": ok}
    feasible = [m for m in out if out[m]["meets"]]
    winner = min(feasible, key=lambda m: out[m]["mass"]) if feasible else None
    return winner, out


def run(name, Wh, payload, mission):
    winner, out = choose(Wh, payload, mission)
    print(f"\n### {name}")
    print(f"    mission: endurance >= {mission['endur_req']} min, "
          f"{'HOVER required' if mission['hover_required'] else 'forward flight OK'}, mass <= {mission['mass_cap']} kg")
    for mech, r in out.items():
        print(f"    {mech:11s}: endurance {r['endurance_min']:5.0f} min | mass {r['mass']:.2f} kg | "
              f"hover {'yes' if r['hover'] else 'no ':3s} | {'MEETS' if r['meets'] else 'fails'}")
    if winner == "wing_lift":
        d = radicality.distance(ROTOR_NODE, WING_NODE)
        print(f"    -> PRODUCED A FIXED WING (crossed rotor->wing, radicality {d}) — the quad could not meet this; physics chose the wing.")
    elif winner == "rotor_lift":
        print(f"    -> stayed a QUAD (rotor) — the wing was disallowed/worse here.")
    else:
        print(f"    -> no platform meets the mission.")
    return winner


if __name__ == "__main__":
    print("NOVELTY TEST — same code, same library, two missions. Does physics pick the platform?")
    Wh, payload = 120.0, 0.8
    a = run("Mission A — loiter in place (must hover), 15 min", Wh, payload,
            {"endur_req": 15, "hover_required": True, "mass_cap": 3.0})
    b = run("Mission B — endurance patrol (forward flight OK), 60 min", Wh, payload,
            {"endur_req": 60, "hover_required": False, "mass_cap": 3.0})
    print("\n" + "=" * 78)
    verdict = (a == "rotor_lift" and b == "wing_lift")
    print("VERDICT:", "PASS — quad for A, fixed wing for B: the platform class was chosen by physics."
          if verdict else "did not split as expected — inspect the numbers.")
