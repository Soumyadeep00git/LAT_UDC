"""Curated bindings that fill gaps found by cross-domain smoke tests. Kept SEPARATE from the generated
physics_archive.py (which stays generated) — library.py merges these at load. This is the workflow:
a smoke test finds a BLIND function -> add the missing law here -> coverage improves, reproducibly.

Each entry: id -> dict(quantity, law, provenance, level, domain, requires{var:+1/-1/0}, points_to[...]).
"""
PATCH = {
    # found blind by the DC-DC converter smoke test: energy stored in an inductor's field
    "circuit_theory.inductor_stored_energy": dict(
        quantity="inductor_energy",
        law="E = 1/2 L I^2 — energy stored in an inductor's magnetic field",
        provenance="derived", level="low", domain="circuit_theory",
        requires={"inductance": 1, "current": 1},
        points_to=["electromagnetism.magnetic_energy_density", "circuit_theory.inductance"]),
}

# CURATED SYNONYMS: natural engineering function-names -> the library's canonical quantity. Build-time,
# reviewable, exact — NOT runtime fuzzy matching. This is the cross-domain vocabulary bridge the smoke
# tests revealed the need for (a car engineer says 'tractive_force'; the library says 'force').
SYNONYMS = {
    "stored_energy": "pack_deliverable_energy",   # energy-storage function -> the battery pack-energy law
    "tractive_force": "force",          # a car's drive force is a Newtonian force
    "drag_force": "drag",               # fluid_dynamics.drag_force lives under quantity 'drag'
    "stress": "normal_stress",          # bare 'stress' -> the normal-stress law
    "wheel_torque": "torque",
}
