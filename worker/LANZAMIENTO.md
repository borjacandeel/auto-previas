# Lanzamiento público — qué tocar en Payhip, el Worker y Cloudflare

Resumen: el Worker **no usa el enlace de la tienda**; solo usa las *product-secret-key* de cada producto para
preguntar a Payhip si una clave de licencia es válida. Por eso hacer públicos los productos **no obliga a tocar
nada en Cloudflare**, salvo que al hacerlo público se **creen productos nuevos** (otro producto = otra clave secreta).

## Caso A — los productos son los mismos y solo cambia su visibilidad (lo normal)
- Cloudflare / Worker: **no hay que cambiar nada** (misma URL del Worker, mismos secrets, mismo KV).
- Si el enlace de la tienda cambia: `python scripts/launch_public.py <enlace> --apply` (lo ejecuta Claude) → versión PATCH.
- Comprobar tras publicar: compra de prueba (Payhip permite un cupón del 100 %), activar la clave en la app y ver
  en Payhip → licencias que figura «1 uso».

## Caso B — se crean productos NUEVOS (otro enlace de producto)
1. En Payhip, en cada producto nuevo, copia su **product secret key** (en los ajustes de licencias del producto).
2. Cloudflare → Workers & Pages → `autoprevias-license` → **Settings → Variables and Secrets**:
   - `PAYHIP_SECRET_PLUS`  = `clave-plus-nueva`   → si quieres que sigan valiendo las licencias del producto antiguo:
     `clave-plus-antigua,clave-plus-nueva` (separadas por una coma, sin espacios; el Worker admite varias).
   - `PAYHIP_SECRET_BASIC` = igual con la de Basic.
3. **Deploy** el Worker con el código actual de `worker/autoprevias-license.js` si aún no tiene el soporte de varias claves
   (se añadió el 2026-10-13). Copia el archivo con `curl` o desde el chat; **desactiva la traducción de Chrome** al pegar.
4. Prueba: `LICENSE_KEY="clave-de-un-producto-nuevo" ADMIN_TOKEN="..." bash worker/smoke_test.sh` → `11 correctas, 0 fallidas`.
5. Los clientes que ya compraron en el producto antiguo siguen funcionando mientras su clave antigua esté en la lista.

## Recomendado el día del lanzamiento (opcional)
- `REQUIRE_DEVICE` = `1` (Settings → Variables): las versiones antiguas de la app (sin identificador de equipo) dejan de
  poder activar licencias nuevas y así nadie puede compartir clave con una versión vieja. Hazlo cuando todos tus
  probadores estén en la 3.2.0 o posterior.
- Vigilar el plan gratuito de Cloudflare (Workers 100.000 peticiones/día, KV 1.000 escrituras/día): alcanza para
  varios cientos de licencias activas al día. Si el lanzamiento va muy bien, el plan de pago cuesta unos 5 USD/mes.
- Dejar tal cual `ADMIN_TOKEN`, el namespace KV `LICENSES` y la URL del Worker: la app lleva la URL integrada.

## Orden del día D (lo que pasa en cuanto me pases el enlace)
1. `python scripts/launch_public.py <enlace>` (simulación) y luego `--apply`: enlace, versión PATCH, CHANGELOG, README, PDF.
2. Re-render de los vídeos que vayas a subir primero (≈4 min cada uno) y de los demás en segundo plano.
3. Commit + push + CI → te aviso cuando el instalador esté listo para que lo pruebes.
4. Tú: ficha de Payhip, precio final y, si procede, Caso B en Cloudflare.
