# Efectos en la onda — propuesta aprobada e implementada en la v3.11.0

> Estado: **implementado** (Basic y Plus). Las imágenes son las maquetas que se enseñaron al usuario antes de construirlo.

**Idea:** el programa no detecta ni aplica efectos solo. El usuario coge un efecto, lo **arrastra hasta la forma de onda** y, **como con los cortes**, elige dónde empieza y cuánto dura.

| Imagen | Qué enseña |
|---|---|
| `efectos-1-carril.png` | Tarjetas de efecto bajo la onda y bloques de efecto dentro de la onda |
| `efectos-2-colocar.png` | Arrastrando una tarjeta: hueco fantasma, ajuste al pulso y tiempos |
| `efectos-3-ajustar.png` | Bloque seleccionado: bordes para estirar y fila de ajustes (inicio, duración, intensidad, quitar) |
| `efectos-4-opciones.png` | Antes/después de las opciones avanzadas (sin casillas automáticas) |

## Cómo funciona

1. **Tarjetas:** 🌀 Flanger · 🌊 Filter Sweep ↗ (sube la tensión) · 🌊 Filter Sweep ↘ (los graves vuelven).
2. **Arrastrar y soltar** sobre la onda (o pulsar la tarjeta para ponerla en el cursor). Se ajusta al pulso más cercano.
3. **Como un corte:** el bloque se mueve arrastrándolo y se estira por los bordes; con él seleccionado se afinan inicio, duración e intensidad. **Supr** o clic derecho lo borra.
4. **Pegado a su trozo del tema:** si se reordenan los cortes, el efecto sigue en el mismo trozo. Fuera de los cortes se ve apagado y no suena.
5. Se guarda con el proyecto («Reabrir proyecto»), no en los presets.

## Decisiones técnicas

- Eventos `{id, type, start, end, amount}` en tiempo del tema original (`src/engine/fx_events.py`).
- Se aplican a cada bloque de audio extraído en el solape evento ∩ bloque, antes de las transiciones; sin eventos la previa es idéntica a la de siempre.
- Desaparecen las casillas automáticas «Flanger» y «Filter Sweep» (5 s antes del drop). Master LUFS se mantiene como casilla de Plus.
- Pendiente para el futuro: botón «▶ Oír» para escuchar solo el efecto, y más efectos (el diseño admite añadir tipos nuevos).
