"""Cross-domain smoke test — is the architecture domain-agnostic, and does the physics library ground
non-drone systems? Express an AUTOMOBILE and a DC-DC CONVERTER as System graphs, ground every subsystem
function against the library, and run the coupled solve. Every function that fails to ground is a library
gap to fill; every domain that solves proves the spine isn't drone-shaped.

Models are deliberately TOY — the test is architecture generality + library coverage, not fidelity.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

import library
from system import Subsystem, System
from solve import solve

RHO = 1.225


# ---------------------------------------------------------------- AUTOMOBILE (toy models)
def car_energy(params, inp):
    Wh = params["kWh"] * 1000.0
    return {"bus_voltage": params["V"], "usable_energy": Wh * 3600 * 0.9, "mass": Wh / 150.0}
def car_powertrain(params, inp):
    return {"drive_power": params["power_kW"] * 1000.0, "mass": params["power_kW"] * 0.5}
def car_chassis(params, inp):
    return {"mass": params["curb_mass"]}

def build_car(cfg):
    return System("Automobile", [
        Subsystem("energy", "stored_energy", provides=["bus_voltage", "usable_energy"],
                  params={"kWh": cfg["kWh"], "V": cfg["V"]},
                  mechanisms={"battery": (car_energy, "electrochemistry_batteries.pack_energy")}, mechanism="battery",
                  physics_vars=["specific_energy", "pack_mass"]),
        Subsystem("powertrain", "tractive_force", requires=["bus_voltage"], provides=["drive_power"],
                  params={"power_kW": cfg["power_kW"]},
                  mechanisms={"emotor": (car_powertrain, "electric_machines.electromagnetic_torque")}, mechanism="emotor",
                  physics_vars=["motor_torque", "wheel_radius"]),
        Subsystem("aero", "drag_force", params={}, mechanisms={"body": (lambda p, i: {"mass": 0.0}, "aerodynamics.drag_coefficient")},
                  mechanism="body", physics_vars=["air_density", "frontal_area", "speed"]),
        Subsystem("chassis", "stress", requires=["drive_power"], params={"curb_mass": cfg["curb_mass"]},
                  mechanisms={"frame": (car_chassis, "solid_mechanics.stress")}, mechanism="frame",
                  physics_vars=["axial_load"]),
    ])

def car_top_speed(system, bus):
    p = system.by_name()["powertrain"].state["drive_power"]
    cd_a = 0.30 * 2.2                                   # Cd * frontal area (m^2)
    return (2 * p / (RHO * cd_a)) ** (1 / 3.0)           # P = 1/2 rho Cd A v^3


# ---------------------------------------------------------------- DC-DC CONVERTER (toy models)
def build_converter(cfg):
    return System("DC-DC Converter", [
        Subsystem("switch", "switching_loss", provides=["heat"], params={"f_khz": cfg["f_khz"]},
                  mechanisms={"mosfet": (lambda p, i: {"heat": p["f_khz"] * 0.4, "mass": 0.02}, "power_electronics.switching_loss")},
                  mechanism="mosfet", physics_vars=["switching_frequency", "voltage", "current"]),
        Subsystem("inductor", "inductor_energy", provides=["ripple"], params={"uH": cfg["uH"]},
                  mechanisms={"coil": (lambda p, i: {"ripple": 1.0 / p["uH"], "mass": p["uH"] * 0.001}, "circuit_theory.inductor_stored_energy")},
                  mechanism="coil", physics_vars=["inductance", "current"]),
        Subsystem("capacitor", "capacitance", provides=["output_voltage"], params={"uF": cfg["uF"]},
                  mechanisms={"cap": (lambda p, i: {"output_voltage": 12.0, "mass": p["uF"] * 1e-4}, "circuit_theory.capacitance")},
                  mechanism="cap", physics_vars=["permittivity", "plate_area", "gap"]),
        Subsystem("thermal", "thermal_resistance", requires=["heat"], params={},
                  mechanisms={"heatsink": (lambda p, i: {"mass": (i.get("heat") or 0) * 0.01}, "heat_transfer.thermal_resistance")},
                  mechanism="heatsink", physics_vars=["conductivity", "area", "thickness"]),
    ])


def ground_report(system):
    print(f"\n=== {system.name} ===")
    grounded = 0
    for s in system.subsystems:
        nid = library.ground_quantity(s.function, s.physics_vars)
        if nid:
            grounded += 1
            desc = [d for d, _, _ in library.descent(nid)][:3]
            print(f"  [{s.name:11s}] '{s.function}' -> [{nid}]  ({' <- '.join(desc)})")
        else:
            print(f"  [{s.name:11s}] '{s.function}' -> BLIND (library gap)")
    return grounded, len(system.subsystems)


if __name__ == "__main__":
    import physics_archive as A
    print("CROSS-DOMAIN SMOKE TEST — architecture generality + library coverage\n")
    total_g, total_n = 0, 0

    car = build_car(dict(kWh=60, V=400, power_kW=150, curb_mass=1600))
    g, n = ground_report(car); total_g += g; total_n += n
    bus = solve(car, seed={"total_mass": 1700})
    print(f"  SOLVE: converged={bus.get('converged')}  total_mass={bus['total_mass']:.0f} kg  "
          f"top_speed={car_top_speed(car, bus):.0f} m/s  ({car_top_speed(car, bus)*3.6:.0f} km/h)")

    conv = build_converter(dict(f_khz=100, uH=47, uF=470))
    g, n = ground_report(conv); total_g += g; total_n += n
    bus = solve(conv, seed={"total_mass": 0.1})
    print(f"  SOLVE: converged={bus.get('converged')}  total_mass={bus['total_mass']*1000:.0f} g")

    print(f"\nCOVERAGE: {total_g}/{total_n} subsystem functions grounded to the library across both domains.")
    print("Blind functions above = the bindings to add next.")
