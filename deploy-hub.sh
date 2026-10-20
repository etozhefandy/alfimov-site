#!/bin/bash
# Пульт admin.alfimov.kz: файлы из движка (engine/hub) → ветка `deploy-hub` → Plesk Git → папка /admin.alfimov.kz.
set -euo pipefail
cd "$(dirname "$0")"
REPO="$PWD"
php engine/tests/php/test_hub.php >/dev/null || { php engine/tests/php/test_hub.php | grep FAIL; echo "Пульт не выложен: тесты"; exit 1; }
REMOTE="$(git remote get-url origin)"
SHA="$(git -C engine rev-parse --short HEAD)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if git ls-remote --exit-code --heads "$REMOTE" deploy-hub >/dev/null; then
  git clone -q --branch deploy-hub --single-branch "$REMOTE" "$TMP"
else
  git init -q "$TMP" && git -C "$TMP" checkout -q --orphan deploy-hub && git -C "$TMP" remote add origin "$REMOTE"
fi
find "$TMP" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
# все файлы пульта (кроме локального dev_router.php) + общие библиотеки движка, которые он подключает
cp engine/hub/*.php engine/hub/.htaccess engine/hub/robots.txt "$TMP"/
rm -f "$TMP/dev_router.php"
cp engine/static/api/_crm.php engine/static/api/_csp.php engine/static/api/_hub.php engine/static/api/_capi.php "$TMP"/
# пульт должен хотя бы запускаться: все require на месте и без синтаксических ошибок
for f in "$TMP"/*.php; do php -l "$f" >/dev/null || { echo "Пульт не выложен: ошибка в $(basename "$f")"; exit 1; }; done
( cd "$TMP" && HUB_DEV=1 HUB_BASE="$(mktemp -d)" php -r 'ob_start(); $_SERVER["REQUEST_METHOD"]="GET"; include "index.php";' >/dev/null 2>"$TMP.err" ) || true
if grep -q "Fatal" "$TMP.err" 2>/dev/null; then cat "$TMP.err"; echo "Пульт не выложен: не запускается"; rm -f "$TMP.err"; exit 1; fi
rm -f "$TMP.err"
echo "$SHA" > "$TMP/version.txt"
cd "$TMP"
git add -A
if git diff --cached --quiet; then echo "Ветка deploy-hub уже актуальна"; exit 0; fi
git -c user.name="deploy" -c user.email="deploy@alfimov.kz" commit -q -m "hub from engine $SHA"
git push -q origin deploy-hub
echo "Пульт: ветка deploy-hub обновлена (движок $SHA)"
