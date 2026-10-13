# Worker de licencias — «una licencia = un equipo»

`autoprevias-license.js` es el Cloudflare Worker que verifica las claves con Payhip y ata cada
clave a **un único equipo**. No contiene credenciales (todo va en *secrets* de Cloudflare).

## Cómo funciona
| Acción (app) | Qué hace el Worker |
|---|---|
| `activate` (al introducir la clave) | Comprueba la clave con Payhip. Si no está ligada a ningún equipo → la liga a este. Si ya es de **otro** equipo → rechaza (`in_use`). |
| `verify` (cada 7 días, en segundo plano) | Igual, y renueva `last_seen`. Si la clave se activó en otro equipo, este recibe `in_use` y queda bloqueado en el siguiente arranque. |
| `deactivate` (⚙ Licencia → Desactivar) | Libera el hueco para poder activarla en otro equipo. |
| `reset` (solo tú, con `ADMIN_TOKEN`) | Libera una licencia a mano (equipo roto, robo, cliente sin conexión). |

Un equipo que lleva **más de 15 días sin verificar** pierde el hueco automáticamente (la app, de todos modos,
ya se bloquea sola a los 14 días sin conexión), así que un cliente con el PC averiado puede activarla en otro
equipo pasadas dos semanas sin escribirte.

En KV solo se guarda: SHA-256 de la clave, hash del equipo, plataforma y fechas. Nunca la clave en claro ni el correo.

## Despliegue (una sola vez, desde el panel de Cloudflare)
1. **Workers & Pages → KV → Create a namespace** → nombre `autoprevias-licenses`.
2. **Workers & Pages → `autoprevias-license` → Settings → Bindings → Add → KV namespace**:
   variable `LICENSES` → el namespace anterior.
3. **Settings → Variables and Secrets → Add** (tipo *Secret*): `ADMIN_TOKEN` = una cadena larga aleatoria
   (por ejemplo la salida de `openssl rand -hex 32`). Guárdala en tu gestor de contraseñas; no la pegues en el repo.
   Comprueba que siguen existiendo `PAYHIP_SECRET_PLUS` y `PAYHIP_SECRET_BASIC` (con las claves **nuevas** si ya las rotaste).
   `PAYHIP_API_KEY` ya no se usa y se puede borrar.
4. **Edit code** → pega el contenido de `autoprevias-license.js` (sustituye el código anterior) → **Deploy**.
5. Prueba con una licencia de compra real o de prueba (el Worker nuevo acepta también las versiones antiguas de la app).

## Orden de despliegue y migración
- El Worker nuevo **acepta las versiones antiguas** de la app (sin identificador de equipo): no se rompe nada al desplegarlo antes.
- Las versiones nuevas funcionan también con el Worker antiguo (simplemente no hay límite todavía).
- Para **obligar** a actualizar (cuando la mayoría ya tenga la versión nueva): añade la variable `REQUIRE_DEVICE` = `1`.
  Las versiones antiguas recibirán «actualiza AutoPrevias» y no podrán activar licencias nuevas.
  Hasta entonces, quien siga en una versión antigua puede seguir compartiendo su clave.

## Liberar la licencia de un cliente (soporte)
```bash
curl -s -X POST https://autoprevias-license.radicalrecordsvlc.workers.dev \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"action":"reset","license_key":"CLAVE-DEL-CLIENTE"}'
```
(o borra la entrada `lic:<sha256 de la clave>` en el KV desde el panel). El cliente podrá activarla en su equipo nuevo.

## Límites conocidos
- KV es de consistencia eventual (hasta ~60 s entre regiones): dos activaciones simultáneas desde sitios distintos podrían
  colarse las dos. Es un caso extremo; si algún día importa, se pasa a Durable Objects.
- Frena el reparto casual de claves; no puede impedir que alguien parchee el binario.

## Pruebas
`node --test worker/test_worker.mjs` (también se ejecuta desde `pytest`, test `test_worker_js`).
