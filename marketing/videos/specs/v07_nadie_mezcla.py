"""Vídeo 7 · Nadie puede mezclar tu previa (voz en castellano)."""
SPEC = dict(
    voice="em_alex", lang="es", speed=1.04, groove_from=3.6,
    scenes=[
        dict(type="words", dur=3.6, bars=True, top=560, gap=0.55, vo="Le mandas una previa a ese DJ… y acaba mezclándola en su set.",
             lines=[dict(t="ENVÍAS", size=210), dict(t="TU PREVIA", size=190), dict(t="Y LA", size=200), dict(t="MEZCLAN", cls="red", size=260, big=True)]),
        dict(type="tempo", dur=7.0, title="ANTI-RETOQUE", vals=[128.0, 126.9, 129.4, 127.2, 129.6, 126.8, 128.9], draw_at=1.2, draw_d=3.6, stamp_at=5.0,
             badges=[dict(at=2.0, t="TEMPO VARIABLE", x=90, y=1390, bg="#7c3aed"), dict(at=2.8, t="MODO VINILO", x=600, y=1390, bg="#ff1f3a")],
             vo="Con el anti-retoque, el tempo de tu previa varía suavemente, y no hay forma de cuadrarla.", vo_at=0.5),
        dict(type="shot", dur=5.5, steps=2, logo=2.0,
             caps=[dict(at=0.2, until=5.4, num="♪", title="Editor <em>de BPM</em>", sub="Controla la variación de tempo (Plus)", step=0)],
             imgs=[dict(at=0, name="05_editor_bpm")],
             cam=[dict(at=0, d=0, c="bpm.plot", z=1.25), dict(at=0.8, d=0.9, c=[640, 1090], z=1.8)],
             cur=[dict(at=0.1, set="bpm.plot"), dict(at=0.9, d=1.0, to="bpm.manual")],
             clicks=[dict(at=2.2, to="bpm.manual")], hls=[dict(at=2.15, hold=1.4, box="bpm.manual", pad=6), dict(at=3.0, hold=1.6, box="bpm.plot", pad=6)],
             vo="Lo controlas en el editor de be pe eme de la edición Plus.", vo_at=0.3),
        dict(type="words", dur=3.6, top=500, gap=0.6, vo="Tu previa suena a ti, no a su set.",
             lines=[dict(t="SUENA", cls="red", size=260, big=True), dict(t="A TI", cls="red", size=260), dict(t="NO A", size=200), dict(t="SU SET", size=220)]),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Tu previa suena a ti.", line2="Solo a ti.", vo="Auto Previas, de Radical Récords. Consíguelo en Pei jip.", vo_at=1.2),
    ])
