# alfimov.kz

SEO-сайт маркетингового агентства Alfimov. Статический, собирается скриптом на Python без зависимостей.

## Как устроено

| Что | Где |
|---|---|
| Тексты RU | `src/content_ru.py` |
| Тексты KZ | `src/content_kz.py` |
| Шаблоны, SEO-разметка, sitemap | `build.py` |
| Стили и скрипты | `static/assets/` |
| Обработчик формы → Telegram | `static/api/send.php` |
| Редиректы (https, www, alfimov.pro) | `static/.htaccess` |
| Статьи блога (источник правды) | `content/articles/*.json` |
| Блог: хранение, расписание, markdown | `blog.py` |
| ИИ-автор статей (Claude) | `seo_writer.py` |
| Админка блога | `admin.py` + `admin/index.html` |

Страницы: главная, 7 услуг, контакты — на русском (`/`) и казахском (`/kz/`), связаны через hreflang.

## Локально

```
python3 build.py --serve   # http://localhost:8000
```

## Блог и SEO-статьи

Перенесено из agency-os (редактор + расписание + сборка в статику) и дополнено ИИ-автором.

```
python3 admin.py   # http://127.0.0.1:8001/admin/ — работает только на этом Mac
```

1. **Написать с ИИ**: тема + поисковые запросы → Claude пишет черновик со всеми SEO-полями
   (title, description, «Коротко», разделы, FAQ, внутренние ссылки на услуги, перелинковка).
2. Проверить и поправить текст; справа SEO-проверка (длины, ключ в title и первом абзаце, объём, ссылки).
3. Статус «Запланировано» + дата выхода (время Алматы) → «Сохранить». Черновики на сайт не попадают.
4. **Опубликовать на сайт**: коммит статей в main → push → `./deploy-git.sh`, затем в Plesk
   «Получить сейчас» → «Развернуть сейчас».

Сайт статический: запланированная статья появится на alfimov.kz при первой публикации после её даты.
Пункт «Блог» в меню и `/blog/` появляются только когда вышла хотя бы одна статья. Статьи — только на русском
(без пары на `/kz/`), в sitemap попадают отдельными адресами.

Для ИИ-автора нужен пакет `anthropic` (`pip3 install anthropic`) и ключ Claude — один раз в Связку ключей:

```
security add-generic-password -a claude -s alfimov-site-anthropic -w
```

(или переменная `ANTHROPIC_API_KEY`; модель меняется через `SEO_WRITER_MODEL`, по умолчанию `claude-opus-5`).
Сборке сайта (`build.py`) зависимости по-прежнему не нужны.

Тесты: `python3 -m unittest discover tests -v`

## Деплой

С Mac, одной командой:

```
./deploy.sh
```

Скрипт собирает сайт и заливает `dist/` по FTPS на хостинг PS.kz (`srv-plesk22.ps.kz`, папка `httpdocs`).
Пароли берутся из Связки ключей macOS — один раз сохранить (команда спросит значение):

```
security add-generic-password -a alfimovk -s alfimov-site-ftp -w
security add-generic-password -a bot -s alfimov-site-tg-token -w
security add-generic-password -a bot -s alfimov-site-tg-chat -w
```

Без Telegram-значений форма отвечает ошибкой и предлагает написать в WhatsApp/Telegram.

Workflow `.github/workflows/deploy.yml` отключён: аккаунт GitHub заблокирован по биллингу, Actions не стартуют.
Если это починить — `gh workflow enable deploy.yml` (секреты FTP_PASSWORD / TG_BOT_TOKEN / TG_CHAT_ID).
