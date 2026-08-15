r"""CLI-CAD automation: cfg -> a parametric multirotor solid -> STEP + STL, via CadQuery (OCCT kernel).

This is real B-rep CAD (not a mesh): frame plates, arm booms, motor cans, prop hubs+blades, battery — all
sized from the same design vector the solver uses. STEP feeds downstream CAD/CAM; STL feeds meshing (e.g.
snappyHexMesh for the OpenFOAM flow case). Runs headless, no GUI.

Python 3.14 notes: needs the local `nptyping` shim (annotation-only) and a `hashCode` patch because
cadquery 2.3 predates OCCT 7.9 (which removed HashCode). Both are applied here at import.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                       # local nptyping shim first

import cadquery as cq                           # noqa: E402
import cadquery.occ_impl.shapes as _S           # noqa: E402
_S.Shape.hashCode = lambda self: hash(self.wrapped)   # OCCT 7.9 removed HashCode(); use native hash

MM = 1000.0
IN2MM = 25.4

DEFAULT_CFG = dict(D_in=13, pitch_in=6, Kv=300, I_max=45, S=6, cap_mAh=5000,
                   C_rate=60, L_arm=0.30, payload=0.6, n_rotors=4)


def _rot(wp, ang_deg):
    return wp.rotate((0, 0, 0), (0, 0, 1), ang_deg)


def build_cad(cfg):
    """Return a CadQuery solid (compound) of the multirotor, dimensions in millimetres."""
    n = int(cfg["n_rotors"])
    R = cfg["D_in"] * IN2MM / 2.0
    L = cfg["L_arm"] * MM
    stator_d = 20.0 + 0.35 * cfg["I_max"]
    motor_h = 8.0 + 0.25 * cfg["I_max"]
    arm_w = 6.0 + 0.6 * cfg["D_in"]
    fr = max(45.0, 0.28 * L)

    z_arm = 10.0
    z_motor = z_arm + motor_h / 2
    z_prop = z_arm + motor_h + 6.0

    # central frame: two plates
    model = cq.Workplane("XY").box(2 * fr, 2 * fr, 4).translate((0, 0, z_arm + 12))
    model = model.union(cq.Workplane("XY").box(2 * fr, 2 * fr, 4).translate((0, 0, z_arm - 4)))

    # battery under the frame, sized by pack energy
    packWh = cfg["S"] * 3.7 * cfg["cap_mAh"] / 1000.0
    vol_mm3 = packWh / 250.0 * 1e6                     # ~250 Wh/L
    bx = (vol_mm3) ** (1 / 3) * 1.6
    by = bx * 0.55
    bz = max(20.0, vol_mm3 / max(bx * by, 1e-6))
    model = model.union(cq.Workplane("XY").box(bx, by, bz).translate((0, 0, z_arm - 6 - bz / 2)))

    for i in range(n):
        ang = 45 + i * 360 / n
        # arm boom (centered at L/2 along +X, then rotated)
        arm = cq.Workplane("XY").box(L, arm_w, arm_w).translate((L / 2, 0, z_arm))
        model = model.union(_rot(arm, ang))
        ex = L * math.cos(math.radians(ang))
        ey = L * math.sin(math.radians(ang))
        # motor can
        model = model.union(cq.Workplane("XY").cylinder(motor_h, stator_d / 2).translate((ex, ey, z_motor)))
        # prop: hub + 2 blades
        model = model.union(cq.Workplane("XY").cylinder(10, 7).translate((ex, ey, z_prop)))
        for b in (0, 180):
            blade = cq.Workplane("XY").box(R, R * 0.16 + 6, 3).translate((R / 2, 0, z_prop))
            blade = blade.rotate((0, 0, z_prop), (0, 0, 1), b).translate((ex, ey, 0))
            model = model.union(blade)
    return model


def generate(cfg=None, out_dir=None, name="specimen"):
    cfg = cfg or DEFAULT_CFG
    out_dir = out_dir or HERE
    os.makedirs(out_dir, exist_ok=True)
    model = build_cad(cfg)
    step = os.path.join(out_dir, f"{name}.step")
    stl = os.path.join(out_dir, f"{name}.stl")
    cq.exporters.export(model, step)
    cq.exporters.export(model, stl)
    bb = model.val().BoundingBox()
    return {"step": step, "stl": stl,
            "span_mm": round(max(bb.xlen, bb.ylen), 1),
            "height_mm": round(bb.zlen, 1),
            "volume_mm3": round(model.val().Volume(), 1),
            "step_bytes": os.path.getsize(step), "stl_bytes": os.path.getsize(stl)}


def build_vehicle(cfg):
    """Full vehicle: airframe + autopilot (Pixhawk-class) + gimballed seeker under the nose (+X)."""
    m = build_cad(cfg)
    fr = max(45.0, 0.28 * cfg["L_arm"] * MM)
    z_top = 10.0 + 12 + 2
    # autopilot stack (flight controller) on top plate
    m = m.union(cq.Workplane("XY").box(70, 45, 16).translate((0, 0, z_top + 10)))
    # seeker: gimbal yoke post + EO/IR ball under the nose
    sx = fr * 1.15
    m = m.union(cq.Workplane("XY").cylinder(28, 6).translate((sx, 0, 10.0 - 16)))
    m = m.union(cq.Workplane("XY").sphere(38).translate((sx, 0, 10.0 - 42)))
    return m


def generate_vehicle(cfg=None, out_dir=None, name="specimen"):
    cfg = cfg or DEFAULT_CFG
    out_dir = out_dir or HERE
    os.makedirs(out_dir, exist_ok=True)
    model = build_vehicle(cfg)
    step = os.path.join(out_dir, f"{name}.step")
    stl = os.path.join(out_dir, f"{name}.stl")
    cq.exporters.export(model, step)
    cq.exporters.export(model, stl)
    bb = model.val().BoundingBox()
    return {"step": step, "stl": stl, "span_mm": round(max(bb.xlen, bb.ylen), 1),
            "height_mm": round(bb.zlen, 1), "volume_mm3": round(model.val().Volume(), 1),
            "step_bytes": os.path.getsize(step), "stl_bytes": os.path.getsize(stl)}


if __name__ == "__main__":
    info = generate(name="specimen_quad")
    print("CAD generated from cfg:")
    for k, v in info.items():
        print(f"  {k:12s} {v}")
