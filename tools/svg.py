# -*- coding: utf-8 -*-
"""svg.py — the still diagrams. Every one of them is computed at build time from
tools/physics.py, so the figure on the page is the figure the equations give.

Nothing here is drawn by hand and nothing is traced from a source. Where a diagram
carries a number — the Lyapunov time, the position of L1, the energy drift — that number
came out of a run made while the page was being built."""
from __future__ import annotations

import html
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import physics as P  # noqa: E402

E = html.escape
ERA = {"law": "var(--e-law)", "shapes": "var(--e-shapes)", "proof": "var(--e-proof)",
       "step": "var(--e-step)", "found": "var(--e-found)", "sky": "var(--e-sky)"}
ERA_NAME = {"law": "the law", "shapes": "exact shapes", "proof": "what cannot be done",
            "step": "stepping it", "found": "finding orbits", "sky": "out there"}
COL = ("var(--teal)", "var(--gold)", "var(--violet)")


def _p(pts, close=False):
    d = " ".join(f'{"M" if i == 0 else "L"}{x:.2f} {y:.2f}' for i, (x, y) in enumerate(pts))
    return d + (" Z" if close else "")


# ------------------------------------------------------------------ the timeline strip
def strip(events, w=1000, h=150):
    y0, y1 = 1680, 2035
    def x(y): return 42 + (y - y0) / (y1 - y0) * (w - 62)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="three-body events by year, 1687 to now">']
    out.append(f'<line x1="{x(y0)}" y1="84" x2="{x(y1)}" y2="84" stroke="var(--mute)" stroke-width="2"/>')
    for y in range(1700, 2001, 50):
        out.append(f'<line x1="{x(y):.1f}" y1="78" x2="{x(y):.1f}" y2="90" stroke="var(--mute)"/>'
                   f'<text x="{x(y):.1f}" y="108" text-anchor="middle" font-size="12" fill="var(--mute)">{y}</text>')
    seen: dict[int, int] = {}
    for e in events:
        d = int(e["year"] / 12)
        n = seen.get(d, 0); seen[d] = n + 1
        cy = 70 - n * 14
        out.append(f'<circle cx="{x(e["year"]):.1f}" cy="{cy}" r="6.5" fill="{ERA.get(e["era"], "var(--teal)")}" '
                   f'stroke="var(--bg)" stroke-width="1.5"><title>{e["year"]} — {E(e["title"])}</title></circle>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ an orbit, drawn
def orbit_svg(state, period, w=300, h=200, laps=1.0, mass=(1.0, 1.0, 1.0), dots=True, pad=1.14):
    """The three tracks of one orbit, as three SVG paths. Integrated here, at build."""
    st = np.asarray(state, float)
    n = max(int(period * laps / 3e-4), 2000)    # fine enough that a close pass draws true
    _, tr = P.yoshida3(st, period * laps / n, n, m=tuple(mass), keep=max(n // 1400, 1))
    tr = np.asarray(tr).reshape(-1, 3, 2)
    if not len(tr):
        return ""
    lim = np.abs(tr).max() * pad or 1.0
    sc = min(w, h) / (2 * lim)
    def T(p): return (w / 2 + p[0] * sc, h / 2 - p[1] * sc)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="three-body orbit">']
    for i in range(3):
        out.append(f'<path d="{_p([T(p) for p in tr[:, i, :]])}" fill="none" stroke="{COL[i]}" '
                   f'stroke-width="1.6" stroke-linecap="round" opacity=".92"/>')
    if dots:
        for i in range(3):
            cx, cy = T(tr[0, i])
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="{COL[i]}" stroke="var(--panel)" stroke-width="1.5"/>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ the shape sphere
def hopf(tr):
    """Configurations → points on the shape sphere. Equal masses, Jacobi coordinates."""
    r1, r2, r3 = tr[:, 0, :], tr[:, 1, :], tr[:, 2, :]
    rho = (r2 - r1) / math.sqrt(2)
    sig = (2 * r3 - r1 - r2) / math.sqrt(6)
    R2 = (rho ** 2).sum(1) + (sig ** 2).sum(1)
    w1 = 2 * (rho * sig).sum(1)
    w2 = (rho ** 2).sum(1) - (sig ** 2).sum(1)
    w3 = 2 * (rho[:, 0] * sig[:, 1] - rho[:, 1] * sig[:, 0])
    return np.stack([w1, w2, w3], 1) / R2[:, None]


def shape_sphere(state, period, w=560, h=420, tilt=0.42):
    """The figure eight as a closed curve on the sphere of triangle shapes."""
    st = np.asarray(state, float)
    n = 40000
    _, tr = P.yoshida3(st, period / n, n, keep=20)
    pts = hopf(np.asarray(tr).reshape(-1, 3, 2))
    R = min(w, h) * 0.42
    cx, cy = w / 2, h / 2
    st_, ct = math.sin(tilt), math.cos(tilt)

    def proj(v):
        x, y, z = v
        # look from above the equator by `tilt`, with w2 across and w3 up
        return (cx + x * R * 0.98, cy - (z * ct - y * st_) * R, (y * ct + z * st_))

    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="the figure-eight orbit drawn on the shape sphere">']
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{R:.1f}" fill="var(--chip)" stroke="var(--line)" stroke-width="1.5"/>')
    # the equator: collinear shapes
    eq = [proj((math.sin(a), math.cos(a), 0.0)) for a in np.linspace(0, 2 * math.pi, 181)]
    out.append(f'<path d="{_p([(p[0], p[1]) for p in eq], True)}" fill="none" stroke="var(--mute)" stroke-width="1.4" stroke-dasharray="4 4"/>')
    # the orbit's own curve on the sphere
    proj_pts = [proj(v) for v in pts]
    out.append(f'<path d="{_p([(q[0], q[1]) for q in proj_pts], True)}" fill="none" stroke="var(--teal)" stroke-width="2.6" opacity=".95"/>')
    # the three two-body collisions, 120° apart on the equator, and the two triangles at the poles
    for ang, lab in ((0, "2 and 3 together"), (2 * math.pi / 3, "1 and 2 together"), (4 * math.pi / 3, "1 and 3 together")):
        v = (math.sin(ang + math.pi / 2), math.cos(ang + math.pi / 2), 0.0)
        px, py, _ = proj(v)
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="var(--red)"><title>{E(lab)}</title></circle>')
    for z, lab in ((1, "equilateral, one way round"), (-1, "equilateral, the other way")):
        px, py, _ = proj((0.0, 0.0, z))
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="var(--gold)"><title>{E(lab)}</title></circle>')
    out.append(f'<text x="{cx:.0f}" y="{cy - R - 8:.0f}" text-anchor="middle" font-size="12" fill="var(--mute)">equilateral triangle</text>')
    out.append(f'<text x="{cx:.0f}" y="{cy + R + 20:.0f}" text-anchor="middle" font-size="12" fill="var(--mute)">the other equilateral triangle</text>')
    out.append(f'<text x="{cx + R * 0.99:.0f}" y="{cy + 20:.0f}" text-anchor="end" font-size="12" fill="var(--red)">collisions sit on this circle</text>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ the five points
def lagrange_svg(mu=0.2, w=620, h=420):
    from draw import lagrange_points
    pts = lagrange_points(mu)
    R = min(w, h) * 0.30
    cx, cy = w / 2, h / 2 + 10
    def T(x, y): return (cx + x * R, cy - y * R)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="the five Lagrange points of a two-body system">']
    out.append(f'<line x1="{T(-2.1,0)[0]:.0f}" y1="{cy:.0f}" x2="{T(2.1,0)[0]:.0f}" y2="{cy:.0f}" stroke="var(--line)"/>')
    ox, oy = T(0.5 - mu, 0)
    out.append(f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="{R * (0.5):.1f}" fill="none" stroke="var(--line)" stroke-dasharray="3 5"/>')
    for (x, y), lab, col in zip(pts, ("L1", "L2", "L3", "L4", "L5"), ("var(--violet)",) * 3 + ("var(--red)",) * 2):
        px, py = T(x, y)
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="{col}"/>'
                   f'<text x="{px:.1f}" y="{py - 13:.1f}" text-anchor="middle" font-size="13" font-weight="700" fill="{col}">{lab}</text>')
    for x, r, lab, col in ((-mu, 16, "the heavy one", "var(--gold)"), (1 - mu, 10, "the light one", "var(--teal)")):
        px, py = T(x, 0)
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="{col}" stroke="var(--ink)" stroke-width="1.5"/>'
                   f'<text x="{px:.1f}" y="{py + r + 17:.1f}" text-anchor="middle" font-size="12" fill="var(--mute)">{E(lab)}</text>')
    # the triangles
    for s in (1, -1):
        a, b = T(-mu, 0), T(1 - mu, 0)
        c = T(0.5 - mu, s * math.sqrt(3) / 2)
        out.append(f'<path d="{_p([a, c, b], False)}" fill="none" stroke="var(--red)" stroke-width="1.2" stroke-dasharray="5 4" opacity=".7"/>')
    out.append(f'<text x="{w-10}" y="{h-8}" text-anchor="end" font-size="12" fill="var(--mute)">mass ratio μ = {mu:g}, '
               f'L1 at x = {pts[0][0]:.4f}, L2 at {pts[1][0]:.4f}, L3 at {pts[2][0]:.4f}</text>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ the quintic, hunted
def quintic_svg(mu, w=620, h=300):
    """The fifth-degree equation whose root is L1, drawn with the root marked."""
    def f(r):
        return r ** 5 - (3 - mu) * r ** 4 + (3 - 2 * mu) * r ** 3 - mu * r ** 2 + 2 * mu * r - mu
    xs = np.linspace(0.005, 1.0, 600)
    ys = np.array([f(x) for x in xs])
    lo, hi = 0.005, 1.0
    for _ in range(200):
        m = 0.5 * (lo + hi)
        if (f(m) > 0) == (f(lo) > 0):
            lo = m
        else:
            hi = m
    root = 0.5 * (lo + hi)
    ymax = max(abs(ys.min()), abs(ys.max()))
    def X(x): return 54 + (x - 0) / 1.0 * (w - 74)
    def Y(y): return h / 2 - y / ymax * (h / 2 - 26)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="the quintic whose root gives L1">']
    out.append(f'<line x1="54" y1="{Y(0):.1f}" x2="{w-20}" y2="{Y(0):.1f}" stroke="var(--mute)"/>')
    out.append(f'<path d="{_p([(X(x), Y(y)) for x, y in zip(xs, ys)])}" fill="none" stroke="var(--teal)" stroke-width="2.6"/>')
    out.append(f'<circle cx="{X(root):.1f}" cy="{Y(0):.1f}" r="7" fill="var(--gold)" stroke="var(--ink)" stroke-width="1.5"/>')
    out.append(f'<text x="{X(root):.1f}" y="{Y(0) - 16:.1f}" text-anchor="middle" font-size="13" font-weight="700" fill="var(--gold)">r = {root:.6f}</text>')
    for x in (0.2, 0.4, 0.6, 0.8, 1.0):
        out.append(f'<text x="{X(x):.1f}" y="{h-6}" text-anchor="middle" font-size="11" fill="var(--mute)">{x:g}</text>')
    out.append(f'<text x="8" y="20" font-size="12" fill="var(--mute)">value of the quintic</text>')
    out.append(f'<text x="{w-20}" y="{Y(0)-8:.0f}" text-anchor="end" font-size="12" fill="var(--mute)">distance from the small body</text>')
    out.append("</svg>")
    return "".join(out), root


# ------------------------------------------------------------------ divergence, measured
def divergence_svg(w=640, h=340, nudges=(1e-4, 1e-7, 1e-10, 1e-13), T=40.0):
    """Gap against time for the same start at four different nudges, log scale."""
    base = P.sd_state(0.28, 0.45)
    mass = np.array([1.0, 1.0, 1.0])
    dt, every = 1e-3, 20
    series, tau = [], []
    for nud in nudges:
        pos = np.tile(np.array(base[:6]).reshape(1, 3, 2), (2, 1, 1))
        vel = np.tile(np.array(base[6:]).reshape(1, 3, 2), (2, 1, 1))
        pos[1, 0, 0] += nud
        tr, _, _ = P.leapfrog_batch(pos, vel, mass, dt, int(T / dt), every=every)
        gap = np.sqrt(((tr[:, 0] - tr[:, 1]) ** 2).sum((1, 2)))
        ts = np.arange(1, len(gap) + 1) * dt * every
        series.append((ts, np.maximum(gap, 1e-18)))
        m = (gap > nud * 10) & (gap < 0.3)
        if m.sum() > 8:
            sl = np.polyfit(ts[m], np.log(gap[m]), 1)[0]
            tau.append(1 / sl if sl > 0 else np.nan)
    def X(t): return 58 + t / T * (w - 78)
    def Y(g): return h - 40 - (math.log10(max(g, 1e-18)) + 18) / 19 * (h - 66)
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="the gap between two nearly identical starts, against time">']
    for p in range(-18, 1, 3):
        out.append(f'<line x1="58" y1="{Y(10.0**p):.1f}" x2="{w-20}" y2="{Y(10.0**p):.1f}" stroke="var(--line)"/>'
                   f'<text x="52" y="{Y(10.0**p)+4:.1f}" text-anchor="end" font-size="11" fill="var(--mute)">10<tspan font-size="8" dy="-4">{p}</tspan></text>')
    cols = ("var(--red)", "var(--gold)", "var(--teal)", "var(--violet)")
    for (ts, gap), c, nud in zip(series, cols, nudges):
        out.append(f'<path d="{_p([(X(t), Y(g)) for t, g in zip(ts, gap)])}" fill="none" stroke="{c}" stroke-width="2.2" opacity=".95">'
                   f'<title>nudge {nud:g}</title></path>')
    for t in range(0, int(T) + 1, 10):
        out.append(f'<text x="{X(t):.1f}" y="{h-18}" text-anchor="middle" font-size="11" fill="var(--mute)">{t}</text>')
    out.append(f'<text x="{w-20}" y="{h-4}" text-anchor="end" font-size="11" fill="var(--mute)">time</text>')
    out.append("</svg>")
    good = [t for t in tau if t == t]
    return "".join(out), (float(np.mean(good)) if good else float("nan"))


# ------------------------------------------------------------------ energy drift
def drift_svg(w=640, h=320, T=60.0):
    """What each stepper does to a quantity that cannot change."""
    st, _ = _eight()
    pos = np.array(st[:6]).reshape(3, 2)
    vel = np.array(st[6:]).reshape(3, 2)
    mass = np.array([1.0, 1.0, 1.0])
    E0 = P.energy(pos, vel, mass)
    dt = 2e-3
    n = int(T / dt)
    out_series = {}
    # Euler, by hand: it is not in physics.py because nothing on the site should use it
    p, v = pos.copy(), vel.copy()
    es, ts = [], []
    for s in range(n):
        a = P.accel(p, mass)
        p = p + dt * v
        v = v + dt * a
        if s % 60 == 0:
            es.append(abs(P.energy(p, v, mass) - E0) / abs(E0)); ts.append(s * dt)
    out_series["Euler"] = (ts, es, "var(--red)")
    p, v, a = pos.copy(), vel.copy(), P.accel(pos, mass)
    es, ts = [], []
    for s in range(n):
        v += 0.5 * dt * a
        p += dt * v
        a = P.accel(p, mass)
        v += 0.5 * dt * a
        if s % 60 == 0:
            es.append(abs(P.energy(p, v, mass) - E0) / abs(E0)); ts.append(s * dt)
    out_series["leapfrog"] = (ts, es, "var(--teal)")
    def X(t): return 62 + t / T * (w - 82)
    def Y(e): return h - 38 - (math.log10(max(e, 1e-16)) + 16) / 16 * (h - 60)
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="energy error against time for two stepping methods">']
    for p_ in range(-16, 1, 2):
        o.append(f'<line x1="62" y1="{Y(10.0**p_):.1f}" x2="{w-20}" y2="{Y(10.0**p_):.1f}" stroke="var(--line)"/>'
                 f'<text x="56" y="{Y(10.0**p_)+4:.1f}" text-anchor="end" font-size="11" fill="var(--mute)">10<tspan font-size="8" dy="-4">{p_}</tspan></text>')
    last = {}
    for name, (ts, es, c) in out_series.items():
        o.append(f'<path d="{_p([(X(t), Y(e)) for t, e in zip(ts, es)])}" fill="none" stroke="{c}" stroke-width="2.4"/>')
        o.append(f'<text x="{X(ts[-1]) - 6:.1f}" y="{Y(es[-1]) - 8:.1f}" text-anchor="end" font-size="13" font-weight="700" fill="{c}">{name}</text>')
        last[name] = es[-1]
    for t in range(0, int(T) + 1, 10):
        o.append(f'<text x="{X(t):.1f}" y="{h-16}" text-anchor="middle" font-size="11" fill="var(--mute)">{t}</text>')
    o.append(f'<text x="8" y="18" font-size="12" fill="var(--mute)">energy error, as a fraction</text>')
    o.append("</svg>")
    return "".join(o), last


def _eight():
    import json
    d = json.loads((Path(__file__).resolve().parent.parent / "data" / "orbits.json").read_text(encoding="utf-8"))
    for o in d["orbits"]:
        if o["id"] == "figure-eight":
            return P.sd_state(*o["v"]), o["period"]
    raise SystemExit("data/orbits.json has no figure-eight row")


# ------------------------------------------------------------------ what usually happens
def outcomes(n=800, T=60.0, seed=11, soft=0.05, dt=1e-3, audit=150):
    """Run n random triples and count how they ended.


    Two choices worth saying out loud. The bottom of each well is rounded off at `soft`,
    because at a fixed step a near-collision throws a body across the sky and the answer
    you get is the stepper's, not the physics'. And the whole thing is run again at a
    third of the step on a smaller sample, to see whether the percentage moves."""
    def sample(k, rng):
        pos = rng.uniform(-1, 1, (k, 3, 2))
        vel = rng.uniform(-0.4, 0.4, (k, 3, 2))
        pos -= pos.mean(1, keepdims=True)
        vel -= vel.mean(1, keepdims=True)
        d = np.linalg.norm(pos[:, None, :, :] - pos[:, :, None, :], axis=-1)
        iu = np.triu_indices(3, 1)
        keep = d[:, iu[0], iu[1]].min(1) > 0.4
        return pos[keep], vel[keep]

    mass = np.array([1.0, 1.0, 1.0])
    iu = np.triu_indices(3, 1)

    def run(pos, vel, h):
        def en(p, v):
            ke = 0.5 * (v ** 2).sum((1, 2))
            dd = np.sqrt(((p[:, None, :, :] - p[:, :, None, :]) ** 2).sum(-1) + soft ** 2)
            return ke - (1 / dd[:, iu[0], iu[1]]).sum(1)
        e0 = en(pos, vel)
        p, v = pos.copy(), vel.copy()
        a = P.accel_batch_soft(p, mass, soft)
        gone = np.full(len(p), np.nan)
        for s_ in range(int(T / h)):
            v += 0.5 * h * a
            p += h * v
            a = P.accel_batch_soft(p, mass, soft)
            v += 0.5 * h * a
            if s_ % max(int(0.2 / h), 1) == 0:
                far = np.linalg.norm(p, axis=2).max(1)
                just = np.isnan(gone) & (far > 12.0)
                gone[just] = (s_ + 1) * h
        return gone, np.abs((en(p, v) - e0) / e0)

    rng = np.random.default_rng(seed)
    pos, vel = sample(n, rng)
    gone, drift = run(pos, vel, dt)
    t = gone[np.isfinite(gone)]
    res = {"n": int(len(pos)), "ejected": int(np.isfinite(gone).sum()),
           "together": int(np.isnan(gone).sum()), "T": T, "soft": soft, "dt": dt,
           "drift": float(np.median(drift)), "drift_max": float(drift.max()),
           "t_median": float(np.median(t)) if len(t) else float("nan"),
           "t_quick": float(np.percentile(t, 10)) if len(t) else float("nan"),
           "t_slow": float(np.percentile(t, 90)) if len(t) else float("nan"),
           "times": t}
    if audit:
        # the same starts again at a third of the step: if the answer is the stepper's
        # rather than the physics', this is where it shows
        ga, da = run(pos[:audit], vel[:audit], dt / 3)
        res["audit"] = {"n": int(min(audit, len(pos))), "dt": dt / 3,
                        "share": float(np.isfinite(ga).mean()),
                        "share_coarse": float(np.isfinite(gone[:audit]).mean()),
                        "agree": float((np.isfinite(ga) == np.isfinite(gone[:audit])).mean()),
                        "drift": float(np.median(da))}
    res["share"] = res["ejected"] / max(res["n"], 1)
    return res


def outcome_svg(res, w=640, h=260):
    t = res["times"]
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="how long the three stayed together before one left">']
    if len(t):
        bins = np.linspace(0, res["T"], 31)
        cnt, _ = np.histogram(t, bins)
        mx = cnt.max() or 1
        bw = (w - 80) / len(cnt)
        for i, c in enumerate(cnt):
            hh = c / mx * (h - 70)
            o.append(f'<rect x="{62 + i*bw:.1f}" y="{h - 40 - hh:.1f}" width="{bw-2:.1f}" height="{hh:.1f}" fill="var(--teal)" opacity=".9">'
                     f'<title>{int(c)} of them left between {bins[i]:.0f} and {bins[i+1]:.0f}</title></rect>')
        for k in range(0, int(res["T"]) + 1, 10):
            o.append(f'<text x="{62 + k/res["T"]*(w-80):.1f}" y="{h-18}" text-anchor="middle" font-size="11" fill="var(--mute)">{k}</text>')
        o.append(f'<text x="8" y="18" font-size="12" fill="var(--mute)">how many left, per slice of time</text>')
        o.append(f'<text x="{w-20}" y="{h-4}" text-anchor="end" font-size="11" fill="var(--mute)">time units</text>')
    o.append("</svg>")
    return "".join(o)


# ------------------------------------------------------------------ the bookkeeping
def ledger_svg(w=640, h=210):
    rows = [("18 numbers to track", 18, "var(--mute)", "three bodies, three coordinates and three speeds each"),
            ("10 of them pinned by conservation", 10, "var(--teal)", "momentum 3 · balance point 3 · energy 1 · spin 3"),
            ("8 left", 8, "var(--gold)", "and no further conserved quantity of the usable kind exists"),
            ("6 after the clock and the compass", 6, "var(--red)", "slide the start time, turn the whole picture")]
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="eighteen numbers reduced to six">']
    for i, (lab, k, col, sub) in enumerate(rows):
        y = 26 + i * 46
        for j in range(18):
            fill = col if j < k else "var(--line)"
            o.append(f'<rect x="{300 + j*18}" y="{y-12}" width="14" height="18" rx="3" fill="{fill}"/>')
        o.append(f'<text x="290" y="{y+2}" text-anchor="end" font-size="13" font-weight="700" fill="var(--ink)">{E(lab)}</text>')
        o.append(f'<text x="300" y="{y+22}" font-size="11" fill="var(--mute)">{E(sub)}</text>')
    o.append("</svg>")
    return "".join(o)
