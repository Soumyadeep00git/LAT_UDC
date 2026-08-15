"""The physics library as a GRAPH OF POINTING NODES.

Each node is a governing relation for one physical QUANTITY. It carries:
  - the law (human-readable, citable),
  - its PROVENANCE  (fundamental = a conservation law / field equation ; model = a specialization or
    convenience ; empirical = fitted to data),
  - points_to      : the lower-level nodes it rests on (prop -> actuator_disk + airfoil -> newton...),
  - requires       : the SENSITIVITY FINGERPRINT — which physical variables the quantity MUST respond
                     to, and in which direction (+1 grows, -1 shrinks). This is what a grounded code
                     model gets audited against: if the model ignores a required variable, the physics
                     says the model is wrong, and the agent raises that as a question.

This is the spine (6 nodes). A full library replicates the pattern; the mechanism is here.
"""
from dataclasses import dataclass, field


@dataclass
class Node:
    id: str
    quantity: str
    provenance: str            # fundamental | model | empirical
    law: str
    requires: dict             # {physical_variable: +1 / -1}   required sensitivity fingerprint
    points_to: list = field(default_factory=list)


NEWTON = Node(
    "newton2", "force", "fundamental",
    "F = dp/dt  (force is the time-rate of momentum)", {}, [])

ACTUATOR_DISK = Node(
    "actuator_disk", "thrust", "fundamental",
    "T = m_dot*Dv,  m_dot = rho*A*(v_i + V):  thrust is momentum flux, so it FALLS with forward airspeed V",
    {"rpm": +1, "diameter": +1, "rho": +1, "airspeed": -1}, ["newton2"])

AIRFOIL = Node(
    "airfoil", "section_force", "fundamental",
    "dL = 0.5*rho*W^2*c*Cl(alpha):  a blade element is an airfoil",
    {"aoa": +1, "chord": +1, "rho": +1}, ["newton2"])

PROPELLER = Node(
    "propeller", "thrust", "model",
    "a propeller SPECIALIZES the actuator disk: induced v_i from blade rotation (Omega*r), Dv set by pitch",
    {"rpm": +1, "diameter": +1, "rho": +1, "airspeed": -1, "pitch": +1}, ["actuator_disk", "airfoil"])

THERMO = Node(
    "thermo", "energy_density", "fundamental",
    "specific energy <= chemistry bond energy (no free energy)", {}, [])

SOM = Node(
    "som", "stress", "fundamental",
    "sigma = M/Z <= sigma_ult (material strength sets structure mass)",
    {"load": +1, "arm": +1, "section": -1}, ["newton2"])

GRAPH = {n.id: n for n in [NEWTON, ACTUATOR_DISK, AIRFOIL, PROPELLER, THERMO, SOM]}

# a physical QUANTITY -> the FUNDAMENTAL node that grounds it (its physics-required fingerprint).
# A code symbol is grounded to the quantity, then to this node — the specialization (propeller) is
# recorded too, so the agent sees "your prop is one realization of momentum flux".
GROUND_OF = {"thrust": "actuator_disk", "energy": "thermo", "stress": "som", "force": "newton2"}
SPECIALIZES = {"actuator_disk": "propeller"}   # fundamental node -> its drone-world specialization
