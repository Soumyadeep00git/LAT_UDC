r"""ArduPilot SITL <-> our FDM bridge (SIM_JSON protocol).

ArduPilot's JSON SITL backend exchanges over UDP:
  SITL -> FDM : struct { uint16 magic=18458; uint16 frame_rate; uint32 frame_count; uint16 pwm[16]; }
  FDM  -> SITL: JSON {timestamp, imu:{gyro[3], accel_body[3]}, position[NED], quaternion[w,x,y,z], velocity[NED]}

Running `arducopter --model JSON:<host>` then makes ArduCopter's REAL controller fly OUR specimen (fdm.py).
Because SITL runs in WSL and our physics stack is Python, run THIS bridge inside WSL (colocated on
127.0.0.1:9002) to avoid WSL<->Windows UDP namespace issues.

`python fdm_json.py --selftest` verifies the protocol + integration over local loopback WITHOUT SITL:
a client injects hover PWM, and the FDM must hover — proving encode/decode/step/reply before we wire the
live autopilot.
"""
from __future__ import annotations

import json
import os
import socket
import struct
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fdm import FDM

MAGIC = 18458
SERVO_FMT = "<HHI16H"                 # magic, frame_rate, frame_count, pwm[16]  = 40 bytes
SERVO_SIZE = struct.calcsize(SERVO_FMT)
PORT = 9002

# ArduCopter QuadX motor order (M1 FR, M2 BL, M3 FL, M4 BR) -> our motor indices (ang 45,135,225,315)
QUADX_MAP = [0, 2, 3, 1]


class JSONBridge:
    def __init__(self, cfg, cda=0.0115, port=PORT):
        self.fdm = FDM(cfg, CdA=cda)
        self.port = port
        self.frames = 0
        self.running = False

    def _reply(self):
        gyro, acc = self.fdm.imu()
        return (json.dumps({
            "timestamp": self.fdm.t,
            "imu": {"gyro": [float(x) for x in gyro], "accel_body": [float(x) for x in acc]},
            "position": [float(x) for x in self.fdm.pos_ned],
            "quaternion": [float(x) for x in self.fdm.q],
            "velocity": [float(x) for x in self.fdm.vel_ned],
        }) + "\n").encode()

    def serve(self, max_frames=None, max_seconds=None):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", self.port))
        s.settimeout(2.0)
        self.running = True
        self.fdm.reset()
        t0 = time.time()
        while self.running:
            try:
                data, addr = s.recvfrom(1024)
            except socket.timeout:
                break
            if len(data) < SERVO_SIZE:
                continue
            fields = struct.unpack(SERVO_FMT, data[:SERVO_SIZE])
            magic, frame_rate, _fcount = fields[0], fields[1], fields[2]
            if magic != MAGIC:
                continue
            pwm = fields[3:3 + 16]
            u_ap = [max(0.0, min(1.0, (pwm[i] - 1000) / 1000.0)) for i in range(4)]
            u = [0.0] * self.fdm.n
            for ap_i, our_i in enumerate(QUADX_MAP):
                u[our_i] = u_ap[ap_i]
            dt = 1.0 / max(frame_rate, 1)
            self.fdm.step(u, dt)
            s.sendto(self._reply(), addr)
            self.frames += 1
            if max_frames and self.frames >= max_frames:
                break
            if max_seconds and (time.time() - t0) > max_seconds:
                break
        s.close()
        self.running = False


def _selftest():
    cfg = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
               C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)
    br = JSONBridge(cfg)
    uh = br.fdm.hover_throttle()
    pwm_h = int(1000 + uh * 1000)
    frame_rate = 400
    N = 800

    th = threading.Thread(target=br.serve, kwargs={"max_frames": N, "max_seconds": 10}, daemon=True)
    th.start()
    time.sleep(0.3)

    cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cli.settimeout(2.0)
    pkt = struct.pack(SERVO_FMT, MAGIC, frame_rate, 0, *([pwm_h] * 4 + [0] * 12))
    got = 0
    for i in range(N):
        cli.sendto(pkt, ("127.0.0.1", PORT))
        try:
            resp, _ = cli.recvfrom(2048)
            got += 1
            last = json.loads(resp.decode().strip())
        except socket.timeout:
            break
    br.running = False
    th.join(timeout=2)

    alt = -br.fdm.pos_ned[2]
    r, p, y = br.fdm.euler_deg()
    print(f"bridge: exchanged {got}/{N} JSON frames over UDP  (hover PWM {pwm_h})")
    print(f"  reply keys: {sorted(last.keys())}")
    print(f"  after {br.fdm.t:.2f}s sim: altitude {alt:+.3f} m | roll {r:+.2f} pitch {p:+.2f} deg | "
          f"vz {-br.fdm.vel_ned[2]:+.3f} m/s")
    ok = got > N * 0.9 and abs(alt) < 0.4 and abs(r) < 1 and abs(p) < 1
    print("  PROTOCOL+INTEGRATION:", "OK — hovers under SIM_JSON packets" if ok else "CHECK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        cfg = dict(D_in=15, pitch_in=8, Kv=340, I_max=45, S=6, cap_mAh=8000,
                   C_rate=25, L_arm=0.33, payload=0.8, n_rotors=4)
        print(f"FDM JSON backend listening on :{PORT}  (launch: arducopter --model JSON:<host>)")
        JSONBridge(cfg).serve(max_seconds=600)
