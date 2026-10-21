/**
 * AutoPrevias — Cloudflare Worker de licencias (una licencia = un equipo).
 *
 * Bindings / variables (Cloudflare → Worker → Settings):
 *   PAYHIP_SECRET_PLUS   (secret)   product-secret-key del producto Plus (varias separadas por comas si hay productos antiguos y nuevos)
 *   PAYHIP_SECRET_BASIC  (secret)   product-secret-key del producto Basic
 *   ADMIN_TOKEN          (secret)   token largo y aleatorio para liberar una licencia a mano (action "reset")
 *   LICENSES             (KV namespace) clave → equipo  [ver worker/README.md]
 *   PAYHIP_PRODUCTS      (secret, opcional) JSON con productos de duración limitada:
 *                        [{"secret":"<product-secret-key>","edition":"plus","days":365}, {"secret":"...","edition":"basic","days":90}]
 *                        `days` admite decimales (1/1440 = 1 minuto, para pruebas). Sin `days` (o 0) = licencia permanente.
 *   DAYS_PLUS / DAYS_BASIC (variable, opcional) días de duración de los productos de PAYHIP_SECRET_PLUS / PAYHIP_SECRET_BASIC (por defecto permanentes)
 *   LEGACY_BEFORE        (variable, opcional) fecha ISO: las claves compradas ANTES son permanentes aunque su producto ahora caduque
 *   OWN_KEYS             (secret, opcional) claves propias permanentes (no son de Payhip, no se cobran): "RR-PLUS-AAAA-BBBB:plus,RR-BAS-CCCC-DDDD:basic"
 *   REQUIRE_DEVICE       (variable, opcional) "1" = rechaza las versiones antiguas de la app sin identificador de equipo
 *   STALE_DAYS           (variable, opcional) días sin verificar tras los que otro equipo puede tomar la licencia (15)
 *
 * Petición (POST JSON): { action, license_key, device_id, platform, app_edition? }
 *   app_edition ("basic"|"plus"): edición del instalador; si la clave es de otra, responde code "wrong_edition" sin ligarla a ningún equipo
 *   action: "activate" | "verify" | "deactivate" | "reset" (reset requiere cabecera Authorization: Bearer ADMIN_TOKEN)
 * Respuesta (siempre JSON):
 *   { success: true, edition: "basic"|"plus", expires_at?: <ms epoch> }   (expires_at ausente = permanente)
 *   { success: false, code: "expired", edition, expires_at }              (la licencia temporal ya caducó)
 *   { success: false, code: "invalid"|"unavailable"|"wrong_edition"|"expired"|"in_use"|"not_owner"|"update_required"|"bad_request"|"unauthorized", error }
 *
 * Privacidad: en KV solo se guarda el SHA-256 de la clave, el hash del equipo, la plataforma y fechas.
 * Nunca se guarda ni se devuelve el correo del comprador.
 */

const DAY = 86400000;
const WRITE_EVERY_MS = 12 * 3600 * 1000;
const KEY_RE = /^[A-Z0-9][A-Z0-9-]{6,63}$/;
const DEVICE_RE = /^[a-f0-9]{64}$/;

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
const fail = (code, error, status = 200) => json({ success: false, code, error }, status);

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

/**
 * Pregunta a Payhip. Devuelve { edition: "plus"|"basic"|null, unavailable: bool }.
 * `unavailable` = Payhip no dio una respuesta fiable (caída, 5xx, 429, 401/403, red): en ese caso NUNCA se
 * dice "clave no válida" (la app revocaría una licencia buena), se responde "unavailable" y el cliente reintenta.
 */
async function payhipEdition(key, env) {
  // Cada edición admite varias product-secret-key separadas por comas (p. ej. producto antiguo + producto nuevo al relanzar la tienda)
  const list = (v) => String(v || "").split(",").map((x) => x.trim()).filter(Boolean);
  const num = (v) => { const n = parseFloat(v); return Number.isFinite(n) && n > 0 ? n : 0; };
  const products = [];   // [edition, secret, days]  (days 0 = permanente)
  for (const sec of list(env.PAYHIP_SECRET_PLUS)) products.push(["plus", sec, num(env.DAYS_PLUS)]);
  for (const sec of list(env.PAYHIP_SECRET_BASIC)) products.push(["basic", sec, num(env.DAYS_BASIC)]);
  try {
    for (const p of JSON.parse(env.PAYHIP_PRODUCTS || "[]")) {
      if (p && p.secret && (p.edition === "plus" || p.edition === "basic")) products.push([p.edition, String(p.secret), num(p.days)]);
    }
  } catch (_) { /* PAYHIP_PRODUCTS mal formado: se ignora, no se rompe el resto */ }
  let unavailable = products.length === 0;
  for (const [edition, secret, days] of products) {
    try {
      const r = await fetch("https://payhip.com/api/v2/license/verify?license_key=" + encodeURIComponent(key), {
        headers: { "product-secret-key": secret, "User-Agent": "AutoPrevias-License-Worker/2.0" },
      });
      if (!r.ok) {
        if (![400, 404, 422].includes(r.status)) unavailable = true;   // respuesta definitiva de "no existe" vs. fallo del servicio
        continue;
      }
      const body = await r.json();
      if (body && !body.error && body.data && body.data.enabled === true) {
        const bought = Date.parse(body.data.date);
        return { edition, days, boughtAt: Number.isFinite(bought) ? bought : null, unavailable: false };
      }
    } catch (_) { unavailable = true; /* siguiente producto */ }
  }
  return { edition: null, days: 0, boughtAt: null, unavailable };
}

