# Instalar el Worker nuevo en Cloudflare (copiar y pegar)

> **Seguridad:** el `ADMIN_TOKEN` es una contraseña tuya. Se genera en tu Mac y se pega directamente en Cloudflare:
> **no se escribe en el chat, ni en el repo, ni en ningún archivo.** Guárdalo en tu gestor de contraseñas.
> El Worker, su dirección (`autoprevias-license.radicalrecordsvlc.workers.dev`) y los secrets de Payhip **ya existen: no se crea nada nuevo**.

Tiempo total: ~10 minutos. Hazlo **en este orden**.

---

## Paso 0 · Copia de seguridad del Worker actual (1 min)
1. https://dash.cloudflare.com → **Workers & Pages** → **autoprevias-license**.
2. Pulsa **Edit code**, selecciona todo (⌘A), copia (⌘C) y pégalo en un archivo `worker_license_ANTIGUO.txt` en tu Mac.
   *(Además Cloudflare guarda versiones en la pestaña **Deployments**, desde donde se puede volver atrás.)*
3. Cierra el editor **sin cambiar nada todavía**.

## Paso 1 · Crear el KV (la «libreta» donde se anota qué equipo usa cada licencia) (1 min)
1. Menú izquierdo → **Storage & Databases** → **KV** (en algunos paneles: *Workers & Pages → KV*).
2. **Create a namespace** → nombre (cópialo tal cual):
   ```
   autoprevias-licenses
   ```
3. **Add**.

## Paso 2 · Enlazar el KV al Worker (1 min)
1. **Workers & Pages → autoprevias-license → Settings → Bindings → Add → KV namespace**.
2. **Variable name** (exactamente, en mayúsculas):
   ```
   LICENSES
   ```
3. **KV namespace** → elige `autoprevias-licenses` → **Save / Deploy**.

## Paso 3 · Crear el `ADMIN_TOKEN` (2 min)
1. En **Terminal** del Mac, pega esta línea (genera un token aleatorio y lo deja **en el portapapeles**; no lo muestra):
   ```bash
   openssl rand -hex 32 | tr -d '\n' | pbcopy && echo "Token copiado al portapapeles (guárdalo en tu gestor de contraseñas)"
   ```
2. En Cloudflare: **autoprevias-license → Settings → Variables and Secrets → Add**.
   - **Type:** `Secret`
   - **Variable name:** `ADMIN_TOKEN`
   - **Value:** pega con ⌘V
   - **Deploy**.
3. **Ahora, antes de copiar otra cosa**, pega el token también en tu gestor de contraseñas (⌘V).
4. Comprueba que en esa misma lista existen `PAYHIP_SECRET_PLUS` y `PAYHIP_SECRET_BASIC` (no los toques).
   `PAYHIP_API_KEY`, si aparece, ya no se usa: puedes borrarla.

## Paso 4 · Pegar el código nuevo (2 min)
1. Abre este enlace, selecciona todo (⌘A) y copia (⌘C):
   https://raw.githubusercontent.com/borjacandeel/auto-previas/main/worker/autoprevias-license.js
   *(o usa el archivo `autoprevias-license.js` que te envié)*
2. Cloudflare → **autoprevias-license → Edit code** → selecciona **todo** lo que hay (⌘A) → pega (⌘V) → **Deploy**.
3. Debe quedar en la primera línea un comentario `/** AutoPrevias — Cloudflare Worker de licencias…`.

## Paso 5 · Probarlo (2 min)
En Terminal, en la carpeta del proyecto (`cd` a tu copia de `auto-previas` y `git pull`). Pega estas **tres** líneas, una a una
(las dos primeras te piden el valor sin mostrarlo ni guardarlo en el historial):
```bash
read -rs -p "Pega tu ADMIN_TOKEN: " ADMIN_TOKEN; echo; export ADMIN_TOKEN
read -rs -p "Pega una clave de licencia de PRUEBA real de Payhip: " LICENSE_KEY; echo; export LICENSE_KEY
bash worker/smoke_test.sh
```
**Resultado esperado:** `Resultado: 11 correctas, 0 fallidas`.
Al terminar, la clave de prueba queda libre. Cierra la terminal (o `unset ADMIN_TOKEN LICENSE_KEY`).

Si algo falla, copia la salida del script (no contiene tokens) y mándamela.

## Paso 6 · Aviso y publicación
Cuando el Paso 5 dé `11 correctas, 0 fallidas`, dímelo y publico la versión **3.2.0**.

---

## Cuando todo esté estable (más adelante)
- Cuando casi todos los clientes tengan la 3.2.0: Cloudflare → **Settings → Variables and Secrets → Add** → tipo *Text*,
  nombre `REQUIRE_DEVICE`, valor `1`. Las versiones antiguas dejarán de poder activar licencias nuevas.

## Rotar las claves de Payhip (recomendado, urgente: estuvieron en el historial público)
1. En Payhip, en cada producto (Basic y Plus), regenera la **product secret key** (en la sección de claves de licencia del producto).
2. Cloudflare → **Settings → Variables and Secrets** → edita `PAYHIP_SECRET_BASIC` y `PAYHIP_SECRET_PLUS` con los valores nuevos → **Deploy**.
3. Regenera/revoca la licencia de prueba antigua y crea una nueva para el Paso 5.
4. Repite el Paso 5 para comprobar que todo sigue funcionando.

## Soporte: liberar la licencia de un cliente (cambio de ordenador, PC roto…)
```bash
read -rs -p "ADMIN_TOKEN: " ADMIN_TOKEN; echo
curl -s -X POST https://autoprevias-license.radicalrecordsvlc.workers.dev \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"action":"reset","license_key":"CLAVE-DEL-CLIENTE"}'; echo
unset ADMIN_TOKEN
```
Debe responder `{"success":true,"released":true}`. El cliente podrá activarla en su equipo nuevo.
(Sin tocar nada, un equipo que lleva más de 15 días sin conectarse también pierde la licencia solo.)

## Si algo sale mal: volver atrás
Cloudflare → **autoprevias-license → Deployments** → versión anterior → **Rollback**; o pega el contenido de `worker_license_ANTIGUO.txt`.
(El Worker antiguo funciona con las apps nuevas; simplemente no limita equipos.)
