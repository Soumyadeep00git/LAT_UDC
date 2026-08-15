"""Solve a System to a consistent state — a fixed point over a shared quantity BUS.

Each subsystem reads the quantities it REQUIRES off the bus, runs its model, and writes what it PROVIDES
back to the bus (plus its mass). The global coupling `total_mass` also lives on the bus. We sweep the
subsystems repeatedly (Gauss-Seidel), which naturally resolves cycles like the battery-sag loop
(energy needs current <- propulsion needs voltage <- energy), and update total_mass until it settles.

This is platform_solve GENERALIZED: the couplings are the graph's edges, read off the bus, not hardcoded.
"""
from __future__ import annotations


def solve(system, seed=None, iters=60, tol=1e-3, relax=0.5):
    """Sweep the LEAF subsystems over the bus (recursion: a parent's leaves are its children's leaves),
    then aggregate each parent's mass from its leaves. Nesting is transparent to the solve."""
    bus = {"total_mass": 4.0}
    if seed:
        bus.update(seed)
    leaves = [lf for s in system.subsystems for lf in s.leaves()]

    prev_mass = None
    for _ in range(iters):
        for s in leaves:
            inputs = {q: bus.get(q) for q in s.requires}
            inputs["total_mass"] = bus["total_mass"]
            st = s.model(s.params, inputs)
            s.state = st
            for q in s.provides:
                if q in st:
                    bus[q] = st[q]
        new_mass = sum(s.state.get("mass", 0.0) for s in leaves)
        bus["total_mass"] = relax * bus["total_mass"] + (1 - relax) * new_mass
        if prev_mass is not None and abs(bus["total_mass"] - prev_mass) < tol:
            bus["converged"] = True
            break
        prev_mass = bus["total_mass"]
    bus.setdefault("converged", False)

    for s in system.subsystems:                      # aggregate parent masses up the recursion
        if s.children:
            s.state = dict(s.state)
            s.state["mass"] = sum(lf.state.get("mass", 0.0) for lf in s.leaves())
    return bus
