# AutoPrevias — Handoff para agente cloud
> Generado el 2026-10-12 al final de la sesión 35.
> **IMPORTANTE:** Este archivo NO contiene valores de credenciales. Los secrets reales están almacenados en Cloudflare (cifrados) y en la memoria local de Claude (`~/.claude/projects/.../memory/`).

---

## 1. Archivos locales no commiteados

### `src/_edition.py` (en .gitignore — NO se commitea)
Ruta: `/Users/borjacandel/Documents/AutoPrevias/src/_edition.py`
Contenido actual:
```python
BAKED_EDITION = "basic"
```
**Propósito:** Simula un build compilado para poder probar el sistema de licencias en desarrollo sin compilar con Nuitka. En CI, este archivo se genera automáticamente antes de compilar con el valor `"basic"` o `"plus"` según el job. **No borrar mientras se hagan pruebas de licencias.** Borrar solo cuando no se necesite probar el flujo de activación localmente.

### `worker_license.txt` (en .gitignore — NO se commitea)
Ruta: `/Users/borjacandel/Documents/AutoPrevias/worker_license.txt`
Copia en Downloads: `/Users/borjacandel/Downloads/worker_license.txt`

**Propósito:** Código del Cloudflare Worker para verificación de licencias. Se excluye del repo porque aunque no contiene credenciales directamente (usa `env.PAYHIP_SECRET_BASIC` / `env.PAYHIP_SECRET_PLUS`), es código de infraestructura sensible.

**Contenido resumido del Worker:** Acepta POST `{ license_key }`, prueba Plus primero (con `env.PAYHIP_SECRET_PLUS`) y luego Basic (con `env.PAYHIP_SECRET_BASIC`) llamando a `GET https://payhip.com/api/v2/license/verify?license_key=XXX` con header `product-secret-key: <secret>`. Devuelve `{ success: true, edition: "plus"|"basic", email, uses }` o `{ success: false, error: "..." }`.

---

## 2. Credenciales y secrets — dónde están

**NUNCA escribir valores reales en código o archivos commiteados.**

| Secret | Dónde está | Descripción |
|--------|-----------|-------------|
| `PAYHIP_SECRET_BASIC` | Cloudflare Worker → Settings → Variables and Secrets | Product secret key del producto Basic en Payhip |
| `PAYHIP_SECRET_PLUS` | Cloudflare Worker → Settings → Variables and Secrets | Product secret key del producto Plus en Payhip |
| `PAYHIP_API_KEY` | Cloudflare (puede borrarse — ya no se usa) | Era el API Key de cuenta; Payhip NO lo acepta para licencias |

**⚠️ Estado actual (2026-10-12):** El Worker en Cloudflare AÚN NO ha sido actualizado con el nuevo código ni con los nuevos secrets. Está pendiente que el usuario lo haga manualmente. Hasta que lo haga, todas las activaciones de licencia fallarán.

---

## 3. Configuración de Cloudflare

- **Dashboard:** https://dash.cloudflare.com
- **Nombre del Worker:** `autoprevias-license`
- **URL del Worker:** `https://autoprevias-license.radicalrecordsvlc.workers.dev`
- **URL codificada en base64 (usada en `src/licensing/license.py`):**
  `aHR0cHM6Ly9hdXRvcHJldmlhcy1saWNlbnNlLnJhZGljYWxyZWNvcmRzdmxjLndvcmtlcnMuZGV2`

**Secrets que deben existir en el Worker (nombres, no valores):**
- `PAYHIP_SECRET_BASIC`
- `PAYHIP_SECRET_PLUS`

**Cómo navegar en Cloudflare:**
Workers & Pages → `autoprevias-license` → Edit code (para pegar el nuevo worker)
Workers & Pages → `autoprevias-license` → Settings → Variables and Secrets (para los secrets)

---

## 4. Estado del entorno local

- **Python del sistema:** 3.14.6
- **Python del .venv:** 3.11 (`/Users/borjacandel/Documents/AutoPrevias/.venv/lib/python3.11/`)
- **Activar venv:** `source .venv/bin/activate`
- **Dependencias clave instaladas en .venv:**
  - PySide6 6.7.3
  - librosa 0.11.0
  - pedalboard 0.9.25
  - soundfile 0.12.1
  - numpy 2.0.2 / scipy 1.14.1
  - pytest 9.1.1
- **Para correr tests:** `source .venv/bin/activate && pytest tests/ -q`
- **Para lanzar la app en dev:** `source .venv/bin/activate && python src/main.py`
- **Para simular build compilado (activar licencias en dev):** Asegurarse de que `src/_edition.py` existe con `BAKED_EDITION = "basic"` o `"plus"`

---

## 5. Tests manuales realizados en sesión 35 y sus resultados

