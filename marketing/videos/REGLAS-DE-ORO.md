# Reglas de oro para generar vídeos de AutoPrevias

> **Leer SIEMPRE antes de producir cualquier vídeo.** Recoge todo lo que el usuario ha pedido y lo que se ha aprendido.
> Kit: `marketing/videos/kit/` · specs: `marketing/videos/specs/` · salida: `marketing/videos/out/`.

## 1. Objetivo: que el espectador se quede hasta el final
- **Gancho en los 2-3 primeros segundos** con una pregunta o un dolor directo (ej. «¿Cansado de hacer tus previas a mano?»).
- **Dolor → giro → solución → prueba → cierre.** Primero se enseña lo pesado del método manual (pasos que se estampan uno tras otro), luego el giro «con AutoPrevias eso ya está hecho» y después lo más importante del programa.
- **Ritmo rápido:** cada escena 3-5 s, cortes secos, una sola idea por escena. Nada de pantallas muertas ni transiciones largas.
- **Duración corta: ≤ 45-50 s** (el mensaje es «tu previa en 30 segundos»; un vídeo de 60+ s se rechazó por largo).
- **Cierre fijo:** «Tu previa en 30 segundos» + enlace de Payhip.

## 2. Contenido
- Mostrar **lo más importante** del programa: arrastrar el tema, mejores momentos elegidos solos, **efectos arrastrables sobre la onda**, vídeo animado (3 formatos), modo promo antifugas, firma y carátula, formatos MP3/WAV/FLAC, generar y abrir carpeta.
- **NO mencionar BPM** (decisión del usuario) ni tempo en los vídeos de presentación.
- Compra/descarga: **siempre Payhip** (`payhip.com/RADICALRECVLC`). Nunca GitHub, Releases, claves, emails ni credenciales.
- Los 3 guiones aprobados:
  1. **«Tu previa en 30 segundos»** (presentación oficial): «¿Cansado de hacer tus previas a mano? Abrir Traktor, cargar el tema, grabar, meter efectos, acortar, guardar, exportar… y subirlo. Pues con AutoPrevias eso ya está hecho» → funciones clave → «Tu previa en 30 segundos».
  2. **Antifugas**: «Si no quieres que nadie pinche tus temas gratis, hazles una previa con AutoPrevias».
  3. **Todo en un clic**: arrastras un tema y sale todo (WAV, MP3, vídeo en 3 formatos, notificación) + destellos de funciones + «Elige tu edición».
- **Un vídeo cada vez**: el usuario aprueba el 1 antes de generar el 2 y el 3.

## 3. La app en pantalla (lo que más se critica)
- El **visor del programa debe ser grande y legible**: usar `tall=True` en el spec (visor 1040×1250) y **zoom alto**. Ojo: `z=1.0` = imagen ajustada al ancho del visor; la región visible es `2240/z` px de ancho de la captura (z≈1.6-2.0 para leer la interfaz).
- **El puntero debe hacer lo que el programa muestra**: cada clic/arrastre cambia el estado del programa. Se consigue **cambiando de captura en el instante del clic** (`imgs=[dict(at=0,name=A), dict(at=t_clic,name=B)]`), con capturas REALES de cada estado (p. ej. `p_estudio_0/1/2` = Estudio sin efectos → con Flanger → con Flanger + Filter Sweep; `03b_exportar` → `08_generada`). Si falta un estado, **capturarlo** con la app real (copia de `scripts/manual/capture.py` con HOME aislado, `QT_SCALE_FACTOR=1.6`) y guardarlo en `docs/manual/_work/plus/`.
- Coordenadas del puntero/recuadros en **píxeles de la captura** (2240 px de ancho); los nombres de `meta.json` (`welcome.open_btn`, `loaded.waveform`…) están en px de ventana.
- Resaltar con recuadro (`hls`) justo lo que se toca y mover la cámara (`cam`) siguiendo al puntero.
- Regenerar las capturas (`python scripts/manual/capture.py plus`) tras cambios de interfaz para que el vídeo muestre la versión actual.

