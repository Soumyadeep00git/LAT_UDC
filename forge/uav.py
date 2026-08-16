r"""The UAV expressed as an explicit SYSTEM graph — the first instance of the spine.

Subsystems and their couplings (the edges are the physics):

    energy --bus_voltage, i_burst--> propulsion --thrust--> structure
      ^-----------current-----------/           \--(mass feeds total_mass -> TWR, a_max, v_max)

Each subsystem's model wraps the already-validated physics modules (battery, motor, BEMT prop table,
structure). Nothing new is derived; the point is that the COUPLINGS are now edges on the bus, not
hardcoded calls. If the coupled solve reproduces platform_solve's numbers, the foundation is real.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "physics"))

from battery import Battery
from motor import Motor, solve as motor_solve
import aero
import structure
from platform_solve import PropTable, MOTOR_R_COEF, MOTOR_I0, MOTOR_KG_PER_A, G, IN2M
from system import Subsystem, System

RHO_AIR = 1.225
FM_HOVER = 0.70
_TABLE_CACHE = {}           # (D,pitch,blades,Kv,S) -> PropTable, reused across re-solves


# ----------------------------------------------------------------- subsystem models
def energy_model(params, inp):
    b = Battery(params["S"], params["cap_mAh"], params["C_rate"],
                wh_per_kg=params.get("wh_per_kg", 400.0))     # specific_energy = a material design DOF
    current = inp.get("current") or 0.0
    return {"bus_voltage": b.v_bus(current), "usable_energy": b.usable_J,
            "i_burst_per_rotor": b.I_burst / params["n_rotors"], "mass": b.mass}


def propulsion_model(params, inp):
    n = params["n_rotors"]
    V = inp.get("bus_voltage") or 3.7 * params["S"]
    i_cap = inp.get("i_burst_per_rotor") or params["I_max"]
    motor = Motor(Kv=params["Kv"], Rm=MOTOR_R_COEF / params["I_max"], I0=MOTOR_I0,
                  I_max=min(params["I_max"], i_cap))
    key = (round(params["D_in"], 2), round(params["pitch_in"], 2), params.get("n_blades", 2),
           round(params["Kv"]), round(params["S"]))
    table = _TABLE_CACHE.get(key)                            # global cache: reuse across re-solves
    if table is None:
        table = PropTable(params["D_in"], params["pitch_in"], params.get("n_blades", 2),
                          rpm_max=params["Kv"] * 3.7 * params["S"] * 1.05)
        _TABLE_CACHE[key] = table
    op = motor_solve(V, motor, lambda rpm: table.torque(rpm, 0.0), 1.0)
    T_rotor = table.thrust(op.rpm, 0.0)
    m_each = MOTOR_KG_PER_A * params["I_max"] + 0.0008 * params["D_in"] ** 2
    return {"thrust": n * T_rotor, "current": n * op.current, "mass": n * m_each,
            "_table": table, "_motor": motor, "_V": V, "_rpm": op.rpm}   # underscored -> stashed, not on the bus


DUCT_GAIN = 1.26            # a shroud recovers slipstream -> ~26% more static thrust for the same power
DUCT_MASS_FACTOR = 1.35     # ...but the duct adds mass


def ducted_fan_model(params, inp):
    """A ducted fan is the rotor's actuator disk with a shroud boundary condition: more static thrust,
    more mass. An ALTERNATIVE MECHANISM for the propulsion subsystem (d=1 from the rotor in the graph)."""
    st = dict(propulsion_model(params, inp))
    st["thrust"] *= DUCT_GAIN
    st["mass"] *= DUCT_MASS_FACTOR
    return st


def arm_model(params, inp):
    """A structure CHILD: the carbon arms, sized for the maneuver bending load. Grounds to beam bending."""
    n = params["n_rotors"]
    thrust = inp.get("thrust") or 0.0
    mass = inp.get("total_mass") or 4.0
    T_rotor = thrust / n if n else 0.0
    n_g = max(thrust / (mass * G), 1.0) if mass else 1.0
    return {"mass": n * structure.arm_mass(T_rotor, L=params["L_arm"], n_g=n_g)}


def frame_model(params, inp):
    """A structure CHILD: the central frame, sized with total thrust. Grounds to axial stress."""
    n = params["n_rotors"]
    thrust = inp.get("thrust") or 0.0
    T_rotor = thrust / n if n else 0.0
    return {"mass": structure.FRAME0 + structure.K_FRAME * n * T_rotor}


def payload_model(params, inp):
    return {"mass": params.get("mass", 0.6)}


# ----------------------------------------------------------------- build the system graph
def build_uav(cfg, propulsion_mechanism="rotor"):
    n = cfg.get("n_rotors", 4)
    energy = Subsystem("energy", "stored_energy", requires=["current"],
                       provides=["bus_voltage", "usable_energy", "i_burst_per_rotor"],
                       params={"S": cfg["S"], "cap_mAh": cfg["cap_mAh"], "C_rate": cfg["C_rate"], "n_rotors": n,
                               "wh_per_kg": cfg.get("wh_per_kg", 400.0)},
                       mechanisms={"battery": (energy_model, "electrochemistry_batteries.pack_energy")},
                       mechanism="battery", radicality_budget=0, owns=["endurance"],
                       physics_vars=["specific_energy", "pack_mass", "usable_capacity_fraction"])
    propulsion = Subsystem("propulsion", "thrust", requires=["bus_voltage", "i_burst_per_rotor"],
                           provides=["thrust", "current"],
                           params={"D_in": cfg["D_in"], "pitch_in": cfg["pitch_in"], "Kv": cfg["Kv"],
                                   "I_max": cfg["I_max"], "S": cfg["S"], "n_rotors": n},
                           mechanisms={"rotor": (propulsion_model, "rotorcraft_bemt.rotor_thrust"),
                                       "ducted_fan": (ducted_fan_model, "rotorcraft_bemt.actuator_disk_momentum")},
                           mechanism=propulsion_mechanism, radicality_budget=2, owns=["a_max", "v_max"],
                           physics_vars=["air_density", "disk_area", "induced_velocity", "climb_velocity"])
    # structure DECOMPOSES into sub-subsystems (recursion "down the line"): arm + frame, each grounded
    arm = Subsystem("arm", "bending_stress", requires=["thrust"],
                    params={"L_arm": cfg["L_arm"], "n_rotors": n},
                    mechanisms={"carbon_beam": (arm_model, "solid_mechanics.beam_bending_stress")},
                    mechanism="carbon_beam", radicality_budget=0, owns=["struct_mass"],
                    physics_vars=["bending_moment", "section_modulus"])
    frame = Subsystem("frame", "stress", requires=["thrust"], params={"n_rotors": n},
                      mechanisms={"plate": (frame_model, "solid_mechanics.stress")},
                      mechanism="plate", physics_vars=["axial_load", "cross_section_area"])
    struct = Subsystem("structure", "stress", requires=["thrust"], children=[arm, frame])
    payload = Subsystem("payload", "mass", params={"mass": cfg.get("payload", 0.6)},
                        mechanisms={"fixed": (payload_model, None)}, mechanism="fixed")
    return System("UAV", [energy, propulsion, struct, payload])


# ----------------------------------------------------------------- system-level capability envelope
def capabilities(system, bus):
    mass = bus["total_mass"]
    thrust = bus.get("thrust", 0.0)
    twr = thrust / (mass * G)
    a_max = G * math.sqrt(max(twr * twr - 1.0, 0.0))
    # v_max: re-solve the propulsion powertrain at forward speed vs drag, using the stashed table/motor
    prop = system.by_name()["propulsion"]
    table, motor, V = prop.state["_table"], prop.state["_motor"], prop.state["_V"]
    n = prop.params["n_rotors"]
    L = next((lf.params["L_arm"] for s in system.subsystems for lf in s.leaves()
              if "L_arm" in lf.params), 0.3)
    W = mass * G
    def excess(vair):
        op = motor_solve(V, motor, lambda rpm: table.torque(rpm, vair), 1.0)
        Ttot = n * table.thrust(op.rpm, vair)
        F_fwd = math.sqrt(max(Ttot * Ttot - W * W, 0.0))
        return F_fwd - aero.drag(vair, n, L, prop.params["D_in"])
    if excess(1.0) <= 0:
        v_max = 0.0
    else:
        lo, hi = 1.0, 5.0
        while hi < 120 and excess(hi) > 0:
            hi *= 1.5
        for _ in range(22):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if excess(mid) > 0 else (lo, mid)
        v_max = 0.5 * (lo + hi)
    # endurance: usable battery energy / momentum-theory hover power
    A_total = n * math.pi * (prop.params["D_in"] * IN2M / 2.0) ** 2
    P_hover = (mass * G) ** 1.5 / (FM_HOVER * math.sqrt(2 * RHO_AIR * A_total)) if A_total > 0 else 1e9
    endurance = bus.get("usable_energy", 0.0) / P_hover if P_hover > 0 else 0.0
    struct_mass = system.by_name()["structure"].state.get("mass", 0.0)
    return {"mass": mass, "TWR": twr, "a_max": a_max, "v_max": v_max, "thrust": thrust,
            "endurance": endurance, "struct_mass": struct_mass}
