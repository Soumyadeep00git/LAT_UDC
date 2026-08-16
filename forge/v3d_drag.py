r"""V3d closed end-to-end for one law: a complete, LIBRARY-FREE drag law.

  FORM     <- dimensional kernel (units only, no library node): drag = C * rho * v^2 * A
  CONSTANT <- a resolved field (OpenFOAM CFD): run the flow, read the drag coefficient, C = Cd/2
  =>       a complete law assembled from first principles + a field solve. The physics library is never
           touched. This is the whole 'decouple the physics from the library' argument, proven on drag.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))

import dimanalysis
import cadgen
import openfoam_runner as ofr

RHO = 1.225


def run(v=18.0, out=None):
    out = out or HERE
    # 1) FORM from units alone
    form, _ = dimanalysis.derive("drag", ["density", "velocity", "area"])

    # 2) a body to solve (any geometry; here the generated airframe)
    cfg = dict(D_in=12, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=6000, C_rate=25,
               L_arm=0.30, payload=0.6, n_rotors=4)
    hw = cadgen.generate_vehicle(cfg, out, "v3d_body")
    aref = (hw["height_mm"] * hw["span_mm"] * 0.25) / 1e6

    # 3) CONSTANT from the resolved field (CFD)
    cfd = ofr.flow_drag(hw["stl"], v, out, aref=aref, lref=hw["span_mm"] / 1000.0, iters=200, timeout=520)
    if not cfd.get("ok"):
        return {"ok": False, "form": form, "reason": cfd.get("reason")}
    Cd = cfd["Cd"]
    C = Cd / 2.0                                    # drag = 1/2 Cd rho v^2 A  ==  C rho v^2 A
    return {"ok": True, "form": form, "Cd": Cd, "C": round(C, 4), "cells": cfd["cells"],
            "complete_law": f"drag = {C:.4f} * rho * v^2 * A", "v": v, "aref": round(aref, 4)}


if __name__ == "__main__":
    r = run()
    print("V3d — a complete, LIBRARY-FREE drag law\n")
    print(f"  [FORM]     from units only (no library): {r['form']}")
    if r["ok"]:
        print(f"  [CONSTANT] from a resolved CFD field ({r['cells']} cells): Cd = {r['Cd']}  ->  C = Cd/2 = {r['C']}")
        print(f"  [LAW]      {r['complete_law']}")
        print(f"\n  Assembled from dimensional analysis + a field solve. The physics library was never touched.")
        print(f"  (Honest: this needed a body + a converged CFD; C here is at one Reynolds number — a full")
        print(f"   law is C(Re), i.e. a sweep of solves. And the CFD itself rests on viscosity, a measured")
        print(f"   material constant.)")
    else:
        print(f"  CFD did not complete: {r.get('reason')}")