/** Claves propias permanentes (OWN_KEYS = "CLAVE:plus,CLAVE:basic"). */
function ownEdition(key, env) {
  for (const item of String(env.OWN_KEYS || "").split(",")) {
    const [k, ed] = item.split(":").map((x) => (x || "").trim());
    if (k && k.toUpperCase() === key && (ed === "plus" || ed === "basic")) return ed;
  }
  return null;
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return fail("bad_request", "Método no permitido", 405);
    let body;
    try { body = await request.json(); } catch (_) { return fail("bad_request", "JSON no válido", 400); }

    const action = String(body.action || "activate");
    const key = String(body.license_key || "").trim().toUpperCase();
    const device = body.device_id ? String(body.device_id).toLowerCase() : "";
    if (!KEY_RE.test(key)) return fail("invalid", "Clave no válida");
    const kvKey = "lic:" + (await sha256Hex(key));
    const now = Date.now();

    // — Liberación manual por el administrador (equipo roto, robo, etc.) —
    if (action === "reset") {
      const auth = request.headers.get("Authorization") || "";
      if (!env.ADMIN_TOKEN || !safeEqual(auth, "Bearer " + env.ADMIN_TOKEN)) return fail("unauthorized", "No autorizado", 401);
      await env.LICENSES.delete(kvKey);
      return json({ success: true, released: true });
    }

    // — Comprobación con Payhip (clave real, activa y de qué edición) —
    const own = ownEdition(key, env);
    const found = own ? { edition: own, days: 0, boughtAt: null, unavailable: false } : await payhipEdition(key, env);
    const { edition, unavailable } = found;
    if (!edition) {
      if (unavailable) return fail("unavailable", "Servicio de licencias temporalmente no disponible; inténtalo más tarde", 503);
      return fail("invalid", "Clave no válida");
    }

    // — La clave debe ser de la misma edición que la app instalada (Basic con Basic, Plus con Plus) —
    const appEdition = String(body.app_edition || "").toLowerCase();
    if (action !== "deactivate" && (appEdition === "basic" || appEdition === "plus") && appEdition !== edition) {
      return json({ success: false, code: "wrong_edition", edition, error: "Esta clave es de otra edición" });
    }

    // — Versiones antiguas de la app (sin identificador de equipo) —
    if (!device) {
      if (env.REQUIRE_DEVICE === "1") return fail("update_required", "Actualiza AutoPrevias para activar tu licencia");
      return json({ success: true, edition, legacy: true });
    }
    if (!DEVICE_RE.test(device)) return fail("bad_request", "Identificador de equipo no válido", 400);

    // — Caducidad (solo licencias temporales): se cuenta desde la primera activación y NO se reinicia al desactivar/reactivar —
    let expiresAt = null;
    if (found.days > 0 && (action === "activate" || action === "verify")) {
      const legacyBefore = Date.parse(env.LEGACY_BEFORE || "");
      const legacy = Number.isFinite(legacyBefore) && found.boughtAt !== null && found.boughtAt < legacyBefore;
      if (!legacy) {
        const startKey = "start:" + (await sha256Hex(key));
        let start = await env.LICENSES.get(startKey, "json");
        if (!start && action === "activate") {
          start = { at: now, days: found.days };
          try { await env.LICENSES.put(startKey, JSON.stringify(start)); }
          catch (_) { return fail("unavailable", "Servicio de licencias temporalmente no disponible; inténtalo más tarde", 503); }
        }
        if (start) {
          expiresAt = start.at + found.days * DAY;
          if (now >= expiresAt) return json({ success: false, code: "expired", edition, expires_at: expiresAt, error: "La licencia ha caducado" });
        }
      }
    }
    const withExp = (o) => (expiresAt ? { ...o, expires_at: expiresAt } : o);

    const bound = await env.LICENSES.get(kvKey, "json");
    const staleMs = (parseInt(env.STALE_DAYS, 10) || 15) * DAY;
    const mine = bound && bound.device === device;
    const stale = bound && !mine && now - (bound.last_seen || 0) > staleMs;

    if (action === "deactivate") {
      if (!bound || mine) {
        if (bound) await env.LICENSES.delete(kvKey);
        return json({ success: true });
      }
      return fail("not_owner", "Esta licencia está activa en otro equipo");
    }
    if (action !== "activate" && action !== "verify") return fail("bad_request", "Acción desconocida", 400);

    // — Una licencia = un equipo —
    if (!bound || mine || stale) {
      // El plan gratuito de KV permite 1.000 escrituras al día: solo se escribe al ligar/cambiar de equipo
      // o, como mucho, cada 12 h para refrescar last_seen (las lecturas, 100.000 al día, no importan).
      const needsWrite = !bound || stale || bound.edition !== edition || now - (bound.last_seen || 0) > WRITE_EVERY_MS;
      if (needsWrite) {
        try {
          await env.LICENSES.put(kvKey, JSON.stringify({
            device,
            edition,
            platform: String(body.platform || "").slice(0, 16),
            activated_at: mine ? bound.activated_at : now,
            last_seen: now,
          }));
        } catch (_) {
          // Cuota de KV agotada o fallo puntual: no se bloquea al cliente que ya está en regla
          if (!mine) return fail("unavailable", "Servicio de licencias temporalmente no disponible; inténtalo más tarde", 503);
        }
      }
      return json(withExp({ success: true, edition }));
    }
    return fail("in_use", "Esta licencia ya está activada en otro equipo");
  },
};