### Test 1 — Verificación con API Key de cuenta (FALLA esperada)
```bash
curl -X POST "https://payhip.com/api/v2/license/verify" \
  -H "Authorization: Bearer <api_key_cuenta>" \
  -H "Content-Type: application/json" \
  -d '{"license_key":"...", "product_link":"https://payhip.com/b/NVkaK"}'
# Resultado: {"code":"authentication_fail","message":"failed to authenticate","success":false}
# Conclusión: Payhip NO acepta API Key de cuenta para verificar licencias
```

### Test 2 — Verificación directa con product-secret-key (ÉXITO)
```bash
curl -G "https://payhip.com/api/v2/license/verify" \
  -d "license_key=<clave_plus>" \
  -H "product-secret-key: <prod_secret_plus>"
# Resultado: {"data":{"enabled":true,"product_link":"mTjEL","license_key":"...","buyer_email":"[correo-del-comprador-redactado]","uses":0,...},"error":false}
# Conclusión: La clave del usuario es válida de tipo PLUS
```

### Test 3 — Worker antiguo (FALLA esperada)
```bash
curl -X POST "https://autoprevias-license.radicalrecordsvlc.workers.dev" \
  -H "Content-Type: application/json" \
  -d '{"license_key":"...", "product_id":"https://payhip.com/b/NVkaK"}'
# Resultado: {"code":"authentication_fail","message":"failed to authenticate","success":false}
# Conclusión: Worker antiguo usa Bearer token que Payhip rechaza
```

### Test 4 — Tests automáticos
```bash
pytest tests/ -q
# Resultado: 30/30 passed, 4 warnings
```

---

## 6. Contexto técnico y decisiones de sesión

### Por qué falló la autenticación Payhip (root cause)
La documentación oficial de Payhip v2 distingue dos tipos de autenticación:
- **`payhip-api-key` header:** Para endpoints de cuenta (cupones, productos, etc.)
- **`product-secret-key` header:** Para verificación de licencias — es una clave **por producto**, no de cuenta

El Worker original usaba `Authorization: Bearer <api_key_cuenta>` — formato incorrecto para este endpoint. Payhip siempre lo rechaza independientemente del valor de la clave.

La `product-secret-key` se obtiene en Payhip → producto → Edit → sección de License Keys.

### Formato correcto de la API de Payhip para licencias
```
GET https://payhip.com/api/v2/license/verify?license_key=XXXX
Headers: product-secret-key: prod_sk_<productCode>_<secret>
Respuesta éxito: {"data": {"enabled": true, "product_link": "...", "buyer_email": "...", "uses": 0, ...}}
Respuesta fallo: {"data": [], "error": true}
```

### Decisión de diseño: Worker prueba ambas ediciones automáticamente
El usuario introduce solo la clave (sin saber si es Basic o Plus). El Worker itera Plus → Basic y devuelve la edición que corresponda. Así la app no necesita saber qué producto es — solo recibe `{ success: true, edition: "plus" }`.

### Cosas que se intentaron y no funcionaron
- `Authorization: Bearer <api_key>` → authentication_fail
- `Api-Key: <api_key>` header → authentication_fail
- `api_key` en body JSON → authentication_fail
- `api_key` en form-data → authentication_fail
- GET con `?api_key=` → authentication_fail
- API v1 endpoint → authentication_fail
- Basic auth (`-u "api_key:"`) → authentication_fail
Todas las variantes fallaron porque Payhip simplemente no acepta el API Key de cuenta en el endpoint de licencias.

### Versión publicada actual vs. estado del código
- **v2.9.2** está en GitHub Releases — tiene `license.py` corregido pero el Worker en Cloudflare no está actualizado
- Cuando el usuario actualice Cloudflare → bump a **v2.9.3** + CI → instaladores funcionales

### Producto comprado por el usuario en Payhip
- Cuenta: `[correo-del-comprador-redactado]`
- Producto: **AutoPrevias Plus** (`mTjEL`)
- La clave es válida y devuelve `enabled: true` cuando se verifica correctamente

---

## Próximos pasos ordenados

1. **[BLOQUEANTE] Usuario actualiza Cloudflare Worker:**
   - Pegar código de `worker_license.txt` en el editor del Worker
   - Añadir secrets `PAYHIP_SECRET_BASIC` y `PAYHIP_SECRET_PLUS`
   - Borrar `PAYHIP_API_KEY` (obsoleto)

2. **[Agente] Verificar Worker actualizado:**
   ```bash
   curl -s -X POST "https://autoprevias-license.radicalrecordsvlc.workers.dev" \
     -H "Content-Type: application/json" \
     -d '{"license_key":"<clave_usuario>"}'
   # Debe devolver: {"success":true,"edition":"plus",...}
   ```

3. **[Agente] Bump v2.9.2 → v2.9.3 + CI:**
   - `src/__version__.py` → `"2.9.3"`
   - Entrada en `CHANGELOG.md`
   - Badge en `README.md`
   - Commit + tag + push → CI compila 4 instaladores

4. **[Usuario] Probar v2.9.3 con .command launcher:**
   - Asegurarse de que `src/_edition.py` existe
   - Lanzar `AutoPrevias_Plus.command`
   - Introducir la clave → debe activar correctamente
