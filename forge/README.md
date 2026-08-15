# forge — the System-based design engine

A **System is a network of Subsystems.** That graph is the spine; every capability attaches to it.
Reuses the validated physics modules in `../physics` and the physics library + radicality in `../agent`.

## Files
| file | role |
|---|---|
| `system.py` | the spine: recursive `Subsystem` (function, requires/provides edges, params, mechanisms, children, state) + `System`. Zero physics. |
| `solve.py` | coupled fixed-point over a shared quantity **bus**; sweeps leaves, resolves cycles (battery sag), aggregates parent mass up the recursion. `platform_solve` generalized. |
| `uav.py` | the quad as an explicit graph: `energy → propulsion → structure(→ arm, frame) → payload`. Models wrap the physics modules. `capabilities()` → TWR/a_max/v_max. |
| `agent.py` | walks the graph: **grounds** each subsystem's function to the library (context-aware), lists **radicality** crossings, **optimizes** through the coupled solve — naive (params) and physics-lensed (mechanism swap within a radicality budget). |
| `validate.py` | foundation gate: system solve reproduces the hi-fi solver. |
| `sanity.py` | 20/20 invariant suite (gate, grounding, mechanism-node existence, recursion, convergence, swap). |

## Run
```
python validate.py     # foundation gate
python sanity.py       # full invariant suite (20/20)
python agent.py        # ground -> scope -> optimize an interceptor to a mission
```

## What holds (guaranteed + tested)
- **Foundation gate PASS** — the explicit graph reproduces `platform_solve` (mass exact, a_max/v_max within a few %).
- **Recursion** — `structure` decomposes into `{arm, frame}`, solved nested, mass aggregates; same machinery at every level.
- **Context-aware grounding** — each subsystem declares the physics variables its model exposes, so a polysemous quantity binds to the right mechanism (thrust→rotor, not jet). Exact-match, no fuzzy search.
- **Two optimization modes** — naive param tuning and physics-lensed mechanism swaps (rotor ↔ ducted-fan) within a radicality budget, both through the one coupled solve.
- **Every mechanism node is verified to exist in the library** (a `sanity.py` check).

## Scoped backlog (tracked, not loose)
The working engine is complete and tested; these are bounded curation/extension items with the
integrity guarantees above already in place:
1. **Broad library vocabulary canon.** The 1069-node library (built by 30 independent agents) has
   fragmented quantity names (~15 for "thrust"). The engine handles this via a small function→quantity
   canon + context grounding; a full canonical-vocabulary pass (an expert agent normalizing all ~500
   quantity names) is the production curation step. Structural integrity is guaranteed regardless
   (0 dangling, 0 orphans).
2. **22 physics-content corrections** flagged by the mega-library verify pass (law/sign/provenance
   refinements to individual nodes) — a curation queue; they do not affect the UAV subsystems' grounding.
3. **Engagement/mission objective.** The agent currently optimizes to a capability floor
   (a_max/v_max ≥ target). Wiring the 2-D engagement back in makes the objective win-rate vs a threat set.
4. **More subsystems / mechanisms** — a wing (fixed-wing crossing), a fuel-cell energy mechanism, motor
   ↔ ESC ↔ rotor decomposition of propulsion — each is a new node/edge on the same spine.
