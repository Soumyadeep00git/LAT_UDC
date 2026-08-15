# LAT_UDC

**A physics-grounded generative design tool for UAVs.** You give it a *mission* (agility, speed,
endurance, payload); it produces a *buildable vehicle* — geometry, a subsystem architecture, a physics
model, and the flight-controller configuration — and it can tell you **why** a design fails and **what to
change**, using real physics instead of a fitted proxy.

It is not a parametric sizing spreadsheet. The design is expressed as a **network of physical subsystems**
solved to a coupled fixed point, grounded to a curated physics library, and improved by a **null-space
repair** on the objective gradient — escalating to a different mechanism only when the math proves the
current one is exhausted.

```
mission ─► [ optimize ] ─► design ⟵ architecture ⟵ physics ─► STEP · CFD · FEA · ArduPilot
                │                                                     │
                └────────────── real forge engine ────────────────────┘
```

---

## 1. The idea in one page

A vehicle is modelled at four levels of abstraction (an "hourglass"):

| Layer | What it is | Fidelity | In code |
|------|------------|----------|---------|
| **I Hardware** | placed parts with mass, geometry, ports | highest | `parts.py`, `cadgen.py` |
| **II Architecture** | subsystems + couplings (a bond graph) | high | `system.py`, `bondgraph.py`, `uav.py` |
| **III Physics** | each subsystem = a field/law + boundary conditions | mid | `fields.py`, `agent/library.py` |
| **IV Objective** | mission as functionals of the fields | lowest (most abstract) | `objectives.py`, `diagnose.py` |

**Encode** goes down (`hardware → architecture → physics → objective`): a concrete vehicle is abstracted
into what it *achieves*. **Decode** goes back up (`objective → physics → architecture → hardware`): from
the mission, regenerate a new vehicle. The objective is the bottleneck — the pure statement of intent.

The key discipline: **abstraction + pluggable backend**, used everywhere. A field is solved by a fast
*reduced* model or handed to an *external* solver (OpenFOAM/CalculiX); geometry is a *template* or a
*constraint solve*; the autopilot is an *abstract control spec* with an *ArduPilot* backend.

---

## 2. How the four encode transitions actually work

These used to be hardcoded; they are now **inferred**, and the inference is verified to reproduce the
hand-written baseline exactly (`python forge/prototype.py` → `PASS, rel err 0.0`).

1. **Place hardware** — parts carry typed *ports* (domain × direction × quantity) and a pose. (`parts.py`)
2. **System ← hardware** — cluster parts by role, count members (→ `n_rotors`), and **wire couplings by
   matching ports across parts**. This is a bond graph: the motor is a gyrator (elec→mech), the prop a
   transformer (mech→fluid). The `energy→propulsion→structure` topology is *discovered*, not written.
   (`bondgraph.infer_system`)
3. **Physics ← system** — each element grounds to its domain law in the physics library, over its placed
   region, with boundary conditions taken from the bonds. (`bondgraph.to_fields`, `agent/library.py`)
4. **Objective ↔ physics** — each requirement is a *functional* of the fields; energy terms are bond-graph
   balances (endurance = stored electrical energy ÷ flow dissipation). (`objectives.py`)

---

## 3. The optimizer (decode) — diagnose → repair → escalate

One unified mechanism, pure math, no menu of options (`diagnose.py`, `cascade.py`):

1. **Diagnose** — assemble the Jacobian `J = ∂(metrics)/∂(params)` by finite-differencing the *real*
   coupled solve. Rank the failing metric's levers; mark each movable/immovable (at a catalogue bound).
2. **Repair** — step the failing metric uphill **without breaking satisfied requirements**, by projecting
   the failing gradient onto the null space of the binding constraints:
   `P = I − Aᵀ(AAᵀ)⁺A`, `d = P·∇g_fail`. Naive optimization is the special case `A = {}` (`P = I`).
3. **Escalate** — only when `‖d‖ ≈ 0` (the null space collapses — provably no parameter can help) do we
   change the *mechanism* (rotor→ducted) or, out of scope, the *platform* (→ fixed wing, gated
   experimental). "The null space says *when*; the library says *what*."

Grounding, alternatives and assumption-relaxation live in `agent/` (`library.py`, `radicality.py`,
`assumptions.py`) over a curated physics archive (`agent/physics_archive.py`).

---

## 4. Backends — the multidisciplinary outputs

Everything below is real and runs on this machine's toolchain; `system_build.py` assembles the full
package for a specific vehicle (quad + seeker + electric + ArduPilot) into `build_specimen/`.

| Discipline | Backend | Output | Status |
|-----------|---------|--------|--------|
| **CAD** | CadQuery (OCCT) | `.step` + `.stl` | generated (`cadgen.py`) |
| **CFD** | OpenFOAM v2412 (WSL) | case + mesh + solved drag | `openfoam_runner.py` — snappyHexMesh off the STL + simpleFoam RANS |
| **FEA** | CalculiX deck + gmsh mesh + numpy beam FE | `.inp` + `.msh` + solved stress | `fea.py` |
| **Autopilot** | ArduPilot | `.param` (generated) + official `.apj` | `ardupilot_gen.py` |
| **Dynamics** | our own 6-DOF FDM | flyable in ArduPilot SITL | `fdm.py`, `fdm_json.py` |

