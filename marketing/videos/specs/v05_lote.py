"""Vídeo 5 · 20 previas mientras tomas café (voz en castellano)."""
SPEC = dict(
    voice="em_alex", lang="es", speed=1.04, groove_from=3.4,
    scenes=[
        dict(type="words", dur=3.4, bars=True, top=640, gap=0.55, vo="Tienes veinte temas y un sello que mover.",
             lines=[dict(t="20 TEMAS", size=210), dict(t="1 SELLO", cls="red", size=210, big=True), dict(t="0 TIEMPO", size=190)]),
        dict(type="folder", dur=8.0, n=20, title="MODO LOTE", in_at=0.4, run_at=3.2, run_d=3.6,
             vo="Con el modo lote, los arrastras todos a la vez y se convierten en previas.", vo_at=0.4),
        dict(type="shot", dur=6.0, steps=2, logo=2.0,
             caps=[dict(at=0.2, until=5.9, num="📁", title="Modo <em>lote</em>", sub="Añade pistas o una carpeta entera y pulsa Iniciar", step=0)],
             imgs=[dict(at=0, name="14_lote")],
             cam=[dict(at=0, d=0, c=[760, 464], z=1.45), dict(at=0.7, d=0.9, c=[560, 464], z=2.0), dict(at=2.6, d=0.9, c=[960, 464], z=2.0)],
             cur=[dict(at=0.1, set=[760, 560]), dict(at=0.7, d=0.9, to=[333, 120]), dict(at=2.6, d=1.0, to=[1380, 875])],
             clicks=[dict(at=1.8, to=[333, 120]), dict(at=3.9, to=[1380, 875])],
             hls=[dict(at=1.75, hold=1.0, box=[231, 98, 204, 44], pad=6), dict(at=3.85, hold=1.6, box=[1267, 848, 224, 54], pad=6)],
             vo="Añade tus pistas, o una carpeta entera, pulsa iniciar lote, y la app trabaja sola."),
        dict(type="words", dur=3.4, top=640, gap=0.6, vo="Mientras tanto, tú te tomas el café.",
             lines=[dict(t="TÚ", size=190), dict(t="TE TOMAS", size=170), dict(t="EL CAFÉ ☕", cls="red", size=180, big=True)]),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Del sello al reel", line2="sin tocar el DAW.", vo="Auto Previas, de Radical Récords. Consíguelo en Pei jip.", vo_at=1.2),
    ])
