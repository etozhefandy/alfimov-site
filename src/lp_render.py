"""Рекламные страницы заказчиков (/lp/<заказчик>/<страница>/) — только под трафик из Meta, noindex.

Контент страниц — в src/lp_<заказчик>.py (CLIENT = {...}), оформление и опрос — static/lp/<заказчик>/lp.css, lp.js.
build.py собирает отсюда HTML и список допустимых ответов опроса для PHP (dist/api/_lp-clients.json).
"""
import hashlib
import html
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"

WA_ICON = (
    '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 '
    "12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 "
    "1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 "
    "2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.5-.3Z\"/></svg>"
)

e = html.escape


def _wa(text, label, cls="btn btn-wa", icon=True):
    return f'<a class="{cls}" href="#" data-wa="{e(text)}">{WA_ICON if icon else ""}{e(label)}</a>'


def _facts(items):
    return '<ul class="facts">' + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"


def _who(h):
    if not h.get("who"):
        return ""
    return '<div class="who"><b>Подходит для:</b>' + "".join(f"<span>{e(x)}</span>" for x in h["who"]) + "</div>"


def _opt(o):
    """Вариант ответа: строка или (подпись, ветка) — ветка решает, какие вопросы пойдут дальше."""
    return (o, "") if isinstance(o, str) else o


def _step(q):
    multi = q.get("multi", False)
    inp = "checkbox" if multi else "radio"
    name = q["key"] + ("[]" if multi else "")
    cols = " cols" if q.get("cols", True) else ""
    opts = ""
    for o in q["options"]:
        label, branch = _opt(o)
        data = f' data-branch="{branch}"' if branch else ""
        opts += f'<label class="opt"><input type="{inp}" name="{name}" value="{e(label)}"{data}><span>{e(label)}</span></label>'
    other = ""
    if multi and "Другое" in q["options"]:
        other = ('<label class="field other" hidden><span>Что именно?</span>'
                 '<input name="comment" maxlength="300" placeholder="Напишите, что нужно"></label>')
    when = f' data-when="{" ".join(q["when"])}"' if q.get("when") else ""
    return (
        f'<div class="quiz-step" data-kind="{"multi" if multi else "one"}"{when}><div class="quiz-q">{e(q["q"])}</div>'
        f'<div class="quiz-hint"></div><div class="opts{cols}">{opts}</div>{other}</div>'
    )


def _quiz(p):
    qz = p["quiz"]
    steps = "".join(_step(q) for q in qz["questions"])
    contacts = (
        f'<div class="quiz-step" data-kind="contacts"><div class="quiz-q">{e(qz["contact_q"])}</div>'
        '<div class="quiz-hint" data-extra="менеджер напишет в WhatsApp или позвонит"></div>'
        '<label class="field"><span>Имя</span><input name="name" autocomplete="name" maxlength="80" required></label>'
        '<label class="field"><span>Телефон / WhatsApp</span><input name="phone" type="tel" inputmode="tel" autocomplete="tel" '
        'placeholder="+7 (701) 234-56-78" maxlength="30" required></label></div>'
    )
    return f"""<section class="soft" id="form">
  <div class="wrap two">
    <div>
      <h2>{e(qz["title"])}</h2>
      <p class="lead">{e(qz["lead"])}</p>
      {_facts(qz["facts"])}
    </div>
    <form class="quiz" id="quiz" novalidate>
      <div class="quiz-bar"><i></i></div>
      <input class="hp" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
      <input type="hidden" name="ts">
      {steps}{contacts}
      <div class="quiz-err" role="alert"></div>
      <div class="quiz-nav">
        <button type="button" class="back">← Назад</button>
        <button type="button" class="btn btn-main next">Далее</button>
        <button type="submit" class="btn btn-main submit">{e(qz["submit"])}</button>
      </div>
      <p class="legal">Нажимая кнопку, вы соглашаетесь на обработку контактных данных для связи по заявке.</p>
    </form>
    <template id="quiz-done">
      <div class="quiz-done">
        <div class="big">✅</div>
        <h3>Заявка отправлена</h3>
        <p>{e(qz["done"])}</p>
        {_wa(qz["done_wa"], "Написать в WhatsApp", icon=False)}
      </div>
    </template>
  </div>
</section>"""


def _catalog(p):
    c = p["catalog"]
    pics = ""
    if c.get("pics"):
        w, h = (1200, 1200) if c.get("square") else (1536, 1024)
        pics = f'<div class="pics{" square" if c.get("square") else ""}">' + "".join(
            f'<figure><img src="{e(g["img"])}" alt="{e(g["name"])}" width="{w}" height="{h}" loading="lazy">'
            f'<figcaption>{e(g["name"])}</figcaption></figure>'
            for g in c["pics"]
        ) + "</div>"
    groups = '<div class="groups">' + "".join(
        f'<div class="group"><h3>{e(g["title"])}</h3><p>{e(g["items"])}</p></div>' for g in c["groups"]
    ) + "</div>"
    note = f'<p class="note">{e(c["note"])}</p>' if c.get("note") else ""
    return f"""<section>
  <div class="wrap">
    <h2>{e(c["title"])}</h2>
    {groups}{pics}{note}
  </div>
</section>"""


