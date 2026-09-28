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

Каждый push в `main` → GitHub Actions собирает сайт и заливает `dist/` по FTPS на хостинг PS.kz (`srv-plesk22.ps.kz`, папка `httpdocs`).

Секреты репозитория (Settings → Secrets and variables → Actions):

| Секрет | Зачем |
|---|---|
| `FTP_PASSWORD` | пароль FTP-пользователя `alfimovk` в Plesk |
| `TG_BOT_TOKEN` | токен бота, который присылает заявки |
| `TG_CHAT_ID` | chat_id, куда слать заявки |

Без `FTP_PASSWORD` сборка проходит, но деплой пропускается. Без Telegram-секретов форма отвечает ошибкой и предлагает написать в WhatsApp/Telegram.
