#!/usr/bin/env bash
# Prueba rápida del Worker de licencias ya desplegado (no guarda nada en el repo).
#   LICENSE_KEY="clave-de-prueba-real" ADMIN_TOKEN="tu-token" bash worker/smoke_test.sh [URL_DEL_WORKER]
# Usa dos identificadores de equipo inventados y, al terminar, deja la clave libre (reset).
set -u
URL="${1:-https://autoprevias-license.radicalrecordsvlc.workers.dev}"
: "${LICENSE_KEY:?Define LICENSE_KEY con una clave de prueba real de Payhip}"
: "${ADMIN_TOKEN:?Define ADMIN_TOKEN (el secret del Worker)}"
DEV_A=$(printf 'a%.0s' $(seq 64)); DEV_B=$(printf 'b%.0s' $(seq 64))
call() { curl -s -X POST "$URL" -H "Content-Type: application/json" -H "User-Agent: AutoPrevias-License/1.0" "$@"; echo; }
body() { printf '{"action":"%s","license_key":"%s","device_id":"%s","platform":"smoke"}' "$1" "$LICENSE_KEY" "$2"; }
pass=0; fail=0
check() { if echo "$2" | grep -q "$3"; then echo "  ✓ $1"; pass=$((pass+1)); else echo "  ✗ $1  → $2"; fail=$((fail+1)); fi; }

echo "1) clave inventada (debe ser inválida)"
r=$(call -d '{"action":"activate","license_key":"AAAA-BBBB-CCCC-DDDD","device_id":"'$DEV_A'"}'); check "rechaza clave falsa" "$r" '"code":"invalid"'
echo "2) limpiar estado previo"
r=$(call -H "Authorization: Bearer $ADMIN_TOKEN" -d "{\"action\":\"reset\",\"license_key\":\"$LICENSE_KEY\"}"); check "reset con ADMIN_TOKEN" "$r" '"success":true'
echo "3) equipo A activa"
r=$(call -d "$(body activate $DEV_A)"); check "A activa (edición devuelta)" "$r" '"success":true,"edition"'
echo "4) equipo B intenta activar la misma clave"
r=$(call -d "$(body activate $DEV_B)"); check "B rechazado (in_use)" "$r" '"code":"in_use"'
echo "5) A reverifica"
r=$(call -d "$(body verify $DEV_A)"); check "A sigue válido" "$r" '"success":true'
echo "6) A desactiva y B activa"
r=$(call -d "$(body deactivate $DEV_A)"); check "A libera la licencia" "$r" '"success":true'
r=$(call -d "$(body activate $DEV_B)"); check "B ya puede activar" "$r" '"success":true'
echo "7) A ya no es el dueño"
r=$(call -d "$(body verify $DEV_A)"); check "A recibe in_use" "$r" '"code":"in_use"'
echo "8) reset de administrador"
r=$(call -H "Authorization: Bearer $ADMIN_TOKEN" -d "{\"action\":\"reset\",\"license_key\":\"$LICENSE_KEY\"}"); check "reset OK" "$r" '"success":true'
r=$(call -H "Authorization: Bearer mal" -d "{\"action\":\"reset\",\"license_key\":\"$LICENSE_KEY\"}"); check "reset sin token correcto es rechazado" "$r" '"code":"unauthorized"'
echo "9) versión antigua de la app (sin device_id) sigue funcionando"
r=$(call -d "{\"license_key\":\"$LICENSE_KEY\"}"); check "modo compatible" "$r" '"success":true'
echo; echo "Resultado: $pass correctas, $fail fallidas"; [ "$fail" -eq 0 ]
