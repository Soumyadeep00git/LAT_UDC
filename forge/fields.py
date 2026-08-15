r"""Layer III as a FIELD schema — the device as coupled fields in space, solver-agnostic.

The vision shift, made into data: a subsystem is not 'a wire' or 'an arm', it is a FIELD occupying a
REGION with BOUNDARY CONDITIONS, coupled to its neighbours only at shared boundaries:

        flow field  (air around props + body)
          stress field  (arms / frame load path)
            E / B field  (battery, windings, motor gap)

Each FieldRegion is backend-agnostic. Two backends implement the same contract:
  - REDUCED   : the fast validated analytic model (BEMT / beam theory / circuit) — runs now.
  - EXTERNAL  : export a solver-agnostic CASE for an external CFD/FEM pipeline. Until a real solver is
                attached it returns status='not attached' and the case — it NEVER fabricates a field.

The validity envelope picks the backend: inside validity -> reduced is trustworthy; outside (tip Mach,
disk loading, ...) -> the field should go to the external solver. Scope stays MULTIROTOR UAV.
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass, field as dc_field

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

from uav import build_uav, capabilities, G, IN2M      # noqa: E402
from solve import solve                                # noqa: E402

ENV = {"tip_mach": 0.70, "disk_loading": 250.0}


@dataclass
class FieldRegion:
    name: str
    field_type: str                 # flow | stress | electric | magnetic | thermal
    region: dict                    # geometry of the space the field occupies
    material: str
    bcs: list                       # boundary conditions (strings: where + what)
    couplings: list                 # coupling BCs to other fields (the physics edges)
    physics_node: str               # grounding in the library
    reduced: dict                   # values from the validated reduced model (the real engine)
    validity: list                  # assumption violations (empty = reduced is trustworthy)
    objective_terms: list           # which objective functionals this field drives

    def backend(self):
        return "external (CFD/FEM — reduced model out of validity)" if self.validity else "reduced"

    def external_case(self):
        """A solver-agnostic case an external pipeline consumes. Geometry + BCs + operating point only —
        no results. This is the L3->external contract."""
        return {"field": self.field_type, "solver_class": _SOLVER_CLASS[self.field_type],
                "region": self.region, "material": self.material,
                "boundary_conditions": self.bcs, "couplings": self.couplings,
                "operating_point": self.reduced.get("op", {}),
                "requested_outputs": self.reduced.get("wants", [])}


_SOLVER_CLASS = {"flow": "CFD (RANS / actuator-line)", "stress": "FEM (linear/nonlinear elasticity)",
                 "electric": "circuit / electroquasistatic", "magnetic": "magnetostatic (FEA)",
                 "thermal": "conjugate heat transfer"}


class ExternalBackend:
    """Plug a real solver by passing runner(case)->results. Absent one, it stays honest."""
    def __init__(self, runner=None):
        self.runner = runner

    def solve(self, region: FieldRegion):
        case = region.external_case()
        if self.runner is None:
            return {"status": "external solver not attached", "case": case}
        return {"status": "solved", "results": self.runner(case)}


# ------------------------------------------------------------------ decompose L1/L2 -> L3 fields
def decompose(cfg, mechanism="rotor"):
    """Run the real engine once, then express the device as coupled FieldRegions with their reduced
    values and validity. Returns (regions, caps)."""
    sysm = build_uav(cfg, propulsion_mechanism=mechanism)
    bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    cap = capabilities(sysm, bus)
    prop = sysm.by_name()["propulsion"]
    n = prop.params["n_rotors"]
    R = prop.params["D_in"] * IN2M / 2
    rpm = prop.state.get("_rpm", 0.0)
    tip_mach = (rpm * 2 * math.pi / 60.0) * R / 343.0 if rpm else 0.0
    A = n * math.pi * R * R
    dl = cap["thrust"] / A if A > 0 else 0.0
    T_rotor = cap["thrust"] / n if n else 0.0
    L = next((lf.params["L_arm"] for s in sysm.subsystems for lf in s.leaves() if "L_arm" in lf.params), 0.3)
    V = bus.get("bus_voltage", 0.0)
    I = bus.get("current", 0.0)

    flow_bad = ([f"tip Mach {tip_mach:.2f}>{ENV['tip_mach']}"] if tip_mach > ENV["tip_mach"] else []) \
        + ([f"disk loading {dl:.0f}>{ENV['disk_loading']} N/m2"] if dl > ENV["disk_loading"] else [])

    regions = [
        FieldRegion(
            name="flow", field_type="flow",
            region={"rotor_disks": n, "disk_radius_m": round(R, 4), "config": "X",
                    "body": "central frame + arms", "domain": "far-field cylinder ~10R"},
            material="air (rho=1.225)",
            bcs=["blade: no-slip rotating wall", "disk: RPM=%.0f" % rpm, "far-field: pressure outlet",
                 "inflow: v_climb / v_forward"],
            couplings=["mech->flow: prop thrust (blade pressure BC)", "flow->stress: aero load on structure"],
            physics_node="rotorcraft_bemt.rotor_thrust" if mechanism == "rotor" else "rotorcraft_bemt.actuator_disk_momentum",
            reduced={"thrust_N": round(cap["thrust"], 2), "thrust_per_rotor_N": round(T_rotor, 2),
                     "disk_loading_Nm2": round(dl, 1), "tip_mach": round(tip_mach, 3),
                     "hover_power_W": round((cap["mass"] * G) ** 1.5 / (0.70 * math.sqrt(2 * 1.225 * A)), 1) if A > 0 else 0,
                     "op": {"rpm": round(rpm, 1), "R_m": round(R, 4), "n_blades": 2,
                            "pitch_in": cfg["pitch_in"], "rho": 1.225},
                     "wants": ["thrust", "torque", "induced_velocity", "figure_of_merit"]},
            validity=flow_bad,
            objective_terms=["a_max (thrust)", "v_max (thrust vs drag)", "endurance (hover power)"]),
        FieldRegion(
            name="stress", field_type="stress",
            region={"members": ["4 arms L=%.2fm" % L, "central frame plates"], "section": "carbon tube/plate"},
            material="carbon-fibre composite",
            bcs=["arm root: fixed at frame", "arm tip: point load = thrust/rotor",
                 "frame: distributed motor reactions"],
            couplings=["flow->stress: rotor thrust as tip load", "gravity: total_mass"],
            physics_node="solid_mechanics.beam_bending_stress",
            reduced={"tip_load_N": round(T_rotor, 2), "arm_moment_Nm": round(T_rotor * L, 3),
                     "struct_mass_kg": round(cap["struct_mass"], 3),
                     "op": {"tip_load_N": round(T_rotor, 2), "L_m": round(L, 3)},
                     "wants": ["max_von_mises", "tip_deflection", "buckling_margin"]},
            validity=[],   # linear beam theory valid in this regime; detailed stress field -> FEM
            objective_terms=["mass", "structural margin"]),
        FieldRegion(
            name="electric", field_type="electric",
            region={"battery_cells_S": cfg["S"], "capacity_mAh": cfg["cap_mAh"], "windings": "motor phases"},
            material="Li-ion + copper",
            bcs=["pack terminal: V_bus under load", "load: burst current", "cell: internal resistance"],
            couplings=["E->mech: winding current -> motor torque"],
            physics_node="electrochemistry_batteries.pack_energy",
            reduced={"bus_voltage_V": round(V, 2), "current_A": round(I, 1),
                     "usable_energy_Wh": round(bus.get("usable_energy", 0.0) / 3600.0, 1),
                     "op": {"S": cfg["S"], "cap_mAh": cfg["cap_mAh"], "C_rate": cfg.get("C_rate", 60)},
                     "wants": ["voltage_sag", "pack_temperature", "usable_capacity"]},
            validity=[],
            objective_terms=["endurance (stored energy)"]),
        FieldRegion(
            name="magnetic", field_type="magnetic",
            region={"location": "motor air gap", "count": n},
            material="NdFeB magnets + steel stator",
            bcs=["stator: 3-phase current sheet", "gap: rotor angle", "back-iron: flux return"],
            couplings=["E->mag: phase currents", "mag->mech: air-gap torque (Maxwell stress)"],
            physics_node="rotorcraft_bemt.rotor_thrust",
            reduced={"Kv": cfg["Kv"], "I_max_A": cfg["I_max"],
                     "op": {"Kv": cfg["Kv"], "I_max": cfg["I_max"]},
                     "wants": ["airgap_torque", "iron_loss", "demag_margin"]},
            validity=[],
            objective_terms=["a_max (torque->thrust)"]),
    ]
    return regions, cap


# ------------------------------------------------------------------ demo
if __name__ == "__main__":
    cfg = dict(D_in=13, pitch_in=6, Kv=300, I_max=45, S=6, cap_mAh=5000,
               C_rate=60, L_arm=0.30, payload=0.6, n_rotors=4)
    regions, cap = decompose(cfg)
    print("L3 FIELD DECOMPOSITION  (device = coupled fields in space)\n")
    for r in regions:
        print(f"  [{r.field_type:8s}] {r.name:8s}  node={r.physics_node}")
        print(f"       region : {r.region}")
        print(f"       BCs    : {r.bcs}")
        print(f"       couple : {r.couplings}")
        print(f"       reduced: {r.reduced}")
        print(f"       drives : {r.objective_terms}")
        print(f"       BACKEND: {r.backend()}")
        print()

    # show the external-solver contract for the flow field (what an external CFD would consume)
    flow = next(r for r in regions if r.field_type == "flow")
    ext = ExternalBackend(runner=None)          # no real CFD attached -> honest
    out = ext.solve(flow)
    print("EXTERNAL BACKEND (flow field), no solver attached:")
    print(f"  status: {out['status']}")
    path = os.path.join(HERE, "cfd_case_flow.json")
    with open(path, "w") as f:
        json.dump(out["case"], f, indent=2)
    print(f"  wrote solver-agnostic case -> {path}")
    print("  (attach a real CFD by ExternalBackend(runner=my_cfd), runner(case)->results)")
