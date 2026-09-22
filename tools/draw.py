#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""draw.py — the pictures, computed from the equations. No photographs, no stock.

Every raster on this site is three bodies actually being moved by tools/physics.py:

    hero.jpg        a chaotic triple, 40 time units of it, trails and all
    band-eight.jpg  the figure-eight orbit, one body's colour per track
    band-fan.jpg    240 starts a millionth apart, agreeing and then spraying
    band-map.jpg    the return map: how close each starting speed comes to closing
    band-well.jpg   the rotating-frame surface, shaded, with the five flat spots
    card.jpg        the share card, 1200×630

    python3 tools/draw.py           # all of them, into build/img/
    python3 tools/draw.py hero      # one
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import physics as P  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "img"
DATA = ROOT / "data"

NAVY = np.array([0.025, 0.045, 0.10])
TEAL = np.array([0.10, 0.72, 0.70])
GOLD = np.array([1.00, 0.76, 0.28])
VIOLET = np.array([0.64, 0.42, 0.96])
RED = np.array([1.00, 0.36, 0.32])
WHITE = np.array([0.98, 0.97, 0.94])
BODY = (TEAL, GOLD, VIOLET)


def save(img, name, quality=86):
    OUT.mkdir(parents=True, exist_ok=True)
    arr = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(arr).save(OUT / name, quality=quality, optimize=True, progressive=True)
    print(f"  {name}  {arr.shape[1]}×{arr.shape[0]}")


def vignette(w, h, strength=0.5):
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))
    return 1 - strength * np.clip(r - 0.35, 0, 1) ** 1.6


