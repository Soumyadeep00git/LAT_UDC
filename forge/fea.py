r"""FEA layer: the stress field of the arm as real FEA artifacts.

Produces:
  - arm.inp  : a complete CalculiX input deck (structured C3D8 hex beam, carbon, root fixed, tip thrust
               load) — runnable with `ccx` where installed.
  - arm.msh  : a gmsh volume mesh of the arm (gmsh is present in WSL) — a real mesh artifact.
  - arm_result.json : solved by a 2-node Euler-Bernoulli beam FE (numpy) — tip deflection, max bending
               stress, safety factor. Exact for a cantilever point load, and honest about being 1D.

No CalculiX solver is installed here, so the 3D deck is emitted (not solved); the 1D FE is solved. The
deck + mesh are the "FEA files"; the json is the solved result.
"""
from __future__ import annotations

import json
import math
import os
import subprocess

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
E_CARBON = 70e9          # Pa, quasi-isotropic CFRP laminate
SIGMA_ALLOW = 600e6      # Pa, conservative CFRP allowable
IN2M = 0.0254


def _section(arm_od_m, wall_m):
    ro = arm_od_m / 2
    ri = max(ro - wall_m, 1e-4)
    I = math.pi / 4 * (ro ** 4 - ri ** 4)
    A = math.pi * (ro ** 2 - ri ** 2)
    return I, A, ro


