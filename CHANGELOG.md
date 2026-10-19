# Historial de Cambios — AutoPrevias

Todos los cambios notables de este proyecto se documentarán en este archivo.
El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [4.1.0] - 2026-10-19

### Añadido
- **Plus: «Cómo empieza y cómo acaba la previa», siempre a la vista.** Una tarjeta nueva encima del panel de exportación (ya no está escondida en una pestaña) con dos filas: **ARRANQUE** (efecto de vinilo de 0 al tempo en los segundos que elijas, o directamente a los BPM originales) y **FINAL** (frenazo de vinilo hasta parar en los segundos que elijas, o acabar a los BPM originales, sin frenazo). Se guarda en los presets y en «Reabrir proyecto». En Basic la previa sigue arrancando y acabando con el efecto de vinilo de 1 s.
- **Botones ▶ (oír) y ✕ (quitar) sobre cada corte, en la propia forma de onda**, además de los de la tabla de cortes. ▶ suena el corte desde su inicio hasta su final.

### Corregido
- **En la tabla de cortes no se podía quitar un corte, ni oírlo desde su inicio, ni «tomar la posición» con 📍** (los botones ▶, ✕ y 📍 de los cortes y de los momentos de tempo manual no hacían caso). Ahora funcionan: ✕ quita el corte y renumera el orden y las flechas ▲ ▼ (siempre queda al menos uno), ▶ suena el corte desde su inicio actual hasta su final y 📍 toma la posición del reproductor. También se corrigieron los botones «Firmar tema» y «Pista original / Previa generada», que recibían un valor que no debían.
- **Al pinchar un efecto, la onda de detrás ya no «se bugueaba»:** antes, al seleccionar un efecto aparecía la fila de ajustes y la onda cambiaba de tamaño a mitad del clic, y además el clic movía la reproducción. Ahora la fila de ajustes está siempre en su sitio (apagada si no hay efecto seleccionado) y pinchar un efecto o un botón de corte no mueve el cursor de reproducción.

## [4.0.0] - 2026-10-19

> **Versión 4.** Pasamos a la 4.0 en lugar de la 3.10: incluye todo lo preparado como 3.10 (cortes con nombre, firmar temas, arranque de BPM, notificaciones con logo) y los efectos en la onda.

### Añadido
- **Efectos en la onda (Basic y Plus).** Debajo de la forma de onda aparecen las tarjetas **🌀 Flanger**, **🌊 Filter Sweep ↗** (sube la tensión quitando graves) y **🌊 Filter Sweep ↘** (los graves vuelven poco a poco). **Arrastra una tarjeta hasta la onda** y suéltala donde quieras que suene (o púlsala para ponerla donde está el cursor de reproducción). El efecto se comporta como un corte: **arrástralo para moverlo, estira sus bordes para elegir la duración** y ajusta el **inicio, la duración y la intensidad** en la fila de ajustes que aparece al seleccionarlo. Mientras arrastras ves el hueco que ocupará y se ajusta solo al pulso más cercano. **Supr** (o clic derecho) borra el seleccionado y **Quitar todos** limpia la onda. Si dos efectos se solapan, se ven en dos filas.
- El efecto se queda pegado a su trozo del tema: si cambias el orden de los cortes sigue sonando en ese mismo trozo. Lo que queda **fuera de los cortes** se ve apagado y no suena. Los efectos se guardan con el proyecto («Reabrir proyecto») pero no en los presets, porque pertenecen a cada tema.
- El recorrido de bienvenida tiene un paso nuevo, «Efectos en la onda» (con un efecto de ejemplo), y los manuales PDF Basic y Plus lo explican.
- **Orden y nombres de los cortes (Basic y Plus).** Cada corte se crea con su nombre: **Corte 1, Corte 2, Corte 3…** (el nombre no cambia aunque cambies el orden). Con **▲ ▼** decides en qué orden suenan en la previa (por ejemplo, que el drop suene primero). La forma de onda y la tabla muestran el orden y el nombre. La edición **Basic** ahora tiene la casilla **«✂ Ordenar y mover cortes»**.
- **Dónde empieza la previa (Basic y Plus).** Dos botones, **⏮ Al inicio del tema** y **⏺ A mitad del tema**, colocan el primer corte donde quieras (siempre ajustado a un compás). Y puedes **arrastrar el primer corte** sobre la onda hasta cualquier punto.
- **Plus: arranque de la previa a tu gusto.** En la pestaña «Variación de BPM», la fila **ARRANQUE** te deja elegir entre el **efecto de vinilo** (el disco arranca de 0 BPM al tempo del tema en los segundos que pongas, por defecto 1 s) o **empezar directamente a los BPM originales**. Se guarda en los presets y en «Reabrir proyecto». Sin tocar nada, la previa suena exactamente igual que antes.
- **Plus: «🖋 Firmar tema»** — una ventana nueva para firmar **canciones enteras, no previas**. Arrastras el tema (o varios), eliges la carátula y las etiquetas y se guarda en **FLAC o WAV a máxima calidad**: sin masterización, sin efectos, sin cambiar volumen ni duración (el audio queda idéntico, con la misma frecuencia de muestreo y bits que el original, hasta 24 bits). Los temas se guardan en una carpeta «Firmados» y nunca pisan el original.
- **Más animaciones:** las tarjetas de BPM y de drops cuentan hasta su valor, los botones de duración aparecen en cascada, los paneles de vídeo, opciones avanzadas y cortes se despliegan y pliegan en vez de saltar, la tarjeta de éxito aparece con un fundido, y la ventana de firmar y el recorrido de bienvenida también. Con el ajuste «Ahorro de recursos» se desactivan.
- El recorrido de bienvenida explica las funciones nuevas (firmar temas, orden de cortes, arranque).