def blur(a, radius):
    """Gaussian blur of a single float plane, via PIL so nothing else is needed."""
    m = float(a.max()) or 1.0
    im = Image.fromarray((np.clip(a / m, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0 * m


def splat(track, w, h, extent, thick=1.6, gain=1.0):
    """Lay a path down as light. track (n,2) in physics units → a (h,w) plane."""
    x0, x1, y0, y1 = extent
    dens = np.zeros((h, w), np.float32)
    px = (track[:, 0] - x0) / (x1 - x0) * (w - 1)
    py = (y1 - track[:, 1]) / (y1 - y0) * (h - 1)
    ok = np.isfinite(px) & np.isfinite(py) & (px >= 0) & (px < w - 1) & (py >= 0) & (py < h - 1)
    px, py = px[ok], py[ok]
    ix, iy = px.astype(int), py.astype(int)
    fx, fy = px - ix, py - iy
    for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                        (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(dens, (iy + dy, ix + dx), wgt)
    return blur(dens, thick) * gain


def ink(img, dens, colour, core=1.0, halo=0.35, halo_r=9):
    """Add a trail to the picture: a bright core and a soft glow around it."""
    d = np.clip(dens, 0, 1.6)
    img += d[..., None] * np.asarray(colour) * core
    img += blur(d, halo_r)[..., None] * np.asarray(colour) * halo
    return img


def orbit(state, T, dt=1e-3, mass=(1.0, 1.0, 1.0)):
    """Run one three-body start and hand back the three tracks."""
    pos = np.array(state[:6], float).reshape(3, 2)
    vel = np.array(state[6:], float).reshape(3, 2)
    n = int(T / dt)
    track, _, _ = P.leapfrog(pos, vel, np.array(mass), dt, n, every=1)
    return track                                            # (n+1, 3, 2)


EIGHT = np.array([0.97000436, -0.24308753, -0.97000436, 0.24308753, 0.0, 0.0,
                  0.466203685, 0.43236573, 0.466203685, 0.43236573, -0.93240737, -0.86473146])


def eight_state():
    """From data/orbits.json if it is there — the refined numbers — else the classic ones."""
    try:
        import json
        d = json.loads((DATA / "orbits.json").read_text(encoding="utf-8"))
        for o in d["orbits"]:
            if o["id"] == "figure-eight":
                return np.array(P.sd_state(*o["v"])), o["period"]
    except Exception:
        pass
    return EIGHT, 6.32591398


# ------------------------------------------------------------------ hero: a chaotic triple
def hero(w=2000, h=1000):
    """Three bodies from an ordinary start, going nowhere in particular, for 60 time units."""
    # an ordinary start: the three mill about for thirty time units, and then one of
    # them leaves for good and the other two are left tighter than they began
    st = P.sd_state(0.28, 0.45)
    pos = np.array(st[:6]).reshape(3, 2)
    vel = np.array(st[6:]).reshape(3, 2)
    track, _, _ = P.leapfrog(pos, vel, np.array([1.0, 1.0, 1.0]), 5e-4, 90000, every=3)
    img = np.tile(NAVY.astype(np.float32), (h, w, 1))
    span = 3.6
    cx, cy = np.median(track[:len(track) // 2].reshape(-1, 2), axis=0)
    cx += span * w / h * 0.16                                # room on the right for the one that leaves
    ext = (cx - span * w / h * 0.5, cx + span * w / h * 0.5, cy - span / 2, cy + span / 2)
    for i in range(3):
        img = ink(img, splat(track[:, i, :], w, h, ext, thick=1.6, gain=0.22), BODY[i], core=1.0, halo=0.6, halo_r=20)
    # where they are at the end
    for i in range(3):
        x, y = track[-1, i]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx = (x - ext[0]) / (ext[1] - ext[0]) * w
        cy = (ext[3] - y) / (ext[3] - ext[2]) * h
        r2 = (xx - cx) ** 2 + (yy - cy) ** 2
        img += np.exp(-r2 / (2 * 7 ** 2))[..., None] * WHITE * 1.5
        img += np.exp(-r2 / (2 * 34 ** 2))[..., None] * BODY[i] * 0.5
    img *= vignette(w, h, 0.45)[..., None]
    return img


# ------------------------------------------------------------------ the figure eight
def eight(w=2000, h=900):
    st, T = eight_state()
    pos = np.array(st[:6]).reshape(3, 2)
    vel = np.array(st[6:]).reshape(3, 2)
    n = int(T * 3 / 4e-4)
    track, _, _ = P.leapfrog(pos, vel, np.array([1.0, 1.0, 1.0]), 4e-4, n, every=3)
    img = np.tile(NAVY.astype(np.float32) * 0.9, (h, w, 1))
    ext = (-2.3 * w / h * 0.5, 2.3 * w / h * 0.5, -1.15, 1.15)
    for i in range(3):
        img = ink(img, splat(track[:, i, :], w, h, ext, thick=2.6, gain=0.20), BODY[i], core=0.9, halo=0.7, halo_r=24)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for i in range(3):
        x, y = track[len(track) // 3, i]
        cx = (x - ext[0]) / (ext[1] - ext[0]) * w
        cy = (ext[3] - y) / (ext[3] - ext[2]) * h
        r2 = (xx - cx) ** 2 + (yy - cy) ** 2
        img += np.exp(-r2 / (2 * 9 ** 2))[..., None] * WHITE * 1.6
        img += np.exp(-r2 / (2 * 46 ** 2))[..., None] * BODY[i] * 0.45
    img *= vignette(w, h, 0.45)[..., None]
    return img


# ------------------------------------------------------------------ the divergence fan
def fan(w=2000, h=900, k=240):
    """One start, k copies, each nudged by a millionth. They agree, and then they do not."""
    rng = np.random.default_rng(7)
    st = P.sd_state(0.3671, 0.5327)
    pos = np.tile(np.array(st[:6]).reshape(1, 3, 2), (k, 1, 1))
    vel = np.tile(np.array(st[6:]).reshape(1, 3, 2), (k, 1, 1))
    pos[1:] += rng.normal(0, 1e-6, (k - 1, 3, 2))
    mass = np.array([1.0, 1.0, 1.0])
    track, _, _ = P.leapfrog_batch(pos, vel, mass, 1e-3, 40000, every=5)   # (m,k,3,2)
    img = np.tile(NAVY.astype(np.float32) * 0.85, (h, w, 1))
    ext = (-2.4 * w / h * 0.5, 2.4 * w / h * 0.5, -1.2, 1.2)
    m = track.shape[0]
    early, late = track[: m // 3], track[m // 3:]
    for i in range(3):
        img = ink(img, splat(late[:, :, i, :].reshape(-1, 2), w, h, ext, thick=1.2, gain=0.006), BODY[i], core=0.9, halo=0.40, halo_r=15)
    for i in range(3):
        img = ink(img, splat(early[:, :, i, :].reshape(-1, 2), w, h, ext, thick=1.0, gain=0.012), WHITE, core=0.40, halo=0.14, halo_r=9)
    img *= vignette(w, h, 0.45)[..., None]
    return img


# ------------------------------------------------------------------ the return map
def retmap(w=2000, h=900):
    """The scan: for each starting speed, the closest it came to its own start. Valleys are orbits."""
    f = DATA / "scan.npz"
    if not f.exists():
        print("  band-map.jpg skipped — run tools/find_orbits.py scan first")
        return np.tile(NAVY.astype(np.float32), (h, w, 1))
    d = np.load(f)
    best = np.clip(d["best"], 2e-3, 1.0)
    t = 1 - (np.log10(best) - np.log10(2e-3)) / (np.log10(1.0) - np.log10(2e-3))
    im = Image.fromarray((np.clip(t, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    t = np.asarray(im, dtype=np.float32) / 255.0
    img = np.zeros((h, w, 3), np.float32)
    stops = [(0.0, NAVY * 0.8), (0.45, NAVY + TEAL * 0.10), (0.7, TEAL * 0.8), (0.86, GOLD), (1.0, WHITE)]
    for (p0, c0), (p1, c1) in zip(stops[:-1], stops[1:]):
        m = (t >= p0) & (t <= p1)
        u = ((t - p0) / (p1 - p0))[..., None]
        img[m] = ((1 - u) * c0 + u * c1)[m]
    img += blur(np.clip(t - 0.7, 0, 1), 16)[..., None] * GOLD * 1.4
    img *= vignette(w, h, 0.4)[..., None]
    return img


# ------------------------------------------------------------------ the rotating-frame surface
def omega(x, y, mu):
    r1 = np.hypot(x + mu, y)
    r2 = np.hypot(x - 1 + mu, y)
    return 0.5 * (x ** 2 + y ** 2) + (1 - mu) / np.maximum(r1, 1e-9) + mu / np.maximum(r2, 1e-9)


def well(w=2000, h=900, mu=0.25):
    """The hill-and-valley surface of the rotating frame, shaded as relief, with contours."""
    span = 3.4
    xs = np.linspace(-span * w / h * 0.5 + 0.2, span * w / h * 0.5 + 0.2, w)
    ys = np.linspace(span / 2, -span / 2, h)
    X, Y = np.meshgrid(xs, ys)
    Z = np.clip(omega(X, Y, mu), 0, 4.2)
    # relief: light from the upper left across the surface's own slope
    gy, gx = np.gradient(Z, ys[1] - ys[0], xs[1] - xs[0])
    n = np.dstack([-gx, -gy, np.ones_like(Z) * 6.0])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    lg = np.array([-0.5, 0.55, 0.67]); lg /= np.linalg.norm(lg)
    lam = np.clip((n * lg).sum(2), 0, 1)
    t = np.clip((Z - 1.4) / 1.9, 0, 1)
    img = np.zeros((h, w, 3), np.float32)
    stops = [(0.0, NAVY * 0.75), (0.35, NAVY + TEAL * 0.16), (0.62, TEAL * 0.75), (0.85, GOLD * 0.95), (1.0, WHITE)]
    for (p0, c0), (p1, c1) in zip(stops[:-1], stops[1:]):
        m = (t >= p0) & (t <= p1)
        u = ((t - p0) / (p1 - p0))[..., None]
        img[m] = ((1 - u) * c0 + u * c1)[m]
    img *= (0.45 + 0.85 * lam)[..., None]
    # contour lines of the surface — these are the zero-velocity curves, one per level
    for level in np.arange(1.5, 3.4, 0.11):
        band = np.abs(Z - level) < 0.006
        img[band] += 0.16
    for i, (lx, ly) in enumerate(lagrange_points(mu)):
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx = (lx - xs[0]) / (xs[-1] - xs[0]) * w
        cy = (ys[0] - ly) / (ys[0] - ys[-1]) * h
        r2 = (xx - cx) ** 2 + (yy - cy) ** 2
        col = VIOLET if i < 3 else RED
        img += np.exp(-r2 / (2 * 8 ** 2))[..., None] * WHITE * 1.3
        img += np.exp(-r2 / (2 * 40 ** 2))[..., None] * col * 0.55
    # the outer bowl rises without limit, so fade it rather than let it go white
    img *= np.clip(1.35 - 0.42 * (X ** 2 + Y ** 2), 0.10, 1.0)[..., None]
    img *= vignette(w, h, 0.42)[..., None]
    return img


def lagrange_points(mu):
    """The five of them, from the quintics and the exact triangle, solved by bisection."""
    def dOmega(x):
        r1 = abs(x + mu); r2 = abs(x - 1 + mu)
        return x - (1 - mu) * (x + mu) / r1 ** 3 - mu * (x - 1 + mu) / r2 ** 3

    def root(a, b, n=200):
        fa = dOmega(a)
        for _ in range(n):
            m = 0.5 * (a + b)
            fm = dOmega(m)
            if (fm > 0) == (fa > 0):
                a, fa = m, fm
            else:
                b = m
        return 0.5 * (a + b)

    e = 1e-7
    l2 = root(1 - mu + e, 2.5)
    l1 = root(-mu + e, 1 - mu - e)
    l3 = root(-2.5, -mu - e)
    return [(l1, 0.0), (l2, 0.0), (l3, 0.0), (0.5 - mu, 3 ** 0.5 / 2), (0.5 - mu, -3 ** 0.5 / 2)]


# ------------------------------------------------------------------ the share card
def font(size):
    for p, idx in (("/System/Library/Fonts/Avenir Next Condensed.ttc", 8),
                   ("/System/Library/Fonts/HelveticaNeue.ttc", 1),
                   ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0)):
        if Path(p).exists():
            for i in (idx, 0):
                try:
                    return ImageFont.truetype(p, size, index=i)
                except Exception:
                    continue
    return ImageFont.load_default()


def card(title="The Three-Body Problem", sub="the math, in plain words, with the pictures moving", w=1200, h=630):
    base = hero(w=1200, h=630)
    im = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    scrim = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(scrim)
    for i in range(h // 2, h):
        a = int(205 * ((i - h / 2) / (h / 2)) ** 1.35)
        d.line([(0, i), (w, i)], fill=(4, 7, 18, a))
    im = Image.alpha_composite(im, scrim)
    d = ImageDraw.Draw(im)
    d.text((58, h - 252), title.upper(), font=font(92), fill=(255, 250, 240))
    d.text((62, h - 116), sub, font=font(38), fill=(220, 230, 235))
    d.text((w - 330, h - 58), "nanobotco.github.io", font=font(27), fill=(150, 205, 200))
    OUT.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(OUT / "card.jpg", quality=88, optimize=True)
    print("  card.jpg  1200×630")


PICTURES = {
    "hero": lambda: save(hero(), "hero.jpg"),
    "eight": lambda: save(eight(), "band-eight.jpg"),
    "fan": lambda: save(fan(), "band-fan.jpg"),
    "map": lambda: save(retmap(), "band-map.jpg"),
    "well": lambda: save(well(), "band-well.jpg"),
    "card": card,
}

if __name__ == "__main__":
    for k in (sys.argv[1:] or list(PICTURES)):
        PICTURES[k]()
