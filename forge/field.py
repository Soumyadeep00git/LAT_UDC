r"""THE FIELD LAYER - a domain-agnostic solver over PARAMS, LINKAGES, and STRUCTURE.

No mission. No platform. No embodiment. A problem is just:
  - PARAMS    : named quantities (optics IFOV, a crank angle, a market price - the engine does not care).
  - LINKAGES  : relations among params. Each is a residual r(assignment) -> 0. A linkage may be a physical
                LAW (immutable) or a DEMAND (a requirement we are imposing). It may carry a grounding node.
  - STRUCTURE : the graph of params tied by linkages.

The engine does four things, all generic (it never mentions a domain):
  1. SOLVE      drive every linkage residual to zero (Gauss-Newton over the unknowns) -> the field state.
  2. DOF        the null space of the linkage Jacobian = the degrees of freedom the structure leaves open.
  3. DIAGNOSE   if imposed DEMANDS make the field inconsistent while each demand is satisfiable alone,
                the structure is MISSING A DEGREE OF FREEDOM. Found by leaving demands out one at a time;
                the binding invariant is the LAW linkage on the path between the conflicting demands.
  4. RELAX      adding one free param (a new axis) turns an over-determined conflict into a solvable field.

This is the whole idea of the project's waist: solve in the field, hand the hardware to the engineers.
If it could only do one domain, that would be the tell. So field_demo.py runs it on optics, kinematics,
and economics with the same code.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field as dc_field
from typing import Callable

import numpy as np


@dataclass
class Param:
    name: str
    scale: float = 1.0          # rough magnitude, for finite-diff steps and seeds
    dim: str = ""               # optional units tag (annotation only)


@dataclass
class Linkage:
    name: str
    variables: list             # param names it relates
    residual: Callable          # (assignment: dict) -> float, ~O(1) (write in ratio form)
    kind: str = "law"           # "law" (immutable) | "demand" (an imposed requirement)
    node: str = ""              # optional grounding (a library node id)


@dataclass
class Structure:
    params: dict = dc_field(default_factory=dict)
    linkages: list = dc_field(default_factory=list)

    def add_param(self, name, scale=1.0, dim=""):
        self.params[name] = Param(name, scale, dim)
        return self

    def add_link(self, name, variables, residual, kind="law", node=""):
        self.linkages.append(Linkage(name, list(variables), residual, kind, node))
        return self

    def laws(self):
        return [L for L in self.linkages if L.kind == "law"]

    def demands(self):
        return [L for L in self.linkages if L.kind == "demand"]


# ---------------------------------------------------------------- numerics (generic, no domain)
def _residuals(links, assign):
    return np.array([L.residual(assign) for L in links], float)


def _jacobian(links, unknowns, assign, scales):
    n, m = len(links), len(unknowns)
    J = np.zeros((n, m))
    base = _residuals(links, assign)
    for j, u in enumerate(unknowns):
        h = 1e-6 * max(abs(assign[u]), scales[u])
        a2 = dict(assign); a2[u] = assign[u] + h
        J[:, j] = (_residuals(links, a2) - base) / h
    return J


@dataclass
class Solution:
    values: dict
    residual: float
    n_dof: int
    dof_basis: list           # each entry: {param: component} - a free direction in unknown space
    status: str               # "solved" | "underdetermined" | "inconsistent" | "trivial"
    unknowns: list


def solve_field(struct, knowns, links=None, seed=None, iters=200, tol=1e-9):
    """Gauss-Newton to drive all (given) linkage residuals to zero; report DOFs via the Jacobian null space."""
    links = struct.linkages if links is None else links
    knowns = dict(knowns)
    unknowns = [n for n in struct.params if n not in knowns]
    scales = {n: struct.params[n].scale for n in struct.params}
    active = [L for L in links if any(v in unknowns for v in L.variables)] or list(links)

    if not unknowns:
        r = float(np.linalg.norm(_residuals(active, knowns))) if active else 0.0
        return Solution(dict(knowns), r, 0, [], "trivial" if r < 1e-6 else "inconsistent", [])

    x = np.array([(seed or {}).get(n, scales[n]) for n in unknowns], float)

    def assign_of(xv):
        a = dict(knowns); a.update({n: v for n, v in zip(unknowns, xv)})
        return a

    for _ in range(iters):
        R = _residuals(active, assign_of(x))
        if np.linalg.norm(R) < tol:
            break
        J = _jacobian(active, unknowns, assign_of(x), scales)
        dx, *_ = np.linalg.lstsq(J, -R, rcond=None)
        step = 1.0
        # simple damping so nonlinear residuals don't overshoot
        for _ls in range(20):
            if np.linalg.norm(_residuals(active, assign_of(x + step * dx))) < np.linalg.norm(R):
                break
            step *= 0.5
        x = x + step * dx

    a = assign_of(x)
    R = _residuals(active, a)
    J = _jacobian(active, unknowns, a, scales)
    # rank / null space -> degrees of freedom. NONDIMENSIONALIZE first: column-scale J by each param's
    # magnitude so a 1e-4 variable and a 1e3 variable are weighed comparably (else rank is a scale artifact).
    scvec = np.array([scales[u] for u in unknowns], float)
    Jn = J * scvec if J.size else J
    s = np.linalg.svd(Jn, compute_uv=False) if Jn.size else np.array([])
    smax = s[0] if s.size else 0.0
    rank = int(np.sum(s > max(1e-12, 1e-6 * smax))) if s.size else 0
    n_dof = len(unknowns) - rank
    dof_basis = []
    if n_dof > 0 and Jn.size:
        _, _, Vt = np.linalg.svd(Jn)
        for row in Vt[rank:]:
            dof_basis.append({u: round(float(c), 3) for u, c in zip(unknowns, row) if abs(c) > 1e-3})
    resid = float(np.linalg.norm(R))
    if resid > 1e-4:
        status = "inconsistent"
    elif n_dof > 0:
        status = "underdetermined"
    else:
        status = "solved"
    return Solution(a, resid, n_dof, dof_basis, status, unknowns)


# ---------------------------------------------------------------- generic conflict diagnosis
def _path_laws(struct, a, b):
    """Law linkages on a path connecting param a to param b (params as nodes, laws as hyperedges)."""
    laws = struct.laws()
    adj = {}
    for L in laws:
        for u in L.variables:
            for v in L.variables:
                if u != v:
                    adj.setdefault(u, []).append((v, L))
    # BFS
    prev = {a: (None, None)}
    q = [a]
    while q:
        x = q.pop(0)
        if x == b:
            break
        for (y, L) in adj.get(x, []):
            if y not in prev:
                prev[y] = (x, L)
                q.append(y)
    if b not in prev:
        return []
    out, cur = [], b
    while prev[cur][0] is not None:
        out.append(prev[cur][1])
        cur = prev[cur][0]
    seen, uniq = set(), []
    for L in out:
        if L.name not in seen:
            seen.add(L.name)
            uniq.append(L)
    return uniq


def diagnose(struct, knowns, seed=None):
    """Domain-agnostic meta-diagnosis. Classify the field under its imposed DEMANDS."""
    laws, demands = struct.laws(), struct.demands()
    full = solve_field(struct, knowns, links=struct.linkages, seed=seed)
    if not demands:
        return {"status": full.status, "n_dof": full.n_dof, "dof_basis": full.dof_basis,
                "values": full.values, "residual": full.residual,
                "reading": "no demands imposed - this is the free field and its degrees of freedom"}
    if full.status in ("solved", "underdetermined", "trivial"):
        return {"status": "satisfiable", "n_dof": full.n_dof, "values": full.values,
                "reading": "the structure meets every demand (a value within its DOFs suffices)"}

    # inconsistent -> is each demand satisfiable ALONE (laws + that one demand)?
    alone = {}
    for d in demands:
        sub = [L for L in struct.linkages if L.kind == "law" or L is d]
        s = solve_field(struct, knowns, links=sub, seed=seed)
        alone[d.name] = s.status in ("solved", "underdetermined", "trivial")
    solo_ok = [d for d in demands if alone[d.name]]

    # which pair conflicts: each ok alone, inconsistent together
    conflict_pair, binding = None, []
    for da, db in itertools.combinations(solo_ok, 2):
        sub = [L for L in struct.linkages if L.kind == "law" or L in (da, db)]
        s = solve_field(struct, knowns, links=sub, seed=seed)
        if s.status == "inconsistent":
            conflict_pair = (da, db)
            va = next((v for v in da.variables), None)
            vb = next((v for v in db.variables), None)
            binding = _path_laws(struct, va, vb) if va and vb else []
            break

    if conflict_pair is None:
        return {"status": "over-constrained", "reading": "demands are jointly infeasible; no clean pair "
                "isolated - the field has too few degrees of freedom for the imposed set"}
    return {
        "status": "MISSING_DOF",
        "conflict": (conflict_pair[0].name, conflict_pair[1].name),
        "each_alone_ok": True,
        "binding_invariant": [{"linkage": L.name, "node": L.node} for L in binding],
        "reading": ("each demand is satisfiable alone but not together: the field is missing a degree of "
                    "freedom. The binding invariant is the law linkage coupling the two demands; relaxing it "
                    "requires ADDING AN AXIS (a new free param), not tuning an existing value."),
    }


def relax_with_new_dof(struct, knowns, new_param, inject, seed=None):
    """Show that ADDING ONE free param (a new axis) turns an over-determined conflict into a solvable field.
    `inject(struct)` mutates a copy's linkages to let `new_param` enter the binding law."""
    import copy
    s2 = copy.deepcopy(struct)
    s2.add_param(new_param, scale=1.0)
    inject(s2)
    return solve_field(s2, knowns, links=s2.linkages, seed=seed)