### Cambiado
- **Ya no hay efectos automáticos:** desaparecen las casillas **Flanger** y **Filter Sweep** que se aplicaban solas 5 segundos antes de cada drop. Ahora tú eliges qué efecto y dónde. En Plus se mantiene **Master LUFS** en las opciones avanzadas. (Flanger y Filter Sweep antes eran solo de Plus; ahora también están en Basic.)
- **Las notificaciones salen con el logo de AutoPrevias** (el mismo icono de la aplicación) y, **al pulsarlas, se abre la carpeta donde está la previa**. Texto: «Previa “…” generada · pulsa para abrir». Lo mismo al terminar un lote o al firmar temas.

### Corregido
- **Las previas en WAV ahora llevan carátula y etiquetas** (artista, sello, BPM, tonalidad…). Antes solo las llevaban el MP3 y el FLAC.
- Los botones pequeños de la tabla de cortes (▶, 📍, ✕) se veían vacíos; ahora se ven.

## [3.9.0] - 2026-10-14

### Añadido
- **Recorrido de bienvenida (solo la primera vez).** Al abrir AutoPrevias por primera vez en una instalación nueva, aparece un aviso con dos botones: **«Hacer el recorrido»** u **«Omitir»**. No se vuelve a preguntar nunca más. Si lo haces, la app oscurece la ventana y te va resaltando, paso a paso y con ejemplos, **toda la app**: carga del tema, Recientes, Lote y Vigilar carpeta (Plus), licencia e idioma, la forma de onda, el reproductor, las tarjetas de BPM y tonalidad, la duración de la previa, los presets, la edición de cortes y BPM (Plus), los formatos, el vídeo animado (formato, estilo, título, imagen propia, final y vista previa), los efectos, Voice Drop, modo promo y firma (Plus), la carpeta de destino, el botón Generar y la semilla. Para enseñarte el panel de resultados real carga una **pista de ejemplo** sintética; no se guarda nada (ni en Recientes ni en tu carpeta) y tus ajustes quedan como estaban.
- Se maneja con **Siguiente / Atrás** o con las teclas **→ ← Intro Espacio**, y puedes salir en cualquier momento con **Omitir recorrido** o **Esc**. En la edición **Basic** solo enseña lo que tiene Basic.
- Si quieres repetirlo, hay un botón **«Ver recorrido de bienvenida»** en la ventana **⚙ Licencia**.
- El recorrido está en castellano y en inglés, y los manuales PDF lo explican.

## [3.8.0] - 2026-10-14

### Añadido
- **Ajuste «Rendimiento»** en «⚙ Licencia»: **Automático** (recomendado: se adapta a tu equipo y deja un núcleo libre para que la app siga fluida), **Ahorro de recursos** (usa pocos recursos: portátil con batería, equipo antiguo u otros programas abiertos) o **Máximo rendimiento** (usa todos los núcleos). Debajo se ve cuántos núcleos y cuánta memoria detecta la app en tu equipo.