def _bonus(p):
    b = p.get("bonus")
    if not b:
        return ""
    return f"""<section>
  <div class="wrap">
    <div class="bonus">
      <span class="bonus-tag">{e(b["tag"])}</span>
      <h2>{e(b["title"])}</h2>
      <p>{e(b["text"])}</p>
    </div>
  </div>
</section>"""


def _calc(p):
    """Блок «сколько вы платите прачечной сейчас» — только текст, расчёт делает менеджер."""
    c = p.get("calc")
    if not c:
        return ""
    rows = "".join(f'<div class="calc-row"><span>{e(a)}</span><b>{e(b)}</b></div>' for a, b in c["rows"])
    return f"""<section>
  <div class="wrap two">
    <div><h2>{e(c["title"])}</h2><p class="lead">{e(c["text"])}</p></div>
    <div class="calc">{rows}<p class="note">{e(c["note"])}</p></div>
  </div>
</section>"""


def _ver(path):
    """?v=<хэш файла>: css/js кэшируются на год (static/.htaccess), новая версия должна грузиться сразу."""
    return hashlib.md5((STATIC / path.lstrip("/")).read_bytes()).hexdigest()[:8]


def render(client, p):
    """HTML страницы p клиента client."""
    base = f'/lp/{client["slug"]}'
    h = p["hero"]
    pains = "".join(f'<div class="pain">{e(x)}</div>' for x in p["pains"]["items"])
    steps = "".join(f'<div class="step"><div><h3>{e(t)}</h3><p>{e(d)}</p></div></div>' for t, d in p["steps"])
    faq = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in p["faq"])
    f = p["final"]
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<title>{e(p["title"])}</title>
<meta name="description" content="{e(p["description"])}">
<meta property="og:title" content="{e(p["title"])}">
<meta property="og:description" content="{e(p["description"])}">
<meta property="og:image" content="https://alfimov.kz{e(h["img"])}">
<meta name="theme-color" content="#2e2463">
<link rel="icon" href="{base}/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}/lp.css?v={_ver(base + "/lp.css")}">
</head>
<body data-page="{e(p["slug"])}">

<header class="top">
  <div class="wrap">
    <img src="{base}/logo.svg" alt="{e(client["name"])}" width="176" height="46">
    {_wa(p["wa"], "WhatsApp", cls="call", icon=False)}
  </div>
</header>

<main>
<section class="hero">
  <div class="wrap grid">
    <div>
      <span class="eyebrow">{e(h["eyebrow"])}</span>
      <h1>{e(h["h1"])}</h1>
      <p class="lead">{e(h["lead"])}</p>
      {_who(h)}
      {_facts(h["facts"])}
      <div class="btns">
        <a class="btn btn-main" href="#form">{e(h["cta"])}</a>
        {_wa(p["wa"], "Написать в WhatsApp")}
      </div>
    </div>
    <div class="hero-img"><img src="{e(h["img"])}" alt="{e(h["img_alt"])}" width="1536" height="1024" fetchpriority="high"></div>
  </div>
</section>

<section class="soft">
  <div class="wrap">
    <h2>{e(p["pains"]["title"])}</h2>
    <div class="pains">{pains}</div>
    <div class="answer">{e(p["pains"]["answer"])}</div>
  </div>
</section>

{_catalog(p)}
{_calc(p)}
{_bonus(p)}
{_quiz(p)}

<section>
  <div class="wrap">
    <h2>Как работаем</h2>
    <div class="steps">{steps}</div>
  </div>
</section>

<section class="soft">
  <div class="wrap">
    <h2>Частые вопросы</h2>
    {faq}
  </div>
</section>

<section class="final">
  <div class="wrap">
    <h2>{e(f["title"])}</h2>
    <p>{e(f["text"])}</p>
    <div class="btns final-btns">
      {_wa(p["wa"], "Написать в WhatsApp")}
      <a class="btn btn-ghost" href="#form">{e(h["cta"])}</a>
    </div>
  </div>
</section>
</main>

<footer class="foot">© {e(client["name"])} — {e(client["tagline"])}</footer>

<div class="sticky">
  {_wa(p["wa"], "WhatsApp", icon=False)}
  <a class="btn btn-main" href="#form">{e(p["sticky_cta"])}</a>
</div>

<script src="{base}/lp.js?v={_ver(base + "/lp.js")}" defer></script>
</body>
</html>
"""


def answers(client):
    """Допустимые ответы опроса для PHP: страница → поле → [подпись, варианты]. Чужие значения в заявку не попадут.
    Один и тот же вопрос в разных ветках («Что нужно» у отеля и ресторана) — варианты объединяются."""
    pages = {}
    for p in client["pages"]:
        qs = {}
        for q in p["quiz"]["questions"]:
            opts = [_opt(o)[0] for o in q["options"]]
            if q["key"] in qs:
                qs[q["key"]][1] += [o for o in opts if o not in qs[q["key"]][1]]
            else:
                qs[q["key"]] = [q["label"], opts]
        pages[p["slug"]] = {"title": p["lead_title"], "questions": qs}
    return {"name": client["name"], "pages": pages}
