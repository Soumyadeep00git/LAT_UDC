r"""Build a full propeller 3D model from the physics-designed blade, write an STL, and emit a self-contained
interactive viewer (Canvas software renderer, no external libraries)."""
from __future__ import annotations

import math
import os

import blade_design as BD

RHO = 1.225


def _section(r, c, th, M, thick=0.09):
    u = [(-c / 4) + (i / (M - 1)) * c for i in range(M)]
    pts_top, pts_bot = [], []
    for uu in u:
        xf = (uu + c / 4) / c
        yt = thick * c * math.sqrt(max(xf * (1 - xf), 0.0))
        pts_top.append((uu * math.cos(th) - yt * math.sin(th), r, uu * math.sin(th) + yt * math.cos(th)))
        pts_bot.append((uu * math.cos(th) + yt * math.sin(th), r, uu * math.sin(th) - yt * math.cos(th)))
    return pts_top + pts_bot[::-1]                        # closed loop, 2M points


def _rotz(p, a):
    x, y, z = p
    return (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), z)


def build_mesh(geom, n_blades=2, M=12):
    r, c, th = geom["r"], geom["chord"], geom["twist"]
    loops = [_section(r[i], c[i], th[i], M) for i in range(len(r))]
    tris = []
    # one blade (pointing +y), lofted between sections
    blade = []
    for i in range(len(loops) - 1):
        a, b = loops[i], loops[i + 1]
        n = len(a)
        for j in range(n):
            k = (j + 1) % n
            blade.append((a[j], a[k], b[j]))
            blade.append((a[k], b[k], b[j]))
    # replicate around the hub axis (z)
    for bi in range(n_blades):
        ang = 2 * math.pi * bi / n_blades
        for (p, q, s) in blade:
            tris.append((_rotz(p, ang), _rotz(q, ang), _rotz(s, ang)))
    # a simple hub cylinder along z
    rh, h, K = 1.25 * r[0], 0.012, 20
    ring_t = [(rh * math.cos(2 * math.pi * k / K), rh * math.sin(2 * math.pi * k / K), h) for k in range(K)]
    ring_b = [(rh * math.cos(2 * math.pi * k / K), rh * math.sin(2 * math.pi * k / K), -h) for k in range(K)]
    ct, cb = (0, 0, h), (0, 0, -h)
    for k in range(K):
        kk = (k + 1) % K
        tris.append((ring_t[k], ring_t[kk], ring_b[k]))
        tris.append((ring_t[kk], ring_b[kk], ring_b[k]))
        tris.append((ct, ring_t[kk], ring_t[k]))
        tris.append((cb, ring_b[k], ring_b[kk]))
    return tris


def write_stl(tris, path):
    with open(path, "w") as f:
        f.write("solid propeller\n")
        for t in tris:
            f.write(" facet normal 0 0 0\n  outer loop\n")
            for v in t:
                f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("  endloop\n endfacet\n")
        f.write("endsolid propeller\n")


def write_viewer(tris, geom, path):
    scale = 1000.0 / geom["R_tip"]                       # normalize to ~unit radius, in convenient units
    flat = []
    for t in tris:
        for v in t:
            flat += [round(v[0] * scale, 1), round(v[1] * scale, 1), round(v[2] * scale, 1)]
    import math as _m
    meta = dict(thrust=round(geom["thrust_forward"], 1), rpm=geom["rpm"], n=len(tris),
                R=round(geom["R_tip"] * 1000), chord_root=round(geom["chord"][0] * 1000, 1),
                chord_tip=round(geom["chord"][-1] * 1000, 1),
                tw_root=round(_m.degrees(geom["twist"][0]), 1), tw_tip=round(_m.degrees(geom["twist"][-1]), 1))
    html = _TEMPLATE.replace("__DATA__", ",".join(str(x) for x in flat)) \
                    .replace("__META__", str(meta).replace("'", '"'))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


