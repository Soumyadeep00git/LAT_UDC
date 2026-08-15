"""Correction pass — apply the verify agent's flagged fixes deterministically, add the missing
fundamental roots the orphans need, dedup, re-check integrity, and regenerate physics_archive.py.
Every edit is inspectable here (no silent agent rewrites)."""
import json
import os
import sys

OUT = sys.argv[1]
DEST = os.path.join(os.path.dirname(__file__), "physics_archive.py")

raw = json.load(open(OUT, encoding="utf-8"))
nodes = {n["id"]: n for n in raw["result"]["nodes"]}

# --- new FUNDAMENTAL roots the library was missing (orphans had nowhere to descend to) ---
def R(id, quantity, law, domain, requires=None):
    return {"id": id, "quantity": quantity, "law": law, "provenance": "fundamental",
            "level": "fundamental", "domain": domain, "requires": requires or [], "points_to": []}

NEW = [
    R("mathematics.euclidean_geometry", "geometry",
      "Euclidean space: lengths, areas and second moments of area are integrals over geometry", "mathematics"),
    R("mathematics.rotation_group_so3", "rotation",
      "Rigid rotations form the group SO(3); quaternion/Euler/DCM kinematics are its parametrizations", "mathematics"),
    R("thermodynamics.kinetic_theory_of_gases", "molecular_kinetics",
      "Pressure & temperature arise from molecular momentum transfer; <1/2 m v^2> = 3/2 kT (equipartition)",
      "thermodynamics", [{"variable": "temperature", "direction": "+"}]),
    R("electrochemistry.faradays_electrolysis_law", "charge_transfer",
      "Q = n*F*(moles reacted): charge transferred is proportional to moles of reactant (Faraday constant)",
      "electrochemistry", [{"variable": "moles_reactant", "direction": "+"},
                           {"variable": "electrons_per_reaction", "direction": "+"}]),
]
for n in NEW:
    nodes[n["id"]] = n

DELETE = {"thermodynamics.fourier_conduction"}          # duplicate of heat_transfer.fouriers_law

# --- field-level patches (points_to / provenance / law / quantity / requires) ---
PATCH = {
    "thermodynamics.first_law": {"provenance": "derived"},
    "thermodynamics.brayton_efficiency": {"drop_points": ["fluids_aero.continuity"]},
    "thermodynamics.ideal_gas_law": {"points_to": ["thermodynamics.kinetic_theory_of_gases"]},
    "electric_machines.electrical_frequency": {"points_to": ["mathematics.rotation_group_so3"]},
    "heat_transfer.view_factor": {"points_to": ["mathematics.euclidean_geometry"], "requires": []},
    "heat_transfer.stefan_boltzmann_law": {"law": "E_b = sigma*T^4 : blackbody hemispherical emissive power",
                                           "requires": [{"variable": "temperature", "direction": "+"}]},
    "electric_machines.eddy_current_loss": {
        "law": "P_eddy ~ (B*f*t)^2 / rho : eddy loss rises with flux density, frequency and lamination "
               "thickness, and FALLS as core resistivity rises",
        "requires": [{"variable": "flux_density", "direction": "+"}, {"variable": "frequency", "direction": "+"},
                     {"variable": "lamination_thickness", "direction": "+"}, {"variable": "resistivity", "direction": "-"}]},
    "electrochemistry.faraday_capacity": {"points_to": ["electrochemistry.faradays_electrolysis_law"]},
    "rigid_body.attitude_rotation_operator": {"provenance": "derived", "points_to": ["mathematics.rotation_group_so3"]},
    "solid_mechanics.second_moment_area": {"provenance": "derived", "points_to": ["mathematics.euclidean_geometry"]},
    "rigid_body.rotational_kinetic_energy": {"quantity": "rotational_kinetic_energy"},
    "electric_machines.slot_current_density": {"points_to": ["mathematics.euclidean_geometry"]},
    "fluids_aero.speed_of_sound": {"add_requires": [{"variable": "heat_capacity_ratio", "direction": "+"}],
                                   "points_to": ["thermodynamics.kinetic_theory_of_gases", "thermodynamics.ideal_gas_law"]},
    "classical_mechanics.gravitational_potential_energy": {
        "law": "U = m*g*h (near-surface uniform-field limit of gravitational PE)"},
}

