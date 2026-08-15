r"""SpecimenLab CAD — a native Windows 3D design workspace over the REAL forge engine.

SolidWorks-style: a shaded, orbit-able 3D model with a feature tree, a property-manager slider column,
and a live capability panel. Pure VTK (no Qt) + numpy — both already installed. Every design parameter
drives BOTH the 3D geometry (props, motors, arms, frame, battery grow/twist to scale) AND the real
coupled solve (mass / TWR / a_max / v_max / endurance / mission), so the device is tangible and honest:
the numbers are the engine's numbers.

    python cad.py            # native 3D window
    python cad.py test       # offscreen -> writes a PNG (for headless verification)

Viewport:  LMB orbit · RMB / wheel zoom · MMB pan · [w] wireframe · [f] fit · [s] screenshot · [q] quit
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import vtk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "physics"))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

from uav import build_uav, capabilities, G           # noqa: E402
from solve import solve                               # noqa: E402
import diagnose                                        # noqa: E402
try:
    from agent import ground_system                   # noqa: E402
except Exception:
    ground_system = None

IN2M = 0.0254

DEFAULT_CFG = dict(D_in=13, pitch_in=6, Kv=300, I_max=45, S=6,
                   cap_mAh=5000, C_rate=60, L_arm=0.30, payload=0.6, n_rotors=4)
# key, lo, hi, label, unit  (the property-manager sliders)
SLIDERS = [
    ("D_in",     8, 22,   "Prop dia (in)"),
    ("pitch_in", 4, 14,   "Prop pitch (in)"),
    ("Kv",       150, 450, "Motor Kv"),
    ("I_max",    20, 90,   "Current cap (A)"),
    ("S",        4, 12,    "Cells (S)"),
    ("cap_mAh",  2000, 16000, "Capacity (mAh)"),
    ("L_arm",    0.15, 0.60, "Arm length (m)"),
    ("payload",  0.0, 2.0, "Payload (kg)"),
]

# palette
CARBON  = (0.10, 0.11, 0.13)
ALUM    = (0.62, 0.65, 0.70)
COPPER  = (0.72, 0.45, 0.20)
PROP    = (0.13, 0.55, 0.52)
BATT    = (0.85, 0.62, 0.16)
ACCENT  = (0.20, 0.84, 0.78)


# ----------------------------------------------------------------- geometry helpers
def _naca_contour(t=0.12, m=0.02, p=0.4, npts=40):
    """A cambered airfoil closed contour (upper TE->LE, lower LE->TE), normalized chord 0..1."""
    xc = (1 - np.cos(np.linspace(0, math.pi, npts))) / 2          # cosine spacing
    yt = 5 * t * (0.2969*np.sqrt(xc) - 0.1260*xc - 0.3516*xc**2 + 0.2843*xc**3 - 0.1015*xc**4)
    yc = np.where(xc < p, m/p**2*(2*p*xc - xc**2), m/(1-p)**2*((1-2*p) + 2*p*xc - xc**2))
    xu, yu = xc, yc + yt
    xl, yl = xc, yc - yt
    X = np.concatenate([xu[::-1], xl[1:]])
    Y = np.concatenate([yu[::-1], yl[1:]])
    return X, Y


def make_propeller(R, pitch_m, n_blades=2, hub_r=0.010):
    """A twisted propeller: airfoil sections lofted along the span, pitch sets the twist. Returns polydata.
    Spins in the XY plane (shaft = +Z); blades extend radially in X, chord in Y, thickness in Z."""
    Xc, Yc = _naca_contour(npts=28)
    M = len(Xc)
    stations = np.linspace(hub_r, R, 14)
    append = vtk.vtkAppendPolyData()

    for b in range(n_blades):
        phi = b * 2*math.pi / n_blades
        cphi, sphi = math.cos(phi), math.sin(phi)
        sg = vtk.vtkStructuredGrid()
        sg.SetDimensions(M, len(stations), 1)
        pts = vtk.vtkPoints()
        pts.SetNumberOfPoints(M*len(stations))
        for i, r in enumerate(stations):
            frac = (r - hub_r) / max(R - hub_r, 1e-6)
            chord = R * (0.16 - 0.09*frac) + 0.006                 # taper toward the tip
            beta = math.atan2(pitch_m, 2*math.pi*max(r, 1e-3))     # blade-element twist from pitch
            cb, sb = math.cos(beta), math.sin(beta)
            for k in range(M):
                y0 = (Xc[k]-0.25)*chord                            # chordwise (about quarter-chord)
                z0 = Yc[k]*chord                                   # thickness
                y = y0*cb - z0*sb
                z = y0*sb + z0*cb
                x = r
                # place blade b by rotating (x,y) about the shaft (Z)
                xr = x*cphi - y*sphi
                yr = x*sphi + y*cphi
                pts.SetPoint(k + M*i, xr, yr, z)
        sg.SetPoints(pts)
        surf = vtk.vtkStructuredGridGeometryFilter()
        surf.SetInputData(sg)
        surf.Update()
        append.AddInputData(surf.GetOutput())

    hub = vtk.vtkCylinderSource()
    hub.SetRadius(hub_r*1.4); hub.SetHeight(0.012); hub.SetResolution(28)
    tf = vtk.vtkTransform(); tf.RotateX(90)                        # cylinder Y-axis -> Z
    tfp = vtk.vtkTransformPolyDataFilter(); tfp.SetTransform(tf); tfp.SetInputConnection(hub.GetOutputPort()); tfp.Update()
    append.AddInputData(tfp.GetOutput())
    append.Update()

    nrm = vtk.vtkPolyDataNormals(); nrm.SetInputConnection(append.GetOutputPort())
    nrm.SplittingOff(); nrm.ConsistencyOn(); nrm.Update()
    return nrm.GetOutput()


def _cyl(radius, height, res=36):
    c = vtk.vtkCylinderSource(); c.SetRadius(radius); c.SetHeight(height); c.SetResolution(res); c.CappingOn()
    tf = vtk.vtkTransform(); tf.RotateX(90)                        # Y-axis -> Z
    f = vtk.vtkTransformPolyDataFilter(); f.SetTransform(tf); f.SetInputConnection(c.GetOutputPort()); f.Update()
    return f.GetOutput()


def make_motor(stator_d, height):
    """An outrunner: bell (can) + stator base + shaft. Returns list of (polydata, color, metal, rough)."""
    parts = []
    bell = _cyl(stator_d/2*1.06, height*0.7); parts.append((bell, ALUM, 0.9, 0.35))
    base = _cyl(stator_d/2*0.7, height*0.35); parts.append((base, COPPER, 0.7, 0.5))
    shaft = _cyl(0.0022, height*1.5); parts.append((shaft, ALUM, 1.0, 0.25))
    return parts


def _box(dx, dy, dz):
    b = vtk.vtkCubeSource(); b.SetXLength(dx); b.SetYLength(dy); b.SetZLength(dz); b.Update()
    return b.GetOutput()


def _translate(pd, x, y, z, rz=0.0):
    tf = vtk.vtkTransform(); tf.Translate(x, y, z); tf.RotateZ(math.degrees(rz))
    f = vtk.vtkTransformPolyDataFilter(); f.SetTransform(tf); f.SetInputData(pd); f.Update()
    return f.GetOutput()


def actor(pd, color, metallic=0.0, roughness=0.6, opacity=1.0):
    m = vtk.vtkPolyDataMapper(); m.SetInputData(pd)
    a = vtk.vtkActor(); a.SetMapper(m)
    p = a.GetProperty()
    try:
        p.SetInterpolationToPBR(); p.SetMetallic(metallic); p.SetRoughness(roughness)
    except Exception:
        pass
    p.SetColor(*color); p.SetOpacity(opacity)
    return a


def make_shroud(R, h):
    """A ducted-fan shroud: an open cylindrical wall (the duct) around the rotor, with a lip ring."""
    wall = vtk.vtkCylinderSource(); wall.SetRadius(R*1.08); wall.SetHeight(h); wall.SetResolution(48); wall.CappingOff()
    tf = vtk.vtkTransform(); tf.RotateX(90)
    f = vtk.vtkTransformPolyDataFilter(); f.SetTransform(tf); f.SetInputConnection(wall.GetOutputPort()); f.Update()
    lip = vtk.vtkParametricTorus(); lip.SetRingRadius(R*1.08); lip.SetCrossSectionRadius(h*0.14)
    src = vtk.vtkParametricFunctionSource(); src.SetParametricFunction(lip); src.SetUResolution(48); src.SetVResolution(12); src.Update()
    top = _translate(src.GetOutput(), 0, 0, h/2)
    ap = vtk.vtkAppendPolyData(); ap.AddInputData(f.GetOutput()); ap.AddInputData(top); ap.Update()
    return ap.GetOutput()


def make_wing(span, chord, fus_len):
    """A fixed-wing airframe: fuselage + main wing + tailplane + fin + pusher prop. Nose = +X, wings = Y.
    Returns list of (polydata, color, metallic, roughness)."""
    parts = []
    # fuselage (a stretched capsule along X)
    fus = vtk.vtkCylinderSource(); fus.SetRadius(fus_len*0.06); fus.SetHeight(fus_len); fus.SetResolution(28); fus.CappingOn()
    tf = vtk.vtkTransform(); tf.RotateZ(90)                     # cylinder Y-axis -> X
    f = vtk.vtkTransformPolyDataFilter(); f.SetTransform(tf); f.SetInputConnection(fus.GetOutputPort()); f.Update()
    parts.append((_translate(f.GetOutput(), 0, 0, 0), CARBON, 0.1, 0.4))
    nose = vtk.vtkSphereSource(); nose.SetRadius(fus_len*0.06); nose.SetThetaResolution(24); nose.SetPhiResolution(24); nose.Update()
    parts.append((_translate(nose.GetOutput(), fus_len/2, 0, 0), CARBON, 0.1, 0.4))
    # main wing (span in Y, chord in X, thin in Z), slight forward mount
    parts.append((_translate(_box(chord, span, 0.012), fus_len*0.06, 0, fus_len*0.05), PROP, 0.15, 0.5))
    # tailplane + vertical fin at the back
    parts.append((_translate(_box(chord*0.5, span*0.42, 0.010), -fus_len*0.42, 0, 0), PROP, 0.15, 0.5))
    parts.append((_translate(_box(chord*0.5, 0.010, span*0.18), -fus_len*0.42, 0, span*0.09), PROP, 0.15, 0.5))
    # pusher prop at the tail (shaft along X)
    prop = make_propeller(chord*0.9, chord*0.8, n_blades=2, hub_r=0.008)
    tfp = vtk.vtkTransform(); tfp.Translate(-fus_len*0.5, 0, 0); tfp.RotateY(90)   # prop plane -> YZ (thrust +X)
    pf = vtk.vtkTransformPolyDataFilter(); pf.SetTransform(tfp); pf.SetInputData(prop); pf.Update()
    parts.append((pf.GetOutput(), ALUM, 0.2, 0.45))
    return parts


# ----------------------------------------------------------------- the app
class CAD:
    def __init__(self):
        self.cfg = dict(DEFAULT_CFG)
        self.mission = dict(a_req=5.0, v_req=30.0, endur_req=10.0)
        self.parts = []
        self.sub_actors = {}          # subsystem name -> [actors]  (for diagnose highlight)
        self.mech = "rotor"           # rotor | ducted_fan
        self.platform = "quad"        # quad | wing
        self.wing_info = None
        self.highlight = None         # subsystem to highlight
        self.wire = False

        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground(0.055, 0.065, 0.085)
        self.ren.SetBackground2(0.11, 0.13, 0.17)
        self.ren.GradientBackgroundOn()
        self.ren.SetUseDepthPeeling(1)

        self.win = vtk.vtkRenderWindow()
        self.win.AddRenderer(self.ren)
        self.win.SetSize(1360, 860)
        self.win.SetWindowName("SpecimenLab CAD  —  physics-grounded design")
        self.win.SetMultiSamples(8)

        self._lights()
        self._ground()
        self._text()
        self.build_geometry()
        self.solve_and_report()

    # -- scene ------------------------------------------------------
    def _lights(self):
        self.ren.AutomaticLightCreationOff()
        key = vtk.vtkLight(); key.SetPosition(1.2, -1.0, 2.2); key.SetFocalPoint(0, 0, 0)
        key.SetIntensity(1.05); key.SetColor(1.0, 0.98, 0.94); key.PositionalOff()
        fill = vtk.vtkLight(); fill.SetPosition(-1.5, 0.6, 1.0); fill.SetIntensity(0.45); fill.SetColor(0.8, 0.85, 1.0); fill.PositionalOff()
        rim = vtk.vtkLight(); rim.SetPosition(-0.4, 1.6, 0.6); rim.SetIntensity(0.5); rim.SetColor(0.9, 0.95, 1.0); rim.PositionalOff()
        for l in (key, fill, rim):
            self.ren.AddLight(l)
        self.key = key

    def _ground(self):
        grid = vtk.vtkAppendPolyData()
        n, step = 9, 0.1
        ext = n*step
        for i in range(-n, n+1):
            for (x0, y0, x1, y1) in [(-ext, i*step, ext, i*step), (i*step, -ext, i*step, ext)]:
                ln = vtk.vtkLineSource(); ln.SetPoint1(x0, y0, -0.001); ln.SetPoint2(x1, y1, -0.001); ln.Update()
                grid.AddInputData(ln.GetOutput())
        grid.Update()
        ga = actor(grid.GetOutput(), (0.16, 0.18, 0.22)); ga.GetProperty().SetLineWidth(1)
        ga.GetProperty().SetLighting(False)
        self.ren.AddActor(ga)

    def _text(self):
        def mk(x, y, size, color=(0.9, 0.94, 1.0), font="Courier", just=0):
            t = vtk.vtkTextActor(); tp = t.GetTextProperty()
            tp.SetFontSize(size); tp.SetColor(*color); tp.SetFontFamilyAsString(font)
            tp.SetJustification(just)
            t.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
            t.SetPosition(x, y)
            self.ren.AddActor2D(t)
            return t
        title = mk(0.012, 0.955, 22, ACCENT)
        title.GetTextProperty().SetVerticalJustificationToTop()
        title.SetInput("SpecimenLab  CAD")
        mk(0.012, 0.928, 12, (0.55, 0.62, 0.72)).SetInput("physics-grounded design  ·  live over the real forge engine")
        self.tree_txt = mk(0.012, 0.47, 13)                       # feature tree (left)
        self.tree_txt.GetTextProperty().SetVerticalJustificationToTop()
        self.res_txt = mk(0.988, 0.99, 15, (0.85, 0.92, 1.0), just=2)   # results (top-right)
        self.res_txt.GetTextProperty().SetVerticalJustificationToTop()
        self.env_txt = mk(0.988, 0.80, 12, (0.95, 0.66, 0.18), just=2)   # validity envelope (right)
        self.env_txt.GetTextProperty().SetVerticalJustificationToTop()
        self.msn_txt = mk(0.988, 0.62, 14, just=2)                # mission (right)
        self.msn_txt.GetTextProperty().SetVerticalJustificationToTop()
        self.diag_txt = mk(0.30, 0.135, 13, ACCENT)               # diagnose/repair log (bottom center)
        self.diag_txt.GetTextProperty().SetVerticalJustificationToTop()
        mk(0.012, 0.018, 11, (0.5, 0.56, 0.66)).SetInput(
            "LMB orbit · wheel/RMB zoom · MMB pan | [d] diagnose  [r] repair  [g] duct  [e] wing (exp)  [1] reset | [w] wire  [f] fit  [s] shot  [q] quit")

    # -- geometry ---------------------------------------------------
    def build_geometry(self):
        for a in self.parts:
            self.ren.RemoveActor(a)
        self.parts = []
        self.sub_actors = {}
        if self.platform == "wing":
            self._build_wing()
        else:
            self._build_quad()
        self.tree_txt.SetInput(self._tree_text())
        self._apply_highlight()

    def _build_quad(self):
        cfg = self.cfg
        n = int(cfg["n_rotors"])
        R = cfg["D_in"]*IN2M/2
        pitch_m = cfg["pitch_in"]*IN2M
        L = cfg["L_arm"]
        stator_d = 0.020 + 0.00035*cfg["I_max"]                   # bigger current cap -> bigger motor
        motor_h = 0.008 + 0.00025*cfg["I_max"]
        arm_r = 0.006 + 0.0006*cfg["D_in"]
        z_arm = 0.010
        z_motor = z_arm + motor_h/2
        z_prop = z_arm + motor_h + 0.006

        # central frame: two carbon plates + standoffs  (structure)
        fr = max(0.045, 0.28*L)
        self._add(_translate(_box(2*fr, 2*fr, 0.004), 0, 0, z_arm+0.014), CARBON, 0.1, 0.35, "structure")
        self._add(_translate(_box(2*fr, 2*fr, 0.004), 0, 0, z_arm-0.004), CARBON, 0.1, 0.35, "structure")
        for sx in (-1, 1):
            for sy in (-1, 1):
                so = _translate(_cyl(0.003, 0.018), sx*fr*0.8, sy*fr*0.8, z_arm+0.005)
                self._add(so, ALUM, 0.9, 0.4, "structure")

        # battery pack under the frame, sized by pack energy  (energy)
        packWh = cfg["S"]*3.7*cfg["cap_mAh"]/1000.0
        vol = packWh/250.0/1000.0                                 # ~250 Wh/L
        bx = (vol)**(1/3)*1.6; by = bx*0.55; bz = max(0.02, vol/max(bx*by, 1e-6))
        self._add(_translate(_box(bx, by, bz), 0, 0, z_arm-0.006-bz/2), BATT, 0.0, 0.5, "energy")

        # arms + motors + props (X config)  (arm=structure, motor/prop/shroud=propulsion)
        prop_pd = make_propeller(R, pitch_m, n_blades=2)
        shroud_pd = make_shroud(R, motor_h + 0.03) if self.mech == "ducted_fan" else None
        for i in range(n):
            ang = math.radians(45 + i*360/n)
            ex, ey = L*math.cos(ang), L*math.sin(ang)
            arm = _cyl(arm_r, L)
            tf = vtk.vtkTransform(); tf.Translate(ex/2, ey/2, z_arm); tf.RotateZ(math.degrees(ang)); tf.RotateY(90)
            f = vtk.vtkTransformPolyDataFilter(); f.SetTransform(tf); f.SetInputData(arm); f.Update()
            self._add(f.GetOutput(), CARBON, 0.1, 0.4, "structure")
            for pd, col, met, rgh in make_motor(stator_d, motor_h):
                self._add(_translate(pd, ex, ey, z_motor), col, met, rgh, "propulsion")
            self._add(_translate(prop_pd, ex, ey, z_prop), PROP, 0.2, 0.45, "propulsion")
            if shroud_pd is not None:
                self._add(_translate(shroud_pd, ex, ey, z_prop-0.01), (0.45, 0.5, 0.58), 0.6, 0.4, "propulsion")

    def _build_wing(self):
        w = self.wing_info
        span, chord, fus = w["span"], w["chord"], w["span"]*0.6
        for pd, col, met, rgh in make_wing(span, chord, fus):
            self._add(pd, col, met, rgh, "propulsion" if col == ALUM else "structure")
        # battery inside the fuselage (energy)
        cfg = self.cfg
        packWh = cfg["S"]*3.7*cfg["cap_mAh"]/1000.0
        vol = packWh/250.0/1000.0
        bx = min(fus*0.4, (vol)**(1/3)*1.6); by = bx*0.5; bz = max(0.015, vol/max(bx*by, 1e-6))
        self._add(_translate(_box(bx, by, bz), fus*0.12, 0, 0), BATT, 0.0, 0.5, "energy")

    def _add(self, pd, color, met=0.0, rgh=0.6, owner=None):
        a = actor(pd, color, met, rgh)
        a._base_color = color
        if self.wire:
            a.GetProperty().SetRepresentationToWireframe()
        self.ren.AddActor(a); self.parts.append(a)
        if owner:
            self.sub_actors.setdefault(owner, []).append(a)

    def _apply_highlight(self):
        for a in self.parts:                                       # restore base colors
            a.GetProperty().SetColor(*a._base_color)
            try: a.GetProperty().SetEmissiveFactor(0, 0, 0)
            except Exception: pass
        if self.highlight and self.highlight in self.sub_actors:
            for a in self.sub_actors[self.highlight]:
                a.GetProperty().SetColor(1.0, 0.55, 0.12)      # distinct highlight (amber)

    def _tree_text(self):
        c = self.cfg
        if self.platform == "wing":
            body = ["  energy       stored_energy   ◆battery",
                    "  weight_supp  lift            ◆wing_lift",
                    "  structure    stress          ◆wing+boom",
                    "  payload      mass"]
            head = " AIRCRAFT (fixed wing)"
        else:
            body = ["  energy       stored_energy   ◆battery",
                    f"  propulsion   thrust          ◆{self.mech}",
                    "  structure    stress",
                    "    arm        bending_stress  ◆carbon_beam",
                    "    frame      stress          ◆plate",
                    "  payload      mass"]
            head = " UAV  (System)"
        return "\n".join(["FEATURE TREE", head] + body + ["",
            f" D={c['D_in']:.1f}in  pitch={c['pitch_in']:.1f}in  Kv={c['Kv']:.0f}",
            f" I={c['I_max']:.0f}A  {c['S']:.0f}S {c['cap_mAh']:.0f}mAh  arm={c['L_arm']:.2f}m"])

    # -- validity envelope (the model's boundaries) -----------------
    # where the physics models are validated; outside these the numbers are extrapolation, not truth.
    ENV = {"tip_mach": 0.70, "disk_loading": 250.0, "twr_min": 1.2}   # BEMT / momentum-theory / control margin

    def _envelope_warnings(self, sysm, bus, cap):
        w = []
        prop = sysm.by_name()["propulsion"]
        n = prop.params["n_rotors"]
        R = prop.params["D_in"] * IN2M / 2
        rpm = prop.state.get("_rpm", 0.0)
        tip_mach = (rpm * 2 * math.pi / 60.0) * R / 343.0 if rpm else 0.0
        if tip_mach > self.ENV["tip_mach"]:
            w.append(f"tip Mach {tip_mach:.2f} > {self.ENV['tip_mach']:.2f} — BEMT extrapolating")
        A = n * math.pi * R * R
        dl = cap["thrust"] / A if A > 0 else 0.0
        if dl > self.ENV["disk_loading"]:
            w.append(f"disk loading {dl:.0f} N/m2 — high, hover-power model strained")
        if cap["TWR"] < 1.0:
            w.append(f"TWR {cap['TWR']:.2f} < 1 — cannot lift off")
        elif cap["TWR"] < self.ENV["twr_min"]:
            w.append(f"TWR {cap['TWR']:.2f} < {self.ENV['twr_min']} — no hover control margin")
        i_pack = bus.get("i_burst_per_rotor")
        if i_pack is not None and i_pack < prop.params["I_max"] - 1e-6:
            w.append(f"C-rate limited: pack {i_pack:.0f} A/rotor < motor cap {prop.params['I_max']:.0f} A")
        if not bus.get("converged"):
            w.append("solve did not converge — result unsettled")
        return w

    # -- solve ------------------------------------------------------
    def solve_and_report(self):
        try:
            if self.platform == "wing":
                w = diagnose.wing_alternative(self.cfg, self.mission)
                mass, a_g, v_max, endur, thrust, conv = w["mass"], 0.0, w["cruise_v"], w["endurance_min"], 0.0, True
                self.res_txt.SetInput(
                    f"platform  FIXED WING (exp)\n"
                    f"mass       {mass:6.2f} kg\n"
                    f"cruise     {v_max:6.1f} m/s\n"
                    f"endurance  {endur:6.1f} min\n"
                    f"wing span  {w['span']*100:6.0f} cm\n"
                    f"hover           no")
                self.env_txt.SetInput("ENVELOPE\nEXPERIMENTAL — outside\nthe UAV tool's\nvalidated scope")
            else:
                sysm = build_uav(self.cfg, propulsion_mechanism=self.mech)
                bus = solve(sysm, seed={"current": 0.0, "total_mass": 4.0})
                cap = capabilities(sysm, bus)
                a_g = cap["a_max"]/G; v_max = cap["v_max"]; endur = cap["endurance"]/60.0; conv = bus.get("converged")
                self.res_txt.SetInput(
                    f"platform   QUAD ({self.mech})\n"
                    f"mass       {cap['mass']:6.2f} kg\n"
                    f"TWR        {cap['TWR']:6.2f}\n"
                    f"a_max      {a_g:6.2f} g\n"
                    f"v_max      {v_max:6.1f} m/s\n"
                    f"endurance  {endur:6.1f} min\n"
                    f"thrust     {cap['thrust']:6.1f} N\n"
                    f"{'converged' if conv else 'not settled'}")
                warns = self._envelope_warnings(sysm, bus, cap)
                self.env_txt.SetInput("ENVELOPE\n" + ("\n".join("! " + x for x in warns)
                                       if warns else "within validated limits"))
                self.env_txt.GetTextProperty().SetColor(*((0.95, 0.66, 0.18) if warns else (0.45, 0.62, 0.5)))
            crit = [("speed", v_max, self.mission["v_req"], "m/s"),
                    ("endur", endur, self.mission["endur_req"], "min")]
            if self.platform != "wing":                            # agility is a multirotor criterion
                crit.insert(0, ("agility", a_g, self.mission["a_req"], "g"))
            lines = ["MISSION"]
            allmet = True
            for nm, have, req, u in crit:
                ok = have >= req - 1e-6; allmet &= ok
                lines.append(f"{nm:6s} {have:5.1f}/{req:.0f}{u:>4s}  {'MET' if ok else 'MISS'}")
            lines.append("ALL MET" if allmet else "NOT MET")
            self.msn_txt.SetInput("\n".join(lines))
            self.msn_txt.GetTextProperty().SetColor(*((0.25, 0.85, 0.35) if allmet else (0.95, 0.35, 0.30)))
        except Exception as e:
            self.res_txt.SetInput(f"solve error:\n{type(e).__name__}\n{e}")

    # -- actions (diagnose / repair / escalate) ---------------------
    def run_diagnose(self):
        d = diagnose.diagnose(self.cfg, self.mission)
        self.diag = d
        if d["failing"] is None:
            self.highlight = None
            self.diag_txt.SetInput("DIAGNOSE:  mission already met — no failing metric.")
        else:
            self.highlight = d["levers"][0]["owner"]
            lines = [f"DIAGNOSE   failing metric: {d['failing']}   "
                     f"(have {d['caps'][d['failing']]:.2f}, need {d['reqs'][d['failing']]:.2f})",
                     "root-cause levers  (d(fail)/d(param), normalized):"]
            for L in d["levers"][:4]:
                lines.append(f"  {L['param']:8s}[{L['owner']:10s}] push {L['help_dir']}  "
                             f"sens {L['sensitivity']:.2f}  {'movable' if L['movable'] else 'IMMOVABLE (at bound)'}")
            held = d["repair_dir"]["held"] if d["repair_dir"] else []
            lines.append(f"null-space repair will HOLD (not break): {held or 'nothing binding'}")
            lines.append("press [r] to repair")
            self.diag_txt.SetInput("\n".join(lines))
        self.build_geometry(); self.win.Render()

    def run_repair(self):
        self.diag_txt.SetInput("REPAIRING…  null-space steps over the real coupled solve"); self.win.Render()
        cfg, met, ex, hist, info = diagnose.repair(self.cfg, self.mission)
        self.cfg.update({k: cfg[k] for k in diagnose.PARAMS})
        self._sync_sliders()
        self.highlight = None
        self.build_geometry(); self.solve_and_report()
        if met:
            self.diag_txt.SetInput(f"REPAIRED in {len(hist)-1} null-space steps — mission MET.  "
                                   f"held (kept satisfied): {info.get('held') or 'nothing'}")
        else:
            fm = info.get("failing", "requirement")
            self.diag_txt.SetInput(
                f"BEYOND THE MULTIROTOR ENVELOPE — '{fm}' cannot be met by any design within the bounds.\n"
                f"reason: {info.get('reason') or 'null space collapsed — no lever helps without breaking another'}.\n"
                "cross-class escalation is OUT OF SCOPE for this UAV tool.   [e] = experimental fixed-wing preview")
        self.win.Render()

    def toggle_duct(self):
        self.platform = "quad"
        self.mech = "ducted_fan" if self.mech == "rotor" else "rotor"
        self.highlight = "propulsion"
        self.build_geometry(); self.solve_and_report()
        self.diag_txt.SetInput(f"MECHANISM SWAP:  propulsion → {self.mech}  (radicality d=1, within budget).  "
                               "shroud recovers slipstream: more static thrust, more mass.")
        self.highlight = None
        self.win.Render()

    def escalate_wing(self):
        w = diagnose.wing_alternative(self.cfg, self.mission)
        before = diagnose.caps_of(self.cfg)["endurance_min"]
        self.wing_info = w
        self.platform = "wing"
        self.highlight = None
        self.build_geometry(); self.solve_and_report()
        self.diag_txt.SetInput(
            f"[EXPERIMENTAL — outside UAV scope]  quad → FIXED WING  (crossed rotor→wing, structural change).\n"
            f"endurance {before:.0f} min (rotor, exhausted) → {w['endurance_min']:.0f} min (wing).  "
            f"shown as a preview of cross-class escalation; not part of the multirotor tool.  [1] to return.")
        self.win.Render()

    def reset_quad(self):
        self.platform = "quad"; self.mech = "rotor"; self.highlight = None
        self.cfg = dict(DEFAULT_CFG)
        self._sync_sliders()
        self.build_geometry(); self.solve_and_report()
        self.diag_txt.SetInput("reset → rotor quad (defaults).")
        self.win.Render()

    def _sync_sliders(self):
        if not hasattr(self, "slider_widgets"):
            return
        for w, (key, lo, hi, label) in zip(self.slider_widgets, SLIDERS):
            w.GetRepresentation().SetValue(self.cfg[key])

    # -- interaction ------------------------------------------------
    def _sliders(self, iren):
        self.slider_widgets = []
        y = 0.90
        for key, lo, hi, label in SLIDERS:
            rep = vtk.vtkSliderRepresentation2D()
            rep.SetMinimumValue(lo); rep.SetMaximumValue(hi); rep.SetValue(self.cfg[key])
            rep.SetTitleText(label)
            rep.GetPoint1Coordinate().SetCoordinateSystemToNormalizedViewport(); rep.GetPoint1Coordinate().SetValue(0.02, y)
            rep.GetPoint2Coordinate().SetCoordinateSystemToNormalizedViewport(); rep.GetPoint2Coordinate().SetValue(0.20, y)
            rep.SetSliderLength(0.012); rep.SetSliderWidth(0.02); rep.SetEndCapLength(0.006)
            rep.SetTubeWidth(0.006); rep.SetLabelHeight(0.018); rep.SetTitleHeight(0.020)
            for tp in (rep.GetSliderProperty(), rep.GetSelectedProperty()):
                tp.SetColor(*ACCENT)
            rep.GetTubeProperty().SetColor(0.3, 0.34, 0.4)
            rep.GetCapProperty().SetColor(0.5, 0.55, 0.62)
            rep.GetTitleProperty().SetColor(0.75, 0.82, 0.92); rep.GetLabelProperty().SetColor(*ACCENT)
            rep.GetTitleProperty().SetFontSize(10); rep.GetLabelProperty().SetFontSize(10)
            w = vtk.vtkSliderWidget(); w.SetInteractor(iren); w.SetRepresentation(rep); w.SetAnimationModeToOff(); w.EnabledOn()

            def on_change(obj, evt, k=key):
                self.cfg[k] = obj.GetRepresentation().GetValue()
                self.build_geometry(); self.win.Render()

            def on_release(obj, evt, k=key):
                self.solve_and_report(); self.win.Render()

            w.AddObserver("InteractionEvent", on_change)
            w.AddObserver("EndInteractionEvent", on_release)
            self.slider_widgets.append(w)
            y -= 0.052

    def _on_key(self, iren, evt):
        k = iren.GetKeySym()
        if k in ("w", "W"):
            self.wire = not self.wire
            for a in self.parts:
                a.GetProperty().SetRepresentationToWireframe() if self.wire else a.GetProperty().SetRepresentationToSurface()
            self.win.Render()
        elif k in ("f", "F"):
            self._camera(); self.win.Render()
        elif k in ("s", "S"):
            self.screenshot(os.path.join(HERE, "specimenlab_shot.png")); print("saved screenshot")
        elif k in ("d", "D"):
            self.run_diagnose()
        elif k in ("r", "R"):
            self.run_repair()
        elif k in ("g", "G"):
            self.toggle_duct()
        elif k in ("e", "E"):
            self.escalate_wing()
        elif k == "1":
            self.reset_quad()

    def screenshot(self, path):
        w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(self.win); w2i.SetScale(2); w2i.Update()
        wr = vtk.vtkPNGWriter(); wr.SetFileName(path); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()

    def _drone_bounds(self):
        b = [1e9, -1e9, 1e9, -1e9, 1e9, -1e9]
        for a in self.parts:
            ab = a.GetBounds()
            for i in (0, 2, 4):
                b[i] = min(b[i], ab[i]); b[i+1] = max(b[i+1], ab[i+1])
        return b

    def _camera(self):
        cam = self.ren.GetActiveCamera()
        self.ren.ResetCamera(self._drone_bounds())          # frame the DRONE, not the floor
        fp = cam.GetFocalPoint(); dist = cam.GetDistance()  # ABSOLUTE iso placement (idempotent)
        d = np.array([0.55, -0.75, 0.48]); d = d / np.linalg.norm(d)
        cam.SetPosition(fp[0] + dist*d[0], fp[1] + dist*d[1], fp[2] + dist*d[2])
        cam.SetViewUp(0, 0, 1)
        cam.Zoom(1.25)
        self.ren.ResetCameraClippingRange()

    def run(self):
        iren = vtk.vtkRenderWindowInteractor()
        iren.SetRenderWindow(self.win)
        iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self._sliders(iren)
        iren.AddObserver("KeyPressEvent", self._on_key)
        # axis gizmo
        axes = vtk.vtkAxesActor()
        self.marker = vtk.vtkOrientationMarkerWidget()
        self.marker.SetOrientationMarker(axes); self.marker.SetInteractor(iren)
        self.marker.SetViewport(0.82, 0.0, 1.0, 0.20); self.marker.EnabledOn(); self.marker.InteractiveOff()
        self._camera()
        self.win.Render()
        iren.Initialize(); iren.Start()

    def _shot(self, tag):
        self._camera(); self.win.Render()
        p = os.path.join(HERE, f"specimenlab_{tag}.png")
        self.screenshot(p); print("wrote", p)


def main():
    app = CAD()
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        app.win.SetOffScreenRendering(1)
        app._shot("cad_test")                                  # default quad
        # diagnose + repair a mission the quad fails on agility
        app.mission = {"a_req": 6.0, "v_req": 10.0, "endur_req": 15.0}
        app.solve_and_report(); app.run_diagnose(); app._shot("01_diagnose")
        app.run_repair(); app._shot("02_repaired")
        # mechanism swap: ducted fan
        app.reset_quad(); app.toggle_duct(); app._shot("03_ducted")
        # structural escalation: endurance the quad cannot meet -> repair exhausts -> fixed wing
        app.reset_quad(); app.mission = {"a_req": 1.5, "v_req": 8.0, "endur_req": 200.0}
        app.run_repair()                                       # parametric repair exhausts (maxes pack)
        app.escalate_wing(); app._shot("04_wing")
    else:
        app.run()


if __name__ == "__main__":
    main()
