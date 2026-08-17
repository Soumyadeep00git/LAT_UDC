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

    # --- trade-invariants: conserved-budget conflicts that no VALUE (V1) or COUNT (V2) can resolve, only a
    #     new degree of freedom. Each names the two factors that trade, and the DOF that relaxes the budget.
    #     These are what the generic meta-requirement engine (forge/v3c.py) ascends to. ---

    # a FIXED-PITCH propeller peaks in efficiency at ONE advance ratio J*=V/(nD) ~ P/D. Hover (J->0) and
    # dash (J=V/(nD)) cannot both sit at the peak with a single geometric pitch: efficient operation at two
    # separated advance ratios is a conserved-budget conflict for one pitch. The relaxing DOF is pitch
    # actuation (variable / collective pitch) — a mechanical degree of freedom, decoupled from which
    # mechanism supplies it (swashplate | variable-pitch hub | tilt).
    "aerodynamics.propeller_advance_efficiency": dict(
        quantity="advance_ratio_efficiency",
        law="eta(J) peaks at J* ~ 0.8*(P/D) for a fixed pitch; simultaneous efficiency at J_hover->0 and "
            "J_dash=V/(nD) is infeasible for a single pitch. Relaxing DOF: variable/collective pitch.",
        provenance="model", level="high", domain="aerodynamics",
        requires={"advance_ratio": 1, "pitch_to_diameter": -1},
        points_to=["rotorcraft_bemt.rotor_thrust"]),

    # a SINGLE cell chemistry occupies ONE point on the Ragone frontier: specific energy (Wh/kg) trades
    # against specific power (W/kg). No one chemistry gives both high energy and high power. The relaxing
    # DOF is a SECOND energy domain (hybrid: energy cells || power cells / supercapacitor) that DECOUPLES
    # energy storage from power delivery — decoupled from which power source is chosen.
    "electrochemistry_batteries.ragone_tradeoff": dict(
        quantity="specific_energy_power_frontier",
        law="specific_power <= P_max(specific_energy): Li-ion energy cells ~250 Wh/kg @ ~750 W/kg; power "
            "cells ~150 Wh/kg @ ~6000 W/kg; supercap ~7 Wh/kg @ ~12000 W/kg. Relaxing DOF: a second energy "
            "domain (energy || power channel) decoupling energy from power.",
        provenance="empirical", level="high", domain="electrochemistry_batteries",
        requires={"specific_energy": 1, "specific_power": 1},
        points_to=["electrochemistry_batteries.pack_energy"]),
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
