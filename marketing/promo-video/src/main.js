(function () {
  const CH = window.CHOREO, RC = window.RECTS;
  const BEAT = 60 / CH.bpm;
  const S0 = 1000 / 2240;           // escala de la captura (2240 px) al visor (1000 px)
  const FIT = 1.6;                  // factor lógico → píxel de imagen de las capturas
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const rnd = mulberry32(2026);
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const tl = gsap.timeline({ paused: true });
  const T = CH.scenes;
  // fromTo: GSAP renderiza el estado "from" de inmediato; solo conviene cuando parte de opacity 0 (oculta el elemento hasta su entrada).
  const _fromTo = tl.fromTo.bind(tl);
  tl.fromTo = function (t, a, b, pos) {
    if (!(a && a.opacity === 0) && b.immediateRender === undefined) b = Object.assign({ immediateRender: false }, b);
    return _fromTo(t, a, b, pos);
  };

  // ── utilidades de efecto ────────────────────────────────────────────────
  function flash(t, a, d, red) { const el = red ? "#flashred" : "#flash"; tl.fromTo(el, { opacity: a }, { opacity: 0, duration: d || 0.25, ease: "power2.out" }, t); }
  function shake(t, amp, dur) {
    const n = 7, step = dur / n;
    for (let i = 0; i < n; i++) {
      const k = 1 - i / n;
      tl.to("#world", { x: (rnd() * 2 - 1) * amp * k, y: (rnd() * 2 - 1) * amp * k, duration: step, ease: "none" }, t + i * step);
    }
    tl.to("#world", { x: 0, y: 0, duration: step, ease: "none" }, t + dur);
  }
  function glitch(el, t, len) {
    const g = el.querySelectorAll(".g"); const l = len || 0.14;
    g.forEach((n, i) => {
      tl.set(n, { opacity: 0.85, x: (i ? 1 : -1) * (12 + rnd() * 10) }, t);
      tl.set(n, { opacity: 0.85, x: (i ? -1 : 1) * (8 + rnd() * 8) }, t + l * 0.5);
      tl.set(n, { opacity: 0, x: 0 }, t + l);
    });
  }
  const tearEl = $("#tear");
  for (let i = 0; i < 6; i++) { const b = document.createElement("i"); b.style.top = (80 + i * 300 + rnd() * 120) + "px"; b.style.height = (14 + rnd() * 40) + "px"; tearEl.appendChild(b); }
  function tear(t) {
    tl.set("#tear", { opacity: 1 }, t);
    $$("#tear i").forEach((b, i) => { tl.set(b, { x: (rnd() * 2 - 1) * 120 }, t); tl.set(b, { x: (rnd() * 2 - 1) * 120 }, t + 0.05); });
    tl.set("#tear", { opacity: 0 }, t + 0.1);
  }
  // grano de película animado (pasos fijos)
  for (let i = 0; i < 12 * 32; i++) tl.set("#grain", { x: -((i * 37) % 128), y: -((i * 53) % 128) }, i / 12);

  // pulso en cada tiempo durante el groove
  for (let tb = T.reveal; tb < T.cta; tb += BEAT) tl.fromTo("#pulse", { opacity: 0.3 }, { opacity: 0, duration: 0.32, ease: "power2.out" }, tb);

  // ═══ 1 · GANCHO ════════════════════════════════════════════════════════
  const bars = document.getElementById("hook-bars");
  const H = [];
  for (let i = 0; i < 40; i++) { const b = document.createElement("i"); bars.appendChild(b); H.push(0.25 + rnd() * 0.75); }
  const barEls = Array.from(bars.children);
  tl.set(barEls, { scaleY: 0.04 }, 0);
  tl.to(barEls, { scaleY: (i) => H[i], duration: 0.55, ease: "power3.out", stagger: { each: 0.008, from: "center" } }, 0.05);
  for (let k = 1; k < 8; k++) {
    tl.to(barEls, { scaleY: (i) => H[i] * (0.45 + 0.55 * ((i * 7 + k * 13) % 10) / 10), duration: 0.14, ease: "power2.out" }, k * BEAT);
  }
  const embers = document.getElementById("embers");
  for (let i = 0; i < 34; i++) {
    const e = document.createElement("i"); e.className = "ember"; e.style.left = (30 + rnd() * 1020) + "px"; e.style.top = (1250 + rnd() * 600) + "px"; embers.appendChild(e);
    tl.fromTo(e, { y: 0, opacity: 0 }, { y: -(700 + rnd() * 700), opacity: 0.9, duration: 1.6 + rnd() * 1.6, ease: "power1.out" }, rnd() * 1.4);
  }
  const W = $$("#hook-words .word");
  tl.set(W, { opacity: 0 }, 0);
  CH.slams.forEach((t, i) => {
    const big = i === 3;
    tl.fromTo(W[i], { opacity: 0, scale: big ? 3.4 : 2.5, y: big ? -120 : -70, rotation: big ? 7 : -5 }, { opacity: 1, scale: 1, y: 0, rotation: 0, duration: 0.24, ease: "expo.out" }, t);
    flash(t, big ? 0.7 : 0.35, big ? 0.35 : 0.2, !big);
    shake(t, big ? 26 : 14, big ? 0.4 : 0.26);
    glitch(W[i], t + 0.26, 0.16);
  });
  for (let g = 0; g < 4; g++) glitch(W[3], 2.95 + g * 0.17, 0.09);   // "A MANO?" parpadea
  tl.to("#hook-words", { x: -40, opacity: 0, duration: 0.18, ease: "power2.in" }, 3.5);
  tear(3.5); tear(3.62); flash(3.72, 0.8, 0.25);

  // ═══ 2 · DOLOR ═════════════════════════════════════════════════════════
  const lanes = document.getElementById("lanes"); const cols = ["#ff1f3a", "#7c3aed", "#2563eb", "#16a34a", "#d97706", "#db2777"];
  for (let l = 0; l < 6; l++) {
    const lane = document.createElement("div"); lane.className = "lane"; let x = 14 + rnd() * 40;
    while (x < 900) { const w = 70 + rnd() * 190; const c = document.createElement("div"); c.className = "clipbox"; c.style.left = x + "px"; c.style.width = w + "px"; c.style.background = cols[(l + Math.floor(rnd() * 3)) % 6]; lane.appendChild(c); x += w + 8 + rnd() * 30; }
    lanes.appendChild(lane);
  }
  tl.from("#lanes .clipbox", { scaleX: 0, transformOrigin: "0% 50%", duration: 0.22, stagger: 0.012, ease: "power3.out" }, 3.85);
  [3.85, 4.85, 5.85, 6.85].forEach((t) => tl.fromTo("#playhead", { x: 0 }, { x: 900, duration: 1.0, ease: "none" }, t));
  const secs = 10033;
  for (let i = 0; i <= 80; i++) {
    const f = i / 80, p = f * f, v = Math.round(secs * p);
    const hh = String(Math.floor(v / 3600)).padStart(2, "0"), mm = String(Math.floor(v % 3600 / 60)).padStart(2, "0"), ss = String(v % 60).padStart(2, "0");
    tl.set("#timer", { textContent: hh + ":" + mm + ":" + ss }, 3.85 + f * 3.3);
  }
  const ST = $$(".stamp");
  tl.set(ST, { opacity: 0 }, 3.75);
  [3.95, 4.69, 5.63, 6.56].forEach((t, i) => {
    tl.fromTo(ST[i], { opacity: 0, x: i % 2 ? 1300 : -1300, rotation: i % 2 ? 8 : -8, scale: 1.3 }, { opacity: 1, x: 0, rotation: i % 2 ? 2 : -2, scale: 1, duration: 0.2, ease: "expo.out" }, t);
    flash(t, 0.22, 0.18, true); shake(t, 10, 0.2);
  });
  tl.to("#pain-all", { scale: 0.04, rotation: 14, opacity: 0, duration: 0.36, ease: "power4.in" }, 7.0);
  flash(7.34, 0.95, 0.22);

  // ═══ 3 · REVELACIÓN ════════════════════════════════════════════════════
  flash(T.reveal, 1, 0.4); shake(T.reveal, 28, 0.45);
  tl.fromTo("#emblem", { opacity: 0, scale: 4, rotation: -10 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.5, ease: "expo.out" }, T.reveal);
  $$(".ring").forEach((r, i) => tl.fromTo(r, { scale: 0.3, opacity: 0.95 }, { scale: 3.4, opacity: 0, duration: 0.95, ease: "power2.out" }, T.reveal + i * 0.13));
  tl.fromTo("#title-auto span", { opacity: 0, y: 140, scale: 1.7 }, { opacity: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(2)", stagger: 0.045 }, 8.0);
  glitch($("#title-auto"), 8.55, 0.1);
  tl.fromTo("#banner-rr", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.35, ease: "power3.out" }, 8.35);
  tl.fromTo("#tagline span", { opacity: 0, scale: 1.9 }, { opacity: 1, scale: 1, duration: 0.2, ease: "expo.out" }, 8.55);
  flash(8.55, 0.3, 0.2, true);
  tl.to(["#emblem", "#title-auto", "#banner-rr", "#tagline"], { y: -1300, duration: 0.28, ease: "power3.in", stagger: 0.025 }, 9.08);

  // ═══ 4 · APP ═══════════════════════════════════════════════════════════
  const A0 = T.demo;
  const imgs = ["i01", "i02", "i03", "i08", "i04", "i05", "i07"];
  tl.set(imgs.map((i) => "#" + i), { opacity: 0 }, A0);
  tl.set("#i01", { opacity: 1 }, A0);
  const CK = [];           // claves de cámara (para escalar cursor y ondas)
  function cam(t, d, tx, ty, z, ease) {
    const S = S0 * z; CK.push({ t, d, z });
    const props = { x: 500 - tx * S, y: 530 - ty * S, scale: S };
    if (d <= 0) tl.set("#cam", props, t); else tl.to("#cam", Object.assign({ duration: d, ease: ease || "power3.inOut" }, props), t);
    const cs = 2.0 / S;
    if (d <= 0) tl.set("#cursor-in", { scale: cs }, t); else tl.to("#cursor-in", { scale: cs, duration: d, ease: ease || "power3.inOut" }, t);
  }
  function zoomAt(t) { let z = 1; for (const k of CK) { if (t >= k.t + k.d) z = k.z; else if (t >= k.t) { z = k.z; } } return z; }
  function show(id, t, hide) {
    if (hide) tl.to("#" + hide, { opacity: 0, duration: 0.1 }, t);
    tl.to("#" + id, { opacity: 1, duration: 0.1 }, t);
  }
  function gcut(t) {
    flash(t, 0.55, 0.2); tear(t);
    tl.fromTo("#vp", { x: -22 }, { x: 0, duration: 0.3, ease: "elastic.out(1,0.4)" }, t);
    tl.fromTo("#cam", { filter: "blur(12px)" }, { filter: "blur(0px)", duration: 0.28, ease: "power2.out" }, t);
  }
  tl.fromTo("#vp", { y: 520, opacity: 0, scale: 0.9 }, { y: 0, opacity: 1, scale: 1, duration: 0.55, ease: "expo.out" }, A0);
  tl.fromTo("#stepper", { opacity: 0 }, { opacity: 1, duration: 0.3 }, A0 + 0.2);
  tl.fromTo("#stepper-lbl", { opacity: 0 }, { opacity: 1, duration: 0.3 }, A0 + 0.2);

  // pies / captions
  const capData = [
    { a: 9.45, b: 11.3, n: "01", t: "Arrastra <em>tu track</em>", s: "WAV · MP3 · FLAC · AIFF · M4A", p: 0 },
    { a: 11.35, b: 13.15, n: "02", t: "Análisis <em>automático</em>", s: "BPM · tonalidad · drops · estructura", p: 1 },
    { a: 13.2, b: 16.25, n: "03", t: "Elige <em>la duración</em>", s: "15 s · 30 s · 60 s · 2 min", p: 2 },
    { a: 16.3, b: 18.7, n: "04", t: "Un clic: <em>generar</em>", s: "Cortes, transiciones y metadatos solos", p: 3 },
    { a: 18.8, b: 22.45, n: "05", t: "<em>Lista</em> para enviar", s: "MP3 320k · WAV 24 bit · Vídeo 9:16", p: 4 },
    { a: 22.5, b: 23.4, n: "+", t: "Editor <em>de cortes</em>", s: "Ajusta cada fragmento al segundo", p: 4 },
    { a: 23.4, b: 24.33, n: "+", t: "Anti-retoque <em>de BPM</em>", s: "Variación de tempo: nadie mezcla tu previa", p: 4 },
    { a: 24.33, b: 25.27, n: "+", t: "Modo promo <em>antifugas</em>", s: "Tu firma de voz repetida · MP3 128k", p: 4 },
    { a: 25.27, b: 26.2, n: "+", t: "Lote <em>y carpeta vigilada</em>", s: "Decenas de tracks, un clic", p: 4 },
  ];
  const capsEl = document.getElementById("caps"); const pills = $$("#stepper i");
  capData.forEach((c, i) => {
    const d = document.createElement("div"); d.className = "cap"; d.id = "cap" + i;
    d.innerHTML = '<div class="num">' + c.n + '</div><div class="ttl">' + c.t + '</div><div class="sub">' + c.s + "</div>";
    capsEl.appendChild(d);
    tl.set(d, { opacity: 0 }, A0);
    tl.fromTo(d, { x: -110, opacity: 0 }, { x: 0, opacity: 1, duration: 0.3, ease: "expo.out" }, c.a);
    tl.to(d, { x: 70, opacity: 0, duration: 0.16, ease: "power2.in" }, c.b - 0.16);
    if (i <= 4) tl.to(pills[c.p], { backgroundColor: "#ff1f3a", duration: 0.2 }, c.a);
  });
  tl.to("#logo-mini", { opacity: 0.9, duration: 0.3 }, 22.6);

  // cursor, ondas y resaltes
  function ctr(stage, key) { const r = RC[stage][key]; return [(r[0] + r[2] / 2) * FIT, (r[1] + r[3] / 2) * FIT]; }
  function box(stage, key, pad) { const r = RC[stage][key]; const p = pad || 8; return [r[0] * FIT - p, r[1] * FIT - p, r[2] * FIT + 2 * p, r[3] * FIT + 2 * p]; }
  const rippleHost = document.getElementById("ripples"), hlHost = document.getElementById("hls");
  let nr = 0;
  function click(t, x, y) {
    const r = document.createElement("div"); r.className = "ripple"; r.style.left = x + "px"; r.style.top = y + "px"; rippleHost.appendChild(r);
    const S = S0 * zoomAt(t);
    tl.fromTo(r, { scale: 0.3 / S * 0.6, opacity: 1 }, { scale: 2.6 / S, opacity: 0, duration: 0.5, ease: "power2.out" }, t);
    tl.fromTo("#cursor-in", { scale: 2.0 / S }, { scale: 1.6 / S, duration: 0.07, yoyo: true, repeat: 1, ease: "power1.inOut" }, t - 0.04);
    nr++;
  }
  function hl(b, t, hold) {
    const h = document.createElement("div"); h.className = "hl"; h.style.left = b[0] + "px"; h.style.top = b[1] + "px"; h.style.width = b[2] + "px"; h.style.height = b[3] + "px"; hlHost.appendChild(h);
    tl.fromTo(h, { opacity: 0, scale: 1.18 }, { opacity: 1, scale: 1, duration: 0.14, ease: "power3.out" }, t);
    tl.to(h, { opacity: 0, duration: 0.22 }, t + (hold || 0.3));
  }
  function curMove(t, d, x, y) {
    tl.to("#cursor", { x: x, duration: d, ease: "power2.inOut" }, t);
    tl.to("#cursor", { y: y, duration: d, ease: "power1.inOut" }, t);
  }
  function curSet(t, x, y) { tl.set("#cursor", { x: x, y: y, opacity: 1 }, t); }

  // — paso 1: arrastrar archivo —
  cam(A0, 0, 1120, 656, 1.25);
  cam(9.8, 1.35, 1120, 660, 1.75);
  tl.set("#chip", { opacity: 0, scale: 2.0, transformOrigin: "0% 0%" }, A0);
  const dz = ctr("welcome", "drop");
  curSet(9.55, 1760, 200);
  tl.fromTo("#chip", { x: 1730, y: 190, opacity: 0 }, { x: 1730, y: 190, opacity: 1, duration: 0.2 }, 9.55);
  curMove(9.75, 1.4, dz[0], dz[1] + 40);
  tl.to("#chip", { x: dz[0] - 60, duration: 1.4, ease: "power2.inOut" }, 9.75);
  tl.to("#chip", { y: dz[1] - 10, duration: 1.4, ease: "power1.inOut" }, 9.75);
  click(CH.clicks[0], dz[0], dz[1] + 40);
  hl(box("welcome", "drop", 6), CH.clicks[0] - 0.05, 0.4);
  tl.to("#chip", { scale: 0.2, opacity: 0, duration: 0.18, ease: "power2.in" }, CH.clicks[0] - 0.02);
  flash(CH.clicks[0], 0.25, 0.2, true);

  // — paso 2: análisis —
  show("i02", 11.3, "i01");
  cam(11.3, 0.4, 1120, 690, 1.6);
  curMove(11.4, 1.6, 1550, 1000);
  const pr = RC.welcome.open_btn;   // la barra de progreso de la pantalla de análisis (coords de captura)
  tl.set("#prog", { opacity: 1 }, 11.35);
  tl.fromTo("#prog i", { width: 0 }, { width: 607, duration: 1.7, ease: "power1.inOut" }, 11.4);
  tl.set("#prog", { opacity: 0 }, 13.15);
  flash(13.125, 0.35, 0.25);

  // — paso 3: pista cargada y presets —
  const LD = "loaded";
  gcut(13.2);
  show("i03", 13.2, "i02");
  cam(13.2, 0, 1120, 800, 1.3);
  cam(13.45, 0.9, 1120, 800, 1.5);
  curSet(13.25, 1500, 760);
  curMove(13.4, 0.5, 900, 430);
  curMove(13.95, 0.35, 1750, 430);
  hl(box(LD, "waveform", 4), 13.5, 0.7);
  hl(box(LD, "bpm", 6), 13.7, 0.5);
  cam(14.05, 0.45, 620, 960, 2.0);
  const pk = ["p15", "p30", "p60", "p120"];
  pk.forEach((k, i) => {
    const t = CH.clicks[2 + i], c = ctr(LD, k);
    curMove(i === 0 ? 14.35 : CH.clicks[1 + i] + 0.04, i === 0 ? 0.2 : 0.38, c[0], c[1]);
    click(t, c[0], c[1]); hl(box(LD, k, 6), t - 0.03, 0.4);
  });
  // — paso 4: generar —
  const gen = ctr(LD, "generate"), gb = box(LD, "generate", 6);
  cam(16.25, 0.85, 1120, 1100, 1.45);
  curMove(16.1, 1.15, gen[0], gen[1]);
  click(CH.clicks[6], gen[0], gen[1]);
  hl(gb, CH.clicks[6] - 0.03, 1.3);
  tl.set("#shim", { left: gb[0], top: gb[1] + 6, height: gb[3] - 12 }, 17.3);
  tl.fromTo("#shim", { x: 0, opacity: 1 }, { x: gb[2] - 250, opacity: 1, duration: 0.55, ease: "power1.inOut" }, 17.4);
  tl.fromTo("#shim", { x: 0, opacity: 1 }, { x: gb[2] - 250, opacity: 1, duration: 0.55, ease: "power1.inOut" }, 17.98);
  tl.set("#shim", { opacity: 0 }, 18.6);

  // — paso 5: previa generada —
  const GN = "generated", T5 = CH.clicks[7];
  gcut(T5); flash(T5, 0.5, 0.35, true);
  show("i08", T5, "i03");
  cam(T5, 0, 1120, 1040, 1.0);
  cam(T5 + 0.35, 0.85, 1120, 1290, 1.5);
  curSet(T5, 1120, 1750);
  hl(box(GN, "success", 6), T5 + 0.25, 1.1);
  const op = ctr(GN, "open"), pl = [1217, 758];
  curMove(T5 + 0.5, 0.7, op[0], op[1]);
  cam(20.25, 0.75, 1160, 800, 1.45);
  curMove(20.1, 0.5, pl[0], pl[1]);
  click(CH.clicks[8], pl[0], pl[1]); hl(box(GN, "player", 4), CH.clicks[8] - 0.02, 1.4);
  // confeti
  const conf = document.getElementById("conf");
  for (let i = 0; i < 46; i++) {
    const c = document.createElement("i"); c.className = "cf"; c.style.left = "500px"; c.style.top = "820px"; c.style.background = ["#ff1f3a", "#ffffff", "#ffd21f", "#a855f7"][i % 4]; conf.appendChild(c);
    const ang = -Math.PI / 2 + (rnd() * 2 - 1) * 1.1, sp = 320 + rnd() * 560;
    tl.set(c, { opacity: 0 }, T5);
    tl.fromTo(c, { x: 0, y: 0, opacity: 1, rotation: 0 }, { x: Math.cos(ang) * sp, y: Math.sin(ang) * sp, rotation: 360 * (rnd() * 2 - 1) * 2, duration: 0.55, ease: "power2.out" }, T5 + 0.02);
    tl.to(c, { y: "+=700", opacity: 0, duration: 0.9, ease: "power2.in" }, T5 + 0.57);
  }

  // — funciones Plus (cortes rápidos) —
  const F = [22.5, 23.4, 24.33, 25.27];
  // editor de cortes
  gcut(F[0]); show("i04", F[0], "i08"); cam(F[0], 0, 1400, 1200, 1.3);
  const addc = ctr("cuts", "add_cut");
  curSet(F[0], 1400, 1250); curMove(F[0] + 0.1, 0.35, addc[0], addc[1]);
  click(CH.clicks[9], addc[0], addc[1]); hl(box("cuts", "add_cut", 6), CH.clicks[9] - 0.03, 0.4);
  hl(box("cuts", "tbl", 6), F[0] + 0.55, 0.3);
  // BPM
  gcut(F[1]); show("i05", F[1], "i04"); cam(F[1], 0, 1000, 1150, 1.45);
  const man = ctr("bpm", "manual");
  curSet(F[1], 900, 1250); curMove(F[1] + 0.1, 0.34, man[0], man[1]);
  click(CH.clicks[10], man[0], man[1]); hl(box("bpm", "manual", 6), CH.clicks[10] - 0.03, 0.4);
  hl(box("bpm", "plot", 6), F[1] + 0.6, 0.3);
  // modo promo
  gcut(F[2]); show("i07", F[2], "i05"); cam(F[2], 0, 1120, 1290, 1.5);
  const pc = ctr("promo", "promo");
  curSet(F[2], 700, 1650); curMove(F[2] + 0.1, 0.38, pc[0], pc[1]);
  click(CH.clicks[11], pc[0], pc[1]); hl(box("promo", "promo", 8), CH.clicks[11] - 0.03, 0.45);
  hl(box("promo", "voice", 6), F[2] + 0.55, 0.3);
  // lote
  gcut(F[3]); show("i03", F[3], "i07");
  tl.set("#dim", { opacity: 0 }, F[3]); tl.to("#dim", { opacity: 1, duration: 0.12 }, F[3]); tl.to("#dlg", { opacity: 1, duration: 0.12 }, F[3]);
  cam(F[3], 0, 1300, 1000, 1.2);
  curSet(F[3], 1100, 800); curMove(F[3] + 0.1, 0.4, 1683, 1355);
  click(CH.clicks[12], 1683, 1355); hl([1571, 1328, 224, 54], CH.clicks[12] - 0.03, 0.4);

  // ═══ 5 · ESTADÍSTICA ═══════════════════════════════════════════════════
  flash(T.stat, 0.9, 0.35); shake(T.stat, 16, 0.3);
  tl.set(["#stat1 .word", "#stat2 .word", "#stat-sub", "#strike"], { opacity: 0 }, T.stat);
  tl.fromTo("#stat1 .word", { opacity: 0, scale: 1.8 }, { opacity: 1, scale: 1, duration: 0.22, ease: "expo.out" }, T.stat);
  tl.fromTo("#strike", { opacity: 1, scaleX: 0 }, { opacity: 1, scaleX: 1, duration: 0.25, ease: "power4.out" }, T.stat + 0.4);
  tl.to(["#stat1 .word", "#strike"], { y: -60, opacity: 0.35, duration: 0.3, ease: "power2.in" }, T.stat + 0.75);
  tl.fromTo("#stat2 .big", { opacity: 0, scale: 3.5, rotation: -6 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.26, ease: "expo.out" }, T.stat + 0.75);
  flash(T.stat + 0.75, 0.55, 0.3, true); shake(T.stat + 0.75, 30, 0.4);
  tl.fromTo("#stat2 .seg", { opacity: 0, scale: 2.2 }, { opacity: 1, scale: 1, duration: 0.22, ease: "expo.out" }, T.stat + 0.95);
  tl.fromTo("#stat-sub", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.3, ease: "power3.out" }, T.stat + 1.15);
  tl.to(["#stat1 .word", "#strike", "#stat2 .big", "#stat2 .seg", "#stat-sub"], { opacity: 0, y: -80, duration: 0.2, ease: "power2.in" }, T.cta - 0.2);

  // ═══ 6 · CTA ═══════════════════════════════════════════════════════════
  const C0 = T.cta;
  flash(C0, 0.9, 0.4, true); shake(C0, 22, 0.4);
  tl.fromTo("#cta-emblem", { opacity: 0, scale: 2.6, rotation: -8 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.5, ease: "expo.out" }, C0);
  tl.fromTo("#cta-title span", { opacity: 0, y: 120, scale: 1.7 }, { opacity: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(2)", stagger: 0.04 }, C0 + 0.25);
  tl.fromTo("#eds span", { opacity: 0, scale: 0 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)", stagger: 0.12 }, C0 + 0.8);
  tl.fromTo("#cta-line", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.35, ease: "power3.out" }, C0 + 1.05);
  tl.fromTo("#buy", { opacity: 0, y: 160, scale: 0.9 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "expo.out" }, C0 + 1.35);
  tl.fromTo("#cta-banner", { opacity: 0 }, { opacity: 1, duration: 0.4 }, C0 + 1.7);
  tl.fromTo("#cta-tag", { opacity: 0 }, { opacity: 1, duration: 0.4 }, C0 + 2.0);
  const buy = [540, 1228];
  tl.set("#cursor2-in", { scale: 1.7 }, C0);
  tl.set("#cursor2", { x: 880, y: 1760, opacity: 1 }, C0 + 1.7);
  tl.to("#cursor2", { x: buy[0] + 120, duration: 1.0, ease: "power2.inOut" }, C0 + 1.9);
  tl.to("#cursor2", { y: buy[1] + 30, duration: 1.0, ease: "power1.inOut" }, C0 + 1.9);
  const cc = CH.clicks[13];
  tl.fromTo("#cursor2-in", { scale: 1.7 }, { scale: 1.3, duration: 0.07, yoyo: true, repeat: 1 }, cc - 0.04);
  tl.set("#ripple2", { left: buy[0] + 120, top: buy[1] + 30 }, cc - 0.1);
  tl.fromTo("#ripple2", { scale: 0.3, opacity: 1 }, { scale: 3.2, opacity: 0, duration: 0.55, ease: "power2.out" }, cc);
  tl.fromTo("#buy", { scale: 1 }, { scale: 0.96, duration: 0.07, yoyo: true, repeat: 1 }, cc - 0.04);
  flash(cc, 0.3, 0.25, true);
  [C0 + 2.4, C0 + 3.0].forEach((t) => tl.fromTo("#buy", { boxShadow: "0 0 80px rgba(255,31,58,.6)" }, { boxShadow: "0 0 160px rgba(255,31,58,1)", duration: 0.25, yoyo: true, repeat: 1 }, t));
  tl.to("#world", { opacity: 0, duration: 0.45, ease: "power2.in" }, 31.55);

  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
})();