def beam_fe(P, L, EI, n=8):
    """2-node Euler-Bernoulli cantilever FE (dofs: v, theta). Returns (tip_defl, root_moment)."""
    le = L / n
    ndof = 2 * (n + 1)
    K = np.zeros((ndof, ndof))
    ke = EI / le ** 3 * np.array([[12, 6*le, -12, 6*le],
                                  [6*le, 4*le**2, -6*le, 2*le**2],
                                  [-12, -6*le, 12, -6*le],
                                  [6*le, 2*le**2, -6*le, 4*le**2]])
    for e in range(n):
        d = [2*e, 2*e+1, 2*e+2, 2*e+3]
        for i in range(4):
            for j in range(4):
                K[d[i], d[j]] += ke[i, j]
    F = np.zeros(ndof)
    F[2*n] = -P                                  # tip transverse load
    free = list(range(2, ndof))                  # clamp node 0: v0=theta0=0
    u = np.zeros(ndof)
    u[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
    tip_defl = abs(u[2*n])
    root_moment = P * L                          # statics
    return tip_defl, root_moment


def run(cfg, out_dir, thrust_per_rotor_N=None):
    os.makedirs(out_dir, exist_ok=True)
    L = cfg["L_arm"]
    arm_od = (6.0 + 0.6 * cfg["D_in"]) / 1000.0          # matches cadgen arm width, m
    wall = 0.0015
    I, A, c = _section(arm_od, wall)
    EI = E_CARBON * I
    # tip load = per-rotor thrust at the maneuver limit (fallback to a hover-ish estimate)
    P = thrust_per_rotor_N if thrust_per_rotor_N else 20.0
    tip_defl, M = beam_fe(P, L, EI)
    sigma_max = M * c / I
    sf = SIGMA_ALLOW / sigma_max if sigma_max > 0 else float("inf")
    result = {"load_tip_N": round(P, 2), "arm_len_m": round(L, 3),
              "arm_OD_mm": round(arm_od*1000, 2), "wall_mm": round(wall*1000, 2),
              "EI_Nm2": round(EI, 3), "tip_deflection_mm": round(tip_defl*1000, 3),
              "root_moment_Nm": round(M, 3), "max_bending_stress_MPa": round(sigma_max/1e6, 2),
              "allowable_MPa": SIGMA_ALLOW/1e6, "safety_factor": round(sf, 2),
              "method": "2-node Euler-Bernoulli beam FE (numpy), exact for cantilever point load"}
    with open(os.path.join(out_dir, "arm_result.json"), "w") as f:
        json.dump(result, f, indent=2)

    _write_ccx_deck(os.path.join(out_dir, "arm.inp"), L, arm_od, P)
    msh = _gmsh_mesh(out_dir, L, arm_od)
    result["files"] = {"deck": "arm.inp", "mesh": os.path.basename(msh) if msh else None,
                       "result": "arm_result.json"}
    return result


def _write_ccx_deck(path, L, od, P, nx=20, nt=4):
    """Structured C3D8 hex mesh of the arm (square approx of the tube) as a runnable CalculiX deck."""
    w = od
    xs = np.linspace(0, L, nx + 1)
    ys = np.linspace(-w/2, w/2, nt + 1)
    zs = np.linspace(-w/2, w/2, nt + 1)
    nid = {}
    nodes = []
    k = 1
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            for m, z in enumerate(zs):
                nid[(i, j, m)] = k
                nodes.append((k, x, y, z)); k += 1
    elems = []
    e = 1
    for i in range(nx):
        for j in range(nt):
            for m in range(nt):
                n = [nid[(i, j, m)], nid[(i+1, j, m)], nid[(i+1, j+1, m)], nid[(i, j+1, m)],
                     nid[(i, j, m+1)], nid[(i+1, j, m+1)], nid[(i+1, j+1, m+1)], nid[(i, j+1, m+1)]]
                elems.append((e, *n)); e += 1
    fixed = [nid[(0, j, m)] for j in range(nt+1) for m in range(nt+1)]
    tip = [nid[(nx, j, m)] for j in range(nt+1) for m in range(nt+1)]
    with open(path, "w", newline="\n") as f:
        f.write("** CalculiX deck — carbon arm cantilever, root fixed, tip thrust load\n*NODE\n")
        for (i, x, y, z) in nodes:
            f.write(f"{i}, {x:.6f}, {y:.6f}, {z:.6f}\n")
        f.write("*ELEMENT, TYPE=C3D8, ELSET=ARM\n")
        for row in elems:
            f.write(", ".join(str(v) for v in row) + "\n")
        f.write("*NSET, NSET=FIXED\n" + ",\n".join(str(v) for v in fixed) + "\n")
        f.write("*NSET, NSET=TIP\n" + ",\n".join(str(v) for v in tip) + "\n")
        f.write("*MATERIAL, NAME=CFRP\n*ELASTIC\n70000.0, 0.3\n")
        f.write("*SOLID SECTION, ELSET=ARM, MATERIAL=CFRP\n")
        f.write("*STEP\n*STATIC\n*BOUNDARY\nFIXED, 1, 3, 0.0\n")
        f.write(f"*CLOAD\nTIP, 3, {-P/len(tip):.4f}\n")
        f.write("*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n")


def _gmsh_mesh(out_dir, L, od):
    """Use gmsh (WSL) to make a real volume mesh of the arm. Returns msh path or None."""
    geo = os.path.join(out_dir, "arm.geo")
    with open(geo, "w", newline="\n") as f:
        f.write(f"SetFactory(\"OpenCASCADE\");\nBox(1) = {{0,{-od/2},{-od/2}, {L},{od},{od}}};\n"
                f"MeshSize{{:}} = {od/2};\nPhysical Volume(\"arm\") = {{1}};\n")
    try:
        import openfoam_runner as ofr
        wgeo = ofr.win_to_wsl(geo)
        wmsh = ofr.win_to_wsl(os.path.join(out_dir, "arm.msh"))
        p = subprocess.run(["wsl.exe", "-e", "bash", "-lc",
                            f"gmsh '{wgeo}' -3 -o '{wmsh}' -format msh2 2>&1 | tail -2"],
                           capture_output=True, text=True, timeout=120)
        msh = os.path.join(out_dir, "arm.msh")
        return msh if os.path.exists(msh) else None
    except Exception:
        return None


if __name__ == "__main__":
    cfg = dict(D_in=15, pitch_in=7, Kv=340, I_max=45, S=6, cap_mAh=5000, C_rate=60, L_arm=0.30,
               payload=0.6, n_rotors=4)
    r = run(cfg, os.path.join(HERE, "build_specimen", "fea"), thrust_per_rotor_N=25.0)
    print(json.dumps(r, indent=2))
