"""Sanity suite for the clean System foundation (forge/). Locks down the invariants so no loose end
reopens silently: the foundation gate, grounding of every subsystem, existence of every mechanism node,
correct recursion/aggregation, solve convergence, and a working physics-lensed mechanism swap."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "physics"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

import physics_archive as A
import platform_solve as PS
from solve import solve
from uav import build_uav, capabilities, G
from agent import ground_system, optimize_physics_lensed
import library

RES = []
def check(name, ok, detail=""):
    RES.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


CFG = dict(D_in=13, pitch_in=6, Kv=300, I_max=45, S=6, cap_mAh=5000, C_rate=60, L_arm=0.30)

print("A) FOUNDATION GATE — system graph reproduces the hi-fi solver")
for name, cfg in [("mid", CFG),
                  ("hi-pitch", dict(D_in=15, pitch_in=13, Kv=350, I_max=55, S=10, cap_mAh=6000, C_rate=60, L_arm=0.35))]:
    sysm = build_uav(cfg)
    cap = capabilities(sysm, solve(sysm, seed={"current": 0.0, "total_mass": 4.0}))
    ref = PS.solve(PS.Config(**cfg))
    dm, da = abs(cap["mass"] - ref.mass) / ref.mass, abs(cap["a_max"] - ref.a_max) / max(ref.a_max, 1e-6)
    check(f"{name}: mass & a_max match hi-fi", dm < 0.05 and da < 0.08, f"dm={dm*100:.1f}% da={da*100:.1f}%")

print("\nB) GROUNDING — every physics subsystem binds to a real library node")
sysm = build_uav(CFG)
for depth, nm, func, nid, desc, alts in ground_system(sysm):
    if nm == "payload":
        check(f"{nm}: 'mass' is a primitive with no defining law (not grounded)", nid is None)
    else:
        check(f"{nm}: '{func}' grounds", nid is not None, nid or "None")

print("\nC) MECHANISM NODES — every mechanism references a node that EXISTS in the library")
def all_subs(s):
    yield s
    for c in s.children:
        yield from all_subs(c)
for s in sysm.subsystems:
    for sub in all_subs(s):
        for mech, (_, node) in sub.mechanisms.items():
            check(f"{sub.name}/{mech} node exists", node is None or node in A.ARCHIVE, node or "-")

print("\nD) RECURSION — parent mass aggregates its children")
bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
st = sysm.by_name()["structure"]
arm = next(c for c in st.children if c.name == "arm")
frame = next(c for c in st.children if c.name == "frame")
agg = arm.state["mass"] + frame.state["mass"]
check("structure.mass == arm.mass + frame.mass", abs(st.state["mass"] - agg) < 1e-9, f"{st.state['mass']:.3f}={agg:.3f}")
check("solve converged", bus.get("converged") is True)
leaf_sum = sum(lf.state.get("mass", 0.0) for s in sysm.subsystems for lf in s.leaves())
check("total_mass == sum of leaf masses", abs(bus["total_mass"] - leaf_sum) < 1e-2, f"{bus['total_mass']:.3f}/{leaf_sum:.3f}")

print("\nE) PHYSICS-LENSED SWAP — both mechanisms evaluated, a winner is chosen")
mission = {"a_req": 5.0, "v_req": 30.0}
bounds = dict(D_in=(8, 22), pitch_in=(4, 14), Kv=(150, 450), I_max=(20, 90),
              S=(4, 12), cap_mAh=(2000, 16000), L_arm=(0.15, 0.6))
(best_mech, bd, bcfg, bcap, bok, _), results = optimize_physics_lensed(mission, CFG, bounds, radius=2)
evaluated = [r for r in results if r[3] is not None]
check("both propulsion mechanisms evaluated", len(evaluated) == 2, f"{[r[0] for r in evaluated]}")
check("chosen design meets the mission", bok is True)
check("chosen is the min-mass mission-meeting option",
      all(bcap["mass"] <= r[3]["mass"] + 1e-6 for r in evaluated if r[4]))

print("\nF) PER-SUBSYSTEM SEARCH CONTROL — budgets are respected")
from codesign import mechanisms_within_budget
g = build_uav(CFG)
prop = g.by_name()["propulsion"]
frame = next(c for c in g.by_name()["structure"].children if c.name == "frame")
check("propulsion budget=2, others pinned=0",
      prop.radicality_budget == 2 and g.by_name()["energy"].radicality_budget == 0 and frame.radicality_budget == 0)
check("propulsion(budget 2) may cross to ducted_fan",
      "ducted_fan" in [m for m, _ in mechanisms_within_budget(prop, 2)])
check("propulsion(budget 0) is pinned to rotor",
      [m for m, _ in mechanisms_within_budget(prop, 0)] == ["rotor"])
check("frame(budget 0) is pinned to its one mechanism", len(mechanisms_within_budget(frame, 0)) == 1)
check("each subsystem declares what it owns",
      prop.owns == ["a_max", "v_max"] and g.by_name()["energy"].owns == ["endurance"])

print("\nG) NAMING STANDARD — every subsystem function is a plain canonical quantity")
import vocabulary as V
g = build_uav(CFG)
allsubs = list(g.subsystems) + [c for s in g.subsystems for c in s.children]
names = [s.function for s in allsubs]
bad = V.lint(names)
check("all subsystem functions are canonical", not bad, f"violations: {bad}")
check("canonical() collapses thrust variants",
      V.canonical("rotor_thrust") == "thrust" and V.canonical("net thrust") == "thrust")
check("is_canonical rejects a variant", not V.is_canonical("rotor_thrust") and V.is_canonical("thrust"))

print("\n" + "=" * 60)
print(f"  {sum(RES)}/{len(RES)} checks passed")
print("=" * 60)
sys.exit(0 if all(RES) else 1)
