"""THE ARCH-2 AGENT PIPELINE, staged exactly per the plan.

Runs end-to-end today. Where a deep function isn't built yet it is a clearly-marked PLACEHOLDER that
returns structured "pending" info, so the FLOW is visible now and each rung can be filled in later.

  1  naive_opt          optimize the given equation over the given parameters (pure math)
  2  intelligent_opt    after opt, QUESTION it:  Q1 bound on params?   Q2 bound on the function?
  3  on function-permit  do NOT naively rewrite the function; instead GET CONTEXT
  4  context pointer     point_to_physics: bind each variable/quantity to the physics library
  5  physics library     the archive (spine now; the agent-built physics_archive.py when it lands)
  6  perceive + design   define the entity via library attributes; separate MATH from PHYSICS; perceive
                         the flow (what happens? what physics? what constraints? how much omittable?);
                         once fully grounded -> ask scope / abstraction / boundary -> DESIGN (placeholder)

The MATH track (steps 1-2) and the PHYSICS track (steps 4-6) are deliberately separate: physics only
starts once objects are DEFINED against the library. Step 3 is the hinge between them.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "physics"))

from discrepancy import sensitivity
import library
import radicality
import generate

IN2M = 0.0254


# ------------------------------------------------------------------ the problem handed to the agent
@dataclass
class Problem:
    name: str
    objective: "callable"           # scalar to MAXIMIZE, objective(**params)
    params: dict                    # {name: [value, (lo, hi)]}
    user_models: dict               # {physical_quantity: model_fn}  the user's model of each quantity
    fixed: dict = field(default_factory=dict)   # non-optimized inputs the models need
    required_properties: frozenset = field(default_factory=frozenset)   # for the generation stage
    radius: int = 0                 # radicality budget for scope/design


@dataclass
class Trace:
    naive: dict = None
    permissions: dict = None
    context: dict = None
    perception: dict = None
    scope: dict = None
    design: dict = None


# ================================================================== 1. NAIVE OPT (pure math)
def naive_opt(prob: Problem) -> dict:
    """Coordinate hill-climb on the given objective within the given param box. No physics — just math."""
    vals = {k: v[0] for k, v in prob.params.items()}
    step = {k: (v[1][1] - v[1][0]) * 0.1 for k, v in prob.params.items()}
    def f(v):
        return prob.objective(**v, **prob.fixed)
    best = f(vals)
    for _ in range(60):
        improved = False
        for k, (lo, hi) in [(k, prob.params[k][1]) for k in prob.params]:
            for d in (+1, -1):
                trial = dict(vals); trial[k] = min(hi, max(lo, vals[k] + d * step[k]))
                if f(trial) > best:
                    vals, best, improved = trial, f(trial), True
        if not improved:
            for k in step: step[k] *= 0.5
    at_bound = {k: (abs(vals[k] - prob.params[k][1][0]) < 1e-6 or abs(vals[k] - prob.params[k][1][1]) < 1e-6)
                for k in prob.params}
    return {"argmax": vals, "value": best, "at_bound": at_bound}


# ================================================================== 2. INTELLIGENT OPT (question it)
def intelligent_opt(prob: Problem, naive: dict) -> dict:
    """After optimizing, raise the two bound questions and return permissions (a knob decides who answers;
    here we self-grant the function permission to demonstrate the downstream flow)."""
    pinned = [k for k, b in naive["at_bound"].items() if b]
    q1 = (f"Q1 (param bound): optimum pins {pinned} against the box edge — the global optimum may lie "
          f"outside. Extend the param scope?") if pinned else \
         "Q1 (param bound): optimum is interior; the box is not the binding limit."
    q2 = ("Q2 (function bound): the objective uses the user's models of "
          f"{list(prob.user_models)}. Is each the right description of the physics? May I re-derive them "
          f"from first principles (not naively swap them) if they disagree with the library?")
    # PLACEHOLDER for the purpose knob: for now, permission to interrogate the function is granted so the
    # physics track can run. A real run reads this from the user or an automated scope-extender.
    return {"q1": q1, "q2": q2,
            "permission_extend_params": bool(pinned),
            "permission_interrogate_function": True}


# ================================================================== 3+4. GET CONTEXT (namespace discipline)
def get_context(prob: Problem) -> dict:
    """Function permission granted -> do NOT rewrite naively. Classify every INPUT by the library
    vocabulary (physics vs math, exact match only), and ground every OUTPUT quantity to a node.
    Variables the library doesn't know are NOT searched — they are math params to be solved."""
    inputs = list(prob.params) + list(prob.fixed)
    variables = {v: library.classify(v) for v in inputs}
    physics_inputs = [v for v, c in variables.items() if c == "physics"]
    # disambiguate a polysemous quantity by which law shares the model's physics variables
    quantities = {q: library.ground_quantity(q, physics_inputs) for q in prob.user_models}
    return {"variables": variables, "quantities": quantities}