### Cambiado
- **El análisis de tu canción es mucho más rápido** (en las pruebas, de unos 45 s a unos 20 s en una pista de 2:30 con un equipo de 4 núcleos; con más núcleos, más). Los resultados son exactamente los mismos: BPM, tonalidad, secciones y previa idénticos. La app calcula a la vez cosas que son independientes y deja de repetir un cálculo que antes hacía dos veces.
- **El vídeo animado se genera más rápido** (en las pruebas, unas 2,4 veces con 3 núcleos; más con más núcleos). El vídeo resultante es idéntico fotograma a fotograma.
- **La app consume menos y va más fluida en reposo:** el brillo animado de la etiqueta de edición y el pulso del cursor de la forma de onda ya no repintan la pantalla sin parar cuando no hacen falta (el brillo hace un barrido cada pocos segundos y el pulso solo corre mientras reproduces o buscas).

## [3.7.0] - 2026-10-14

### Añadido
- **Plus: «Looks» de un clic.** Un selector con aspectos listos para el vídeo: *Neón clásico*, *Foto + barras abajo*, *Foto + círculo en el centro*, *Foto y título* y *Solo la foto*. Los looks de foto usan tu imagen (si no has elegido ninguna, te la pide) y conservan las que ya tenías.
- **Plus: arrastra una imagen sobre la tarjeta del vídeo** y se usa de fondo al instante. Si la imagen tiene otro formato válido (9:16, 1:1 o 16:9), el vídeo cambia solo a ese formato; si no es ninguno, te avisa y te muestra ejemplos.
- **Plus: vista previa en vivo** en la ventana «Personalizar…»: ves cómo queda el vídeo mientras cambias fondo, onda, textos y posiciones, y puedes alternar entre los tres formatos.
- **Resumen antes de generar**: justo encima del botón, una línea dice qué se va a crear (formatos, vídeo, duración de la previa, efectos activos y carpeta).
- **Basic: se ven las opciones de Plus**, bloqueadas con un candado («Tu imagen de fondo, onda de sonido y final a medida: solo en Plus»), para que sepas qué ganas al pasar a Plus; al pulsarlo se abre la página de compra.

### Cambiado
- **Panel de exportación más claro y ordenado en pasos:** ① Nombre y formatos, ② Vídeo animado, ③ Opciones avanzadas.
- **Todo el vídeo en una sola tarjeta:** el formato se elige con **tres botones** (9:16 Vertical, 1:1 Cuadrado, 16:9 Horizontal) en lugar de un desplegable, y junto a él están el color, el título, el final y la vista previa.
- **Opciones avanzadas plegables (Plus):** efectos de estudio, Voice Drop, Modo promo y la firma/carátula están agrupados y plegados para que el panel quede limpio. Se abren solos en cuanto activas algo de ellas (por ejemplo, un efecto o tu voz) y recuerdan si los dejaste abiertos; la línea de la sección te avisa de qué hay activo aunque esté plegada.

## [3.6.0] - 2026-10-14

### Añadido
- **Plus: vídeo con tu propia imagen.** Nuevo botón **«🖼 Estilo del vídeo…»** para elegir entre la plantilla Neón de siempre o **tu foto de fondo** con un zoom lento. Puedes poner **una imagen distinta para cada formato** (9:16, 1:1 y 16:9) o una sola para todos, y decidir si se **recorta** para rellenar la pantalla o se muestra **entera sobre un fondo desenfocado**.
- **Plus: onda de sonido a tu gusto.** Mostrarla u ocultarla; en **barras, línea o círculo**; abajo, en el centro o arriba; con los colores de la paleta Neón o en blanco. También puedes colocar los textos (título, artista, BPM y tonalidad) arriba, en el centro o abajo, o quitarlos.
- **Plus: aviso si la imagen no tiene el formato del vídeo.** Los vídeos son 9:16, 1:1 o 16:9. Si eliges una imagen con otra proporción (por ejemplo 4:3), AutoPrevias te avisa de que el formato no es correcto, te muestra **ejemplos de los tres formatos** y te deja cambiarla (o usarla igualmente, y se recortará o se verá con fondo desenfocado). Junto a cada imagen verás si el formato es correcto y si la resolución es baja. Si cambias de formato después de elegir la imagen, también te avisa al generar.
- **Plus: elige qué textos se ven** (título, artista, BPM y tonalidad, etiqueta «Previa exclusiva») o **solo la foto**: sin textos, sin onda y sin banner, solo tu imagen con el zoom lento.
- **Plus: final con tu imagen.** Nueva opción «Final: mi imagen»: el vídeo termina con la foto que elijas (tu logo, el cartel del sello…) y un texto opcional debajo.
- Los ajustes del vídeo se recuerdan y se guardan en los presets de estilo, y la **vista previa** los muestra antes de generar.

