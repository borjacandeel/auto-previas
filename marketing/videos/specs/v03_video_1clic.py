"""Vídeo 3 · Tu vídeo animado en 1 clic (sin voz)."""
SPEC = dict(
    voice="em_alex", lang="es", groove_from=3.0,
    scenes=[
        dict(type="words", dur=3.4, bars=True, top=650, gap=0.5,
             lines=[dict(t="TU PREVIA", size=190), dict(t="YA VIENE", size=190), dict(t="CON VÍDEO", cls="red", size=200, big=True)]),
        dict(type="shot", dur=5.6, steps=3, logo=3.6,
             caps=[dict(at=0.2, until=2.8, num="01", title="Marca <em>vídeo animado</em>", sub="Un clic y se exporta con tu previa", step=0),
                   dict(at=2.9, until=5.5, num="02", title="Sale <em>con tu previa</em>", sub="Eliges formato y paleta de color", step=1)],
             imgs=[dict(at=0, name="07_promo")],
             cam=[dict(at=0, d=0, c=[1500, 1400], z=1.2), dict(at=0.4, d=0.9, c=[1700, 1444], z=2.2)],
             cur=[dict(at=0.1, set=[1000, 1800]), dict(at=0.5, d=1.2, to=[1812, 1444])],
             clicks=[dict(at=2.0, to=[1812, 1444])], hls=[dict(at=1.95, hold=2.4, box=[1790, 1420, 420, 54], pad=6)]),
        dict(type="cards", dur=6.4, title="3 formatos", title_top=1260, title_at=2.2, sub="TikTok · Reels · Shorts · YouTube", sub_at=2.7, sub_top=1470,
             cards=[dict(src="neon_916_crimson", x=285, y=150, w=560, h=996, at=0.2, rot=0), dict(src="neon_11", x=20, y=630, w=480, h=480, at=0.8, rot=-4, **{"from": "left"}),
                    dict(src="neon_169", x=560, y=720, w=500, h=281, at=1.4, rot=4, **{"from": "right"})],
             badges=[]),
        dict(type="cards", dur=6.2, title="Basic o Plus", title_top=1360, title_at=3.0, sub="Basic: con marca de agua · Plus: sin marca y final a elegir", sub_at=3.6, sub_top=1560,
             cards=[dict(src="neon_916_basic", x=50, y=160, w=470, h=836, at=0.2, rot=-3, **{"from": "left"}), dict(src="neon_916_crimson", x=560, y=160, w=470, h=836, at=0.8, rot=3, **{"from": "right"})],
             badges=[dict(at=1.6, t="BASIC · con marca", x=60, y=1060, bg="#2563eb"), dict(at=2.2, t="PLUS · sin marca", x=590, y=1060, bg="#7c3aed")]),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Sube tu previa", line2="con vídeo en 30 s."),
    ])
