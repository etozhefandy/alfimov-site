#!/bin/bash
# Собирает сайт и публикует готовый dist/ в ветку `deploy` на GitHub.
# Plesk (Git → alfimov-site, ветка deploy, папка httpdocs) забирает её сам — без паролей FTP.
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
REMOTE="$(git remote get-url origin)"
SRC_SHA="$(git rev-parse --short HEAD)"
cd dist
rm -rf .git
git init -q -b deploy
git add -A
git -c user.name="deploy" -c user.email="deploy@alfimov.kz" commit -q -m "build from $SRC_SHA"
git push -q -f "$REMOTE" deploy
rm -rf .git
echo "Ветка deploy обновлена (сборка из $SRC_SHA)"
