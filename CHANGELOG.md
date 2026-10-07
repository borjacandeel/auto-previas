# Historial de Cambios — AutoPrevias

Todos los cambios notables de este proyecto se documentarán en este archivo.
El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [2.5.1] - 2026-10-07

### Corregido
- **Cortes de previa más musicales**: el algoritmo de detección de secciones ya no descartaba las subidas (buildups) de temas donde el bombo continúa durante la subida (dance, house, hardstyle). Los cortes ahora aterrizan correctamente en el inicio de la subida o del breakdown más cercano, en lugar de en un punto aleatorio calculado con offset fijo.
- **Detección de buildup mejorada**: se eliminó la restricción errónea que exigía ausencia de bombo para detectar una subida. También se detectan siempre los 1-2 compases justo antes del drop (redoble / corte vocal) como parte del buildup.
- **Inicio de INTRO ajustado**: los primeros 8 compases se clasifican como INTRO (antes eran 12), evitando que buildups cortos al inicio del tema se solaparan y no se detectaran.

## [2.5.0] - 2026-10-07

### Añadido
- **Voice Drop con región visual y ducking profesional**: al seleccionar un archivo de voice drop, la waveform muestra ahora una región sombreada dorada que indica exactamente cuánto tiempo ocupa el audio (no solo una línea). El label también muestra la duración del archivo (ej. "✓ firma.wav · 3.2s").
- **Ducking de 1 segundo con rampa suave**: el master baja progresivamente al 20% durante 1 segundo antes de que arranque el voice drop, se mantiene al 20% mientras suena, y sube de vuelta al 100% en 1 segundo al acabar. Sin cortes bruscos.

### Cambiado
- **Keylock eliminado**: la opción de modo Keylock se ha quitado de la interfaz. La app usa siempre modo Vinilo (+Pitch Armónico).

## [2.4.0] - 2026-10-07

### Añadido
- **4 instaladores compilados por release** (Basic macOS, Basic Windows, Plus macOS, Plus Windows). La edición queda horneada en el binario en tiempo de compilación mediante `src/_edition.py` generado por el CI antes de Nuitka — el usuario no puede cambiar de edición editando archivos.
- **`BAKED_EDITION` en `config.py`**: si el módulo `src._edition` existe (build compilado), su valor es la fuente autoritativa de edición y el JSON de configuración no puede sobreescribirlo.
- **Inno Setup actualizado**: acepta `/DEdition=basic|plus`, genera `AppId`, `DefaultDirName` y nombre del instalador distintos por edición, permitiendo que Basic y Plus coexistan instalados en el mismo PC sin conflicto.

## [2.3.0] - 2026-10-07

### Añadido
- **Sistema de ediciones: Básica y Plus**. La app ahora distingue dos modos de operación controlados por el ajuste `edition` en la configuración:
  - *Edición PLUS* (por defecto): acceso completo a todas las funciones — exportación WAV/FLAC, vídeo para redes, Keylock, Voice Drop, editor avanzado de cortes/BPM, modo lote y vigilar carpeta.
  - *Edición BÁSICA*: solo exportación MP3, modo Vinyl fijo, sin vídeo, sin Voice Drop, sin editor avanzado ni procesamiento en lote. Pensada para un precio de entrada más bajo.
- **Badge de edición visible en el header** de la aplicación: etiqueta de color diferenciada (violeta "✦ PLUS" o azul "◈ BÁSICA") para que el usuario siempre sepa qué versión está usando.
- **Launchers dedicados por edición**: cuatro nuevos scripts de inicio (`AutoPrevias_Plus.command`, `AutoPrevias_Basic.command`, `AutoPrevias_Plus.bat`, `AutoPrevias_Basic.bat`) que fuerzan la edición correspondiente con `--edition=plus` / `--edition=basic` sin necesidad de tocar la configuración manualmente.
- **Argumento `--edition=`** en `main.py`: permite forzar la edición al arrancar desde la línea de comandos o desde los launchers. Útil para demos, pruebas y futura integración con el sistema de licencias.

## [2.2.0] - 2026-10-07