### Cambiado
- **Basic ya puede elegir el final del vídeo** entre la firma «Generado por AutoPrevias · Radical Records» con el enlace o un **fundido a negro**. La marca de agua pequeña se mantiene.
- Los manuales PDF de Basic y Plus explican las nuevas opciones.

## [3.5.1] - 2026-10-13

### Añadido
- **Cada clave solo sirve para su edición**: una clave de **Basic** no activa AutoPrevias **Plus**, y una de **Plus** no activa **Basic**. Si te equivocas de instalador, la app te lo dice con claridad y te indica dónde descargar el correcto, y la clave no queda ligada a ningún equipo.

### Corregido
- **Tu licencia ya no se marca como inválida si el servicio de licencias falla un momento**: antes, una caída puntual de Payhip al comprobar la licencia podía hacer que la app te pidiera la clave de nuevo. Ahora se reintenta sola más tarde y no tienes que escribir nada.
- **Si una versión anterior había marcado tu licencia como no válida por error, se corrige sola al abrir la app** (se comprueba con el servidor antes de pedirte la clave).

## [3.5.0] - 2026-10-13

### Añadido
- **La edición Basic también genera vídeo animado**: con las plantillas Radical Neón (formatos 9:16, 1:1 y 16:9, las cinco paletas, título propio y vista previa), hecho a partir de la previa en MP3. En Basic el vídeo lleva siempre una **marca de agua pequeña y translúcida** abajo a la derecha («Generado por Radical Records · AutoPrevias Basic») y termina con el cierre «Generado por AutoPrevias · Radical Records» con el enlace de compra.
- **En Plus, el final del vídeo a tu elección**: nuevo selector «Final» con tres opciones: cierre con la firma de AutoPrevias y el enlace, **fundido a negro** o **sin cierre** (corte seco). Tu elección se recuerda y se guarda en los presets de estilo.

### Cambiado
- La edición **Plus** exporta el vídeo **sin marca de agua**.
- Los manuales PDF de Basic y Plus explican las diferencias del vídeo entre ediciones.

## [3.4.0] - 2026-10-13

### Añadido
- **Vista previa del vídeo antes de generarlo**: junto al campo «Título» hay un botón «👁 Vista previa». Muestra en una ventana unos segundos del vídeo (a baja resolución y con sonido), con tu título, paleta de color, formato, banner y carátula, y el cierre con la firma de Radical Records. Así compruebas cómo queda sin esperar a la exportación completa. La muestra sale del momento del primer drop de tu pista.

### Cambiado
- **El vídeo siempre exporta también el MP3**: como el vídeo se hace a partir de la previa, al marcar «🎬 Vídeo animado» la casilla del MP3 se marca y queda bloqueada (en la exportación normal y en el Lote), de modo que nunca se pide un vídeo sin previa.

## [3.3.1] - 2026-10-13

### Añadido
- **Título del vídeo a tu gusto**: al marcar «🎬 Vídeo animado» aparece un campo «Título» para escribir el nombre que sale en el centro del vídeo (por ejemplo, el nombre artístico del tema). Si lo dejas vacío se usa el nombre de la pista.

- **Cierre con firma**: el vídeo animado termina ahora con el logo de Radical Records, la frase «Generado por AutoPrevias · Radical Records» y el enlace de compra (payhip.com/RADICALRECVLC), y el cierre dura un poco más para que dé tiempo a leerlo.

### Corregido
- En el vídeo animado el título salía como «Previa» en lugar del nombre real de la pista. Ahora sale el nombre del archivo (sin el «PREVIA - » del principio) o el que tú escribas.

## [3.3.0] - 2026-10-13

### Añadido
- **Vídeo animado «Radical Neón»**: el vídeo para redes sociales se ha rediseñado por completo. Ahora es una pieza animada con el estilo Radical Records: tu **carátula** con resplandor neón, título, artista, BPM y tonalidad, un **analizador de espectro** que baila con la música, destellos que golpean con el bombo, un golpe especial cuando entra el drop y tu texto de banner. Se exporta en los tres formatos: **9:16** (TikTok / Reels), **1:1** (Instagram) y **16:9** (YouTube).
- Nuevo formato **16:9 (YouTube / horizontal)** en el selector de formato del vídeo.

### Cambiado
- La casilla del vídeo pasa a llamarse «🎬 Vídeo animado (TikTok/Reels/YouTube)».
- La paleta por defecto del vídeo es ahora Rojo Carmesí (puedes cambiarla cuando quieras). Las cinco paletas (Cian y Magenta, Verde Rave, Carmesí, Ámbar y Cyber Violet) funcionan con el nuevo vídeo.
- Si por cualquier motivo no se pudiera crear el vídeo animado, la app genera el vídeo clásico en su lugar para que la exportación nunca falle.
- Los manuales PDF (Basic y Plus) explican el nuevo vídeo y están actualizados a esta versión.

