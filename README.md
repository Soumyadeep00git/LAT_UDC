# LAT_UDC

**A physics-grounded generative design tool for UAVs.** Give it a *mission*; it resolves the *physics*,
hands you a *buildable design and its blade geometry*, tells you **why** a design fails and **what
dimension it's missing**, and honestly **flags what it cannot yet validate**. Real physics throughout — no
fitted proxy — with a validation gate on every number.

```
mission ─► encode ─► resolve (V1·V2·V3) ─► engagement metric ─► solve the FIELD ─► decode to GEOMETRY
   parts → architecture → physics                (interception)     (thrust field)     (blade chord/twist → STL)
                         └──────────── every step cross-checked against ground truth ───────────┘
```

> **Honest status.** This is a working research prototype. Most numbers are validated for *internal
> consistency* (against the project's own reduced models / analytic ideals), **not against experiment**.
> The aerodynamics is ideal momentum/blade-element (no profile drag or tip loss yet); the physics library
> is ~77% prose (a curated slice is executable); the engagement is point-mass. Every such limit is flagged
> in code and in §8. The bet is a tool that **knows what it doesn't know**.

---

## 1. Quick start (headless)

```bash
pip install -r requirements.txt            # core = numpy; matplotlib for reports/renders

# the whole physics layer, end to end (solve -> resolve -> diagnose):
python forge/physics_pipeline.py

# or from Python, via the stable API:
python - <<'PY'
import sys; sys.path.insert(0, "forge")
import api
out = api.run_pipeline()                    # default quad + interceptor mission
print(out["resolve"]["caps"], out["diagnose"]["verdict"])
PY
```

Every capability is also a one-line standalone demo: `python forge/<module>.py` (see the table in §4).

---

## 2. The idea — an hourglass, resolved and closed

A vehicle is modelled at four levels of abstraction; **encode** goes down to intent, **decode** regenerates
up from it. The objective is the narrow waist — the pure statement of what the mission needs.

| Layer | What it is | In code |
|------|------------|---------|
| **I Hardware** | placed parts with mass, geometry, typed ports | `parts.py`, `cadgen.py` |
| **II Architecture** | subsystems + couplings (a bond graph), *discovered from ports* | `bondgraph.py`, `system.py`, `uav.py` |
| **III Physics** | each subsystem = a field/law + boundary conditions | `fields.py`, `uav_seeker_pack.py`, `agent/library.py` |
| **IV Objective** | mission as functionals of the fields | `objectives.py`, `diagnose.py`, `engagement.py` |

Two disciplines run everywhere: **abstraction + pluggable backend** (a field is a fast reduced model *or*
an external solve), and a **validation gate** (nothing is trusted until it reproduces a ground truth).

---

## 3. The pipeline, end to end

1. **Parts → Architecture (Layer II).** Parts carry typed ports; `bondgraph.infer_system` clusters them
   into subsystems and *discovers* the couplings by port-matching (the `energy→propulsion→structure`
   topology is not written down). → `quadcopter_demo.py`
2. **Architecture → Physics (Layer III).** Each subsystem grounds to its domain law over its region;
   `bondgraph.to_fields` emits the fields with BCs from the bonds.
3. **Optimize — V1 / V2 / V3.**
   - **V1** tunes parameter *values* by null-space repair on the objective gradient (`diagnose.repair`).
   - **V2** rearranges *structure* (rotor count) wrapping V1 (`physics_adapt.adapt`).
   - **V3** abstracts the *function*: a diagnosis-only **conservation-wall detector** that names a
     *missing dimension* (`v3c.meta_requirements`), and **leashless** enumerates every mechanism the
     physics graph offers to break a wall, pricing each leap (`v3_leashless.py`).
4. **Resolve.** On a fixed topology, `resolve.resolve` returns the best design (max worst-case margin),
   the reachable envelope, and the binding wall. `uav_seeker_pack.solve_uav_seeker` is the UAV-seeker as a
   closed, linked, executable structure — solved and matched to the trusted model to 0.03%.
5. **Mission metric.** `engagement.max_interception` plays the resolved vehicle against a threat set
   (dumb targets: fixed / straight-line) → an interception fraction. `intercept_optimize` makes that
   fraction the objective the physics maximizes (co-design).
6. **Solve the FIELD.** `thrust_field.py` treats the induced-flow field as the unknown and optimizes the
   distribution that maximizes thrust (recovers the Betz optimum, validated to 1e-15).
7. **Decode to GEOMETRY.** `blade_design.py` inverts blade-element+momentum: target thrust → chord & twist,
   *iterating the geometry until forward-solved thrust hits the target* (0.16%), then lofts a definite STL.

---

## 4. Use it as independent submodules

Every function is importable and headless. Add `forge/` to `sys.path` (or `import api`).

| Capability | Module · callable | One-liner |
|---|---|---|
| Parts → architecture | `bondgraph.infer_system(parts, cfg)` | `sys,meta = infer_system(quad_parts(cfg), cfg)` |
| Architecture → fields | `bondgraph.to_fields(sys, bus, cap, meta)` | the Layer III physics fields |
| Capabilities of a design | `diagnose.caps_of(cfg)` | `{a_max_g, v_max, endurance_min, mass}` |
| **V1** tune values | `diagnose.repair(cfg, mission)` | `cfg2, met, exhausted, hist, info` |
| **V2** rearrange structure | `physics_adapt.adapt(cfg, mission)` | `best, candidates, rule` |
| **V3** missing dimension | `v3c.meta_requirements(cfg, mission)` | `verdict + confirmed/model-gap walls` |
| **V3** leashless frontier | `v3_leashless.alternatives(qty, node, radius)` | every mechanism, priced by radicality |
| Auto-fill ceiling | `autoderive.analyze(node)` | can units recover this law? |
| Generic field solver | `field.solve_field(struct, knowns)` | domain-agnostic (optics/kinematics/economics) |
| Physics on elements | `elements.Network(...).assemble()` | wiring → conservation for free |
| Executable law | `executable_law.Law(...)`, `.assemble(...)` | prose → runnable + closed dataflow |
| Resolve best design | `resolve.resolve(cfg, mission)` | best design + envelope + wall |
| UAV-seeker structure | `uav_seeker_pack.solve_uav_seeker(cfg)` | `sol, caps, laws` (matches uav.py) |
| Interception metric | `engagement.max_interception(caps, ...)` | fraction nullified over a threat set |
| Co-design for intercept | `intercept_optimize.search(pool)` | designs maximizing interception |
| Solve the thrust field | `thrust_field.solve_max_thrust_field(dA, P)` | the max-thrust induced-flow field |
| Blade from thrust | `blade_design.design_iterate(T, rpm, R)` | chord+twist iterated to the target thrust |
| Blade → shape | `blade_design.to_stl(geom, path)` | loft to a definite STL |
| Whole pipeline | `physics_pipeline.run(cfg, mission)` / `api.run_pipeline()` | solve → resolve → diagnose |

The **`forge/api.py`** front door re-exports all of the above (`python forge/api.py` lists them) and adds
`api.run_pipeline()` and `api.load_backends()` (optional CAD/CFD/FEA/autopilot/dynamics, imported on demand).

---

## 5. Backends — the multidisciplinary outputs (optional)

Real toolchain, auto-selected by validity envelope (reduced model until it leaves its limits, then external).

| Discipline | Backend | In code |
|-----------|---------|---------|
| **CAD** | CadQuery (OCCT) → STEP/STL | `cadgen.py` |
| **CFD** | OpenFOAM v2412 (WSL) → drag | `openfoam_runner.py` |
| **FEA** | CalculiX/gmsh + beam FE | `fea.py` |
| **Dynamics (time)** | OpenModelica (WSL) DAE/ODE | `modelica_backend.py`, `dynamic_diagnosis.py` |
| **Autopilot** | ArduPilot `.param` + official `.apj` | `ardupilot_gen.py` |
| **6-DOF FDM** | own FDM + SITL JSON bridge | `fdm.py`, `fdm_json.py` |
| **3D CAD app** | native VTK workspace | `forge/cad.py` (needs `vtk`) |

`system_build.py` / `validate_pipeline.py` assemble the full buildable package into `build_interceptor/`.

---

## 6. Dependencies

- **Core (required):** Python 3.x, **numpy**. That's the entire headless physics layer.
- **Reports/renders:** matplotlib.
- **Optional:** vtk (3D app); cadquery+deps (CAD); and the external toolchains OpenFOAM / CalculiX+gmsh /
  OpenModelica / ArduPilot (WSL). See `requirements.txt`. Missing backends degrade gracefully —
  `api.load_backends()` reports which are available rather than crashing.

---

## 7. Layout

```
LAT_UDC/
├── forge/                       the engine
│   ├── api.py                   ★ stable callable surface (import this)
│   ├── physics_pipeline.py      ★ whole pipeline: solve -> resolve -> diagnose
│   ├── parts.py, bondgraph.py   Layer I->II->III inference (hardware -> architecture -> physics)
│   ├── system.py, solve.py      the Subsystem/System spine + coupled fixed-point solver
│   ├── uav.py                   the quad as an explicit System (reduced physics models)
│   ├── diagnose.py              V1: Jacobian + null-space repair
│   ├── physics_adapt.py         V2: structure (rotor count) search wrapping V1
│   ├── v3c.py, v3_leashless.py  V3: missing-dimension diagnosis / leashless mechanism frontier
│   ├── autoderive.py            measured auto-fill ceiling of the library
│   ├── field.py                 generic domain-agnostic solver (params + linkages + structure)
│   ├── elements.py              physics-on-elements: wiring -> conservation for free
│   ├── executable_law.py        prose law -> runnable + closed dataflow
│   ├── uav_seeker_pack.py       UAV-seeker as a closed, linked, executable structure
│   ├── resolve.py               best design + reachable envelope + binding wall
│   ├── engagement.py            interception metric (point-mass pursuit, dumb targets)
│   ├── intercept_optimize.py    co-design: maximize interception
│   ├── thrust_field.py          SOLVE the induced-flow field for max thrust (Betz)
│   ├── blade_design.py          DECODE: thrust -> blade chord/twist -> STL (forward-validated)
│   ├── cadgen/openfoam_runner/fea/ardupilot_gen/fdm/modelica_backend.py   external backends
│   ├── cad.py, make_report.py   3D app / PDF report
│   └── *_demo.py, validate*.py  runnable demos + tests
├── physics/                     reduced physics (aero, battery, motor, prop, structure)
├── agent/                       physics library, grounding, radicality, vocabulary
├── examples/                    captured demo outputs (reference)
└── legacy/                      pre-forge experiments (kept for history)
```

---

## 8. Honest scope & limitations

Held to the project's own honesty rule:

- **Self-consistency, not reality.** Field solves and the blade validate against the project's reduced
  models / analytic ideals — internal consistency, not experiment. No external CFD/FEA is folded into this
  session's field solves yet.
- **Ideal aero.** `thrust_field`/`blade_design` are momentum + blade-element with no profile drag, tip
  loss, real airfoil polars, or compressibility → figure-of-merit is the ideal (FM=1). Real FM (<1) is the
  next fidelity and would flip the rotor pitch `MODEL_GAP` to solve-confirmed.
- **Library is ~77% prose.** A curated slice is executable; auto-generation is *proven not scalable*
  (~13% of dimensioned laws recoverable by units alone — `autoderive.py`). The rest is curation.
- **Delegated atoms.** BEMT thrust, battery, v_max are wrapped from pre-existing reduced models.
- **Engagement.** Point-mass proportional-navigation vs *dumb* targets (fixed / straight-line). The
  smart-evader differential game (scenario 3) is a separate, deferred inner policy optimizer.
- **Topology is fixed.** Generation ("what we need → what we can build") is deliberately not attempted.
- **Backends.** CFD = airframe drag (not rotor thrust); FEA solves a 1-D beam (3-D deck emitted); `.apj`
  is the official firmware (not compiled here); FDM↔SITL verified in loopback.

None of these are hidden; each is flagged where it applies. The muscles go around these bones.
