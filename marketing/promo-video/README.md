# Vídeo promocional de AutoPrevias (9:16 · 32 s · Radical Records)

Anuncio vertical para TikTok / Reels / Shorts hecho con **HyperFrames** (HTML + GSAP → MP4):
gancho «¿Cansado de hacer tus previas a mano?», una app manejada por un puntero animado sobre
**capturas reales** de AutoPrevias, motion blur, glitch y música/efectos sintetizados a 128 BPM.
La llamada final remite a la tienda de Radical Records en Payhip (nunca al repositorio).

## Regenerarlo (cuando cambie la interfaz o la versión)
```bash
python scripts/manual/capture.py plus          # capturas reales + rectángulos de los botones
cd marketing/promo-video
python build_assets.py                          # capturas, logos, tipografía, grano
python build_audio.py                           # música y efectos (choreo.json = tiempos)
python build_html.py                            # ensambla index.html (src/ + motion-blur)
npx hyperframes@0.8.151 check                   # lint + layout + contraste
npx hyperframes@0.8.151 render -o renders/AutoPrevias-Promo-9x16.mp4
```
Los tiempos de clics, golpes y whooshes viven en `choreo.json`; los lee tanto el audio como la animación.
