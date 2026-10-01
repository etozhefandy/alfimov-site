"""Статьи блога alfimov.kz: хранение, расписание выхода, markdown → HTML (только stdlib).

Устройство перенесено из agency-os (site_articles + build_blog), но без базы данных:
сайт — статика, поэтому источник правды — файлы `content/articles/<slug>.json` в репо.
HTML страниц — вывод, его собирает build.py; руками dist/ не правим.

ВЫХОД ПО РАСПИСАНИЮ. В сборку попадают только статьи со статусом `scheduled`, у которых
`publish_at` уже наступил (время Алматы). Черновик и статья «на завтра» в открытую часть dist/
не пишутся — их нельзя открыть по угаданному адресу до срока. Будущие версии сайта лежат в
закрытой dist/_scheduled/, их выкладывает по времени PHP-скрипт на хостинге (см. build.py).
"""
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
ARTICLES_DIR = ROOT / "content" / "articles"

TZ = timezone(timedelta(hours=5))  # Алматы, UTC+5
STATUSES = ("draft", "scheduled")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WORDS_PER_MIN = 180

# Поля статьи. Каждое делает свою работу (как в agency-os): `seo_title` — <title> для выдачи,
# `title` — h1 для человека; `description` — сниппет в поиске, `summary` — блок «Коротко»
# для читателя, `lead` — подзаголовок под h1.
FIELDS = {
    "slug": "",
    "title": "",
    "seo_title": "",
    "description": "",
    "lead": "",
    "summary": "",
    "body_md": "",
    "category": "",
    "keywords": [],
    "cover_path": "",
    "author": "",
    "read_min": None,
    "faq": [],
    "related": [],
    "status": "draft",
    "publish_at": "",
    "created_at": "",
    "updated_at": "",
}


# ---------------------------------------------------------------- время

_frozen = None  # build.py собирает «сайт в момент T» для выхода по расписанию — см. freeze()


def now():
    return _frozen or datetime.now(TZ)


def freeze(at):
    """Подменяет «сейчас» (aware datetime) для сборки будущей версии сайта; None — вернуть часы."""
    global _frozen
    _frozen = at


