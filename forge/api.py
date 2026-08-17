r"""forge.api — the stable, headless, callable surface of the tool.

One import gives you every core function, grouped by layer. Core is numpy-only (no external solvers);
the CAD/CFD/FEA/autopilot backends are optional and imported on demand (see load_backends()).

Usage (headless):
    import sys; sys.path.insert(0, "forge")      # or run from inside forge/
    import api
    out = api.run_pipeline(api.DEFAULT_CFG, api.DEFAULT_MISSION)   # whole tool
    caps = api.caps_of(api.DEFAULT_CFG)                            # a single submodule

Every function below is also runnable standalone as `python forge/<module>.py` for a demo.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "physics"), os.path.join(HERE, "..", "agent")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---- Layer II/III: hardware -> architecture -> physics ------------------------------------------
from parts import quad_parts                                           # noqa: E402
from bondgraph import infer_system, to_fields, describe_bonds          # noqa: E402
from uav import build_uav, capabilities                               # noqa: E402
from solve import solve                                                # noqa: E402

# ---- the generic FIELD solver (domain-agnostic: params + linkages + structure) ------------------
from field import Structure, Linkage, solve_field                     # noqa: E402
from field import diagnose as field_diagnose                          # noqa: E402
from field import relax_with_new_dof                                  # noqa: E402
from elements import Network, ElementType, SOURCE, RESISTANCE, ORIFICE  # noqa: E402
from executable_law import Law, assemble as assemble_laws             # noqa: E402

# ---- the OPTIMIZER: V1 (values) / V2 (structure) / V3 (abstraction, diagnosis-only) -------------
from diagnose import repair as v1_repair, caps_of, PARAMS, BOUNDS, METRICS  # noqa: E402
from physics_adapt import adapt as v2_adapt                           # noqa: E402
from v3c import meta_requirements as v3_meta_requirements             # noqa: E402
import autoderive                                                     # noqa: E402  library auto-fill ceiling
import v3_leashless                                                   # noqa: E402  unleashed mechanism frontier

# ---- physics RESOLUTION on a fixed topology -----------------------------------------------------
from uav_seeker_pack import solve_uav_seeker, etendue_gate            # noqa: E402
from resolve import resolve                                           # noqa: E402

# ---- MISSION: the engagement metric + co-design -------------------------------------------------
from engagement import simulate as engage, max_interception          # noqa: E402
import intercept_optimize                                            # noqa: E402

# ---- SOLVE THE FIELD + DECODE to geometry -------------------------------------------------------
from thrust_field import solve_max_thrust_field                       # noqa: E402
from thrust_field import thrust as field_thrust, power as field_power  # noqa: E402
from blade_design import design as blade_from_thrust                  # noqa: E402
from blade_design import design_iterate as blade_iterate, forward_bemt, to_stl as blade_to_stl  # noqa: E402

# ---- MISSION front door: a threat spec drives the whole pipeline --------------------------------
from intercept_mission import design_for_threat, report as intercept_report  # noqa: E402

# ---- the whole pipeline: solve -> resolve -> diagnose -------------------------------------------
import physics_pipeline                                               # noqa: E402


DEFAULT_CFG = dict(D_in=13, pitch_in=7, Kv=320, I_max=45, S=6, cap_mAh=6000, C_rate=25,
                   L_arm=0.30, payload=0.6, n_rotors=4, wh_per_kg=300.0,
                   focal_length_mm=38.0, pixel_pitch_um=3.0, n_pixels=1920, frame_rate_hz=60.0)
DEFAULT_MISSION = dict(a_req=5.0, v_req=26.0, endur_req=16.0, detect_range_m=2500.0, search_halfangle_deg=30.0)


def run_pipeline(cfg=None, mission=None):
    """The whole physics layer end to end: solve -> resolve -> diagnose. Returns a dict."""
    return physics_pipeline.run(cfg or DEFAULT_CFG, mission or DEFAULT_MISSION)


def load_backends():
    """Import the OPTIONAL external backends (CAD/CFD/FEA/autopilot/dynamics). Needs their toolchains."""
    import importlib
    mods = {}
    for name in ("cadgen", "openfoam_runner", "fea", "ardupilot_gen", "fdm", "modelica_backend"):
        try:
            mods[name] = importlib.import_module(name)
        except Exception as e:                                        # missing toolchain -> report, don't crash
            mods[name] = f"unavailable: {e.__class__.__name__}: {e}"
    return mods


__all__ = [
    "quad_parts", "infer_system", "to_fields", "describe_bonds", "build_uav", "capabilities", "solve",
    "Structure", "Linkage", "solve_field", "field_diagnose", "relax_with_new_dof",
    "Network", "ElementType", "SOURCE", "RESISTANCE", "ORIFICE", "Law", "assemble_laws",
    "v1_repair", "caps_of", "PARAMS", "BOUNDS", "METRICS", "v2_adapt", "v3_meta_requirements",
    "autoderive", "v3_leashless", "solve_uav_seeker", "etendue_gate", "resolve",
    "engage", "max_interception", "intercept_optimize", "design_for_threat", "intercept_report",
    "solve_max_thrust_field", "field_thrust", "field_power",
    "blade_from_thrust", "blade_iterate", "forward_bemt", "blade_to_stl",
    "run_pipeline", "load_backends", "DEFAULT_CFG", "DEFAULT_MISSION",
]


if __name__ == "__main__":
    print(f"forge.api  -  {len(__all__)} callables exposed. Core is numpy-only.\n")
    for name in __all__:
        obj = globals()[name]
        kind = "module" if type(obj).__name__ == "module" else ("fn" if callable(obj) else "data")
        print(f"  [{kind:6}] api.{name}")
    print("\nquick check: api.run_pipeline() runs solve->resolve->diagnose on the default quad + mission.")
