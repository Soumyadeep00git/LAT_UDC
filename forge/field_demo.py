r"""FIELD-LAYER DEMONSTRATOR - one engine, no platform, no mission. Optics, kinematics, economics.

Every problem below is written ONLY as params + linkages. The same field.solve_field / field.diagnose /
field.relax_with_new_dof run on all of them. The engine never learns what domain it is in. That is the
point: the field is embodiment-free; the hardware (a lens, a linkage bar, a policy instrument) is the
engineer's job downstream.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import field
from field import Structure


def line():
    print("-" * 88)


# ============================================================ 1. SOLVE THE FIELD (three domains)
def optics_structure():
    s = Structure()
    for n, sc in [("focal", 0.03), ("pixel_pitch", 3e-6), ("ifov", 1e-4), ("n_pixels", 2000),
                  ("fov", 0.3), ("target_size", 0.35), ("detection_range", 2500.0), ("n_det", 2.0)]:
        s.add_param(n, scale=sc)
    s.add_link("ifov_law", ["ifov", "focal", "pixel_pitch"],
               lambda a: a["ifov"] * a["focal"] / a["pixel_pitch"] - 1)
    s.add_link("fov_law", ["fov", "n_pixels", "ifov"],
               lambda a: a["fov"] / (a["n_pixels"] * a["ifov"]) - 1,
               node="optics.space_bandwidth_product")
    s.add_link("detect_law", ["detection_range", "n_det", "ifov", "target_size"],
               lambda a: a["detection_range"] * a["n_det"] * a["ifov"] / a["target_size"] - 1)
    return s


def kinematics_structure():
    s = Structure()
    for n, sc in [("r", 0.05), ("l", 0.15), ("theta", 1.0), ("x", 0.15), ("omega", 10.0), ("vx", 0.5)]:
        s.add_param(n, scale=sc)

    def _pos(a):
        den = a["r"] * math.cos(a["theta"]) + math.sqrt(a["l"] ** 2 - (a["r"] * math.sin(a["theta"])) ** 2)
        return a["x"] / den - 1

    def _vel(a):
        root = math.sqrt(a["l"] ** 2 - (a["r"] * math.sin(a["theta"])) ** 2)
        expr = -(a["r"] * math.sin(a["theta"]) * a["omega"]
                 + a["r"] ** 2 * math.sin(a["theta"]) * math.cos(a["theta"]) * a["omega"] / root)
        return a["vx"] / expr - 1

    s.add_link("slider_position", ["x", "r", "l", "theta"], _pos, node="kinematics.slider_crank")
    s.add_link("slider_velocity", ["vx", "r", "l", "theta", "omega"], _vel, node="kinematics.slider_crank")
    return s


def economics_structure():
    s = Structure()
    for n, sc in [("P", 10.0), ("Q", 100.0), ("a", 120.0), ("b", 2.0), ("c", 20.0), ("d", 3.0)]:
        s.add_param(n, scale=sc)
    s.add_link("demand_curve", ["Q", "a", "b", "P"], lambda z: z["Q"] / (z["a"] - z["b"] * z["P"]) - 1,
               node="microeconomics.linear_demand")
    s.add_link("supply_curve", ["Q", "c", "d", "P"], lambda z: z["Q"] / (z["c"] + z["d"] * z["P"]) - 1,
               node="microeconomics.linear_supply")
    return s


def demo_solve():
    print("=" * 88)
    print("1.  SOLVE THE FIELD  -  same engine, three unrelated domains")
    print("=" * 88)

    line(); print("OPTICS   knowns: focal 30mm, pixel 3um, 1920 px, target 0.35m  ->  solve the optical field")
    s = optics_structure()
    r = field.solve_field(s, {"focal": 0.03, "pixel_pitch": 3e-6, "n_pixels": 1920,
                              "target_size": 0.35, "n_det": 2.0}, seed={"detection_range": 2000})
    v = r.values
    print(f"  status={r.status}  ifov={v['ifov']*1e3:.3f} mrad  fov={math.degrees(v['fov']):.1f} deg  "
          f"detection_range={v['detection_range']:.0f} m")

    line(); print("KINEMATICS  slider-crank  knowns: r 50mm, l 150mm, theta 1rad, omega 10rad/s  ->  x, vx")
    s = kinematics_structure()
    r = field.solve_field(s, {"r": 0.05, "l": 0.15, "theta": 1.0, "omega": 10.0},
                          seed={"x": 0.15, "vx": -0.4})
    v = r.values
    print(f"  status={r.status}  x={v['x']*1000:.1f} mm  vx={v['vx']:.3f} m/s")

    line(); print("ECONOMICS  supply/demand  knowns: Qd=120-2P, Qs=20+3P  ->  equilibrium P, Q")
    s = economics_structure()
    r = field.solve_field(s, {"a": 120, "b": 2, "c": 20, "d": 3}, seed={"P": 15, "Q": 80})
    v = r.values
    print(f"  status={r.status}  P*={v['P']:.2f}  Q*={v['Q']:.2f}   (closed form P*=(a-c)/(b+d)=20, Q*=80)")


# ============================================================ 2. DEGREES OF FREEDOM (generic)
def demo_dof():
    print("\n" + "=" * 88)
    print("2.  DEGREES OF FREEDOM  -  the null space of the linkage Jacobian, read generically")
    print("=" * 88)
    s = optics_structure()
    # leave focal AND n_pixels open -> the optical field has free axes
    r = field.solve_field(s, {"pixel_pitch": 3e-6, "target_size": 0.35, "n_det": 2.0},
                          seed={"focal": 0.03, "n_pixels": 1920, "detection_range": 2000})
    print(f"OPTICS with focal & n_pixels open: status={r.status}  n_dof={r.n_dof}")
    for i, d in enumerate(r.dof_basis):
        print(f"  free axis {i+1}: {d}")
    print("  (the engine found the open axes itself - it did not know these were 'lens' and 'sensor').")


# ============================================================ 3. MISSING DIMENSION (generic diagnosis)
def demo_conflict():
    print("\n" + "=" * 88)
    print("3.  MISSING DIMENSION  -  imposed demands over-constrain the field (domain-agnostic)")
    print("=" * 88)

    line(); print("OPTICS: demand long detection AND a wide cone, with the sensor pixel count FIXED")
    s = optics_structure()
    R_req, FOV_req = 2500.0, math.radians(60.0)
    s.add_link("demand_detect", ["detection_range"], lambda a: a["detection_range"] / R_req - 1, kind="demand")
    s.add_link("demand_cover", ["fov"], lambda a: a["fov"] / FOV_req - 1, kind="demand")
    knowns = {"pixel_pitch": 3e-6, "target_size": 0.35, "n_det": 2.0, "n_pixels": 1920}
    d = field.diagnose(s, knowns, seed={"focal": 0.03, "ifov": 1e-4, "fov": 0.3, "detection_range": 2000})
    print(f"  diagnosis: {d['status']}")
    if d["status"] == "MISSING_DOF":
        print(f"    conflict          : {d['conflict'][0]}  vs  {d['conflict'][1]}")
        print(f"    binding invariant : {d['binding_invariant']}")
        print(f"    reading           : {d['reading']}")
        # RELAX: add one new axis (a scan gain = coverage over time) into the etendue law
        def inject_scan(st):
            for i, L in enumerate(st.linkages):
                if L.name == "fov_law":
                    st.linkages[i] = field.Linkage(
                        "fov_law", ["fov", "n_pixels", "ifov", "scan_gain"],
                        lambda a: a["fov"] / (a["n_pixels"] * a["ifov"] * a["scan_gain"]) - 1, "law", L.node)
        r2 = field.relax_with_new_dof(s, knowns, "scan_gain", inject_scan,
                                      seed={"focal": 0.03, "ifov": 1e-4, "fov": 0.3,
                                            "detection_range": 2000, "scan_gain": 3.0})
        print(f"    RELAX + scan_gain : status={r2.status}  scan_gain={r2.values.get('scan_gain'):.2f}x  "
              f"-> adding ONE axis makes the field solvable (the hardware for it is the engineer's choice)")

    line(); print("ECONOMICS: the market field has 0 DOF; a policymaker demands Q >= 100 (above equilibrium 80)")
    s = economics_structure()
    s.add_link("demand_qfloor", ["Q"], lambda z: z["Q"] / 100.0 - 1, kind="demand")
    knowns = {"a": 120, "b": 2, "c": 20, "d": 3}
    d = field.diagnose(s, knowns, seed={"P": 15, "Q": 80})
    print(f"  diagnosis: {d['status']}  ->  {d['reading']}")

    def inject_subsidy(st):
        for i, L in enumerate(st.linkages):
            if L.name == "supply_curve":
                st.linkages[i] = field.Linkage(
                    "supply_curve", ["Q", "c", "d", "P", "subsidy"],
                    lambda z: z["Q"] / (z["c"] + z["d"] * z["P"] + z["subsidy"]) - 1, "law", L.node)
    r2 = field.relax_with_new_dof(s, knowns, "subsidy", inject_subsidy, seed={"P": 12, "Q": 100, "subsidy": 30})
    print(f"    RELAX + subsidy   : status={r2.status}  subsidy={r2.values.get('subsidy'):.1f}, "
          f"P={r2.values.get('P'):.2f}  -> the SAME 'add an axis' move, now a policy instrument")


def main():
    demo_solve()
    demo_dof()
    demo_conflict()
    print("\n" + "=" * 88)
    print("READING IT")
    print("  One solver. Optics, a mechanism, and a market - solved, DOF-counted, and diagnosed with the")
    print("  identical code, because all three are just params linked by relations. 'Missing dimension' is a")
    print("  structural property of the linkage graph (over-determined but each demand feasible alone), and")
    print("  its fix is always the same shape: ADD AN AXIS. What that axis becomes in metal - a gimbal, a")
    print("  variable-pitch hub, a subsidy - is the embodiment, and that is handed to the engineers.")


if __name__ == "__main__":
    main()
