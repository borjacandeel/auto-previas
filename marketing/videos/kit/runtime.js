(function () {
  const SP = window.SPEC;
  const BEAT = 60 / SP.bpm;
  const S0 = 1000 / 2240;           // escala de la captura (2240 px) al visor (1000 px)
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const rnd = mulberry32(SP.seed || 2026);
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const tl = gsap.timeline({ paused: true });
  const _fromTo = tl.fromTo.bind(tl);
  tl.fromTo = function (t, a, b, pos) {
    if (!(a && a.opacity === 0) && b.immediateRender === undefined) b = Object.assign({ immediateRender: false }, b);
    return _fromTo(t, a, b, pos);
  };

  // ── efectos comunes ────────────────────────────────────────────────────
  function flash(t, a, d, red) { tl.fromTo(red ? "#flashred" : "#flash", { opacity: a }, { opacity: 0, duration: d || 0.25, ease: "power2.out" }, t); }
  function shake(t, amp, dur) {
    const n = 7, step = dur / n;
    for (let i = 0; i < n; i++) { const k = 1 - i / n; tl.to("#world", { x: (rnd() * 2 - 1) * amp * k, y: (rnd() * 2 - 1) * amp * k, duration: step, ease: "none" }, t + i * step); }
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
    $$("#tear i").forEach((b) => { tl.set(b, { x: (rnd() * 2 - 1) * 120 }, t); tl.set(b, { x: (rnd() * 2 - 1) * 120 }, t + 0.05); });
    tl.set("#tear", { opacity: 0 }, t + 0.1);
  }
  for (let i = 0; i < Math.ceil(12 * SP.dur); i++) tl.set("#grain", { x: -((i * 37) % 128), y: -((i * 53) % 128) }, i / 12);
  for (let tb = SP.groove[0]; tb < SP.groove[1]; tb += BEAT) tl.fromTo("#pulse", { opacity: 0.3 }, { opacity: 0, duration: 0.32, ease: "power2.out" }, tb);
  function exitFade(sel, t) { tl.to(sel, { opacity: 0, y: -60, duration: 0.2, ease: "power2.in" }, t); }

  const CURSOR_SVG = '<svg width="40" height="44" viewBox="0 0 40 44"><path d="M4 2 L4 33 L12 26 L18 40 L24 37.5 L18 24 L29 24 Z" fill="#fff" stroke="#05060a" stroke-width="2.6" stroke-linejoin="round"/></svg>';
  const B = {};

  // ═══ words ════════════════════════════════════════════════════════════
  B.words = function (sc, el, t0, dur) {
    if (sc.bars) {
      const bars = $(".hbars", el); const H = [];
      for (let i = 0; i < 40; i++) { const b = document.createElement("i"); b.style.height = "760px"; bars.appendChild(b); H.push(0.25 + rnd() * 0.75); }
      const be = Array.from(bars.children);
      tl.set(be, { scaleY: 0.04 }, t0);
      tl.to(be, { scaleY: (i) => H[i], duration: 0.55, ease: "power3.out", stagger: { each: 0.008, from: "center" } }, t0 + 0.05);
      for (let k = 1; t0 + k * BEAT < t0 + dur - 0.3; k++) tl.to(be, { scaleY: (i) => H[i] * (0.45 + 0.55 * ((i * 7 + k * 13) % 10) / 10), duration: 0.14, ease: "power2.out" }, t0 + k * BEAT);
    }
    const W = $$(".word", el); tl.set(W, { opacity: 0 }, t0);
    W.forEach((w, i) => {
      const at = t0 + sc.at[i]; const big = (sc.lines[i].big === true);
      tl.fromTo(w, { opacity: 0, scale: big ? 3.2 : 2.4, y: big ? -110 : -60, rotation: big ? 6 : -4 }, { opacity: 1, scale: 1, y: 0, rotation: 0, duration: 0.24, ease: "expo.out" }, at);
      flash(at, big ? 0.65 : 0.3, big ? 0.35 : 0.2, !big); shake(at, big ? 24 : 12, big ? 0.4 : 0.26); glitch(w, at + 0.26, 0.16);
    });
    if (sc.strike !== undefined) {
      const w = W[sc.strike.line]; const s = $(".strike", w);
      tl.fromTo(s, { scaleX: 0 }, { scaleX: 1, duration: 0.25, ease: "power4.out" }, t0 + sc.strike.at);
      tl.to(w, { opacity: 0.35, y: -20, duration: 0.3, ease: "power2.in" }, t0 + sc.strike.at + 0.45);
    }
    if (sc.sub) tl.fromTo($(".wsub", el), { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.3, ease: "power3.out" }, t0 + sc.sub_at);
    tl.to($(".words", el), { x: -40, opacity: 0, duration: 0.18, ease: "power2.in" }, t0 + dur - 0.22);
    if (sc.sub) tl.to($(".wsub", el), { opacity: 0, duration: 0.15 }, t0 + dur - 0.2);
    if (sc.bars) tl.to($(".hbars", el), { opacity: 0, duration: 0.2 }, t0 + dur - 0.2);
    tear(t0 + dur - 0.2); flash(t0 + dur - 0.08, 0.5, 0.22);
  };

  // ═══ shot (demo de la app con cursor) ════════════════════════════════
  B.shot = function (sc, el, t0, dur) {
    const camEl = $(".cam", el), cur = $(".cursor", el), cin = $(".cin", el);
    const CK = [];
    function cam(a) {
      const S = S0 * a.z; CK.push({ t: a.at, d: a.d, z: a.z });
      // la cámara no sale de la captura (evita bandas negras)
      let cx = a.cx, cy = a.cy;
      if (sc.img_size) {
        const vw = 1000 / S, vh = 1060 / S;
        cx = sc.img_size[0] <= vw ? sc.img_size[0] / 2 : Math.min(Math.max(cx, vw / 2), sc.img_size[0] - vw / 2);
        cy = sc.img_size[1] <= vh ? sc.img_size[1] / 2 : Math.min(Math.max(cy, vh / 2), sc.img_size[1] - vh / 2);
      }
      const props = { x: 500 - cx * S, y: 530 - cy * S, scale: S };
      const cs = 2.0 / S;
      if (a.d <= 0) { tl.set(camEl, props, t0 + a.at); tl.set(cin, { scale: cs }, t0 + a.at); }
      else { tl.to(camEl, Object.assign({ duration: a.d, ease: a.ease || "power3.inOut" }, props), t0 + a.at); tl.to(cin, { scale: cs, duration: a.d, ease: a.ease || "power3.inOut" }, t0 + a.at); }
    }
    function zoomAt(t) { let z = 1; for (const k of CK) if (t >= k.t) z = k.z; return z; }
    sc.cam.forEach(cam);
    tl.fromTo($(".vp", el), { y: 520, opacity: 0, scale: 0.9 }, { y: 0, opacity: 1, scale: 1, duration: 0.5, ease: "expo.out" }, t0);
    tl.fromTo($(".stepper", el), { opacity: 0 }, { opacity: 1, duration: 0.3 }, t0 + 0.2);
    tl.fromTo($(".stlbl", el), { opacity: 0 }, { opacity: 1, duration: 0.3 }, t0 + 0.2);
    const shots = $$("img.shot", el); tl.set(shots, { opacity: 0 }, t0);
    let prev = null;
    sc.imgs.forEach((im) => {
      const e = $('img.shot[data-n="' + im.id + '"]', el);
      if (prev) { tl.to(prev, { opacity: 0, duration: 0.1 }, t0 + im.at); flash(t0 + im.at, 0.5, 0.2); tear(t0 + im.at); tl.fromTo($(".vp", el), { x: -22 }, { x: 0, duration: 0.3, ease: "elastic.out(1,0.4)" }, t0 + im.at); tl.fromTo(camEl, { filter: "blur(12px)" }, { filter: "blur(0px)", duration: 0.28, ease: "power2.out" }, t0 + im.at); }
      tl.to(e, { opacity: 1, duration: 0.1 }, t0 + im.at); prev = e;
    });
    sc.caps.forEach((c, i) => {
      const d = $$(".cap", el)[i];
      tl.fromTo(d, { x: -110, opacity: 0 }, { x: 0, opacity: 1, duration: 0.3, ease: "expo.out" }, t0 + c.at);
      tl.to(d, { x: 70, opacity: 0, duration: 0.16, ease: "power2.in" }, t0 + c.until - 0.16);
      if (c.step !== undefined) tl.to($$(".stepper i", el)[c.step], { backgroundColor: "#ff1f3a", duration: 0.2 }, t0 + c.at);
    });
    if (sc.logo) tl.to($(".logomini", el), { opacity: 0.9, duration: 0.3 }, t0 + sc.logo);
    // cursor
    sc.cur.forEach((m) => {
      if (m.set) tl.set(cur, { x: m.x, y: m.y, opacity: 1 }, t0 + m.at);
      else { tl.to(cur, { x: m.x, duration: m.d, ease: "power2.inOut" }, t0 + m.at); tl.to(cur, { y: m.y, duration: m.d, ease: "power1.inOut" }, t0 + m.at); }
    });
    const rip = $(".ripples", el);
    sc.clicks.forEach((c) => {
      const r = document.createElement("div"); r.className = "ripple"; r.style.left = c.x + "px"; r.style.top = c.y + "px"; rip.appendChild(r);
      const S = S0 * zoomAt(c.at);
      tl.fromTo(r, { scale: 0.3 / S * 0.6, opacity: 1 }, { scale: 2.6 / S, opacity: 0, duration: 0.5, ease: "power2.out" }, t0 + c.at);
      tl.fromTo(cin, { scale: 2.0 / S }, { scale: 1.6 / S, duration: 0.07, yoyo: true, repeat: 1, ease: "power1.inOut" }, t0 + c.at - 0.04);
    });
    const hlh = $(".hls", el);
    sc.hls.forEach((h) => {
      const e = document.createElement("div"); e.className = "hl"; e.style.left = h.box[0] + "px"; e.style.top = h.box[1] + "px"; e.style.width = h.box[2] + "px"; e.style.height = h.box[3] + "px"; hlh.appendChild(e);
      tl.fromTo(e, { opacity: 0, scale: 1.18 }, { opacity: 1, scale: 1, duration: 0.14, ease: "power3.out" }, t0 + h.at);
      tl.to(e, { opacity: 0, duration: 0.22 }, t0 + h.at + (h.hold || 0.4));
    });
    if (sc.dlg) {
      tl.set($(".dim", el), { opacity: 0 }, t0); tl.to($(".dim", el), { opacity: 1, duration: 0.12 }, t0 + sc.dlg.at); tl.to($(".dlg", el), { opacity: 1, duration: 0.12 }, t0 + sc.dlg.at);
    }
    if (sc.chip) {
      const c = $(".chip", el), m = sc.chip;
      tl.set(c, { opacity: 0, scale: 2.0 }, t0);
      tl.fromTo(c, { x: m.from[0], y: m.from[1], opacity: 0 }, { x: m.from[0], y: m.from[1], opacity: 1, duration: 0.2 }, t0 + m.at);
      tl.to(c, { x: m.to[0], duration: m.d, ease: "power2.inOut" }, t0 + m.at + 0.2); tl.to(c, { y: m.to[1], duration: m.d, ease: "power1.inOut" }, t0 + m.at + 0.2);
      tl.to(c, { scale: 0.2, opacity: 0, duration: 0.18, ease: "power2.in" }, t0 + m.at + 0.2 + m.d);
    }
    if (sc.confetti !== undefined) {
      const conf = $(".conf", el);
      for (let i = 0; i < 46; i++) {
        const c = document.createElement("i"); c.className = "cf"; c.style.left = "500px"; c.style.top = "820px"; c.style.background = ["#ff1f3a", "#ffffff", "#ffd21f", "#a855f7"][i % 4]; conf.appendChild(c);
        const ang = -Math.PI / 2 + (rnd() * 2 - 1) * 1.1, sp = 320 + rnd() * 560;
        tl.fromTo(c, { x: 0, y: 0, opacity: 1, rotation: 0 }, { x: Math.cos(ang) * sp, y: Math.sin(ang) * sp, rotation: 360 * (rnd() * 2 - 1) * 2, duration: 0.55, ease: "power2.out" }, t0 + sc.confetti + 0.02);
        tl.to(c, { y: "+=700", opacity: 0, duration: 0.9, ease: "power2.in" }, t0 + sc.confetti + 0.57);
      }
      flash(t0 + sc.confetti, 0.5, 0.35, true);
    }
    tl.to([$(".caps", el), $(".vp", el), $(".stepper", el), $(".stlbl", el), $(".logomini", el)], { opacity: 0, duration: 0.18 }, t0 + dur - 0.2);
    tear(t0 + dur - 0.2);
  };

  // ═══ race (a mano vs AutoPrevias) ════════════════════════════════════
  B.race = function (sc, el, t0, dur) {
    const cols = ["#ff1f3a", "#7c3aed", "#2563eb", "#16a34a", "#d97706", "#db2777"];
    const lanes = $(".lanes", el);
    for (let l = 0; l < 6; l++) {
      const lane = document.createElement("div"); lane.className = "lane"; let x = 14 + rnd() * 40;
      while (x < 900) { const w = 70 + rnd() * 190; const c = document.createElement("div"); c.className = "clipbox"; c.style.left = x + "px"; c.style.width = w + "px"; c.style.background = cols[(l + Math.floor(rnd() * 3)) % 6]; lane.appendChild(c); x += w + 8 + rnd() * 30; }
      lanes.appendChild(lane);
    }
    tl.fromTo($$(".rp", el), { opacity: 0, y: 60 }, { opacity: 1, y: 0, duration: 0.4, stagger: 0.12, ease: "expo.out" }, t0);
    tl.from($$(".clipbox", el), { scaleX: 0, transformOrigin: "0% 50%", duration: 0.22, stagger: 0.01, ease: "power3.out" }, t0 + 0.3);
    const rt = sc.race_end - 0.4;
    for (let k = 0; k < 4; k++) tl.fromTo($(".playhead", el), { x: 0 }, { x: 900, duration: rt / 4, ease: "none" }, t0 + 0.4 + k * rt / 4);
    const A = $(".tA", el), Bt = $(".tB", el);
    const fmt = (v) => String(Math.floor(v / 60)).padStart(2, "0") + ":" + String(Math.floor(v % 60)).padStart(2, "0");
    for (let i = 0; i <= 60; i++) { const f = i / 60; tl.set(A, { textContent: fmt(300 * f * f) }, t0 + 0.4 + f * rt); }
    for (let i = 0; i <= 30; i++) { const f = i / 30; tl.set(Bt, { textContent: fmt(30 * f) }, t0 + sc.imgs[0].at + f * (sc.done_at - sc.imgs[0].at)); }
    const im = $$(".rvp img", el); tl.set(im, { opacity: 0 }, t0);
    sc.imgs.forEach((m, i) => {
      const e = im[i]; if (i) { tl.to(im[i - 1], { opacity: 0, duration: 0.1 }, t0 + m.at); flash(t0 + m.at, 0.35, 0.2); }
      tl.set(e, { y: -m.y }, t0 + m.at - 0.05); tl.to(e, { opacity: 1, duration: 0.1 }, t0 + m.at);
    });
    tl.fromTo($(".rdone", el), { opacity: 0, scale: 2.4, y: -40 }, { opacity: 1, scale: 1, y: 0, duration: 0.26, ease: "expo.out" }, t0 + sc.done_at);
    flash(t0 + sc.done_at, 0.8, 0.4); shake(t0 + sc.done_at, 22, 0.4);
    tl.to(Bt, { color: "#22e07a", duration: 0.2 }, t0 + sc.done_at);
    $$(".stamp", el).forEach((s, i) => {
      const at = t0 + sc.stamps[i];
      tl.fromTo(s, { opacity: 0, x: i % 2 ? 900 : -900, rotation: i % 2 ? 8 : -8 }, { opacity: 1, x: 0, rotation: i % 2 ? 2 : -2, duration: 0.2, ease: "expo.out" }, at);
      flash(at, 0.18, 0.18, true);
    });
    tl.to($(".race", el), { opacity: 0, duration: 0.2 }, t0 + dur - 0.2); tear(t0 + dur - 0.2);
  };

  // ═══ cards (vídeos de muestra) ═══════════════════════════════════════
  B.cards = function (sc, el, t0, dur) {
    $$(".ncard", el).forEach((c, i) => {
      const m = sc.cards[i];
      const from = m.from === "left" ? { x: -460, y: 0 } : m.from === "right" ? { x: 460, y: 0 } : { x: 0, y: 380 };
      tl.fromTo(c, Object.assign({ opacity: 0, scale: 0.8, rotation: (m.rot || 0) * 2 }, from), { opacity: 1, x: 0, y: 0, scale: 1, rotation: m.rot || 0, duration: 0.4, ease: "expo.out" }, t0 + m.at);
      flash(t0 + m.at, 0.25, 0.25, i % 2 === 1);
      tl.to(c, { y: (i % 2 ? 12 : -14), duration: 0.9, yoyo: true, repeat: 5, ease: "sine.inOut" }, t0 + m.at + 0.5);
    });
    if (sc.title) { const w = $(".ctitle .word", el); tl.fromTo(w, { opacity: 0, scale: 2.4, y: 40 }, { opacity: 1, scale: 1, y: 0, duration: 0.24, ease: "expo.out" }, t0 + sc.title_at); shake(t0 + sc.title_at, 16, 0.25); glitch(w, t0 + sc.title_at + 0.26, 0.16); }
    if (sc.sub) tl.fromTo($(".csub", el), { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.3, ease: "power3.out" }, t0 + sc.sub_at);
    $$(".badge", el).forEach((b, i) => { const at = t0 + sc.badges[i].at; tl.fromTo(b, { opacity: 0, scale: 0.4, rotation: -8 }, { opacity: 1, scale: 1, rotation: sc.badges[i].rot || 0, duration: 0.3, ease: "back.out(3)" }, at); flash(at, 0.2, 0.2, true); });
    tl.to(el.querySelectorAll(".ncard,.ctitle,.csub,.badge"), { opacity: 0, y: "-=70", duration: 0.2, ease: "power2.in" }, t0 + dur - 0.22);
    tear(t0 + dur - 0.2); flash(t0 + dur - 0.08, 0.5, 0.22);
  };

  // ═══ compare (Basic vs Plus) ═════════════════════════════════════════
  B.compare = function (sc, el, t0, dur) {
    $$(".cpanel", el).forEach((p, pi) => {
      const m = sc.panels[pi];
      tl.fromTo(p, { opacity: 0, x: pi ? 300 : -300 }, { opacity: 1, x: 0, duration: 0.4, ease: "expo.out" }, t0 + m.at);
      flash(t0 + m.at, 0.3, 0.25, pi === 0);
      $$(".it", p).forEach((it, i) => tl.fromTo(it, { opacity: 0, x: -50 }, { opacity: 1, x: 0, duration: 0.28, ease: "power3.out" }, t0 + m.items_at[i]));
    });
    tl.to($$(".cpanel", el), { opacity: 0, y: -60, duration: 0.2, ease: "power2.in" }, t0 + dur - 0.22);
    tear(t0 + dur - 0.2); flash(t0 + dur - 0.08, 0.5, 0.22);
  };

  // ═══ tips (errores / consejos) ═══════════════════════════════════════
  B.tips = function (sc, el, t0, dur) {
    if (sc.head) tl.fromTo($(".word", el), { opacity: 0, scale: 2.2, y: -50 }, { opacity: 1, scale: 1, y: 0, duration: 0.24, ease: "expo.out" }, t0 + 0.05);
    $$(".tip", el).forEach((p, i) => {
      const m = sc.tips[i];
      tl.fromTo(p, { opacity: 0, x: -400, rotation: -4 }, { opacity: 1, x: 0, rotation: 0, duration: 0.35, ease: "expo.out" }, t0 + m.at);
      flash(t0 + m.at, 0.3, 0.2, true); shake(t0 + m.at, 12, 0.25);
      tl.fromTo($(".fix", p), { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.3, ease: "power3.out" }, t0 + m.fix_at);
      tl.to(p, { borderColor: "#22e07a", duration: 0.2 }, t0 + m.fix_at);
    });
    tl.to(el.querySelectorAll(".tip,.word"), { opacity: 0, y: -60, duration: 0.2, ease: "power2.in" }, t0 + dur - 0.22);
    tear(t0 + dur - 0.2); flash(t0 + dur - 0.08, 0.5, 0.22);
  };

  // ═══ gallery (paletas / looks) ═══════════════════════════════════════
  B.gallery = function (sc, el, t0, dur) {
    const imgs = $$(".gframe img", el), labs = $$(".glabel", el), sws = $$(".gsw i", el), frame = $(".gframe", el);
    tl.fromTo(frame, { opacity: 0, scale: 0.8, y: 120 }, { opacity: 1, scale: 1, y: 0, duration: 0.4, ease: "expo.out" }, t0);
    tl.set(imgs, { opacity: 0 }, t0); tl.set(labs, { opacity: 0 }, t0);
    sc.frames.forEach((f, i) => {
      const at = t0 + f.at;
      if (i) { tl.set(imgs[i - 1], { opacity: 0 }, at); tl.set(labs[i - 1], { opacity: 0 }, at); }
      tl.set(imgs[i], { opacity: 1 }, at);
      tl.fromTo(labs[i], { opacity: 0, scale: 1.8, y: 20 }, { opacity: 1, scale: 1, y: 0, duration: 0.22, ease: "expo.out" }, at);
      tl.fromTo(frame, { scale: 1.05 }, { scale: 1, duration: 0.3, ease: "power2.out" }, at);
      tl.fromTo(frame, { borderColor: f.color }, { borderColor: f.color, duration: 0.01 }, at);
      tl.to(sws[i], { opacity: 1, scale: 1.25, duration: 0.2 }, at);
      if (i) tl.to(sws[i - 1], { scale: 1, duration: 0.2 }, at);
      tl.fromTo("#flash", { opacity: 0.45, backgroundColor: f.color }, { opacity: 0, duration: 0.3, ease: "power2.out" }, at);
      shake(at, 10, 0.2);
    });
    tl.set("#flash", { backgroundColor: "#ffffff" }, t0 + dur - 0.3);
    tl.to([frame, $(".gsw", el), ...labs], { opacity: 0, y: -60, duration: 0.2, ease: "power2.in" }, t0 + dur - 0.22);
    tear(t0 + dur - 0.2);
  };

  // ═══ scan (forma de onda por secciones + datos) ══════════════════════
  B.scan = function (sc, el, t0, dur) {
    const wrap = $(".wfrap", el), line = $(".scanline", el), bars = $$(".wfrap rect", el);
    tl.fromTo(wrap, { opacity: 0, y: 60, scale: 0.95 }, { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "expo.out" }, t0);
    tl.set(bars, { opacity: 0.18 }, t0);
    const W = 960, x0 = t0 + sc.sweep_at, sd = sc.sweep_d;
    tl.fromTo(line, { opacity: 1, x: 0 }, { opacity: 1, x: W - 5, duration: sd, ease: "none" }, x0);
    tl.to(line, { opacity: 0, duration: 0.2 }, x0 + sd);
    sc.secs.forEach((s, i) => {
      const at = x0 + sd * s.from;
      const idx = bars.filter((b, j) => j / bars.length >= s.from && j / bars.length < s.to);
      tl.to(idx, { opacity: 1, duration: 0.2, stagger: 0.003 }, at);
      const l = $$(".seclbl", el)[i];
      tl.fromTo(l, { opacity: 0, y: -20, scale: 0.8 }, { opacity: 1, y: 0, scale: 1, duration: 0.25, ease: "back.out(3)" }, at + 0.1);
      if (s.hit) { flash(at + 0.1, 0.45, 0.3, true); shake(at + 0.1, 14, 0.25); }
    });
    $$(".scard", el).forEach((c, i) => {
      const at = t0 + sc.cards[i].at;
      tl.fromTo(c, { opacity: 0, y: 140, scale: 0.7 }, { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "back.out(2.4)" }, at);
      flash(at, 0.25, 0.2, true);
    });
    if (sc.title) tl.fromTo($(".word", el), { opacity: 0, scale: 2.2, y: -50 }, { opacity: 1, scale: 1, y: 0, duration: 0.24, ease: "expo.out" }, t0 + 0.05);
    tl.to(el.querySelectorAll(".wfrap,.scard,.word"), { opacity: 0, y: -60, duration: 0.2, ease: "power2.in" }, t0 + dur - 0.22);
    tear(t0 + dur - 0.2); flash(t0 + dur - 0.08, 0.5, 0.22);
  };

  // ═══ antileak (firma repetida) ═══════════════════════════════════════
  B.antileak = function (sc, el, t0, dur) {
    const bar = $(".tlbar", el), bars = $$(".tlbar rect", el);
    tl.fromTo(bar, { opacity: 0, y: 60 }, { opacity: 1, y: 0, duration: 0.4, ease: "expo.out" }, t0);
    tl.fromTo(bars, { scaleY: 0.1 }, { scaleY: 1, duration: 0.5, stagger: 0.004, ease: "power3.out", transformOrigin: "50% 50%" }, t0 + 0.2);
    $$(".mark", el).forEach((m, i) => {
      const at = t0 + sc.marks[i];
      tl.fromTo(m, { opacity: 0, y: -80, scale: 0.4 }, { opacity: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(3)" }, at);
      flash(at, 0.18, 0.18, true);
    });
    $$(".badge", el).forEach((b, i) => { const at = t0 + sc.badges[i].at; tl.fromTo(b, { opacity: 0, scale: 0.4, rotation: -8 }, { opacity: 1, scale: 1, rotation: sc.badges[i].rot || 0, duration: 0.3, ease: "back.out(3)" }, at); flash(at, 0.25, 0.2, true); });
    const st = $(".stamp", el); if (st) { tl.fromTo(st, { opacity: 0, scale: 2.6, rotation: -14 }, { opacity: 1, scale: 1, rotation: -6, duration: 0.25, ease: "expo.out" }, t0 + sc.stamp_at); flash(t0 + sc.stamp_at, 0.7, 0.35); shake(t0 + sc.stamp_at, 20, 0.35); }
    if (sc.title) tl.fromTo($(".word", el), { opacity: 0, scale: 2.2, y: -50 }, { opacity: 1, scale: 1, y: 0, duration: 0.24, ease: "expo.out" }, t0 + 0.05);
    tl.to(el.querySelectorAll(".tlbar,.badge,.stamp,.word"), { opacity: 0, y: -60, duration: 0.2, ease: "power2.in" }, t0 + dur - 0.22);
    tear(t0 + dur - 0.2); flash(t0 + dur - 0.08, 0.5, 0.22);
  };

  // ═══ tempo (anti-retoque) ════════════════════════════════════════════
  B.tempo = function (sc, el, t0, dur) {
    const box = $(".tempo", el), path = $(".tempo path.w", el), L = path.getTotalLength();
    tl.fromTo(box, { opacity: 0, y: 60 }, { opacity: 1, y: 0, duration: 0.4, ease: "expo.out" }, t0);
    tl.set(path, { strokeDasharray: L, strokeDashoffset: L }, t0);
    tl.to(path, { strokeDashoffset: 0, duration: sc.draw_d, ease: "none" }, t0 + sc.draw_at);
    const nums = $$(".tnum", el);
    sc.vals.forEach((v, i) => tl.set(nums[0], { textContent: v.toFixed(1) }, t0 + sc.draw_at + sc.draw_d * i / (sc.vals.length - 1)));
    tl.fromTo(nums[1], { opacity: 0 }, { opacity: 1, duration: 0.3 }, t0 + sc.draw_at);
    $$(".stamp", el).forEach((s) => { tl.fromTo(s, { opacity: 0, scale: 2.6, rotation: -14 }, { opacity: 1, scale: 1, rotation: -6, duration: 0.25, ease: "expo.out" }, t0 + sc.stamp_at); });
    flash(t0 + sc.stamp_at, 0.7, 0.35); shake(t0 + sc.stamp_at, 20, 0.35);
    if (sc.title) tl.fromTo($(".word", el), { opacity: 0, scale: 2.2, y: -50 }, { opacity: 1, scale: 1, y: 0, duration: 0.24, ease: "expo.out" }, t0 + 0.05);
    $$(".badge", el).forEach((b, i) => { const at = t0 + sc.badges[i].at; tl.fromTo(b, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)" }, at); });
    tl.to(el.querySelectorAll(".tempo,.stamp,.word,.badge"), { opacity: 0, y: -60, duration: 0.2, ease: "power2.in" }, t0 + dur - 0.22);
    tear(t0 + dur - 0.2); flash(t0 + dur - 0.08, 0.5, 0.22);
  };

  // ═══ folder (lote) ═══════════════════════════════════════════════════
  B.folder = function (sc, el, t0, dur) {
    const chips = $$(".fchip", el), n = chips.length, cnt = $(".fcount", el);
    tl.fromTo(chips, { opacity: 0, y: 50, scale: 0.8 }, { opacity: 1, y: 0, scale: 1, duration: 0.3, stagger: 0.03, ease: "back.out(2)" }, t0 + sc.in_at);
    tl.set(cnt, { textContent: "0 / " + n }, t0);
    tl.fromTo(cnt, { opacity: 0, scale: 1.5 }, { opacity: 1, scale: 1, duration: 0.3, ease: "expo.out" }, t0 + 0.1);
    chips.forEach((c, i) => {
      const at = t0 + sc.run_at + (sc.run_d * Math.pow(i / (n - 1), 0.8));
      tl.to(c, { backgroundColor: "#0f3d27", borderColor: "#22e07a", color: "#22e07a", duration: 0.12 }, at);
      tl.set(c, { textContent: "✓ PREVIA" }, at);
      tl.set(cnt, { textContent: (i + 1) + " / " + n }, at);
    });
    const end = t0 + sc.run_at + sc.run_d;
    tl.to(cnt, { color: "#22e07a", duration: 0.2 }, end); flash(end, 0.7, 0.4); shake(end, 22, 0.4);
    $$(".stamp", el).forEach((s) => tl.fromTo(s, { opacity: 0, scale: 2.4, rotation: -10 }, { opacity: 1, scale: 1, rotation: -4, duration: 0.3, ease: "expo.out" }, end + 0.1));
    if (sc.title) tl.fromTo($(".word", el), { opacity: 0, scale: 2.2, y: -50 }, { opacity: 1, scale: 1, y: 0, duration: 0.24, ease: "expo.out" }, t0 + 0.05);
    tl.to(el.querySelectorAll(".fgrid,.fcount,.stamp,.word"), { opacity: 0, y: -60, duration: 0.2, ease: "power2.in" }, t0 + dur - 0.22);
    tear(t0 + dur - 0.2); flash(t0 + dur - 0.08, 0.5, 0.22);
  };

  // ═══ cta ═════════════════════════════════════════════════════════════
  B.cta = function (sc, el, t0, dur) {
    const C0 = t0;
    flash(C0, 0.9, 0.4, true); shake(C0, 22, 0.4);
    tl.fromTo($(".ctaemb", el), { opacity: 0, scale: 2.6, rotation: -8 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.5, ease: "expo.out" }, C0);
    tl.fromTo($$(".ctatitle span", el), { opacity: 0, y: 120, scale: 1.7 }, { opacity: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(2)", stagger: 0.04 }, C0 + 0.25);
    tl.fromTo($$(".eds span", el), { opacity: 0, scale: 0 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)", stagger: 0.12 }, C0 + 0.8);
    tl.fromTo($(".ctaline", el), { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.35, ease: "power3.out" }, C0 + 1.05);
    tl.fromTo($(".buy", el), { opacity: 0, y: 160, scale: 0.9 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "expo.out" }, C0 + 1.35);
    tl.fromTo($(".ctabanner", el), { opacity: 0 }, { opacity: 1, duration: 0.4 }, C0 + 1.7);
    tl.fromTo($(".ctatag", el), { opacity: 0 }, { opacity: 1, duration: 0.4 }, C0 + 2.0);
    const cur = $(".cur2", el), buy = [540 + 120, 1228 + 30], cc = C0 + sc.click_at;
    tl.set($(".cur2 .cin", el), { scale: 1.7 }, C0);
    tl.set(cur, { x: 880, y: 1760, opacity: 1 }, C0 + 1.7);
    tl.to(cur, { x: buy[0], duration: sc.click_at - 1.9, ease: "power2.inOut" }, C0 + 1.9);
    tl.to(cur, { y: buy[1], duration: sc.click_at - 1.9, ease: "power1.inOut" }, C0 + 1.9);
    tl.fromTo($(".cur2 .cin", el), { scale: 1.7 }, { scale: 1.3, duration: 0.07, yoyo: true, repeat: 1 }, cc - 0.04);
    tl.set($(".rip2", el), { left: buy[0], top: buy[1] }, cc - 0.1);
    tl.fromTo($(".rip2", el), { scale: 0.3, opacity: 1 }, { scale: 3.2, opacity: 0, duration: 0.55, ease: "power2.out" }, cc);
    tl.fromTo($(".buy", el), { scale: 1 }, { scale: 0.96, duration: 0.07, yoyo: true, repeat: 1 }, cc - 0.04);
    flash(cc, 0.3, 0.25, true);
    for (let t = C0 + 2.2; t < t0 + dur - 0.7; t += 0.8) tl.fromTo($(".buy", el), { boxShadow: "0 0 80px rgba(255,31,58,.6)" }, { boxShadow: "0 0 160px rgba(255,31,58,1)", duration: 0.3, yoyo: true, repeat: 1 }, t);
    tl.to("#world", { opacity: 0, duration: 0.45, ease: "power2.in" }, t0 + dur - 0.5);
  };

  SP.scenes.forEach((sc, i) => { const el = document.getElementById("s" + i); B[sc.type](sc, el, sc.t0, sc.dur); });
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
})();
