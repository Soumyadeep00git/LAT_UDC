"""A SYSTEM is a network of SUBSYSTEMS. This is the spine of the whole design tool.

A Subsystem delivers a physical FUNCTION (a quantity, grounded to the physics library), REQUIRES
quantities from other subsystems and PROVIDES quantities to them — those provides/requires are the
EDGES, and the edges are the physical couplings (energy feeds propulsion; propulsion loads structure).
It carries design PARAMS and a MODEL that computes its state, and it may decompose into CHILDREN
(recursion: a subsystem is a system one level down).

Nothing in this file knows any physics. Physics enters only through each subsystem's `model` and through
grounding `function` to the library. Keep this file minimal — a field earns its place or it isn't here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Subsystem:
    name: str
    function: str                                   # physical quantity it delivers (grounds to library)
    requires: list = field(default_factory=list)    # quantities it consumes from the bus
    provides: list = field(default_factory=list)     # quantities it publishes to the bus
    params: dict = field(default_factory=dict)       # design parameters
    # a subsystem can be realized by several MECHANISMS; each maps to (model_fn, library_node_id).
    # swapping the active mechanism (within a radicality budget) is a physics-lensed design move.
    mechanisms: dict = field(default_factory=dict)   # {mechanism_name: (model_fn, node_id)}
    mechanism: Optional[str] = None                  # active mechanism
    physics_vars: list = field(default_factory=list)  # fingerprint vars the function exposes (grounding ctx)
    # per-subsystem SEARCH CONTROL (requirements flowdown): how far THIS subsystem may cross mechanisms
    # (0 = pinned to its current mechanism), and which performance terms it is RESPONSIBLE for optimizing.
    radicality_budget: int = 0                       # crossing leash for THIS subsystem
    owns: list = field(default_factory=list)          # performance term(s) this subsystem optimizes
    children: list = field(default_factory=list)      # sub-subsystems (recursion)
    state: dict = field(default_factory=dict)         # filled by the solver

    @property
    def model(self) -> Optional[Callable]:
        m = self.mechanisms.get(self.mechanism)
        return m[0] if m else None

    @property
    def node(self) -> Optional[str]:
        m = self.mechanisms.get(self.mechanism)
        return m[1] if m else None

    def leaves(self):
        """Flatten to the leaf subsystems that actually carry models (recursion)."""
        if not self.children:
            return [self]
        out = []
        for c in self.children:
            out.extend(c.leaves())
        return out


@dataclass
class System:
    name: str
    subsystems: list = field(default_factory=list)

    def by_name(self):
        return {s.name: s for s in self.subsystems}

    def edges(self):
        """The interface graph: list of (producer, consumer, quantity)."""
        producer = {}
        for s in self.subsystems:
            for q in s.provides:
                producer[q] = s.name
        out = []
        for s in self.subsystems:
            for q in s.requires:
                if q in producer and producer[q] != s.name:
                    out.append((producer[q], s.name, q))
        return out

    def describe(self):
        lines = [f"SYSTEM {self.name}"]
        for s in self.subsystems:
            lines.append(f"  [{s.name}] delivers '{s.function}'"
                         f"  requires {s.requires or '-'}  provides {s.provides or '-'}")
        lines.append("  couplings:")
        for a, b, q in self.edges():
            lines.append(f"    {a} --{q}--> {b}")
        return "\n".join(lines)
