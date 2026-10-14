# AutoPrevias · Todo lo implementado desde el lunes 12 de octubre de 2026

Radical Records · versiones 2.9.3 → 3.9.0 (la 3.9.0 está terminada y pendiente de publicar)

## Lunes 12 de octubre — Licencias y actualizaciones (2.9.x → 3.1.0)
- **Licencias operativas** con clave de Payhip (2.9.3–2.9.7): arreglados los fallos de conexión en macOS (certificados SSL, cabecera propia ante Cloudflare) y un cierre inesperado al pulsar «Activar».
- **v3.0.0 — Actualizaciones automáticas con ventana propia**: avisa de la versión nueva con sus novedades (*Descargar e instalar / Más tarde / Omitir esta versión*), descarga el instalador de tu sistema y edición, comprueba que no está dañado (SHA-256) y lo abre.
- **v3.0.0 — Arreglo del cierre tras activar**: se fija la versión del compilador (Nuitka 4.2.2) y el *selftest* abre la ventana principal antes de publicar.
- **v3.0.1 — La actualización no abre ninguna web**: descarga directa a Descargas, con reintento si falla.
- **v3.1.0 — Modo promo antifugas (Plus)**: repite tu firma de voz cada pocos segundos y exporta solo MP3 128 kbps con la nota «PROMO — NO DISTRIBUIR».
- **v3.1.0 — Presets de firma y de estilo (Plus)**: guardados como archivos, aplicables con un clic.
- **v3.1.0 — «Recientes» renovado**: historial de previas con reproductor rápido, «Mostrar archivo», **«Reabrir proyecto»** (mismos ajustes y misma semilla) y «Quitar de la lista».
- **v3.1.0 — Ventana «⚙ Licencia y ajustes»** (versión, edición, estado de la licencia, buscar actualizaciones, desactivar).
- **v3.1.0 — Interfaz en inglés** (botón ES/EN; arranca siempre en castellano).
- **Manuales PDF Basic y Plus** con capturas reales de la app, regenerados en cada versión.
- **Vídeo promocional** de AutoPrevias (9:16) hecho con HyperFrames.
- El repositorio pasa a ser **público** (decisión del usuario) y se retiran los secretos de la documentación.

## Martes 13 de octubre — Licencias seguras, vídeo animado y marketing (3.2.0 → 3.5.1)
- **v3.2.0 — Una licencia = un equipo**: la clave no se puede compartir; se libera con «Desactivar licencia», con reset de administrador o a los 15 días sin conexión. Clave guardada cifrada y ligada al equipo.
- **v3.2.0 — Verificación automática**: la app se revalida sola al arrancar y cada 6 horas; hasta 14 días sin conexión; nunca vuelve a pedir la clave.
- **Servidor de licencias** en Cloudflare (Worker + KV), desplegado y probado, con guías de instalación.
- **v3.3.0 — Vídeo animado «Radical Neón»** para TikTok, Reels y YouTube: carátula con resplandor, espectro que baila, destellos con el bombo y golpe en el drop; formatos **9:16, 1:1 y nuevo 16:9**; 5 paletas.
- **v3.3.1 — Título del vídeo a elegir** y **cierre con firma** «Generado por AutoPrevias · Radical Records» y enlace de compra.
- **v3.4.0 — Vista previa del vídeo** antes de generarlo; el vídeo siempre exporta también el MP3.
- **v3.5.0 — Basic también genera vídeo** (con marca de agua pequeña y cierre fijo); **Plus sin marca de agua** y con el **final a elegir** (firma, fundido a negro o sin cierre).
- **v3.5.1 — Cada clave solo sirve para su edición** (Basic no activa Plus y viceversa) y una caída de Payhip ya no invalida la licencia.
- **11 vídeos de marketing** producidos con voces de España (Álvaro y Ximena), música y efectos sincronizados, y el plan de marketing.
- **Enlaces de compra centralizados** y *scripts* para el día de lanzamiento (cambiar el enlace de Payhip en app, PDF, vídeos y README, subir versión, regenerar PDF).

## Miércoles 14 de octubre — Vídeo a medida, panel fácil, rendimiento y recorrido (3.6.0 → 3.9.0)
- **v3.6.0 — Vídeo con tu propia imagen (Plus)**: fondo con tu foto (una por formato), recorte o fondo desenfocado, **onda de sonido** en barras, línea o círculo (posición y color), textos a elegir o **solo la foto**, **final con tu imagen**. **Basic** elige el final entre la firma o fundido a negro.
- **v3.6.0 — Aviso de formato de imagen**: si no es 9:16, 1:1 o 16:9, la app avisa y muestra ejemplos de formatos válidos.
- **v3.7.0 — Panel de vídeo más fácil**: tarjeta única con **botones de formato**, **looks de un clic** (Neón clásico, foto + barras, foto + círculo, foto y título, solo la foto), **arrastrar una imagen** sobre la tarjeta, **vista previa en vivo** al personalizar, **resumen antes de generar**, **opciones avanzadas plegables** y Basic viendo lo de Plus bloqueado con candado.
- **v3.7.0 — La onda ya no pisa los textos** (se recoloca en el hueco libre en los tres formatos).
- **v3.8.0 — Análisis hasta ~2× más rápido y vídeo hasta ~2,4× más rápido**, con **resultados idénticos** (BPM, tonalidad, secciones, fotogramas).
- **v3.8.0 — Ajuste «Rendimiento»** (Automático / Ahorro / Máximo) en ⚙ Licencia, y **menos consumo en reposo**.
- **v3.9.0 — Recorrido de bienvenida (solo la primera vez)**: oferta «Hacer el recorrido / Omitir»; recorre **toda la app** con ejemplos (36 pasos en Plus, 25 en Basic) usando una pista de ejemplo que no deja rastro; teclado → ← Intro Espacio, Esc para salir; ES/EN; repetible desde ⚙ Licencia.
- **Manuales PDF ampliados** con el panel de vídeo, rendimiento y el recorrido.
- **README** actualizado en cada versión (características, tabla de ediciones, historial).
- **Vídeo tutorial 16:9 de generación de vídeos (Plus)**: ~7 min 34 s, 31 escenas, voces Álvaro y Ximena, con ejemplos para usar el 100 % de las funciones desde cero (en renderizado al escribir esto).

## Pendiente (pedido, sin implementar)
- Notificación del sistema cada vez que se genere una previa, con el logo de la app, «AutoPrevias · Previa X generada, pulsa para abrir», y abrir la carpeta al pulsarla.
