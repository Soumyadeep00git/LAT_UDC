r"""ELEMENTS - physics folded onto the architecture.

A physics linkage has two halves (see the field layer):
  - CONNECTIVE (conservation): FREE from the architecture. Wire ports at nodes and the balance laws fall
    out - flows into a node sum to zero (Kirchhoff / continuity / force balance). Nobody writes these.
  - CONSTITUTIVE (the element's own law): the ONE bit of physics you must define. It lives on the ELEMENT
    TYPE, defined once, and every design that uses that element inherits it.

So a design is: pick element types, wire them. `Network.assemble()` emits a `field.Structure` whose
conservation linkages are generated from the wiring and whose constitutive linkages come from the types.
Then the ordinary field solver runs it. No separate physics tree to bridge, no physics retyped.

Convention (bond-graph across/through): every node carries an EFFORT (potential: voltage, pressure, ...);
every element carries a THROUGH flow from terminal a to b (current, volumetric flow, ...); across = e_a - e_b.
Conservation at a node: sum of oriented throughs = 0. That is the only thing the architecture asserts.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field as dcf
from typing import Callable

import field


@dataclass
class ElementType:
    name: str
    domain: str
    constitutive: Callable          # (across, through, params) -> residual (~O(1)); the DEFINED physics


@dataclass
class Element:
    name: str
    etype: ElementType
    a: str
    b: str
    params: dict = dcf(default_factory=dict)


class Network:
    """The architecture: nodes tied by two-terminal elements. Ground is the effort reference (e=0)."""

    def __init__(self, ground, effort_scale=1.0, flow_scale=1.0):
        self.ground = ground
        self.effort_scale = effort_scale
        self.flow_scale = flow_scale
        self.elements = []

    def add(self, name, etype, a, b, **params):
        self.elements.append(Element(name, etype, a, b, params))
        return self

    def nodes(self):
        seen = []
        for e in self.elements:
            for n in (e.a, e.b):
                if n not in seen:
                    seen.append(n)
        return seen

    def assemble(self):
        s = field.Structure()
        for n in self.nodes():
            s.add_param("e_" + n, scale=self.effort_scale)
        for e in self.elements:
            s.add_param("f_" + e.name, scale=self.flow_scale)
        knowns = {"e_" + self.ground: 0.0}

        # CONSTITUTIVE - one per element, pulled from its TYPE (the defined physics)
        for e in self.elements:
            def mk_const(e):
                return lambda a: e.etype.constitutive(a["e_" + e.a] - a["e_" + e.b], a["f_" + e.name], e.params)
            s.add_link("const_" + e.name, ["e_" + e.a, "e_" + e.b, "f_" + e.name],
                       mk_const(e), node="element:" + e.etype.name)

        # CONSERVATION - one per non-ground node, GENERATED FROM THE WIRING (never authored)
        n_cons = 0
        for n in self.nodes():
            if n == self.ground:
                continue
            inc = [(e, +1.0 if e.b == n else -1.0) for e in self.elements if e.a == n or e.b == n]

            def mk_kcl(inc):
                return lambda a: sum(sgn * a["f_" + e.name] for e, sgn in inc) / self.flow_scale
            s.add_link("kcl_" + n, ["f_" + e.name for e, _ in inc], mk_kcl(inc))
            n_cons += 1

        stats = {"conservation_from_architecture": n_cons, "constitutive_from_elements": len(self.elements),
                 "distinct_element_types": len({e.etype.name for e in self.elements})}
        return s, knowns, stats


# ---------------------------------------------------------------- the element library (each law defined ONCE)
# across = e_a - e_b ;  through = flow a->b
SOURCE = ElementType("effort_source", "generic",
                     lambda across, through, p: across / p["value"] - 1)           # sets across = value
RESISTANCE = ElementType("linear_resistance", "generic",
                         lambda across, through, p: across / (p["R"] * through) - 1)  # across = R * through
ORIFICE = ElementType("nonlinear_orifice", "fluid",
                      lambda across, through, p: through / (p["C"] * math.sqrt(max(across, 1e-12))) - 1)  # Q = C*sqrt(dP)