### Añadido
- **Botón "Generar otra previa"** en la tarjeta de éxito: tras exportar, un botón rojo permite abrir directamente un selector de archivos para cargar un nuevo track y generar su previa sin cerrar ni reiniciar la app. El análisis se lanza automáticamente y los resultados se muestran en la misma pantalla.

## [2.1.0] - 2026-10-06

### Corregido
- **Keylock sonaba con artefactos**: el factor de time-stretch estaba invertido (`1/rate` en lugar de `rate`), haciendo la previa más lenta en lugar de más rápida. Corregido para que el tempo aumente correctamente sin distorsión.
- **Keylock ahora incluye efecto spin-up/spin-down**: los primeros y últimos segundos usan varispeed vinilo (pitch sube/baja naturalmente al arrancar y frenar), mientras el cuerpo central mantiene el tono bloqueado.
- **Vídeo siempre exportaba en 9:16** aunque se seleccionara 1:1: el `aspect_ratio` no se incluía en el diccionario de metadatos pasado al motor de vídeo. Corregido.
- **Pitch/tempo máximo reducido a 3% (≈3 BPM)**: el valor por defecto era 15%, causando variaciones de tempo excesivas. Ahora el rango es más sutil y profesional.
- **Carátula incrustada y guardada como predeterminada no se cargaba** al volver a abrir la app o cargar un nuevo track. Corregido el orden de prioridad: carátula guardada → carátula embebida → logo oficial.
- **Preferencias de exportación no persistían**: al guardar firma/carátula, ahora también se guardan el modo de velocidad, paleta de vídeo y ratio de aspecto.
- **Voice Drop: sin marcador visual en la forma de onda**. Ahora al seleccionar un archivo de voz aparece una línea dorada discontinua arrastrable en la waveform indicando el punto de inserción. El usuario puede arrastrarlo para elegir la posición exacta (modo "Manual") o usar Pre-Drop/Intro automáticos.

## [2.0.0] - 2026-10-06

### Añadido (BIG UPDATE — Versión 2.0.0 + Visualizador Vídeo Triple Capa v2.1)
- **Modo DJ Vinyl Speedup vs Keylock Digital**:
  - *Modo Vinyl Clásico*: Varispeed continuo con pitch shift armónico analógico (estilo giradiscos Technics 1200 / CDJ vinyl mode), acelerando tempo y tono conjuntamente para máxima energía en club.
  - *Modo Keylock Digital*: Algoritmo time-stretch que congela la tonalidad y afinación musical original mientras acelera los BPM de la previa.
- **Firma Vocal / Voice Drop Personalizable con Auto-Ducking**:
  - Integración de samples de voz del sello / DJ con atenuación inteligente automática del audio musical (-4 dB auto-ducking) y posicionador dinámico en la previa (*Pre-Drop* 3.8s antes del drop principal o *Intro* al compás inicial).
- **Extracción Automática de Carátulas Incrustadas en Audio**:
  - Extracción transparente a través de FFmpeg de portadas incrustadas en metadatos ID3v2, FLAC PICTURE, Vorbis Comment, AIFF y M4A sin dependencias externas pesadas.
- **Rediseño Integral Hiper-Profesional de la Plantilla de Vídeo Social**:
  - Fondo cinemático ultra-profundo con color grading de alta saturación y desenfoque atmosférico multicapa.
  - Carátula de estudio con bisel neón doble, esquinas curvadas de alta resolución y efecto flotante.
  - Analizador de espectro FFT de 64 bandas y osciloscopio analógico enriquecidos sobre tarjeta de cristal esmerilado (*glassmorphism*).
  - Barra de progreso TikTok / Reels animada frame a frame en el borde inferior con color a juego de la paleta.
  - Píldora promocional dinámica personalizable para redes sociales (ej. "¡YA DISPONIBLE EN BEATPORT & SPOTIFY!").
- **Selector de Paletas de Color Neón de Estudio**:
  - *Cian & Magenta Radical* (eléctrico club)
  - *Verde Neón Rave / Acid* (underground rave)
  - *Rojo Carmesí Studio* (firma Radical Records)
  - *Ámbar Gold & Solar* (tonos cálidos y festival)
  - *Cyber Violet & Purple* (estética synthwave / retrowave)