# ================================================================== 5. LIBRARY  (referenced in stage 4/6)
# The physics library is physics_graph (the 6-node spine) today; swap to the agent-built physics_archive
# once the workflow lands. The pipeline code does not change — only the library behind it grows.


# ================================================================== 6. PERCEIVE + (scope) + DESIGN
def perceive(prob: Problem, ctx: dict) -> dict:
    """Reason ONLY over library-known variables. For each grounded output quantity, check the model
    against the node's required fingerprint: a required physics variable that the model has is checked
    for sign; a required physics variable the model LACKS is a missing dependence; math params are noted
    but carry no physics claim. 'what physics / what must hold / what is violated / what is just math'."""
    base = dict(prob.fixed)
    for k, v in prob.params.items():
        base[k] = v[0]
    physics_vars = [v for v, c in ctx["variables"].items() if c == "physics"]
    math_vars = [v for v, c in ctx["variables"].items() if c == "math"]
    perception = {"physics_vars": physics_vars, "math_vars": math_vars,
                  "grounded": {}, "blind": [], "questions": []}

    for quantity, nid in ctx["quantities"].items():
        if nid is None:
            perception["blind"].append(quantity)                 # quantity not in library -> unknown
            continue
        n = library.node(nid)
        model = prob.user_models[quantity]
        viols = []
        for var, req in n.requires.items():
            if var in base:                                       # model carries this physics variable
                s = sensitivity(model, base, var)
                if s is None or abs(s) < 0.02:
                    viols.append(("insensitive", var, req, s))
                elif (s > 0) != (req > 0):
                    viols.append(("wrong_sign", var, req, s))
            else:                                                 # law needs it; model has no such input
                viols.append(("missing_input", var, req, None))
        perception["grounded"][quantity] = {"node": n.id, "law": n.law, "provenance": n.provenance,
                                            "requires": n.requires, "violations": viols}
        for kind, var, req, s in viols:
            d = "increase" if req > 0 else "decrease" if req < 0 else "be independent of"
            if kind == "missing_input":
                perception["questions"].append(
                    f"Q  '{quantity}' is grounded to [{n.id}] ({n.law}). That law requires it to {d} with "
                    f"'{var}', but your model has NO such input. Either the physics is being omitted, or an "
                    f"ungrounded math param IS this quantity under a non-library name — rename it to ground it.")
            elif kind == "insensitive":
                perception["questions"].append(
                    f"Q  '{quantity}' must {d} with '{var}' per [{n.id}], but your model is insensitive to it "
                    f"(sensitivity {s:+.3f}).")
            else:
                perception["questions"].append(
                    f"Q  '{quantity}' must {d} with '{var}' per [{n.id}], but your model moves it the opposite "
                    f"way (sensitivity {s:+.3f}).")
    perception["fully_connected"] = (not perception["blind"] and
                                     all(not g["violations"] for g in perception["grounded"].values()))
    return perception


def ask_scope(prob: Problem, perception: dict) -> dict:
    """Scope/boundary — reached only once the equation is fully connected to physics. For each grounded
    mechanism, enumerate the crossings the RADICALITY budget permits (what you may swap to, and how far)."""
    crossings = {}
    for quantity, g in perception["grounded"].items():
        node = g["node"]
        alts = radicality.alternatives(quantity, node, prob.radius)
        crossings[quantity] = [{"to": nid, "radicality": d,
                                "tier": radicality.swap_report(node, nid).get("tier", "")} for nid, d in alts]
    return {"radius": prob.radius,
            "mechanism": {q: g["node"] for q, g in perception["grounded"].items()},
            "allowed_crossings": crossings}


def design(prob: Problem, scope: dict) -> dict:
    """Inverse generation: required property-set -> minimum-cost cover (fusion allowed), bounded by the
    radicality budget. segregate -> correlate -> generate."""
    if not prob.required_properties:
        return {"pending": True, "note": "no required-property set supplied"}
    subset, mass = generate.generate(frozenset(prob.required_properties), prob.radius)
    return {"config": [s["name"] for s in subset], "parts": len(subset), "mass": round(mass, 2),
            "fused": [s["name"] for s in subset if len(s["provides"]) > 1]}


# ================================================================== driver
def run(prob: Problem, verbose=True):
    t = Trace()
    t.naive = naive_opt(prob)
    t.permissions = intelligent_opt(prob, t.naive)
    if t.permissions["permission_interrogate_function"]:
        t.context = get_context(prob)
        t.perception = perceive(prob, t.context)
        if t.perception["fully_connected"]:
            t.scope = ask_scope(prob, t.perception)
            t.design = design(prob, t.scope)
    if verbose:
        _report(prob, t)
    return t