## [3.2.0] - 2026-10-13

### Añadido
- **Una licencia = un equipo.** Si tu licencia ya está activa en un ordenador, no se puede activar en otro hasta que la desactives allí (⚙ Licencia → «Desactivar licencia en este equipo») o pasen 15 días sin que ese equipo se conecte. Así tu clave no se puede compartir.
- Mensajes claros en español e inglés cuando la licencia está en uso en otro equipo, cuando no hay conexión o cuando la clave ya no es válida.

### Cambiado
- «Desactivar licencia» ahora **libera la clave en el servidor** para poder usarla en tu otro equipo (si no hay conexión, te lo avisa y te deja reintentar).
- Tu clave se guarda en el equipo cifrada y ligada a él: copiar el archivo de licencia a otro ordenador no sirve.

### Corregido
- La licencia se reverificaba solo «en teoría»: tras 14 días la app volvía a pedir la clave. Ahora la app se verifica sola con el servidor en cada arranque y cada 6 horas, en segundo plano y sin volver a pedirte nunca la clave. Si pasa más de 14 días sin conexión, la verifica al abrirse (y solo te pide conexión, no la clave). Si el servidor revoca la licencia mientras trabajas, te avisa y se cierra al terminar de exportar.

## [3.1.0] - 2026-10-12

### Añadido
- **Modo promo antifugas (Plus)**: nueva casilla «🛡️ Modo promo» junto al Voice Drop. Repite tu firma de voz cada pocos segundos (tú eliges cada cuántos, por defecto 20 s) sobre toda la previa y la exporta solo en MP3 de 128 kbps con la nota «PROMO — NO DISTRIBUIR» en las etiquetas. Así la previa es inservible para reutilizarla sin tu firma. La app avisa si todavía no has elegido tu audio de firma, y al desactivar el modo recuperas tus formatos de exportación.
- **Presets de firma y de estilo (Plus)**: guarda con nombre (por ejemplo «Radical Main» o «Set de Verano») tu firma (artista, sello, álbum, género, comentario y carátula) y/o tu estilo (duración, formatos, efectos, voice drop, modo promo y vídeo). Se aplican con un clic desde la nueva barra «MIS PRESETS», junto a los presets de duración. Cada preset es un archivo, así que se puede copiar a otro ordenador.
- **Panel «Recientes» renovado**: ahora muestra tus previas generadas (fecha, pista, duración, BPM, formatos y si eran promo) con reproductor rápido, «Mostrar archivo», «Reabrir proyecto» (carga la pista original con los mismos ajustes y la misma seed para regenerar exactamente la misma previa) y «Quitar de la lista». Incluye también la pestaña de pistas abiertas recientemente. El historial de previas generadas es una función Plus.
- **Pantalla «Licencia y ajustes»**: nuevo botón «⚙ Licencia» con la versión, la edición, el estado de tu licencia (ID, última verificación y hasta cuándo es válida sin conexión), buscador manual de actualizaciones y la opción de desactivar la licencia en este equipo para poder activarla en otro.
- **Interfaz en inglés**: nuevo botón «ES/EN» en la cabecera (y selector en «Licencia y ajustes») para cambiar el idioma al instante. **AutoPrevias siempre arranca en castellano** salvo que elijas inglés; la elección se recuerda para la próxima vez. Incluye la forma de onda, los avisos, la ventana de actualización y la de activación.

### Cambiado
- Las novedades de la ventana de actualización se muestran ahora con títulos y viñetas en lugar de texto sin formato, sin enlaces ni direcciones de internet.
- Los botones «Cambiar» y «Abrir» de la carpeta de destino ya no aparecen cortados.
- La comprobación interna que se ejecuta antes de publicar cada versión ahora también abre las pantallas nuevas (presets, historial, licencia y modo promo) para evitar publicar instaladores que se cierren al usarlas.

## [3.0.1] - 2026-10-12

### Cambiado
- **La actualización ya no te lleva a ninguna página web**: al aceptar, AutoPrevias descarga el instalador directamente en tu carpeta de Descargas, comprueba que no está dañado y lo abre. Si algo falla (sin conexión, archivo dañado), te lo dice en la propia ventana y puedes pulsar *Reintentar*; nunca se abre un navegador ni se muestran direcciones de internet.

## [3.0.0] - 2026-10-12

