// Licencias temporales del Worker (KV y fetch simulados, reloj controlado):  node --test worker/test_worker_expiry.mjs
import test from "node:test";
import assert from "node:assert/strict";
import worker from "./autoprevias-license.js";

const KEY = "ABCD-1234-EFGH-5678";
const DEV_A = "a".repeat(64);
const DEV_B = "b".repeat(64);
const MIN = 60000, DAY = 86400000;

function makeKV() {
  const m = new Map();
  return { m, get: async (k) => (m.has(k) ? JSON.parse(m.get(k)) : null), put: async (k, v) => void m.set(k, v), delete: async (k) => void m.delete(k) };
}
let bought;      // fecha de compra que devuelve "Payhip"
let owner;       // secreto del producto al que pertenece la clave
globalThis.fetch = async (url, init) => {
  const secret = init.headers["product-secret-key"];
  if (secret !== owner) return new Response("{}", { status: 404 });
  return new Response(JSON.stringify({ error: false, data: { enabled: true, license_key: KEY, uses: 0, date: new Date(bought).toISOString() } }), { status: 200 });
};
let clock = Date.parse("2026-11-01T10:00:00Z");
Date.now = () => clock;
const call = async (env, body, headers = {}) =>
  (await worker.fetch(new Request("https://w/", { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) }), env)).json();
const makeEnv = (extra = {}) => ({
  PAYHIP_SECRET_PLUS: "plus-3m", PAYHIP_SECRET_BASIC: "basic-3m", DAYS_PLUS: "90", DAYS_BASIC: "90",
  PAYHIP_PRODUCTS: JSON.stringify([{ secret: "plus-12m", edition: "plus", days: 365 }, { secret: "plus-test", edition: "plus", days: 1 / 1440 }]),
  ADMIN_TOKEN: "t".repeat(40), LICENSES: makeKV(), ...extra });
test.beforeEach(() => { clock = Date.parse("2026-11-01T10:00:00Z"); bought = clock; owner = "plus-3m"; });

test("licencia de 1 minuto: vale al activar, a los 59 s y caduca al minuto", async () => {
  owner = "plus-test"; const env = makeEnv();
  const a = await call(env, { action: "activate", license_key: KEY, device_id: DEV_A });
  assert.equal(a.success, true); assert.equal(a.edition, "plus"); assert.equal(a.expires_at, clock + MIN);
  clock += 59000;
  assert.equal((await call(env, { action: "verify", license_key: KEY, device_id: DEV_A })).success, true);
  clock += 1000;
  const v = await call(env, { action: "verify", license_key: KEY, device_id: DEV_A });
  assert.equal(v.success, false); assert.equal(v.code, "expired"); assert.equal(v.edition, "plus");
});

test("3 meses (90 días) y 12 meses (365 días) devuelven su fecha de caducidad", async () => {
  let env = makeEnv(); owner = "plus-3m";
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_A })).expires_at, clock + 90 * DAY);
  env = makeEnv(); owner = "plus-12m";
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_A })).expires_at, clock + 365 * DAY);
});

test("caducada: no se puede reactivar ni en otro equipo ni tras desactivar (el reloj no se reinicia)", async () => {
  const env = makeEnv(); owner = "plus-3m";
  await call(env, { action: "activate", license_key: KEY, device_id: DEV_A });
  clock += 40 * DAY;
  assert.equal((await call(env, { action: "deactivate", license_key: KEY, device_id: DEV_A })).success, true);
  const b = await call(env, { action: "activate", license_key: KEY, device_id: DEV_B });
  assert.equal(b.success, true); assert.equal(b.expires_at, Date.parse("2026-11-01T10:00:00Z") + 90 * DAY);   // sigue contando desde la 1.ª activación
  clock += 51 * DAY;
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_B })).code, "expired");
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_A })).code, "expired");
});

test("comprados antes de LEGACY_BEFORE son permanentes aunque el producto ahora caduque", async () => {
  const env = makeEnv({ LEGACY_BEFORE: "2026-10-22T00:00:00Z" });
  bought = Date.parse("2026-10-15T12:00:00Z");
  const a = await call(env, { action: "activate", license_key: KEY, device_id: DEV_A });
  assert.deepEqual(a, { success: true, edition: "plus" });
  clock += 1000 * DAY;
  assert.equal((await call(env, { action: "verify", license_key: KEY, device_id: DEV_A })).success, true);
});

test("comprados después de LEGACY_BEFORE sí caducan", async () => {
  const env = makeEnv({ LEGACY_BEFORE: "2026-10-22T00:00:00Z" });
  bought = Date.parse("2026-10-30T12:00:00Z");
  assert.ok((await call(env, { action: "activate", license_key: KEY, device_id: DEV_A })).expires_at);
});

test("claves propias (OWN_KEYS): válidas, permanentes y sin pasar por Payhip", async () => {
  const env = makeEnv({ OWN_KEYS: "RR-PLUS-AAAA-BBBB:plus, RR-BAS-CCCC-DDDD:basic" }); owner = "nadie";
  assert.deepEqual(await call(env, { action: "activate", license_key: "rr-plus-aaaa-bbbb", device_id: DEV_A }), { success: true, edition: "plus" });
  assert.equal((await call(env, { action: "activate", license_key: "RR-BAS-CCCC-DDDD", device_id: DEV_B })).edition, "basic");
  clock += 5000 * DAY;
  assert.equal((await call(env, { action: "verify", license_key: "RR-PLUS-AAAA-BBBB", device_id: DEV_A })).success, true);
  assert.equal((await call(env, { action: "activate", license_key: "RR-PLUS-AAAA-BBBB", device_id: DEV_B })).code, "in_use");
  assert.equal((await call(env, { action: "activate", license_key: "RR-PLUS-ZZZZ-ZZZZ", device_id: DEV_B })).code, "invalid");
});

test("sin DAYS ni PAYHIP_PRODUCTS todo sigue siendo permanente (compatibilidad)", async () => {
  const env = { PAYHIP_SECRET_PLUS: "plus-3m", ADMIN_TOKEN: "t".repeat(40), LICENSES: makeKV() };
  assert.deepEqual(await call(env, { action: "activate", license_key: KEY, device_id: DEV_A }), { success: true, edition: "plus" });
});

test("PAYHIP_PRODUCTS mal formado no rompe el resto", async () => {
  const env = makeEnv({ PAYHIP_PRODUCTS: "{no es json" });
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_A })).success, true);
});