- **Historial de Temas Recientes con 1 Clic**:
  - Acceso inmediato desde el botón `🕒 Recientes` en la cabecera principal, con lista desplegable de pistas cargadas recientemente y opción de limpieza rápida.
- **Carpeta Vigilada en Segundo Plano (Watch Folder)**:
  - Modo centinela activable desde `👁️ Vigilar Carpeta` que monitoriza un directorio seleccionado en segundo plano cada 4 segundos y procesa automáticamente nuevos audios que caigan en la carpeta.
- **Visualizador de Vídeo Triple Capa (`src/engine/video.py`)**:
  - *Capa 1 — Espectrograma scrolling*: `showspectrum color=channel:saturation=8:gain=5:scale=cbrt` — heatmap arcoíris en tiempo real, la pieza visual más llamativa.
  - *Capa 2 — Barras FFT*: `showfreqs win_size=2048` — mayor resolución frecuencial, barras EQ multicolor con paleta neón.
  - *Capa 3 — Osciloscopio P2P*: `showwaves mode=p2p:draw=full` — líneas peak-to-peak gruesas y vívidas.
  - Tarjeta glassmorphism rediseñada con etiquetas de sección, divisores neón y segundo bisel interior.
  - Fondo cinemático más profundo: `boxblur=52` + `saturation=3.0`.
  - Barra de progreso TikTok de 14px con highlight blanco superior.
- **Repositorio Git inicializado y publicado**:
  - Primera subida completa a `https://github.com/borjacandeel/auto-previas` con historial fusionado.
  - Tag `v2.0.0` publicado → dispara CI/CD: compilación Nuitka macOS arm64 (DMG) + Windows x64 (EXE) + GitHub Release automático.

---

## [1.2.4] - 2026-10-06

### Corregido
- **Arranque Universal en Windows sin Permisos de Administrador (Standard User Fix)**:
  - Asignación explícita de permisos NTFS `users-modify` en Inno Setup (`installer/windows/setup.iss`) para el directorio de instalación `{app}` y todos sus archivos, permitiendo que usuarios estándar de Windows sin permisos administrativos puedan ejecutar la aplicación sin bloqueos ni requerir "Ejecutar como administrador".
  - Habilitación de la directiva `PrivilegesRequiredOverridesAllowed=dialog commandline` en Inno Setup para permitir la instalación tanto por usuario actual (sin UAC) como para todos los usuarios.
  - Endurecimiento de rutas en `src/config.py` con fallbacks defensivos a directorios `%TEMP%` y comprobación segura de entornos standalone (`__compiled__` / `frozen`).

---

## [1.2.3] - 2026-10-06

### Corregido
- **Prevención de Bloqueos de Proceso y Fork-Bombs en Windows**:
  - Incorporación de `multiprocessing.freeze_support()` en el punto de entrada de `src/main.py`.
  - Desactivación forzada de generación de bytecode en runtime (`sys.dont_write_bytecode = True`).
  - Precompilación AOT de todos los módulos Python en el script de empaquetado de dependencias runtime (`scripts/bundle_runtime_deps.py`).
  - Inclusión explícita de plugins de Qt (`sensible,multimedia,platforms,styles,imageformats`) en la compilación Nuitka.
  - Registro de arranque inmediato en `%TEMP%\autoprevias_startup.log` y captura visual de errores con MessageBox nativa.

---

## [1.2.2] - 2026-10-06

### Añadido
- **Calibración Musical con Referencias Reales (`ORIGINAL 2.flac` vs `PREVIA 2.wav`)**:
  - Ingeniería inversa sobre el patrón comercial de Radical Records con análisis Chroma CENS y Beat Grid denso: Corte 1 desde compás 1 cuando la intro ≤ 16 compases, Corte 2 con 12-16 compases del breakdown melódico central y Corte 3 con subida final + drop cerrado en límite de frase.
- **Preset por Defecto de 120 Segundos / 2 Minutos (Club)**:
  - Cuarto preset rápido añadido a la interfaz y motor configurado como valor por defecto (`default_preset_sec: 120`).
