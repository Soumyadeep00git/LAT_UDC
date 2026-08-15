"""Sanity checks for the whole Arch-2 agent — archive integrity, grounding, namespace discipline,
radicality laws, generation validity, and the end-to-end pipeline flow. PASS/FAIL per invariant."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "physics"))

import physics_archive as A
import library
import radicality as R
import generate as G
import pipeline as P

RESULTS = []
def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def descends(nid, seen=None):
    seen = seen or set()
    if nid in seen: return False
    seen.add(nid)
    n = A.ARCHIVE.get(nid)
    if not n: return False
    if n.provenance == "fundamental": return True
    return any(descends(p, seen) for p in n.points_to if p in A.ARCHIVE)


print("A) ARCHIVE INTEGRITY")
ids = set(A.ARCHIVE)
dangling = [(nid, p) for nid, n in A.ARCHIVE.items() for p in n.points_to if p not in ids]
check("no dangling pointers", not dangling, f"{len(dangling)} found")
orphans = [nid for nid, n in A.ARCHIVE.items() if n.provenance != "fundamental" and not descends(nid)]
check("every node descends to a fundamental", not orphans, f"{len(orphans)} orphans")
bad_fund = [nid for nid, n in A.ARCHIVE.items() if n.provenance == "fundamental" and n.points_to]
check("fundamentals have empty points_to", not bad_fund, f"{len(bad_fund)} violate")
selfloop = [nid for nid, n in A.ARCHIVE.items() if nid in n.points_to]
check("no self-loops", not selfloop, f"{len(selfloop)} found")
baddir = [nid for nid, n in A.ARCHIVE.items() for d in n.requires.values() if d not in (1, -1, 0)]
check("all requires directions in {+1,-1,0}", not baddir, f"{len(baddir)} bad")
idx_ok = all(nid in A.BY_QUANTITY.get(n.quantity, []) for nid, n in A.ARCHIVE.items())
check("BY_QUANTITY index consistent", idx_ok)

print("\nB) GROUNDING & NAMESPACE DISCIPLINE")
check("known quantity classifies as physics", library.classify("thrust") == "physics")
check("unknown name classifies as math", library.classify("zzq_not_a_thing_42") == "math")
g = library.ground_quantity("thrust", ["disk_area", "induced_velocity", "air_density"])
overlap = g and (set(A.ARCHIVE[g].requires) & {"disk_area", "induced_velocity", "air_density"})
check("thrust grounds to an overlapping law", bool(overlap), f"{g}")
check("unknown quantity grounds to None", library.ground_quantity("not_a_quantity_xyz") is None)

print("\nC) RADICALITY LAWS")
rotor = "rotorcraft_bemt.rotor_thrust"
near = "rotorcraft_bemt.blade_element_thrust"       # a variation (adjacent)
far = "rocket_propulsion.thrust"                     # a different mechanism
check("self-distance is zero", R.distance(rotor, rotor) == 0)
check("distance is symmetric", R.distance(rotor, far) == R.distance(far, rotor))
check("adjacent variation is nearer than a different mechanism", R.distance(rotor, near) < R.distance(rotor, far),
      f"near={R.distance(rotor,near)} far={R.distance(rotor,far)}")
a2 = {x for x, _ in R.alternatives("thrust", far, 2)}
a5 = {x for x, _ in R.alternatives("thrust", far, 5)}
check("alternatives monotonic in radius", a2 <= a5, f"{len(a2)}<= {len(a5)}")
check("swap_report reachable for connected pair", R.swap_report(rotor, far).get("reachable") is True)

print("\nD) GENERATION VALIDITY")
req = frozenset({"thrust", "energy_storage", "load_bearing"})
masses = {}
for r in (0, 5, 8):
    subset, mass = G.generate(req, r)
    masses[r] = mass
    covered = frozenset().union(*[s["provides"] for s in subset])
    over = [s for s in subset if s["radicality"] > r]
    check(f"radius {r}: cover is complete", req <= covered)
    check(f"radius {r}: no provider exceeds budget", not over)
check("mass non-increasing as radius opens", masses[0] >= masses[5] >= masses[8],
      f"{masses[0]} >= {masses[5]} >= {masses[8]}")
r0_subset, _ = G.generate(req, 0)
check("radius 0 uses no fusion", all(len(s["provides"]) == 1 for s in r0_subset))

print("\nE) PIPELINE FLOW")
def T_flawed(air_density, disk_area, induced_velocity, tuning_knob):
    return disk_area * induced_velocity ** 2 * tuning_knob / air_density   # WRONG: thrust falls with air density
def T_correct(air_density, disk_area, induced_velocity, climb_velocity):
    return 2.0 * air_density * disk_area * induced_velocity * (induced_velocity + climb_velocity)

flawed = P.Problem("flawed", lambda **k: 0, {"disk_area": [0.3, (0.1, 1.5)]},
                   {"thrust": T_flawed}, fixed={"air_density": 1.225, "induced_velocity": 8.0, "tuning_knob": 1.0})
tf = P.run(flawed, verbose=False)
check("flawed model is NOT fully connected", tf.perception["fully_connected"] is False)
check("flawed model does not reach design", tf.design is None)

correct = P.Problem("correct", lambda **k: 0, {"disk_area": [0.3, (0.1, 1.5)]},
                    {"thrust": T_correct}, fixed={"air_density": 1.225, "induced_velocity": 8.0, "climb_velocity": 15.0},
                    required_properties=req, radius=8)
tc = P.run(correct, verbose=False)
check("correct model IS fully connected", tc.perception["fully_connected"] is True)
check("correct model reaches a design", tc.design is not None and bool(tc.design.get("config")))

print("\n" + "=" * 60)
print(f"  {sum(RESULTS)}/{len(RESULTS)} checks passed")
print("=" * 60)
sys.exit(0 if all(RESULTS) else 1)
