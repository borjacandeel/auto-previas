"""Presentación oficial 1 · «Tu previa en 30 segundos» (sin voz; el modo con voz se genera sin --no-voice)."""
SPEC = dict(
    tall=True,
    voice="edge:es-ES-AlvaroNeural", lang="es", speed=1.16, groove_from=2.6,
    scenes=[
        # 1 · Gancho (≤3 s): pregunta directa
        dict(type="words", dur=2.8, bars=True, top=560, gap=0.42, vo="¿Cansado de hacer tus previas a mano?",
             lines=[dict(t="¿CANSADO", size=190), dict(t="DE HACER TUS", size=140), dict(t="PREVIAS", size=210), dict(t="A MANO?", cls="red", size=250, big=True)]),
        # 2 · El dolor: la lista interminable de pasos
        dict(type="race", dur=6.4, race_end=5.6, done_at=3.0,
             stamps=[0.3, 0.8, 1.3, 1.8, 2.3, 2.8, 3.3, 3.8],
             stamps_def=[
                 dict(t="Abrir Traktor", x=60, y=330), dict(t="Cargar el tema", x=420, y=400, cls="white"),
                 dict(t="Grabar", x=70, y=480), dict(t="Meter efectos", x=380, y=550, cls="white"),
                 dict(t="Acortar", x=80, y=630), dict(t="Guardar", x=400, y=700, cls="white"),
                 dict(t="Exportar", x=90, y=780), dict(t="Y subirlo…", x=400, y=850)],
             imgs=[dict(at=1.0, name="01_bienvenida", y=40), dict(at=2.0, name="03_cargada", y=70), dict(at=3.0, name="08_generada", y=430)],
             vo="Abrir Traktor, cargar, grabar, meter efectos, acortar, guardar, exportar… y subirlo.", vo_at=0.2),
        # 3 · Giro
        dict(type="words", dur=3.0, bars=True, top=560, gap=0.5, vo="Pues con Autoprevias, eso ya está hecho.",
             lines=[dict(t="PUES CON", size=150), dict(t="AUTOPREVIAS", cls="red", size=150, big=True), dict(t="ESO YA", size=190), dict(t="ESTÁ HECHO", cls="red", size=170, big=True)]),
        # 4 · Arrastras el tema y elige los mejores momentos
        dict(type="shot", dur=3.8, steps=3, logo=2.8,
             caps=[dict(at=0.15, until=1.9, num="01", title="Arrastra <em>tu tema</em>", sub="Y ya está", step=0),
                   dict(at=1.9, until=3.7, num="02", title="Elige <em>los mejores momentos</em>", sub="Cortes listos, sin tocar nada", step=1)],
             imgs=[dict(at=0, name="01_bienvenida"), dict(at=1.9, name="03_cargada")],
             cam=[dict(at=0, d=0, c=[1120, 700], z=1.7), dict(at=1.9, d=0.8, c="loaded.waveform", z=1.8)],
             cur=[dict(at=0.05, set="welcome.drop"), dict(at=0.3, d=0.8, to="welcome.open_btn"), dict(at=2.1, d=0.9, to="loaded.waveform")],
             clicks=[dict(at=1.3, to="welcome.open_btn")], hls=[dict(at=1.25, hold=0.6, box="welcome.open_btn", pad=6), dict(at=2.1, hold=1.9, box="loaded.waveform", pad=4)],
             vo="Arrastra tu tema, y ella elige los mejores momentos.", vo_at=0.2),
        # 5 · Efectos: el puntero los arrastra y el programa los coloca
        dict(type="shot", dur=4.9, steps=3, logo=3.9,
             caps=[dict(at=0.15, until=2.5, num="03", title="Arrastra <em>los efectos</em>", sub="Flanger o Filter Sweep, donde quieras", step=1),
                   dict(at=2.6, until=4.8, num="04", title="Mueve, estira <em>y escucha</em>", sub="Tú decides cuánto dura y dónde suena", step=1)],
             imgs=[dict(at=0, name="p_estudio_0"), dict(at=1.55, name="p_estudio_1"), dict(at=3.75, name="p_estudio_2")],
             cam=[dict(at=0, d=0, c=[700, 790], z=2.0), dict(at=1.9, d=0.8, c=[1180, 790], z=1.7)],
             cur=[dict(at=0.05, set=[417, 815]), dict(at=0.5, d=0.9, to=[946, 752]), dict(at=2.1, d=0.5, to=[589, 815]), dict(at=2.8, d=0.9, to=[1779, 752])],
             clicks=[dict(at=1.5, to=[946, 752]), dict(at=2.65, to=[589, 815]), dict(at=3.7, to=[1779, 752])],
             hls=[dict(at=0.3, hold=1.0, box=[359, 786, 125, 52], pad=4), dict(at=1.45, hold=1.0, box=[895, 722, 100, 56], pad=6),
                  dict(at=2.6, hold=0.9, box=[497, 786, 183, 52], pad=4), dict(at=3.65, hold=1.1, box=[1725, 722, 110, 56], pad=6)],
             vo="Corta y mete efectos, arrastrándolos sobre la onda.", vo_at=0.2),
        # 6 · Vídeo animado
        dict(type="cards", dur=3.8, title="Vídeo animado", title_top=1290, title_at=1.2, sub="TikTok · Reels · Shorts · YouTube", sub_at=1.6, sub_top=1500,
             cards=[dict(src="neon_916_crimson", x=285, y=140, w=560, h=996, at=0.15, rot=0), dict(src="neon_11", x=20, y=630, w=480, h=480, at=0.6, rot=-4, **{"from": "left"}),
                    dict(src="neon_169", x=560, y=720, w=500, h=281, at=1.0, rot=4, **{"from": "right"})],
             badges=[], vo="Y crea el vídeo animado para tus redes, en tres formatos.", vo_at=0.2),
        # 7 · Antifugas
        dict(type="antileak", dur=4.2, title="ANTIFUGAS", mark_pos=[0.1, 0.28, 0.46, 0.64, 0.82], marks=[0.7, 1.2, 1.7, 2.2, 2.7], stamp_at=3.3,
             badges=[dict(at=1.3, t="🛡 ANTIFUGAS", x=90, y=930, bg="#7c3aed"), dict(at=2.1, t="MP3 128 kbps", x=540, y=930, bg="#ff1f3a")],
             vo="Con el modo promo antifugas, nadie podrá mezclarla.", vo_at=0.2),
        # 8 · Todo en uno
        dict(type="words", dur=3.6, top=470, gap=0.5, vo="Con tu firma y carátula. En MP3, WAV o FLAC, y con vídeo.",
             lines=[dict(t="MP3 · WAV · FLAC", size=110), dict(t="VÍDEO 9:16 · 1:1", size=110), dict(t="TU FIRMA", size=150), dict(t="Y CARÁTULA", cls="red", size=170, big=True)]),
        # 9 · Marcar, generar y listo (el puntero hace clic y el programa cambia)
        dict(type="shot", dur=5.6, steps=3, logo=4.2,
             caps=[dict(at=0.15, until=2.0, num="05", title="Marca <em>lo que necesitas</em>", sub="MP3, WAV, FLAC y vídeo para redes", step=2),
                   dict(at=2.1, until=3.45, num="06", title="Un clic: <em>generar</em>", sub="Y AutoPrevias hace el resto", step=2),
                   dict(at=3.55, until=5.5, num="✓", title="<em>Lista</em> para subir", sub="La ves, la oyes y abres la carpeta", step=2)],
             imgs=[dict(at=0, name="03b_exportar"), dict(at=3.45, name="08_generada")],
             cam=[dict(at=0, d=0, c=[1500, 700], z=1.6), dict(at=3.5, d=0.7, c=[1350, 640], z=1.3)],
             cur=[dict(at=0.05, set=[1100, 880]), dict(at=0.4, d=0.8, to=[1230, 500]), dict(at=2.0, d=1.0, to=[1954, 1018]), dict(at=3.6, d=0.9, to=[1813, 357])],
             clicks=[dict(at=1.2, to=[1230, 500]), dict(at=3.35, to=[1954, 1018])],
             hls=[dict(at=0.3, hold=1.3, box=[1135, 410, 525, 235], pad=4), dict(at=3.3, hold=0.6, box=[1730, 990, 450, 56], pad=6),
                  dict(at=3.6, hold=1.6, box=[60, 335, 1990, 46], pad=4)],
             confetti=3.5, vo="Y ya está lista para subir.", vo_at=0.3),
        # 10 · Cierre
        dict(type="words", dur=2.8, bars=True, top=560, gap=0.45, vo="Tu previa, en treinta segundos.",
             lines=[dict(t="TU PREVIA", size=200), dict(t="EN 30", cls="red", size=330, big=True), dict(t="SEGUNDOS", size=170)]),
        dict(type="cta", dur=5.4, click_at=3.3, line1="Tu previa", line2="en 30 segundos.", vo="Autoprevias, de Radical Récords. Consíguelo en Peijip.", vo_at=0.8),
    ])
