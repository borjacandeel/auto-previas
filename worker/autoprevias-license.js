/**
 * AutoPrevias — Cloudflare Worker de licencias (una licencia = un equipo).
 *
 * Bindings / variables (Cloudflare → Worker → Settings):
 *   PAYHIP_SECRET_PLUS   (secret)   product-secret-key del producto Plus
 *   PAYHIP_SECRET_BASIC  (secret)   product-secret-key del producto Basic
 *   ADMIN_TOKEN          (secret)   token largo y aleatorio para liberar una licencia a mano (action "reset")
 *   LICENSES             (KV namespace) clave → equipo  [ver worker/README.md]
 *   REQUIRE_DEVICE       (variable, opcional) "1" = rechaza las versiones antiguas de la app sin identificador de equipo
 *   STALE_DAYS           (variable, opcional) días sin verificar tras los que otro equipo puede tomar la licencia (15)
 *
 * Petición (POST JSON): { action, license_key, device_id, platform }
 *   action: "activate" | "verify" | "deactivate" | "reset" (reset requiere cabecera Authorization: Bearer ADMIN_TOKEN)
 * Respuesta (siempre JSON):
 *   { success: true, edition: "basic"|"plus" }
 *   { success: false, code: "invalid"|"in_use"|"not_owner"|"update_required"|"bad_request"|"unauthorized", error }
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

/** Pregunta a Payhip. Devuelve "plus" | "basic" | null. Plus primero (como antes). */
async function payhipEdition(key, env) {
  const products = [["plus", env.PAYHIP_SECRET_PLUS], ["basic", env.PAYHIP_SECRET_BASIC]];
  for (const [edition, secret] of products) {
    if (!secret) continue;
    try {
      const r = await fetch("https://payhip.com/api/v2/license/verify?license_key=" + encodeURIComponent(key), {
        headers: { "product-secret-key": secret, "User-Agent": "AutoPrevias-License-Worker/2.0" },
      });
      if (!r.ok) continue;
      const body = await r.json();
      if (body && !body.error && body.data && body.data.enabled === true) return edition;
    } catch (_) { /* siguiente producto */ }
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
    const edition = await payhipEdition(key, env);
    if (!edition) return fail("invalid", "Clave no válida");

    // — Versiones antiguas de la app (sin identificador de equipo) —
    if (!device) {
      if (env.REQUIRE_DEVICE === "1") return fail("update_required", "Actualiza AutoPrevias para activar tu licencia");
      return json({ success: true, edition, legacy: true });
    }
    if (!DEVICE_RE.test(device)) return fail("bad_request", "Identificador de equipo no válido", 400);

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
          if (!mine) return fail("invalid", "Servicio de licencias temporalmente no disponible; inténtalo más tarde");
        }
      }
      return json({ success: true, edition });
    }
    return fail("in_use", "Esta licencia ya está activada en otro equipo");
  },
};
