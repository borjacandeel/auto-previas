"""Presentación oficial 2 · «Si no quieres que pinchen tus temas gratis, hazles una previa» (CON voz, Ximena)."""
SPEC = dict(
    tall=True,
    voice="edge:es-ES-XimenaNeural", lang="es", speed=1.16, groove_from=2.6,
    scenes=[
        # 1 · Gancho
        dict(type="words", dur=2.8, bars=True, top=520, gap=0.42,
             lines=[dict(t="¿NO QUIERES", size=170), dict(t="QUE NADIE", size=170), dict(t="PINCHE TUS TEMAS", size=130), dict(t="GRATIS?", cls="red", size=300, big=True)],
             vo="¿No quieres que nadie pinche tus temas gratis?"),
        # 2 · El problema
        dict(type="words", dur=3.0, top=520, gap=0.5,
             lines=[dict(t="TU TEMA", size=190), dict(t="EN EL SET", size=190), dict(t="DE OTRO DJ", size=170), dict(t="SIN PAGAR", cls="red", size=230, big=True)],
             vo="Tu tema, en el set de otro DJ, sin pagar."),
        # 3 · Giro
        dict(type="words", dur=3.0, bars=True, top=560, gap=0.5,
             lines=[dict(t="HAZLES UNA", size=170), dict(t="PREVIA", cls="red", size=280, big=True), dict(t="CON", size=150), dict(t="AUTOPREVIAS", size=150)],
             vo="Hazles una previa con Autoprevias."),
        # 4 · Modo promo: el clic activa la tarjeta
        dict(type="shot", dur=4.6, steps=3, logo=3.6,
             caps=[dict(at=0.15, until=1.35, num="01", title="Activa <em>el modo promo</em>", sub="Un clic", step=0),
                   dict(at=1.45, until=4.5, num="02", title="Tu voz <em>cada ~20 s</em>", sub="Y MP3 a 128 kbps: no sirve para mezclar", step=0)],
             imgs=[dict(at=0, name="03b_exportar"), dict(at=1.35, name="07_promo")],
             cam=[dict(at=0, d=0, c=[1580, 640], z=1.7)],
             cur=[dict(at=0.05, set=[1100, 880]), dict(at=0.4, d=0.9, to=[1728, 509])],
             clicks=[dict(at=1.3, to=[1728, 509])],
             hls=[dict(at=0.3, hold=1.0, box=[1685, 409, 523, 238], pad=4), dict(at=1.45, hold=2.6, box=[1820, 570, 320, 40], pad=6)],
             vo="Activa el modo promo, y tu voz se repite cada veinte segundos.", vo_at=0.2),
        # 5 · Cómo queda en la onda
        dict(type="antileak", dur=4.4, title="ANTIFUGAS", mark_pos=[0.1, 0.28, 0.46, 0.64, 0.82], marks=[0.7, 1.2, 1.7, 2.2, 2.7], stamp_at=3.4,
             badges=[dict(at=1.3, t="🛡 TU VOZ", x=90, y=930, bg="#7c3aed"), dict(at=2.1, t="MP3 128 kbps", x=540, y=930, bg="#ff1f3a")],
             vo="Y la previa sale en eme pe tres a ciento veintiocho kilobits: no sirve para mezclar.", vo_at=0.2),
        # 6 · Tu firma de voz
        dict(type="shot", dur=4.0, steps=3, logo=3.0,
             caps=[dict(at=0.15, until=3.9, num="03", title="Tu <em>firma de voz</em>", sub="Un jingle tuyo, justo donde quieras", step=1)],
             imgs=[dict(at=0, name="07_promo")],
             cam=[dict(at=0, d=0, c=[1000, 970], z=2.0)],
             cur=[dict(at=0.05, set=[1500, 700]), dict(at=0.5, d=0.9, to=[813, 972])],
             clicks=[dict(at=1.5, to=[813, 972])],
             hls=[dict(at=0.4, hold=1.2, box=[700, 950, 230, 44], pad=4), dict(at=1.9, hold=1.8, box=[1130, 953, 230, 36], pad=6)],
             vo="Con tu firma de voz, justo donde quieras.", vo_at=0.2),
        # 7 · Firma y carátula
        dict(type="words", dur=3.0, top=520, gap=0.5,
             lines=[dict(t="TU NOMBRE", size=190), dict(t="TU CARÁTULA", size=170), dict(t="EN CADA", size=170), dict(t="ARCHIVO", cls="red", size=240, big=True)],
             vo="Tu nombre y tu carátula, en cada archivo."),
        # 8 · Generar y enviar
        dict(type="shot", dur=5.2, steps=3, logo=3.9,
             caps=[dict(at=0.15, until=3.1, num="04", title="Un clic: <em>generar</em>", sub="Y AutoPrevias hace el resto", step=2),
                   dict(at=3.2, until=5.1, num="✓", title="<em>Lista</em> para enviar", sub="Con tu voz repetida en toda la previa", step=2)],
             imgs=[dict(at=0, name="07_promo"), dict(at=3.2, name="08_generada")],
             cam=[dict(at=0, d=0, c=[1500, 800], z=1.6), dict(at=3.3, d=0.7, c=[1350, 640], z=1.3)],
             cur=[dict(at=0.05, set=[1000, 900]), dict(at=0.5, d=1.3, to=[1954, 1076]), dict(at=3.4, d=0.9, to=[1813, 357])],
             clicks=[dict(at=3.1, to=[1954, 1076])],
             hls=[dict(at=1.6, hold=1.5, box=[1730, 1048, 450, 56], pad=6), dict(at=3.4, hold=1.6, box=[60, 335, 1990, 46], pad=4)],
             confetti=3.3, vo="Un clic, y lista para enviar.", vo_at=0.3),
        # 9 · Cierre
        dict(type="words", dur=3.0, bars=True, top=560, gap=0.5,
             lines=[dict(t="ENVÍALA", size=210), dict(t="SIN MIEDO", cls="red", size=250, big=True)],
             vo="Envíala sin miedo."),
        dict(type="cta", dur=5.4, click_at=3.3, line1="Protege tus temas", line2="con AutoPrevias.", vo="Protege tus temas con Autoprevias, de Radical Récords. Consíguelo en Peijip.", vo_at=0.8),
    ])