- **Modo Consola `attach` en Nuitka**:
  - Configurado `--windows-console-mode=attach` para permitir ejecución limpia desde escritorio y trazas de error inmediatas si se lanza desde consola.

---

## [1.2.1] - 2026-10-05

### Corregido
- **Configuración de WorkingDir en Inno Setup**:
  - Asignación explícita de `WorkingDir: "{app}"` en las entradas `[Icons]` y `[Run]` de Inno Setup, garantizando la resolución correcta de rutas relativas y assets al lanzar desde el escritorio o el instalador.
- **Renderizado por Software Seguro**:
  - Activación forzada de `QT_OPENGL=software`, `QT_QUICK_BACKEND=software` y `AA_UseSoftwareOpenGL` para evitar cuelgues en máquinas virtuales y controladores GPU incompatibles en Windows.

---

## [1.2.0] - 2026-10-05

### Añadido
- **Organización Automática en Subcarpeta `Previas/`**:
  - Todas las previas generadas (WAV, MP3, FLAC, AIFF y Vídeo MP4) se guardan automáticamente dentro de una subcarpeta organizada llamada `Previas` en el directorio de la canción de origen (o dentro de la carpeta personalizada configurada), evitando mezclar archivos en las carpetas principales del usuario.
- **Plantilla de Vídeo Viral para Redes Sociales (TikTok, Reels, Shorts)**:
  - Fondo cinemático enriquecido con color grading (`eq=brightness=-0.35:contrast=1.35:saturation=2.2`) y desenfoque atmosférico extraído de la propia carátula.
  - Carátula de estudio con esquinas redondeadas (`radius=28`), máscara alfa de alta resolución y doble bisel iluminado (resplandor cian translúcido + contorno blanco nítido).
  - Analizador de espectro FFT tricolor (Cian Eléctrico / Magenta Radical / Ámbar) + osciloscopio dinámico analógico con opacidad total (`draw=full`) sobre tarjeta glassmórfica con marcadores de frecuencia de estudio (20Hz a 20kHz) y niveles de referencia (-6dB y -18dB).
  - Sustitución completa de emojis rotos (`[]`) por iconos vectoriales trazados matemáticamente en Pillow (rayo de BPM, vinilo de Tonalidad, faders de Master y estrella de Exclusivo).
  - Tipografía broadcast en gran formato (50pt) con sombras oscuras profundas y cabecera de emisión en directo con indicador `REC` rojo.
- **Efectos Pre-Drop Agresivos y Automáticos (5s antes del Drop)**:
  - Flanger de estudio con feedback agresivo (0.74), profundidad modulada (3.8ms), oscilador LFO (0.65 Hz), mezcla wet al 75%, apertura suave de 0.6s y parada en seco instantánea (3ms) en el downbeat (beat 1) del drop.
  - Sweep de filtro pasa-altos complementario aplicado automáticamente 5 segundos antes de cada drop real.
- **Claridad de Rutas de Guardado y Botones Directos de Apertura**:
  - Tarjeta flotante de confirmación `_card_export_success` en la pantalla principal con la lista de archivos creados, ruta completa y botón de acción rápida `📂 Abrir Carpeta en Finder / Explorador`.
  - Selector visual explícito de carpeta destino en el Procesador por Lote (Batch), columna de acciones interactivas con botón `📂 Abrir` por fila, soporte para apertura por doble clic y diálogo emergente de resumen con botón directo a la carpeta.

### Corregido
- **Integridad del Sello Digital de Firma (`codesign`) en macOS**:
  - Reordenamiento del pipeline de CI/CD para ejecutar el selftest con `PYTHONDONTWRITEBYTECODE=1` y limpiar exhaustivamente archivos `.pyc` antes de la firma definitiva, eliminando la alerta de Gatekeeper *"AutoPrevias.app está dañado y no se puede abrir"*.
- **Cierre Seguro de Hilos y Prevención de `Abort trap: 6`**:
  - Implementación de `closeEvent()` y `_cleanup_threads()` en `MainWindow` con comprobación periódica de `isInterruptionRequested()` en `WaveformLoader`, `AnalysisWorker` y `ExportWorker`, garantizando una salida limpia sin abortos de proceso.

