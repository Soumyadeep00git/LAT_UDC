r"""UAV-SEEKER PACK — the sanctuary restructured on a STRUCT basis for one real problem.

Stop battling in the abstract. Here the physics is a CLOSED, LINKED structure for the UAV-seeker: every
capability is a node, every coupling is an executable law, nothing dangles. It assembles into the field
solver and is validated the honest way (the reliability gate) — by reproducing uav.py's numbers.

Division of labour (deficit dispatch, the project's own principle):
  - ATOMS: the few quantities that need the validated numerical backends (per-rotor BEMT thrust, battery
    energy, coupled electrical sag, the v_max root-find, component masses) are read from one uav.py solve.
    These are the "constitutive" values - defined once, in the modules that own them.
  - LINKS: everything the design reasoning actually turns on (mass buildup, weight, thrust-to-weight,
    a_max, disk area, hover power, endurance WITH the seeker's power draw, and the full seeker chain
    ifov -> detection_range / fov / track_rate, plus the etendue limiter) is a structured law here.

Solve the structure -> the UAV-seeker capabilities, produced from the linked laws, matching uav.py.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import field
from executable_law import Law, assemble
from uav import build_uav, capabilities, G, IN2M, RHO_AIR, FM_HOVER, SEEKER_TARGET_M, SEEKER_DEFAULTS
from solve import solve

N_DET = 2.0


def atoms(cfg):
    """Read the constitutive atoms from ONE validated uav.py solve (the backend-owned quantities)."""
    sysm = build_uav(cfg)
    bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
    cap = capabilities(sysm, bus)
    by = sysm.by_name()
    n = cfg["n_rotors"]
    a = {
        "n_rotors": n, "D_in": cfg["D_in"],
        "T_rotor": by["propulsion"].state["thrust"] / n,
        "prop_mass": by["propulsion"].state.get("mass", 0.0),
        "battery_mass": by["energy"].state.get("mass", 0.0),
        "usable_energy": bus.get("usable_energy", 0.0),
        "structure_mass": by["structure"].state.get("mass", 0.0),
        "seeker_mass": by["seeker"].state.get("mass", 0.0),
        "seeker_power": by["seeker"].state.get("seeker_power_W", 0.0),
        "payload_mass": cfg.get("payload", 0.6),
        "focal": cfg.get("focal_length_mm", SEEKER_DEFAULTS["focal_length_mm"]) / 1000.0,
        "pixel_pitch": cfg.get("pixel_pitch_um", SEEKER_DEFAULTS["pixel_pitch_um"]) * 1e-6,
        "n_pixels": cfg.get("n_pixels", SEEKER_DEFAULTS["n_pixels"]),
        "frame_rate": cfg.get("frame_rate_hz", SEEKER_DEFAULTS["frame_rate_hz"]),
        "v_max_backend": cap["v_max"],
        # constants
        "g": G, "air_density": RHO_AIR, "figure_of_merit": FM_HOVER,
        "target_size": SEEKER_TARGET_M, "n_det": N_DET,
    }
    return a, cap


# ---- the LINKED structure: every capability a node, every coupling an executable law ----
def _laws():
    P = lambda **kw: kw
    L = []
    L.append(Law("rotorcraft_bemt.rotor_thrust", "thrust",
                 P(n_rotors="base", T_rotor="base"),
                 lambda a: a["thrust"] / (a["n_rotors"] * a["T_rotor"]) - 1,
                 "Total thrust = n rotors x per-rotor thrust (BEMT atom)."))
    L.append(Law("geometry_math.disk_diameter", "D_m",
                 P(D_in="base"),
                 lambda a: a["D_m"] / (a["D_in"] * IN2M) - 1,
                 "Rotor diameter in metres = D_in * 0.0254."))
    L.append(Law("geometry_math.circle_area", "disk_area",
                 P(n_rotors="base", D_m="derived"),
                 lambda a: a["disk_area"] / (a["n_rotors"] * math.pi * (a["D_m"] / 2) ** 2) - 1,
                 "Total actuator-disk area = n * pi (D/2)^2."))
    L.append(Law("classical_mechanics.mass_additivity", "total_mass",
                 P(battery_mass="base", prop_mass="base", structure_mass="base",
                   payload_mass="base", seeker_mass="base"),
                 lambda a: a["total_mass"] / (a["battery_mass"] + a["prop_mass"] + a["structure_mass"]
                                              + a["payload_mass"] + a["seeker_mass"]) - 1,
                 "Vehicle mass = sum of subsystem masses (incl. the seeker)."))
    L.append(Law("classical_mechanics.newtons_second_law", "weight",
                 P(total_mass="derived", g="base"),
                 lambda a: a["weight"] / (a["total_mass"] * a["g"]) - 1,
                 "Weight = mass * g."))
    L.append(Law("classical_mechanics.thrust_to_weight", "TWR",
                 P(thrust="derived", weight="derived"),
                 lambda a: a["TWR"] / (a["thrust"] / a["weight"]) - 1,
                 "Thrust-to-weight ratio = thrust / weight."))
    L.append(Law("classical_mechanics.max_lateral_accel", "a_max",
                 P(TWR="derived", g="base"),
                 lambda a: a["a_max"] / (a["g"] * math.sqrt(max(a["TWR"] ** 2 - 1.0, 1e-9))) - 1,
                 "Max lateral accel a = g sqrt(TWR^2 - 1)."))
    L.append(Law("rotorcraft_bemt.actuator_disk_momentum", "hover_power",
                 P(weight="derived", figure_of_merit="base", air_density="base", disk_area="derived"),
                 lambda a: a["hover_power"] / (a["weight"] ** 1.5
                                              / (a["figure_of_merit"] * math.sqrt(2 * a["air_density"] * a["disk_area"]))) - 1,
                 "Momentum-theory hover power P = W^1.5/(FM sqrt(2 rho A))."))
    L.append(Law("electrochemistry_batteries.pack_energy", "endurance",
                 P(usable_energy="base", hover_power="derived", seeker_power="base"),
                 lambda a: a["endurance"] / (a["usable_energy"] / (a["hover_power"] + a["seeker_power"])) - 1,
                 "Endurance = usable energy / (hover power + SEEKER power)."))
    # ---- seeker chain (the interception-relevant physics) ----
    L.append(Law("optics.angular_resolution", "ifov",
                 P(pixel_pitch="base", focal="base"),
                 lambda a: a["ifov"] / (a["pixel_pitch"] / a["focal"]) - 1,
                 "IFOV = pixel_pitch / focal_length."))
    L.append(Law("electro_optics.detection_range", "detection_range",
                 P(target_size="base", n_det="base", ifov="derived"),
                 lambda a: a["detection_range"] / (a["target_size"] / (a["n_det"] * a["ifov"])) - 1,
                 "Johnson detection range R = target / (N_det * IFOV)."))
    L.append(Law("electro_optics.field_of_view", "fov",
                 P(n_pixels="base", ifov="derived"),
                 lambda a: a["fov"] / (a["n_pixels"] * a["ifov"]) - 1,
                 "Instantaneous FOV = n_pixels * IFOV."))
    L.append(Law("electro_optics.field_of_view", "fov_deg",
                 P(fov="derived"),
                 lambda a: a["fov_deg"] / (a["fov"] * 180.0 / math.pi) - 1,
                 "FOV in degrees."))
    L.append(Law("electro_optics.track_rate", "track_rate",
                 P(frame_rate="base"),
                 lambda a: a["track_rate"] / a["frame_rate"] - 1,
                 "Track rate = sensor frame rate."))
    L.append(Law("aerodynamics.forward_flight_vmax", "v_max",
                 P(v_max_backend="base"),
                 lambda a: a["v_max"] / a["v_max_backend"] - 1,
                 "Top speed (BEMT forward-flight root-find atom)."))
    return L


DERIVED_SCALES = {"thrust": 40, "D_m": 0.33, "disk_area": 0.3, "total_mass": 3, "weight": 30,
                  "TWR": 2, "a_max": 20, "hover_power": 250, "endurance": 1600, "ifov": 1e-4,
                  "detection_range": 2000, "fov": 0.2, "fov_deg": 11, "track_rate": 60, "v_max": 30}


def solve_uav_seeker(cfg):
    a, cap = atoms(cfg)
    laws = _laws()
    s, knowns = assemble(laws, a, DERIVED_SCALES)
    sol = field.solve_field(s, knowns, seed=DERIVED_SCALES)
    return sol, cap, laws


def etendue_gate(sol, search_halfangle_deg=30.0):
    """The interception limiter, structurally: can the STATIC seeker cover the search cone at detection res?"""
    v = sol.values
    omega_inst = v["fov"] ** 2
    th = math.radians(search_halfangle_deg)
    omega_req = 2 * math.pi * (1 - math.cos(th))
    return {"inst_coverage_sr": omega_inst, "search_solid_sr": omega_req,
            "static_covers": omega_inst >= omega_req,
            "tiles": omega_req / omega_inst if omega_inst > 0 else float("inf")}


if __name__ == "__main__":
    cfg = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, C_rate=25,
               L_arm=0.30, payload=0.6, n_rotors=6, wh_per_kg=300.0,
               focal_length_mm=38.0, pixel_pitch_um=3.0, n_pixels=1920, frame_rate_hz=60.0)
    sol, cap, laws = solve_uav_seeker(cfg)
    v = sol.values

    print("=" * 82)
    print("UAV-SEEKER PACK  -  the sanctuary as a linked, closed, executable structure")
    print("=" * 82)
    print(f"  solve status: {sol.status}   residual: {sol.residual:.1e}   laws: {len(laws)}   orphans: 0")

    print("\n  CAPABILITIES from the linked laws     vs   uav.py (the trusted model):")
    checks = [("mass (kg)", v["total_mass"], cap["mass"]),
              ("a_max (g)", v["a_max"] / G, cap["a_max"] / G),
              ("v_max (m/s)", v["v_max"], cap["v_max"]),
              ("endurance (min)", v["endurance"] / 60, cap["endurance"] / 60),
              ("detection_range (m)", v["detection_range"], cap["detection_range"]),
              ("seeker FOV (deg)", v["fov_deg"], cap["seeker_fov_deg"]),
              ("track rate (Hz)", v["track_rate"], cap["track_rate_hz"])]
    worst = 0.0
    for name, got, ref in checks:
        rel = abs(got - ref) / max(abs(ref), 1e-9)
        worst = max(worst, rel)
        print(f"    {name:22s} {got:12.3f}   {ref:12.3f}   rel_err {rel:.2e}")
    print(f"\n  WORST rel err vs uav.py: {worst:.2e}  -> {'MATCH (structure reproduces the model)' if worst < 1e-3 else 'MISMATCH - investigate'}")

    print("\n  SEEKER LIMITER (why interception is seeker-bound), read from the structure:")
    gate = etendue_gate(sol, 30.0)
    print(f"    detection {v['detection_range']:.0f} m needs IFOV {v['ifov']*1e3:.3f} mrad -> FOV {v['fov_deg']:.1f} deg "
          f"(coverage {gate['inst_coverage_sr']:.3f} sr)")
    print(f"    a 60 deg search cone is {gate['search_solid_sr']:.2f} sr -> static seeker covers it: {gate['static_covers']}"
          + ("" if gate['static_covers'] else f"  (needs {gate['tiles']:.0f} looks -> a SCAN degree of freedom)"))

    grounded = sum(1 for lw in laws if __import__("library").A.ARCHIVE.get(lw.node))
    print(f"\n  grounding: {grounded}/{len(laws)} laws hit an existing sanctuary node "
          f"({len(laws)-grounded} are new producer nodes this pack defines).")
