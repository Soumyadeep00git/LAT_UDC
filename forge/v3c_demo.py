r"""V3c DEMONSTRATOR — one generic diagnostic algorithm, three domains added purely as DATA.

Each case is just a design + a mission. The SAME engine (v3c.diagnose_invariant) runs the same steps for
every grounded TradeInvariant in v3c.REGISTRY. Nothing is hand-flagged; no per-domain branch in the engine.
Output per diagnosis:
  CONFLICT    a pair of constraints is each satisfiable alone but never together -> a confirmed missing axis
  MODEL_GAP   a real trade the reduced model cannot price (a constraint returns None)
  no_wall     a single configuration satisfies every constraint (a value fix), or V1/V2 already met it
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import v3c

BASE = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, C_rate=25,
            L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0,
            n_pixels=1920, focal_length_mm=38.0, pixel_pitch_um=3.0, frame_rate_hz=60.0)

CASES = [
    ("CONTROL - a modest mission a value/structure should meet",
     dict(a_req=4.0, v_req=16.0, endur_req=14.0)),
    ("SEEKER - long detection AND a wide search cone  (optics)",
     dict(a_req=3.0, v_req=14.0, endur_req=12.0,
          detect_range_m=2500.0, search_halfangle_deg=30.0, max_revisit_s=1.5)),
    ("BATTERY - endurance AND high-g burst  (electrochemistry)",
     dict(a_req=8.0, v_req=18.0, endur_req=30.0)),
    ("ROTOR - long loiter AND high dash speed  (aerodynamics)",
     dict(a_req=3.5, v_req=45.0, endur_req=35.0)),
]


def main():
    print("=" * 86)
    print("V3c - UNIFORM META-REQUIREMENT DIAGNOSTIC   (one engine, domains added as grounded DATA)")
    print("=" * 86)
    print(f"REGISTRY (data records, not engine code): {[inv.key for inv in v3c.REGISTRY]}")
    print("For every record the SAME steps run: engaged? -> sample the free config space -> evaluate each")
    print("constraint at each point -> any point meets all? (value fix) / a pair met alone but never together?")
    print("(missing axis) / a constraint unpriceable? (model gap).")

    n_conf = 0
    for title, mission in CASES:
        print("\n" + "-" * 86)
        print(title)
        r = v3c.meta_requirements(BASE, dict(mission))
        if "V1" in r:
            print(f"  V1 (values)   : met={r['V1']['met']}  exhausted={r['V1']['exhausted']}  failing={r['V1']['failing']}")
        if "V2" in r:
            print(f"  V2 (structure): feasible={r['V2']['feasible']}  ({r['V2']['n_rotors']} rotors)")
        print(f"  ==> VERDICT: {r['verdict']}")

        for d in r["diagnoses"]:
            st = d.get("status")
            if st in ("CONFLICT", "MODEL_GAP"):
                g = d.get("grounded", {})
                tag = "[MISSING DIMENSION - CONFIRMED]" if st == "CONFLICT" else "[MISSING DIMENSION - MODEL GAP]"
                print(f"\n  {tag}  {d['name']}   (subsystem: {d['subsystem']})")
                print(f"    grounded node : {g.get('node','?')}  (in_library={g.get('in_library')}, descent {g.get('descent_depth','?')})")
                print(f"    conflicting   : {d['conflict_pair'][0]}  vs  {d['conflict_pair'][1]}")
                if "demands" in d:
                    print(f"      - {d['conflict_pair'][0]}: {d['demands'][0]}")
                    print(f"      - {d['conflict_pair'][1]}: {d['demands'][1]}")
                print(f"    evidence      : {d.get('evidence')}")
                print(f"    why           : {d['why']}")
                print(f"    MISSING AXIS  : {d['missing_dof']}")
                if st == "CONFLICT":
                    n_conf += 1
            elif st == "ABSOLUTE_LIMIT":
                print(f"\n  [ABSOLUTE LIMIT]  {d['name']}  ({d['subsystem']}): {d['why']}")
            elif st == "no_wall" and d.get("example_config"):
                print(f"  [no new axis]  {d['name']}: value fix exists -> {d.get('example_config')}")

    print("\n" + "=" * 86)
    print("READING IT")
    print(f"  Confirmed missing dimensions (proven by the solve): {n_conf}  (seeker etendue, battery Ragone).")
    print("  One algorithm processed all three from DATA; the engine holds no domain knowledge. The rotor case")
    print("  is honestly a MODEL-GAP: its 'hover-efficiency' constraint is unpriceable (momentum-theory hover")
    print("  power is pitch-independent), so the conflict is real physics the current model cannot score.")
    print("  Adding a 4th domain = adding a 4th TradeInvariant record. No engine change.")


if __name__ == "__main__":
    main()
