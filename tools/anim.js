/* anim.js — the demos. Vanilla, no library, inlined into the pages that use them.

   Each demo mounts into an element with data-demo="<name>". The physics is the same as
   tools/physics.py, written out for three bodies: a leapfrog, the fourth-order
   composition of it for anything with a close pass in it, and a step chosen from the
   closest pair rather than fixed. Continuous motion runs only where the reader has not
   asked for reduced motion; every demo also works from its buttons, so a still page is
   a working page.

   The orbits a demo can load are put on the page by tools/build.py as window.TB_ORBITS. */
(function () {
  "use strict";
  var RM = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ORB = window.TB_ORBITS || [];

  function el(tag, attrs, kids) {
    var e = document.createElement(tag);
    if (attrs) for (var k in attrs) { if (k === "text") e.textContent = attrs[k]; else if (k === "html") e.innerHTML = attrs[k]; else e.setAttribute(k, attrs[k]); }
    (kids || []).forEach(function (c) { e.appendChild(c); });
    return e;
  }
  function btn(label, cls) { return el("button", { class: "btn" + (cls ? " " + cls : ""), type: "button", text: label }); }
  function range(min, max, val, step) { return el("input", { type: "range", min: min, max: max, value: val, step: step || 1 }); }
  function readout(t) { return el("span", { class: "readout", text: t || "" }); }
  function row(kids) { return el("div", { class: "row" }, kids); }
  function note(t) { return el("p", { class: "note", text: t }); }
  function label(t, kids) { return el("label", { text: t }, kids); }
  function fmt(x, d) { return (isFinite(x) ? x : 0).toFixed(d); }
  function pick(opts, val) {
    var s = el("select", { class: "sel" });
    opts.forEach(function (o) { var op = el("option", { value: o[0], text: o[1] }); if (o[0] === val) op.selected = true; s.appendChild(op); });
    return s;
  }
  var css = getComputedStyle(document.documentElement);
  function v(n, d) { return (css.getPropertyValue(n) || "").trim() || d; }
  var C = { teal: v("--teal", "#0b7a76"), gold: v("--gold", "#b7791f"), violet: v("--violet", "#6d4fc4"),
            red: v("--red", "#c8323c"), ink: v("--ink", "#101418"), mute: v("--mute", "#5b6570"),
            line: v("--line", "#e2e0d6"), panel: v("--panel", "#fff") };
  var BODY = [C.teal, C.gold, C.violet];

  /* ---------------------------------------------------------------- the physics */
  function accel(s, m, soft) {
    var a = [0, 0, 0, 0, 0, 0], e = soft || 0;
    for (var i = 0; i < 3; i++) for (var j = i + 1; j < 3; j++) {
      var dx = s[2 * j] - s[2 * i], dy = s[2 * j + 1] - s[2 * i + 1];
      var r2 = dx * dx + dy * dy + e * e, inv = 1 / (r2 * Math.sqrt(r2));
      a[2 * i] += m[j] * dx * inv; a[2 * i + 1] += m[j] * dy * inv;
      a[2 * j] -= m[i] * dx * inv; a[2 * j + 1] -= m[i] * dy * inv;
    }
    return a;
  }
  /* state = [x1,y1,x2,y2,x3,y3, vx1,vy1,vx2,vy2,vx3,vy3] */
  function step(s, m, h, soft) {
    var a = accel(s, m, soft), i;
    for (i = 0; i < 6; i++) { s[6 + i] += 0.5 * h * a[i]; s[i] += h * s[6 + i]; }
    a = accel(s, m, soft);
    for (i = 0; i < 6; i++) s[6 + i] += 0.5 * h * a[i];
    return s;
  }
  /* Yoshida's fourth-order composition of the leapfrog: three of them, with these
     weights. Three times the work for about a thousand times the accuracy, and the
     sandbox needs it — with a plain leapfrog, Burrau's problem below throws out a
     different body depending on the step size. Same composition as tools/physics.py. */
  var W1 = 1 / (2 - Math.cbrt(2)), W0 = -Math.cbrt(2) * W1;
  function step4(s, m, h) { step(s, m, W1 * h, 0); step(s, m, W0 * h, 0); step(s, m, W1 * h, 0); }
  function stepEuler(s, m, h) {
    var a = accel(s, m, 0), i;
    for (i = 0; i < 6; i++) { s[i] += h * s[6 + i]; s[6 + i] += h * a[i]; }
    return s;
  }
  function energy(s, m) {
    var ke = 0, pe = 0, i, j;
    for (i = 0; i < 3; i++) ke += 0.5 * m[i] * (s[6 + 2 * i] * s[6 + 2 * i] + s[7 + 2 * i] * s[7 + 2 * i]);
    for (i = 0; i < 3; i++) for (j = i + 1; j < 3; j++) {
      var dx = s[2 * j] - s[2 * i], dy = s[2 * j + 1] - s[2 * i + 1];
      pe -= m[i] * m[j] / Math.sqrt(dx * dx + dy * dy);
    }
    return ke + pe;
  }
  function spin(s, m) {
    var l = 0;
    for (var i = 0; i < 3; i++) l += m[i] * (s[2 * i] * s[7 + 2 * i] - s[2 * i + 1] * s[6 + 2 * i]);
    return l;
  }
  function momentum(s, m) {
    var px = 0, py = 0;
    for (var i = 0; i < 3; i++) { px += m[i] * s[6 + 2 * i]; py += m[i] * s[7 + 2 * i]; }
    return [px, py];
  }
  function sdState(vx, vy) { return [-1, 0, 1, 0, 0, 0, vx, vy, vx, vy, -2 * vx, -2 * vy]; }
  function minSep(s) {
    var r = 1e9;
    for (var i = 0; i < 3; i++) for (var j = i + 1; j < 3; j++) {
      var dx = s[2 * j] - s[2 * i], dy = s[2 * j + 1] - s[2 * i + 1];
      r = Math.min(r, Math.sqrt(dx * dx + dy * dy));
    }
    return r;
  }
  /* Advance a trajectory by `budget` of its own time, choosing each step from the
     closest pair. The time two bodies take to fall together goes as their separation to
     the three halves, so that is what sets the step. At a fixed step a close pass throws
     a body across the sky and the energy goes with it — which is the whole reason
     Burrau's problem below needs this. */
  function advance(s, m, budget, cap) {
    var M = m[0] + m[1] + m[2], t = 0, n = 0, hmin = 1e-7, hmax = 4e-3;
    cap = cap || 12000;
    while (t < budget && n < cap) {
      var r = minSep(s);
      var h = Math.min(Math.max(0.006 * Math.sqrt(r * r * r / M), hmin), hmax);
      if (h > budget - t) h = budget - t;
      step4(s, m, h);
      t += h; n++;
    }
    return { t: t, n: n };
  }
  /* Which body has left, if any. Distance alone is not enough — one of them can swing
     wide and come back — so it also has to be moving outward and clear of the pair it
     left behind. Same test as tools/ghost_tally.py. */
  function escaper(s, m) {
    for (var i = 0; i < 3; i++) {
      var o = [0, 1, 2].filter(function (j) { return j !== i; });
      var mo = m[o[0]] + m[o[1]];
      var cx = (m[o[0]] * s[2 * o[0]] + m[o[1]] * s[2 * o[1]]) / mo;
      var cy = (m[o[0]] * s[2 * o[0] + 1] + m[o[1]] * s[2 * o[1] + 1]) / mo;
      var ux = (m[o[0]] * s[6 + 2 * o[0]] + m[o[1]] * s[6 + 2 * o[1]]) / mo;
      var uy = (m[o[0]] * s[7 + 2 * o[0]] + m[o[1]] * s[7 + 2 * o[1]]) / mo;
      var rx = s[2 * i] - cx, ry = s[2 * i + 1] - cy;
      var vx = s[6 + 2 * i] - ux, vy = s[7 + 2 * i] - uy;
      var d = Math.hypot(rx, ry), mu = m[i] * mo / (m[i] + mo);
      var e = 0.5 * mu * (vx * vx + vy * vy) - m[i] * mo / d;
      var gap = Math.hypot(s[2 * o[0]] - s[2 * o[1]], s[2 * o[0] + 1] - s[2 * o[1] + 1]);
      if (e > 0 && rx * vx + ry * vy > 0 && d > 3 * gap) return i;
    }
    return -1;
  }
  function comet(c, V, pts, col, width) {
    var g = c._g, n = pts.length;
    if (n < 2) return;
    /* the trail fades back in four bands rather than per segment, which keeps it cheap */
    for (var b = 0; b < 4; b++) {
      var lo = Math.floor(n * b / 4), hi = Math.floor(n * (b + 1) / 4);
      g.beginPath();
      for (var i = Math.max(lo - 1, 0); i < hi; i++) {
        var X = V.x(pts[i][0]), Y = V.y(pts[i][1]);
        if (i === Math.max(lo - 1, 0)) g.moveTo(X, Y); else g.lineTo(X, Y);
      }
      g.globalAlpha = 0.12 + 0.28 * b;
      g.strokeStyle = col;
      g.lineWidth = (width || 1.6) * (0.55 + 0.2 * b);
      g.stroke();
    }
    g.globalAlpha = 1;
  }
  function clone(s) { return s.slice(0); }

  /* ---------------------------------------------------------------- canvas helpers */
  function canvas(root, w, h) {
    var c = el("canvas"); var dpr = Math.min(window.devicePixelRatio || 1, 2);
    c.width = w * dpr; c.height = h * dpr; c.style.aspectRatio = w + " / " + h;
    var g = c.getContext("2d"); g.scale(dpr, dpr);
    c._w = w; c._h = h; c._g = g;
    root.appendChild(c);
    return c;
  }
  function clear(c, fade) {
    var g = c._g;
    g.globalCompositeOperation = "source-over";
    g.fillStyle = fade ? "rgba(7,11,19," + fade + ")" : "#070b13";
    g.fillRect(0, 0, c._w, c._h);
  }
  function view(c, span, cx, cy) {
    var s = Math.min(c._w, c._h) / span;
    return { x: function (x) { return c._w / 2 + (x - (cx || 0)) * s; },
             y: function (y) { return c._h / 2 - (y - (cy || 0)) * s; }, s: s };
  }
  function dot(c, V, x, y, r, col) {
    var g = c._g;
    g.beginPath(); g.arc(V.x(x), V.y(y), r, 0, 6.2832); g.fillStyle = col; g.fill();
  }
  /* A loop that runs when it is both wanted and on screen. Wanted is the reader's
     doing — the Run and Pause buttons — and on screen is the observer's, so scrolling
     past a demo stops it and scrolling back starts it again where it left off. */
  function rafLoop(fn) {
    var on = false, id = 0, wanted = false, vis = true;
    function tick() { if (!on) return; fn(); id = requestAnimationFrame(tick); }
    function sync() {
      if (wanted && vis) { if (!on) { on = true; tick(); } }
      else { on = false; cancelAnimationFrame(id); }
    }
    return { start: function () { wanted = true; sync(); },
             stop: function () { wanted = false; sync(); },
             setVisible: function (v) { vis = v; sync(); },
             get running() { return wanted; } };
  }
  function onScreen(node, loop) {
    if (!("IntersectionObserver" in window)) return;
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { loop.setVisible(e.isIntersecting); });
    }, { rootMargin: "200px" }).observe(node);
  }

  /* ---------------------------------------------------------------- 1  inverse square */
  function inverse(root) {
    var s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", "0 0 640 190"); s.setAttribute("role", "img");
    s.setAttribute("aria-label", "two masses and the pull between them");
    root.appendChild(s);
    function mk(tag, at) { var e = document.createElementNS(s.namespaceURI, tag); for (var k in at) e.setAttribute(k, at[k]); return e; }
    var barBg = mk("rect", { x: 60, y: 140, width: 520, height: 16, rx: 8, fill: C.line });
    var bar = mk("rect", { x: 60, y: 140, height: 16, rx: 8, fill: C.teal });
    var a = mk("circle", { cx: 90, cy: 70, r: 22, fill: C.gold, stroke: C.ink, "stroke-width": 2 });
    var b = mk("circle", { cx: 400, cy: 70, r: 16, fill: C.violet, stroke: C.ink, "stroke-width": 2 });
    var link = mk("line", { x1: 90, y1: 70, x2: 400, y2: 70, stroke: C.mute, "stroke-dasharray": "5 5" });
    var txt = mk("text", { x: 60, y: 128, "font-size": 13, fill: C.mute }); txt.textContent = "";
    [link, a, b, barBg, bar, txt].forEach(function (n) { s.appendChild(n); });
    var d = range(10, 100, 30), m2 = range(1, 10, 3), out = readout("");
    function draw() {
      var dist = d.value / 10, mm = +m2.value;
      var F = mm / (dist * dist);
      var Fmax = 10 / 1;
      b.setAttribute("cx", 90 + dist * 55);
      b.setAttribute("r", 8 + mm * 1.6);
      link.setAttribute("x2", 90 + dist * 55);
      var wpx = Math.max(2, Math.min(1, F / Fmax) * 520);
      bar.setAttribute("width", wpx);
      txt.textContent = "pull";
      out.textContent = "distance " + fmt(dist, 1) + " · weight " + mm + " · pull " + (F < 0.01 ? F.toExponential(1) : fmt(F, 3));
    }
    d.oninput = draw; m2.oninput = draw;
    root.appendChild(row([label("distance", [d]), label("the other weight", [m2]), out]));
    root.appendChild(note("Double the distance and the bar drops to a quarter. Double the weight and it doubles. That is the whole of Newton's law in two sliders."));
    draw();
  }

  /* ---------------------------------------------------------------- 2  Kepler */
  function kepler(root) {
    var c = canvas(root, 640, 340);
    var ecc = range(0, 85, 50), speed = range(1, 40, 14), out = readout("");
    var th = 0, sweeps = [], last = 0;
    function draw() {
      var e = ecc.value / 100, a = 1.0;
      clear(c);
      var V = view(c, 2.9, e * a, 0);
      var g = c._g;
      // the ellipse
      g.beginPath();
      for (var k = 0; k <= 240; k++) {
        var t = k / 240 * 6.2832, r = a * (1 - e * e) / (1 + e * Math.cos(t));
        var x = r * Math.cos(t), y = r * Math.sin(t);
        if (k === 0) g.moveTo(V.x(x), V.y(y)); else g.lineTo(V.x(x), V.y(y));
      }
      g.strokeStyle = C.mute; g.lineWidth = 1.2; g.stroke();
      // equal areas: wedges swept in equal time
      var r0 = a * (1 - e * e) / (1 + e * Math.cos(th));
      sweeps.forEach(function (w, i) {
        g.beginPath(); g.moveTo(V.x(0), V.y(0));
        w.forEach(function (p, j) { g.lineTo(V.x(p[0]), V.y(p[1])); });
        g.closePath(); g.fillStyle = i % 2 ? "rgba(47,196,189,.30)" : "rgba(240,181,69,.30)"; g.fill();
      });
      dot(c, V, 0, 0, 9, C.gold);
      dot(c, V, r0 * Math.cos(th), r0 * Math.sin(th), 6, C.teal);
      var vel = Math.sqrt((1 + e * e + 2 * e * Math.cos(th)) / (1 - e * e));
      out.textContent = "e = " + fmt(e, 2) + " · distance " + fmt(r0, 2) + " · speed " + fmt(vel, 2) + " (fast when close, slow when far)";
    }
    var loop = rafLoop(function () {
      var e = ecc.value / 100;
      var r = 1 * (1 - e * e) / (1 + e * Math.cos(th));
      th += (speed.value / 1400) / (r * r) * (1 - e * e);       // equal areas in equal times
      if (th > 6.2832) { th -= 6.2832; }
      var pts = sweeps[sweeps.length - 1];
      if (!pts || pts.length > 26) { sweeps.push(pts = []); if (sweeps.length > 6) sweeps.shift(); }
      pts.push([r * Math.cos(th), r * Math.sin(th)]);
      draw();
    });
    var go = btn("Pause");
    go.onclick = function () { if (loop.running) { loop.stop(); go.textContent = "Run"; } else { loop.start(); go.textContent = "Pause"; } };
    root.appendChild(row([go, label("squash", [ecc]), label("speed", [speed]), out]));
    root.appendChild(note("One body, one fixed pull, and the shape closes and repeats forever. The shaded wedges are swept in equal times — Kepler's second law, which is angular momentum not changing."));
    ecc.oninput = function () { sweeps = []; th = 0; draw(); };
    draw();
    onScreen(c, loop);
    if (!RM) loop.start(); else go.textContent = "Run";
  }

  /* ---------------------------------------------------------------- 3  the sandbox */
  function sim(root) {
    var c = canvas(root, 640, 420);
    var PRE = {
      pythagoras: { name: "Burrau's Pythagorean problem (1913)", span: 6,
        note: "Weights 3, 4 and 5, at rest, at the corners of a 3-4-5 triangle. Nothing is moving at the start and nothing is arranged; it runs for about sixty time units of near misses and then throws the lightest one out for good, leaving the other two paired up.",
        m: [3, 4, 5], s: [1, 3, -2, -1, 1, -1, 0, 0, 0, 0, 0, 0] },
      slingshot: { name: "a pair and an intruder", span: 8,
        note: "Two bodies in a circular orbit and a third one arriving. Most of the time it leaves again with more speed than it came in with, and the pair pays for it by drawing closer together.",
        m: [1, 1, 1], s: [-0.5, 0, 0.5, 0, 4.2, 2.2, 0, -0.707, 0, 0.707, -0.62, -0.33] },
      wobble: { name: "the figure eight, nudged", span: 3.4,
        note: "The closed orbit with a thousandth added to one starting speed. It holds the shape for a few laps, wanders, and comes apart.",
        m: [1, 1, 1], s: null, wobble: 1e-3 },
      drop: { name: "three dropped from rest", span: 5,
        note: "Three equal weights, no motion at all to start with. Zero spin, so all three are allowed to meet — and they very nearly do.",
        m: [1, 1, 1], s: [-1, 0.3, 1, 0.1, 0.1, -1.4, 0, 0, 0, 0, 0, 0] },
      random: { name: "a random throw", span: 4.5, note: "Whatever the shuffle turns up. Press it again.", m: [1, 1, 1], s: null },
      eight: { name: "the figure eight, exactly", span: 3.4,
        note: "For comparison: the one start in this list that repeats forever.", m: [1, 1, 1], s: null }
    };
    var order = ["pythagoras", "slingshot", "wobble", "drop", "random", "eight"];
    var sel = pick(order.map(function (k) { return [k, PRE[k].name]; }), "pythagoras");
    var play = btn("Pause"), again = btn("Shuffle", "alt"), reset = btn("Restart", "alt");
    var sp = range(1, 40, 16), out = readout(""), eout = readout(""), what = el("p", { class: "note" });
    var m = [1, 1, 1], s = null, E0 = 0, t = 0, trails = [[], [], []], span = 4, target = 4, gone = null, key = "pythagoras";

    function eightState(w) {
      var o = (ORB.filter(function (q) { return q.id === "figure-eight"; })[0] || { v: [0.3471169, 0.5327249] });
      var st = sdState(o.v[0], o.v[1]);
      if (w) st[6] += w;
      return st;
    }
    function randomState() {
      var st = [], vs = [], vx = 0, vy = 0, k;
      for (k = 0; k < 3; k++) st.push((Math.random() * 2 - 1) * 1.2, (Math.random() * 2 - 1) * 1.2);
      for (k = 0; k < 3; k++) { var ax = (Math.random() * 2 - 1) * 0.45, ay = (Math.random() * 2 - 1) * 0.45; vs.push(ax, ay); vx += ax; vy += ay; }
      for (k = 0; k < 3; k++) { vs[2 * k] -= vx / 3; vs[2 * k + 1] -= vy / 3; }
      st = st.concat(vs);
      return minSep(st) > 0.45 ? st : randomState();
    }
    function setup(k) {
      key = k; var P0 = PRE[k];
      m = P0.m.slice(0);
      s = P0.s ? P0.s.slice(0) : (k === "random" ? randomState() : eightState(P0.wobble || 0));
      t = 0; gone = null; trails = [[], [], []];
      span = target = P0.span;
      E0 = energy(s, m);
      what.textContent = P0.note;
      again.textContent = k === "random" ? "Shuffle" : "Shuffle a random one";
    }
    function fit() {
      /* follow the action: the frame grows to hold whatever is still in the fight and
         lets an escaper go once it is well clear */
      var d = [];
      for (var i = 0; i < 3; i++) d.push(Math.hypot(s[2 * i], s[2 * i + 1]));
      d.sort(function (a, b) { return a - b; });
      var want = Math.max(2.2, Math.min(d[1] * 3.4, 26));
      target = want;
      span += (target - span) * 0.04;
    }
    function draw() {
      clear(c);
      var V = view(c, span), g = c._g;
      for (var i = 0; i < 3; i++) {
        comet(c, V, trails[i], BODY[i], 1.8);
        var r = 3.2 + 2.6 * Math.cbrt(m[i]);
        g.beginPath(); g.arc(V.x(s[2 * i]), V.y(s[2 * i + 1]), r + 5, 0, 6.2832);
        g.fillStyle = BODY[i]; g.globalAlpha = 0.18; g.fill(); g.globalAlpha = 1;
        dot(c, V, s[2 * i], s[2 * i + 1], r, BODY[i]);
      }
      var E = energy(s, m), dr = Math.abs((E - E0) / E0);
      out.textContent = "t = " + fmt(t, 1) + " · closest pair " + fmt(minSep(s), 3) + " · frame " + fmt(span, 1);
      eout.textContent = "energy error " + (dr < 1e-9 ? "under 1e-9" : dr.toExponential(1)) +
        (gone === null ? " · all three still in it" : " · body " + (gone + 1) + " left at t = " + fmt(gone_t, 0));
    }
    var gone_t = 0;
    var loop = rafLoop(function () {
      var budget = 0.004 * sp.value * sp.value / 8 + 0.01;
      var r = advance(s, m, budget);
      t += r.t;
      for (var i = 0; i < 3; i++) {
        trails[i].push([s[2 * i], s[2 * i + 1]]);
        if (trails[i].length > 1600) trails[i].shift();
      }
      if (gone === null) {
        var e = escaper(s, m);
        if (e >= 0) { gone = e; gone_t = t; }
      }
      fit();
      draw();
      if (t > 400) loop.stop();
    });
    play.onclick = function () { if (loop.running) { loop.stop(); play.textContent = "Run"; } else { loop.start(); play.textContent = "Pause"; } };
    reset.onclick = function () { setup(key); draw(); };
    again.onclick = function () { sel.value = "random"; setup("random"); draw(); };
    sel.onchange = function () { setup(sel.value); draw(); };
    root.appendChild(row([play, reset, again, sel]));
    root.appendChild(row([label("speed", [sp]), out]));
    root.appendChild(el("div", { class: "row" }, [eout]));
    root.appendChild(what);
    root.appendChild(note("The step is not fixed: before every move it is set from the closest pair, because that is what goes wrong. The energy error beside the clock is the check on it. Burrau's problem at a fixed step comes out with the energy wrong by a factor of a thousand and the wrong body thrown out; even with the step chosen this way, a plain leapfrog ejects a different body depending on how fine you make it, which is why these demos run the fourth-order version. Where the escaper ends up is still nobody's to reproduce — only that it was the lightest."));
    setup("pythagoras"); draw();
    onScreen(c, loop);
    if (!RM) loop.start(); else play.textContent = "Run";
  }

  /* ---------------------------------------------------------------- 4  the ten */
  function integrals(root) {
    var c = canvas(root, 640, 300);
    var s = sdState(0.28, 0.45), m = [1, 1, 1], t = 0, trails = [[], [], []];
    var E0 = energy(s, m), L0 = spin(s, m), P0 = momentum(s, m);
    var tbl = el("div", { class: "kvgrid" });
    var cells = {};
    [["energy", "never changes"], ["spin", "never changes"], ["momentum x", "never changes"],
     ["momentum y", "never changes"], ["time", "runs on"]].forEach(function (r) {
      tbl.appendChild(el("b", { text: r[0] }));
      var sp2 = el("span", { class: "readout" }); cells[r[0]] = sp2; tbl.appendChild(sp2);
    });
    function draw() {
      clear(c);
      var V = view(c, 4.2), g = c._g;
      for (var i = 0; i < 3; i++) {
        g.beginPath();
        trails[i].forEach(function (p, j) { var X = V.x(p[0]), Y = V.y(p[1]); if (j === 0) g.moveTo(X, Y); else g.lineTo(X, Y); });
        g.strokeStyle = BODY[i]; g.globalAlpha = .7; g.lineWidth = 1.4; g.stroke(); g.globalAlpha = 1;
        dot(c, V, s[2 * i], s[2 * i + 1], 5, BODY[i]);
      }
      var p = momentum(s, m);
      cells["energy"].textContent = fmt(energy(s, m), 8);
      cells["spin"].textContent = fmt(spin(s, m), 8);
      cells["momentum x"].textContent = fmt(p[0], 8);
      cells["momentum y"].textContent = fmt(p[1], 8);
      cells["time"].textContent = fmt(t, 2);
    }
    var loop = rafLoop(function () {
      for (var k = 0; k < 10; k++) { step(s, m, 0.0012, 0); t += 0.0012; }
      for (var i = 0; i < 3; i++) { trails[i].push([s[2 * i], s[2 * i + 1]]); if (trails[i].length > 700) trails[i].shift(); }
      draw();
    });
    var go = btn("Pause"), rs = btn("Reset", "alt");
    go.onclick = function () { if (loop.running) { loop.stop(); go.textContent = "Run"; } else { loop.start(); go.textContent = "Pause"; } };
    rs.onclick = function () { s = sdState(0.28, 0.45); t = 0; trails = [[], [], []]; draw(); };
    root.appendChild(row([go, rs]));
    root.appendChild(tbl);
    root.appendChild(note("Four of the ten, ticking away while the three bodies do whatever they like. They hold to eight decimal places, and they are not enough to pin the motion down — that is the whole difficulty in one panel."));
    draw(); onScreen(c, loop); if (!RM) loop.start(); else go.textContent = "Run";
  }

  /* ---------------------------------------------------------------- 5  divergence */
  function chaos(root) {
    var c = canvas(root, 640, 400);
    var plot = canvas(root, 640, 190);
    var K = 48;
    var STARTS = {
      burrau: { name: "Burrau's problem, 48 times over", m: [3, 4, 5], span: 6, T: 150,
        s: [1, 3, -2, -1, 1, -1, 0, 0, 0, 0, 0, 0],
        note: "Weights 3, 4 and 5 dropped from rest at the corners of a 3-4-5 triangle — forty-eight copies of it, each moved at the start by the distance on the slider. They dance as one, fray, and then throw a body out; and the copies do not agree about which body it is." },
      tangle: { name: "a bound tangle", m: [1, 1, 1], span: 4.5, T: 60,
        s: null, v: [0.28, 0.45],
        note: "Three equal weights that mill about for a while and then break up. The copies part company long before that." },
      island: { name: "beside the figure eight — the quiet one", m: [1, 1, 1], span: 3.4, T: 60,
        s: null, v: [0.3671, 0.5327],
        note: "Two hundredths away from the figure eight, and this one does not fray: the copies spread a little and then stop spreading. Not everywhere in this problem is chaotic, and the islands that are not are what the KAM theorem is about." }
    };
    var sel = pick(Object.keys(STARTS).map(function (k) { return [k, STARTS[k].name]; }), "burrau");
    var nud = range(3, 14, 6), sp = range(1, 40, 26);
    var go = btn("Pause"), rs = btn("Reset", "alt"), out = readout("");
    var m = [1, 1, 1], base = null, ghosts = [], t = 0, hist = [], trail = [[], [], []];
    var span = 5, tally = [0, 0, 0], left = [], cfg = null, done = 0;
    var bars = el("div", { class: "tally" }), rows = [];
    function buildBars() {
      bars.innerHTML = ""; rows = [];
      for (var i = 0; i < 3; i++) {
        bars.appendChild(el("span", { text: "copies that threw out body " + (i + 1) + " (weight " + m[i] + ")" }));
        var bar = el("div", { class: "bar" + (i === 1 ? " t" : "") }), fill = el("i");
        bar.appendChild(fill); bars.appendChild(bar);
        var n = el("span", { text: "0" }); bars.appendChild(n);
        rows.push({ fill: fill, n: n });
      }
    }
    function setup() {
      cfg = STARTS[sel.value];
      m = cfg.m.slice(0);
      var e = Math.pow(10, -nud.value);
      base = cfg.s ? cfg.s.slice(0) : sdState(cfg.v[0], cfg.v[1]);
      ghosts = [];
      for (var k = 0; k < K; k++) {
        var g = base.slice(0), a = 6.2832 * k / K;
        g[0] += e * Math.cos(a); g[1] += e * Math.sin(a);
        ghosts.push(g);
      }
      left = []; for (k = 0; k < K; k++) left.push(-1);
      tally = [0, 0, 0]; done = 0;
      t = 0; hist = []; trail = [[], [], []]; span = cfg.span;
      buildBars();
      out.textContent = K + " copies, each moved by " + e.toExponential(0) + " at the start";
    }
    function spread() {
      var d = 0;
      for (var k = 0; k < K; k++) {
        var q = 0;
        for (var i = 0; i < 12; i++) { var u = ghosts[k][i] - base[i]; q += u * u; }
        d += Math.sqrt(q);
      }
      return d / K;
    }
    function fit() {
      var d = [];
      for (var i = 0; i < 3; i++) d.push(Math.hypot(base[2 * i], base[2 * i + 1]));
      d.sort(function (a, b) { return a - b; });
      span += (Math.max(cfg.span, Math.min(d[1] * 3.2, 30)) - span) * 0.04;
    }
    function draw() {
      clear(c);
      var V = view(c, span), g = c._g, i, k;
      for (k = 0; k < K; k++) {
        g.globalAlpha = 0.55;
        for (i = 0; i < 3; i++) dot(c, V, ghosts[k][2 * i], ghosts[k][2 * i + 1], 1.8, BODY[i]);
      }
      g.globalAlpha = 1;
      for (i = 0; i < 3; i++) {
        comet(c, V, trail[i], BODY[i], 1.5);
        dot(c, V, base[2 * i], base[2 * i + 1], 6.5, "#ffffff");
        dot(c, V, base[2 * i], base[2 * i + 1], 4.6, BODY[i]);
      }
      var pg = plot._g;
      pg.fillStyle = C.panel; pg.fillRect(0, 0, plot._w, plot._h);
      pg.strokeStyle = C.line; pg.lineWidth = 1;
      for (var q = -13; q <= 3; q += 2) {
        var Y = 172 - (q + 14) / 17 * 154;
        pg.beginPath(); pg.moveTo(44, Y); pg.lineTo(632, Y); pg.stroke();
        pg.fillStyle = C.mute; pg.font = "11px system-ui"; pg.fillText("1e" + q, 4, Y + 4);
      }
      pg.beginPath();
      hist.forEach(function (h, j) {
        var X = 44 + h[0] / cfg.T * 588, Y = 172 - (Math.log(Math.max(h[1], 1e-14)) / Math.LN10 + 14) / 17 * 154;
        if (j === 0) pg.moveTo(X, Y); else pg.lineTo(X, Y);
      });
      pg.strokeStyle = C.teal; pg.lineWidth = 2.6; pg.stroke();
      pg.fillStyle = C.mute; pg.font = "11px system-ui";
      pg.fillText("how far the copies have wandered from the original", 48, 16);
      var n = done || 1;
      for (i = 0; i < 3; i++) {
        rows[i].fill.style.setProperty("--v", tally[i] / K);
        rows[i].n.textContent = tally[i] + (done ? " (" + Math.round(100 * tally[i] / K) + "%)" : "");
      }
      var e = Math.pow(10, -nud.value), d = spread();
      var fitpts = hist.filter(function (h) { return h[1] > e * 30 && h[1] < 1; });
      var tail = "";
      if (fitpts.length > 12) {
        var nn = fitpts.length, sx = 0, sy = 0, sxx = 0, sxy = 0;
        fitpts.forEach(function (h) { var x = h[0], y = Math.log(h[1]); sx += x; sy += y; sxx += x * x; sxy += x * y; });
        var sl = (nn * sxy - sx * sy) / (nn * sxx - sx * sx);
        if (sl > 0) tail = " · doubling every " + fmt(0.693 / sl, 2) + " time units";
      }
      out.textContent = "t = " + fmt(t, 1) + " · started " + e.toExponential(0) + " apart · now " +
        (d < 1e-3 ? d.toExponential(1) : fmt(d, 3)) + tail +
        (done ? " · " + done + " of " + K + " have thrown a body out" : "");
    }
    var loop = rafLoop(function () {
      var budget = 0.0016 * sp.value + 0.004;
      advance(base, m, budget);
      for (var k = 0; k < K; k++) {
        advance(ghosts[k], m, budget);
        if (left[k] < 0) {
          var e = escaper(ghosts[k], m);
          if (e >= 0) { left[k] = e; tally[e]++; done++; }
        }
      }
      t += budget;
      for (var i2 = 0; i2 < 3; i2++) { trail[i2].push([base[2 * i2], base[2 * i2 + 1]]); if (trail[i2].length > 1100) trail[i2].shift(); }
      hist.push([t, spread()]);
      fit();
      draw();
      if (t > cfg.T) { loop.stop(); go.textContent = "Run it again"; }
    });
    go.onclick = function () { if (loop.running) { loop.stop(); go.textContent = "Run"; } else { if (t > cfg.T) setup(); loop.start(); go.textContent = "Pause"; } };
    rs.onclick = function () { setup(); draw(); };
    nud.oninput = function () { setup(); draw(); };
    sel.onchange = function () { setup(); draw(); };
    root.appendChild(row([go, rs, sel]));
    root.appendChild(row([label("how far apart they start", [nud]), label("speed", [sp]), ]));
    root.appendChild(el("div", { class: "row" }, [out]));
    root.appendChild(bars);
    root.appendChild(note("The white dots are the original and the small ones are the copies. Watch the tally: with a billionth of a difference at the start, the copies do not agree about which body ends up thrown out. Some of that disagreement is the arithmetic rather than the physics — which is the same point said twice, and the reason the numbers page exists."));
    setup(); draw(); onScreen(c, loop);
    if (!RM) { loop.start(); go.textContent = "Pause"; }
  }

  /* ---------------------------------------------------------------- 6  the fence */
  function zvc(root) {
    var c = canvas(root, 640, 400);
    var mu = range(1, 50, 25), cj = range(280, 420, 360), out = readout("");
    function lagr(m2) {
      function dO(x) {
        var r1 = Math.abs(x + m2), r2 = Math.abs(x - 1 + m2);
        return x - (1 - m2) * (x + m2) / (r1 * r1 * r1) - m2 * (x - 1 + m2) / (r2 * r2 * r2);
      }
      function root(a, b) { var fa = dO(a); for (var i = 0; i < 90; i++) { var m = (a + b) / 2, fm = dO(m); if ((fm > 0) === (fa > 0)) { a = m; fa = fm; } else b = m; } return (a + b) / 2; }
      var e = 1e-7;
      return [[root(-m2 + e, 1 - m2 - e), 0], [root(1 - m2 + e, 2.5), 0], [root(-2.5, -m2 - e), 0],
              [0.5 - m2, Math.sqrt(3) / 2], [0.5 - m2, -Math.sqrt(3) / 2]];
    }
    function draw() {
      var m2 = mu.value / 100, Cj = cj.value / 100;
      var g = c._g, w = c._w, h = c._h;
      /* The field is computed once per CSS pixel on an offscreen canvas and then drawn
         to fill this one. putImageData ignores the device-pixel scaling on the context,
         so writing it straight in would paint one corner of a retina canvas. */
      var off = document.createElement("canvas");
      off.width = w; off.height = h;
      var og = off.getContext("2d"), img = og.createImageData(w, h);
      var span = 3.4, sc = Math.min(w, h) / span;
      for (var py = 0; py < h; py++) for (var px = 0; px < w; px++) {
        var x = (px - w / 2) / sc, y = (h / 2 - py) / sc;
        var r1 = Math.hypot(x + m2, y), r2 = Math.hypot(x - 1 + m2, y);
        var Om = 0.5 * (x * x + y * y) + (1 - m2) / r1 + m2 / r2;
        var vv = 2 * Om - Cj;
        var k = (py * w + px) * 4;
        if (vv < 0) { img.data[k] = 12; img.data[k + 1] = 16; img.data[k + 2] = 26; }      // shut out
        else {
          var u = Math.min(Math.sqrt(vv) / 2.2, 1);
          img.data[k] = 20 + u * 60; img.data[k + 1] = 40 + u * 150; img.data[k + 2] = 60 + u * 140;
        }
        img.data[k + 3] = 255;
      }
      og.putImageData(img, 0, 0);
      g.drawImage(off, 0, 0, w, h);
      var V = view(c, span);
      dot(c, V, -m2, 0, 9, C.gold); dot(c, V, 1 - m2, 0, 6, C.teal);
      lagr(m2).forEach(function (p, i) {
        dot(c, V, p[0], p[1], 5, i < 3 ? C.violet : C.red);
        g.fillStyle = i < 3 ? C.violet : C.red; g.font = "bold 12px system-ui";
        g.fillText("L" + (i + 1), V.x(p[0]) + 8, V.y(p[1]) - 6);
      });
      out.textContent = "mass ratio \u03bc = " + fmt(m2, 2) + " \u00b7 Jacobi constant C = " + fmt(Cj, 2) +
        " \u00b7 the dark region is where this body cannot go";
    }
    mu.oninput = draw; cj.oninput = draw;
    root.appendChild(row([label("mass ratio", [mu]), label("Jacobi constant", [cj]), out]));
    root.appendChild(note("Bring the constant down and watch the neck open at L1, then the back door at L2. Every low-energy transfer ever flown goes through those gates, and the picture is computed per pixel from 2Ω − C."));
    draw();
  }

  /* ---------------------------------------------------------------- 7  the two shapes */
  function shapes(root) {
    var c = canvas(root, 640, 360);
    var kind = pick([["tri", "Lagrange's triangle"], ["line", "Euler's line"]], "tri");
    var m1 = range(5, 40, 10), m3 = range(5, 40, 10), out = readout("");
    var s = null, m = [1, 1, 1], trails = [[], [], []];
    /* Three on a line, spinning about the balance point. Bodies at -1, 0 and x with
       weights m1, m2, m3: both outer bodies have to need the same ω, which fixes x.
       There is no formula for it — this hunts for it by bisection, every time. */
    function lineConfig(m1v, m2v, m3v) {
      function mism(x) {
        var M = m1v + m2v + m3v;
        var xc = (m1v * -1 + m3v * x) / M;
        var w1 = (m2v + m3v / ((x + 1) * (x + 1))) / (xc + 1);
        var w3 = (m1v / ((x + 1) * (x + 1)) + m2v / (x * x)) / (x - xc);
        return w1 - w3;
      }
      var lo = 0.02, hi = 40, flo = mism(lo);
      for (var i = 0; i < 200; i++) {
        var mid = Math.sqrt(lo * hi), fm = mism(mid);
        if ((fm > 0) === (flo > 0)) { lo = mid; flo = fm; } else hi = mid;
      }
      var x = Math.sqrt(lo * hi);
      var M2 = m1v + m2v + m3v, xc2 = (m1v * -1 + m3v * x) / M2;
      var om2 = (m2v + m3v / ((x + 1) * (x + 1))) / (xc2 + 1);
      return { x: x, xc: xc2, om: Math.sqrt(Math.abs(om2)) };
    }
    function setup() {
      m = [m1.value / 10, 1, m3.value / 10];
      trails = [[], [], []];
      if (kind.value === "tri") {
        var M = m[0] + m[1] + m[2], a = 1.0;
        var om = Math.sqrt(M / (a * a * a));
        var pos = [[0, 0], [1, 0], [0.5, Math.sqrt(3) / 2]];
        var cx = (m[0] * pos[0][0] + m[1] * pos[1][0] + m[2] * pos[2][0]) / M;
        var cy = (m[0] * pos[0][1] + m[1] * pos[1][1] + m[2] * pos[2][1]) / M;
        s = [];
        pos.forEach(function (p) { s.push(p[0] - cx, p[1] - cy); });
        pos.forEach(function (p) { s.push(-om * (p[1] - cy), om * (p[0] - cx)); });
        out.textContent = "any three weights, one equilateral triangle, ω = " + fmt(om, 4) + " — no equation to solve";
      } else {
        var cfg = lineConfig(m[0], m[1], m[2]);
        var xs = [-1 - cfg.xc, 0 - cfg.xc, cfg.x - cfg.xc];
        s = [xs[0], 0, xs[1], 0, xs[2], 0];
        xs.forEach(function (px) { s.push(0, cfg.om * px); });
        var x = cfg.x, om2 = cfg.om;
        out.textContent = "spacing solved by hunting: the far body sits at " + fmt(x, 5) + " · ω = " + fmt(om2, 4);
      }
    }
    function draw() {
      clear(c);
      var V = view(c, 3.4), g = c._g;
      for (var i = 0; i < 3; i++) {
        g.beginPath();
        trails[i].forEach(function (p, j) { var X = V.x(p[0]), Y = V.y(p[1]); if (j === 0) g.moveTo(X, Y); else g.lineTo(X, Y); });
        g.strokeStyle = BODY[i]; g.globalAlpha = .8; g.lineWidth = 1.4; g.stroke(); g.globalAlpha = 1;
        dot(c, V, s[2 * i], s[2 * i + 1], 4 + 3 * m[i], BODY[i]);
      }
      g.strokeStyle = C.mute; g.setLineDash([4, 4]); g.beginPath();
      g.moveTo(V.x(s[0]), V.y(s[1])); g.lineTo(V.x(s[2]), V.y(s[3])); g.lineTo(V.x(s[4]), V.y(s[5])); g.closePath();
      g.stroke(); g.setLineDash([]);
    }
    var loop = rafLoop(function () {
      for (var k = 0; k < 8; k++) step(s, m, 0.0015, 0);
      for (var i = 0; i < 3; i++) { trails[i].push([s[2 * i], s[2 * i + 1]]); if (trails[i].length > 500) trails[i].shift(); }
      draw();
    });
    var go = btn("Pause");
    go.onclick = function () { if (loop.running) { loop.stop(); go.textContent = "Run"; } else { loop.start(); go.textContent = "Pause"; } };
    [m1, m3].forEach(function (r) { r.oninput = function () { setup(); draw(); }; });
    kind.onchange = function () { setup(); draw(); };
    root.appendChild(row([go, kind, label("first weight", [m1]), label("third weight", [m3]), ]));
    root.appendChild(el("div", { class: "row" }, [out]));
    root.appendChild(note("The triangle holds its shape for any weights you set. The line has to be re-solved every time you move a slider, and the solving is a hunt, because there is no formula for a fifth-degree equation."));
    setup(); draw(); onScreen(c, loop); if (!RM) loop.start(); else go.textContent = "Run";
  }

  /* ---------------------------------------------------------------- 8  the closed ones */
  function eight(root) {
    var c = canvas(root, 640, 420);
    var opts = ORB.map(function (o) { return [o.id, o.name + " · T = " + o.period.toFixed(3)]; });
    var sel = pick(opts.length ? opts : [["figure-eight", "figure eight"]], "figure-eight");
    var go = btn("Pause"), tr = btn("Clear trails", "alt");
    var nud = range(0, 10, 0), sp = range(1, 40, 22), out = readout(""), out2 = readout("");
    var m = [1, 1, 1], s = null, t = 0, trails = [[], [], []], cur = null, span = 3.4, ref = [], off = null, offAt = 0;
    function nudge() { return nud.value == 0 ? 0 : Math.pow(10, -7 + nud.value * 0.5); }
    function setup() {
      cur = ORB.filter(function (o) { return o.id === sel.value; })[0] ||
            { v: [0.3471169, 0.5327249], period: 6.325914, closes: 0, name: "figure eight" };
      s = sdState(cur.v[0], cur.v[1]);
      var e = nudge();
      if (e) s[6] += e;
      t = 0; trails = [[], [], []]; off = null; offAt = 0;
      /* the exact orbit, drawn once and left on the canvas as the track to wander off */
      ref = [[], [], []];
      var q = sdState(cur.v[0], cur.v[1]), mx = 0;
      var N = 1400, h = cur.period / N;
      for (var k = 0; k < N; k++) {
        step(q, m, h, 0);
        for (var i = 0; i < 3; i++) {
          ref[i].push([q[2 * i], q[2 * i + 1]]);
          mx = Math.max(mx, Math.abs(q[2 * i]), Math.abs(q[2 * i + 1]));
        }
      }
      span = Math.max(2.4, mx * 2.3);
      out.textContent = cur.name + " · period " + cur.period.toFixed(6) + " · closes to " +
        (cur.closes ? cur.closes.toExponential(1) : "—");
      out2.textContent = e ? "started " + e.toExponential(0) + " off the exact orbit" : "started exactly on it";
    }
    function fromTrack() {
      /* how far the nearest point of the drawn orbit is from where body 1 now is */
      var best = 1e9;
      for (var k = 0; k < ref[0].length; k += 3) {
        var dx = ref[0][k][0] - s[0], dy = ref[0][k][1] - s[1];
        var d = dx * dx + dy * dy;
        if (d < best) best = d;
      }
      return Math.sqrt(best);
    }
    function draw() {
      clear(c);
      var V = view(c, span), g = c._g, i;
      g.globalAlpha = 0.30; g.lineWidth = 1.2;
      for (i = 0; i < 3; i++) {
        g.beginPath();
        ref[i].forEach(function (p2, j) { var X = V.x(p2[0]), Y = V.y(p2[1]); if (j === 0) g.moveTo(X, Y); else g.lineTo(X, Y); });
        g.strokeStyle = BODY[i]; g.stroke();
      }
      g.globalAlpha = 1;
      for (i = 0; i < 3; i++) {
        comet(c, V, trails[i], BODY[i], 2);
        dot(c, V, s[2 * i], s[2 * i + 1], 6, BODY[i]);
      }
      g.fillStyle = C.mute; g.font = "12px system-ui";
      g.fillText("t = " + fmt(t, 2) + "  ·  lap " + Math.floor(t / cur.period + 1), 12, 20);
      var d = fromTrack();
      if (off === null && d > 0.15) { off = d; offAt = t; }
      out2.textContent = (nudge() ? "started " + nudge().toExponential(0) + " off · " : "started exactly on it · ") +
        "now " + (d < 1e-4 ? d.toExponential(1) : fmt(d, 4)) + " from the drawn track" +
        (off !== null ? " · left it after " + fmt(offAt / cur.period, 1) + " laps" : "");
    }
    var loop = rafLoop(function () {
      var budget = 0.0012 * sp.value + 0.004;
      advance(s, m, budget);
      t += budget;
      for (var i = 0; i < 3; i++) { trails[i].push([s[2 * i], s[2 * i + 1]]); if (trails[i].length > 2200) trails[i].shift(); }
      draw();
    });
    go.onclick = function () { if (loop.running) { loop.stop(); go.textContent = "Run"; } else { loop.start(); go.textContent = "Pause"; } };
    tr.onclick = function () { trails = [[], [], []]; draw(); };
    sel.onchange = function () { setup(); draw(); };
    nud.oninput = function () { setup(); draw(); };
    root.appendChild(row([go, tr, sel]));
    root.appendChild(row([label("nudge the start", [nud]), label("speed", [sp]), out2]));
    root.appendChild(el("div", { class: "row" }, [out]));
    root.appendChild(note("The faint curve is the orbit as found; the bright bodies are what you are running. Leave the nudge at nothing and they stay on it for as long as you care to watch. Move it one notch — a millionth — and they hold the track for a few laps and then leave it, and where they go after that is nobody's to say."));
    setup(); draw(); onScreen(c, loop); if (!RM) loop.start(); else go.textContent = "Run";
  }

  /* ---------------------------------------------------------------- 9  the two steppers */
  function integrator(root) {
    var c = canvas(root, 640, 300);
    var plot = canvas(root, 640, 200);
    var hs = range(5, 120, 40), go = btn("Run"), rs = btn("Reset", "alt"), out = readout("");
    var m = [1, 1, 1], a = null, b = null, E0 = 0, t = 0, hist = [];
    function setup() {
      var st = [0.97000436, -0.24308753, -0.97000436, 0.24308753, 0, 0,
                0.466203685, 0.43236573, 0.466203685, 0.43236573, -0.93240737, -0.86473146];
      a = clone(st); b = clone(st); E0 = energy(a, m); t = 0; hist = [];
    }
    function draw() {
      clear(c);
      var V = view(c, 3.2), g = c._g, i;
      for (i = 0; i < 3; i++) dot(c, V, a[2 * i], a[2 * i + 1], 5, C.teal);
      for (i = 0; i < 3; i++) dot(c, V, b[2 * i], b[2 * i + 1], 5, C.red);
      g.fillStyle = C.teal; g.font = "bold 13px system-ui"; g.fillText("leapfrog", 12, 22);
      g.fillStyle = C.red; g.fillText("Euler", 12, 42);
      var pg = plot._g;
      pg.fillStyle = C.panel; pg.fillRect(0, 0, plot._w, plot._h);
      pg.strokeStyle = C.line;
      for (var p = -12; p <= 2; p += 2) {
        var Y = 180 - (p + 13) / 15 * 160;
        pg.beginPath(); pg.moveTo(44, Y); pg.lineTo(630, Y); pg.stroke();
        pg.fillStyle = C.mute; pg.font = "11px system-ui"; pg.fillText("1e" + p, 6, Y + 4);
      }
      [[0, C.teal], [1, C.red]].forEach(function (q) {
        pg.beginPath();
        hist.forEach(function (hh, j) {
          var X = 44 + hh[0] / 60 * 586, Y = 180 - (Math.log(Math.max(hh[1 + q[0]], 1e-13)) / Math.LN10 + 13) / 15 * 160;
          if (j === 0) pg.moveTo(X, Y); else pg.lineTo(X, Y);
        });
        pg.strokeStyle = q[1]; pg.lineWidth = 2.2; pg.stroke();
      });
      var ea = Math.abs((energy(a, m) - E0) / E0), eb = Math.abs((energy(b, m) - E0) / E0);
      out.textContent = "step " + fmt(hs.value / 10000, 4) + " · t = " + fmt(t, 1) +
        " · leapfrog error " + ea.toExponential(1) + " · Euler error " + eb.toExponential(1);
    }
    var loop = rafLoop(function () {
      var h = hs.value / 10000;
      for (var k = 0; k < 8; k++) { step(a, m, h, 0); stepEuler(b, m, h); t += h; }
      hist.push([t, Math.abs((energy(a, m) - E0) / E0), Math.abs((energy(b, m) - E0) / E0)]);
      draw();
      if (t > 60) { loop.stop(); go.textContent = "Run again"; }
    });
    go.onclick = function () { if (loop.running) { loop.stop(); go.textContent = "Run"; } else { if (t > 60) setup(); loop.start(); go.textContent = "Pause"; } };
    rs.onclick = function () { setup(); draw(); };
    hs.oninput = function () { setup(); draw(); };
    root.appendChild(row([go, rs, label("step size", [hs])]));
    root.appendChild(el("div", { class: "row" }, [out]));
    root.appendChild(note("Both start on the figure eight. Leapfrog's energy error wobbles and stays put; Euler's climbs and keeps climbing, and its orbit swells until it comes apart. Same equations, same step, four lines of difference."));
    setup(); draw(); onScreen(c, loop);
  }

  /* ---------------------------------------------------------------- 10  the odds */
  function odds(root) {
    var runs = range(50, 600, 200, 50), go = btn("Run them"), out = readout(""), bars = el("div", { class: "tally" });
    var plot = canvas(root, 640, 200);
    root.insertBefore(el("p", { class: "mute small", text: "Random starts, equal weights, zero total momentum. Each one is run for 60 time units and the ending is recorded. The bottom of each well is rounded off at 0.05, so that a near pass cannot throw the arithmetic — the same choice, and the same number, as the chart above." }), plot);
    var rows = {};
    ["one was thrown out", "all three still together"].forEach(function (k) {
      bars.appendChild(el("span", { text: k }));
      var bar = el("div", { class: "bar" }), fill = el("i");
      bar.appendChild(fill); bars.appendChild(bar);
      var n = el("span", { text: "0" }); bars.appendChild(n);
      rows[k] = { fill: fill, n: n };
    });
    function one() {
      var s = [], vx = 0, vy = 0, k;
      for (k = 0; k < 3; k++) s.push((Math.random() * 2 - 1) * 1.1, (Math.random() * 2 - 1) * 1.1);
      var vs = [];
      for (k = 0; k < 3; k++) { var ax = (Math.random() * 2 - 1) * 0.4, ay = (Math.random() * 2 - 1) * 0.4; vs.push(ax, ay); vx += ax; vy += ay; }
      for (k = 0; k < 3; k++) { vs[2 * k] -= vx / 3; vs[2 * k + 1] -= vy / 3; }
      s = s.concat(vs);
      for (k = 0; k < 3; k++) for (var j = k + 1; j < 3; j++) {
        var dx = s[2 * j] - s[2 * k], dy = s[2 * j + 1] - s[2 * k + 1];
        if (Math.hypot(dx, dy) < 0.4) return null;
      }
      var m = [1, 1, 1], t = 0, out2 = null;
      while (t < 60) {
        step(s, m, 0.001, 0.05); t += 0.001;
        var far = 0;
        for (k = 0; k < 3; k++) far = Math.max(far, Math.hypot(s[2 * k], s[2 * k + 1]));
        if (far > 12) { out2 = t; break; }
      }
      return { ejected: out2 !== null, t: out2 };
    }
    var times = [], tally = { "one was thrown out": 0, "all three still together": 0 }, total = 0;
    function draw() {
      var n = total || 1;
      Object.keys(tally).forEach(function (k) {
        rows[k].fill.style.setProperty("--v", tally[k] / n);
        rows[k].n.textContent = tally[k] + " (" + Math.round(100 * tally[k] / n) + "%)";
      });
      var g = plot._g;
      g.fillStyle = C.panel; g.fillRect(0, 0, plot._w, plot._h);
      var bins = new Array(30).fill(0);
      times.forEach(function (t) { bins[Math.min(29, Math.floor(t / 2))]++; });
      var mx = Math.max.apply(null, bins) || 1;
      bins.forEach(function (cnt, i) {
        var hh = cnt / mx * 150;
        g.fillStyle = C.teal;
        g.fillRect(40 + i * 19, 175 - hh, 17, hh);
      });
      g.fillStyle = C.mute; g.font = "11px system-ui";
      [0, 20, 40, 60].forEach(function (k) { g.fillText(String(k), 36 + k / 60 * 570, 192); });
      g.fillText("how long before one of them left, in time units", 40, 16);
    }
    go.onclick = function () {
      go.disabled = true; go.textContent = "running…";
      var want = +runs.value, done = 0;
      times = []; tally = { "one was thrown out": 0, "all three still together": 0 }; total = 0;
      function batch() {
        for (var i = 0; i < 12 && done < want; i++) {
          var r = one();
          if (!r) continue;
          done++; total++;
          if (r.ejected) { tally["one was thrown out"]++; times.push(r.t); }
          else tally["all three still together"]++;
        }
        draw();
        out.textContent = done + " of " + want + " run" + (done >= want && times.length ?
          " · half of the ejections happened before t = " + fmt(times.slice().sort(function (a, b) { return a - b; })[Math.floor(times.length / 2)], 1) : "");
        if (done < want) setTimeout(batch, 0); else { go.disabled = false; go.textContent = "Run them again"; }
      }
      batch();
    };
    root.appendChild(row([go, label("how many", [runs]), out]));
    root.appendChild(bars);
    root.appendChild(note("Run it twice. Which triples break up changes; the percentage barely moves. That is why this problem has a statistical answer even though it has no formula."));
    draw();
  }

  var DEMOS = { inverse: inverse, kepler: kepler, sim: sim, integrals: integrals, chaos: chaos,
                zvc: zvc, shapes: shapes, eight: eight, integrator: integrator, odds: odds };
  document.querySelectorAll("[data-demo]").forEach(function (root) {
    var f = DEMOS[root.getAttribute("data-demo")];
    if (f) { root.innerHTML = ""; try { f(root); } catch (e) { root.innerHTML = '<p class="note">This demo did not start: ' + e.message + "</p>"; } }
  });

  var tl = document.querySelector(".tl");
  if (tl && !RM && "IntersectionObserver" in window) {
    tl.classList.remove("nojs");
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -8% 0px" });
    tl.querySelectorAll("li").forEach(function (li) { io.observe(li); });
  }
})();