### Añadido
- **Sistema de licencias plenamente operativo**: la activación con clave de Payhip funciona de forma fiable (incluye las correcciones de la serie 2.9).
- **Actualizaciones automáticas con ventana propia**: al abrir AutoPrevias comprueba si hay una versión nueva. Si la hay, aparece una ventana con las novedades y tres opciones: *Descargar e instalar*, *Más tarde* u *Omitir esta versión*. La app descarga el instalador que corresponde a tu sistema y a tu edición (Basic o Plus), muestra el progreso y comprueba que el archivo no está dañado antes de abrirlo. Al pulsar *Instalar y cerrar AutoPrevias* se abre el instalador y la app se cierra para poder actualizarse.
- Si por cualquier motivo no se puede descargar o verificar el instalador, la ventana te lleva a la página de descargas en vez de instalar algo dudoso.

### Corregido
- **La app se cerraba sola justo después de activar la licencia**: el instalador se estaba construyendo con una versión nueva del compilador que generaba un programa inestable al abrir la ventana principal (el visor de forma de onda). Se fija la versión del compilador que funcionaba y se añade una comprobación automática que impide publicar un instalador que se cierre al abrir esa ventana.
- **El aviso de nueva versión llevaba a un enlace roto**: la dirección de descarga tenía un error tipográfico. Ahora el aviso de la parte inferior abre la ventana de actualización.
- La comprobación de versiones ya no depende de un componente externo que podía faltar en el instalador.

## [2.9.7] - 2026-10-12

### Corregido
- **Por fin se acepta la clave de licencia**: el servidor de licencias rechazaba las peticiones de la app por la forma en que se identificaba ante Cloudflare (no tenía nada que ver con los certificados). Ahora la app se identifica correctamente y la activación funciona.
- **La app se cerraba de golpe al pulsar "Activar licencia"**: la versión 2.9.6 incluía un componente de certificados que provocaba un cierre inesperado. Se ha eliminado por completo.

## [2.9.6] - 2026-10-12

### Corregido
- **La clave de licencia seguía sin aceptarse en macOS (v2.9.5 insuficiente)**: el intento anterior de cargar los certificados SSL del sistema no era suficiente en todos los entornos. Ahora se utiliza el paquete `certifi`, que incluye su propio bundle de certificados de confianza directamente en el instalador. La verificación de licencia funciona de forma fiable en macOS sin depender de la configuración del sistema.

## [2.9.5] - 2026-10-12

### Corregido
- **La clave de licencia siempre mostraba "Clave no válida o sin conexión" en macOS**: en los instaladores compilados con Nuitka, el proceso de verificación HTTPS no encontraba el paquete de certificados SSL del sistema, haciendo que la conexión al servidor de licencias fallara en silencio aunque la clave fuese correcta. Ahora se carga explícitamente el certificado raíz del sistema (`/etc/ssl/cert.pem`) y la verificación funciona correctamente.

## [2.9.4] - 2026-10-12

### Corregido
- **La app arrancaba pero se cerraba sin mostrar la pantalla de activación**: un import obsoleto (`PRODUCT_IDS`) en el código de arranque causaba un error silencioso que saltaba la pantalla de activación y dejaba la edición sin inicializar, provocando un cierre inmediato. Ahora el flujo de activación funciona correctamente al arrancar.
- **Diagnóstico mejorado de inicio de interfaz**: se añaden mensajes de log más detallados durante la construcción de la ventana principal para facilitar la identificación de problemas en futuras compilaciones.

## [2.9.3] - 2026-10-12

### Corregido
- **Activación de licencia fallaba siempre en los instaladores**: la app compilada (v2.9.1–v2.9.2) seguía usando el código antiguo que enviaba un campo `product_id` que el nuevo Worker ya no acepta. Ahora solo se envía `license_key` y el Worker gestiona internamente la verificación contra los productos Basic y Plus.

## [2.9.2] - 2026-10-08

### Corregido
- **Verificación de licencia siempre fallaba con "clave no válida"**: la API de Payhip requiere la URL completa del producto (`https://payhip.com/b/XXXXX`) en el campo `product_link`, no solo el código corto. Al enviar únicamente el código, Payhip no encontraba el producto y rechazaba todas las claves. Ahora se envía la URL completa correctamente.

## [2.9.1] - 2026-10-08

### Cambiado
- **Diálogo de activación con identidad visual**: colores rojos de la app, logo oficial de AutoPrevias y campo de clave con fuente monoespaciada.
- **Enlace de compra directo**: el botón "Obtener licencia" abre `payhip.com/RADICALRECVLC`.
- **Reverificación cada 7 días** con período de gracia de 14 días sin conexión.

