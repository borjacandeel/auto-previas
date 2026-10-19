# AutoPrevias — Reglas Operativas Permanentes del Repositorio

## 0. Confidencialidad y Seguridad del Repositorio y Tokens
- **Repositorio PÚBLICO (decisión del usuario, 2026-10-12):** Este repositorio es y debe permanecer **público**. El auto-update y los enlaces de descarga `releases/latest/download/...` dependen de ello (API de GitHub sin token). No cambiar la visibilidad a privado bajo ninguna circunstancia sin confirmación explícita del usuario. Por ser público, NUNCA commitear secretos (ver reglas de tokens más abajo).
- **Seguridad estricta de Tokens y Credenciales:**
  - NUNCA escribir ningún token (`ghp_...`, `github_pat_...`), clave o credencial en archivos de código, configs, `.git/config`, URLs de git remoto, scripts, logs ni mensajes de commit.
  - NUNCA imprimir tokens por pantalla ni repetirlos en el chat.
  - Para Git usar siempre `gh auth setup-git` (las credenciales se manejan mediante el helper de GitHub CLI).
  - Si en algún momento se detecta un token expuesto en la salida de un comando o en un archivo, avisar inmediatamente al usuario para su revocación inmediata.
  - Si una operación de `gh` falla por permisos, indicar con exactitud qué scope/permiso le falta al token en lugar de buscar rodeos.

---

## 1. Actualización Obligatoria de progreso.md
- **Regla permanente:** Al inicio de cada sesión se debe leer `progreso.md` para conocer el contexto y estado exacto del proyecto.
- **Al finalizar cualquier cambio, corrección de bug, mejora o tarea solicitada por el usuario:** se debe **actualizar inmediatamente `progreso.md`** reflejando con detalle todo lo implementado, el estado actual, las decisiones técnicas y las pruebas ejecutadas.

---

## 2. Ciclo de Publicación Obligatorio tras CADA Cambio
Cada vez que se complete un cambio, mejora o corrección solicitada por el usuario, se debe ejecutar de forma autónoma el siguiente ciclo completo sin esperar a que lo recuerde:

1. **Tests locales:** Ejecutar `pytest` en local dentro del entorno virtual (`.venv`). Si falla algún test, corregir la causa raíz antes de continuar.
2. **Incremento de versión semántica (SemVer):**
   - La versión vive en un único punto canónico: `src/__version__.py`.
   - `PATCH` (`x.y.Z`) para correcciones de bugs y ajustes menores.
   - `MINOR` (`x.Y.0`) para nuevas funcionalidades o mejoras sustanciales.
   - `MAJOR` (`X.0.0`) **únicamente** con confirmación explícita del usuario.
3. **Actualizar `CHANGELOG.md`:**
   - Formato *Keep a Changelog*, redactado en **español claro y comprensible para un usuario final**, sin jerga técnica innecesaria. Secciones: Añadido, Cambiado, Corregido.
4. **Actualizar `README.md`** (**regla permanente del usuario, 2026-10-14: «siempre acuérdate»**; además de la versión y el historial, reflejar las funciones nuevas en «Características Principales», en la tabla «Diferencias entre ediciones» y en los apartados que cambien; y **guardar todo en memoria**: decisiones del usuario en `CLAUDE.md` §6 y el detalle técnico en `progreso.md`):
   - Descripción de AutoPrevias y capturas si aplican.
   - Versión actual y fecha.
   - Tabla de descargas con enlaces directos predecibles a los instaladores de la última Release:
     `https://github.com/<usuario>/auto-previas/releases/latest/download/<archivo>`
   - Instrucciones de instalación para macOS y Windows (incluyendo pasos para apps sin firma de pago: `xattr -cr` en Mac / advertencias de SmartScreen en Windows).
   - Historial resumido de versiones enlazando a `CHANGELOG.md`.
   - Requisitos del sistema y contacto de soporte (`radicalrecordsvlc@gmail.com`).
