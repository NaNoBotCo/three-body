#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""find_orbits.py — find the closed three-body orbits instead of copying their numbers.

    python3 tools/find_orbits.py scan      # the map: how close each start comes to closing
    python3 tools/find_orbits.py refine    # Gauss-Newton on every orbit in data/orbits.json

`scan` walks a grid of starting speeds on the Šuvakov–Dmitrašinović line — two bodies at
±1 with the same velocity, the third at the origin with twice it the other way — runs each
one forward and records the closest it ever comes to its own starting state. Valleys in
that map are periodic orbits. `refine` drops Gauss-Newton into a valley: three unknowns
(the two velocity components and the period), twelve residuals (the state at T minus the
state at 0), finite-difference Jacobian, until the orbit closes on itself.

The initial conditions in data/orbits.json are the output of `refine` on this machine, not
numbers read off a paper. Each one carries the distance it closes to."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import physics as P  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ORBITS = ROOT / "data" / "orbits.json"
SCAN = ROOT / "data" / "scan.npz"


def scan(n=200, vmax=0.7, T=40.0, dt=0.004, m=(1.0, 1.0, 1.0)):
    """The return map over starting velocities, computed all at once."""
    vs = np.linspace(0.02, vmax, n)
    VX, VY = np.meshgrid(vs, vs)
    k = VX.size
    mass = np.array(m)
    pos0 = np.zeros((k, 3, 2))
    pos0[:, 0] = (-1.0, 0.0)
    pos0[:, 1] = (1.0, 0.0)
    vel0 = np.zeros((k, 3, 2))
    vel0[:, 0, 0] = vel0[:, 1, 0] = VX.ravel()
    vel0[:, 0, 1] = vel0[:, 1, 1] = VY.ravel()
    vel0[:, 2, 0] = -2 * VX.ravel()
    vel0[:, 2, 1] = -2 * VY.ravel()
    pos, vel = pos0.copy(), vel0.copy()
    best = np.full(k, np.inf)
    at = np.zeros(k)
    steps = int(T / dt)
    a = P.accel_batch(pos, mass)
    t0 = time.time()
    for s in range(steps):
        vel += 0.5 * dt * a
        pos += dt * vel
        a = P.accel_batch(pos, mass)
        vel += 0.5 * dt * a
        t = (s + 1) * dt
        if t < 1.0:
            continue
        d = np.sqrt(((pos - pos0) ** 2).sum((1, 2)) + ((vel - vel0) ** 2).sum((1, 2)))
        hit = d < best
        best[hit] = d[hit]
        at[hit] = t
        if (s + 1) % 2000 == 0:
            print(f"  t={t:5.1f}  {time.time()-t0:5.1f}s  best so far {best.min():.4f}")
    np.savez_compressed(SCAN, vs=vs, best=best.reshape(n, n), at=at.reshape(n, n), T=T, dt=dt)
    print(f"wrote {SCAN} — {n}×{n} starts, {(best < 0.05).sum()} of them come back within 0.05")
    return vs, best.reshape(n, n), at.reshape(n, n)


def residual(p, mass, dt_target=2e-4, kind="sd", fixed=None):
    """state(T) − state(0), the twelve numbers a periodic orbit sends to zero."""
    if kind == "sd":
        s0 = P.sd_state(p[0], p[1])
        T = p[2]
    else:
        s0 = np.asarray(fixed, float).copy()
        s0[6:] = s0[6:] * p[0]
        T = p[1]
    n = max(int(round(T / dt_target)), 200)
    s1, _ = P.yoshida3(s0, T / n, n, m=mass)
    return s1 - s0


def refine_sd(vx, vy, T, mass=(1.0, 1.0, 1.0), iters=12, dt=2e-4, verbose=False):
    p = np.array([vx, vy, T], float)
    r = residual(p, mass, dt)
    best = (np.linalg.norm(r), p.copy())
    for it in range(iters):
        J = np.zeros((12, 3))
        for j in range(3):
            h = 1e-7 * max(abs(p[j]), 1e-3)
            q = p.copy(); q[j] += h
            J[:, j] = (residual(q, mass, dt) - r) / h
        step, *_ = np.linalg.lstsq(J, -r, rcond=None)
        for damp in (1.0, 0.5, 0.25, 0.1):
            q = p + damp * step
            rq = residual(q, mass, dt)
            if np.linalg.norm(rq) < np.linalg.norm(r):
                p, r = q, rq
                break
        else:
            break
        nr = np.linalg.norm(r)
        if verbose:
            print(f"    it{it}: |r|={nr:.3e}  v=({p[0]:.8f},{p[1]:.8f})  T={p[2]:.8f}")
        if nr < best[0]:
            best = (nr, p.copy())
        if nr < 1e-10:
            break
    return best[1], best[0]