## [2.9.0] - 2026-10-08

### Añadido
- **Sistema de licencias completo**: al arrancar la app en versión compilada, se verifica la licencia contra los servidores de Payhip a través de un proxy Cloudflare Worker seguro. Si no hay licencia activada, aparece una pantalla de activación donde el usuario introduce su clave de compra. Las claves de Basic y Plus desbloquean cada edición automáticamente.
- **Período de gracia de 14 días**: si no hay conexión a internet, la app funciona hasta 14 días desde la última verificación exitosa, sin interrumpir el trabajo.
- **Verificación cada 7 días**: la licencia se reverifica en segundo plano cada 7 días de forma silenciosa.

## [2.8.2] - 2026-10-08

### Corregido
- **WAV con firma y carátula completa**: el archivo WAV exportado ahora incrusta todos los metadatos (artista, sello, álbum, BPM, clave, carátula) igual que el MP3. Antes salía sin ninguna etiqueta.

### Cambiado
- **Edición Básica sin sección de Firma**: los campos de artista, sello, álbum y carátula quedan ocultos en la edición Básica — esta opción es exclusiva de Plus.
- **Edición Básica sin efectos de estudio**: los efectos Flanger, Filter Sweep y Master LUFS quedan ocultos en la edición Básica — son exclusivos de Plus.

## [2.8.1] - 2026-10-08

### Cambiado
- **Auto-update simplificado**: el comprobador de versiones ahora consulta directamente la API pública de GitHub, eliminando la necesidad del proxy Cloudflare Worker. Requiere que el repositorio sea público (ya lo es).

## [2.8.0] - 2026-10-08

### Añadido
- **Corrección manual de BPM (doble clic)**: haz doble clic sobre la tarjeta de BPM en el panel de resultados para introducir el BPM real del track. El motor usa el valor corregido al generar la siguiente previa, sin necesidad de reanalizar.
- **Notificaciones nativas del sistema operativo**: al terminar una exportación (individual o por lote), el sistema operativo muestra una notificación emergente con el nombre del archivo exportado. Funciona en macOS y Windows.
- **Informe de lote exportado automáticamente**: al completar el modo Lote, se genera un fichero `autoprevias_lote_YYYYMMDD_HHMMSS.txt` en la misma carpeta de destino con el resumen de archivos producidos.
- **Sistema de actualizaciones automáticas**: la app comprueba al arrancar si existe una versión nueva (usando un proxy Cloudflare Worker que oculta el repositorio privado). Si hay actualización disponible, aparece un banner discreto en la parte inferior de la ventana con un enlace directo a la descarga.
- **Registro de fallos con rotación**: los errores no capturados se guardan automáticamente en un archivo de log con rotación automática (máx. 3 ficheros de 512 KB). Ubicación: `~/Library/Logs/AutoPrevias/crashes.log` en macOS, `%LOCALAPPDATA%\AutoPrevias\logs\crashes.log` en Windows.

## [2.7.0] - 2026-10-08

### Añadido
- **FLAC y AIFF con firma completa**: los archivos FLAC y AIFF exportados ahora incluyen todos los metadatos (artista, sello, álbum, género, comentario, BPM, clave) y la carátula incrustada, igual que el MP3. Hasta ahora salían completamente vacíos de etiquetas.
- **Procesamiento por lote con firma**: los temas generados desde el modo Lote (batch) ahora utilizan el artista, sello, álbum y género guardados en la sección de Firma, en lugar de usar siempre "Radical Records Studio".
- **FX recordados entre sesiones**: los ajustes de Flanger, Filter Sweep y Master LUFS se guardan automáticamente y se restauran al cargar un nuevo tema.

