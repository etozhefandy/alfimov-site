# alfimov-site — заметки для ИИ-агента

Сайт = свои страницы и тексты + общий движок (`engine/`, git submodule → `~/Desktop/site-engine`) + пульт
admin.alfimov.kz (`hub/` движка, но выкладывается только отсюда).

## ⚠️ Где чьё

| Что | Где править |
|---|---|
| Главная, услуги, контакты, SEO-разметка этих страниц (canonical/OG/JSON-LD/hreflang — уже всё есть) | `build.py` (этот репо) |
| Тексты RU/KZ | `src/content_ru.py`, `src/content_kz.py` |
| Лендинги заказчика Guestory | `src/lp_guestory.py`, `src/lp_render.py` |
| Тексты ниши для ИИ-автора (кто пишет, стиль обложек, затравки) | `site/prompts.php` (этот репо) |
| Блог, админка, ИИ-автор статей, очередь/автопилот, SEO-автопилот, CRM, пульт | **`~/Desktop/site-engine`** —
  правь там, не здесь. `engine/` тут — только синхронизированная копия (submodule). См. его
  [AGENTS.md](https://github.com/etozhefandy/site-engine/blob/main/AGENTS.md) |

Если задача про блог/админку/ИИ/SEO-автопилот — иди в `~/Desktop/site-engine`, делай там, потом синкай сюда
(ниже). Не правь `engine/static/...` прямо в этом репо напрямую — убьётся при следующем синке.

## Деплой (после правки своего или синка движка)

```
git -C engine fetch origin main -q && git -C engine checkout -B main origin/main -q   # если обновлял движок
python3 build.py
for f in engine/tests/php/test_*.php tests/php/test_*.php; do php "$f" . ; done        # все зелёные — обязательно
git add -A && git commit -m "…" && git push
./deploy-git.sh     # сайт
./deploy-hub.sh     # только если менялся hub/ в движке — пульт деплоится отдельно
```

**Грабли**: `git checkout main` в `engine/` тихо не обновляет его на стухшей локальной ветке — всегда
`fetch` + `checkout -B main origin/main` (см. выше). Тесты гоняй против собранного `dist/` (`python3 build.py`
первым делом), не против исходников движка.

`deploy.sh` (прямой FTPS с этого Mac) — старый способ, с 28 сентября не используется. Деплой — только
`deploy-git.sh`/`deploy-hub.sh` (Plesk Git по вебхуку).

## Репозиторий публичный

Никаких токенов, ключей, диагностических эндпоинтов в коде — секреты только на хостинге
(`alfimov-data/`, вне Plesk Git).

Подробности и таблица файлов сайта — [README.md](README.md).