_TEMPLATE = r"""<title>Interceptor Blade</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root{--bg:#0d1521;--panel:#151f2d;--ink:#e7edf4;--mut:#8b99ac;--rule:#2a3a4e;--acc:#4aa3df;
        --mono:ui-monospace,Menlo,Consolas,monospace;--sans:system-ui,-apple-system,Segoe UI,sans-serif}
  *{box-sizing:border-box} html,body{margin:0;height:100%}
  body{background:var(--bg);color:var(--ink);font-family:var(--sans);overflow:hidden}
  #wrap{position:fixed;inset:0} canvas{display:block;width:100%;height:100%;cursor:grab}
  canvas:active{cursor:grabbing}
  .hdr{position:fixed;top:18px;left:20px;pointer-events:none}
  .hdr .eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--acc)}
  .hdr h1{margin:.2rem 0 0;font-family:var(--mono);font-size:22px;font-weight:700;letter-spacing:-.5px}
  .panel{position:fixed;bottom:18px;left:20px;background:rgba(21,31,45,.82);border:1px solid var(--rule);
    border-radius:12px;padding:12px 15px;font-family:var(--mono);font-size:12px;line-height:1.7;backdrop-filter:blur(4px)}
  .panel .k{color:var(--mut)} .panel b{color:var(--ink)} .panel .g{color:var(--acc)}
  .hint{position:fixed;bottom:18px;right:20px;color:var(--mut);font-family:var(--mono);font-size:11px;text-align:right}
  button{font-family:var(--mono);font-size:11px;background:var(--panel);color:var(--ink);border:1px solid var(--rule);
    border-radius:7px;padding:5px 9px;cursor:pointer;margin-top:6px}
</style>
<div id="wrap"><canvas id="c"></canvas></div>
<div class="hdr"><div class="eyebrow">LAT_UDC &middot; physics-designed</div><h1>Interceptor Blade</h1></div>
<div class="panel" id="meta"></div>
<div class="hint">drag to rotate &middot; scroll to zoom<br><button id="spin">pause spin</button></div>
<script>
const TRI = [__DATA__];            // flat: 9 numbers per triangle (3 verts x xyz), mm-ish
const M = __META__;
const c = document.getElementById('c'), g = c.getContext('2d');
let W,H,DPR; function resize(){DPR=Math.min(2,devicePixelRatio||1);W=c.clientWidth;H=c.clientHeight;
  c.width=W*DPR;c.height=H*DPR;g.setTransform(DPR,0,0,DPR,0,0);} addEventListener('resize',resize);resize();

// center the mesh
let cx=0,cy=0,cz=0,nV=TRI.length/3;
for(let i=0;i<TRI.length;i+=3){cx+=TRI[i];cy+=TRI[i+1];cz+=TRI[i+2];}
cx/=nV;cy/=nV;cz/=nV;

let rotX=-1.05, rotY=0.5, zoom=1.7, spinning=true;
const LIGHT=(()=>{const v=[0.35,0.5,1];const n=Math.hypot(...v);return v.map(x=>x/n);})();

function render(){
  g.clearRect(0,0,W,H);
  const cxr=Math.cos(rotX),sxr=Math.sin(rotX),cyr=Math.cos(rotY),syr=Math.sin(rotY);
  const s=Math.min(W,H)*0.0016*zoom, ox=W/2, oy=H/2, f=2200;
  const rot=p=>{ // rotate about Y then X
    let x=p[0]-cx,y=p[1]-cy,z=p[2]-cz;
    let x1=x*cyr+z*syr, z1=-x*syr+z*cyr;
    let y2=y*cxr-z1*sxr, z2=y*sxr+z1*cxr;
    return [x1,y2,z2];
  };
  const tris=[];
  for(let i=0;i<TRI.length;i+=9){
    const a=rot([TRI[i],TRI[i+1],TRI[i+2]]),b=rot([TRI[i+3],TRI[i+4],TRI[i+5]]),d=rot([TRI[i+6],TRI[i+7],TRI[i+8]]);
    const ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2],vx=d[0]-a[0],vy=d[1]-a[1],vz=d[2]-a[2];
    let nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;const nl=Math.hypot(nx,ny,nz)||1;nx/=nl;ny/=nl;nz/=nl;
    const diff=Math.abs(nx*LIGHT[0]+ny*LIGHT[1]+nz*LIGHT[2]);
    const sh=0.18+0.82*diff; // two-sided
    const R=Math.round(46+sh*120),Gc=Math.round(90+sh*120),B=Math.round(130+sh*95);
    tris.push({z:(a[2]+b[2]+d[2])/3,col:`rgb(${R},${Gc},${B})`,
      p:[[ox+a[0]*s*f/(f-a[2]),oy-a[1]*s*f/(f-a[2])],[ox+b[0]*s*f/(f-b[2]),oy-b[1]*s*f/(f-b[2])],[ox+d[0]*s*f/(f-d[2]),oy-d[1]*s*f/(f-d[2])]]});
  }
  tris.sort((p,q)=>p.z-q.z); // painter's: far first
  for(const t of tris){g.beginPath();g.moveTo(t.p[0][0],t.p[0][1]);g.lineTo(t.p[1][0],t.p[1][1]);
    g.lineTo(t.p[2][0],t.p[2][1]);g.closePath();g.fillStyle=t.col;g.fill();
    g.strokeStyle='rgba(10,18,28,.35)';g.lineWidth=.4;g.stroke();}
}
function loop(){ if(spinning) rotY+=0.006; render(); requestAnimationFrame(loop); }

// interaction
let drag=false,px,py;
c.addEventListener('pointerdown',e=>{drag=true;px=e.clientX;py=e.clientY;c.setPointerCapture(e.pointerId);});
c.addEventListener('pointermove',e=>{if(!drag)return;rotY+=(e.clientX-px)*0.008;rotX+=(e.clientY-py)*0.008;px=e.clientX;py=e.clientY;});
c.addEventListener('pointerup',()=>drag=false);
c.addEventListener('wheel',e=>{e.preventDefault();zoom*=e.deltaY<0?1.08:0.93;zoom=Math.max(.4,Math.min(6,zoom));},{passive:false});
document.getElementById('spin').onclick=e=>{spinning=!spinning;e.target.textContent=spinning?'pause spin':'resume spin';};

document.getElementById('meta').innerHTML =
  `<span class="k">designed for</span> <b class="g">${M.thrust} N</b> thrust @ ${M.rpm} rpm<br>`+
  `<span class="k">radius</span> <b>${M.R} mm</b> &middot; <span class="k">chord</span> <b>${M.chord_root}&rarr;${M.chord_tip} mm</b><br>`+
  `<span class="k">twist</span> <b>${M.tw_root}&deg;&rarr;${M.tw_tip}&deg;</b> (washout) &middot; <span class="k">${M.n} triangles</span>`;
loop();
</script>
"""


if __name__ == "__main__":
    geom = BD.design_iterate(20.0, rpm=9800, R_tip=0.165, n_blades=2, N=16)
    tris = build_mesh(geom, n_blades=2, M=12)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build_blade")
    os.makedirs(out, exist_ok=True)
    write_stl(tris, os.path.join(out, "propeller.stl"))
    sc = r"C:\Users\LOGAN_SD\AppData\Local\Temp\claude\d--Interceptor-Sim-digital-twin-interceptor-main\b4140022-fc14-43c4-8685-53f67d62184e\scratchpad\blade_model.html"
    write_viewer(tris, geom, sc)
    print(f"propeller: {len(tris)} triangles, forward thrust {geom['thrust_forward']:.1f} N")
    print(f"STL   -> {os.path.relpath(os.path.join(out,'propeller.stl'))}")
    print(f"viewer-> {sc}")