---

## [1.1.0] - 2026-10-05

### Añadido
- **Compatibilidad Universal con Windows ARM64 (Snapdragon X Elite / Parallels en Apple Silicon)**:
  - Detección precisa de procesadores ARM mediante llamadas directas a `GetNativeSystemInfo` e `IsWow64Process2` vía `ctypes` en `src/compat.py`.
  - Configuración automática de renderizado por software seguro (`QT_OPENGL=software`, `QT_QUICK_BACKEND=software`, `AA_UseSoftwareOpenGL`) eliminando bloqueos de inicialización de la GPU emulada en `qwindows.dll`.
  - Soporte de instalación universal en Inno Setup (`ArchitecturesInstallIn64BitMode=x64compatible arm64`).
- **Módulo de Efectos de Estudio y Masterización (`src/engine/effects.py`)**:
  - **Flanger Analógico Estéreo**: LFO sinusoidal estéreo con desfase de 90° para apertura espacial, modulación de retardo, feedback y control de mezcla Dry/Wet.
  - **Filter Sweep Dinámico**: Barrido de filtro bicuadrático progresivo para generar tensión y clímax en subidas.
  - **Voice Drop / Audio Tag con Auto-Ducking Inteligente**: Inserción de firma de voz con atenuación de la pista base (-4 dB) y rampas suaves de 80 ms para inteligibilidad absoluta.
  - **Masterizador LUFS & Limitador Soft**: Normalización comercial a -9.0 LUFS (Club/Beatport) con limitador analógico de codo suave y compresión hiperbólica (`tanh soft-clipping`) a -0.3 dB True Peak.
- **Detección Tonal Armónica y Rueda Camelot (`src/analysis/key.py`)**:
  - Algoritmo Krumhansl-Schmuckler sobre perfiles de cromagrama (12 notas) con correlación de Pearson y confianza estadística.
  - Visualización en panel de estadísticas (`CLAVE / CAMELOT`, ej. `8A · Am`).
  - Inyección automática en metadatos ID3v2 (`TKEY`, `TBPM`) para Pioneer CDJ, Rekordbox, Serato y Traktor.
- **Generador de Vídeos Sociales para TikTok, Reels y Shorts (`src/engine/video.py`)**:
  - Renderizado automático en formato vertical 9:16 (1080x1920) y cuadrado 1:1 con fondo desenfocado atmosférico, carátula nítida central, visualizador interactivo de onda de audio reactivo y cartelería tipográfica.
- **Procesamiento por Lote (Batch Engine) (`src/ui/batch.py`)**:
  - Diálogo especializado para procesar carpetas completas o listas de múltiples canciones.
  - Detección automática al arrastrar varios archivos a la ventana de la aplicación.
- **Modo Bucle Infinito (Loop Mode) en Reproductor (`src/ui/player.py`)**:
  - Botón `🔁` para reproducción continua sin pausas ni clics.
- **Presets Rápidos de Duración**:
  - ⚡ 15s (Teaser / Stories) · 📻 30s (Promo Estándar) · 🚀 60s (Extended Showcase).
- **Formatos Profesionales de Exportación**:
  - WAV 24-bit PCM, MP3 320 kbps con carátula oficial y metadatos ID3 completos, FLAC Lossless, AIFF 24-bit y Vídeo Social MP4.

---

## [1.0.8] - 2026-10-05

### Corregido
- **Liberación de bloqueo de archivo de audio en Windows durante el Selftest**:
  - Corrección de `PermissionError: [WinError 32] El proceso no puede tener acceso al archivo porque está siendo utilizado por otro proceso` al limpiar el directorio temporal al finalizar el selftest en Windows.
  - Cierre y desvinculación explícita de `QMediaPlayer.setSource(QUrl())`, `player.stop()`, destrucción de objetos de reproducción y parámetro de resiliencia `ignore_cleanup_errors=True` en `tempfile.TemporaryDirectory`.
- **Privacidad y Sanitización de Información Personal en Repositorio Público**:
  - Eliminación total de rutas locales absolutas, referencias de usuario y nombres personales en la documentación y banco de pruebas (`progreso.md`, `tests/test_ui_and_export.py`, scripts de build).
  - Estandarización a rutas relativas y denominaciones neutrales de pistas de prueba (`Demo_Club_Track.wav`, `Demo_Track_Remix.wav`).

