r"""The complete SpecimenLab pipeline — one runnable loop over all layers.

    ENCODE:  I hardware (CAD)  ->  II architecture  ->  III physics fields  ->  IV objective
    DECODE:  IV objective  ->  V physics  ->  VI architecture  ->  VII new hardware (CAD)

It wires the real components end to end:
  L1  cadgen.generate   -> STEP/STL of the actual part            (hardware)
  L2  build_uav         -> system graph (mechanism)               (architecture)
  L3  fields.decompose  -> coupled field regions + backend        (physics)  [reduced | external CFD]
  L4  diagnose/mission  -> objective                              (objective)
  decode  cascade       -> gradient repair + physics/arch search  -> a NEW design
  re-encode  cadgen     -> STEP/STL of the NEW part
  (optional) openfoam_runner -> real CFD for a field out of validity, folded back into the objective

Output: the new design WITH its provenance (design <- architecture <- physics), the CAD artifacts at both
ends, and which fields were solved by the reduced model vs handed to OpenFOAM. Scope: multirotor UAV.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import diagnose
import fields
import cascade
import cadgen
try:
    import openfoam_runner
except Exception:
    openfoam_runner = None

METRICS = diagnose.METRICS


def _caps_line(caps, reqs):
    return "  ".join(f"{m}={caps[m]:.1f}/{reqs[m]:.0f}" for m in METRICS)


def run(cfg0, mission, use_cfd=False, out_dir=None, cfd_speed=18.0):
    out_dir = out_dir or HERE
    reqs = diagnose._reqs(mission)
    R = {"log": [], "artifacts": {}, "fields": {}}

    def log(s): R["log"].append(s)

    log("=" * 78)
    log("ENCODE  (hardware -> architecture -> physics -> objective)")
    # L1 hardware
    cad0 = cadgen.generate(cfg0, out_dir, "specimen_start")
    R["artifacts"]["start_step"] = cad0["step"]
    log(f"  I  hardware  : {os.path.basename(cad0['step'])}  span {cad0['span_mm']:.0f} mm  "
        f"vol {cad0['volume_mm3']/1000:.0f} cm^3")
    # L2 architecture + L3 physics fields
    regions0, _ = fields.decompose(cfg0)
    caps0 = diagnose.caps_of(cfg0)                     # normalized metric dict (a_max_g, v_max, ...)
    log(f"  II arch      : multirotor · mechanism=rotor")
    log(f"  III physics  : {len(regions0)} coupled fields  "
        + ", ".join(f"{r.field_type}[{r.backend().split()[0]}]" for r in regions0))
    log(f"  IV objective : {'MET' if all(caps0[m]>=reqs[m]-1e-6 for m in METRICS) else 'UNMET'}   "
        + _caps_line(caps0, reqs))

    log("")
    log("DECODE  (objective -> physics -> architecture -> new hardware)")
    result = cascade.cascade(cfg0, mission, allow_experimental=False)
    for layer, msg in result.log:
        if layer.startswith(("V", "VI", "VII", "=", "scope")):
            log(f"  {layer:12s} {msg}")
    cfg1, mech1 = result.cfg, result.mechanism

    # re-encode the resulting design as hardware + fields
    cad1 = cadgen.generate(cfg1, out_dir, "specimen_final")
    R["artifacts"]["final_step"] = cad1["step"]
    R["artifacts"]["final_stl"] = cad1["stl"]
    regions1, _ = fields.decompose(cfg1, mech1)
    caps1 = diagnose.caps_of(cfg1, mech1)
    R["fields"] = {r.field_type: {"backend": r.backend(), "node": r.physics_node,
                                  "validity": r.validity} for r in regions1}

    log("")
    log("RE-ENCODE  (the new design as hardware + physics)")
    log(f"  VII hardware : {os.path.basename(cad1['step'])}  span {cad1['span_mm']:.0f} mm")
    for r in regions1:
        tag = r.backend()
        log(f"       field {r.field_type:8s} -> {tag}" + (f"  ({'; '.join(r.validity)})" if r.validity else ""))

    # ---- optional: hand the flow field to OpenFOAM for a real drag number ----
    if use_cfd and openfoam_runner is not None:
        log("")
        log("EXTERNAL CFD  (flow field -> OpenFOAM v2412 via WSL)")
        try:
            cfd = openfoam_runner.flow_drag(cad1["stl"], cfd_speed, out_dir)
            R["cfd"] = cfd
            if cfd.get("ok"):
                import aero
                d_reduced = aero.drag(cfd_speed, int(cfg1["n_rotors"]), cfg1["L_arm"], cfg1["D_in"])
                delta = 100.0 * (cfd["drag_N"] - d_reduced) / d_reduced if d_reduced else 0.0
                R["cfd"]["reduced_drag_N"] = round(d_reduced, 3)
                log(f"  drag(body) @ {cfd_speed:.0f} m/s :  CFD {cfd['drag_N']:.2f} N   "
                    f"vs reduced-model {d_reduced:.2f} N   (diff {delta:+.0f}%)   [{cfd['cells']} cells, Cd={cfd['Cd']}]")
                log(f"  -> reduced model was off by {delta:+.0f}%; CFD is the trustworthy parasitic drag "
                    "for v_max / forward-flight power (RESULT below still shows reduced caps)")
            else:
                log(f"  CFD did not complete: {cfd.get('reason','?')} — reduced model retained (honest fallback)")
        except Exception as e:
            log(f"  CFD error: {type(e).__name__}: {e} — reduced model retained")

    log("")
    log("RESULT")
    met = result.met
    log(f"  design    : " + ", ".join(f"{k}={cfg1[k]:.1f}" for k in diagnose.PARAMS))
    log(f"  <- arch   : multirotor · {mech1}")
    log(f"  <- physics: " + ", ".join(f"{r.field_type}:{r.physics_node.split('.')[-1]}" for r in regions1))
    log(f"  objective : {'MET' if met else 'NOT MET within multirotor scope'}   {_caps_line(caps1, reqs)}")
    log(f"  CAD out   : {os.path.basename(cad1['step'])} , {os.path.basename(cad1['stl'])}")
    log("=" * 78)
    R["met"] = met
    R["cfg_final"] = cfg1
    R["mechanism"] = mech1
    R["caps_final"] = caps1
    return R


if __name__ == "__main__":
    cfg0 = dict(D_in=13, pitch_in=6, Kv=300, I_max=45, S=6, cap_mAh=5000,
                C_rate=60, L_arm=0.30, payload=0.6, n_rotors=4)
    mission = {"a_req": 6.0, "v_req": 12.0, "endur_req": 15.0}
    use_cfd = "--cfd" in sys.argv
    R = run(cfg0, mission, use_cfd=use_cfd)
    print("\n".join(R["log"]))