def refine_all():
    doc = json.loads(ORBITS.read_text(encoding="utf-8"))
    for o in doc["orbits"]:
        if o.get("family") != "sd":
            continue
        t0 = time.time()
        p, r = refine_sd(o["v"][0], o["v"][1], o["period"], tuple(o["mass"]), verbose=True)
        print(f"{o['id']:<14} |r| {r:.3e}  v=({p[0]:.9f}, {p[1]:.9f})  T={p[2]:.8f}  {time.time()-t0:.1f}s")
        o["v"] = [round(float(p[0]), 9), round(float(p[1]), 9)]
        o["period"] = round(float(p[2]), 8)
        o["closes"] = float(f"{r:.3g}")
    ORBITS.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {ORBITS}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if cmd == "scan":
        scan(n=int(sys.argv[2]) if len(sys.argv) > 2 else 200)
    elif cmd == "refine":
        refine_all()


def valleys(thresh=0.05):
    """Local minima of the scan map — the candidate periodic orbits."""
    d = np.load(SCAN)
    vs, best, at = d["vs"], d["best"], d["at"]
    n = len(vs)
    out = []
    for i in range(1, n - 1):
        for j in range(1, n - 1):
            b = best[i, j]
            if b > thresh:
                continue
            w = best[i - 1:i + 2, j - 1:j + 2]
            if b <= w.min():
                out.append((float(b), float(vs[j]), float(vs[i]), float(at[i, j])))
    out.sort()
    return out


def harvest(thresh=0.05, out_path=None):
    """Refine every valley and keep the ones that close. Writes the list it found."""
    found = []
    cands = valleys(thresh)
    print(f"{len(cands)} valleys under {thresh}")
    for b, vx, vy, T in cands:
        try:
            p, r = refine_sd(vx, vy, T)
        except Exception as e:                       # a valley can sit on a near-collision
            print(f"  ({vx:.4f},{vy:.4f}) T={T:.2f}  failed: {e}")
            continue
        ok = r < 1e-8 and p[2] > 1.0 and abs(p[0]) > 1e-3
        # the same orbit shows up again at two and three times its period, because the
        # scan keeps whichever return was closest — so a start that lands on a known
        # velocity is the same orbit, and the shortest period is the true one
        same = [f for f in found if abs(f["v"][0] - p[0]) < 3e-3 and abs(f["v"][1] - p[1]) < 3e-3]
        dup = bool(same)
        print(f"  ({vx:.4f},{vy:.4f}) scan {b:.4f} T≈{T:5.2f} → v=({p[0]:.7f},{p[1]:.7f}) T={p[2]:.6f} |r|={r:.2e}"
              f"{'  dup' if dup else ''}{'' if ok else '  rejected'}")
        if ok and dup and p[2] < same[0]["period"] - 1e-6:
            # the scan reports whichever return was closest, which is often two or three
            # laps; the shortest period that closes is the orbit's own
            same[0].update(v=[round(float(p[0]), 9), round(float(p[1]), 9)],
                           period=round(float(p[2]), 8), closes=float(f"{r:.3g}"))
        if ok and not dup:
            found.append({"v": [round(float(p[0]), 9), round(float(p[1]), 9)],
                          "period": round(float(p[2]), 8), "closes": float(f"{r:.3g}"),
                          "scan": [round(vx, 5), round(vy, 5), round(b, 5)]})
    p = Path(out_path or ROOT / "data" / "found.json")
    p.write_text(json.dumps({"method": "grid scan then Gauss-Newton, tools/find_orbits.py",
                             "threshold": thresh, "orbits": found}, indent=1) + "\n", encoding="utf-8")
    print(f"{len(found)} orbits closed to better than 1e-8 → {p}")


def fundamental(v, period, tol=1e-7):
    """The scan keeps whichever return was closest, and that is often two or three laps.
    Try the period divided by 2, 3, 4, 5: the shortest division that still closes is the
    orbit's own period."""
    s0 = P.sd_state(*v)
    for k in (6, 5, 4, 3, 2):
        T = period / k
        if T < 1.0:
            continue
        if P.returns(s0, T, dt=2e-4) < tol:
            return T
    return period


def tidy(path=None):
    p = Path(path or ROOT / "data" / "found.json")
    doc = json.loads(p.read_text(encoding="utf-8"))
    for o in doc["orbits"]:
        T = fundamental(o["v"], o["period"])
        if abs(T - o["period"]) > 1e-9:
            pr, r = refine_sd(o["v"][0], o["v"][1], T)
            print(f"  {o['period']:.5f} → {pr[2]:.6f}  |r|={r:.1e}")
            o["v"] = [round(float(pr[0]), 9), round(float(pr[1]), 9)]
            o["period"] = round(float(pr[2]), 8)
            o["closes"] = float(f"{r:.3g}")
    doc["orbits"].sort(key=lambda o: o["period"])
    p.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"{len(doc['orbits'])} orbits, shortest period {doc['orbits'][0]['period']:.5f}")
