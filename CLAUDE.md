# AutoPrevias — Reglas Operativas Permanentes del Repositorio

## 0. Confidencialidad y Seguridad del Repositorio y Tokens
- **Repositorio PRIVADO:** Este repositorio es y debe permanecer **privado**. No cambiar la visibilidad a público bajo ninguna circunstancia sin confirmación explícita del usuario.
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
- El repositorio es privado y los runners de macOS y Windows consumen cuota de minutos a mayor tasa que Linux.
- Mantener `concurrency` activa en `.github/workflows/release.yml` para cancelar automáticamente ejecuciones redundantes de tags obsoletos.
- Usar cachés eficientes de pip y Nuitka.
- Revisar el consumo mensual de minutos y avisar si supera el 70% de la cuota disponible.

---

## 4. Licencias de Terceros
- El proyecto utiliza `pedalboard` (GPL-3) y `Rubber Band` (GPL).
- Mantener siempre la documentación de licencias al día en `THIRD_PARTY_LICENSES.txt`.
- No alterar dependencias críticas ni licenciamiento sin validación y confirmación previa del usuario.