The validity envelope auto-selects the backend: a field inside its reduced model's limits uses the fast
model; when it leaves them (tip Mach > 0.7, disk loading > 250 N/m²) it is dispatched to the external
solver.

**3D CAD app** — `python forge/cad.py` opens a native VTK workspace (feature tree, sliders, shaded model)
where `[d]` diagnoses, `[r]` repairs, `[g]` swaps to a ducted fan, `[e]` previews the wing escalation.

---

## 5. Layout

```
LAT_UDC/
├── forge/                  the design engine
│   ├── system.py           Subsystem/System spine (the network)
│   ├── solve.py            coupled fixed-point solver over a shared bus
│   ├── uav.py              the quad as an explicit System (physics models)
│   ├── parts.py            (a) hardware = placed parts + typed ports
│   ├── bondgraph.py        (b)(c) parts → system → fields, by inference
│   ├── objectives.py       (d) objective = functionals over fields
│   ├── prototype.py        end-to-end encode chain + baseline consistency check
│   ├── diagnose.py         Jacobian + null-space repair
│   ├── cascade.py          layered decode: repair → physics → architecture
│   ├── fields.py           L3 field schema + reduced/external backends
│   ├── cadgen.py           CAD backend (CadQuery)
│   ├── openfoam_runner.py  CFD backend (OpenFOAM via WSL)
│   ├── fea.py              FEA backend (CalculiX/gmsh + beam FE)
│   ├── ardupilot_gen.py    ArduPilot params + firmware
│   ├── fdm.py, fdm_json.py 6-DOF FDM + ArduPilot SITL JSON bridge
│   ├── system_build.py     assemble the full buildable package
│   ├── cad.py, ui.html     3D CAD app (VTK) / browser view
│   ├── nptyping.py         Py3.14 shim so CadQuery imports
│   └── sanity.py, smoke_test.py, test_novelty.py, validate.py   tests
├── physics/                reduced physics (aero, battery, motor, prop, structure)
├── agent/                  physics library, grounding, radicality, assumptions
└── legacy/                 pre-forge sizing experiments (kept for history)
```

---

## 6. Setup & running

**Core** (design engine, no external solvers): Python 3.14, `numpy`. Optional `vtk` for the 3D app.

```bash
python forge/prototype.py     # encode chain + consistency check (fast, PASS)
python forge/sanity.py        # foundation/invariant suite
python forge/cascade.py       # diagnose → repair → escalate demo
python forge/cad.py           # 3D CAD workspace (needs vtk)
```

**External backends** (as configured on the build machine):
- **CAD** — `pip install cadquery cadquery-ocp multimethod typish ezdxf casadi`; on Python 3.14 the local
  `forge/nptyping.py` shim + a one-line `hashCode` patch are applied automatically.
- **CFD** — OpenFOAM v2412 in WSL (`source /usr/lib/openfoam/openfoam2412/etc/bashrc`); driven over `/mnt`
  paths. `python forge/openfoam_runner.py` runs a cavity case as a smoke test.
- **FEA** — gmsh in WSL for meshing; CalculiX (`ccx`) optional (deck is emitted either way).
- **ArduPilot** — SITL builds natively in WSL (`./waf configure --board sitl && ./waf copter`); firmware
  `.apj` is the official release for the chosen board (downloaded, checksummed).

```bash
python forge/system_build.py  # full package -> build_specimen/ (STEP, CFD, FEA, .param, .apj)
```

Generated outputs (`build_specimen/`, OpenFOAM cases, STEP/STL, screenshots) are reproducible and are
**not** committed — see `.gitignore`.

---

## 7. Honest scope & limitations

This is a working research tool, not a certified design authority. Held to the project's own honesty rule,
the current boundaries are:

- **Multirotor scope.** The tool is a UAV/multirotor designer (mechanisms: rotor, ducted fan). The
  quad→fixed-wing escalation exists but is **gated experimental** (out of the validated envelope).
- **CFD** computes airframe **parasitic drag**, not rotor thrust (an actuator-line rotor case is future
  work). BEMT remains the thrust model.
- **FEA** solves a 1-D beam FE for results; the 3-D CalculiX deck is emitted but not solved here (`ccx`
  not installed).
- **CFD-in-loop** compares against the reduced model but does not yet *recompute* v_max/endurance from the
  CFD drag.
- **ArduPilot `.apj`** is the official firmware for the board (not compiled here — no ARM toolchain);
  the design-specific artifact is the generated `.param`.
- **FDM ↔ SITL** — the FDM and the SIM_JSON bridge are built and verified in loopback; wiring them to a
  *live* SITL flight (in-WSL, motor-map/sign tuning) is the remaining step.
- **Magnetic field** grounding uses a placeholder node (no motor-EM node in the library yet).

None of these are hidden; each is flagged in the code/output where it applies.
