"""Vídeo 9 · Tu estilo en 1 clic (sin voz)."""
SPEC = dict(
    voice="em_alex", lang="es", groove_from=3.2,
    scenes=[
        dict(type="words", dur=3.2, bars=True, top=470, gap=0.5,
             lines=[dict(t="TU FIRMA", size=200), dict(t="TU ESTILO", size=200), dict(t="1 CLIC", cls="red", size=260, big=True)]),
        dict(type="shot", dur=6.0, steps=2, logo=2.0,
             caps=[dict(at=0.2, until=5.9, num="💾", title="Presets <em>propios</em>", sub="Artista, sello, carátula, formatos y vídeo", step=0)],
             imgs=[dict(at=0, name="07_promo")],
             cam=[dict(at=0, d=0, c=[1500, 1100], z=1.2), dict(at=0.5, d=0.9, c="promo.preset_bar", z=2.2)],
             cur=[dict(at=0.1, set=[1200, 1500]), dict(at=0.6, d=1.2, to=[1760, 1114])],
             clicks=[dict(at=2.2, to=[1760, 1114])], hls=[dict(at=2.15, hold=1.8, box="promo.preset_bar", pad=8)]),
        dict(type="shot", dur=5.6, steps=2, logo=2.0,
             caps=[dict(at=0.2, until=5.5, num="↺", title="Reabre <em>cualquier previa</em>", sub="Mismos ajustes, misma seed", step=1)],
             imgs=[dict(at=0, name="13_recientes")],
             cam=[dict(at=0, d=0, c=[656, 416], z=1.5), dict(at=1.0, d=1.0, c=[656, 480], z=1.7)],
             cur=[dict(at=0.1, set=[300, 200]), dict(at=1.0, d=1.2, to=[780, 700])],
             clicks=[dict(at=2.4, to=[780, 700])], hls=[dict(at=2.35, hold=1.6, box=[60, 130, 1200, 600], pad=0)]),
        dict(type="words", dur=3.4, top=520, gap=0.6,
             lines=[dict(t="TU IDENTIDAD", size=170), dict(t="SIEMPRE", size=200), dict(t="IGUAL", cls="red", size=240, big=True)]),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Tu estilo,", line2="en cada previa."),
    ])
