"""Tutorial 1 · Cómo crear vídeos animados con AutoPrevias Plus, de cero, con ejemplos (16:9, voces Álvaro y Ximena).

Los tiempos son simbólicos: «vN» = inicio de la línea de voz N de la escena, «vNe» = su final, «vN+0.5» = medio segundo después.
Así la cámara, los resaltados y los rótulos siguen a la narración sin ajustar a mano.
"""
A = "edge:es-ES-AlvaroNeural"
X = "edge:es-ES-XimenaNeural"
ED = "tutorial"          # capturas reales en docs/manual/_work/tutorial
FW = 2240                # ancho de las capturas de la ventana principal


def demo(num, title, sub, frames, vos, pts=None, ex="EJEMPLO", pts_at=None, dur=6.0, voice=A, box=None):
    d = dict(type="demo", edition=ED, num=num, title=title, sub=sub, frames=frames, vos=vos, pts=pts or [], dur=dur, voice=voice)
    if pts_at:
        d["pts_at"] = pts_at
    if ex:
        d["ex"] = ex
    if box:
        d["box"] = box
    return d


SPEC = dict(
    format="16:9", voice=A, lang="es", speed=1.06, groove_from=3.0, seed=2027,
    scenes=[
        # ═══════════════ 0 · Portada ═══════════════
        dict(type="words", dur=4.0, bars=True, top=250, gap=0.6, sub="De cero a tu primer vídeo, con ejemplos", sub_at=2.4, sub_top=830,
             vos=[dict(t="Tutorial de Autoprevias Plus. Cómo crear tus vídeos animados, paso a paso, desde cero y con ejemplos.", at=0.4)],
             lines=[dict(t="TUTORIAL", size=210), dict(t="VÍDEOS ANIMADOS", cls="red", size=210, big=True)]),

        demo("00", "Lo que vas a <em>conseguir</em>", "Tu previa, convertida en un vídeo que late con tu música",
             frames=[dict(at="v1+0.2", src="tut_look_neon", label="Plantilla Neón · tu carátula late con el bombo", color="#ff6b81"),
                     dict(at="v2+0.2", src="tut_look_bars", label="Con tu propia foto de fondo", color="#c084fc"),
                     dict(at="v3+0.2", src="tut_look_circle", label="Con la onda de sonido que elijas", color="#22e07a")],
             pts=["Sin editor de vídeo", "Al ritmo de tu música", "En vertical, cuadrado o horizontal"], pts_at=["v1+0.8", "v2+0.8", "v3+0.8"],
             vos=[dict(t="Con Autoprevias Plus, tu previa se convierte en un vídeo animado que late al ritmo de tu música.", voice=A),
                  dict(t="Puedes usar tu propia foto como fondo, sin ningún editor de vídeo.", voice=X),
                  dict(t="Y elegir cómo se ve la onda de sonido, los textos y el final.", voice=A)]),

        # ═══════════════ 1 · Marcar el vídeo ═══════════════
        dict(type="shot", edition=ED, steps=4, logo=6.0, voice=A,
             vos=[dict(t="Paso uno. Carga tu tema y deja que la app lo analice. Después, en la fila de formatos, marca la casilla Vídeo animado.", voice=A),
                  dict(t="Al marcarla, aparece la tarjeta del vídeo con todas sus opciones.", voice=X, gap=0.5),
                  dict(t="Fíjate: el eme pe tres se exporta siempre, porque el vídeo se hace a partir de tu previa.", voice=A, gap=0.3)],
             caps=[dict(at=0.3, until="v1e+0.3", num="01", title="Marca <em>Vídeo animado</em>", sub="Casilla en la fila de formatos, junto a WAV, MP3 y FLAC", step=0),
                   dict(at="v2", until="v3e+0.3", num="01", title="Aparece la <em>tarjeta del vídeo</em>", sub="Todo el vídeo se configura en un solo sitio",
                        ex="El MP3 se exporta siempre: sin previa no hay vídeo.", step=0)],
             imgs=[dict(at=0, name="t01_sin_video"), dict(at="v1e-0.9", name="t02_video")],
             cam=[dict(at=0, d=0, c="sin_video.name", z=1.25), dict(at=0.6, d=1.0, c="sin_video.chk_video", z=1.9),
                  dict(at="v2", d=0.9, c="video.card", z=1.55)],
             cur=[dict(at=0.1, set="sin_video.name"), dict(at="v1+2.0", d=1.2, to="sin_video.chk_video")],
             clicks=[dict(at="v1e-1.0", to="sin_video.chk_video")],
             hls=[dict(at="v1e-1.05", hold=1.2, box="sin_video.chk_video", pad=8), dict(at="v2+0.2", hold=1.6, box="video.card", pad=10)],
             dur=8.0),

        # ═══════════════ 2 · Formato ═══════════════
        dict(type="shot", edition=ED, steps=4, logo=5.0, voice=A,
             vos=[dict(t="Paso dos. Elige el formato con estos tres botones.", voice=A),
                  dict(t="Vertical, nueve dieciséis, para TikTok, Reels y Shorts.", voice=X, gap=0.35),
                  dict(t="Cuadrado, uno a uno, para el feed de Instagram.", voice=A, gap=0.3),
                  dict(t="Y horizontal, dieciséis nueve, para YouTube.", voice=X, gap=0.3)],
             caps=[dict(at=0.2, until="v4e+0.3", num="02", title="Elige el <em>formato</em>", sub="Tres botones: vertical, cuadrado y horizontal",
                        ex="Un mismo vídeo en 9:16, 1:1 o 16:9 según la red.", step=1)],
             imgs=[dict(at=0, name="t02_video")],
             cam=[dict(at=0, d=0, c="video.card", z=1.5), dict(at=0.4, d=0.9, c="video.f11", z=2.1)],
             cur=[dict(at=0.1, set="video.card"), dict(at="v1+0.6", d=0.8, to="video.f916"), dict(at="v3", d=0.5, to="video.f11"), dict(at="v4", d=0.5, to="video.f169")],
             clicks=[dict(at="v2+0.3", to="video.f916"), dict(at="v3+0.3", to="video.f11"), dict(at="v4+0.3", to="video.f169")],
             hls=[dict(at="v2", hold=2.0, box="video.f916", pad=6), dict(at="v3", hold=2.0, box="video.f11", pad=6), dict(at="v4", hold=2.0, box="video.f169", pad=6)],
             dur=8.0),

        demo("02", "Un vídeo, <em>tres formatos</em>", "El mismo tema, con una foto distinta para cada formato",
             frames=[dict(at="v1+0.2", src="tut_fmt_916_foto", label="9:16 · TikTok · Reels · Shorts", color="#ff6b81"),
                     dict(at="v2+0.2", src="tut_fmt_11_foto", label="1:1 · Instagram y Facebook", color="#c084fc"),
                     dict(at="v3+0.2", src="tut_fmt_169_foto", label="16:9 · YouTube y pantallas", color="#22e07a")],
             pts=["Vertical para historias y Reels", "Cuadrado para el feed", "Horizontal para YouTube"], pts_at=["v1+0.8", "v2+0.8", "v3+0.8"],
             vos=[dict(t="Así queda el vídeo en vertical.", voice=X), dict(t="Así, en cuadrado.", voice=A), dict(t="Y así, en horizontal. Elige el que pida cada red.", voice=X)]),

        # ═══════════════ 3 · Color ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=X,
             vos=[dict(t="Paso tres. El menú de color cambia la paleta neón del vídeo.", voice=X)],
             caps=[dict(at=0.2, until="v1e+0.4", num="03", title="Elige el <em>color</em>", sub="Cinco paletas neón: la que mejor vaya con tu portada",
                        ex="Se aplica a las barras, los destellos y los detalles.", step=2)],
             imgs=[dict(at=0, name="t02_video")],
             cam=[dict(at=0, d=0, c="video.card", z=1.5), dict(at=0.4, d=0.9, c="video.pal", z=2.0)],
             cur=[dict(at=0.1, set="video.card"), dict(at=0.7, d=0.9, to="video.pal")],
             clicks=[dict(at="v1e-0.6", to="video.pal")],
             hls=[dict(at=1.2, hold=3.0, box="video.pal", pad=6)], dur=5.0),

        demo("03", "Cinco <em>paletas</em>", "Elige la que combine con tu portada",
             frames=[dict(at="v1+0.1", src="tut_pal_radical", label="Cian y Magenta Radical", color="#00e5ff"),
                     dict(at="v2+0.1", src="tut_pal_rave", label="Verde Neón Rave", color="#39ff14"),
                     dict(at="v3+0.1", src="tut_pal_crimson", label="Rojo Carmesí Studio", color="#ff1f3a"),
                     dict(at="v4+0.1", src="tut_pal_amber", label="Ámbar Gold y Solar", color="#ffb700"),
                     dict(at="v5+0.1", src="tut_pal_cyber", label="Cyber Violet", color="#b026ff")],
             vos=[dict(t="Cian y magenta.", voice=A), dict(t="Verde rave.", voice=X, gap=0.2), dict(t="Rojo carmesí.", voice=A, gap=0.2),
                  dict(t="Ámbar.", voice=X, gap=0.2), dict(t="Y cyber violeta.", voice=A, gap=0.2)]),

        # ═══════════════ 4 · Título ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=A,
             vos=[dict(t="Paso cuatro. En el campo Título escribes el nombre que verá la gente en el vídeo.", voice=A),
                  dict(t="Si lo dejas vacío, se usa el nombre de tu pista.", voice=X, gap=0.3)],
             caps=[dict(at=0.2, until="v2e+0.3", num="04", title="Pon tu <em>título</em>", sub="Es el nombre grande del centro del vídeo",
                        ex="Vacío = nombre de la pista, sin el «PREVIA - » del archivo.", step=2)],
             imgs=[dict(at=0, name="t02_video"), dict(at="v1+2.2", name="t02b_video_rellenado")],
             cam=[dict(at=0, d=0, c="video.card", z=1.5), dict(at=0.4, d=0.9, c="video.vtitle", z=2.0)],
             cur=[dict(at=0.1, set="video.card"), dict(at=0.6, d=1.0, to="video.vtitle")],
             clicks=[dict(at="v1+1.6", to="video.vtitle")],
             hls=[dict(at="v1+1.3", hold=2.2, box="video.vtitle", pad=6)], dur=7.0),

        demo("04", "Título: <em>pista o propio</em>", "Tu archivo se llama «Midnight Groove (Original Mix)»",
             frames=[dict(at="v1+0.1", src="tut_title_pista", label="Campo vacío → nombre de la pista", color="#ff6b81"),
                     dict(at="v2+0.1", src="tut_title_propio", label="Escribes «Midnight Groove» → ese es el título", color="#22e07a")],
             vos=[dict(t="Con el campo vacío, el vídeo muestra el nombre completo del archivo.", voice=X),
                  dict(t="Si escribes solo Midnight Groove, ese es el título que verá todo el mundo.", voice=A)]),

        # ═══════════════ 5 · Banner ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=X,
             vos=[dict(t="Paso cinco. En Plus puedes añadir un banner con el texto que quieras.", voice=X),
                  dict(t="Por ejemplo: Radical Récords, promo exclusiva.", voice=A, gap=0.3)],
             caps=[dict(at=0.2, until="v2e+0.3", num="05", title="Añade un <em>banner</em>", sub="Una franja de color con tu mensaje",
                        ex="Ideal para «PROMO EXCLUSIVA» o el nombre de tu sello.", step=3)],
             imgs=[dict(at=0, name="t02b_video_rellenado")],
             cam=[dict(at=0, d=0, c="video.card", z=1.5), dict(at=0.4, d=0.9, c="video.banner", z=2.0)],
             cur=[dict(at=0.1, set="video.card"), dict(at=0.6, d=1.0, to="video.banner")],
             clicks=[dict(at="v2", to="video.banner")],
             hls=[dict(at="v1+0.8", hold=3.0, box="video.banner", pad=6)], dur=7.0),

        demo("05", "El <em>banner</em>", "Texto propio sobre tu vídeo",
             frames=[dict(at="v1+0.1", src="tut_banner_off", label="Sin banner", color="#8a8fa3"),
                     dict(at="v2+0.1", src="tut_banner_on", label="Con banner: «RADICAL RECORDS · PROMO EXCLUSIVA»", color="#ff6b81")],
             vos=[dict(t="Así se ve sin banner.", voice=A), dict(t="Y así, con tu mensaje en una franja.", voice=X)]),

        # ═══════════════ 6 · Looks ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=A,
             vos=[dict(t="Paso seis. El selector Look te da cinco aspectos listos con un solo clic.", voice=A),
                  dict(t="Los de foto usan tu imagen: si aún no has elegido ninguna, la app te la pide.", voice=X, gap=0.3)],
             caps=[dict(at=0.2, until="v2e+0.3", num="06", title="Elige un <em>look</em>", sub="Cinco aspectos listos para usar",
                        ex="Neón clásico, foto + barras, foto + círculo, foto y título o solo la foto.", step=3)],
             imgs=[dict(at=0, name="t02_video"), dict(at="v1e+0.6", name="t03_foto")],
             cam=[dict(at=0, d=0, c="video.card", z=1.5), dict(at=0.4, d=0.9, c="video.look", z=2.0)],
             cur=[dict(at=0.1, set="video.card"), dict(at=0.6, d=1.0, to="video.look")],
             clicks=[dict(at="v1e-0.4", to="video.look")],
             hls=[dict(at="v1+0.9", hold=2.4, box="video.look", pad=6)], dur=8.0),

        demo("06", "Cinco <em>looks</em>", "Mismo tema, cinco aspectos distintos",
             frames=[dict(at="v1+0.1", src="tut_look_neon", label="Neón clásico · tu carátula late con el bombo", color="#ff6b81"),
                     dict(at="v2+0.1", src="tut_look_bars", label="Foto + barras abajo", color="#c084fc"),
                     dict(at="v3+0.1", src="tut_look_circle", label="Foto + círculo en el centro", color="#22e07a"),
                     dict(at="v4+0.1", src="tut_look_title", label="Foto y título, sin onda", color="#ffd21f"),
                     dict(at="v5+0.1", src="tut_look_photo", label="Solo la foto", color="#00e5ff")],
             vos=[dict(t="Neón clásico: tu carátula late con el bombo.", voice=X), dict(t="Foto más barras abajo.", voice=A, gap=0.2),
                  dict(t="Foto con un círculo en el centro.", voice=X, gap=0.2), dict(t="Foto y título, sin onda.", voice=A, gap=0.2),
                  dict(t="Y solo la foto, limpia, con el zoom lento.", voice=X, gap=0.2)]),

        # ═══════════════ 7 · Arrastrar imagen ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=A,
             vos=[dict(t="Paso siete. La forma más rápida de usar tu foto: arrástrala sobre la tarjeta del vídeo.", voice=A),
                  dict(t="Se usa de fondo al instante. Y si es dieciséis nueve, el vídeo cambia solo a ese formato.", voice=X, gap=0.3)],
             caps=[dict(at=0.2, until="v2e+0.3", num="07", title="<em>Arrastra</em> tu foto", sub="Suéltala sobre la tarjeta del vídeo",
                        ex="Imagen 16:9 → el vídeo pasa solo a 16:9 con el look «Foto + barras».", step=3)],
             imgs=[dict(at=0, name="t02_video"), dict(at="v2-0.2", name="t03_foto")],
             cam=[dict(at=0, d=0, c="video.card", z=1.35), dict(at="v2", d=0.9, c="video.card", z=1.7)],
             cur=[dict(at=0.1, set=[1400, 2150])],
             chip=dict(text="📄 foto_club.jpg", at="v1+1.4", **{"from": [1050, 2300]}, to="video.drop", d=1.5),
             clicks=[], hls=[dict(at="v2-0.3", hold=2.6, box="video.card", pad=10)], dur=9.0),

        # ═══════════════ 8 · Formato de la imagen ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=X,
             vos=[dict(t="Ojo con la proporción de tu imagen. Los vídeos son nueve dieciséis, uno a uno, o dieciséis nueve.", voice=X),
                  dict(t="Si eliges una imagen con otra proporción, por ejemplo cuatro tercios, Autoprevias te lo dice.", voice=A, gap=0.3),
                  dict(t="Aparece este aviso: el formato de la imagen no es correcto. Puedes cambiarla, ver ejemplos o usarla igualmente.", voice=X, gap=0.3),
                  dict(t="Los ejemplos te enseñan los tres formatos válidos y la medida ideal de cada uno.", voice=A, gap=0.3)],
             caps=[dict(at=0.2, until="v4e+0.3", num="08", title="El <em>formato</em> de la imagen", sub="9:16, 1:1 o 16:9: si no encaja, la app te avisa",
                        ex="Foto de 1600×1200 (4:3) → aviso; mejor recórtala a 16:9.", step=3)],
             imgs=[dict(at=0, name="t09_formato_mal"), dict(at="v3+0.2", name="t11_aviso_formato"), dict(at="v4", name="t10_formatos_validos")],
             cam=[dict(at=0, d=0, c=[688, 681], z=1.45), dict(at="v2+0.2", d=0.9, c="dlg_mal.bg11", z=2.2),
                  dict(at="v3+0.2", d=0.1, c=[345, 130], z=3.0), dict(at="v4", d=0.1, c=[410, 266], z=2.3)],
             cur=[dict(at=0.1, set="dlg_mal.bg11")],
             clicks=[], hls=[dict(at="v2+0.4", hold=3.4, box="dlg_mal.bg11", pad=10)], dur=9.0),

        demo("08", "Si no encaja: <em>recortar o desenfocar</em>", "Ejemplo: una foto 4:3 en un vídeo 16:9",
             frames=[dict(at="v1+0.1", src="tut_fit_crop", label="Recortar para rellenar la pantalla", color="#ff6b81"),
                     dict(at="v2+0.1", src="tut_fit_blur", label="Imagen entera con fondo desenfocado", color="#22e07a")],
             vos=[dict(t="Con recortar, la foto rellena toda la pantalla, y se pierden los bordes.", voice=A),
                  dict(t="Con imagen entera, se ve completa sobre un fondo desenfocado de la propia foto.", voice=X)]),

        # ═══════════════ 9 · Personalizar ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=A,
             vos=[dict(t="Paso ocho. Pulsa Personalizar para ajustarlo todo.", voice=A),
                  dict(t="Se abre esta ventana, con una vista previa en vivo a la derecha. Cada cambio se ve al instante.", voice=X, gap=0.3),
                  dict(t="Arriba eliges el fondo: la plantilla Neón, o tu imagen.", voice=A, gap=0.3),
                  dict(t="Puedes poner una foto distinta para cada formato, o una sola para todos.", voice=X, gap=0.3),
                  dict(t="Y decides si se recorta o se ve entera con fondo desenfocado.", voice=A, gap=0.3)],
             caps=[dict(at=0.2, until="v2e+0.2", num="08", title="<em>Personaliza</em> todo", sub="Botón «⚙ Personalizar…» en la tarjeta del vídeo",
                        ex="Vista previa en vivo: ves cada cambio al momento.", step=3),
                   dict(at="v3", until="v5e+0.3", num="08", title="Fondo e <em>imágenes</em>", sub="Una foto por formato o una sola para todos",
                        ex="Verás «✓ formato correcto» junto a cada imagen válida.", step=3)],
             imgs=[dict(at=0, name="t03_foto"), dict(at="v1e-0.4", name="t06_personalizar")],
             cam=[dict(at=0, d=0, c="video.card", z=1.5), dict(at="v1+0.3", d=0.9, c="video.custom", z=2.0),
                  dict(at="v1e", d=0.1, c=[688, 681], z=1.5), dict(at="v2+1.0", d=1.0, c="dlg_a.prev", z=2.0),
                  dict(at="v3", d=1.0, c="dlg_a.style", z=2.0), dict(at="v4", d=0.9, c="dlg_a.bg11", z=1.9), dict(at="v5", d=0.9, c="dlg_a.fit", z=2.1)],
             cur=[dict(at=0.1, set="video.card"), dict(at="v1+0.4", d=0.9, to="video.custom"), dict(at="v1e+0.4", d=0.1, to="dlg_a.style"),
                  dict(at="v4", d=0.8, to="dlg_a.bg11"), dict(at="v5", d=0.7, to="dlg_a.fit")],
             clicks=[dict(at="v1e-0.3", to="video.custom")],
             hls=[dict(at="v1+0.8", hold=1.8, box="video.custom", pad=8), dict(at="v2+1.1", hold=3.0, box="dlg_a.prev", pad=8),
                  dict(at="v3+0.3", hold=2.4, box="dlg_a.style", pad=8), dict(at="v4+0.2", hold=2.8, box="dlg_a.bg916", pad=6),
                  dict(at="v4+0.9", hold=2.0, box="dlg_a.bg11", pad=6), dict(at="v4+1.6", hold=2.0, box="dlg_a.bg169", pad=6),
                  dict(at="v5+0.3", hold=2.6, box="dlg_a.fit", pad=8)], dur=10.0),

        dict(type="shot", edition=ED, steps=4, voice=X,
             vos=[dict(t="Más abajo, la onda de sonido: puedes mostrarla u ocultarla.", voice=X),
                  dict(t="Eliges el estilo: barras, línea o círculo.", voice=A, gap=0.3),
                  dict(t="La posición: arriba, en el centro o abajo.", voice=X, gap=0.3),
                  dict(t="Y el color: los de la paleta neón, o blanco.", voice=A, gap=0.3)],
             caps=[dict(at=0.2, until="v4e+0.3", num="09", title="La <em>onda de sonido</em>", sub="Estilo, posición y color a tu gusto",
                        ex="Barras, línea o círculo · arriba, centro o abajo.", step=3)],
             imgs=[dict(at=0, name="t06_personalizar"), dict(at="v2+0.6", name="t07_personalizar_b")],
             cam=[dict(at=0, d=0, c=[688, 681], z=1.5), dict(at=0.6, d=1.0, c="dlg_a.wstyle", z=2.0), dict(at="v4", d=0.9, c="dlg_b.wcol", z=2.0)],
             cur=[dict(at=0.1, set="dlg_a.fit"), dict(at=0.6, d=0.8, to="dlg_a.wave"), dict(at="v2", d=0.7, to="dlg_a.wstyle"),
                  dict(at="v3", d=0.7, to="dlg_a.wpos"), dict(at="v4", d=0.7, to="dlg_a.wcol")],
             clicks=[dict(at="v2+0.5", to="dlg_a.wstyle")],
             hls=[dict(at="v1+0.3", hold=1.8, box="dlg_a.wave", pad=8), dict(at="v2+0.2", hold=2.0, box="dlg_a.wstyle", pad=8),
                  dict(at="v3+0.2", hold=2.0, box="dlg_a.wpos", pad=8), dict(at="v4+0.2", hold=2.0, box="dlg_a.wcol", pad=8)], dur=9.0),

        demo("09", "La onda: <em>estilo</em>", "Barras, línea o círculo",
             frames=[dict(at="v1+0.1", src="tut_wave_bars", label="Barras", color="#ff6b81"), dict(at="v2+0.1", src="tut_wave_line", label="Línea", color="#c084fc"),
                     dict(at="v3+0.1", src="tut_wave_circle", label="Círculo", color="#22e07a")],
             vos=[dict(t="Barras, el clásico.", voice=A), dict(t="Línea, más sutil.", voice=X, gap=0.2), dict(t="Y círculo, ideal con la foto centrada.", voice=A, gap=0.2)]),

        demo("09", "La onda: <em>posición y color</em>", "Arriba, centro, abajo · colores de la paleta o blanco",
             frames=[dict(at="v1+0.1", src="tut_wpos_top", label="Arriba (los textos pasan abajo)", color="#ff6b81"),
                     dict(at="v2+0.1", src="tut_wpos_center", label="En el centro", color="#c084fc"),
                     dict(at="v3+0.1", src="tut_wpos_bottom", label="Abajo", color="#22e07a"),
                     dict(at="v4+0.1", src="tut_wcol_white", label="En blanco", color="#ffffff")],
             vos=[dict(t="Arriba, y los textos bajan para no pisarse.", voice=X), dict(t="En el centro.", voice=A, gap=0.2), dict(t="O abajo.", voice=X, gap=0.2),
                  dict(t="Y si prefieres, la onda en blanco.", voice=A, gap=0.2)]),

        # ═══════════════ 10 · Textos ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=A,
             vos=[dict(t="Paso nueve. Los textos: marca solo los que quieras ver.", voice=A),
                  dict(t="Título de la pista, artista, bepeemes y tonalidad, y la etiqueta Previa exclusiva.", voice=X, gap=0.3),
                  dict(t="Elige también su posición: arriba, en el centro o abajo.", voice=A, gap=0.3),
                  dict(t="Y con Solo la foto, desaparecen los textos, la onda y el banner: se ve únicamente tu imagen.", voice=X, gap=0.3)],
             caps=[dict(at=0.2, until="v4e+0.3", num="10", title="Qué <em>textos</em> se ven", sub="Título, artista, BPM y tonalidad, etiqueta",
                        ex="«Solo la foto» deja la imagen limpia, con el zoom lento.", step=3)],
             imgs=[dict(at=0, name="t07_personalizar_b"), dict(at="v4+0.3", name="t08_personalizar_solofoto")],
             cam=[dict(at=0, d=0, c=[688, 681], z=1.5), dict(at=0.5, d=1.0, c="dlg_b.ctitle", z=2.0), dict(at="v3", d=0.8, c="dlg_b.tpos", z=2.0),
                  dict(at="v4", d=0.9, c="dlg_c.only", z=2.0)],
             cur=[dict(at=0.1, set="dlg_b.wcol"), dict(at=0.6, d=0.9, to="dlg_b.ctitle"), dict(at="v3", d=0.8, to="dlg_b.tpos"), dict(at="v4", d=0.7, to="dlg_c.only")],
             clicks=[dict(at="v4+0.4", to="dlg_c.only")],
             hls=[dict(at="v1+0.3", hold=1.8, box="dlg_b.ctitle", pad=8), dict(at="v2+0.2", hold=3.0, box="dlg_b.cartist", pad=8),
                  dict(at="v3+0.2", hold=2.0, box="dlg_b.tpos", pad=8), dict(at="v4+0.4", hold=2.6, box="dlg_c.only", pad=8)], dur=10.0),

        demo("10", "Textos: <em>tú decides</em>", "Desde todos los datos hasta solo la foto",
             frames=[dict(at="v1+0.1", src="tut_txt_todos", label="Todos los textos y el banner", color="#ff6b81"),
                     dict(at="v2+0.1", src="tut_txt_titulo", label="Solo el título", color="#c084fc"),
                     dict(at="v3+0.1", src="tut_txt_ninguno", label="Sin textos, con la onda", color="#22e07a"),
                     dict(at="v4+0.1", src="tut_txt_solofoto", label="Solo la foto", color="#00e5ff")],
             vos=[dict(t="Con todos los textos y el banner.", voice=A), dict(t="Solo el título.", voice=X, gap=0.2), dict(t="Sin textos, pero con la onda.", voice=A, gap=0.2),
                  dict(t="O solo la foto, para un vídeo limpio.", voice=X, gap=0.2)]),

        # ═══════════════ 11 · Final ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=A,
             vos=[dict(t="Paso diez. El final del vídeo. Lo eliges en este selector.", voice=A),
                  dict(t="Y si quieres terminar con tu propia imagen, por ejemplo el cartel de tu sello, la eliges en Personalizar, con un texto opcional debajo.", voice=X, gap=0.3)],
             caps=[dict(at=0.2, until="v2e+0.3", num="11", title="Cómo <em>termina</em> el vídeo", sub="Selector «Final» en la tarjeta del vídeo",
                        ex="Firma Autoprevias, fundido a negro, sin cierre o tu imagen.", step=3)],
             imgs=[dict(at=0, name="t03_foto"), dict(at="v1e+0.4", name="t06_personalizar")],
             cam=[dict(at=0, d=0, c="video.card", z=1.5), dict(at=0.5, d=1.0, c="video.final", z=2.0), dict(at="v2", d=0.1, c=[688, 681], z=1.5),
                  dict(at="v2+0.8", d=1.0, c="dlg_a.endimg", z=2.0)],
             cur=[dict(at=0.1, set="video.card"), dict(at=0.6, d=1.0, to="video.final"), dict(at="v2+0.2", d=0.6, to="dlg_a.endimg")],
             clicks=[dict(at="v1+1.4", to="video.final")],
             hls=[dict(at="v1+1.0", hold=2.2, box="video.final", pad=6), dict(at="v2+1.0", hold=3.2, box="dlg_a.endimg", pad=8), dict(at="v2+1.6", hold=2.6, box="dlg_a.endtxt", pad=8)],
             dur=9.0),

        demo("11", "Cuatro <em>finales</em>", "Cómo se cierra tu vídeo",
             frames=[dict(at="v1+0.1", src="tut_end_brand", label="Firma Autoprevias + enlace", color="#ff6b81"),
                     dict(at="v2+0.1", src="tut_end_fade", label="Fundido a negro", color="#c084fc"),
                     dict(at="v3+0.1", src="tut_end_none", label="Sin cierre: corte seco", color="#22e07a"),
                     dict(at="v4+0.1", src="tut_end_image", label="Tu imagen, con texto opcional", color="#ffd21f")],
             vos=[dict(t="Con la firma de Autoprevias y el enlace.", voice=X), dict(t="Con un fundido a negro.", voice=A, gap=0.2),
                  dict(t="Sin cierre, corte seco al terminar el audio.", voice=X, gap=0.2), dict(t="O con tu propia imagen, como el cartel de tu lanzamiento.", voice=A, gap=0.2)]),

        # ═══════════════ 12 · Vista previa y resumen ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=X,
             vos=[dict(t="Antes de generar, comprueba el resultado con Vista previa.", voice=X),
                  dict(t="Te enseña unos segundos del vídeo, con sonido, con tu título, tu color, tu formato y tu banner.", voice=A, gap=0.3),
                  dict(t="Y justo encima del botón, una línea de resumen te dice qué se va a crear: formatos, vídeo, duración y carpeta.", voice=X, gap=0.3)],
             caps=[dict(at=0.2, until="v3e+0.3", num="12", title="<em>Comprueba</em> antes de generar", sub="Vista previa con sonido y línea de resumen",
                        ex="El resumen te avisa si algo no es lo que esperabas.", step=3)],
             imgs=[dict(at=0, name="t03_foto"), dict(at="v1+1.3", name="t12_vista_previa"), dict(at="v3-0.3", name="t03_foto")],
             cam=[dict(at=0, d=0, c="video_foto.card", z=1.45), dict(at=0.5, d=0.9, c="video_foto.prev", z=2.1),
                  dict(at="v1+1.3", d=0.1, c="vista_previa.video", z=1.5), dict(at="v3-0.3", d=0.1, c="video_foto.summary", z=1.7)],
             cur=[dict(at=0.1, set="video_foto.card"), dict(at=0.6, d=0.9, to="video_foto.prev"), dict(at="v3", d=0.9, to="video_foto.summary")],
             clicks=[dict(at="v1+0.9", to="video_foto.prev")],
             hls=[dict(at="v1+0.5", hold=1.6, box="video_foto.prev", pad=8), dict(at="v3+0.3", hold=3.6, box="video_foto.summary", pad=10)], dur=11.0),

        # ═══════════════ 13 · Generar ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=A, confetti="v2+0.2",
             vos=[dict(t="Y ahora sí: pulsa Generar previa.", voice=A),
                  dict(t="Autoprevias crea tu previa y, a la vez, el vídeo animado. Las dos cosas, en la misma carpeta.", voice=X, gap=0.5),
                  dict(t="Súbelo tal cual a TikTok, a Reels, a Shorts o a YouTube.", voice=A, gap=0.3)],
             caps=[dict(at=0.2, until="v3e+0.3", num="13", title="<em>Genera</em> y publica", sub="Previa y vídeo, listos en tu carpeta",
                        ex="En el lote, el mismo vídeo para todas tus pistas.", step=3)],
             imgs=[dict(at=0, name="t03_foto"), dict(at="v1e+0.2", name="t13_generada")],
             cam=[dict(at=0, d=0, c="video_foto.generate", z=1.5), dict(at="v2", d=0.9, c="generada.success", z=1.6)],
             cur=[dict(at=0.1, set="video_foto.summary"), dict(at="v1-0.2", d=0.8, to="video_foto.generate")],
             clicks=[dict(at="v1e-0.4", to="video_foto.generate")],
             hls=[dict(at="v1e-0.45", hold=1.0, box="video_foto.generate", pad=8), dict(at="v2+0.4", hold=3.6, box="generada.success", pad=10)], dur=11.0),

        # ═══════════════ 14 · Avanzadas, presets, lote ═══════════════
        dict(type="shot", edition=ED, steps=4, voice=X,
             vos=[dict(t="Un último apartado: Opciones avanzadas. Esta sección viene plegada para que el panel quede limpio.", voice=X),
                  dict(t="Dentro están los efectos de estudio, el Vois Drop, el modo promo antifugas y tu firma y carátula.", voice=A, gap=0.3),
                  dict(t="Se abre sola en cuanto activas algo de ella.", voice=X, gap=0.3)],
             caps=[dict(at=0.2, until="v3e+0.3", num="14", title="Opciones <em>avanzadas</em>", sub="Efectos, Voice Drop, modo promo y firma",
                        ex="Plegadas por defecto; se abren solas al activarlas.", step=3)],
             imgs=[dict(at=0, name="t03_foto"), dict(at="v1+1.2", name="t04_avanzadas")],
             cam=[dict(at=0, d=0, c="video_foto.adv", z=1.6), dict(at="v1+1.2", d=0.1, c="avanzadas.adv", z=1.35), dict(at="v2", d=1.0, c="avanzadas.fx", z=1.9)],
             cur=[dict(at=0.1, set="video_foto.summary"), dict(at=0.5, d=0.9, to="video_foto.adv")],
             clicks=[dict(at="v1+0.9", to="video_foto.adv")],
             hls=[dict(at="v1+0.5", hold=1.4, box="video_foto.adv", pad=8), dict(at="v2+0.2", hold=3.2, box="avanzadas.fx", pad=8), dict(at="v2+1.0", hold=2.4, box="avanzadas.branding", pad=8)],
             dur=11.0),

        dict(type="shot", edition=ED, steps=4, voice=A,
             vos=[dict(t="Cuando tengas el estilo que te gusta, guárdalo como preset con el botón Guardar.", voice=A),
                  dict(t="El preset recuerda también tu vídeo: formato, color, look, imagen, onda y final.", voice=X, gap=0.3),
                  dict(t="La próxima vez, lo aplicas con un clic. Y en el modo lote, usas el mismo estilo con todas tus pistas.", voice=A, gap=0.3)],
             caps=[dict(at=0.2, until="v3e+0.3", num="15", title="Guarda tu <em>estilo</em>", sub="Presets: tu vídeo siempre igual, con un clic",
                        ex="Un preset por sello, por artista o por red social.", step=3)],
             imgs=[dict(at=0, name="t05_presets")],
             cam=[dict(at=0, d=0, c="presets.bar", z=1.4), dict(at=0.6, d=1.0, c="presets.save", z=2.2)],
             cur=[dict(at=0.1, set="presets.bar"), dict(at=0.6, d=1.0, to="presets.save")],
             clicks=[dict(at="v1+2.2", to="presets.save")],
             hls=[dict(at="v1+1.8", hold=2.0, box="presets.save", pad=8), dict(at="v2+0.6", hold=2.4, box="presets.combo", pad=8), dict(at="v2+1.4", hold=2.0, box="presets.apply", pad=8)],
             dur=10.0),

        # ═══════════════ 15 · Rendimiento ═══════════════
        dict(type="shot", edition="plus", steps=4, voice=X,
             vos=[dict(t="Y si quieres que todo vaya más rápido, o gastar menos recursos, abre Licencia y mira el ajuste Rendimiento.", voice=X),
                  dict(t="Automático se adapta a tu equipo. Ahorro usa poco, y Máximo usa todos los núcleos para terminar antes.", voice=A, gap=0.3)],
             caps=[dict(at=0.2, until="v2e+0.3", num="16", title="Ajusta el <em>rendimiento</em>", sub="⚙ Licencia → Rendimiento",
                        ex="Automático, ahorro de recursos o máximo rendimiento.", step=3)],
             imgs=[dict(at=0, name="11_licencia")],
             cam=[dict(at=0, d=0, c=[400, 372], z=2.1)],
             cur=[dict(at=0.1, set=[250, 520]), dict(at="v1+2.2", d=0.8, to=[640, 418])],
             clicks=[dict(at="v2", to=[640, 418])], hls=[dict(at="v1+2.0", hold=4.0, box=[30, 388, 740, 100], pad=4)], dur=9.0),

        # ═══════════════ cierre ═══════════════
        dict(type="recap", edition=ED, head="RESUMEN", head_size=150, voice=A, vos=[
            dict(t="En resumen: marca el vídeo, elige formato, color y título. Escoge un look o arrastra tu foto.", voice=A, at=0.5),
            dict(t="Personaliza la onda, los textos y el final, comprueba la vista previa, y genera.", voice=X, gap=0.3),
            dict(t="Así de fácil. Y ahora, ya sabes usar todo.", voice=A, gap=0.3)],
             items=["Marca «Vídeo animado»", "Formato: 9:16, 1:1 o 16:9", "Color, título y banner", "Look de un clic o tu foto",
                    "Onda: estilo, posición, color", "Textos y «solo la foto»", "Final: firma, negro, corte o tu imagen", "Vista previa y resumen",
                    "Presets y lote: tu estilo siempre igual", "Rendimiento a tu medida"],
             items_at=["v1+0.2", "v1+1.6", "v1+3.0", "v1+4.4", "v2+0.2", "v2+1.4", "v2+2.6", "v2+4.0", "v3+0.0", "v3+1.2"], dur=14.0),

        dict(type="cta", dual=True, dur=8.0, click_at=5.0, line1="Crea tus vídeos animados", line2="con AutoPrevias Plus.",
             vos=[dict(t="Autoprevias, de Radical Récords. Consíguelo en Peijip.", voice=X, at=1.2)]),
    ])