def _report(prob, t):
    print("=" * 90)
    print(f"AGENT PIPELINE  ::  {prob.name}")
    print("=" * 90)
    print("\n[1] NAIVE OPT (math)")
    print(f"    argmax { {k: round(v, 2) for k, v in t.naive['argmax'].items()} }  value {t.naive['value']:.3g}")
    print("\n[2] INTELLIGENT OPT (question the optimum)")
    print("    " + t.permissions["q1"])
    print("    " + t.permissions["q2"])
    print(f"    permissions: extend_params={t.permissions['permission_extend_params']}  "
          f"interrogate_function={t.permissions['permission_interrogate_function']}")
    if t.context is None:
        print("\n[3-6] function interrogation NOT permitted -> stop at math."); return
    print("\n[3-4] GET CONTEXT  (namespace discipline: exact match, no fuzzy search)")
    for v, c in t.context["variables"].items():
        tag = "PHYSICS (grounded to library)" if c == "physics" else "math param (not in library -> solve, don't interpret)"
        print(f"    input '{v}'  ->  {tag}")
    for q, nid in t.context["quantities"].items():
        print(f"    output '{q}'  ->  " + (f"[{nid}]" if nid else "NOT IN LIBRARY (blind)"))
    print("\n[6] PERCEIVE  (reason only over library-known variables)")
    print(f"    physics variables: {t.perception['physics_vars']}")
    print(f"    math parameters  : {t.perception['math_vars']}  (optimized; no physics claim)")
    for q, g in t.perception["grounded"].items():
        status = "OK" if not g["violations"] else f"{len(g['violations'])} violation(s)"
        print(f"    '{q}' [{g['node']}] requires "
              f"{ {v: ('+' if d>0 else '-') for v, d in g['requires'].items()} }  -> {status}")
    for q in t.perception["questions"]:
        print("    " + q.replace("\n", "\n    "))
    if t.perception["blind"]:
        print(f"    blind spots (not in library): {t.perception['blind']}")
    print(f"\n    fully_connected = {t.perception['fully_connected']}")
    if t.scope:
        print("\n[SCOPE] radicality budget = %d — permitted crossings per mechanism:" % t.scope["radius"])
        for q, alts in t.scope["allowed_crossings"].items():
            print(f"    {q} (in hand: {t.scope['mechanism'][q]})")
            for a in alts[:5]:
                print(f"       -> {a['to']}  (d={a['radicality']})")
            if not alts:
                print("       -> none within budget (raise the radius to cross)")
        if t.design.get("config"):
            print(f"\n[DESIGN] segregate->correlate->generate: {t.design['parts']} parts, {t.design['mass']} kg")
            for c in t.design["config"]:
                print(f"    - {c}")
            if t.design["fused"]:
                print(f"    (fused, boundary crossed: {t.design['fused']})")
        else:
            print("\n[DESIGN] " + t.design.get("note", ""))
    else:
        print("\n[SCOPE/DESIGN] not reached — resolve the physics violations above first.")


# ------------------------------------------------------------------ demo problem: thrust, library names
if __name__ == "__main__":
    # inputs named in the LIBRARY vocabulary ground to physics; 'tuning_knob' is not in the library, so
    # it is treated as a pure math parameter. The model omits 'flight_velocity', which the grounded
    # thrust law requires -> the agent raises that as a missing physical dependence.
    def T_user(air_density, disk_area, induced_velocity, tuning_knob):
        return disk_area * induced_velocity ** 2 * tuning_knob / air_density   # WRONG: thrust falls with air density

    prob = Problem(
        name="FLAWED rotor_thrust model: omits climb_velocity, adds a non-library tuning_knob",
        objective=lambda air_density, disk_area, induced_velocity, tuning_knob:
            T_user(air_density, disk_area, induced_velocity, tuning_knob),
        params={"disk_area": [0.3, (0.1, 1.5)], "induced_velocity": [8.0, (2.0, 20.0)],
                "tuning_knob": [1.0, (0.5, 2.0)]},
        user_models={"thrust": T_user},
        fixed={"air_density": 1.225},
        required_properties=frozenset({"thrust", "energy_storage", "load_bearing"}), radius=8,
    )
    run(prob)

    # a CORRECTED model that obeys momentum theory -> fully connected -> reaches scope + design
    def T_correct(air_density, disk_area, induced_velocity, climb_velocity):
        return 2.0 * air_density * disk_area * induced_velocity * (induced_velocity + climb_velocity)

    print("\n\n" + "#" * 90)
    prob2 = Problem(
        name="CORRECTED rotor_thrust model: momentum theory with climb_velocity -> full arc to design",
        objective=lambda air_density, disk_area, induced_velocity, climb_velocity:
            T_correct(air_density, disk_area, induced_velocity, climb_velocity),
        params={"disk_area": [0.3, (0.1, 1.5)], "induced_velocity": [8.0, (2.0, 20.0)]},
        user_models={"thrust": T_correct},
        fixed={"air_density": 1.225, "climb_velocity": 15.0},
        required_properties=frozenset({"thrust", "energy_storage", "load_bearing"}), radius=8,
    )
    run(prob2)
