r"""Catalog map: turn an emergent physics quantity (from field_dofs) into a BUILDABLE, movable knob.

field_dofs.py discovers *what* governs each field (disk_area, specific_energy, ...). This maps each such
quantity to the concrete design variable(s) that set it, their bounds/options, and whether the model
currently RESPONDS to that knob ("wired"). specific_energy -> the battery's wh_per_kg (a discrete
chemistry choice) is now wired, so the optimizer can make a *material* (V3) move, not just resize mass.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

import diagnose
import field_dofs
import bondgraph
import parts as P

# specific_energy is a material choice: pick the cell chemistry (gravimetric energy density, Wh/kg)
CHEMISTRY = {"LiPo": 200, "Li-ion": 250, "Li-ion-HE": 300, "Li-S": 400, "solid-state": 450}

# emergent quantity -> actionable knob spec
CATALOG = {
    "disk_area":                {"knobs": ["D_in", "n_rotors"], "kind": "geometry",    "wired": True,
                                 "note": "A = n·π(D_in·0.0254/2)²"},
    "pack_mass":                {"knobs": ["S", "cap_mAh"],      "kind": "geometry",    "wired": True,
                                 "note": "pack size (voltage × capacity)"},
    "specific_energy":          {"knobs": ["wh_per_kg"],         "kind": "material",    "wired": True,
                                 "options": CHEMISTRY, "bounds": (200, 450), "note": "cell chemistry"},
    "usable_capacity_fraction": {"knobs": ["dod"],              "kind": "material",    "wired": False,
                                 "bounds": (0.8, 0.95), "note": "BMS depth-of-discharge (model DOD fixed)"},
    "disk_area_partition":      {"knobs": ["n_rotors"],          "kind": "geometry",    "wired": True},
    "fiber_distance":           {"knobs": ["arm_od"],            "kind": "geometry",    "wired": False,
                                 "note": "arm tube OD (structure model uses fixed section)"},
    "second_moment_of_area":    {"knobs": ["arm_od", "arm_wall"], "kind": "geometry",   "wired": False},
    "cross_section_area":       {"knobs": ["frame_area"],        "kind": "geometry",    "wired": False},
}


def design_vector(system):
    """The actionable design vector emerging from the fields' laws, via the catalog."""
    spec = []
    for q, cat, field in field_dofs.emergent_params(system):
        entry = CATALOG.get(q, {"knobs": ["?"], "kind": cat, "wired": False})
        spec.append({"quantity": q, "field": field, **entry})
    return spec


def _caps(cfg):
    c = diagnose.caps_of(cfg)
    return c


if __name__ == "__main__":
    cfg = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)
    system, meta = bondgraph.infer_system(P.quad_parts(cfg), cfg)

    print("ACTIONABLE DESIGN VECTOR (emerged from laws -> mapped to buildable knobs)\n")
    for s in design_vector(system):
        opt = f"  options={list(s.get('options', {}))}" if "options" in s else \
              (f"  bounds={s['bounds']}" if "bounds" in s else "")
        print(f"  {s['quantity']:24s} [{s['kind']:8s}] knobs={s['knobs']}  "
              f"{'WIRED' if s.get('wired') else 'not-wired-yet'}{opt}")

    print("\n" + "=" * 70)
    print("V3 MATERIAL lever: at a FIXED battery-mass budget, chemistry sets how much energy fits")
    S = cfg["S"]
    m_batt = S * (cfg["cap_mAh"] / 1000.0) * 3.7 / CHEMISTRY["LiPo"]   # baseline LiPo battery mass (kg)
    print(f"  battery-mass budget held at {m_batt:.2f} kg (baseline LiPo {cfg['cap_mAh']} mAh)\n")
    print(f"  {'chemistry':12s} {'Wh/kg':>6s} {'cap(mAh)':>9s} {'energy(Wh)':>10s} "
          f"{'endurance':>9s} {'mass(kg)':>8s}")
    for name, whkg in sorted(CHEMISTRY.items(), key=lambda kv: kv[1]):
        cap = m_batt * whkg / (S * 3.7) * 1000.0                       # mAh that fills the mass budget
        v = dict(cfg, wh_per_kg=whkg, cap_mAh=cap)
        c = _caps(v)
        Wh = S * (cap / 1000.0) * 3.7
        print(f"  {name:12s} {whkg:>6.0f} {cap:>9.0f} {Wh:>10.0f} {c['endurance_min']:>8.1f}m {c['mass']:>8.2f}")
    print("\n  endurance scales with specific_energy at ~equal mass — a MATERIAL (V3) lever the")
    print("  hand-param list (D_in,pitch,Kv,I_max,S,cap_mAh,L_arm) never exposed. It emerged from the law.")