# --- re-root the orphan families down to a fundamental ---
ORPHAN_ROOT = {
    "rigid_body.quaternion_kinematics": ["mathematics.rotation_group_so3"],
    "rigid_body.euler_angle_kinematics": ["mathematics.rotation_group_so3"],
    "rigid_body.angular_velocity_composition": ["mathematics.rotation_group_so3"],
    "solid_mechanics.normal_strain": ["mathematics.euclidean_geometry"],
    "solid_mechanics.polar_moment_area": ["mathematics.euclidean_geometry"],
    "solid_mechanics.section_modulus": ["mathematics.euclidean_geometry"],
    "solid_mechanics.radius_of_gyration": ["mathematics.euclidean_geometry"],
}

for nid in DELETE:
    nodes.pop(nid, None)
for nid, p in PATCH.items():
    if nid not in nodes:
        continue
    n = nodes[nid]
    if "provenance" in p: n["provenance"] = p["provenance"]
    if "quantity" in p: n["quantity"] = p["quantity"]
    if "law" in p: n["law"] = p["law"]
    if "requires" in p: n["requires"] = p["requires"]
    if "add_requires" in p: n["requires"] = n.get("requires", []) + p["add_requires"]
    if "points_to" in p: n["points_to"] = p["points_to"]
    if "drop_points" in p: n["points_to"] = [x for x in n.get("points_to", []) if x not in p["drop_points"]]
for nid, roots in ORPHAN_ROOT.items():
    if nid in nodes:
        nodes[nid]["points_to"] = roots

# --- integrity re-check ---
ids = set(nodes)
dangling = {nid: [p for p in n.get("points_to", []) if p not in ids] for nid, n in nodes.items()}
dangling = {k: v for k, v in dangling.items() if v}
def descends(nid, seen=None):
    seen = seen or set()
    if nid in seen: return False
    seen.add(nid)
    n = nodes.get(nid)
    if not n: return False
    if n["provenance"] == "fundamental": return True
    return any(descends(p, seen) for p in n.get("points_to", []) if p in ids)
orphans = [nid for nid, n in nodes.items() if n["provenance"] != "fundamental" and not descends(nid)]

# --- regenerate physics_archive.py ---
def dir_map(reqs):
    return {r["variable"]: (1 if r["direction"] == "+" else -1 if r["direction"] == "-" else 0) for r in reqs}
lines = ['"""Agent-built physics archive (corrected). %d nodes. Generated; do not hand-edit."""' % len(nodes),
         "from dataclasses import dataclass", "", "@dataclass", "class ArcNode:",
         "    id: str", "    quantity: str", "    law: str", "    provenance: str", "    level: str",
         "    domain: str", "    requires: dict", "    points_to: list", "", "ARCHIVE = {"]
for nid in sorted(nodes):
    n = nodes[nid]
    lines.append("    %r: ArcNode(%r, %r, %r, %r, %r, %r, %r, %r)," % (
        nid, nid, n["quantity"], n["law"], n["provenance"], n["level"], n["domain"],
        dir_map(n.get("requires", [])), n.get("points_to", [])))
lines += ["}", "", "BY_QUANTITY = {}", "for _n in ARCHIVE.values():",
          "    BY_QUANTITY.setdefault(_n.quantity, []).append(_n.id)"]
open(DEST, "w", encoding="utf-8").write("\n".join(lines))

print(f"CORRECTED archive: {len(nodes)} nodes (added {len(NEW)} roots, deleted {len(DELETE)} dup, "
      f"patched {len(PATCH)}, re-rooted {len(ORPHAN_ROOT)} orphans)")
print(f"  dangling pointers: {sum(len(v) for v in dangling.values())}")
print(f"  orphan nodes: {len(orphans)}  {orphans if orphans else ''}")