---

## [1.0.7] - 2026-10-05

### Añadido
- **Estudio de Firma de Audio y Carátula Personalizada (Branding & Artwork Studio)**:
  - Soporte completo de Drag & Drop para imágenes (`.jpg`, `.jpeg`, `.png`, `.webp`) sobre el nuevo widget `CoverDropArea`.
  - Panel `BrandingCard` para firmar temas con metadatos profesionales: Artista / DJ, Sello / Discográfica, Álbum / Colección, Género y Comentarios de promoción.
  - Inyección automática del BPM detectado en la etiqueta oficial ID3 `TBPM`.
  - Normalizador de arte `prepare_cover_art`: convierte y escala cualquier imagen a un JPEG cuadrado RGB optimizado de 1000x1000 px para máxima fidelidad en pantallas de reproductores DJ profesionales (Pioneer CDJ-3000, RX3, Rekordbox, Serato) y smartphones.
  - Opción de persistencia *"Guardar firma y carátula como predeterminada"* para recordar el branding entre aperturas de la app.

### Corregido
- **Carga robusta directa de `llvmlite.dll` en Windows 64-bit**:
  - Parche interceptor en `src/compat.py` sobre `llvmlite.binding.ffi._lib_wrapper._load_lib` para cargar directamente la DLL física con `ctypes.CDLL` desde las rutas de distribución (`dist\AutoPrevias.dist\`), evitando que `importlib.resources` falle en el entorno empaquetado de Nuitka.
- **Repositorio Público y CI/CD Ilimitado**:
  - Repositorio configurado como público en GitHub para desbloquear compilaciones ilimitadas y 100% gratuitas en GitHub Actions sin límites de minutos de facturación.

---

## [1.0.6] - 2026-10-05

### Corregido
- **Activación del backend multimedia de PySide6 para el reproductor integrado (`QMediaPlayer` / `QAudioOutput`)**:
  - Corrección de `Failed to initialize QMediaPlayer: Not available` / `No QtMultimedia backends found` al abrir la aplicación nativa compilada.
  - Inclusión explícita de la familia de plugins `--include-qt-plugins=sensible,multimedia` y `--include-package=PySide6.QtMultimedia` en Nuitka para macOS y Windows.
  - Sincronización y re-enlazado dinámico de `libdarwinmediaplugin.dylib` y `windowsmediaplugin.dll` en `scripts/bundle_runtime_deps.py`.
  - Registro de `QCoreApplication.addLibraryPath` en `src/compat.py` y `src/ui/player.py` para asegurar que Qt descubra inmediatamente los plugins multimedia locales en el bundle ejecutable.
  - Incorporación del paso de diagnóstico `[6/6] Verificando motor de reproducción de audio (QMediaPlayer)` en `run_selftest()` para verificar la inicialización del reproductor antes de crear el instalador.
- **Resolución de carga de `llvmlite.dll` en Windows 64-bit**:
  - Invocación de `os.add_dll_directory` en `src/compat.py` para directorios de DLLs locales en Python 3.8+ Windows.
  - Duplicación de `llvmlite.dll` tanto en el subdirectorio de recursos `llvmlite\binding` como en la raíz de distribución `AutoPrevias.dist\`.

---

## [1.0.5] - 2026-10-05

### Corregido
- **Inclusión de módulos estándar críticos (`uuid`, `dis`, `inspect`, `opcode`) en standalone:**
  - Corrección de `x ERROR EN SELFTEST: No module named 'uuid'` en los ejecutables compilados con Nuitka en macOS y Windows.
  - Al aislar `librosa` de la compilación estática a C, Numba y sus despachadores (`numba.core.dispatcher`) invocan `import uuid` en tiempo de ejecución.
  - Inclusión explícita de `uuid`, `dis`, `inspect` y `opcode` en `src/compat.py` y como argumentos `--include-module` en Nuitka para macOS y Windows, garantizando su presencia nativa dentro del bundle compilado.

---

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
