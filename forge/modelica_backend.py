r"""TIME-DOMAIN backend via OpenModelica in WSL - drive a real DAE/ODE solver from Python.

This is the time-domain sibling of openfoam_runner.py. Where that module hands a steady field to
OpenFOAM, this one hands a small DYNAMIC system to OpenModelica and reads the trajectory back.

It is a thin ADAPTER, NOT a solver. We do NOT hand-roll an integrator: OpenModelica compiles the
Modelica model and integrates it with its mature DASSL/IDA stack. This module only:
  - emits a Modelica .mo model from a small dataclass description (states, params, equations),
  - writes an .mos driver script, runs `omc` in WSL (mirroring openfoam_runner.run),
  - parses the result CSV back into numpy arrays.

Kept minimal but general enough to express any 2nd-order (or n-state first-order) system with
parameters - which is all the dynamic missing-dimension diagnosis (dynamic_diagnosis.py) needs.

OpenModelica install (this machine, verified): the OSMC apt repo added in WSL Ubuntu 24.04,
`apt-get install openmodelica` -> omc 1.27.0. `wsl omc --version` confirms it.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field as dc_field

import numpy as np


def win_to_wsl(path):
    """Windows path -> /mnt WSL path (same helper as openfoam_runner)."""
    path = os.path.abspath(path)
    drive, rest = os.path.splitdrive(path)
    return "/mnt/" + drive[0].lower() + rest.replace("\\", "/")


@dataclass
class DynamicSystem:
    """A small continuous dynamic system, general enough for any 2nd-order plant.

    states    : {name: start_value}       - each becomes a state with der(name) in an equation.
    params    : {name: value}             - Modelica parameters (the tunable axes).
    equations : list of Modelica equation strings, e.g. "der(x) = v" or "der(v) = k*(r-x) - c*v".
    outputs   : variable names to record (defaults to the state names).
    """
    name: str
    states: dict = dc_field(default_factory=dict)
    params: dict = dc_field(default_factory=dict)
    equations: list = dc_field(default_factory=list)
    outputs: list = dc_field(default_factory=list)

    def model_text(self):
        lines = [f"model {self.name}"]
        for s, x0 in self.states.items():
            lines.append(f"  Real {s}(start={x0!r}, fixed=true);")
        for p, val in self.params.items():
            lines.append(f"  parameter Real {p} = {val!r};")
        lines.append("equation")
        for eq in self.equations:
            lines.append(f"  {eq};")
        lines.append(f"end {self.name};")
        return "\n".join(lines) + "\n"


@dataclass
class Trajectory:
    ok: bool
    t: np.ndarray = dc_field(default_factory=lambda: np.array([]))
    series: dict = dc_field(default_factory=dict)     # {var: np.ndarray}
    reason: str = ""

    def col(self, name):
        return self.series.get(name, np.array([]))


def simulate(sys, case_dir, stop_time=10.0, intervals=1000, tol=1e-6, timeout=180):
    """Emit sys as a Modelica model, simulate it in OpenModelica (WSL), return the Trajectory.

    Real integration is done by omc's DASSL/IDA - this function only writes files, runs omc, parses CSV.
    """
    os.makedirs(case_dir, exist_ok=True)
    outputs = sys.outputs or list(sys.states)
    vfilter = "|".join(outputs)
    wsl_dir = win_to_wsl(case_dir)

    with open(os.path.join(case_dir, f"{sys.name}.mo"), "w", newline="\n") as f:
        f.write(sys.model_text())

    mos = (
        f'cd("{wsl_dir}"); getErrorString();\n'
        f'loadFile("{sys.name}.mo"); getErrorString();\n'
        f'simulate({sys.name}, stopTime={stop_time}, numberOfIntervals={intervals}, '
        f'tolerance={tol}, outputFormat="csv", variableFilter="{vfilter}"); getErrorString();\n'
    )
    with open(os.path.join(case_dir, "run.mos"), "w", newline="\n") as f:
        f.write(mos)

    try:
        p = subprocess.run(["wsl.exe", "-e", "bash", "-lc", f"cd '{wsl_dir}' && omc run.mos"],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return Trajectory(False, reason="omc timeout")
    log = (p.stdout or "") + (p.stderr or "")
    if "The simulation finished successfully" not in log:
        tail = "\n".join(log.strip().splitlines()[-4:])
        return Trajectory(False, reason=f"omc did not finish: {tail[:200]}")

    csv_path = os.path.join(case_dir, f"{sys.name}_res.csv")
    if not os.path.exists(csv_path):
        return Trajectory(False, reason="result CSV not produced")
    return _parse_csv(csv_path)


def _parse_csv(path):
    with open(path) as f:
        header = f.readline().strip()
        cols = [c.strip().strip('"') for c in header.split(",")]
        rows = []
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append([float(v) for v in ln.split(",")])
            except ValueError:
                continue
    if not rows:
        return Trajectory(False, reason="empty CSV")
    arr = np.array(rows)
    series = {c: arr[:, i] for i, c in enumerate(cols)}
    t = series.pop("time", arr[:, 0])
    return Trajectory(True, t=t, series=series)


# ------------------------------------------------------------------ convenience: a 2nd-order plant
def second_order_plant(k, c, m=1.0, setpoint=1.0, name="Plant"):
    """Closed-loop 2nd-order position plant: m*x'' = k*(r - x) - c*x', released from rest at x=0.

    k = proportional stiffness/gain (the one available axis in the diagnosis).
    c = damping / rate feedback (the MISSING axis; c=0 leaves the response purely stiffness-shaped).
    DC steady state is x=r for any k>0, so overshoot and rise are the meaningful trajectory metrics.
    """
    return DynamicSystem(
        name=name,
        states={"x": 0.0, "v": 0.0},
        params={"k": float(k), "c": float(c), "m": float(m), "r": float(setpoint)},
        equations=["der(x) = v", "der(v) = (k*(r - x) - c*v)/m"],
        outputs=["x", "v"],
    )


if __name__ == "__main__":
    import tempfile
    case = os.path.join(tempfile.gettempdir(), "om_backend_smoke")
    sysd = second_order_plant(k=4.0, c=0.4)
    print("WSL case dir:", win_to_wsl(case))
    tr = simulate(sysd, case, stop_time=8.0, intervals=400)
    print("ok:", tr.ok, "reason:", tr.reason)
    if tr.ok:
        x = tr.col("x")
        print(f"  samples={len(tr.t)}  x(0)={x[0]:.3f}  x(end)={x[-1]:.3f}  max(x)={x.max():.3f}")
        print("  END-TO-END: Python -> WSL -> OpenModelica (omc) -> parsed trajectory  [OK]")
