/* anim.js — the demos. Vanilla, no library, inlined into the pages that use them.

   Each demo mounts into an element with data-demo="<name>". The physics is the same
   leapfrog step as tools/physics.py, written out for three bodies. Continuous motion
   runs only where the reader has not asked for reduced motion; every demo also works
   from its buttons, so a still page is a working page.

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
  function rafLoop(fn) {
    var on = false, id = 0;
    function tick() { if (!on) return; fn(); id = requestAnimationFrame(tick); }
    return { start: function () { if (!on) { on = true; tick(); } }, stop: function () { on = false; cancelAnimationFrame(id); },
             get running() { return on; } };
  }
  function onScreen(node, loop) {
    if (!("IntersectionObserver" in window)) return;
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (!e.isIntersecting && loop.running) loop.stop(); });
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
    var c = canvas(root, 640, 400);
    var presets = [["eight", "figure eight"], ["triangle", "Lagrange triangle"], ["line", "Euler line"],
                   ["random", "a random throw"], ["binary", "a pair and an intruder"]];
    ORB.slice(0, 6).forEach(function (o) { if (o.id !== "figure-eight") presets.push(["orb:" + o.id, o.name]); });
    var sel = pick(presets, "eight");
    var play = btn("Pause"), reset = btn("Reset", "alt"), trailsBtn = btn("Clear trails", "alt");
    var sp = range(1, 40, 14), out = readout(""), eout = readout("");
    var m = [1, 1, 1], s = null, E0 = 0, t = 0, trails = [[], [], []], span = 3.2;
    function setup(kind) {
      t = 0; trails = [[], [], []]; m = [1, 1, 1]; span = 3.2;
      if (kind === "eight" || kind.indexOf("orb:") === 0) {
        var o = kind === "eight" ? (ORB.filter(function (q) { return q.id === "figure-eight"; })[0] || { v: [0.3471169, 0.5327249] })
                                 : ORB.filter(function (q) { return "orb:" + q.id === kind; })[0];
        s = sdState(o.v[0], o.v[1]); span = 3.4;
      } else if (kind === "triangle") {
        var w = Math.sqrt(3);                                   // ω² = 3Gm/a³ with a = side = √3 r
        var r = 1 / Math.sqrt(3), om = Math.sqrt(3 * 1 / Math.pow(w * r, 3));
        s = [];
        for (var i = 0; i < 3; i++) { var th = i * 2.0944; s.push(r * Math.cos(th), r * Math.sin(th)); }
        for (i = 0; i < 3; i++) { var th2 = i * 2.0944; s.push(-om * r * Math.sin(th2), om * r * Math.cos(th2)); }
        span = 2.4;
      } else if (kind === "line") {
        var omg = Math.sqrt(1.25);                              // equal masses at -1, 0, 1
        s = [-1, 0, 0, 0, 1, 0, 0, -omg, 0, 0, 0, omg];
        span = 3.0;
      } else if (kind === "binary") {
        s = [-0.5, 0, 0.5, 0, 3.0, 1.6, 0, -0.707, 0, 0.707, -0.62, -0.30];
        span = 7.0;
      } else {
        s = [];
        for (var k = 0; k < 3; k++) s.push((Math.random() * 2 - 1) * 1.1, (Math.random() * 2 - 1) * 1.1);
        var vx = 0, vy = 0, vs = [];
        for (k = 0; k < 3; k++) { var ax = (Math.random() * 2 - 1) * 0.45, ay = (Math.random() * 2 - 1) * 0.45; vs.push(ax, ay); vx += ax; vy += ay; }
        for (k = 0; k < 3; k++) { vs[2 * k] -= vx / 3; vs[2 * k + 1] -= vy / 3; }
        s = s.concat(vs); span = 4.0;
      }
      E0 = energy(s, m);
    }
    function draw() {
      clear(c);
      var V = view(c, span);
      var g = c._g;
      for (var i = 0; i < 3; i++) {
        g.beginPath();
        trails[i].forEach(function (p, j) { var X = V.x(p[0]), Y = V.y(p[1]); if (j === 0) g.moveTo(X, Y); else g.lineTo(X, Y); });
        g.strokeStyle = BODY[i]; g.globalAlpha = 0.85; g.lineWidth = 1.6; g.stroke(); g.globalAlpha = 1;
        dot(c, V, s[2 * i], s[2 * i + 1], 5.5 + 2 * (m[i] - 1), BODY[i]);
      }
      var E = energy(s, m);
      out.textContent = "t = " + fmt(t, 1);
      eout.textContent = "energy " + fmt(E, 5) + "  ·  drift " + ((Math.abs((E - E0) / E0)) < 1e-9 ? "under 1e-9" : (Math.abs((E - E0) / E0)).toExponential(1));
    }
    var loop = rafLoop(function () {
      var h = 0.0006 * sp.value;
      for (var k = 0; k < 12; k++) { step(s, m, h / 12, 0); t += h / 12; }
      for (var i = 0; i < 3; i++) { trails[i].push([s[2 * i], s[2 * i + 1]]); if (trails[i].length > 1400) trails[i].shift(); }
      draw();
    });
    play.onclick = function () { if (loop.running) { loop.stop(); play.textContent = "Run"; } else { loop.start(); play.textContent = "Pause"; } };
    reset.onclick = function () { setup(sel.value); draw(); };
    trailsBtn.onclick = function () { trails = [[], [], []]; draw(); };
    sel.onchange = function () { setup(sel.value); draw(); };
    root.appendChild(row([play, reset, trailsBtn, sel]));
    root.appendChild(row([label("speed", [sp]), out, eout]));
    root.appendChild(note("The same four lines of arithmetic as tools/physics.py, running in your browser. The drift readout is the check on it: energy cannot change, so anything it does here is the stepper's doing, not the physics."));
    setup("eight"); draw();
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
    var c = canvas(root, 640, 300);
    var plot = canvas(root, 640, 220);
    var nud = range(3, 14, 6), go = btn("Run"), rs = btn("Reset", "alt"), out = readout("");
    var m = [1, 1, 1], a = null, b = null, t = 0, hist = [], trails = [[], []];
    function setup() {
      var e = Math.pow(10, -nud.value);
      a = sdState(0.28, 0.45); b = sdState(0.28, 0.45); b[0] += e;
      t = 0; hist = []; trails = [[], []];
      out.textContent = "nudge " + e.toExponential(0) + " — the two starts differ by that much, in one number";
    }
    function gap() {
      var d = 0; for (var i = 0; i < 12; i++) { var q = a[i] - b[i]; d += q * q; } return Math.sqrt(d);
    }
    function draw() {
      clear(c);
      var V = view(c, 4.6), g = c._g, i;
      [a, b].forEach(function (s, k) {
        for (i = 0; i < 3; i++) dot(c, V, s[2 * i], s[2 * i + 1], k ? 4 : 6, k ? C.red : BODY[i]);
      });
      [0, 1].forEach(function (k) {
        g.beginPath();
        trails[k].forEach(function (p, j) { var X = V.x(p[0]), Y = V.y(p[1]); if (j === 0) g.moveTo(X, Y); else g.lineTo(X, Y); });
        g.strokeStyle = k ? C.red : C.teal; g.globalAlpha = .55; g.lineWidth = 1.2; g.stroke(); g.globalAlpha = 1;
      });
      // the log plot
      var pg = plot._g;
      pg.fillStyle = C.panel; pg.fillRect(0, 0, plot._w, plot._h);
      pg.strokeStyle = C.line; pg.lineWidth = 1;
      for (var p = -14; p <= 1; p += 3) {
        var Y = 200 - (p + 15) / 16 * 180;
        pg.beginPath(); pg.moveTo(40, Y); pg.lineTo(630, Y); pg.stroke();
        pg.fillStyle = C.mute; pg.font = "11px system-ui"; pg.fillText("1e" + p, 4, Y + 4);
      }
      pg.beginPath();
      hist.forEach(function (h, j) {
        var X = 40 + h[0] / 60 * 590, Y = 200 - (Math.log(Math.max(h[1], 1e-15)) / Math.LN10 + 15) / 16 * 180;
        if (j === 0) pg.moveTo(X, Y); else pg.lineTo(X, Y);
      });
      pg.strokeStyle = C.teal; pg.lineWidth = 2.4; pg.stroke();
      // fit the straight stretch → Lyapunov time
      var fit = hist.filter(function (h) { return h[1] > Math.pow(10, -nud.value) * 30 && h[1] < 0.3; });
      if (fit.length > 12) {
        var n = fit.length, sx = 0, sy = 0, sxx = 0, sxy = 0;
        fit.forEach(function (h) { var x = h[0], y = Math.log(h[1]); sx += x; sy += y; sxx += x * x; sxy += x * y; });
        var sl = (n * sxy - sx * sy) / (n * sxx - sx * sx);
        if (sl > 0) out.textContent = "nudge " + Math.pow(10, -nud.value).toExponential(0) +
          " · the gap multiplies by e every " + fmt(1 / sl, 2) + " time units · at this rate a millionth becomes a whole in " +
          fmt(Math.log(1e6) / sl, 1);
      }
    }
    var loop = rafLoop(function () {
      for (var k = 0; k < 44; k++) { step(a, m, 0.002, 0); step(b, m, 0.002, 0); t += 0.002; }
      hist.push([t, gap()]);
      trails[0].push([a[0], a[1]]); trails[1].push([b[0], b[1]]);
      if (trails[0].length > 900) { trails[0].shift(); trails[1].shift(); }
      draw();
      if (t > 60) { loop.stop(); go.textContent = "Run again"; }
    });
    go.onclick = function () { if (loop.running) { loop.stop(); go.textContent = "Run"; } else { if (t > 60) setup(); loop.start(); go.textContent = "Pause"; } };
    rs.onclick = function () { setup(); draw(); };
    nud.oninput = function () { setup(); draw(); };
    root.appendChild(row([go, rs, label("nudge size", [nud])]));
    root.appendChild(el("div", { class: "row" }, [out]));
    root.appendChild(note("Two copies of one start, differing in a single number. The lower panel is the gap between them on a log scale: flat, then a straight climb — that straight stretch is the exponent — then flat again at the top, where the gap has run out of room to grow."));
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
      var img = g.createImageData(w, h);
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
      g.putImageData(img, 0, 0);
      var V = view(c, span);
      dot(c, V, -m2, 0, 9, C.gold); dot(c, V, 1 - m2, 0, 6, C.teal);
      lagr(m2).forEach(function (p, i) {
        dot(c, V, p[0], p[1], 5, i < 3 ? C.violet : C.red);
        g.fillStyle = i < 3 ? C.violet : C.red; g.font = "bold 12px system-ui";
        g.fillText("L" + (i + 1), V.x(p[0]) + 8, V.y(p[1]) - 6);
      });
      out.textContent = "mass ratio μ = " + fmt(m2, 2) + " · Jacobi constant C = " + fmt(Cj, 2) +
        " · the dark region is where this body cannot go";
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
    var c = canvas(root, 640, 380);
    var opts = ORB.map(function (o) { return [o.id, o.name + " · T = " + o.period.toFixed(3)]; });
    var sel = pick(opts.length ? opts : [["figure-eight", "figure eight"]], "figure-eight");
    var go = btn("Pause"), tr = btn("Clear trails", "alt"), sp = range(1, 40, 16), out = readout("");
    var s = null, m = [1, 1, 1], t = 0, trails = [[], [], []], cur = null, span = 3.4;
    function setup() {
      cur = ORB.filter(function (o) { return o.id === sel.value; })[0] || { v: [0.3471169, 0.5327249], period: 6.325914, closes: 0, name: "figure eight" };
      s = sdState(cur.v[0], cur.v[1]); t = 0; trails = [[], [], []];
      var mx = 0;
      var probe = clone(s);
      for (var k = 0; k < 4000; k++) { step(probe, m, cur.period / 4000, 0); for (var i = 0; i < 3; i++) mx = Math.max(mx, Math.abs(probe[2 * i]), Math.abs(probe[2 * i + 1])); }
      span = Math.max(2.4, mx * 2.3);
      out.textContent = cur.name + " · period " + cur.period.toFixed(6) + " · returns to its start within " +
        (cur.closes ? cur.closes.toExponential(1) : "—");
    }
    function draw() {
      clear(c);
      var V = view(c, span), g = c._g;
      for (var i = 0; i < 3; i++) {
        g.beginPath();
        trails[i].forEach(function (p, j) { var X = V.x(p[0]), Y = V.y(p[1]); if (j === 0) g.moveTo(X, Y); else g.lineTo(X, Y); });
        g.strokeStyle = BODY[i]; g.lineWidth = 1.7; g.globalAlpha = .9; g.stroke(); g.globalAlpha = 1;
        dot(c, V, s[2 * i], s[2 * i + 1], 6, BODY[i]);
      }
      g.fillStyle = C.mute; g.font = "12px system-ui";
      g.fillText("t = " + fmt(t, 2) + " of " + cur.period.toFixed(3), 12, 20);
    }
    var loop = rafLoop(function () {
      var h = 0.0005 * sp.value;
      for (var k = 0; k < 10; k++) { step(s, m, h / 10, 0); t += h / 10; }
      for (var i = 0; i < 3; i++) { trails[i].push([s[2 * i], s[2 * i + 1]]); if (trails[i].length > 2600) trails[i].shift(); }
      draw();
    });
    go.onclick = function () { if (loop.running) { loop.stop(); go.textContent = "Run"; } else { loop.start(); go.textContent = "Pause"; } };
    tr.onclick = function () { trails = [[], [], []]; draw(); };
    sel.onchange = function () { setup(); draw(); };
    root.appendChild(row([go, tr, sel, label("speed", [sp])]));
    root.appendChild(el("div", { class: "row" }, [out]));
    root.appendChild(note("Every start in this list was found on the machine that built the page: a grid of starting speeds, then a solver that walks each near-miss in until the orbit closes. The number it closes to is printed beside it."));
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
