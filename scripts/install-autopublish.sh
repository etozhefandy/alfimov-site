#!/bin/bash
# Устанавливает (или обновляет) автопубликацию блога: launchd раз в 15 минут.
#   ./scripts/install-autopublish.sh            — установить
#   ./scripts/install-autopublish.sh --remove   — удалить
# Лог: ~/Library/Logs/alfimov-autopublish.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="kz.alfimov.autopublish"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/alfimov-autopublish.log"
PY="$(command -v python3)"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
if [ "${1:-}" = "--remove" ]; then
  rm -f "$PLIST"; echo "Автопубликация удалена"; exit 0
fi

mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>$ROOT/scripts/autopublish.py</string></array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartInterval</key><integer>900</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>$(dirname "$PY"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>LANG</key><string>ru_RU.UTF-8</string>
  </dict>
</dict>
</plist>
PLIST
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Автопубликация установлена: каждые 15 минут. Лог: $LOG"
