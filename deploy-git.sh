#!/bin/bash
# Собирает сайт и публикует готовый dist/ в ветку `deploy` на GitHub.
# Коммиты добавляются поверх текущей ветки (без force-push), чтобы Plesk Git
# (ветка deploy → /httpdocs) спокойно подтягивал их кнопкой «Получить сейчас».
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
REMOTE="$(git remote get-url origin)"
SRC_SHA="$(git rev-parse --short HEAD)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git clone -q --branch deploy --single-branch "$REMOTE" "$TMP"
find "$TMP" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R dist/. "$TMP"/
cd "$TMP"
git add -A
if git diff --cached --quiet; then
  echo "Ветка deploy уже актуальна"
  exit 0
fi
git -c user.name="deploy" -c user.email="deploy@alfimov.kz" commit -q -m "build from $SRC_SHA"
git push -q origin deploy
echo "Ветка deploy обновлена (сборка из $SRC_SHA)"
