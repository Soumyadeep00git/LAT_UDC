r"""OpenFOAM automation via WSL — drive a real solver from Python and parse the result back.

OpenFOAM v2412 (ESI) is installed in the WSL Ubuntu on this machine. This module:
  - translates a Windows case path to its /mnt WSL path,
  - sources the OpenFOAM environment and runs a list of applications (blockMesh, a solver, ...),
  - parses a result from the case.

It is the concrete `runner(case)->results` that plugs into fields.ExternalBackend, honouring the L3
field/BC contract. This file proves the PIPELINE end-to-end on a canonical case (lid-driven cavity,
icoFoam) — fast and deterministic. Mapping the rotor flow field to an actuator-disk simpleFoam case is
the next physics increment; the execution/plumbing below is unchanged by it.
"""
from __future__ import annotations

import os
import re
import subprocess

OF_BASHRC = "/usr/lib/openfoam/openfoam2412/etc/bashrc"


def win_to_wsl(path):
    path = os.path.abspath(path)
    drive, rest = os.path.splitdrive(path)
    return "/mnt/" + drive[0].lower() + rest.replace("\\", "/")


def run(case_dir, apps, timeout=300):
    """Run OpenFOAM apps in case_dir (Windows path) via WSL. Returns (ok, log)."""
    wsl_case = win_to_wsl(case_dir)
    cmds = f"source {OF_BASHRC} && cd '{wsl_case}' && " + \
           " && ".join(f"{a} > log.{a.split()[0]} 2>&1" for a in apps) + " && echo __OF_OK__"
    try:
        p = subprocess.run(["wsl.exe", "-e", "bash", "-lc", cmds],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    out = (p.stdout or "") + (p.stderr or "")
    return ("__OF_OK__" in out), out


# ------------------------------------------------------------------ a real, fast case: cavity (icoFoam)
_FILES = {
    "system/controlDict": """FoamFile
{ version 2.0; format ascii; class dictionary; object controlDict; }
application     icoFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         0.5;
deltaT          0.005;
writeControl    timeStep;
writeInterval   100;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
runTimeModifiable true;
""",
    "system/fvSchemes": """FoamFile
{ version 2.0; format ascii; class dictionary; object fvSchemes; }
ddtSchemes          { default Euler; }
gradSchemes         { default Gauss linear; }
divSchemes          { default none; div(phi,U) Gauss linear; }
laplacianSchemes    { default Gauss linear orthogonal; }
interpolationSchemes { default linear; }
snGradSchemes       { default orthogonal; }
""",
    "system/fvSolution": """FoamFile
{ version 2.0; format ascii; class dictionary; object fvSolution; }
solvers
{
    p     { solver PCG; preconditioner DIC; tolerance 1e-06; relTol 0.05; }
    pFinal { $p; relTol 0; }
    U     { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-05; relTol 0; }
}
PISO { nCorrectors 2; nNonOrthogonalCorrectors 0; pRefCell 0; pRefValue 0; }
""",
    "system/blockMeshDict": """FoamFile
{ version 2.0; format ascii; class dictionary; object blockMeshDict; }
scale 0.1;
vertices
(
    (0 0 0) (1 0 0) (1 1 0) (0 1 0)
    (0 0 0.1) (1 0 0.1) (1 1 0.1) (0 1 0.1)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (20 20 1) simpleGrading (1 1 1)
);
edges ( );
boundary
(
    movingWall   { type wall;  faces ( (3 7 6 2) ); }
    fixedWalls   { type wall;  faces ( (0 4 7 3) (2 6 5 1) (1 5 4 0) ); }
    frontAndBack { type empty; faces ( (0 3 2 1) (4 5 6 7) ); }
);
mergePatchPairs ( );
""",
    "constant/transportProperties": """FoamFile
{ version 2.0; format ascii; class dictionary; object transportProperties; }
nu 0.01;
""",
    "0/U": """FoamFile
{ version 2.0; format ascii; class volVectorField; object U; }
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField
{
    movingWall   { type fixedValue; value uniform (1 0 0); }
    fixedWalls   { type noSlip; }
    frontAndBack { type empty; }
}
""",
    "0/p": """FoamFile
{ version 2.0; format ascii; class volScalarField; object p; }
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    movingWall   { type zeroGradient; }
    fixedWalls   { type zeroGradient; }
    frontAndBack { type empty; }
}
""",
}


def write_cavity(case_dir):
    for rel, txt in _FILES.items():
        p = os.path.join(case_dir, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", newline="\n") as f:
            f.write("/*--------------------------------*- C++ -*----------------------------------*/\n" + txt)


def parse_max_U(case_dir):
    """Read the final time's U field and return its peak magnitude — proof the solver produced a field."""
    times = [d for d in os.listdir(case_dir)
             if re.fullmatch(r"\d+(\.\d+)?", d) and d != "0" and os.path.isdir(os.path.join(case_dir, d))]
    if not times:
        return None, None
    tdir = max(times, key=float)
    with open(os.path.join(case_dir, tdir, "U")) as f:
        txt = f.read()
    vecs = re.findall(r"\(([-\d.eE+ ]+)\)", txt.split("internalField")[-1])
    mags = []
    for v in vecs:
        parts = v.split()
        if len(parts) == 3:
            try:
                x, y, z = map(float, parts); mags.append((x*x + y*y + z*z) ** 0.5)
            except ValueError:
                pass
    return (tdir, max(mags) if mags else None)


# ================================================================== flow field: airframe drag (RANS)
# External aero over the generated STL (snappyHexMesh + simpleFoam + forceCoeffs) -> real parasitic drag.
_CFD = {
    "system/controlDict": """FoamFile
{ version 2.0; format ascii; class dictionary; object controlDict; }
application simpleFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime {ITERS};
deltaT 1; writeControl timeStep; writeInterval {ITERS}; purgeWrite 1;
writeFormat ascii; writePrecision 6; runTimeModifiable true;
functions
{
    forceCoeffs
    {
        type forceCoeffs; libs (forces); patches (body);
        rho rhoInf; rhoInf 1.225;
        magUInf {U}; lRef {LREF}; Aref {AREF};
        liftDir (0 0 1); dragDir (1 0 0); pitchAxis (0 1 0); CofR (0 0 0);
        writeControl timeStep; writeInterval 20;
    }
}
""",
    "system/fvSchemes": """FoamFile
{ version 2.0; format ascii; class dictionary; object fvSchemes; }
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes { default none; div(phi,U) bounded Gauss linearUpwind grad(U);
 div(phi,k) bounded Gauss upwind; div(phi,omega) bounded Gauss upwind;
 div((nuEff*dev2(T(grad(U))))) Gauss linear; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
""",
    "system/fvSolution": """FoamFile
{ version 2.0; format ascii; class dictionary; object fvSolution; }
solvers
{
    p { solver GAMG; smoother GaussSeidel; tolerance 1e-6; relTol 0.05; }
    "(U|k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-7; relTol 0.05; }
}
SIMPLE { nNonOrthogonalCorrectors 0; consistent yes; residualControl { p 1e-4; U 1e-4; } }
relaxationFactors { equations { U 0.9; k 0.7; omega 0.7; } }
""",
    "system/blockMeshDict": """FoamFile
{ version 2.0; format ascii; class dictionary; object blockMeshDict; }
scale 1;
vertices
(
    (-1.5 -1.2 -0.9) (4.0 -1.2 -0.9) (4.0 1.2 -0.9) (-1.5 1.2 -0.9)
    (-1.5 -1.2 0.9)  (4.0 -1.2 0.9)  (4.0 1.2 0.9)  (-1.5 1.2 0.9)
);
blocks ( hex (0 1 2 3 4 5 6 7) (55 24 18) simpleGrading (1 1 1) );
edges ( );
boundary
(
    freestream { type patch; faces ( (0 4 7 3) (1 2 6 5) (0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7) ); }
);
mergePatchPairs ( );
""",
    "system/snappyHexMeshDict": """FoamFile
{ version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }
castellatedMesh true; snap true; addLayers false;
geometry { body { type triSurfaceMesh; file "body.stl"; } }
castellatedMeshControls
{
    maxLocalCells 1000000; maxGlobalCells 2000000; minRefinementCells 10; maxLoadUnbalance 0.1;
    nCellsBetweenLevels 2; features ( );
    refinementSurfaces { body { level (2 2); } }
    resolveFeatureAngle 30; refinementRegions { }
    locationInMesh (3.5 1.0 0.7); allowFreeStandingZoneFaces true;
}
snapControls { nSmoothPatch 3; tolerance 2.0; nSolveIter 30; nRelaxIter 5; }
addLayersControls { relativeSizes true; layers { } expansionRatio 1.0; finalLayerThickness 0.3; minThickness 0.1; }
meshQualityControls { maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4; maxConcave 80;
 minVol 1e-13; minTetQuality 1e-9; minArea -1; minTwist 0.02; minDeterminant 0.001; minFaceWeight 0.02;
 minVolRatio 0.01; minTriangleTwist -1; nSmoothScale 4; errorReduction 0.75; }
mergeTolerance 1e-6;
""",
    "constant/transportProperties": """FoamFile
{ version 2.0; format ascii; class dictionary; object transportProperties; }
transportModel Newtonian; nu 1.5e-05;
""",
    "constant/turbulenceProperties": """FoamFile
{ version 2.0; format ascii; class dictionary; object turbulenceProperties; }
simulationType RAS;
RAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }
""",
    "0/U": """FoamFile
{ version 2.0; format ascii; class volVectorField; object U; }
dimensions [0 1 -1 0 0 0 0]; internalField uniform ({U} 0 0);
boundaryField { freestream { type freestream; freestreamValue uniform ({U} 0 0); }
 body { type noSlip; } }
""",
    "0/p": """FoamFile
{ version 2.0; format ascii; class volScalarField; object p; }
dimensions [0 2 -2 0 0 0 0]; internalField uniform 0;
boundaryField { freestream { type freestreamPressure; freestreamValue uniform 0; }
 body { type zeroGradient; } }
""",
    "0/k": """FoamFile
{ version 2.0; format ascii; class volScalarField; object k; }
dimensions [0 2 -2 0 0 0 0]; internalField uniform {K};
boundaryField { freestream { type inletOutlet; inletValue uniform {K}; value uniform {K}; }
 body { type kqRWallFunction; value uniform {K}; } }
""",
    "0/omega": """FoamFile
{ version 2.0; format ascii; class volScalarField; object omega; }
dimensions [0 0 -1 0 0 0 0]; internalField uniform {OMEGA};
boundaryField { freestream { type inletOutlet; inletValue uniform {OMEGA}; value uniform {OMEGA}; }
 body { type omegaWallFunction; value uniform {OMEGA}; } }
""",
    "0/nut": """FoamFile
{ version 2.0; format ascii; class volScalarField; object nut; }
dimensions [0 2 -1 0 0 0 0]; internalField uniform 0;
boundaryField { freestream { type calculated; value uniform 0; }
 body { type nutkWallFunction; value uniform 0; } }
""",
}


def flow_drag(stl_path, v, out_dir, aref=0.05, lref=0.5, iters=250, timeout=600):
    """Real RANS parasitic drag over the airframe STL. Returns {ok, drag_N, Cd, CdA, cells, reason}."""
    case = os.path.join(out_dir, "of_flow_case")
    tri = os.path.join(case, "constant", "triSurface")
    os.makedirs(tri, exist_ok=True)
    k = 1.5 * (0.05 * v) ** 2
    omega = k ** 0.5 / (0.09 ** 0.25 * 0.1)
    subs = {"{U}": f"{v:g}", "{ITERS}": str(iters), "{AREF}": f"{aref:g}", "{LREF}": f"{lref:g}",
            "{K}": f"{k:g}", "{OMEGA}": f"{omega:g}"}
    for rel, txt in _CFD.items():
        for a, b in subs.items():
            txt = txt.replace(a, b)
        p = os.path.join(case, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", newline="\n") as f:
            f.write("/*--------------------------------*- C++ -*----------------------------------*/\n" + txt)
    # STL is in mm from cadgen -> scale to metres into constant/triSurface/body.stl
    src = win_to_wsl(stl_path)
    dst = win_to_wsl(os.path.join(tri, "body.stl"))
    ok, log = run(case, [f"surfaceTransformPoints -scale '(0.001 0.001 0.001)' '{src}' '{dst}'",
                         "blockMesh", "snappyHexMesh -overwrite", "simpleFoam"], timeout=timeout)
    if not ok:
        tail = "\n".join(log.strip().splitlines()[-4:])
        return {"ok": False, "reason": f"solver chain failed ({tail[:160]})"}
    # parse forceCoeffs coefficient.dat for Cd
    cd = _parse_coeff(case, "Cd")
    if cd is None:
        return {"ok": False, "reason": "forceCoeffs produced no Cd"}
    cda = cd * aref
    drag = 0.5 * 1.225 * v * v * cda
    return {"ok": True, "Cd": round(cd, 4), "CdA": round(cda, 5), "drag_N": round(drag, 3),
            "cells": _grep_cells(case)}


def _parse_coeff(case, col):
    base = os.path.join(case, "postProcessing", "forceCoeffs")
    if not os.path.isdir(base):
        return None
    for root, _dirs, files in os.walk(base):
        for fn in files:
            if fn.endswith("coefficient.dat") or fn == "forceCoeffs.dat":
                header, last = None, None
                with open(os.path.join(root, fn)) as f:
                    for ln in f:
                        if ln.startswith("#"):
                            header = ln
                        elif ln.strip():
                            last = ln
                if header and last and col in header:
                    cols = header.lstrip("#").split()
                    try:
                        return float(last.split()[cols.index(col)])
                    except (ValueError, IndexError):
                        continue
    return None


def _grep_cells(case):
    log = os.path.join(case, "log.snappyHexMesh")
    if os.path.exists(log):
        with open(log, errors="ignore") as f:
            txt = f.read()
        m = re.findall(r"cells:\s*(\d+)", txt)
        if m:
            return int(m[-1])
    return None


if __name__ == "__main__":
    import tempfile
    case = os.path.join(tempfile.gettempdir(), "of_cavity_case")
    os.makedirs(case, exist_ok=True)
    write_cavity(case)
    print("case:", case, "\n  WSL path:", win_to_wsl(case))
    ok, log = run(case, ["blockMesh", "icoFoam"], timeout=180)
    print("  run ok:", ok)
    if ok:
        t, umax = parse_max_U(case)
        print(f"  solved to t={t}s, peak |U| = {umax:.4f} m/s  (expected ~1.0 = lid speed)")
        print("  END-TO-END: Python -> WSL -> OpenFOAM v2412 -> parsed result  [OK]")
    else:
        print("  --- last log lines ---")
        print("\n".join(log.strip().splitlines()[-15:]))
