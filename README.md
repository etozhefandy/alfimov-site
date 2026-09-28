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

Страницы: главная, 7 услуг, контакты — на русском (`/`) и казахском (`/kz/`), связаны через hreflang.

## Локально

```
python3 build.py --serve   # http://localhost:8000
```

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
