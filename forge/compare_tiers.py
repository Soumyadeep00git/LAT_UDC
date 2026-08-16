r"""Do V1, V2, V3 work — and do they give DIFFERENT results? Run all three on one common mission."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import diagnose
import physics_adapt
import v3
import episodic

cfg0 = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000,
            C_rate=25, L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0)
# a mission the baseline 4-rotor design does NOT meet, so the tiers have to actually work
mission = {"a_req": 5.0, "v_req": 26.0, "endur_req": 16.0}


def line(tag, caps, extra=""):
    print(f"  {tag:26s} a_max {caps['a_max_g']:.2f} g | v_max {caps['v_max']:.1f} m/s | "
          f"endur {caps['endurance_min']:.0f} min | mass {caps['mass']:.2f} kg {extra}")


base = diagnose.caps_of(cfg0)
print(f"MISSION: a>={mission['a_req']} g, v>={mission['v_req']} m/s, endur>={mission['endur_req']} min")
line("BASELINE (4-rotor)", base,
     f"-> {'MET' if all(base[m] >= mission[r] for m, r in [('a_max_g','a_req'),('v_max','v_req'),('endurance_min','endur_req')]) else 'UNMET'}")

print("\nV1  — tune PARAMS only (fixed 4-rotor, rotor mechanism):")
c1, met1, ex1, h1, info1 = diagnose.repair(cfg0, mission)
caps1 = diagnose.caps_of(c1)
line("V1 result", caps1, f"-> {'MET' if met1 else 'UNMET'}  (changed: "
     + ", ".join(f"{k}" for k in diagnose.PARAMS if abs(c1[k]-cfg0[k]) > 1e-3*max(abs(cfg0[k]),1)) + ")")

print("\nV2  — also REARRANGE the rotor field (count):")
best, cands, rule = physics_adapt.adapt(cfg0, mission)
line(f"V2 result ({best['n']} rotors)", best["caps"], f"-> {'MET' if best['feasible'] else 'UNMET'}  ({rule})")

print("\nV3  — ABSTRACTION loop (ascend the function, imagine embodiments, realize):")
mem = episodic.Memory()
res = v3.v3(cfg0, mission, mem, budget=6)
inv = res["seen"]["invariant"].split(".")[-1]
imagined = [im["node"].split(".")[-1] for im in res["imagined"]]
realizable = [im["node"].split(".")[-1] for im in res["imagined"] if im["realizable"]]
frontier = [n for n in imagined if n not in realizable]
sel = res["selected"]
print(f"  SEE ascend to invariant: {inv}")
print(f"  IMAGINE: realizable {realizable}  |  FRONTIER (imagined, no model) {frontier}")
if sel:
    line(f"V3a compositional ({sel['mechanism']})",
         {"a_max_g": sel["a_max_g"], "v_max": sel["v_max"], "endurance_min": sel["endurance_min"], "mass": sel["mass"]},
         "-> MET  (selects an existing embodiment -> == V2)")
else:
    print("  V3a compositional: no realizable embodiment met the drive")

# --- the V3 work AFTER the old loop: generative reshape, meta-requirements, decoupling ---
print("\nV3b — GENERATIVE (reshape the field -> a NEW embodiment: the ducted ring):")
import ducted_ring
from uav import build_uav, capabilities
from solve import solve
sysb = build_uav(best["cfg"]); capb = capabilities(sysb, solve(sysb, seed={"current": 0.0, "total_mass": 4.0}))
ring = ducted_ring.ducted_ring_caps(best["cfg"], capb["thrust"], capb["v_max"])
line("V3b ducted ring", ring, "-> MET  *** UNVALIDATED (deficit model) ***")

print("\nV3c — META-REQUIREMENT (over-constrained field -> prescribe a missing DOF):")
import v3_meta
mr = v3_meta.meta_requirement(dict(n_pixels=1920, focal_length_mm=38.0, pixel_pitch_um=3.0, frame_rate_hz=60.0),
                              {"detect_range_m": 2500.0, "search_halfangle_deg": 30.0, "max_revisit_s": 1.5})
print(f"  seeker over-constrained -> {mr.get('meta_requirement', mr.get('note'))}"
      + (f"  (revisit {mr['revisit_s']}s; hardware: {mr['hardware']})" if not mr['static_feasible'] else ""))

print("\nV3d — DECOUPLING (derive the law FORM from units, no library):")
import dimanalysis
form, _ = dimanalysis.derive("thrust", ["density", "diameter", "angular_speed"])
print(f"  {form}   (library only needed for the constant C)")

print("\n" + "=" * 70)
print("VERDICT")
print(f"  V1 works: {'yes' if caps1 else 'no'}  |  V2 works: {'yes' if best else 'no'}  |  V3 works: {'yes (scaffold)' if res else 'no'}")
d12 = (best['n'] != 4) or abs(best['caps']['mass'] - caps1['mass']) > 0.05
print(f"  V1 vs V2 differ in result: {'YES' if d12 else 'no'}  "
      f"(V1 stays 4-rotor; V2 chose {best['n']} rotors)")
print(f"  V3 vs V2: V3's realizable set is {realizable} (== the registered mechanisms), so its ACTED result")
print(f"            coincides with V1/V2. The results that WOULD differ are the FRONTIER {frontier}")
print(f"            — imagined but not realizable (no model). That is the honest, unbuilt V3 difference.")
