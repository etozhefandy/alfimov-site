#!/bin/bash
# Сборка и загрузка сайта на хостинг PS.kz по FTPS прямо с этого Mac.
# Пароли берутся из Связки ключей macOS (один раз сохранить):
#   security add-generic-password -a alfimovk -s alfimov-site-ftp -w
#   security add-generic-password -a bot -s alfimov-site-tg-token -w      (необязательно)
#   security add-generic-password -a bot -s alfimov-site-tg-chat -w       (необязательно)
set -euo pipefail
cd "$(dirname "$0")"

HOST="srv-plesk22.ps.kz"
USER="alfimovk"
REMOTE_DIR="httpdocs"

# Экранирование для конфига curl: \ и " внутри кавычек.
esc() { local s="${1//\\/\\\\}"; printf '%s' "${s//\"/\\\"}"; }

keychain() { security find-generic-password -s "$1" -w 2>/dev/null || true; }

FTP_PW="$(keychain alfimov-site-ftp)"
if [ -z "$FTP_PW" ]; then
  echo "Нет пароля FTP в Связке ключей. Сохраните его командой:"
  echo "  security add-generic-password -a alfimovk -s alfimov-site-ftp -w"
  exit 1
fi

TG_BOT_TOKEN="$(keychain alfimov-site-tg-token)" TG_CHAT_ID="$(keychain alfimov-site-tg-chat)" python3 build.py

# Один процесс curl на все файлы; пароль и список идут через stdin, а не в аргументах.
CONFIG="$(
  printf 'user = "%s:%s"\nssl-reqd\nftp-create-dirs\nsilent\nshow-error\nfail-early\n' "$USER" "$(esc "$FTP_PW")"
  (cd dist && find . -type f | sed 's|^\./||' | sort) | while read -r f; do
    printf 'upload-file = "dist/%s"\nurl = "ftp://%s/%s/%s"\n' "$f" "$HOST" "$REMOTE_DIR" "$f"
  done
)"
COUNT="$(cd dist && find . -type f | wc -l | tr -d ' ')"
echo "Загружаю $COUNT файлов на $HOST/$REMOTE_DIR …"
printf '%s\n' "$CONFIG" | curl -K -
echo "Готово: https://alfimov.kz"
