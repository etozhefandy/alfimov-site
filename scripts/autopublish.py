#!/usr/bin/env python3
"""Автопубликация блога: запускается launchd раз в 15 минут (scripts/install-autopublish.sh).

Подтягивает main, коммитит сохранённые в админке статьи и обложки, пушит и запускает
./deploy-git.sh. Сборка кладёт на сайт только вышедшие статьи, поэтому запланированная
статья появится в первый запуск после своей даты. Если ничего не изменилось —
deploy-git.sh ничего не пушит, сайт не трогается.
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import admin  # noqa: E402


def main():
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with admin.publish_lock():
            subprocess.run(["git", "pull", "-q", "--rebase", "--autostash", "origin", "main"],
                           cwd=ROOT, check=True, capture_output=True, text=True, timeout=120)
            log = admin.publish()
        print(f"[{stamp}] " + " | ".join(log[:-1]))  # последняя строка — подсказка для экрана админки
    except Exception as ex:  # noqa: BLE001 — лог для человека, а не трейсбек
        detail = getattr(ex, "stderr", "") or str(ex)
        print(f"[{stamp}] ОШИБКА: {detail.strip()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
