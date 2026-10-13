// Pruebas del Worker con un KV y un fetch simulados:  node --test worker/test_worker.mjs
import test from "node:test";
import assert from "node:assert/strict";
import worker from "./autoprevias-license.js";

const KEY = "ABCD-1234-EFGH-5678";
const DEV_A = "a".repeat(64);
const DEV_B = "b".repeat(64);

function makeKV() {
  const m = new Map();
  return { m, get: async (k) => (m.has(k) ? JSON.parse(m.get(k)) : null), put: async (k, v) => void m.set(k, v), delete: async (k) => void m.delete(k) };
}
function makeEnv(extra = {}) {
  return { PAYHIP_SECRET_PLUS: "plus-secret", PAYHIP_SECRET_BASIC: "basic-secret", ADMIN_TOKEN: "t".repeat(40), LICENSES: makeKV(), ...extra };
}
let payhip;   // { plus: bool|"disabled", basic: ... }
globalThis.fetch = async (url, init) => {
  const secret = init.headers["product-secret-key"];
  const which = secret === "plus-secret" ? "plus" : "basic";
  const ok = payhip[which];
  const data = ok ? { enabled: ok === true, license_key: KEY, buyer_email: "x@y.z", uses: 0 } : null;
  return new Response(JSON.stringify(ok ? { data, error: false } : { error: true }), { status: ok ? 200 : 404 });
};
const call = async (env, body, headers = {}) =>
  (await worker.fetch(new Request("https://w/", { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) }), env)).json();

test.beforeEach(() => { payhip = { plus: true, basic: false }; });

test("activa en el primer equipo y no devuelve el correo del comprador", async () => {
  const env = makeEnv();
  const r = await call(env, { action: "activate", license_key: KEY, device_id: DEV_A });
  assert.deepEqual(r, { success: true, edition: "plus" });
});

test("segundo equipo: rechazado mientras el primero la tiene activa", async () => {
  const env = makeEnv();
  await call(env, { action: "activate", license_key: KEY, device_id: DEV_A });
  const r = await call(env, { action: "activate", license_key: KEY, device_id: DEV_B });
  assert.equal(r.success, false); assert.equal(r.code, "in_use");
});

test("el mismo equipo puede reactivar y reverificar", async () => {
  const env = makeEnv();
  await call(env, { action: "activate", license_key: KEY, device_id: DEV_A });
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_A })).success, true);
  assert.equal((await call(env, { action: "verify", license_key: KEY, device_id: DEV_A })).success, true);
});

test("desactivar libera el hueco para otro equipo", async () => {
  const env = makeEnv();
  await call(env, { action: "activate", license_key: KEY, device_id: DEV_A });
  assert.equal((await call(env, { action: "deactivate", license_key: KEY, device_id: DEV_B })).code, "not_owner");
  assert.equal((await call(env, { action: "deactivate", license_key: KEY, device_id: DEV_A })).success, true);
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_B })).success, true);
});

test("un equipo que lleva más de 15 días sin verificar pierde el hueco", async () => {
  const env = makeEnv();
  await call(env, { action: "activate", license_key: KEY, device_id: DEV_A });
  const k = [...env.LICENSES.m.keys()][0];
  const rec = JSON.parse(env.LICENSES.m.get(k)); rec.last_seen = Date.now() - 16 * 86400000; env.LICENSES.m.set(k, JSON.stringify(rec));
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_B })).success, true);
  assert.equal((await call(env, { action: "verify", license_key: KEY, device_id: DEV_A })).code, "in_use");
});

test("clave desactivada o inexistente en Payhip", async () => {
  const env = makeEnv(); payhip = { plus: false, basic: false };
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_A })).code, "invalid");
  payhip = { plus: "disabled", basic: false };
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_A })).code, "invalid");
  assert.equal((await call(env, { action: "activate", license_key: "x", device_id: DEV_A })).code, "invalid");
});

test("edición Basic", async () => {
  const env = makeEnv(); payhip = { plus: false, basic: true };
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_A })).edition, "basic");
});

test("versiones antiguas sin device_id: pasan, salvo REQUIRE_DEVICE=1", async () => {
  assert.equal((await call(makeEnv(), { license_key: KEY })).legacy, true);
  assert.equal((await call(makeEnv({ REQUIRE_DEVICE: "1" }), { license_key: KEY })).code, "update_required");
});

test("reset: solo con el token de administrador", async () => {
  const env = makeEnv();
  await call(env, { action: "activate", license_key: KEY, device_id: DEV_A });
  assert.equal((await call(env, { action: "reset", license_key: KEY })).code, "unauthorized");
  assert.equal((await call(env, { action: "reset", license_key: KEY }, { Authorization: "Bearer wrong" })).code, "unauthorized");
  assert.equal((await call(env, { action: "reset", license_key: KEY }, { Authorization: "Bearer " + "t".repeat(40) })).success, true);
  assert.equal((await call(env, { action: "activate", license_key: KEY, device_id: DEV_B })).success, true);
});

test("en KV no se guarda la clave en claro ni el correo", async () => {
  const env = makeEnv();
  await call(env, { action: "activate", license_key: KEY, device_id: DEV_A });
  const dump = JSON.stringify([...env.LICENSES.m.entries()]);
  assert.ok(!dump.includes(KEY)); assert.ok(!dump.includes("x@y.z"));
});

test("identificador de equipo mal formado", async () => {
  const r = await call(makeEnv(), { action: "activate", license_key: KEY, device_id: "zzz" });
  assert.equal(r.code, "bad_request");
});
