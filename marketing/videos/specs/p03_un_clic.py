"""Presentación oficial 3 · «Todo en un clic» (sin voz)."""
SPEC = dict(
    tall=True,
    voice="edge:es-ES-AlvaroNeural", lang="es", speed=1.16, groove_from=2.6,
    scenes=[
        # 1 · Gancho
        dict(type="words", dur=2.8, bars=True, top=540, gap=0.42,
             lines=[dict(t="ARRASTRAS", size=180), dict(t="UN TEMA", size=200), dict(t="Y SALE", size=200), dict(t="TODO", cls="red", size=330, big=True)]),
        # 2 · Arrastras el tema
        dict(type="shot", dur=3.8, steps=3, logo=2.8,
             caps=[dict(at=0.15, until=1.9, num="01", title="Arrastra <em>tu tema</em>", sub="Y ya está", step=0),
                   dict(at=1.9, until=3.7, num="02", title="Cortes <em>listos</em>", sub="Elige solo los mejores momentos", step=1)],
             imgs=[dict(at=0, name="01_bienvenida"), dict(at=1.9, name="03_cargada")],
             cam=[dict(at=0, d=0, c=[1120, 700], z=1.7), dict(at=1.9, d=0.8, c="loaded.waveform", z=1.8)],
             cur=[dict(at=0.05, set="welcome.drop"), dict(at=0.3, d=0.8, to="welcome.open_btn"), dict(at=2.1, d=0.9, to="loaded.waveform")],
             clicks=[dict(at=1.3, to="welcome.open_btn")], hls=[dict(at=1.25, hold=0.6, box="welcome.open_btn", pad=6), dict(at=2.1, hold=1.7, box="loaded.waveform", pad=4)]),
        # 3 · Un clic: generar
        dict(type="shot", dur=5.0, steps=3, logo=3.8,
             caps=[dict(at=0.15, until=2.9, num="03", title="Marca <em>lo que quieras</em>", sub="MP3, WAV, FLAC y vídeo", step=2),
                   dict(at=3.0, until=4.9, num="✓", title="Un clic y <em>sale todo</em>", sub="La previa ya está lista", step=2)],
             imgs=[dict(at=0, name="03b_exportar"), dict(at=3.0, name="08_generada")],
             cam=[dict(at=0, d=0, c=[1500, 700], z=1.6), dict(at=3.1, d=0.7, c=[1350, 640], z=1.3)],
             cur=[dict(at=0.05, set=[1100, 880]), dict(at=0.4, d=0.8, to=[1230, 500]), dict(at=1.6, d=1.0, to=[1954, 1018]), dict(at=3.2, d=0.9, to=[1813, 357])],
             clicks=[dict(at=2.9, to=[1954, 1018])],
             hls=[dict(at=0.3, hold=1.3, box=[1135, 410, 525, 235], pad=4), dict(at=2.85, hold=0.6, box=[1730, 990, 450, 56], pad=6), dict(at=3.2, hold=1.6, box=[60, 335, 1990, 46], pad=4)],
             confetti=3.1),
        # 4 · Lo que sale
        dict(type="words", dur=3.2, top=470, gap=0.5,
             lines=[dict(t="WAV · MP3 · FLAC", size=110), dict(t="VÍDEO EN 3 FORMATOS", size=96), dict(t="TU FIRMA", size=150), dict(t="Y CARÁTULA", cls="red", size=170, big=True)]),
        dict(type="cards", dur=3.6, title="Vídeo animado", title_top=1290, title_at=1.2, sub="TikTok · Reels · Shorts · YouTube", sub_at=1.6, sub_top=1500,
             cards=[dict(src="neon_916_crimson", x=285, y=140, w=560, h=996, at=0.15, rot=0), dict(src="neon_11", x=20, y=630, w=480, h=480, at=0.6, rot=-4, **{"from": "left"}),
                    dict(src="neon_169", x=560, y=720, w=500, h=281, at=1.0, rot=4, **{"from": "right"})],
             badges=[]),
        # 5 · Destellos: efectos arrastrables
        dict(type="shot", dur=4.4, steps=3, logo=3.4,
             caps=[dict(at=0.15, until=2.2, num="04", title="Arrastra <em>los efectos</em>", sub="Flanger y Filter Sweep sobre la onda", step=1),
                   dict(at=2.3, until=4.3, num="05", title="Tú decides <em>dónde</em>", sub="Y los escuchas antes de generar", step=1)],
             imgs=[dict(at=0, name="p_estudio_0"), dict(at=1.5, name="p_estudio_1"), dict(at=3.4, name="p_estudio_2")],
             cam=[dict(at=0, d=0, c=[700, 790], z=2.0), dict(at=1.8, d=0.8, c=[1180, 790], z=1.7)],
             cur=[dict(at=0.05, set=[417, 815]), dict(at=0.4, d=0.9, to=[946, 752]), dict(at=1.9, d=0.5, to=[589, 815]), dict(at=2.5, d=0.8, to=[1779, 752])],
             clicks=[dict(at=1.45, to=[946, 752]), dict(at=2.4, to=[589, 815]), dict(at=3.35, to=[1779, 752])],
             hls=[dict(at=0.25, hold=0.9, box=[359, 786, 125, 52], pad=4), dict(at=1.4, hold=0.9, box=[895, 722, 100, 56], pad=6),
                  dict(at=2.35, hold=0.8, box=[497, 786, 183, 52], pad=4), dict(at=3.3, hold=1.0, box=[1725, 722, 110, 56], pad=6)]),
        # 6 · Temas de color
        dict(type="shot", dur=4.6, steps=3, logo=3.6,
             caps=[dict(at=0.15, until=1.5, num="06", title="Tema <em>Original</em>", sub="Elige tu tema de color", step=1),
                   dict(at=1.6, until=3.0, num="06", title="Tema <em>One Dark</em>", sub="Elige tu tema de color", step=1),
                   dict(at=3.1, until=4.5, num="06", title="Tema <em>Claro</em>", sub="Elige tu tema de color", step=1)],
             imgs=[dict(at=0, name="p_estudio_2"), dict(at=1.6, name="p_tema_onedark"), dict(at=3.1, name="p_tema_light")],
             cam=[dict(at=0, d=0, c=[1500, 700], z=1.4)],
             cur=[dict(at=0.05, set=[2000, 300]), dict(at=0.5, d=0.9, to=[1716, 71])],
             clicks=[dict(at=1.5, to=[1716, 71]), dict(at=3.0, to=[1716, 71])],
             hls=[dict(at=1.45, hold=0.6, box=[1690, 50, 52, 44], pad=6), dict(at=2.95, hold=0.6, box=[1690, 50, 52, 44], pad=6)]),
        # 7 · Cierre
        dict(type="words", dur=3.0, bars=True, top=560, gap=0.5,
             lines=[dict(t="BASIC", size=200), dict(t="O PLUS", cls="red", size=260, big=True), dict(t="ELIGE", size=170), dict(t="TU EDICIÓN", size=170)]),
        dict(type="cta", dur=5.4, click_at=3.3, line1="Todo en un clic.", line2="Elige tu edición.", dual=True),
    ])
