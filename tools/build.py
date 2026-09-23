#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build.py — every page, from data/, into build/site/.

    SITE_URL=https://example.org python3 tools/build.py

Reads data/*.json, runs the equations to draw the diagrams, inlines the stylesheet and
the demo script, and writes the HTML plus the machine files. Counts on the pages are
computed here rather than typed, and the figures come out of tools/physics.py at the
moment the page is written."""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fleet  # noqa: E402
import physics as P  # noqa: E402
import svg as diagrams  # noqa: E402
from css import CSS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BUILD = ROOT / "build"
SITE = BUILD / "site"
IMG = BUILD / "img"
SITE_URL = os.environ.get("SITE_URL", "https://nanobotco.github.io/three-body").rstrip("/")
SITE_NAME = "The Three-Body Problem"
SELF_ID = "three-body"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
REPO = "https://github.com/NaNoBotCo/three-body"
TODAY = date.today().isoformat()
E = html.escape
JS = (ROOT / "tools" / "anim.js").read_text(encoding="utf-8")
PROGRAM = (ROOT / "three_body.py").read_text(encoding="utf-8")


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


TH = load("theory.json")["chapters"]
TL = load("timeline.json")["events"]
GL = load("words.json")["terms"]
ORB = load("orbits.json")
GH = load("ghosts.json") if (DATA / "ghosts.json").exists() else None
# a run whose energy walked away is not evidence of anything; the page leaves it out
if GH and GH.get("energy_error_median", 1) > 1e-3:
    print(f"ghosts.json ignored: energy error {GH['energy_error_median']:.1e}")
    GH = None
ORBITS = ORB["orbits"]
ROSTER = fleet.load()

NAV = [("index.html", "Home"), ("math/index.html", "Math"), ("orbits/index.html", "Orbits"),
       ("history/index.html", "History"), ("code/index.html", "Code"), ("words/index.html", "Words"),
       ("sources/index.html", "Sources")]


def rel(depth):
    return "../" * depth


def page(title, body, depth=0, desc="", canonical="", jsonld=None, wide=False, current="", demos=False):
    r = rel(depth)
    ld = "".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>' for o in (jsonld or []))
    nav = " · ".join(f'<a href="{r}{h}"{" aria-current=page" if h == current else ""}>{n}</a>' for h, n in NAV)
    card = f"{SITE_URL}/img/card.jpg"
    orbjs = ""
    if demos:
        slim = [{"id": o["id"], "name": o["name"], "v": o["v"], "period": o["period"], "closes": o["closes"]} for o in ORBITS]
        orbjs = f'<script>window.TB_ORBITS={json.dumps(slim)};</script><script>{JS}</script>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc[:300])}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta name="color-scheme" content="light dark">
<meta property="og:site_name" content="{E(SITE_NAME)}"><meta property="og:locale" content="en_US">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc[:200])}"><meta property="og:type" content="website">
<meta property="og:image" content="{card}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{card}">
{f'<link rel="canonical" href="{E(canonical)}">' if canonical else ''}
<link rel="icon" href="{r}icon.svg" type="image/svg+xml">
<link rel="manifest" href="{r}manifest.webmanifest">
<meta name="theme-color" content="#0b7a76">
<link rel="license" href="{LICENSE_URL}">
<style>{CSS}</style>
{ld}
</head>
<body>
<header class="top"><a class="brand" href="{r}index.html">Three <b>Body</b></a>
<nav class="crumbs">{nav} · <a href="{r}llms.txt">llms.txt</a> · <a href="{REPO}">Source</a></nav></header>
<main{' class="wide"' if wide else ''}>
{body}
</main>
<footer>
<div class="bots">For the machines: <a href="{r}api/theory.json">theory.json</a> <a href="{r}api/orbits.json">orbits.json</a> <a href="{r}api/timeline.json">timeline.json</a> <a href="{r}api/words.json">words.json</a> <a href="{r}llms-full.txt">llms-full.txt</a> <a href="{r}sitemap.xml">sitemap.xml</a></div>
<p>Text, data and pictures <a href="{LICENSE_URL}">CC BY 4.0</a>; code <a href="{REPO}/blob/main/LICENSE">MIT</a>. The pictures and diagrams are computed from the equations in <a href="{REPO}/blob/main/tools/physics.py">tools/physics.py</a> when the page is built. Sources sit beside the facts they support and are listed at <a href="{r}sources/index.html">Sources</a>. Built {TODAY}.</p>
{fleet.row_html(SELF_ID, roster=ROSTER)}
{fleet.support_html(self_id="three-body", roster=ROSTER)}
{fleet.maker_html(roster=ROSTER)}
</footer>
{orbjs}
</body>
</html>
"""


def write(path, text):
    p = SITE / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def shot(href, img, lab, sub="", cls="", depth=0):
    r = rel(depth)
    return (f'<a class="shot {cls}" href="{E(href)}"><span class="bg" style="background-image:url({r}img/{img})"></span>'
            f'<span class="scrim"></span><span class="sp"></span><span class="tx">{E(lab)}'
            f'{f"<small>{E(sub)}</small>" if sub else ""}</span></a>')


def band(img, kicker, h2, p, depth=0, big=""):
    r = rel(depth)
    inner = f'<p class="big">{big}</p>' if big else f'<h2>{E(h2)}</h2><p>{E(p)}</p>'
    return (f'<section class="band" style="background-image:url({r}img/{img})">'
            f'<div class="in"><span class="kicker">{E(kicker)}</span>{inner}</div></section>')


def prose(paras):
    out = []
    for p in paras:
        t = E(p)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", t)
        out.append(f"<p>{t}</p>")
    return "".join(out)


def eq_html(e):
    return (f'<div class="eq"><span class="eqn">{e["html"]}</span>'
            f'<p class="read"><b>Reading it:</b> {E(e["read"])}</p>'
            f'{f"""<p class="why">{E(e["note"])}</p>""" if e.get("note") else ""}</div>')


def sources_list(srcs):
    return "<ul class='small'>" + "".join(f'<li><a href="{E(u)}">{E(n)}</a></li>' for n, u in srcs) + "</ul>"


# ------------------------------------------------------------------ counts, computed
N_CH = len(TH)
N_EQ = sum(len(c["eqs"]) for c in TH)
N_DEMOS = len({c["demo"] for c in TH if c.get("demo")})
N_EV = len(TL)
N_TERMS = len(GL)
N_ORB = len(ORBITS)
SCAN_N = ORB.get("scan", {}).get("grid", 0)
SCAN_STARTS = SCAN_N * SCAN_N
FOUND_HERE = sum(1 for o in ORBITS if o.get("origin") == "scan")
WORST_CLOSE = max((o["closes"] for o in ORBITS), default=0)
N_CHOREO = sum(1 for o in ORBITS if o.get("choreography"))
ALL_SOURCES: dict[str, str] = {}
for c in TH:
    for n, u in c["sources"]:
        ALL_SOURCES[u] = n
for e in TL:
    ALL_SOURCES[e["source"]] = e["source_name"]
for o in ORBITS:
    if o.get("source"):
        ALL_SOURCES[o["source"]] = o.get("source_name", o["source"])
N_SRC = len(ALL_SOURCES)

# figures that need a run, made once and used on more than one page
LYAP_SVG, LYAP_TAU = diagrams.divergence_svg()
DRIFT_SVG, DRIFT_LAST = diagrams.drift_svg()
QUINT_SVG, QUINT_ROOT = diagrams.quintic_svg(3.0034e-6)          # Sun and Earth
L1_KM = QUINT_ROOT * 149.598e6
ODDS = diagrams.outcomes(n=900)
ODDS_SVG = diagrams.outcome_svg(ODDS)
EIGHT = [o for o in ORBITS if o["id"] == "figure-eight"][0]


def demo_block(name):
    return (f'<div class="demo" data-demo="{name}"><p class="mute small">This one runs in the browser, '
            f'with JavaScript on. The words above it stand on their own.</p></div>')


# ------------------------------------------------------------------ pages
def home():
    body = f"""
<div class="hero">{shot("math/index.html", "hero.jpg", "Three bodies", "the math behind the three-body problem, in plain words, with the pictures moving", "hero")}</div>
<p class="lead">Two rocks pulling on each other: solved, on a napkin, in 1687. Add a third rock and there is no napkin. This is why, in plain English, with the equations printed and read out loud.</p>
<p>{N_CH} chapters, {N_EQ} equations with a plain reading under each, {N_DEMOS} things to press, {N_ORB} closed orbits found on the machine that built this page, {N_EV} events since Newton, {N_TERMS} words defined, {N_SRC} sources.</p>
<div class="doors">
{shot("math/index.html", "band-well.jpg", "Math", f"{N_CH} chapters, {N_EQ} equations")}
{shot("orbits/index.html", "band-eight.jpg", "Orbits", f"{N_ORB} that come back around")}
{shot("history/index.html", "band-fan.jpg", "History", f"{N_EV} events, 1687 to now")}
{shot("code/index.html", "band-map.jpg", "Code", "thirty lines, no libraries")}
</div>
<h2>The whole thing in five sentences</h2>
<p>Every body pulls every other body, with a force that falls off as the square of the distance. For two bodies that rule can be solved once and for all: an ellipse, repeating forever, written on one line.</p>
<p>For three, the same rule gives you eighteen numbers to track and ten quantities that never change — and two theorems that say no further quantity of the usable kind exists, so the bookkeeping stops there. Worse, two starts a millionth apart drift apart at a rate that doubles, so knowing the start better buys you only a little more warning.</p>
<p>What is left is exact special cases, a catalogue of orbits that repeat, a method of stepping the equations forward with an audit attached, and a set of odds for what usually happens. That is the whole of this site.</p>
{band("band-fan.jpg", "why it is hard", "", "", big=f"×{int(round(2.718281828 ** (10 / LYAP_TAU))):,}<small>how much a starting error grows in ten time units, measured on this page's own run</small>")}
<h2>Start here</h2>
<ol>
<li><a href="math/pull/index.html">Everything pulls on everything</a> — the one law.</li>
<li><a href="math/two/index.html">Two is easy</a> — the case with an answer.</li>
<li><a href="math/three/index.html">Add one rock</a> — where the answer goes, with the sandbox: three weights dropped from rest in 1913, sixty time units of near misses, and one of them thrown out at the end.</li>
<li><a href="math/chaos/index.html">A hair's difference, and a different sky</a> — the reason it stays gone. Forty-eight copies of that same start, a billionth apart, ending differently.</li>
<li><a href="math/myths/index.html">What it is not</a> — before the next headline.</li>
</ol>
<h2>Things on this site that were worked out here</h2>
<ul>
<li><b>{N_ORB} closed orbits</b>, {FOUND_HERE} of them turned up by scanning {SCAN_STARTS:,} starting speeds and then solving; the worst of them returns to its own start within {WORST_CLOSE:.0e}. <a href="orbits/index.html">Orbits</a>.</li>
<li><b>The Lyapunov time</b> for the start on the chaos page: {LYAP_TAU:.2f} time units, fitted to the measured gap between two runs. <a href="math/chaos/index.html">Chaos</a>.</li>
<li><b>L1 for the Sun and the Earth</b>: {L1_KM:,.0f} km, from solving the fifth-degree equation while the page was being built. <a href="math/shapes/index.html">Shapes</a>.</li>
<li><b>{100 * ODDS['share']:.0f}% of {ODDS['n']} random triples</b> threw a body out within {ODDS['T']:.0f} time units — and at a third of the step size, the same share, with only {100 * ODDS['audit']['agree']:.0f}% of the individual triples ending the same way. <a href="math/odds/index.html">Odds</a>.</li>
</ul>
"""
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/",
           "description": "The mathematics of the three-body problem in plain words, with animated demos and orbits computed on the spot.",
           "license": LICENSE_URL, "publisher": fleet.publisher_ld(ROSTER), "inLanguage": "en", "dateModified": TODAY},
          fleet.catalog_ld(ROSTER)]
    write("index.html", page(f"{SITE_NAME} — the math, in plain words", body, 0,
                             "The mathematics of the three-body problem explained in plain English: gravity, the two-body solution, why three has no formula, chaos, Lagrange points, the figure-eight orbit, and how it is computed.",
                             SITE_URL + "/", ld, current="index.html"))


def math_index():
    items = "".join(
        f'<li><a href="{c["id"]}/index.html"><b>{E(c["title"])}</b></a><br><span class="mute">{E(c["line"])}</span></li>'
        for c in TH)
    body = f"""
<h1>Math</h1>
<p class="lead">{N_CH} chapters in the order to read them. {N_EQ} equations, each with a line underneath saying what it says out loud. {N_DEMOS} of the chapters have something to press.</p>
<ol class="toc">{items}</ol>
{band("band-well.jpg", "the fence", "Where a small body can and cannot go", "Two heavy bodies, one speck, and the one quantity the speck cannot change. Every picture on this site is drawn from the equations rather than traced from one.", depth=1)}
<p>Nothing here needs mathematics past squaring a number and taking a square root. Where a symbol turns up it is named the first time, and again at <a href="../words/index.html">Words</a>.</p>
"""
    write("math/index.html", page("Math — The Three-Body Problem", body, 1,
                                  "The three-body problem chapter by chapter: gravity, two bodies solved, the equations for three, the ten conserved quantities, chaos, the restricted problem, central configurations, periodic orbits, Sundman's series, singularities, numerical stepping, and the statistics.",
                                  f"{SITE_URL}/math/", current="math/index.html"))


def math_chapters():
    for i, c in enumerate(TH):
        prev = TH[i - 1] if i else None
        nxt = TH[i + 1] if i + 1 < len(TH) else None
        eqs = "".join(eq_html(e) for e in c["eqs"])
        extra = ""
        if c["id"] == "count":
            extra = f'<div class="chart">{diagrams.ledger_svg()}<p class="cap">Eighteen numbers, ten of them held fixed by conservation, then the clock and the compass. Six left, and no way through them by bookkeeping.</p></div>'
        if c["id"] == "chaos" and GH:
            tal = GH["tally"]
            pct = [round(100 * n / GH["copies"]) for n in tal]
            extra = (f'<div class="chart"><div class="tallyrow">'
                     + "".join(f'<b>weight {mm}</b><span class="bar"><i style="--v:{n / GH["copies"]:.3f}"></i></span>'
                               f'<span>{n} of {GH["copies"]} ({p}%)</span>'
                               for mm, n, p in zip(GH["masses"], tal, pct))
                     + (f'<b>still together</b><span class="bar"><i style="--v:{GH["none"] / GH["copies"]:.3f}"></i></span>'
                        f'<span>{GH["none"]}</span>' if GH["none"] else "")
                     + f'</div><p class="cap">Burrau\'s problem run <b>{GH["copies"]} times over</b>, each copy moved by '
                     f'{GH["nudge"]:.0e} at the start — a billionth of the distance between the bodies — and stepped together with a step '
                     f'taken from the closest pair. The bars are which body ended up thrown out. The copies do not agree. '
                     f'The first ejection happened at t = {GH["escape_t_min"]:.0f} and the last at t = {GH["escape_t_max"]:.0f}; '
                     f'the median energy error over the whole run was {GH["energy_error_median"]:.0e}. '
                     f'Some of the disagreement is the arithmetic rather than the physics, which is the same point said twice — '
                     f'see <a href="../numbers/index.html">So you step it</a>. Run by '
                     f'<a href="{REPO}/blob/main/tools/ghost_tally.py">tools/ghost_tally.py</a>.</p></div>')
            extra += (f'<div class="chart">{LYAP_SVG}<p class="cap">The gap between two runs of the same start, on a log scale, '
                     f'for four sizes of nudge — computed while this page was built. The straight climb is the exponential; its slope '
                     f'gives a Lyapunov time of about <b>{LYAP_TAU:.2f}</b> time units, so a starting error grows roughly '
                     f'a thousandfold every {2.302585 * LYAP_TAU:.1f}. The flattening at the top is the gap running out of room.</p></div>')
        if c["id"] == "chaos" and not GH:
            extra = (f'<div class="chart">{LYAP_SVG}<p class="cap">'
                     f'The gap between two runs of the same start, on a log scale, for four sizes of nudge — computed while this page was built. '
                     f'The straight climb is the exponential; its slope gives a Lyapunov time of about <b>{LYAP_TAU:.2f}</b> time units.</p></div>')
        if c["id"] == "shapes":
            extra = (f'<div class="chart">{QUINT_SVG}<p class="cap">Euler\'s quintic for the Sun and the Earth, drawn and then solved by '
                     f'bisection at build time: the root is r = {QUINT_ROOT:.6f} in units of the Earth\'s distance, which puts L1 '
                     f'<b>{L1_KM:,.0f} km</b> sunward of us. No formula exists for a general fifth-degree equation, so this is a hunt, and it '
                     f'takes about forty steps.</p></div>'
                     f'<div class="chart">{diagrams.lagrange_svg(0.2)}<p class="cap">The five places, computed for a mass ratio of 0.2. '
                     f'Three on the line through the pair, from the quintics; two at the corners of equilateral triangles, from Lagrange.</p></div>')
        if c["id"] == "numbers":
            extra = (f'<div class="chart">{DRIFT_SVG}<p class="cap">Both steppers on the figure eight, same step size, energy error against time. '
                     f'After sixty time units the leapfrog is out by {DRIFT_LAST["leapfrog"]:.1e} and the obvious method by '
                     f'{DRIFT_LAST["Euler"]:.1e} — and the second is still climbing.</p></div>')
        if c["id"] == "odds":
            au = ODDS["audit"]
            extra = (f'<div class="chart">{ODDS_SVG}<p class="cap">{ODDS["n"]:,} random triples of equal weight, run for {ODDS["T"]:.0f} time units '
                     f'while this page was being built. <b>{ODDS["ejected"]}</b> of them — {100 * ODDS["share"]:.1f}% — threw a body clear out; '
                     f'{ODDS["together"]} were still together at the end. Half the ejections had happened by t = {ODDS["t_median"]:.1f}, '
                     f'a tenth before {ODDS["t_quick"]:.1f}, and a tenth not until after {ODDS["t_slow"]:.1f}.</p></div>'
                     f'<div class="try"><b>The audit on that figure.</b> The bottom of each well is rounded off at {ODDS["soft"]}, because at a fixed step '
                     f'a near pass throws a body across the sky and the answer you get is the stepper\'s rather than the physics\'. '
                     f'The median energy error over the run is {ODDS["drift"]:.0e}. Then the first {au["n"]} of the same starts were run again at a third of the step: '
                     f'the share that ejected came out at {100 * au["share"]:.1f}% against {100 * au["share_coarse"]:.1f}% — the same answer — '
                     f'while only {100 * au["agree"]:.0f}% of the individual triples ended the same way. The statistics hold and the trajectories do not, '
                     f'which is the finding of this whole page.</div>')
        if c["id"] == "eight":
            extra = (f'<div class="chart">{diagrams.shape_sphere(P.sd_state(*EIGHT["v"]), EIGHT["period"])}'
                     f'<p class="cap">The figure eight drawn on the shape sphere: every triangle shape is a point on this ball, size and '
                     f'direction thrown away. The dashed circle is every straight-line arrangement, and the three red dots on it are the three '
                     f'two-body collisions. The orbit threads between them and closes.</p></div>')
        nav = '<p class="row">' + (f'<a class="btn alt" href="../{prev["id"]}/index.html">← {E(prev["title"])}</a> ' if prev else "") + \
              (f'<a class="btn" href="../{nxt["id"]}/index.html">{E(nxt["title"])} →</a>' if nxt else '<a class="btn" href="../../orbits/index.html">The orbits →</a>') + "</p>"
        body = f"""
<p class="small mute">Math · chapter {i + 1} of {N_CH}</p>
<h1>{E(c["title"])}</h1>
<p class="line">{E(c["line"])}</p>
<div class="chapter{' myth' if c['id'] == 'myths' else ''}"><div class="body">{prose(c["body"])}</div></div>
{eqs}
{f'<div class="try"><b>Try it.</b> {E(c["try"])}</div>' if c.get("try") else ''}
{demo_block(c["demo"]) if c.get("demo") else ''}
{extra}
<h3>Sources</h3>{sources_list(c["sources"])}
{nav}
"""
        ld = [{"@context": "https://schema.org", "@type": "Article", "headline": c["title"], "description": c["line"],
               "url": f"{SITE_URL}/math/{c['id']}/", "license": LICENSE_URL, "inLanguage": "en",
               "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/"},
               "publisher": fleet.publisher_ld(ROSTER), "dateModified": TODAY}]
        write(f"math/{c['id']}/index.html",
              page(f"{c['title']} — The Three-Body Problem", body, 2, c["line"], f"{SITE_URL}/math/{c['id']}/", ld,
                   current="math/index.html", demos=True))


def orbits_page():
    cards = []
    for o in sorted(ORBITS, key=lambda q: q["period"]):
        st = P.sd_state(*o["v"])
        src = (f'<br><a href="{E(o["source"])}">{E(o.get("source_name", "source"))}</a>' if o.get("source") else "")
        cards.append(f"""<article class="orb" id="{E(o['id'])}">{diagrams.orbit_svg(st, o["period"])}
<span class="tag">{'choreography · ' if o.get('choreography') else ''}{E(o.get('origin_label', ''))}</span>
<h3>{E(o["name"])}</h3>
<p class="small">{E(o.get("note", ""))}{src}</p>
<div class="kv">period {o['period']:.6f}<br>start speed ({o['v'][0]:.9f}, {o['v'][1]:.9f})<br>closes to {o['closes']:.1e}<br>solver reached {o['closes_solver']:.0e}<br>closest approach {o['closest_approach']:.3f}</div></article>""")
    scan = ORB.get("scan", {})
    body = f"""
<h1>Orbits</h1>
<p class="lead">{N_ORB} three-body starts that come back to exactly where they began and then do it again, each one found by the machine that built this page and each one saying how close it comes to closing. {N_CHOREO} of them are choreographies: all three bodies on a single track, one behind the other.</p>
<div class="demo" data-demo="eight"><p class="mute small">The browser runs these from the same numbers printed on the cards below.</p></div>
<h2>How they were found</h2>
<ol class="steps">
<li><b>One line of starts.</b> Two bodies at −1 and +1 with the same velocity, the third at the origin with twice that velocity the other way. Zero total momentum, zero spin, three bodies in a row. Two numbers describe the whole start, which makes it a sheet of paper you can search.</li>
<li><b>Run {SCAN_STARTS:,} of them at once.</b> A {SCAN_N}×{SCAN_N} grid of starting speeds, stepped forward together for {scan.get('T', 40)} time units, each one asked at every step how far it is from its own starting state. Keep the closest it ever got. That is <a href="{REPO}/blob/main/tools/find_orbits.py">tools/find_orbits.py scan</a>, and it takes about three and a half minutes.</li>
<li><b>Read the valleys.</b> {scan.get('near', 0)} of the {SCAN_STARTS:,} came back within 0.05 of their own start. The dips in that map are where the closed orbits live — the picture below is that map.</li>
<li><b>Walk each one in.</b> Three unknowns — the two velocity components and the period — against twelve residuals, the state at time T minus the state at 0. Finite-difference Jacobian, least squares, damped. Ten iterations takes the residual from about 10⁻² to about 10⁻¹¹.</li>
<li><b>Round it, and measure again.</b> The numbers printed on the cards are rounded to nine decimal places. That rounding moves the answer, so the residual on each card is re-measured from the rounded start rather than reported from the solver — both figures are on the card, and the gap between them is below.</li>
<li><b>Throw out the repeats.</b> The scan keeps whichever return was closest, which is often two or three laps, so the same orbit arrives several times with its period doubled or tripled. The shortest period that closes is the orbit's own.</li>
</ol>
{band("band-map.jpg", "the map", "Every start, and how close it came to closing", "Brighter is closer. The bright valleys are the periodic orbits; everything dark is a start that wandered off and never came back to itself. This is the whole search, drawn.", depth=1)}
<h2>The ones that closed</h2>
<div class="orbits">{"".join(cards)}</div>
<p class="small mute">Each card's picture is one period, integrated at build time from the numbers printed under it. The period is in the units the equations use — three equal weights of 1, G = 1 — and the close figure is the distance between the twelve numbers at time T and the twelve at time 0.</p>
<h2>Two numbers, and the gap between them</h2>
<p>Every card carries the residual twice. <b>Closes to</b> is what the start printed on that card does: type those numbers in, run them for that period, and the state comes back within that distance. <b>Solver reached</b> is what the search got to before the numbers were rounded to nine decimal places for printing.</p>
<p>The gap is a factor of ten thousand or so, and it is not the stepper: the same residual comes out at a step four times finer and at one four times coarser. It is the rounding itself. A change of five in the tenth decimal place of a starting speed, grown over one period of a three-body orbit, is a change in the eighth decimal of where everything ends up. The subject of this whole site, turning up in its own data files, on the tidiest orbits it has.</p>
<h2>What is not here</h2>
<p>This scan covers one two-dimensional sheet of starts, at one resolution, for one set of weights, looking only at returns inside {scan.get('T', 40)} time units. Longer periods, unequal weights, non-zero spin and the whole rest of the space are outside it. Šuvakov and Dmitrašinović reported thirteen families from a finer search of the same sheet in 2013, and Li and Liao have since taken the catalogue into the thousands with more machine and more digits. The point of the search here is not the count; it is that the method fits in a file you can read in ten minutes.</p>
<p><a class="btn" href="../code/index.html">The program that does it →</a></p>
"""
    write("orbits/index.html", page("Orbits — The Three-Body Problem", body, 1,
                                    f"{N_ORB} periodic three-body orbits, found by scanning {SCAN_STARTS:,} starting speeds and refining each near-miss until it closes; each with its initial conditions, period and residual.",
                                    f"{SITE_URL}/orbits/", wide=True, current="orbits/index.html", demos=True))


def history():
    legend = "".join(f'<span style="--e:{diagrams.ERA[k]}">{E(v)}</span>' for k, v in diagrams.ERA_NAME.items())
    items = []
    for e in TL:
        items.append(f"""<li style="--e:{diagrams.ERA[e["era"]]}"><span class="dot"></span><span class="yr">{e["year"]}</span><div>
<span class="era">{E(diagrams.ERA_NAME[e["era"]])}</span><span class="who">{E(e.get("who", ""))}</span>
<h3>{E(e["title"])}</h3><p class="plain">{E(e["plain"])}</p>
<details><summary>more</summary><p>{E(e["more"])}</p><p class="small">Source: <a href="{E(e["source"])}">{E(e["source_name"])}</a></p></details></div></li>""")
    body = f"""
<h1>History</h1>
<p class="lead">{N_EV} events, from the book that stated the problem to the telescope that lives on a saddle point. Each one gets a line first and the rest underneath.</p>
<div class="chart">{diagrams.strip(TL)}<div class="legend">{legend}</div><p class="cap">Two hundred years of trying to solve it, then a century of proving which routes are closed, then the computers.</p></div>
{band("band-fan.jpg", "1890", "He won the prize, and then he found his own mistake", "Poincaré's corrected memoir on the three-body problem is where chaos enters mathematics. The picture behind this is " + (f"{GH['copies']} runs of Burrau's problem, each started {GH['nudge']:.0e} from the others" if GH else "one start, run many times over from almost the same place") + " — the thing he saw without a screen.", depth=1)}
<ul class="tl nojs">{"".join(items)}</ul>
<p><a class="btn" href="../math/index.html">The math →</a></p>
"""
    write("history/index.html", page("History — The Three-Body Problem", body, 1,
                                     f"{N_EV} events in the history of the three-body problem: Newton 1687, Euler 1767, Lagrange 1772, Jacobi 1836, Bruns 1887, Poincaré 1890, Sundman 1912, the figure eight in 1993, and the statistical solution in 2019.",
                                     f"{SITE_URL}/history/", current="history/index.html", demos=True))


def code_page():
    prog = E(PROGRAM)
    body = f"""
<h1>Code</h1>
<p class="lead">The three-body problem in thirty lines of Python, no libraries, and it draws its own picture. Copy it, run it, change the numbers.</p>
<p>The program below is the same arithmetic as everything else on this site: work out the pull on each body, kick the speeds by half a step, drift the positions a whole step, kick again. It starts the three bodies on the figure-eight orbit, runs one full period, prints the track as characters, and then prints the energy at the start and at the end so you can see for yourself that the stepping did not leak.</p>
<p><a class="btn" href="three_body.py" download>Download three_body.py</a> <a class="btn alt" href="{REPO}/blob/main/three_body.py">On GitHub</a></p>
<pre class="code">{prog}</pre>
<h2>What it prints</h2>
<pre class="code">{E(EXAMPLE_OUTPUT)}</pre>
<h2>Things to change</h2>
<ul>
<li><b>The step, H.</b> Make it ten times bigger and watch the energy at the end move. Make it a hundred times bigger and the orbit falls apart. That is the whole numbers chapter in one edit.</li>
<li><b>The starting speeds, P.</b> Nudge the last digit and run it again. Nothing happens at first, and by the end of the period the picture is different — that is the chaos chapter, at home, in one edit.</li>
<li><b>The weights, M.</b> Make one of them 1.2. The figure eight needs all three equal, so it comes apart; how long it takes to is a fair question and the program answers it.</li>
<li><b>Swap the stepper.</b> Replace the three lines in <code>step</code> with position first, speed second — the obvious way — and watch the energy climb instead of hold.</li>
</ul>
<h2>The rest of the toolchain</h2>
<p>The site is built by the same kind of code, a little longer:</p>
<div class="kvgrid">
<b>tools/physics.py</b><span>the equations, the leapfrog, a fourth-order stepper for when the answer has to be good, and the batch version that moves forty thousand trajectories at once</span>
<b>tools/find_orbits.py</b><span>the scan over starting speeds and the Gauss-Newton solver that walks each near-miss in until it closes</span>
<b>tools/draw.py</b><span>the photographs that are not photographs: every raster on the site is a trajectory laid down as light</span>
<b>tools/svg.py</b><span>the diagrams, computed while the page is written, which is why the numbers in the captions match the pictures above them</span>
<b>tools/anim.js</b><span>the demos: the same steppers in the browser, including the fourth-order one and the step chosen from the closest pair</span>
<b>tools/build.py</b><span>this page and the rest of them</span>
</div>
<p class="small mute">All of it is <a href="{REPO}">on GitHub</a>, MIT for the code and CC BY 4.0 for the words, pictures and data. It needs Python 3, numpy and pillow; the program above needs nothing at all.</p>
"""
    write("code/index.html", page("Code — The Three-Body Problem", body, 1,
                                  "The three-body problem in thirty lines of Python with no libraries: the equations, a leapfrog stepper, the figure-eight orbit, and an energy check. Free to copy.",
                                  f"{SITE_URL}/code/", current="code/index.html"))
    write("code/three_body.py", PROGRAM)


def words():
    chap = {c["id"]: c["title"] for c in TH}
    dl = []
    for t in sorted(GL, key=lambda t: t["term"].lower()):
        see = t.get("see", "")
        link = f'<a href="../math/{see}/index.html">{E(chap[see])}</a>' if see in chap else ""
        anchor = re.sub(r"[^a-z0-9]+", "-", t["term"].lower()).strip("-")
        dl.append(f'<dt id="{anchor}">{E(t["term"])}</dt><dd>{E(t["plain"])}{f" — {link}" if link else ""}</dd>')
    body = f"""
<h1>Words</h1>
<p class="lead">{N_TERMS} words, each in a sentence or two, with the chapter that uses it.</p>
<dl class="gloss">{"".join(dl)}</dl>
"""
    write("words/index.html", page("Words — The Three-Body Problem", body, 1,
                                   f"{N_TERMS} terms from the three-body problem defined in plain English: Lyapunov time, Jacobi constant, central configuration, shape sphere, symplectic, regularisation, Hill sphere and the rest.",
                                   f"{SITE_URL}/words/", current="words/index.html"))


def sources():
    rows = "".join(f'<li><a href="{E(u)}">{E(n)}</a> <span class="small mute">{E(u.split("/")[2] if "//" in u else u)}</span></li>'
                   for u, n in sorted(ALL_SOURCES.items(), key=lambda kv: kv[1].lower()))
    body = f"""
<h1>Sources</h1>
<p class="lead">{N_SRC} sources, one line each. Every fact on the site sits next to one of these; this page lists them once.</p>
<p>Wikipedia is used for the settled history, where its articles carry the primary citations. For results, the source is the paper. Where a figure was computed here rather than read from a source — the orbits, the Lyapunov time, the L1 distance, the ejection count — the page says so and names the file that computed it.</p>
<ul>{rows}</ul>
<h2>Further reading, for the next step up</h2>
<ul>
<li>June Barrow-Green, <a href="https://bookstore.ams.org/hmath-11">Poincaré and the Three Body Problem</a> (1997) — the history of the prize, the error and the correction, in detail.</li>
<li>Florin Diacu, <a href="https://doi.org/10.1007/BF03024313">The solution of the n-body problem</a> (1996) — nine pages on what 'solved' has meant to different centuries.</li>
<li>Richard Montgomery, <a href="https://arxiv.org/abs/1402.0841">The three-body problem and the shape sphere</a> (2015) — how the sphere works, with the mathematics kept gentle.</li>
<li>Carl Murray and Stanley Dermott, <a href="https://www.cambridge.org/core/books/solar-system-dynamics/A0CC1D3E36E2ED8FC8F7C3BFFF7EF4D3">Solar System Dynamics</a> (1999) — the standard textbook for the restricted problem, Lagrange points and resonances.</li>
<li>Douglas Heggie and Piet Hut, <a href="https://www.cambridge.org/core/books/gravitational-millionbody-problem/">The Gravitational Million-Body Problem</a> (2003) — where three-body scattering fits into star clusters.</li>
</ul>
"""
    write("sources/index.html", page("Sources — The Three-Body Problem", body, 1,
                                     f"The {N_SRC} sources behind the site, and five things to read next.",
                                     f"{SITE_URL}/sources/", current="sources/index.html"))


def machine_files():
    (SITE / "api").mkdir(parents=True, exist_ok=True)
    for name in ("theory", "timeline", "words", "orbits"):
        shutil.copy(DATA / f"{name}.json", SITE / "api" / f"{name}.json")
    write("api/index.json", json.dumps({
        "site": SITE_NAME, "url": SITE_URL + "/", "license": LICENSE_URL, "built": TODAY,
        "counts": {"chapters": N_CH, "equations": N_EQ, "demos": N_DEMOS, "orbits": N_ORB,
                   "orbits_found_here": FOUND_HERE, "scan_starts": SCAN_STARTS, "events": N_EV,
                   "terms": N_TERMS, "sources": N_SRC},
        "computed": {"lyapunov_time": round(LYAP_TAU, 4), "sun_earth_L1_km": round(L1_KM),
                     "random_triples": ODDS["n"], "ejected": ODDS["ejected"],
                     "ejected_share": round(ODDS["share"], 4), "softening": ODDS["soft"],
                     "energy_drift_median": ODDS["drift"],
                     "audit": {k: v for k, v in ODDS["audit"].items()}},
        "files": ["theory.json", "timeline.json", "words.json", "orbits.json"]}, indent=1))
    urls = ["", "math/", "orbits/", "history/", "code/", "words/", "sources/"] + [f"math/{c['id']}/" for c in TH]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"<url><loc>{SITE_URL}/{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    chapters = "\n".join(f"- [{c['title']}]({SITE_URL}/math/{c['id']}/): {c['line']}" for c in TH)
    write("llms.txt", f"""# {SITE_NAME}

> The mathematics of the three-body problem in plain English: the law, the two-body solution, the eighteen numbers and the ten that hold, Bruns and Poincaré, chaos and the Lyapunov time, the restricted problem and the Lagrange points, central configurations, periodic orbits including the figure eight, Sundman's series, singularities, numerical stepping, and the statistics of what usually happens. {N_EQ} equations, each with a plain reading. CC BY 4.0.

- [Math]({SITE_URL}/math/): {N_CH} chapters
{chapters}
- [Orbits]({SITE_URL}/orbits/): {N_ORB} periodic orbits with initial conditions, periods and residuals; {FOUND_HERE} found by a scan of {SCAN_STARTS:,} starts run on the building machine
- [History]({SITE_URL}/history/): {N_EV} events, 1687 to 2022
- [Code]({SITE_URL}/code/): the whole thing in 30 lines of Python, no libraries
- [Words]({SITE_URL}/words/): {N_TERMS} terms
- [Sources]({SITE_URL}/sources/): {N_SRC} sources

## Computed on this site rather than quoted
- Lyapunov time for the reference start: {LYAP_TAU:.3f} time units
- Sun–Earth L1 from the quintic: {L1_KM:,.0f} km
- {ODDS['ejected']} of {ODDS['n']} random equal-mass triples ejected a body within {ODDS['T']:.0f} time units ({100 * ODDS['share']:.1f}%); rerun at a third of the step the share is unchanged but only {100 * ODDS['audit']['agree']:.0f}% of individual triples end the same way

## Data
- {SITE_URL}/api/theory.json · {SITE_URL}/api/orbits.json · {SITE_URL}/api/timeline.json · {SITE_URL}/api/words.json
- {SITE_URL}/llms-full.txt — every chapter, equation, orbit and event as text
- Repository: {REPO}
""")
    full = [f"# {SITE_NAME}\n\nBuilt {TODAY}. CC BY 4.0. {SITE_URL}/\n"]
    for c in TH:
        full.append(f"\n## {c['title']}\n\n{c['line']}\n\n" + "\n\n".join(c["body"]))
        for e in c["eqs"]:
            plain = re.sub(r"<[^>]+>", "", e["html"]).replace("&nbsp;", " ")
            full.append(f"\n    {plain}\n    — {e['read']}" + (f"\n    ({e['note']})" if e.get("note") else ""))
        full.append("\n\nSources: " + "; ".join(f"{n} <{u}>" for n, u in c["sources"]) + "\n")
    full.append("\n## Orbits\n")
    for o in sorted(ORBITS, key=lambda q: q["period"]):
        full.append(f"\n- {o['name']}: start speeds ({o['v'][0]:.9f}, {o['v'][1]:.9f}) on the line x=(-1,0),(1,0),(0,0) "
                    f"with v3 = -2 v1; period {o['period']:.8f}; closes to {o['closes']:.2e}; {o.get('origin_label','')}")
    full.append("\n\n## History\n")
    for e in TL:
        full.append(f"\n- {e['year']} — {e['title']}. {e['plain']} {e['more']} Source: {e['source_name']} <{e['source']}>")
    full.append("\n\n## Words\n")
    for t in GL:
        full.append(f"\n- {t['term']}: {t['plain']}")
    write("llms-full.txt", "".join(full) + "\n")
    write("humans.txt", f"/* {SITE_NAME} */\nBuilt by NaNoBotCo. The pictures are trajectories, computed in tools/draw.py. {REPO}\n")
    write("manifest.webmanifest", json.dumps({"name": SITE_NAME, "short_name": "Three Body", "start_url": "./",
                                              "display": "standalone", "background_color": "#0d1117", "theme_color": "#0b7a76",
                                              "icons": [{"src": "icon.svg", "sizes": "any", "type": "image/svg+xml"}]}))
    write("icon.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0b1220"/>'
                      '<path d="M32 32c-7-9-20-9-20 0s13 9 20 0 20-9 20 0-13 9-20 0z" fill="none" stroke="#2fc4bd" stroke-width="2.5"/>'
                      '<circle cx="14" cy="32" r="4" fill="#f0b545"/><circle cx="50" cy="32" r="4" fill="#a891f2"/>'
                      '<circle cx="32" cy="32" r="3.5" fill="#eef1f4"/></svg>')
    write("404.html", page("Not here — The Three-Body Problem", '<h1>Not here</h1><p class="lead">That address left the system. '
                           '<a href="index.html">Home</a>, or the <a href="math/index.html">math</a>.</p>', 0, "Page not found."))
    fleet.decorate(SITE, SELF_ID, ROSTER)


EXAMPLE_OUTPUT = ""


def main():
    global EXAMPLE_OUTPUT
    import subprocess
    try:
        EXAMPLE_OUTPUT = subprocess.run([sys.executable, str(ROOT / "three_body.py")], capture_output=True,
                                        text=True, timeout=120).stdout
    except Exception as exc:
        EXAMPLE_OUTPUT = f"(three_body.py did not run here: {exc})"
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    if not (IMG / "hero.jpg").exists():
        import draw
        for k in draw.PICTURES:
            draw.PICTURES[k]()
    shutil.copytree(IMG, SITE / "img")
    home(); math_index(); math_chapters(); orbits_page(); history(); code_page(); words(); sources(); machine_files()
    n = len(list(SITE.rglob("*.html")))
    print(f"built {n} pages into {SITE} for {SITE_URL}: {N_CH} chapters, {N_EQ} equations, {N_ORB} orbits "
          f"({FOUND_HERE} found here), {N_EV} events, {N_TERMS} terms, {N_SRC} sources · "
          f"Lyapunov {LYAP_TAU:.2f} · L1 {L1_KM:,.0f} km · {ODDS['ejected']}/{ODDS['n']} ejected")


if __name__ == "__main__":
    main()