### Corregido
- **Firma y carátula no se recordaban entre sesiones**: al cerrar y abrir la app, los campos de artista, sello, álbum, género y comentario aparecían vacíos aunque el usuario los hubiera rellenado antes. Ahora se guardan siempre al generar una previa, sin necesidad de marcar "Recordar".
- **Carpeta de destino incorrecta en edición Básica**: la tarjeta de éxito mostraba una carpeta interna de caché del sistema como destino en lugar de la carpeta real del usuario.
- **Archivo interno aparecía en el listado de archivos generados**: el archivo temporal `autoprevias_temp_XXX.wav` aparecía junto a los archivos reales en la notificación de exportación completada.
- **Edición Básica exportaba WAV sin metadatos**: el checkbox de WAV estaba oculto pero activo en Básica, generando un archivo sin tags que confundía al usuario. Ahora Básica solo exporta MP3.
- **Año del copyright hardcodeado a 2026**: en 2027 y siguientes todos los MP3 tendrían fecha incorrecta. Ahora usa el año del sistema.
- **Carpeta vigilada detectaba el mismo archivo dos veces en macOS**: en sistemas de archivos sin distinción de mayúsculas, `*.wav` y `*.WAV` devolvían el mismo archivo, causando doble procesamiento ocasional.
- **Timer de brillo del playhead no se detenía al cerrar**: el timer de 45ms seguía activo tras destruir el widget, pudiendo causar un crash al acceder a memoria liberada.
- **Guardar configuración podía corromperse**: si la app se cerraba a mitad de escritura del archivo de ajustes, el JSON quedaba incompleto y se perdían todas las preferencias. Ahora escribe a un archivo temporal y hace un reemplazo atómico.
- **Configuración corrupta fallaba silenciosamente**: si el JSON de ajustes estaba dañado, la app lo ignoraba sin aviso. Ahora muestra un mensaje en consola y guarda una copia de seguridad `.bak` antes de usar los valores por defecto.

### Cambiado
- **Configuración por defecto más completa**: añadidos los valores iniciales para todos los ajustes que antes faltaban (`export_flac`, `export_video`, `aspect_ratio`, `fx_flanger`, `fx_filter_sweep`, `studio_mastering`), evitando inconsistencias en instalaciones nuevas.

## [2.6.2] - 2026-10-07

### Corregido
- **Ventana fantasma de "Vinilo" en macOS (fix definitivo)**: la corrección anterior (eliminar `processEvents`) no era suficiente. La causa raíz era que `QSplashScreen.finish()` llamaba internamente a `winId()` en macOS para inicializar los handles nativos antes de que la ventana principal fuera visible, lo que hacía aparecer el popup nativo del `QComboBox`. Ahora la ventana se muestra explícitamente primero (`win.show()`) y el splash se cierra 80ms después mediante un temporizador, evitando por completo la inicialización prematura de controles nativos.
- **Email de soporte tapado por el badge de edición**: el header aumenta de 58px a 72px para que todos los elementos del panel derecho (logo, estado, badge y email) quepan sin solaparse.
- **Edición Básica no arrancaba correctamente**: el splash no se cerraba porque el evento `QEvent::Show` se perdía con el orden anterior de `win.show()` + `splash.finish()`. Resuelto con el nuevo patrón `win.show()` + cierre por temporizador.

## [2.6.1] - 2026-10-07

### Añadido
- **Animación de tarjetas de estadísticas**: al cargar un tema, las 6 tarjetas (BPM, clave, drops, etc.) aparecen con un efecto de fundido escalonado en lugar de mostrarse todas de golpe.
- **Filas de tabla de cortes animadas**: al regenerar los cortes, cada fila de la tabla aparece de forma escalonada de arriba a abajo.
- **Brillo pulsante en el playhead**: la línea roja del reproductor en la waveform pulsa sutilmente mientras hay audio cargado, dando más vida a la interfaz.

### Corregido
- **Ventana fantasma de "Vinilo" en macOS**: al abrir la app, aparecía una pequeña ventana flotante con el texto del combo "Vinilo (+Pitch Armónico)". Corregido eliminando el `processEvents()` que inicializaba los controles nativos de macOS antes de que la ventana principal estuviera visible.

## [2.6.0] - 2026-10-07

### Añadido
- **Pantalla de bienvenida animada (Splash Screen)**: al abrir la app aparece el logo de Radical Records con barra de progreso y mensajes de estado mientras carga el motor de audio.
- **Pantalla de análisis animada**: al cargar un archivo, en lugar de mostrar la zona de arrastre estática, se muestra el logo de RR pulsando/escalando con barra de progreso en tiempo real. Mucho más informativo y visual.
- **Botón "← Nuevo track" siempre visible** en la barra de presets del panel de resultados — ya no hay que desplazarse hasta el final para cargar otro tema.
- **Cache de hardware**: al primer inicio se guardan los specs del PC (CPU, cores, RAM, plataforma) en `hw_cache.json` para futuras optimizaciones automáticas.

### Cambiado
- **Badge de edición Plus/Básica más prominente**: gradiente de color, tipografía más grande (10px → mayor peso visual) y padding ampliado para que se vea más profesional.
- **Badge "PRO STUDIO" con versión real**: muestra la versión instalada actual en lugar de un número fijo (`v2.0` → `v2.6.0`), así el usuario siempre sabe qué versión tiene.

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
