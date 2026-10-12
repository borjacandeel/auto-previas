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

