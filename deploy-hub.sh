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
cp engine/hub/index.php engine/hub/pult.php engine/hub/clients.php engine/hub/.htaccess engine/hub/robots.txt engine/static/api/_crm.php engine/static/api/_csp.php "$TMP"/
echo "$SHA" > "$TMP/version.txt"
cd "$TMP"
git add -A
if git diff --cached --quiet; then echo "Ветка deploy-hub уже актуальна"; exit 0; fi
git -c user.name="deploy" -c user.email="deploy@alfimov.kz" commit -q -m "hub from engine $SHA"
git push -q origin deploy-hub
echo "Пульт: ветка deploy-hub обновлена (движок $SHA)"
