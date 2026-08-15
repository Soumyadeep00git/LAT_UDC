"""THE canonical vocabulary — an enforced coding standard.

Every physical quantity is named PLAINLY in its canonical form. One rule, canonical(), replaces the
scattered synonym patches: it maps any variant to its plain name, so a rotor's thrust, a jet's 'net
thrust', and an actuator disk's thrust all resolve to `thrust`. Applied uniformly to the library index
and to subsystem functions, it makes independently-authored artifacts line up — the fragmentation problem
dissolves instead of being bailed out pair by pair. New code and new agent swarms MUST use CANONICAL names;
`lint()` flags anything that isn't plain.
"""
from __future__ import annotations

CANONICAL = {
    # mechanics
    "force", "thrust", "drag", "lift", "torque", "power", "energy", "momentum", "impulse",
    "pressure", "mass", "velocity", "acceleration", "angular_velocity", "friction",
    # structures / materials
    "stress", "bending_stress", "strain", "deflection", "moment_of_inertia", "fracture_toughness",
    # thermo / heat / fluids
    "temperature", "heat", "entropy", "energy_density", "thermal_resistance", "efficiency",
    "mass_flow_rate", "speed_of_sound",
    # electrical
    "voltage", "current", "resistance", "capacitance", "inductance", "inductor_energy",
    "magnetic_energy", "switching_loss", "conduction_loss", "back_emf",
    # energy storage
    "stored_energy", "specific_energy",
    # mission-level capabilities
    "endurance", "range", "a_max", "v_max",
}

# variant (normalized) -> canonical plain name. Grows as new variants appear; the LINT keeps it honest.
ALIASES = {
    "rotor_thrust": "thrust", "net_thrust": "thrust", "actuator_disk_thrust": "thrust",
    "blade_element_thrust": "thrust", "momentum_thrust_component": "thrust", "momentum_thrust": "thrust",
    "pressure_thrust_component": "thrust", "specific_thrust": "thrust", "required_thrust": "thrust",
    "tractive_force": "force", "drive_force": "force",
    "drag_force": "drag", "aerodynamic_drag": "drag", "total_drag": "drag",
    "normal_stress": "stress", "axial_stress": "stress", "cauchy_stress_tensor": "stress",
    "pack_deliverable_energy": "stored_energy", "cell_energy": "stored_energy", "pack_energy": "stored_energy",
    "wheel_torque": "torque", "electromagnetic_torque": "torque",
    "load_bearing": "stress", "payload_mass": "mass",
}


def _norm(s):
    return str(s).strip().lower().replace(" ", "_").replace("-", "_")


def canonical(name):
    """The plain canonical name for any quantity string."""
    n = _norm(name)
    return ALIASES.get(n, n)


def is_canonical(name):
    """True iff `name` is ALREADY written in its plain canonical form (the enforced standard)."""
    return _norm(name) == canonical(name) and canonical(name) in CANONICAL


def lint(names):
    """Return [(name, suggested_canonical)] for every name that violates the standard."""
    out = []
    for x in names:
        if not is_canonical(x):
            c = canonical(x)
            out.append((x, c if c in CANONICAL else "?"))
    return out
