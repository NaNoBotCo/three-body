#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ghost_tally.py — run one start many times over, a hair apart, and count the endings.

    python3 tools/ghost_tally.py [copies] [nudge]

Burrau's Pythagorean problem, copied `copies` times with each copy moved by `nudge` at
the start, stepped together with a step taken from the closest pair. Writes:

    data/ghosts.json   the tally, the energy error, the escape times
    data/ghosts.npz    a sampled track per copy, which tools/draw.py turns into a picture

It takes a few minutes, so it is a tool and not a build step: the site reads the JSON."""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import physics as P  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BURRAU = (np.array([[1.0, 3.0], [-2.0, -1.0], [1.0, -1.0]]), np.zeros((3, 2)), np.array([3.0, 4.0, 5.0]))


def run(k=12, nudge=1e-9, T=115.0, eta=0.006, keep=0.05, far=16.0):
    """Each copy is run on its own, with its own step, because they stop sharing their
    close passes as soon as they part company — and a step chosen for whichever copy is
    in trouble would hold up all the others."""
    p0, v0, mass = BURRAU
    ang = np.linspace(0, 2 * math.pi, k, endpoint=False)
    gone = np.full(k, -1, int)
    gone_t = np.full(k, np.nan)
    err = np.zeros(k)
    tracks = []
    t0 = time.time()
    for i in range(k):
        s0 = np.concatenate([p0.ravel().copy(), v0.ravel().copy()])
        s0[0] += nudge * math.cos(ang[i])
        s0[1] += nudge * math.sin(ang[i])
        tr, times, sf, e = P.yoshida3_adaptive(s0, T, m=tuple(mass), eta=eta, keep=keep, hmin=1e-9)
        err[i] = e
        pts = tr.reshape(-1, 3, 2)
        who, dist, _ = P.escaped(sf[:6].reshape(3, 2), sf[6:].reshape(3, 2), mass)
        if who >= 0:
            gone[i] = who
            r = np.linalg.norm(pts[:, who, :], axis=1)
            back = np.argwhere(r < far)
            first = int(back[-1][0]) + 1 if len(back) else 0
            gone_t[i] = float(times[min(first, len(times) - 1)])
        tracks.append(pts.astype(np.float32))
        print(f"  copy {i + 1}/{k}: energy error {e:.1e}, "
              f"{'body ' + str(gone[i] + 1) + ' left at t=' + format(gone_t[i], '.1f') if gone[i] >= 0 else 'still together'}"
              f"  ({time.time() - t0:.0f}s)")
    n = min(len(x) for x in tracks)
    track = np.stack([x[:n] for x in tracks], axis=1)          # (frames, k, 3, 2)
    out = {
        "problem": "Burrau's Pythagorean problem: weights 3, 4, 5 at rest at the corners of a 3-4-5 triangle",
        "copies": int(k), "nudge": nudge, "T": T, "eta": eta,
        "tally": [int((gone == i).sum()) for i in range(3)],
        "none": int((gone < 0).sum()), "masses": [3, 4, 5],
        "escape_t_median": float(np.nanmedian(gone_t)) if np.isfinite(gone_t).any() else None,
        "escape_t_min": float(np.nanmin(gone_t)) if np.isfinite(gone_t).any() else None,
        "escape_t_max": float(np.nanmax(gone_t)) if np.isfinite(gone_t).any() else None,
        "energy_error_median": float(np.median(err)), "energy_error_max": float(err.max()),
        "ran": time.strftime("%Y-%m-%d"), "seconds": round(time.time() - t0),
        "note": ("Every copy is the same problem; they differ only by the nudge, applied to the first "
                 "body's position. They do not agree on which body ends up thrown out. Some of that "
                 "disagreement is the arithmetic and not the physics, which is the same point twice."),
    }
    (ROOT / "data" / "ghosts.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    np.savez_compressed(ROOT / "data" / "ghosts.npz", track=track, gone=gone, gone_t=gone_t,
                        times=np.arange(n) * keep)
    print(json.dumps({q: v for q, v in out.items() if q != "note"}, indent=1))
    return out


if __name__ == "__main__":
    run(k=int(sys.argv[1]) if len(sys.argv) > 1 else 24,
        nudge=float(sys.argv[2]) if len(sys.argv) > 2 else 1e-9)