def parse_dt(value):
    """'2026-10-01T10:00' (время Алматы) → aware datetime; пусто/мусор → None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=TZ)


def is_live(a, at=None):
    if a.get("status") != "scheduled":
        return False
    dt = parse_dt(a.get("publish_at"))
    return dt is not None and dt <= (at or now())


def state(a, at=None):
    """draft | scheduled (дата впереди) | live (дата наступила — будет на сайте)."""
    if a.get("status") != "scheduled":
        return "draft"
    return "live" if is_live(a, at) else "scheduled"


# ---------------------------------------------------------------- хранилище

def normalize(a):
    out = {k: (list(v) if isinstance(v, list) else v) for k, v in FIELDS.items()}
    for k in FIELDS:
        if k in a and a[k] is not None:
            out[k] = a[k]
    for k in ("slug", "title", "seo_title", "description", "lead", "summary", "category",
              "cover_path", "author", "status", "publish_at"):
        out[k] = str(out[k] or "").strip()
    out["slug"] = out["slug"].lower()
    out["body_md"] = str(out["body_md"] or "").replace("\r\n", "\n").strip() + "\n"
    out["keywords"] = [str(k).strip() for k in out["keywords"] if str(k).strip()]
    out["faq"] = [[str(q).strip(), str(ans).strip()] for q, ans in (out["faq"] or [])
                  if str(q).strip() and str(ans).strip()]
    out["related"] = [str(s).strip() for s in out["related"] if str(s).strip() and str(s).strip() != out["slug"]]
    try:
        out["read_min"] = int(out["read_min"]) if out["read_min"] not in (None, "") else None
    except (TypeError, ValueError):
        out["read_min"] = None
    return out


def validate(a):
    """Список ошибок человеческим языком; пустой — можно сохранять."""
    errors = []
    if not SLUG_RE.match(a["slug"]) or len(a["slug"]) > 120:
        errors.append("Адрес (slug): строчная латиница, цифры и дефис — он попадёт в URL")
    if len(a["title"]) < 2:
        errors.append("Нужен заголовок")
    if a["status"] not in STATUSES:
        errors.append("Статус: черновик или запланировано")
    # Запланировать без даты нельзя: такая статья не выйдет никогда, а числиться будет
    # запланированной — ровно тот случай, когда экран врёт о состоянии.
    if a["status"] == "scheduled":
        if not a["publish_at"]:
            errors.append("Для «запланировано» нужна дата выхода")
        elif parse_dt(a["publish_at"]) is None:
            errors.append("Дата выхода не распознана")
        if not a["body_md"].strip():
            errors.append("Нельзя запланировать пустую статью")
    # Обложка только со своего сайта: внешний адрес отвалится вместе с чужим хостингом.
    if a["cover_path"] and not a["cover_path"].startswith("/assets/"):
        errors.append("Обложка — путь вида /assets/blog/…")
    return errors


def _path(slug):
    return ARTICLES_DIR / f"{slug}.json"


def load_all():
    items = []
    if ARTICLES_DIR.is_dir():
        for f in sorted(ARTICLES_DIR.glob("*.json")):
            items.append(normalize(json.loads(f.read_text(encoding="utf-8"))))
    items.sort(key=lambda a: (a["publish_at"] or a["created_at"] or ""), reverse=True)
    return items


def get(slug):
    f = _path(slug)
    if not SLUG_RE.match(slug or "") or not f.is_file():
        return None
    return normalize(json.loads(f.read_text(encoding="utf-8")))


def save(article, old_slug=None):
    """Сохраняет статью; при смене адреса старый файл удаляется. Возвращает статью."""
    a = normalize(article)
    errors = validate(a)
    if errors:
        raise ValueError("; ".join(errors))
    if a["slug"] != old_slug and _path(a["slug"]).exists():
        raise ValueError("Такой адрес уже занят другой статьёй")
    prev = get(old_slug) if old_slug else None
    stamp = now().isoformat(timespec="seconds")
    a["created_at"] = (prev or {}).get("created_at") or a["created_at"] or stamp
    a["updated_at"] = stamp
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    _path(a["slug"]).write_text(json.dumps(a, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if old_slug and old_slug != a["slug"] and _path(old_slug).exists():
        _path(old_slug).unlink()
    return a


def delete(slug):
    f = _path(slug)
    if not SLUG_RE.match(slug or "") or not f.is_file():
        return False
    f.unlink()
    return True


def live(at=None):
    return [a for a in load_all() if is_live(a, at)]


def read_minutes(a):
    if a.get("read_min"):
        return a["read_min"]
    words = len(re.findall(r"\w+", a.get("body_md", "")))
    return max(1, round(words / WORDS_PER_MIN))


# ---------------------------------------------------------------- slug

_TR = dict(zip(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюяәғқңөұүһі",
    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s",
     "t", "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya",
     "a", "g", "k", "n", "o", "u", "u", "h", "i"],
))


def slugify(text):
    s = "".join(_TR.get(ch, ch) for ch in str(text).lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:80].rstrip("-") or "section"


# ---------------------------------------------------------------- markdown

_e = html.escape


def _safe_url(u):
    u = u.strip()
    if re.match(r"^(https?://|/|#|mailto:|tel:)", u):
        return u
    return "#"


def _inline(text):
    """Инлайн-разметка поверх экранированного текста: `код`, **жирный**, *курсив*, [ссылка](url)."""
    codes = []

    def keep_code(m):
        codes.append(f"<code>{_e(m.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep_code, text)
    links = []

    def keep_link(m):
        href = _safe_url(m.group(2))
        external = href.startswith("http") and "alfimov.kz" not in href
        rel = ' target="_blank" rel="noopener"' if external else ""
        links.append((f'<a href="{_e(href)}"{rel}>', m.group(1)))
        return f"\x01{len(links) - 1}\x01"

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", keep_link, text)
    text = _e(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"\x01(\d+)\x01", lambda m: links[int(m.group(1))][0] + _inline(links[int(m.group(1))][1]) + "</a>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)
    return text


def _table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], [r for r in cells[2:]]
    th = "".join(f"<th>{_inline(c)}</th>" for c in head)
    trs = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def markdown(md):
    """Markdown статьи → (html, оглавление [(id, текст h2)]).

    Поддерживается то, что нужно SEO-статье: ## и ### заголовки (с якорями), абзацы,
    списки, цитаты, таблицы, **жирный**, *курсив*, `код`, ссылки, картинки отдельной строкой
    ![подпись](/assets/…) — только со своего сайта. Сырой HTML экранируется.
    Заголовок уровня # превращается в ## — h1 на странице один, это заголовок статьи.
    """
    lines = (md or "").replace("\r\n", "\n").split("\n")
    out, toc, used = [], [], set()
    para, i = [], 0

    def flush():
        if para:
            out.append(f"<p>{_inline(' '.join(p.strip() for p in para))}</p>")
            para.clear()

    def anchor(text):
        base = slugify(re.sub(r"[*`\[\]()]", "", text))
        a, n = base, 2
        while a in used:
            a, n = f"{base}-{n}", n + 1
        used.add(a)
        return a

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush()
            i += 1
            continue
        img = re.match(r"^!\[([^\]]*)\]\((/assets/[^)\s]+)\)$", s)
        if img:
            flush()
            alt, src = img.group(1).strip(), img.group(2)
            cap = f"<figcaption>{_inline(alt)}</figcaption>" if alt else ""
            out.append(f'<figure><img src="{_e(src)}" alt="{_e(alt)}" loading="lazy">{cap}</figure>')
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.+?)\s*#*$", s)
        if m:
            flush()
            level = max(2, min(3, len(m.group(1)) if len(m.group(1)) > 1 else 2))
            text = m.group(2)
            aid = anchor(text)
            if level == 2:
                toc.append((aid, re.sub(r"[*`]", "", text)))
            out.append(f'<h{level} id="{aid}">{_inline(text)}</h{level}>')
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(_table(rows))
            continue
        if re.match(r"^([-*+]|\d+[.)])\s+", s):
            flush()
            ordered = bool(re.match(r"^\d", s))
            items = []
            while i < len(lines) and re.match(r"^\s*([-*+]|\d+[.)])\s+", lines[i]):
                item = re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", lines[i])
                i += 1
                while i < len(lines) and lines[i].startswith("  ") and lines[i].strip() and not re.match(r"^\s*([-*+]|\d+[.)])\s+", lines[i]):
                    item += " " + lines[i].strip()
                    i += 1
                items.append(f"<li>{_inline(item)}</li>")
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue
        if s.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote><p>{_inline(' '.join(quote))}</p></blockquote>")
            continue
        if re.match(r"^(-{3,}|\*{3,})$", s):
            flush()
            out.append("<hr>")
            i += 1
            continue
        para.append(line)
        i += 1
    flush()
    return "\n".join(out), toc
