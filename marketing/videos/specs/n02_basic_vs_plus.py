"""Vídeo nuevo 2 · «Basic vs Plus: ¿cuál es para ti?». Con voz (Ximena)."""
SPEC = dict(
    tall=True,
    voice="edge:es-ES-XimenaNeural", lang="es", speed=1.12, groove_from=2.4,
    scenes=[
        dict(type="words", dur=2.6, bars=True, top=600, gap=0.5, vo="¿Basic o Plus? Te lo cuento rápido.",
             lines=[dict(t="¿BASIC", size=250), dict(t="O PLUS?", cls="red", size=250, big=True)]),
        dict(type="compare", dur=5.0, vo_at=0.3,
             vos=[dict(t="Basic: previa automática.", at=0.3), dict(t="Cortes y efectos, a mano."), dict(t="Eme pe tres de trescientos veinte."), dict(t="Y vídeo con marca de agua.")],
             panels=[dict(name="BASIC", cls="basic big", top=420, at=0.2, items_at=["v1+0.2", "v2", "v3", "v4"],
             items=["Previa automática", "Cortes y efectos a mano", "MP3 320 kbps", "Vídeo con marca de agua"])]),
        dict(type="compare", dur=6.6, vo_at=0.3,
             vos=[dict(t="Plus: todo lo de Basic.", at=0.3), dict(t="Wav de veinticuatro bits y flac."), dict(t="Vídeo sin marca de agua."),
                  dict(t="Tu propio logo en el vídeo."), dict(t="Modo antifugas, con tu voz."), dict(t="Lote, ajustes guardados y firma de temas.")],
             panels=[dict(name="PLUS", cls="plus big", top=340, at=0.2, items_at=["v1+0.2", "v2", "v3", "v4", "v5", "v6"],
             items=["Todo lo de Basic", "WAV 24 bit y FLAC", "Vídeo sin marca de agua", "Tu propio logo en el vídeo", "Modo antifugas y tu voz", "Lote, presets y firma"])]),
        dict(type="words", dur=3.6, bars=True, top=420, gap=0.55,
             vos=[dict(t="Basic, para empezar.", at=0.2), dict(t="Plus, para sacarle todo el partido.")],
             at=[0.15, "v1+0.35", "v2", "v2+0.5"],
             lines=[dict(t="BASIC", size=220), dict(t="PARA EMPEZAR", size=120), dict(t="PLUS", cls="red", size=220, big=True), dict(t="PARA TODO", cls="red", size=120)]),
        dict(type="cta", dual=True, dur=5.6, click_at=4.0, line1="Elige la tuya.", line2="", vo="Elige la tuya en Peijip.", vo_at=1.0),
    ])
