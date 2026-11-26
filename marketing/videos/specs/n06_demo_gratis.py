"""Vídeo nuevo 6 · «¿Una previa para tu Instagram GRATIS? Prueba AutoPrevias Demo» → Demo → Basic → Plus → cierre. Con voz (Ximena)."""
SPEC = dict(
    tall=True, lang="es",
    voice="edge:es-ES-XimenaNeural", speed=1.22, groove_from=2.4,
    scenes=[
        # 1 · Gancho
        dict(type="words", dur=3.0, bars=True, top=470, gap=0.42,
             vo="¿Quieres una previa para tu Instagram gratis?",
             lines=[dict(t="¿QUIERES UNA", size=160), dict(t="PREVIA PARA", size=160), dict(t="TU INSTAGRAM", size=150),
                    dict(t="GRATIS?", cls="red", size=300, big=True)]),
        # 2 · Giro
        dict(type="words", dur=2.8, bars=True, top=560, gap=0.5,
             vo="Pues prueba Autoprevias Demo.",
             lines=[dict(t="PRUEBA", size=190), dict(t="AUTOPREVIAS", size=170), dict(t="DEMO", cls="red", size=300, big=True)]),
        # 3 · Qué incluye la Demo
        dict(type="compare", dur=5.2, vo_at=0.3,
             vos=[dict(t="Siete días gratis.", at=0.3), dict(t="Arrastras tu tema y elige los mejores cortes."),
                  dict(t="Elige la plantilla: quince, treinta segundos, uno o dos minutos,"), dict(t="y lista para Instagram.")],
             panels=[dict(name="DEMO · GRATIS", cls="demo big", top=420, at=0.2, items_at=["v1+0.2", "v2", "v2+1.2", "v3", "v4"],
                          items=["7 días gratis", "Arrastras tu tema y listo", "Elige solo los mejores cortes",
                                 "15 s · 30 s · 1 min · 2 min", "Lista para subir a Instagram"])]),
        # 4 · ¿Quieres más?
        dict(type="words", dur=2.4, bars=True, top=640, gap=0.5, vo="¿Quieres más?",
             lines=[dict(t="¿QUIERES", size=200), dict(t="MÁS?", cls="red", size=300, big=True)]),
        # 5 · Basic
        dict(type="compare", dur=4.6, vo_at=0.3,
             vos=[dict(t="Basic: previa automática, cortes y efectos a mano,", at=0.3), dict(t="y vídeo con marca de agua.")],
             panels=[dict(name="BASIC", cls="basic big", top=420, at=0.2, items_at=["v1+0.2", "v1+1.3", "v1+2.3", "v2"],
                          items=["Previa automática", "Cortes y efectos a mano", "MP3 320 kbps", "Vídeo con marca de agua"])]),
        # 6 · Plus
        dict(type="compare", dur=5.6, vo_at=0.3,
             vos=[dict(t="Plus: todo lo de Basic, en wav y flac,", at=0.3), dict(t="vídeo sin marca de agua y con tu logo,"),
                  dict(t="y modo antifugas con tu voz.")],
             panels=[dict(name="PLUS", cls="plus big", top=340, at=0.2, items_at=["v1+0.2", "v1+1.2", "v2", "v2+1.0", "v3", "v3+0.9"],
                          items=["Todo lo de Basic", "WAV 24 bit y FLAC", "Vídeo sin marca de agua", "Tu propio logo en el vídeo",
                                 "Modo antifugas y tu voz", "Lote, presets y firma"])]),
        # 7 · Cierre de siempre
        dict(type="cta", dual=True, dur=5.4, click_at=3.6, line1="Tu previa en 30 segundos.", line2="",
             vo="Tu previa en treinta segundos. Consíguelo en Peijip.", vo_at=0.8),
    ])