## 3 bis. Arrastrar y soltar (petición del usuario, 2026-10-21)
- En las escenas de **cortes** y de **efectos** el espectador debe VER que se arrastran y se sueltan: el cursor lleva un **«fantasma»** (`chips=[dict(text, at, d, **{"from":[x,y]}, to=[x,y], bg, fg)]` en una escena `shot`; mismo `at+0.1` y `d` que el movimiento del cursor) desde el origen hasta el destino, y en el momento de soltar **se cambia a la captura con el resultado**.
- Capturas reales por estado (script de captura con la app: `R._on_waveform_cuts_changed(cortes)`, `R._on_add_cut_clicked()`, `R._waveform._add_fx(tipo, t)`): `p_cut_0/1/2` (cortes: original → borde estirado → «+ Corte») y `p_fx_1/2` (+ Flanger, + Filter Sweep). Guardarlas en `docs/manual/_work/plus/`.
- Coordenadas útiles (px de la captura 2240 de ancho, Estudio): fila de efectos y≈809 (Flanger x≈419, Filter Sweep ↗ x≈587), bloques de efecto sobre la onda y≈747, onda y 444–774, botón «+ Corte» (1408, 317), ⚙ (1716, 71).

## 4. Voz y música
- **El vídeo 3 («Todo en un clic») lleva VOZ** (Álvaro); los vídeos 1 y 2 van SIN voz (decisión del usuario, 2026-10-21).
- Por defecto SIN voz (con voz salen más largos), salvo el vídeo 3. Voces si se usan: Álvaro / Ximena (`edge:es-ES-…Neural`), castellano de España.
- Música sintetizada a 128 BPM del kit; efectos sincronizados con las escenas.

## 5. Flujo de trabajo (técnico)
1. Escribir el spec en `specs/<id>.py` (escenas: `words`, `shot`, `race`, `cards`, `antileak`, `cta`…; ver specs existentes).
2. `cd marketing/videos/kit && /tmp/claude-0/pyside_venv/bin/python build.py <id> --no-voice --no-render` (comprueba duración total).
3. **Revisar fotogramas ANTES de renderizar:** `cd work/<id> && npx --yes hyperframes@0.8.151 snapshot --at t1,t2,…` y leer `snapshots/contact-sheet.jpg`. Sacar ≥1 fotograma por escena y por cada cambio de estado.
4. Renderizar sin `--no-render` con `setsid nohup … &` (≈6-7 min). **Monitor de progreso cada 5 s** leyendo `"pct"` de `work/<id>/render.log` (el usuario lo pide).
5. Enviar el MP4 con `SendUserFile` (adjunto). Responder en **castellano, ultracorto** (skill `respuestas-ultracortas`).
6. Commit y push del spec (el MP4 no se sube; `out/` y `work/` no van al repo).

## 6. Trampas conocidas
- `pkill -f "build.py p01"` mata también el propio shell (la orden contiene el patrón): usar `pkill -f "[b]uild.py p01"` o `kill <pid>`.
- Un `words` con la misma `dur=2.8` aparece también en otras escenas: **no cortar specs con `str.index` de textos repetidos**; reescribir el fichero entero.
- La escena `recap` sale diminuta en vertical: no usarla en 9:16 (usar `words`).
- Las escenas con voz se alargan al tamaño de la locución; sin voz mandan las `dur` del spec.
- Si hay procesos viejos de `hyperframes render`/`ffmpeg`, matarlos por PID antes de relanzar.
- Skills de referencia que pasó el usuario (awesome-claude-video-skills): HyperFrames es lo que ya usa el kit; ideas útiles de otros: zoom que sigue al clic (cursorcam), cortes sincronizados con la música (product-launch-motion).
- El AAC no debe pasar de -1 dBFS: el kit normaliza el pico a 0,70 (si no, el render falla al final con «AAC true peak remained above -1 dBFS»).
