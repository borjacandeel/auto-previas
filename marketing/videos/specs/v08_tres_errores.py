"""Vídeo 8 · 3 errores que arruinan una previa (voz en castellano)."""
def L(t, px, cls="", color=""):
    """Línea grande dentro de la tarjeta de error (tamaño propio, mayúsculas)."""
    st = f"font-size:{px}px;line-height:1.02;text-transform:uppercase;letter-spacing:-1px" + (f";color:{color}" if color else "")
    return f"<span class='{cls}' style='{st}'>{t}</span>"


def sm(t):
    return f"<span style='font-size:52px;font-weight:700;color:#c9ccd8;line-height:1.2'>{t}</span>"


def fx(t):
    return f"<span style='font-size:62px;line-height:1.1'>{t}</span>"

SPEC = dict(
    voice="em_alex", lang="es", speed=1.04, groove_from=3.0,
    scenes=[
        dict(type="words", dur=3.0, bars=True, top=690, gap=0.5, vo="Tres errores que arruinan tu previa.",
             lines=[dict(t="3 ERRORES", cls="red", size=230, big=True), dict(t="QUE ARRUINAN", size=150), dict(t="TU PREVIA", size=190)]),
        dict(type="tips", dur=7.0, vo="Uno: que dure tres minutos. Nadie la escucha. Usa quince, treinta o sesenta segundos.", vo_at=0.3,
             tips=[dict(n="1", top=680, at=0.2, fix_at=3.3,
                        bad=L("Una previa de", 80) + "<br>" + L("3 minutos", 124, "red") + "<br>" + sm("Nadie la escucha."), fix=fx("Usa 15, 30 o 60 segundos"))]),
        dict(type="tips", dur=7.0, vo="Dos: cortar en mitad de compás. Auto Previas corta siempre a tiempo.", vo_at=0.3,
             tips=[dict(n="2", top=640, at=0.2, fix_at=2.2,
                        bad=L("Cortar en", 80) + "<br>" + L("mitad de", 124, "red") + "<br>" + L("compás", 124, "red"), fix=fx("Siempre a tiempo"))]),
        dict(type="tips", dur=7.0, vo="Tres: no poner tu nombre. Añade tu firma y tu carátula a cada previa.", vo_at=0.3,
             tips=[dict(n="3", top=680, at=0.2, fix_at=2.5,
                        bad=L("No poner", 80) + "<br>" + L("tu nombre", 124, "red") + "<br>" + sm("en la previa."), fix=fx("Tu firma y tu carátula en cada previa"))]),
        dict(type="words", dur=3.6, top=620, gap=0.6, vo="Auto Previas lo hace bien por ti.",
             lines=[dict(t="LO HACE", size=200), dict(t="BIEN", cls="red", size=260, big=True), dict(t="POR TI", size=200)]),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Previas sin errores,", line2="en 30 segundos.", vo="Consíguelo en Pei jip.", vo_at=1.2),
    ])
