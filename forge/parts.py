r"""(a) The hardware layer as PLACED PARTS with typed ports.

A Part is a physical object with a pose and a set of PORTS. A port is where the part exchanges a physical
quantity with another part, typed by energy DOMAIN and DIRECTION (out=produces, in=consumes). The ports
are what the bond-graph builder (bondgraph.py) matches to infer the system — nothing about "energy ->
propulsion -> structure" is written here; that topology is DISCOVERED from these ports.

Placement here is a parametric template (quad X); the principled version is a constraint/packing solve,
but the ports+poses are the substrate either way.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

IN2M = 0.0254

# energy domains
ELEC, MECH, FLUID, MASS = "electrical", "mechanical", "fluid", "mass"


@dataclass
class Port:
    domain: str
    direction: str          # "out" (produces) | "in" (consumes)
    quantities: list        # physical quantities exchanged on this port


@dataclass
class Part:
    name: str
    role: str               # source | propulsor | arm | frame | avionics | payload | environment
    ports: list = field(default_factory=list)
    pos: tuple = (0.0, 0.0, 0.0)
    params: dict = field(default_factory=dict)


def quad_parts(cfg):
    """The physical parts of the seeker quad, each with typed ports and a placed pose (m)."""
    n = int(cfg["n_rotors"])
    L = cfg["L_arm"]
    parts = [
        Part("battery", "source",
             [Port(ELEC, "out", ["bus_voltage", "i_burst_per_rotor", "usable_energy"]),
              Port(ELEC, "in", ["current"])],
             pos=(0.0, 0.0, -0.02)),
    ]
    for i in range(n):
        a = math.radians(45 + i * 360 / n)
        ex, ey = L * math.cos(a), L * math.sin(a)
        parts.append(Part(f"rotor{i+1}", "propulsor",
                          [Port(ELEC, "in", ["bus_voltage", "i_burst_per_rotor"]),
                           Port(ELEC, "out", ["current"]),
                           Port(MECH, "out", ["thrust"]),
                           Port(FLUID, "out", ["slipstream"])],
                          pos=(ex, ey, 0.02)))
        parts.append(Part(f"arm{i+1}", "arm",
                          [Port(MECH, "in", ["thrust"])],
                          pos=(ex/2, ey/2, 0.0)))
    parts.append(Part("frame", "frame", [Port(MECH, "in", ["thrust"])], pos=(0.0, 0.0, 0.0)))
    parts.append(Part("pixhawk", "avionics", [Port(ELEC, "in", ["bus_voltage"])], pos=(0.0, 0.0, 0.03)))
    parts.append(Part("seeker", "sensor",
                      [Port(ELEC, "in", ["bus_voltage"]),
                       Port("optical", "out", ["detection_range", "field_of_view_deg", "track_rate_hz"])],
                      pos=(0.12, 0.0, -0.05)))
    parts.append(Part("air", "environment", [Port(FLUID, "in", ["slipstream"])], pos=None))
    return parts


if __name__ == "__main__":
    cfg = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)
    ps = quad_parts(cfg)
    print(f"{len(ps)} parts:")
    for p in ps:
        outs = [q for pt in p.ports if pt.direction == "out" for q in pt.quantities]
        ins = [q for pt in p.ports if pt.direction == "in" for q in pt.quantities]
        print(f"  {p.name:9s} [{p.role:11s}] out={outs} in={ins}")
