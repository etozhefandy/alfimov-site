"""ИИ-автор SEO-статей для блога alfimov.kz (Claude API).

Пишет ЧЕРНОВИК: тело в markdown и все SEO-поля (title, description, «Коротко», FAQ,
перелинковка). Публикует всегда человек — статья сохраняется черновиком, её правят и
ставят в расписание в админке. В agency-os генерации не было, это наша надстройка.

Ключ: переменная ANTHROPIC_API_KEY или Связка ключей macOS
    security add-generic-password -a claude -s alfimov-site-anthropic -w
Нужен пакет `anthropic` (pip3 install anthropic) — только для админки, сборке сайта он не нужен.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
import content_ru  # noqa: E402

MODEL = os.environ.get("SEO_WRITER_MODEL", "claude-opus-5")
KEYCHAIN_SERVICE = "alfimov-site-anthropic"

SCHEMA = {
    "type": "object",
    "properties": {
        "slug": {"type": "string", "description": "латиница, цифры, дефис; 3–6 слов"},
        "title": {"type": "string", "description": "h1 для человека"},
        "seo_title": {"type": "string", "description": "<title> до 60 символов, главный ключ в начале"},
        "description": {"type": "string", "description": "meta description 140–160 символов"},
        "lead": {"type": "string", "description": "подзаголовок под h1, 1–2 предложения"},
        "summary": {"type": "string", "description": "блок «Коротко»: суть статьи в 2–3 предложениях"},
        "category": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "body_md": {"type": "string", "description": "тело статьи в markdown, без h1"},
        "faq": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"q": {"type": "string"}, "a": {"type": "string"}},
                "required": ["q", "a"],
                "additionalProperties": False,
            },
        },
        "related": {"type": "array", "items": {"type": "string"}, "description": "slug существующих статей"},
    },
    "required": ["slug", "title", "seo_title", "description", "lead", "summary", "category",
                 "keywords", "body_md", "faq", "related"],
    "additionalProperties": False,
}


class WriterError(Exception):
    pass


def api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def system_prompt():
    services = "\n".join(f"- {s['name']} — /{s['slug']}/ — {s['short']}" for s in content_ru.SERVICES)
    return f"""Ты — редактор блога маркетингового агентства Alfimov (alfimov.kz), Казахстан.
Агентство ведёт рекламу и маркетинг для бизнеса по всему Казахстану (Алматы, Астана, Шымкент и другие города).
Услуги агентства и адреса их страниц на сайте:
{services}

Ты пишешь SEO-статьи на русском языке для владельцев и маркетологов казахстанского бизнеса. Статья должна
ранжироваться в Google и Яндексе по заданным запросам и при этом быть полезной: конкретика, шаги, примеры
расчётов, типичные ошибки, чек-листы. Читатель — предприниматель, а не маркетолог: без воды и канцелярита.

Требования к статье:
- Структура: вступление 2–3 абзаца без заголовка, затем 5–9 разделов `##`, внутри при необходимости `###`.
  Заголовки разделов содержательные и отвечают на вопросы из поиска. `#` (h1) в теле не используй.
- Главный ключ — в title, seo_title, первом абзаце и хотя бы одном `##`; остальные ключи и их вариации
  распредели естественно. Никакого переспама.
- Используй списки, где перечисление; таблицу markdown, где сравнение; `**жирный**` — для ключевых мыслей, редко.
- Контекст Казахстана: цены и бюджеты в тенге, местные площадки и реалии (Kaspi, 2ГИС, OLX, Instagram, WhatsApp,
  Telegram), города. Цифры давай только как общеизвестные ориентиры или как пример расчёта, явно помеченный как пример.
- НЕ выдумывай кейсы агентства, клиентов, результаты, отзывы, статистику с источником и цены на услуги Alfimov.
- Внутренние ссылки: 2–4 уместные ссылки markdown на страницы услуг из списка выше (относительный путь, например
  [таргетированная реклама](/target-facebook-instagram/)). Внешние ссылки не нужны.
- В конце — короткий раздел с выводом и мягким призывом обсудить задачу с агентством (без агрессивной продажи).
- FAQ: 4–6 вопросов, которые реально задают в поиске, ответы по 1–3 предложения, не повторяют текст дословно.
- related: выбери до 3 slug из списка существующих статей, если они по теме; иначе пустой список.
- slug: транслит латиницей по главному ключу, 3–6 слов через дефис, без стоп-слов.
"""


def user_prompt(topic, keywords, notes, words, existing):
    lines = [f"Тема статьи: {topic.strip()}"]
    if keywords:
        lines.append("Поисковые запросы (первый — главный): " + "; ".join(keywords))
    lines.append(f"Объём тела: около {int(words)} слов.")
    if notes and notes.strip():
        lines.append(f"Пожелания редактора: {notes.strip()}")
    if existing:
        lines.append("Существующие статьи блога (slug — заголовок):\n" +
                     "\n".join(f"- {a['slug']} — {a['title']}" for a in existing))
    else:
        lines.append("Других статей в блоге пока нет.")
    return "\n".join(lines)


def generate(topic, keywords=(), notes="", words=1500, existing=(), client=None):
    """Возвращает словарь полей статьи (без статуса и даты). Бросает WriterError с понятным текстом."""
    if not topic or not topic.strip():
        raise WriterError("Укажите тему статьи")
    keywords = [k.strip() for k in keywords if k and k.strip()]
    if client is None:
        key = api_key()
        if not key:
            raise WriterError(
                "Нет ключа Claude. Сохраните его командой: "
                f"security add-generic-password -a claude -s {KEYCHAIN_SERVICE} -w  (или задайте ANTHROPIC_API_KEY)")
        try:
            import anthropic
        except ImportError:
            raise WriterError("Не установлен пакет anthropic: pip3 install anthropic") from None
        client = anthropic.Anthropic(api_key=key)

    import anthropic

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=32000,
            thinking={"type": "adaptive"},
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            system=system_prompt(),
            messages=[{"role": "user", "content": user_prompt(topic, keywords, notes, words, list(existing))}],
        ) as stream:
            msg = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise WriterError("Claude отклонил ключ — проверьте ANTHROPIC_API_KEY / Связку ключей") from None
    except anthropic.RateLimitError:
        raise WriterError("Лимит запросов Claude — попробуйте через минуту") from None
    except anthropic.APIStatusError as ex:
        raise WriterError(f"Ошибка Claude API ({ex.status_code}): {ex.message}") from None
    except anthropic.APIConnectionError:
        raise WriterError("Нет связи с Claude API — проверьте интернет") from None

    if msg.stop_reason == "refusal":
        raise WriterError("Claude отказался писать на эту тему — переформулируйте тему")
    if msg.stop_reason == "max_tokens":
        raise WriterError("Статья не уместилась в лимит ответа — уменьшите объём")
    text = next((b.text for b in msg.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise WriterError("Claude вернул неразборчивый ответ — попробуйте ещё раз") from None

    known = {a["slug"] for a in existing}
    data["faq"] = [[f["q"], f["a"]] for f in data.get("faq", [])]
    data["related"] = [s for s in data.get("related", []) if s in known]
    data["keywords"] = data.get("keywords") or keywords
    return data
