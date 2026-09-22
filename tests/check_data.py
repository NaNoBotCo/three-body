#!/usr/bin/env python3
"""check_data.py — the data files say what they claim, and the orbits still close.

    python3 tests/check_data.py            # the quick gate publish.sh runs
    python3 tests/check_data.py --deep     # re-integrate every orbit at a finer step

Run before every build. An orbit whose initial conditions have drifted, a chapter with a
source missing, a glossary entry pointing at a chapter that is not there — each is the
kind of thing that makes a page quietly untrue, so each one fails here instead."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import physics as P  # noqa: E402

bad = []


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def check(cond, msg):
    if not cond:
        bad.append(msg)


TH = load("theory.json")["chapters"]
TL = load("timeline.json")["events"]
GL = load("words.json")["terms"]
ORB = load("orbits.json")

ids = [c["id"] for c in TH]
check(len(set(ids)) == len(ids), "theory.json: two chapters share an id")
for c in TH:
    for k in ("id", "title", "line", "body", "eqs", "sources"):
        check(k in c, f"theory.json {c.get('id')}: no {k}")
    check(len(c["body"]) >= 2, f"theory.json {c['id']}: body is too short to be a chapter")
    check(len(c["sources"]) >= 1, f"theory.json {c['id']}: no sources")
    for n, u in c["sources"]:
        check(u.startswith("http"), f"theory.json {c['id']}: source {n} is not a URL")
    for e in c["eqs"]:
        check(e.get("html") and e.get("read"), f"theory.json {c['id']}: an equation with no reading")
        check(e["html"].count("<span") == e["html"].count("</span>"), f"theory.json {c['id']}: unbalanced span in an equation")

for e in TL:
    for k in ("year", "era", "title", "plain", "more", "source", "source_name"):
        check(k in e, f"timeline.json {e.get('year')}: no {k}")
    check(1600 < e["year"] <= 2030, f"timeline.json: year {e['year']} is not a year")
    check(e["era"] in ("law", "shapes", "proof", "step", "found", "sky"), f"timeline.json {e['year']}: era {e['era']}")

for t in GL:
    check(t.get("plain"), f"words.json {t.get('term')}: no definition")
    if t.get("see"):
        check(t["see"] in ids, f"words.json {t['term']}: points at chapter '{t['see']}', which is not there")

check(any(o["id"] == "figure-eight" for o in ORB["orbits"]), "orbits.json: no figure-eight row")
deep = "--deep" in sys.argv
for o in ORB["orbits"]:
    for k in ("id", "name", "v", "period", "closes", "origin"):
        check(k in o, f"orbits.json {o.get('id')}: no {k}")
    check(o["closes"] < 1e-5, f"orbits.json {o['id']}: published as closing to {o['closes']}, which is not closed")
    s0 = P.sd_state(*o["v"])
    # re-run the published start for the published period and hold the answer to the
    # residual the row claims. Deep mode does it at a quarter of the step: the residual
    # is set by the rounding of the printed numbers, not by the stepper, so it should
    # barely move — and if it moves, the row is wrong about itself.
    dt = o.get("closes_dt", 5e-5) * (0.25 if deep else 4.0)
    r = P.returns(s0, o["period"], dt=dt)
    tol = max(o["closes"] * 3, 1e-9)
    check(r < tol, f"orbits.json {o['id']}: re-run here returns {r:.2e}, over the {tol:.0e} tolerance")
    e0 = P.energy(np.array(s0[:6]).reshape(3, 2), np.array(s0[6:]).reshape(3, 2), np.array(o.get("mass", [1, 1, 1])))
    check(e0 < 0, f"orbits.json {o['id']}: energy {e0:.3f} is not bound")

# the two-body case the site rests on: a circular orbit stays circular
pos = np.array([[-0.5, 0.0], [0.5, 0.0], [1e6, 1e6]])
# separation 1, total weight 2: the relative speed is √2 and each body carries half of it
vel = np.array([[0.0, -(2 ** 0.5) / 2], [0.0, (2 ** 0.5) / 2], [0.0, 0.0]])
mass = np.array([1.0, 1.0, 1e-12])
_, p1, v1 = P.leapfrog(pos, vel, mass, 1e-4, 20000)
r1 = np.linalg.norm(p1[0] - p1[1])
check(abs(r1 - 1.0) < 1e-4, f"physics.py: a circular two-body orbit drifted to r = {r1:.6f}")

if bad:
    print("\n".join("FAIL " + b for b in bad))
    sys.exit(1)
print(f"data ok: {len(TH)} chapters, {sum(len(c['eqs']) for c in TH)} equations, {len(TL)} events, "
      f"{len(GL)} terms, {len(ORB['orbits'])} orbits{' (deep)' if deep else ''}, "
      f"{len(ORB['orbits'])} of them re-integrated here")
