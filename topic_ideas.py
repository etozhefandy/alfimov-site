"""Идеи тем для блога: живые запросы из подсказок Google и Яндекса (Казахстан) → Claude.

1. collect() — по затравкам из услуг сайта собирает поисковые подсказки: Google (gl=kz, hl=ru)
   и Яндекс (регион Казахстан, lr=159). Это реальные запросы людей, но без частотности.
2. propose() — Claude отсеивает мусор («таргетная терапия», сериалы), группирует запросы
   и предлагает темы статей: главный ключ, запросы, к какой услуге ведёт, почему стоит писать.

Бесплатно, кроме вызова Claude. Частотность (сколько раз ищут) — только в платных
источниках (Яндекс Вордстат API, DataForSEO); сюда можно добавить позже.
"""
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import content_ru  # noqa: E402
import seo_writer  # noqa: E402

CACHE = ROOT / ".cache" / "topic_ideas.json"

SEEDS = [
    "таргетированная реклама", "таргет инстаграм", "реклама в инстаграм", "реклама в тикток",
    "таргетолог", "контекстная реклама", "реклама в гугл", "яндекс директ",
    "seo продвижение", "продвижение сайта", "smm продвижение", "ведение инстаграм",
    "маркетинговое агентство", "маркетинговое исследование", "маркетинг для бизнеса",
]
PATTERNS = ["{s}", "{s} цена", "{s} алматы", "{s} астана", "сколько стоит {s}", "как {s}"]

GOOGLE = "https://suggestqueries.google.com/complete/search?client=firefox&hl=ru&gl=kz&q={q}"
YANDEX = "https://suggest.yandex.ru/suggest-ff.cgi?part={q}&lr=159&uil=ru"

SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "тема статьи — готовый рабочий заголовок"},
                    "main_keyword": {"type": "string", "description": "главный запрос из списка"},
                    "keywords": {"type": "array", "items": {"type": "string"}, "description": "3–8 запросов из списка"},
                    "intent": {"type": "string", "enum": ["коммерческий", "информационный"]},
                    "service": {"type": "string", "description": "slug услуги, к которой ведёт статья"},
                    "why": {"type": "string", "description": "одно предложение: почему тема стоит статьи"},
                },
                "required": ["topic", "main_keyword", "keywords", "intent", "service", "why"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ideas"],
    "additionalProperties": False,
}


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
        if not ctx.get_ca_certs():
            ctx.load_verify_locations("/etc/ssl/cert.pem")
        return ctx


def fetch_suggestions(url):
    """Подсказки в формате OpenSearch: [запрос, [варианты...]]. Ошибки сети → пустой список."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (alfimov.kz topic ideas)"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context()) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        return [s for s in data[1] if isinstance(s, str)]
    except Exception:  # noqa: BLE001 — одна неудачная подсказка не должна ронять сбор
        return []


def collect(seeds=SEEDS, patterns=PATTERNS, fetch=fetch_suggestions, workers=8):
    """→ {запрос: {"google", "yandex"}} — где встретился. Регистр и пробелы нормализованы."""
    jobs = []
    for s in seeds:
        for p in patterns:
            q = urllib.parse.quote(p.format(s=s))
            jobs += [("google", GOOGLE.format(q=q)), ("yandex", YANDEX.format(q=q))]
    found = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for (engine, _), items in zip(jobs, pool.map(lambda j: fetch(j[1]), jobs)):
            for item in items:
                key = " ".join(item.lower().split())
                if key:
                    found.setdefault(key, set()).add(engine)
    return found


def _prompt(queries, existing, focus):
    services = "\n".join(f"- {s['slug']} — {s['name']}: {s['short']}" for s in content_ru.SERVICES)
    lines = [f"{q}{'  [Google+Яндекс]' if len(src) > 1 else ''}" for q, src in sorted(queries.items())]
    parts = [
        "Ты SEO-редактор блога маркетингового агентства ALFIMOV.KZ (Казахстан). Читатель — владелец бизнеса.",
        f"Услуги агентства (slug — название):\n{services}",
        "Реальные запросы из поисковых подсказок Google и Яндекса по Казахстану "
        "(пометка [Google+Яндекс] — встречается в обоих, это более надёжный спрос):\n" + "\n".join(lines),
    ]
    if existing:
        parts.append("Статьи, которые уже есть (не повторяй их темы):\n" + "\n".join(f"- {t}" for t in existing))
    if focus:
        parts.append(f"Пожелание редактора: {focus}")
    parts.append(
        "Предложи 8–10 тем статей. Правила: только темы, полезные бизнесу и ведущие к услугам агентства; "
        "игнорируй нерелевантное (медицина, сериалы, вакансии, обучение на таргетолога, чужие бренды); "
        "главный запрос и запросы бери только из списка выше, ничего не выдумывай и не пиши частотность; "
        "не делай двух статей под один и тот же главный запрос; предпочитай запросы с деньгами и выбором "
        "(«сколько стоит», «как выбрать», город) и объясняющие темы, после которых естественно обратиться "
        "в агентство. service — один slug из списка услуг."
    )
    return "\n\n".join(parts)


def propose(queries, existing=(), focus="", client=None):
    """→ список идей (dict). Бросает seo_writer.WriterError с понятным текстом."""
    if not queries:
        raise seo_writer.WriterError("Не удалось получить подсказки Google и Яндекса — проверьте интернет")
    if client is None:
        key = seo_writer.api_key()
        if not key:
            raise seo_writer.WriterError("Нет ключа Claude — см. README, раздел про ИИ-автора")
        import anthropic
        client = anthropic.Anthropic(api_key=key)
    import anthropic

    try:
        with client.messages.stream(
            model=seo_writer.MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": _prompt(queries, list(existing), focus)}],
        ) as stream:
            msg = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise seo_writer.WriterError("Claude отклонил ключ") from None
    except anthropic.RateLimitError:
        raise seo_writer.WriterError("Лимит запросов Claude — попробуйте через минуту") from None
    except anthropic.APIStatusError as ex:
        raise seo_writer.WriterError(f"Ошибка Claude API ({ex.status_code}): {ex.message}") from None
    except anthropic.APIConnectionError:
        raise seo_writer.WriterError("Нет связи с Claude API — проверьте интернет") from None

    if msg.stop_reason == "refusal":
        raise seo_writer.WriterError("Claude отказался подбирать темы — попробуйте ещё раз")
    text = next((b.text for b in msg.content if b.type == "text"), "")
    try:
        ideas = json.loads(text)["ideas"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise seo_writer.WriterError("Claude вернул неразборчивый ответ — попробуйте ещё раз") from None
    slugs = {s["slug"] for s in content_ru.SERVICES}
    for i in ideas:
        if i.get("service") not in slugs:
            i["service"] = ""
    return ideas


def run(existing=(), focus=""):
    """Полный цикл + кэш в .cache/topic_ideas.json (не в git)."""
    queries = collect()
    ideas = propose(queries, existing, focus)
    result = {"ideas": ideas, "queries": len(queries), "focus": focus,
              "created": time.strftime("%Y-%m-%d %H:%M")}
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def cached():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