4 bis. **Regenerar los manuales PDF (Basic y Plus)** — obligatorio en CADA cambio de versión:
   - Ejecutar `python scripts/manual/build_manual.py` (captura la app real en offscreen para cada edición y genera `docs/manual/AutoPrevias-Manual-Basic.pdf` y `docs/manual/AutoPrevias-Manual-Plus.pdf`, firmados "Radical Records", con la versión leída de `src/__version__.py`).
   - Si el cambio añade o modifica funciones/pantallas, actualizar antes el texto en `scripts/manual/build_manual.py` (y las capturas en `scripts/manual/capture.py` si hace falta) para que el manual explique la novedad.
   - Revisar visualmente el PDF (`pdftoppm -r 55 -png`) y subir los dos PDF en el mismo commit que la versión. El test `tests/test_manual_pdfs.py` hace fallar el CI si los PDF no son de la versión actual, y el workflow los adjunta a la Release.
   - **Los PDF NUNCA mencionan el repositorio de GitHub ni sus Releases** (decisión del usuario): la compra y la descarga se indican siempre en Payhip (`payhip.com/RADICALRECVLC`). Tampoco deben contener claves de licencia, emails de compradores ni credenciales (la captura usa HOME aislado y diálogos vacíos).
5. **Actualizar `progreso.md`** con el detalle técnico exhaustivo.
6. **Commit, Tag y Push:**
   - Crear un commit con mensaje descriptivo y claro.
   - Crear el tag git correspondiente (`vX.Y.Z`).
   - Push del commit y del tag hacia `main`.
7. **Monitoreo de GitHub Actions:**
   - Seguir el progreso del workflow con `gh run watch`.
   - Si algún job falla, inspeccionar el log completo, solucionar el problema de raíz, subir un nuevo parche (`PATCH`) y repetir. Jamás borrar ni reutilizar tags ya publicados.
8. **Verificación de Release:**
   - Verificar con `gh release view` que los binarios instaladores y el archivo `SHA256SUMS.txt` están adjuntos y correctos.
9. **Resumen al usuario:**
   - Versión publicada, enlace a la Release, tamaño de instaladores, resultados de `--selftest` y tiempo de compilación.

*Excepción:* Consultas de solo lectura, explicaciones conceptuales o peticiones explícitas de prueba local ("prueba esto sin publicar").

---

## 3. Control de Minutos y Recursos de GitHub Actions
- El repositorio es público (los minutos de Actions en repos públicos no consumen cuota de pago), pero se mantiene el ahorro de ejecuciones redundantes. Antes de lanzar un run nuevo, cancelar siempre los runs activos.
- Mantener `concurrency` activa en `.github/workflows/release.yml` para cancelar automáticamente ejecuciones redundantes de tags obsoletos.
- Usar cachés eficientes de pip y Nuitka.
- Revisar el consumo mensual de minutos y avisar si supera el 70% de la cuota disponible.

---

## 4. Licencias de Terceros
- El proyecto utiliza `pedalboard` (GPL-3) y `Rubber Band` (GPL).
- Mantener siempre la documentación de licencias al día en `THIRD_PARTY_LICENSES.txt`.
- No alterar dependencias críticas ni licenciamiento sin validación y confirmación previa del usuario.

---

## 5. Reglas Técnicas Aprendidas (no repetir errores)
- **Nuitka fijado en `nuitka==4.2.2`** (`requirements-dev.txt`). La 4.3 produjo binarios que crashean en macOS. No actualizar sin compilar y abrir el binario en un Mac.
- **No importar `certifi`** en el código compilado (segfault con Nuitka). Usar el contexto SSL por defecto.
- **Cloudflare bloquea el User-Agent por defecto de `urllib`** (403, error 1010): toda petición HTTP de la app lleva un `User-Agent` propio.
- **Lanzar CI con `workflow_dispatch` (`tag_name`)**, no con push de tags (el token cloud no puede). Antes de cada run nuevo, cancelar los activos.
- **El selftest del binario** (`--selftest`) debe seguir construyendo widgets reales (waveform y activación) para detectar crashes antes de publicar.
- **Secretos:** nunca en archivos, commits ni logs. El repo es público.
- **Manuales PDF:** se generan con Playwright usando el Chromium ya instalado (`executable_path=/opt/pw-browsers/chromium`; NO ejecutar `playwright install`). Las capturas salen de la app real en offscreen (`QT_SCALE_FACTOR=1.6`, HOME aislado, pista sintética). La carátula se renderiza aparte y se une con `pypdf` para que no lleve cabecera/pie.

---

