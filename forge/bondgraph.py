r"""(b) hardware -> system, and (c) system -> physics fields.

(b) infer_system: cluster PARTS by role into SUBSYSTEMS, count rotor-group members to get n_rotors, attach
    each subsystem's model+library-node by role, and WIRE couplings by matching port quantities across the
    parts (a producer 'out' quantity becomes `provides`; a consumer 'in' becomes `requires`). The
    energy->propulsion->structure topology is DISCOVERED from the ports, not written down. The result is a
    standard forge System, so solve.py + capabilities() run on it unchanged.

(c) to_fields: walk the inferred subsystems and assign each its DOMAIN field (electrical/flow/stress) over
    its placed region, with boundary conditions taken from the inferred bonds. Reduced values come from the
    solved state; a field flips to an external CFD/FEM backend when it leaves the reduced model's validity.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

from uav import (energy_model, propulsion_model, arm_model, frame_model, payload_model,          # noqa: E402
                 seeker_model, SEEKER_DEFAULTS, IN2M)
from system import Subsystem, System                                                            # noqa: E402

# role -> how that role realises as a subsystem (which model, which library law, which domain)
ROLE = {
    "source":    dict(sub="energy",     func="stored_energy", model=energy_model,
                      node="electrochemistry_batteries.pack_energy", domain="electrical", owns=["endurance"]),
    "propulsor": dict(sub="propulsion", func="thrust",        model=propulsion_model,
                      node="rotorcraft_bemt.rotor_thrust",           domain="flow",       owns=["a_max", "v_max"]),
    "arm":       dict(sub="arm",        func="bending_stress", model=arm_model,
                      node="solid_mechanics.beam_bending_stress",    domain="stress",     parent="structure"),
    "frame":     dict(sub="frame",      func="stress",         model=frame_model,
                      node="solid_mechanics.stress",                 domain="stress",     parent="structure"),
    "payload":   dict(sub="payload",    func="mass",           model=payload_model,
                      node=None,                                     domain="mass"),
    "avionics":  dict(sub="payload",    func="mass",           model=payload_model,
                      node=None,                                     domain="mass"),
    "sensor":    dict(sub="seeker",     func="detection_range", model=seeker_model,
                      node="electro_optics.detection_range",         domain="electro-optical", owns=["detection"]),
    "environment": None,   # a sink (the air), not a subsystem
}

DOMAIN_OF_Q = {"bus_voltage": "electrical", "i_burst_per_rotor": "electrical", "current": "electrical",
               "usable_energy": "electrical", "thrust": "mechanical"}


def infer_system(parts, cfg):
    """Cluster parts -> subsystems, wire by port matching. Returns (System, meta)."""
    # 1) cluster parts by their role's target subsystem
    clusters = {}
    for p in parts:
        spec = ROLE.get(p.role)
        if spec is None:
            continue
        clusters.setdefault(spec["sub"], []).append(p)
    n_rotors = sum(1 for p in parts if p.role == "propulsor")

    # 2) aggregate ports per subsystem (union of member quantities by direction)
    agg = {sub: {"out": set(), "in": set()} for sub in clusters}
    for sub, members in clusters.items():
        for p in members:
            for pt in p.ports:
                if pt.domain in ("electrical", "mechanical"):
                    agg[sub][pt.direction].update(pt.quantities)

    # 3) wire: producer of q -> provides; consumers of q -> requires
    producer = {}
    for sub, io in agg.items():
        for q in io["out"]:
            producer[q] = sub
    provides = {sub: sorted(io["out"]) for sub, io in agg.items()}
    requires = {sub: sorted(io["in"]) for sub, io in agg.items()}
    bonds = []
    for sub, io in agg.items():
        for q in io["in"]:
            if q in producer and producer[q] != sub:
                bonds.append((producer[q], sub, DOMAIN_OF_Q.get(q, "?"), q))

    # 4) params per subsystem (from cfg + inferred counts)
    P = {
        "energy":     {"S": cfg["S"], "cap_mAh": cfg["cap_mAh"], "C_rate": cfg["C_rate"], "n_rotors": n_rotors,
                       "wh_per_kg": cfg.get("wh_per_kg", 400.0)},
        "propulsion": {"D_in": cfg["D_in"], "pitch_in": cfg["pitch_in"], "Kv": cfg["Kv"],
                       "I_max": cfg["I_max"], "S": cfg["S"], "n_rotors": n_rotors},
        "arm":        {"L_arm": cfg["L_arm"], "n_rotors": n_rotors},
        "frame":      {"n_rotors": n_rotors},
        "payload":    {"mass": cfg.get("payload", 0.6)},
        "seeker":     {k: cfg.get(k, v) for k, v in SEEKER_DEFAULTS.items()},
    }

    def mk(sub):
        spec = next(v for v in ROLE.values() if v and v["sub"] == sub)
        return Subsystem(sub, spec["func"], requires=requires.get(sub, []), provides=provides.get(sub, []),
                         params=P[sub], mechanisms={sub: (spec["model"], spec["node"])}, mechanism=sub,
                         owns=spec.get("owns", []))

    # 5) assemble; structure is the parent of arm+frame (recursion)
    energy = mk("energy")
    propulsion = mk("propulsion")
    arm = mk("arm")
    frame = mk("frame")
    structure = Subsystem("structure", "stress", requires=["thrust"], children=[arm, frame])
    payload = mk("payload")
    seeker = mk("seeker")
    system = System("UAV", [energy, propulsion, structure, payload, seeker])

    meta = {"n_rotors": n_rotors, "bonds": bonds,
            "roles": {s.name: dict(role_for(s.name), domain=domain_for(s.name)) for s in
                      [energy, propulsion, arm, frame, payload, seeker]},
            "parts": parts, "cfg": cfg}
    return system, meta


def role_for(sub):
    for r, v in ROLE.items():
        if v and v["sub"] == sub:
            return {"role": r}
    return {"role": "?"}


def domain_for(sub):
    for v in ROLE.values():
        if v and v["sub"] == sub:
            return v["domain"]
    return "?"


# ---------------------------------------------------------------- (c) system -> physics fields
def to_fields(system, bus, cap, meta):
    cfg = meta["cfg"]
    prop = system.by_name()["propulsion"]
    n = prop.params["n_rotors"]
    R = prop.params["D_in"] * IN2M / 2
    rpm = prop.state.get("_rpm", 0.0)
    tip_mach = (rpm * 2 * math.pi / 60.0) * R / 343.0 if rpm else 0.0
    A = n * math.pi * R * R
    dl = cap["thrust"] / A if A > 0 else 0.0
    T_rotor = cap["thrust"] / n if n else 0.0
    flow_bad = ([f"tip Mach {tip_mach:.2f}>0.70"] if tip_mach > 0.70 else []) + \
               ([f"disk loading {dl:.0f}>250"] if dl > 250 else [])
    fields = [
        {"field": "flow", "from": "propulsion", "node": prop.node,
         "region": f"{n} rotor disks R={R:.3f} m + body",
         "bcs": ["mech->flow: prop thrust (blade BC)", "flow->stress: aero load"],
         "reduced": {"thrust_N": round(cap["thrust"], 2), "disk_loading": round(dl, 1),
                     "tip_mach": round(tip_mach, 3)},
         "drives": ["a_max", "v_max", "endurance(power)"],
         "backend": "external CFD" if flow_bad else "reduced"},
        {"field": "electrical", "from": "energy", "node": system.by_name()["energy"].node,
         "region": f"{cfg['S']}S {cfg['cap_mAh']} mAh pack + harness",
         "bcs": ["E->mech: winding current -> motor torque"],
         "reduced": {"bus_voltage_V": round(bus.get("bus_voltage", 0.0), 2),
                     "usable_Wh": round(bus.get("usable_energy", 0.0) / 3600.0, 1)},
         "drives": ["endurance(energy)"], "backend": "reduced"},
        {"field": "stress", "from": "structure", "node": "solid_mechanics.beam_bending_stress",
         "region": f"{n} arms L={cfg['L_arm']:.2f} m + frame",
         "bcs": ["flow->stress: rotor thrust as tip load", "gravity: total_mass"],
         "reduced": {"tip_load_N": round(T_rotor, 2), "struct_mass_kg": round(cap["struct_mass"], 3)},
         "drives": ["mass", "structural margin"], "backend": "reduced"},
    ]
    return fields


def describe_bonds(meta):
    return [f"{a} --{q} [{d}]--> {b}" for (a, b, d, q) in meta["bonds"]]
