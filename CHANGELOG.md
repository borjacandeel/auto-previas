# Historial de Cambios — AutoPrevias

Todos los cambios notables de este proyecto se documentarán en este archivo.
El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [1.0.4] - 2026-10-05

### Corregido
- **Extracción de binarios FFmpeg en Windows:**
  - Sustitución de `tar` (incompatible con archivos zip en GNU tar de MSYS/Git bash) por `python -m zipfile -e ffmpeg-win.zip ffmpeg_bin/`, garantizando una extracción limpia y sin dependencias externas en el runner de Windows.

---

## [1.0.3] - 2026-10-05


### Corregido
- **Optimización masiva del tiempo de compilación CI/CD (de 82 min a ~12 min en Windows):**
  - Desactivación de Link-Time Optimization (`--lto=no`) en MSVC y Clang para suprimir la fase de enlace monohilo `/LTCG` que bloqueaba el runner durante más de 50 minutos.
  - Bloqueo de importación de frameworks de pruebas (`--nofollow-import-to=librosa,pytest,unittest,lazy_loader.tests`) que evitaba compilar a C cientos de módulos de prueba arrastrados por `lazy_loader`.
  - Reemplazo de `--include-package=lazy_loader` por `--include-module=lazy_loader`.
  - Compilación paralela forzada (`--jobs=2` en Windows, `--jobs=3` en macOS).
  - Eliminación del flag redundante `--disable-cache=ccache` en macOS para permitir reuso de caché C.
- **Inclusión robusta de binarios FFmpeg en Windows:**
  - Sustitución de `Invoke-WebRequest` + `Expand-Archive` de PowerShell por `curl` + `tar` nativos de Windows, garantizando la presencia de `ffmpeg.exe`, `ffprobe.exe` y `ffplay.exe` dentro de `ffmpeg_bin/` y eliminando la advertencia `No data files in directory 'ffmpeg_bin'`.

---

## [1.0.2] - 2026-10-05


### Corregido
- **Carga de bibliotecas nativas de LLVM en Windows (llvmlite.dll):**
  - Corrección de `OSError: Could not find/load shared object file 'llvmlite.dll' from resource location: 'llvmlite.binding'` en el ejecutable compilado con Nuitka en Windows x64.
  - Inclusión automática de `llvmlite.dll` en `llvmlite/binding/` y en la raíz del paquete de datos de Python durante la fase de empaquetado post-compilación en GitHub Actions.
  - Activación de `--include-package-data=llvmlite` en Nuitka para Windows para empaquetar metadatos y recursos binarios necesarios para `ctypes.CDLL`.
  - Superación del 100% de la suite de auto-diagnóstico `--selftest` en Windows y macOS.

---

## [1.0.1] - 2026-10-04


### Corregido
- **Compatibilidad de empaquetado standalone con Nuitka:**
  - Creación del sincronizador de dependencias de tiempo de ejecución `scripts/bundle_runtime_deps.py` para preservar librerías puras de Python (`librosa`, `numba`, `llvmlite`, `decorator`, `joblib`, `msgpack`, `cloudpickle`, `pooch`, `platformdirs`, `requests`, `urllib3`, `certifi`, `idna`, `charset_normalizer`, `packaging`, `sklearn`, `threadpoolctl`, `narwhals`).
  - Resolución del conflicto de inspección de bytecode JIT en ejecutables compilados C.
  - Corrección de la estructura de `.dylibs` en ruedas de `sklearn` en macOS mediante `install_name_tool` para firma ad-hoc compatible con Apple codesign sin alertas de bundle inválido.
  - Corrección del codec de consola Windows CP1252 (`UnicodeEncodeError` en caracteres de estado como `✓`) mediante reconfiguración UTF-8 forzada y variables `PYTHONUTF8=1` y `PYTHONIOENCODING=utf-8`.
  - Corrección del atributo `__version__` perezoso en `librosa` durante el auto-diagnóstico `--selftest`.

### Cambiado
- **Estrategia de versiones semánticas:**
  - Parches y correcciones técnicas de empaquetado y compatibilidad catalogados bajo el esquema `1.0.x`.
  - Actualizaciones funcionales mayores reservadas para el ciclo `1.x.0`.
- **Matriz de CI/CD optimizada:**
  - Enfoque exclusivo en arquitecturas de destino solicitadas: **macOS Apple Silicon (ARM64)** y **Windows (64-bit x64)**.

---

## [1.0.0] - 2026-10-04

### Añadido
- **Lanzamiento inicial oficial de AutoPrevias v1.0.0** para macOS (Apple Silicon arm64) y Windows (x64).
- **Instaladores automáticos:**
  - macOS: Imágenes de disco `.dmg` con ventana de instalación "arrastrar a Aplicaciones" y accesos directos configurados.
  - Windows: Asistente de instalación completo `.exe` con Inno Setup, accesos directos en escritorio y menú Inicio, icono oficial y desinstalador limpio.
- **Motor acústico de análisis musical de alta definición:**
  - Detección precisa de BPM y cuadrícula de compases (beat grid).
  - Separación armónica-percusiva (HPSS) para distinguir con precisión quirúrgica entre descansos con bombos/vocales y drops con melodías densas.
  - Análisis espectral adaptativo por percentiles (fullness, planitud espectral, ancho de banda y similitud cromática).
  - Plan automático de previa en 3 bloques clave respetando la musicalidad (apertura, clímax central y final).
- **Procesamiento de audio de estudio:**
  - Filtro DC Blocker y limitador suave transparente a -0.5 dBFS.
  - Time-stretching con preservación de transientes y corrección de pitch.
  - Exportación simultánea a WAV de estudio (24-bit PCM) y MP3 (320 kbps) con carátula oficial de Radical Records y etiquetas ID3 completas.
- **Interfaz gráfica moderna e interactiva:**
  - Waveform acelerado con indicadores visuales de corte (líneas verdes y rojas) y máscaras de zonas omitidas.
  - Reproductor integrado de baja latencia con vúmetro estéreo en tiempo real.
  - Editor interactivo de curvas de tempo (aceleraciones progresivas o tempo constante).
- **Modo de diagnóstico `--selftest`:**
  - Permite verificar de forma autónoma el correcto funcionamiento de todos los componentes de audio y exportación en el ejecutable compilado.
- **Integración continua con GitHub Actions:**
  - Compilación automática en paralelo para macOS y Windows, ejecución de selftest y publicación de releases con sumas de verificación SHA-256.

### Cambiado
- Reubicación de preferencias y caché a carpetas de usuario estándar (`~/Library/Application Support/AutoPrevias` en macOS y `%APPDATA%\AutoPrevias` en Windows) para garantizar compatibilidad con permisos restringidos.
- Búsqueda inteligente de FFmpeg dentro del bundle empaquetado antes de consultar el sistema.

### Corregido
- Eliminación de falsos positivos en la clasificación de drops cuando una pista contiene únicamente bombos y voces en los descansos.
- Manejo robusto de cortes manuales en la waveform manteniendo la alineación al compás musical.
