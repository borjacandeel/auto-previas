"""Vídeo 1 · De 5 min a 30 s: la carrera (sin voz)."""
SPEC = dict(
    voice="em_alex", lang="es", groove_from=3.2,
    scenes=[
        dict(type="words", dur=3.2, bars=True, top=640, gap=0.5,
             lines=[dict(t="¿CUÁNTO TARDAS", cls="", size=150), dict(t="TÚ EN UNA", cls="", size=150), dict(t="PREVIA?", cls="red", size=260, big=True)]),
        dict(type="race", dur=11.0, race_end=10.2, done_at=3.8,
             stamps=[1.6, 3.3, 5.0, 6.7], stamps_def=[
                 dict(t="✂ Cortar", x=110, y=520), dict(t="♪ Cuadrar el BPM", x=330, y=450, cls="white"),
                 dict(t="⏱ Exportar", x=560, y=560), dict(t="↻ Y repetir…", x=250, y=380, cls="white")],
             imgs=[dict(at=0.9, name="01_bienvenida", y=40), dict(at=2.1, name="03_cargada", y=70), dict(at=3.0, name="08_generada", y=430)]),
        dict(type="words", dur=3.4, top=560, at=[0.15, 0.85, 1.1], strike=dict(line=0, at=0.55),
             lines=[dict(t="DE 5 MIN", cls="gray", size=190), dict(t="A 30", cls="red", size=330, big=True), dict(t="SEGUNDOS", cls="", size=165)],
             sub="Detecta BPM, clave y drops.<br>Corta y exporta. Solo.", sub_at=1.6, sub_top=1380),
        dict(type="shot", dur=6.2, steps=3, logo=4.2,
             caps=[dict(at=0.1, until=1.9, num="01", title="Elige <em>la duración</em>", sub="15 s · 30 s · 60 s · 2 min", step=0),
                   dict(at=2.0, until=3.6, num="02", title="Un clic: <em>generar</em>", sub="Cortes, transiciones y metadatos solos", step=1),
                   dict(at=3.7, until=6.0, num="03", title="<em>Lista</em> para enviar", sub="MP3 · WAV · vídeo animado", step=2)],
             imgs=[dict(at=0, name="03_cargada"), dict(at=3.65, name="08_generada")],
             cam=[dict(at=0, d=0, c="loaded.waveform", z=1.3), dict(at=0.35, d=0.7, c="loaded.p30", z=2.0), dict(at=2.0, d=0.8, c="loaded.generate", z=1.45),
                  dict(at=3.7, d=0.8, c=[900, 1560], z=1.25)],
             cur=[dict(at=0.05, set="loaded.waveform"), dict(at=0.4, d=0.9, to="loaded.p30"), dict(at=2.0, d=1.0, to="loaded.generate"), dict(at=3.8, d=0.7, to="generated.open")],
             clicks=[dict(at=1.5, to="loaded.p30"), dict(at=3.2, to="loaded.generate")],
             hls=[dict(at=1.47, hold=0.45, box="loaded.p30", pad=6), dict(at=3.17, hold=1.0, box="loaded.generate", pad=6), dict(at=3.9, hold=1.4, box="generated.success", pad=6)],
             confetti=3.65),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Tu previa profesional,", line2="lista en segundos."),
    ])
