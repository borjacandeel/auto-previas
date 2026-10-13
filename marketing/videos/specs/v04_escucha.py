"""Vídeo 4 · La app que escucha tu tema (voz en castellano)."""
SPEC = dict(
    voice="em_alex", lang="es", speed=1.04, groove_from=3.4,
    scenes=[
        dict(type="words", dur=3.4, bars=True, top=650, gap=0.6, vo="Auto Previas escucha tu tema como lo haría un productor.",
             lines=[dict(t="ELLA", size=200), dict(t="ESCUCHA", cls="red", size=200, big=True), dict(t="TU TEMA", size=190)]),
        dict(type="scan", dur=7.0, title="DETECTA", sweep_at=0.9, sweep_d=3.6,
             secs=[dict(name="INTRO", color="#8a8fa3", **{"from": 0.0}, to=0.14), dict(name="SUBIDA", color="#ff9a2f", **{"from": 0.14}, to=0.34),
                   dict(name="DROP", color="#ff1f3a", **{"from": 0.34}, to=0.62, hit=True), dict(name="BAJA", color="#a855f7", **{"from": 0.62}, to=0.74),
                   dict(name="DROP", color="#ff1f3a", **{"from": 0.74}, to=0.88, hit=True), dict(name="FIN", color="#8a8fa3", **{"from": 0.88}, to=1.0)],
             cards=[dict(at=4.6, x=60, y=1160, v="128.0", l="BPM"), dict(at=5.1, x=390, y=1160, v="11B · A", l="CLAVE"), dict(at=5.6, x=720, y=1160, v="2", l="DROPS")],
             vo="Detecta el tempo, la tonalidad y dónde están los drops.", vo_at=0.5),
        dict(type="shot", dur=6.0, steps=2, logo=2.0,
             caps=[dict(at=0.2, until=5.9, num="✂", title="Cortes <em>en compás</em>", sub="Siempre justo donde mejor suena", step=0)],
             imgs=[dict(at=0, name="04_editor_cortes")],
             cam=[dict(at=0, d=0, c=[1500, 800], z=1.6)],
             cur=[dict(at=0.1, set=[1100, 340]), dict(at=1.0, d=1.0, to="cuts.add_cut")],
             clicks=[dict(at=2.3, to="cuts.add_cut")], hls=[dict(at=0.3, hold=1.2, box="cuts.waveform", pad=4), dict(at=2.2, hold=1.6, box="cuts.tbl", pad=6)],
             vo="Y corta la previa justo donde mejor suena, siempre en compás."),
        dict(type="words", dur=3.4, top=700, gap=0.6, vo="Tú produces. Ella escucha.",
             lines=[dict(t="TÚ PRODUCES", size=160), dict(t="ELLA", cls="red", size=200, big=True), dict(t="ESCUCHA", size=190)]),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Tu previa profesional,", line2="lista en segundos.", vo="Auto Previas, de Radical Récords. Consíguelo en Pei jip.", vo_at=1.2),
    ])