## 6. Memoria de decisiones del usuario (no olvidar)
- **Visibilidad del repo = PÚBLICO, ya aplicada y verificada el 2026-10-13** (sin token: API `private:false`, `releases/latest` 200, `releases/latest/download/...` 302, `raw.githubusercontent.com` 200). El código no usa ningún token de GitHub (el actualizador llama a la API anónima). Hacerlo público no requiere tocar nada; hacerlo privado rompería el auto-update y las descargas.
- **Secretos ya expuestos en el historial público:** las `product-secret-key` de Payhip (Basic/Plus) y una licencia de prueba. La solución real es **rotarlas** (Payhip + secrets del Worker de Cloudflare); reescribir el historial no sirve porque el repo ya es público. Sigue PENDIENTE del usuario.
- **Compra y descarga para el público: siempre Payhip** (`payhip.com/RADICALRECVLC`). Ni los PDF, ni el vídeo, ni ningún material de marketing deben mencionar el repo de GitHub ni sus Releases.
- **Cada cambio se sube a GitHub** (commit + push a `main`) y se refleja en `progreso.md`; cada versión nueva regenera los PDF (§2, paso 4 bis).
- **Vídeo promocional:** `marketing/promo-video/` (HyperFrames; instrucciones en su README). Regenerarlo solo si cambia mucho la interfaz o el mensaje; no es obligatorio en cada versión.
- **Licencia = 1 equipo por clave (decisión del usuario, 2026-10-13), PUBLICADA en v3.2.0; Worker desplegado y probado (11/11).** Si una clave ya está activa en un equipo no se puede activar en otro (se libera con «Desactivar licencia», con `reset` de administrador o tras 15 días sin verificar). Código: `src/licensing/{device,license}.py`, `worker/autoprevias-license.js` (+ `worker/README.md` con el despliegue en Cloudflare: KV `LICENSES`, secret `ADMIN_TOKEN`). Pendiente: rotar claves de Payhip (recrearlas como *Secret*), cambiar `ADMIN_TOKEN`, y más adelante `REQUIRE_DEVICE=1` en el Worker. Al guiar al usuario en Cloudflare/Terminal: desactivar la traducción de Chrome (rompe el código) y usar sintaxis zsh (Mac), no `read -p`.
- **ADMIN_TOKEN del Worker: el usuario decidió mantener el actual (2026-10-13).** No volver a listarlo como pendiente ni insistir en cambiarlo; nunca escribir su valor en archivos, commits ni respuestas. Siguen pendientes solo: rotar las `product-secret-key` de Payhip (recrearlas como *Secret* en Cloudflare) y revocar/regenerar la licencia de prueba.
- **Estado publicado (2026-10-13): v3.2.0** (Release con 4 instaladores + alias estables, `SHA256SUMS.txt` y los 2 PDF; inventario y tamaños en `progreso.md` sesión 41). Pruebas pendientes del usuario en el Mac: checklist de la sesión 41. Pendientes de seguridad del usuario: rotar `product-secret-key` de Payhip (recrear como *Secret*) y revocar la licencia de prueba.
- **Rotación de las `product-secret-key` de Payhip: el usuario decidió IGNORARLA (2026-10-13).** No volver a listarla como pendiente ni insistir (solo mencionarla si él pregunta por seguridad). Siguen sin escribirse sus valores en ningún archivo ni respuesta. Pendiente solo de limpiar: licencias de prueba creadas en Payhip.
- **Decisiones del usuario sobre pendientes (2026-10-13):** prueba de un equipo = OK (el rechazo y el reparto funcionan); **no limpiar las licencias de prueba de Payhip** (dejarlo); **PENDIENTE PARA EL DÍA DE LANZAMIENTO: si se pasan los productos de Payhip de privado a público, abrir el enlace de la tienda en ventana de incógnito y comprobar que se ven; si el enlace cambia, actualizarlo en app (`src/ui/activate.py`, `src/i18n_en.py`), PDF, vídeo, README/CHANGELOG/CLAUDE/progreso y sacar versión PATCH.**
- **Publicada en v3.3.0 (2026-10-13): generador de vídeo animado «Radical Neón»** (motor en Python `src/engine/video_neon.py`, fotogramas → FFmpeg; 9:16, 1:1, 16:9; paleta carmesí por defecto; fallback al vídeo clásico). El vídeo promocional (`marketing/promo-video/`) se amplió a ~47 s con pausas de lectura (`holds` en `choreo.json`, mapeadas con `M(t)` en JS y Python) y una escena del vídeo Neón.
- **Vídeo por ediciones (decisión del usuario, 2026-10-13, v3.5.0):** **Basic SÍ genera vídeo animado** (plantillas Neón, desde el MP3) con **marca de agua obligatoria** pequeña y translúcida abajo a la derecha («Generado por Radical Records · AutoPrevias Basic») + cierre con firma y enlace fijos; **Plus** exporta **sin marca de agua** y elige el final (firma AutoPrevias / fundido a negro / sin cierre). Garantizado en el motor por `get_edition()`. Con vídeo marcado, el MP3 se exporta siempre. Hay vista previa del vídeo en la app.
- **Plan de marketing (2026-10-13):** `marketing/PLAN-VIDEOS.md` — 11 vídeos (el general ya hecho + 10 por producir, orden 1, 3, 2, 4, 5, 6, 7, 8, 9, 10, 11; el 11 es la versión en inglés). Pendientes de producir; un vídeo cada vez para que el usuario apruebe. Ver tabla de pendientes en `progreso.md` (sesión 46).
- **Voces de los vídeos (decisión del usuario, 2026-10-13):** castellano de **España**; elegidas **Álvaro y Ximena** (`edge:es-ES-AlvaroNeural` / `edge:es-ES-XimenaNeural`). Las voces latinoamericanas de Kokoro se descartaron. Aviso de licencia: servicio de lectura de Edge no oficial; para uso comercial formal, Azure Speech. Los 11 vídeos están producidos con `marketing/videos/kit` (ver progreso sesión 47).
- **Decisiones del usuario sobre el lanzamiento (2026-10-13):** pruebas en Mac/Windows de la v3.5.0 y revisión de los 11 vídeos = **dados por hechos**. **Fichas de Payhip: las actualizará él más adelante.** **Voces (licencia Azure/Edge): lo decidirá él más adelante** (no insistir). **Día de lanzamiento:** cuando los productos de Payhip sean públicos él avisará con los enlaces; hay que ser **rápidos**: comprobar el enlace, si cambia ejecutar `python scripts/set_store_link.py <nuevo> --apply` (cambia app, PDF, vídeos, README), versión PATCH, regenerar PDF, re-render de vídeos si hace falta, publicar y probar; **después** actualizará el precio final y habrá que revisar textos/vídeos si mencionan precios (ahora no los mencionan).
- **Procedimiento del día de lanzamiento (preparado 2026-10-13):** al recibir el enlace público: `python scripts/launch_public.py <enlace>` (simulación) y `--apply` (cambia enlace en app/PDF/vídeos/README, sube PATCH, CHANGELOG, tests y PDF); después re-render de vídeos (`marketing/videos/kit/build.py <id>`, ~4 min c/u; kit en `marketing/videos/kit`, requiere los venvs de TTS descritos en progreso sesión 47), commit, push y CI. Worker/Cloudflare: **solo hay que tocar algo si se crean productos NUEVOS en Payhip** (nuevas `product-secret-key`; el Worker admite varias por edición separadas por comas) — guía completa en `worker/LANZAMIENTO.md`. Recomendado ese día: `REQUIRE_DEVICE=1`.
- **Licencias por edición (decisión del usuario, 2026-10-13, v3.5.1):** una clave Basic NO activa el instalador Plus y una Plus NO activa Basic (el cliente envía `app_edition` y el Worker responde `wrong_edition` sin ligar la clave). Una caída de Payhip nunca revoca una licencia (`unavailable`). Prueba real de licencia Plus con el Mac del usuario: OK.
- **Vídeo personalizable (decisión del usuario, 2026-10-14, v3.6.0):** **Plus elige todo** (fondo: plantilla Neón o su imagen por formato; onda de sonido sí/no, barras/línea/círculo, posición y color; textos y su posición; final: firma, negro, sin cierre o su imagen). **Basic elige el final entre «Generado por AutoPrevias» (firma + enlace) o fundido a negro**, con marca de agua siempre y sin imagen propia. Código: `src/engine/video_neon.py` (`normalize_custom`), `src/ui/video_custom.py`.
- **Panel de vídeo (decisión del usuario, 2026-10-14, v3.7.0):** el usuario aprobó las 8 propuestas de facilidad de uso: tarjeta única de vídeo con botones de formato, looks de un clic, arrastrar imagen, vista previa en vivo, resumen antes de generar, Basic con opciones de Plus bloqueadas y opciones avanzadas plegables. Las imágenes del vídeo deben ser 9:16, 1:1 o 16:9: si no lo son, la app avisa y enseña ejemplos.
- **Rendimiento (2026-10-14, v3.8.0):** el usuario pidió una app más fluida que se adapte al equipo («dale caña pero no la cagues»). Regla: toda optimización debe dejar los resultados **idénticos** (BPM, secciones, audio, fotogramas) y llevar test de equivalencia; no tocar el procesado de audio. Código en `src/perf.py` y `src/analysis/fastdsp.py`; ajuste «Rendimiento» en ⚙ Licencia.
- **Regla de cierre de cada cambio (decisión del usuario, 2026-10-14):** al terminar, **guardar todo en la memoria** (`CLAUDE.md` §6 + `progreso.md`) y **actualizar `README.md`** (versión, historial, características, tabla de ediciones) — siempre, sin que haya que recordarlo.
- **Notificación al generar cada previa (pedida 2026-10-14): HECHA en v3.10.0** (logo propio `assets/notify_icon.png` y, al pulsarla, se abre la carpeta; el usuario pidió corregir que antes no salía bien el logo ni abría la carpeta). Código: `src/notifications.py`. Pendiente solo probar el clic en Mac/Windows.
- **Recorrido de bienvenida (decisión del usuario, 2026-10-14, v3.9.0):** tutorial interactivo **solo la primera vez** tras instalar/activar, con dos opciones («Hacer el recorrido» / «Omitir»); después **nunca más** (flag `onboarding_done`; no se ofrece a quien ya tiene Recientes). Cubre **toda la app** con ejemplos (pantalla de inicio + panel de resultados con pista de ejemplo sintética que no deja rastro); Basic solo ve lo de Basic. Código: `src/ui/tour.py` (`TourOverlay`, `OnboardingTour`, `WelcomeDialog`, `build_steps`), disparo en `launch()` (`MainWindow.maybe_start_onboarding`). Extra: botón «Ver recorrido de bienvenida» en ⚙ Licencia (solo manual). Textos ES/EN en `src/i18n_en.py` (`EN_TOUR`). Si se añade una función nueva a la app, **añadir su paso en `build_steps`** (y su traducción; el test lo exige).
- **Vídeo tutorial 16:9 de generación de vídeos (2026-10-14):** `marketing/videos/specs/t01_tutorial_videos.py` (kit en `marketing/videos/kit`, voces Álvaro/Ximena, ~7:34, 31 escenas). Resultado final en `marketing/videos/publicados/AutoPrevias-Tutorial-Videos-Plus.mp4`.
- **Estado publicado (2026-10-14): v3.9.0** (Release con 4 instaladores + alias, `SHA256SUMS.txt` y los 2 PDF; inventario en `progreso.md` sesión 58). Regla aprendida: la interfaz y sus tests deben probarse también a **tamaño mínimo de ventana** y teniendo en cuenta que **Windows no borra archivos abiertos** (liberar `QMediaPlayer` antes de borrar).
- **Cortes y orden (decisión del usuario, 2026-10-19, v3.10.0):** en **Basic y Plus** los cortes se llaman «Corte 1, Corte 2…» (nombre fijo), se pueden **ordenar con ▲ ▼** y la previa puede **empezar al inicio, a mitad del tema o donde el usuario arrastre el primer corte**. **Plus:** botón de **arranque de BPM** (vinilo de 0 al tempo en N s por defecto 1 s, o BPM originales) y **🖋 Firmar tema** (temas enteros: solo carátula + etiquetas, FLAC/WAV máxima calidad, sin master ni efectos). **Notificaciones** con el logo (`assets/notify_icon.png`) que abren la carpeta al pulsarlas (`src/notifications.py`; **pendiente de probar el clic en Mac/Windows**).
- **EFECTOS EN LA ONDA: PROPUESTA PENDIENTE DE SÍ/NO del usuario (2026-10-19).** Quiere que **el usuario elija y coloque los efectos en la forma de onda** en vez de que la app los detecte (Flanger/Filter Sweep hoy van 5 s antes de cada drop detectado). Propuesta e imágenes en `docs/propuestas/` (carril de efectos, paleta, bloques ajustables, botón «🎛 Efectos en la onda…»). **No implementar hasta que diga sí.**
- **Regla aprendida (2026-10-19):** FFmpeg no permite carátula en WAV: se escribe una etiqueta ID3v2.3 propia dentro del WAV (`src/engine/sign.py`). Las animaciones usan `src/ui/anim.py` y se desactivan en tests (`tests/conftest.py`).

