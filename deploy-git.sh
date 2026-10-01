#!/bin/bash
# Собирает сайт и публикует готовый dist/ в ветку `deploy` на GitHub.
# Коммиты добавляются поверх текущей ветки (без force-push), чтобы Plesk Git
# (ветка deploy → /httpdocs) спокойно подтягивал их кнопкой «Получить сейчас».
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
# PHP-блог и админка: синтаксис и тесты (если php есть на этом компьютере).
if command -v php >/dev/null; then
  for f in $(find dist -name '*.php'); do php -l "$f" >/dev/null || { echo "Ошибка PHP в $f"; exit 1; }; done
  php tests/php/test_blog.php >/dev/null || { php tests/php/test_blog.php | grep FAIL; echo 'Выкладка остановлена: PHP-тесты блога'; exit 1; }
fi
# Критичные SEO-ошибки (битые ссылки, дубли title, нет H1) — не выкладываем.
python3 seo_audit.py >/dev/null || { python3 seo_audit.py | grep '\[critical\]'; echo 'Выкладка остановлена: исправьте critical-ошибки SEO-аудита'; exit 1; }
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
