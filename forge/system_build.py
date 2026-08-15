r"""Assemble the COMPLETE buildable package for a specific real vehicle:

    Quadcopter · gimballed seeker · electric powertrain · Pixhawk-class autopilot (ArduCopter)

Runs the pipeline to finalise the design, then emits the four deliverable classes into build_specimen/:
    hardware/   -> STEP + STL         (CadQuery, generated)
    cfd/        -> OpenFOAM case+mesh+results (OpenFOAM v2412 via WSL, solved)
    fea/        -> CalculiX deck + gmsh mesh + solved beam-FE result (generated + solved)
    ardupilot/  -> specimen.param (generated) + official arducopter.apj (downloaded) + manifest

Every artifact is tagged with its provenance (generated / solved / official-release). Nothing is faked.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

import diagnose
import cascade
import cadgen
import fea
import ardupilot_gen
import openfoam_runner as ofr
from uav import build_uav, capabilities, G
from solve import solve

OUT = os.path.join(HERE, "build_specimen")
BOARD = "CubeOrange"


def _tree(root):
    lines = []
    for dp, _dn, fn in os.walk(root):
        for f in sorted(fn):
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            lines.append(f"    {rel:34s} {os.path.getsize(p):>10,} B")
    return lines


def main(cfd_speed=18.0):
    os.makedirs(OUT, exist_ok=True)
    # --- the specific vehicle: seeker quad on electric power ---
    cfg0 = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
                C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)     # payload = seeker + gimbal
    mission = {"a_req": 3.0, "v_req": 18.0, "endur_req": 25.0}
    print("VEHICLE: quadcopter + seeker + electric + Pixhawk/ArduCopter")
    print(f"  starting design: {cfg0}")
    print(f"  mission: {mission}\n")

    # --- finalise the design through the pipeline decode ---
    res = cascade.cascade(cfg0, mission, allow_experimental=False)
    cfg = res.cfg
    caps = diagnose.caps_of(cfg, res.mechanism)
    sysm = build_uav(cfg, propulsion_mechanism=res.mechanism)
    cap = capabilities(sysm, solve(sysm, seed={"current": 0.0, "total_mass": 4.0}))
    per_rotor = cap["thrust"] / cfg["n_rotors"]
    maneuver_load = per_rotor * max(cap["TWR"], 1.0)          # worst-case arm tip load
    print(f"  final design : " + ", ".join(f"{k}={cfg[k]:.1f}" for k in diagnose.PARAMS))
    print(f"  capabilities : mass {cap['mass']:.2f} kg | TWR {cap['TWR']:.2f} | a_max {caps['a_max_g']:.2f} g | "
          f"v_max {caps['v_max']:.1f} m/s | endurance {caps['endurance_min']:.0f} min")
    print(f"  objective    : {'MET' if res.met else 'NOT MET'}\n")

    manifest = {"vehicle": "quad + seeker + electric + ArduCopter", "board": BOARD,
                "design": {k: round(cfg[k], 2) for k in diagnose.PARAMS},
                "capabilities": {"mass_kg": round(cap["mass"], 2), "TWR": round(cap["TWR"], 2),
                                 "a_max_g": round(caps["a_max_g"], 2), "v_max_ms": round(caps["v_max"], 1),
                                 "endurance_min": round(caps["endurance_min"], 1)},
                "artifacts": {}}

    # 1) HARDWARE (STL/STEP)
    print("[1/4] HARDWARE  (CadQuery -> STEP + STL)")
    hw = cadgen.generate_vehicle(cfg, os.path.join(OUT, "hardware"), "specimen")
    manifest["artifacts"]["hardware"] = {"provenance": "generated (CadQuery OCCT)",
                                         "span_mm": hw["span_mm"], "height_mm": hw["height_mm"],
                                         "files": ["specimen.step", "specimen.stl"]}
    print(f"      span {hw['span_mm']:.0f} mm, {hw['step_bytes']:,} B STEP\n")

    # 2) CFD (OpenFOAM)
    print("[2/4] CFD  (OpenFOAM v2412 via WSL -> case + mesh + results)")
    aref = (hw["height_mm"] * hw["span_mm"] * 0.25) / 1e6
    cfd = ofr.flow_drag(hw["stl"], cfd_speed, os.path.join(OUT, "cfd"),
                        aref=aref, lref=hw["span_mm"]/1000.0, iters=200, timeout=560)
    manifest["artifacts"]["cfd"] = {"provenance": "solved (OpenFOAM simpleFoam RANS)", **cfd,
                                    "speed_ms": cfd_speed}
    if cfd.get("ok"):
        print(f"      drag {cfd['drag_N']:.2f} N @ {cfd_speed:.0f} m/s, Cd {cfd['Cd']}, {cfd['cells']} cells\n")
    else:
        print(f"      CFD did not complete: {cfd.get('reason')}\n")

    # 3) FEA (CalculiX deck + gmsh mesh + solved beam FE)
    print("[3/4] FEA  (CalculiX deck + gmsh mesh + solved beam FE)")
    fe = fea.run(cfg, os.path.join(OUT, "fea"), thrust_per_rotor_N=maneuver_load)
    manifest["artifacts"]["fea"] = {"provenance": "deck+mesh generated; result solved (beam FE)",
                                    "max_stress_MPa": fe["max_bending_stress_MPa"],
                                    "safety_factor": fe["safety_factor"], "files": fe["files"]}
    print(f"      tip load {fe['load_tip_N']:.1f} N -> stress {fe['max_bending_stress_MPa']:.0f} MPa, "
          f"SF {fe['safety_factor']:.1f}\n")

    # 4) ARDUPILOT (.param generated + official .apj downloaded)
    print("[4/4] ARDUPILOT  (.param generated + official .apj)")
    cfg_ap = dict(cfg); cfg_ap["_TWR"] = cap["TWR"]
    pp, npar = ardupilot_gen.gen_param(cfg_ap, os.path.join(OUT, "ardupilot"), board=BOARD)
    fw = ardupilot_gen.fetch_firmware(os.path.join(OUT, "ardupilot"), board=BOARD)
    manifest["artifacts"]["ardupilot"] = {"param": {"provenance": "generated", "params": npar,
                                                    "file": "specimen.param"},
                                          "firmware": fw}
    print(f"      specimen.param ({npar} params) | firmware: "
          + (f"arducopter.apj {fw['bytes']:,} B (official {fw.get('git_identity','')})" if fw.get("ok")
             else f"NOT fetched ({fw.get('reason')})") + "\n")

    with open(os.path.join(OUT, "MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print("=" * 66)
    print("PACKAGE  build_specimen/")
    print("\n".join(_tree(OUT)))
    print("=" * 66)
    return manifest


if __name__ == "__main__":
    main()
