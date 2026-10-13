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
4. **Actualizar `README.md`:**
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
