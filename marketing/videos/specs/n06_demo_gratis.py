"""Vídeo nuevo 6 · «¿Una previa para tu Instagram GRATIS? Prueba AutoPrevias Demo» → Demo → Basic → Plus → cierre. Sin voz."""
SPEC = dict(
    tall=True, lang="es",
    groove_from=2.4,
    scenes=[
        # 1 · Gancho
        dict(type="words", dur=3.0, bars=True, top=470, gap=0.42,
             lines=[dict(t="¿QUIERES UNA", size=160), dict(t="PREVIA PARA", size=160), dict(t="TU INSTAGRAM", size=150),
                    dict(t="GRATIS?", cls="red", size=300, big=True)]),
        # 2 · Giro
        dict(type="words", dur=2.8, bars=True, top=560, gap=0.5,
             lines=[dict(t="PRUEBA", size=190), dict(t="AUTOPREVIAS", size=170), dict(t="DEMO", cls="red", size=300, big=True)]),
        # 3 · Qué incluye la Demo
        dict(type="compare", dur=5.2,
             panels=[dict(name="DEMO · GRATIS", cls="demo big", top=420, at=0.2, items_at=[0.8, 1.5, 2.2, 2.9, 3.6],
                          items=["7 días gratis", "Arrastras tu tema y listo", "Elige solo los mejores cortes", "Previa de 60 s en MP3",
                                 "Lista para subir a Instagram"])]),
        # 4 · ¿Quieres más?
        dict(type="words", dur=2.4, bars=True, top=640, gap=0.5,
             lines=[dict(t="¿QUIERES", size=200), dict(t="MÁS?", cls="red", size=300, big=True)]),
        # 5 · Basic
        dict(type="compare", dur=4.6,
             panels=[dict(name="BASIC", cls="basic big", top=420, at=0.2, items_at=[0.8, 1.4, 2.0, 2.6],
                          items=["Previa automática", "Cortes y efectos a mano", "MP3 320 kbps", "Vídeo con marca de agua"])]),
        # 6 · Plus
        dict(type="compare", dur=5.6,
             panels=[dict(name="PLUS", cls="plus big", top=340, at=0.2, items_at=[0.8, 1.4, 2.0, 2.6, 3.2, 3.8],
                          items=["Todo lo de Basic", "WAV 24 bit y FLAC", "Vídeo sin marca de agua", "Tu propio logo en el vídeo",
                                 "Modo antifugas y tu voz", "Lote, presets y firma"])]),
        # 7 · Cierre de siempre
        dict(type="cta", dual=True, dur=5.4, click_at=3.6, line1="Tu previa en 30 segundos.", line2=""),
    ])
