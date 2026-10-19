# Propuesta: efectos que elige y coloca el usuario en la forma de onda

**Estado: PROPUESTA — sin implementar. Pendiente de que el usuario diga sí o no.**
Imágenes: `efectos-1-carril.png`, `efectos-2-colocar.png`, `efectos-3-ajustar.png`, `efectos-4-opciones.png` (en esta carpeta).

## Qué cambia
Hoy Flanger y Filter Sweep se aplican solos 5 s antes de cada drop que detecta la app. La propuesta quita esa detección:
**solo suena un efecto si el usuario lo coloca.**

## Cómo funciona (3 pasos)
1. **Paleta de efectos** bajo la onda: `🌀 Flanger`, `🌊 Filter Sweep ↗` (subida), `🌊 Filter Sweep ↘` (bajada). Hay hueco para añadir más efectos en el futuro.
2. **Carril de efectos** alineado con la onda y con los cortes. Eliges un efecto, aparece un bloque «fantasma» pegado al cursor que se ajusta al compás (por defecto 4 compases) y, al hacer clic, se coloca. Se mueve arrastrando el centro y se alarga o acorta arrastrando los bordes.
3. **Ajuste del bloque**: al pulsarlo se abre un panel pequeño con intensidad (0–100 %), dirección (subida/bajada), duración en compases, `▶ Oír este efecto` y `🗑 Quitar`.

## Reglas
- Los efectos van ligados al **tema original** (igual que los cortes). Si se reordenan los cortes con ▲ ▼, cada efecto se va con su corte. Un efecto fuera de los cortes aparece rayado y no suena.
- En «Opciones avanzadas» las casillas Flanger y Filter Sweep se sustituyen por un botón **«🎛 Efectos en la onda…»** (con el número de efectos puestos). **Master LUFS** sigue siendo una casilla porque afecta a todo el tema.
- Opcional (apagado por defecto): botón **«✨ Sugerir»** que coloca bloques antes de cada drop para que el usuario los mueva o los borre.
- Se guardan en los presets de estilo y en «Reabrir proyecto». Solo en **Plus**.

## Trabajo previsto
Motor (aplicar cada bloque sobre el audio del corte correspondiente), carril interactivo en la forma de onda, panel de ajuste, guardado en presets/proyectos, paso nuevo en el recorrido de bienvenida, manuales, tests de equivalencia (sin efectos = audio idéntico al actual) y traducción al inglés. Versión MINOR.

## Decisiones que necesito
1. ¿Sí o no a la propuesta tal cual?
2. ¿Quitar del todo la detección automática o dejar el botón «✨ Sugerir»?
3. ¿Más efectos desde el principio (por ejemplo eco/delay, reverso, «riser»)?
