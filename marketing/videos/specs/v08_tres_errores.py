"""Vídeo 8 · 3 errores que arruinan una previa (voz en castellano)."""
def tip(n, bad, fix):
    return dict(type="tips", dur=5.0, tips=[dict(n=n, top=560, at=0.2, fix_at=2.6, bad=bad, fix=fix)])

SPEC = dict(
    voice="em_alex", lang="es", speed=1.04, groove_from=3.0,
    scenes=[
        dict(type="words", dur=3.0, bars=True, top=470, gap=0.5, vo="Tres errores que arruinan tu previa.",
             lines=[dict(t="3 ERRORES", cls="red", size=230, big=True), dict(t="QUE ARRUINAN", size=150), dict(t="TU PREVIA", size=190)]),
        dict(type="tips", dur=7.0, vo="Uno: que dure tres minutos. Nadie la escucha. Usa quince, treinta o sesenta segundos.", vo_at=0.3,
             tips=[dict(n="1", top=540, at=0.2, fix_at=3.3, bad="Una previa de <span class='red'>3 minutos</span>. Nadie la escucha.", fix="Usa 15, 30 o 60 segundos")]),
        dict(type="tips", dur=7.0, vo="Dos: cortar en mitad de compás. Auto Previas corta siempre a tiempo.", vo_at=0.3,
             tips=[dict(n="2", top=540, at=0.2, fix_at=2.2, bad="Cortar <span class='red'>en mitad de compás</span>.", fix="Cortes siempre a tiempo, en compás")]),
        dict(type="tips", dur=7.0, vo="Tres: no poner tu nombre. Añade tu firma y tu carátula a cada previa.", vo_at=0.3,
             tips=[dict(n="3", top=540, at=0.2, fix_at=2.5, bad="<span class='red'>No poner tu nombre</span> en la previa.", fix="Tu firma y tu carátula en cada previa")]),
        dict(type="words", dur=3.6, top=520, gap=0.6, vo="Auto Previas lo hace bien por ti.",
             lines=[dict(t="LO HACE", size=200), dict(t="BIEN", cls="red", size=260, big=True), dict(t="POR TI", size=200)]),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Previas sin errores,", line2="en 30 segundos.", vo="Consíguelo en Pei jip.", vo_at=1.2),
    ])
