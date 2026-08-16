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

    # --- EO/IR seeker (added when the seeker subsystem was introduced) ---
    "optics.angular_resolution": dict(
        quantity="angular_resolution",
        law="IFOV = pixel_pitch / focal_length — instantaneous field of view per pixel",
        provenance="derived", level="mid", domain="electro_optics",
        requires={"pixel_pitch": 1, "focal_length": -1},
        points_to=[]),
    "electro_optics.detection_range": dict(
        quantity="detection_range",
        law="R_det = target_size / (N_pixels_detect * IFOV) — Johnson detection criterion",
        provenance="empirical", level="high", domain="electro_optics",
        requires={"target_size": 1, "angular_resolution": -1, "pixels_for_detection": -1},
        points_to=["optics.angular_resolution"]),
    "electro_optics.field_of_view": dict(
        quantity="field_of_view",
        law="FOV = n_pixels * IFOV — angular coverage of the detector array",
        provenance="derived", level="mid", domain="electro_optics",
        requires={"n_pixels": 1, "angular_resolution": 1},
        points_to=["optics.angular_resolution"]),
    # the conserved budget behind the seeker wall: a fixed sensor resolves a fixed number of spots,
    # so resolution (detection range) and instantaneous coverage trade against each other. Adding a
    # TEMPORAL degree of freedom (scanning) buys coverage over time — this is the invariant V3 ascends to
    # in order to hint that the seeker is missing a motion DOF.
    "optics.space_bandwidth_product": dict(
        quantity="space_bandwidth_product",
        law="SBP = coverage_solid_angle / IFOV^2 = n_pixels (fixed) — resolution vs instantaneous coverage "
            "trade on a conserved budget (etendue); a temporal/scan DOF trades time for coverage.",
        provenance="fundamental", level="fundamental", domain="electro_optics",
        requires={"n_pixels": 1, "coverage_solid_angle": -1, "angular_resolution": 0},
        points_to=[]),
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
