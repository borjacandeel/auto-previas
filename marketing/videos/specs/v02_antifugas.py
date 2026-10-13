"""Vídeo 2 · Previa antifugas (voz en castellano)."""
SPEC = dict(
    voice="edge:es-ES-AlvaroNeural", lang="es", speed=1.10, groove_from=4.0,
    scenes=[
        dict(type="words", dur=4.0, bars=True, top=650, gap=0.6, vo="¿Te ha pasado? Mandas una previa… y a la semana ya circula sin tu nombre.",
             lines=[dict(t="TU PREVIA", size=170), dict(t="CIRCULA", cls="red", size=190, big=True), dict(t="SIN TU NOMBRE", size=140)]),
        dict(type="antileak", dur=6.0, title="MODO PROMO", mark_pos=[0.1, 0.28, 0.46, 0.64, 0.82], marks=[1.6, 2.4, 3.2, 4.0, 4.8],
             badges=[dict(at=2.0, t="🛡 ANTIFUGAS", x=90, y=930, bg="#7c3aed"), dict(at=3.0, t="MP3 128 kbps", x=540, y=930, bg="#ff1f3a")], stamp_at=5.2,
             vo="Con el modo promo de Autoprevias, tu firma de voz se repite sobre toda la previa."),
        dict(type="shot", dur=5.5, steps=2, logo=2.0,
             caps=[dict(at=0.2, until=5.4, num="🛡", title="Modo promo <em>antifugas</em>", sub="Tu firma cada pocos segundos · MP3 128k", step=0)],
             imgs=[dict(at=0, name="07_promo")],
             cam=[dict(at=0, d=0, c=[1500, 1400], z=1.15), dict(at=0.4, d=0.9, c=[1530, 1490], z=2.3)],
             cur=[dict(at=0.1, set=[1000, 1800]), dict(at=0.5, d=1.1, to=[1264, 1502])],
             clicks=[dict(at=1.8, to=[1264, 1502])], hls=[dict(at=1.75, hold=1.6, box=[1190, 1465, 560, 70], pad=6), dict(at=2.6, hold=1.8, box=[1480, 1465, 400, 70], pad=6)],
             vo="Sale en eme pe tres de ciento veintiocho kilobits, con la marca: promo, no distribuir."),
        dict(type="words", dur=3.6, top=700, gap=0.55, vo="Así, tu previa no sirve de nada sin ti.",
             lines=[dict(t="SIN TU FIRMA", size=150), dict(t="NO SIRVE", cls="red", size=200, big=True), dict(t="DE NADA", size=170)]),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Tu previa, siempre", line2="con tu firma.", vo="Autoprevias, de Radical Récords. Consíguelo en Peijip.", vo_at=1.2),
    ])
