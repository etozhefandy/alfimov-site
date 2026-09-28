#!/usr/bin/env python3
"""Генератор статического сайта alfimov.kz (без зависимостей, только stdlib).

    python3 build.py            # собирает сайт в dist/
    python3 build.py --serve    # собирает и поднимает http://localhost:8000

Дизайн по design brief: Marketing × Data × Technology — белый, почти чёрный,
серые и один синий акцент; типографика и сетка вместо декора.
"""
import hashlib
import html
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
import content_kz  # noqa: E402
import content_ru  # noqa: E402

import blog  # noqa: E402

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
STATIC = ROOT / "static"

SITE_URL = "https://alfimov.kz"
BRAND = "Alfimov"
PHONE_DISPLAY = "+7 776 902 66 69"
PHONE_TEL = "+77769026669"
WHATSAPP_URL = "https://wa.me/77769026669"
TELEGRAMS = ["fandylol"]
INSTAGRAM = "etozhefandy"
INSTAGRAM_URL = f"https://www.instagram.com/{INSTAGRAM}/"
FONT_URL = (
    "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500;600;700"
    "&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"
)
ASSET_VER = hashlib.md5(
    b"".join((STATIC / "assets" / f).read_bytes() for f in ("style.css", "main.js"))
).hexdigest()[:8]

LANGS = [content_ru, content_kz]
HREFLANG = {"ru": "ru-KZ", "kk": "kk-KZ"}

e = html.escape


# ---------------------------------------------------------------- icons (только функциональные)

ICONS = {
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "arrow-down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "phone": '<path d="M5 4h3.5l1.5 4.5-2 1.5a11 11 0 0 0 6 6l1.5-2 4.5 1.5V19a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/>',
    "whatsapp": '<path d="M4 20l1.2-4A8 8 0 1 1 8 18.8Z"/><path d="M9 9.5c0 3 2.5 5.5 5.5 5.5l1-1.5-2-1-1 .8c-1-.5-2-1.5-2.3-2.3l.8-1-1-2-1 .5Z"/>',
    "telegram": '<path d="M21 4 3 11l6 2.2L18 7l-7 7.5V20l3-3.5 4 3Z"/>',
    "menu": '<path d="M4 8h16M4 16h16"/>',
    "instagram": '<rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="3.8"/><circle cx="17.2" cy="6.8" r=".7" fill="currentColor" stroke="none"/>',
}


def icon(name, cls="ic"):
    return (
        f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'
    )


# Логотип ALFIMOV.KZ (векторные контуры из brand-kit, static/assets/brand/).
LOGO_BLUE = "#1769FF"
LOGO_MARK_PATHS = (
    f'<path fill="{LOGO_BLUE}" d="M56 114 80 78 Q84 72 90 72 H108 L81 114Z"/>'
    '<path d="M102 47 108 38 H123 L166 114 H143Z"/>'
)
LOGO_WORD_PATHS = (
    '<path d="M196 44H216V97H271V114H196Z"/>'
    '<path d="M300 44H375V60H320V75H369V91H320V114H300Z"/>'
    '<path d="M403 44H423V114H403Z"/>'
    '<path d="M455 44H471L510 82 548 44H564V114H545V74L510 108 474 75V114H455Z"/>'
    '<path fill-rule="evenodd" d="M644 43C608 43 594 52 594 79S608 114 644 114 695 106 695 79 681 43 644 43ZM644 60C669 60 675 63 675 79S669 98 644 98 614 94 614 79 620 60 644 60Z"/>'
    '<path d="M720 44H743L773 92 801 44H824L782 114H762Z"/>'
    '<path d="M854 108A6 6 0 1 1 842 108A6 6 0 1 1 854 108Z"/>'
    '<path d="M890 44H896V80L935 44H944L908 77 946 114H937L896 86V114H890Z"/>'
    '<path d="M979 44H1036V50L988 108H1037V114H978V108L1026 50H979Z"/>'
)


def logo(href):
    return (
        f'<a class="logo" href="{href}" aria-label="ALFIMOV.KZ">'
        f'<svg viewBox="52 34 990 84" fill="currentColor" aria-hidden="true">{LOGO_MARK_PATHS}{LOGO_WORD_PATHS}</svg></a>'
    )


# ---------------------------------------------------------------- helpers

def url(c, slug=""):
    """Путь страницы с языковым префиксом, всегда со слешем на конце."""
    return f"{c.PREFIX}/{slug + '/' if slug else ''}"


def link(c, target):
    """Ссылка из контента: '#якорь' — на главной, иначе slug услуги."""
    return f"{url(c)}{target}" if target.startswith("#") else url(c, target)


def other_lang(c):
    return content_kz if c is content_ru else content_ru


def org_schema():
    return {
        "@type": "ProfessionalService",
        "@id": f"{SITE_URL}/#org",
        "name": "ALFIMOV.KZ",
        "alternateName": BRAND,
        "url": f"{SITE_URL}/",
        "logo": f"{SITE_URL}/assets/brand/icon-512.png",
        "image": f"{SITE_URL}/assets/og.png",
        "telephone": PHONE_TEL,
        "priceRange": "$$",
        "address": {"@type": "PostalAddress", "addressCountry": "KZ"},
        "areaServed": {"@type": "Country", "name": "Kazakhstan"},
        "sameAs": [INSTAGRAM_URL, *(f"https://t.me/{t}" for t in TELEGRAMS)],
    }


def faq_schema(items):
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in items
        ],
    }


def breadcrumbs_schema(trail):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": SITE_URL + path}
            for i, (name, path) in enumerate(trail)
        ],
    }


def price_text(c, slug, short=False):
    """«от 200 000 ₸ в месяц» / «по запросу»."""
    amount, period = c.PRICES.get(slug, (None, None))
    if amount is None:
        return c.UI["price_on_request"]
    s = c.UI["price_from"].format(sum=f"{amount:,}".replace(",", "\u00a0"))
    return s if short or period != "month" else f"{s} {c.UI['price_month']}"


def offer_schema(c, slug):
    amount, _ = c.PRICES.get(slug, (None, None))
    if amount is None:
        return {}
    return {"offers": {"@type": "Offer", "priceCurrency": "KZT",
                       "priceSpecification": {"@type": "UnitPriceSpecification", "minPrice": amount,
                                              "priceCurrency": "KZT", "unitText": "MON"}}}


def eyebrow(num, text):
    return f'<p class="eyebrow"><span>{num}</span>{e(text)}</p>'


# ---------------------------------------------------------------- partials

def header(c, alt_path):
    ui = c.UI
    nav_services = "".join(
        f'<li><a href="{url(c, s["slug"])}">{e(s["name"])}</a></li>' for s in c.SERVICES
    )
    cases_link = f'<a href="{url(c)}#cases">{e(c.HOME["cases_eyebrow"])}</a>' if c.CASES else ""
    # Блог — только русский и только когда вышла хотя бы одна статья: пустой раздел в меню не нужен.
    blog_link = f'<a href="{BLOG_PATH}">{e(BLOG_UI["nav"])}</a>' if c is content_ru and blog.live() else ""
    return f"""
<header class="hdr">
  <div class="wrap hdr-in">
    {logo(url(c))}
    <nav class="nav" id="nav" aria-label="Main">
      <div class="dd">
        <a href="{url(c)}#services">{e(ui['nav_services'])}</a>
        <ul class="dd-menu">{nav_services}</ul>
      </div>
      <a href="{url(c)}#approach">{e(c.HOME['approach_eyebrow'])}</a>
      {cases_link}
      <a href="{url(c)}#automation">{e(c.HOME['automation_eyebrow'])}</a>
      {blog_link}
      <a href="{url(c, 'kontakty')}">{e(ui['nav_contacts'])}</a>
      <a class="lang" href="{alt_path}" hreflang="{other_lang(c).LANG}" aria-label="{e(ui['lang_switch_label'])}">{e(ui['lang_switch'])}</a>
      <a class="btn btn-sm" href="#lead">{e(ui['cta'])}</a>
    </nav>
    <button class="burger" type="button" aria-controls="nav" aria-expanded="false" aria-label="Menu">{icon('menu')}</button>
  </div>
</header>"""


def contact_links():
    tg = "".join(
        f'<a class="clink" href="https://t.me/{t}" target="_blank" rel="noopener">{icon("telegram")}@{t}</a>'
        for t in TELEGRAMS
    )
    return (
        f'<a class="clink" href="tel:{PHONE_TEL}">{icon("phone")}{PHONE_DISPLAY}</a>'
        f'<a class="clink" href="{WHATSAPP_URL}" target="_blank" rel="noopener">{icon("whatsapp")}WhatsApp</a>'
        + tg
        + f'<a class="clink" href="{INSTAGRAM_URL}" target="_blank" rel="noopener">{icon("instagram")}Instagram @{INSTAGRAM}</a>'
    )


def lead_form(c, source, title=None, lead=None, num="→"):
    ui = c.UI
    title = title or c.HOME["final_title"]
    lead = lead or c.HOME["final_lead"]
    return f"""
<section class="final" id="lead">
  <div class="wrap final-in">
    <div class="final-copy rv">
      <h2>{e(title)}</h2>
      <p>{e(lead)}</p>
      <div class="clinks">{contact_links()}</div>
    </div>
    <form class="form rv" action="/api/send.php" method="post" data-ok="{e(ui['form_ok'])}" data-err="{e(ui['form_err'])}" data-sending="{e(ui['form_sending'])}">
      <input type="hidden" name="source" value="{e(source)}">
      <input type="hidden" name="lang" value="{c.LANG}">
      <input type="hidden" name="ts" value="">
      <div class="hp" aria-hidden="true"><label>Company<input type="text" name="company" tabindex="-1" autocomplete="off"></label></div>
      <label class="fld"><span>{e(ui['form_name'])}</span><input type="text" name="name" required maxlength="80" autocomplete="name"></label>
      <label class="fld"><span>{e(ui['form_phone'])}</span><input type="text" name="contact" required maxlength="80" autocomplete="tel" inputmode="tel"></label>
      <label class="fld"><span>{e(ui['form_message'])}</span><textarea name="message" rows="2" maxlength="1000"></textarea></label>
      <button class="btn btn-lg" type="submit">{e(ui['form_submit'])} {icon('arrow', 'ic ic-sm')}</button>
      <p class="form-status" role="status" aria-live="polite"></p>
      <p class="consent">{e(ui['form_consent'])}</p>
    </form>
  </div>
</section>"""


def footer(c):
    ui = c.UI
    svc = "".join(f'<li><a href="{url(c, s["slug"])}">{e(s["name"])}</a></li>' for s in c.SERVICES)
    tg = "".join(f'<li><a href="https://t.me/{t}" target="_blank" rel="noopener">Telegram @{t}</a></li>' for t in TELEGRAMS)
    return f"""
<footer class="ftr">
  <div class="wrap ftr-in">
    <div class="ftr-brand">
      {logo(url(c))}
      <p>{e(ui['footer_about'])}</p>
    </div>
    <div>
      <h3>{e(ui['footer_services'])}</h3>
      <ul>{svc}</ul>
    </div>
    <div>
      <h3>{e(ui['footer_contacts'])}</h3>
      <ul>
        <li><a href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a></li>
        <li><a href="{WHATSAPP_URL}" target="_blank" rel="noopener">WhatsApp</a></li>
        {tg}
        <li><a href="{INSTAGRAM_URL}" target="_blank" rel="noopener">Instagram @{INSTAGRAM}</a></li>
      </ul>
    </div>
  </div>
  <div class="wrap ftr-bottom"><span>© {date.today().year} ALFIMOV.KZ</span><span>{e(ui['rights'])}</span></div>
</footer>"""


def page(c, *, path, title, desc, body, schema, alt_path, noindex=False, og_type="website", image=None):
    graph = {"@context": "https://schema.org", "@graph": [org_schema(), *schema]}
    o = other_lang(c)
    alternates = ""
    if alt_path is None:
        # Нет перевода (статьи блога — только RU): hreflang не ставим, переключатель языка ведёт на главную.
        alt_path = url(o)
    elif not noindex:
        alternates = (
            f'<link rel="alternate" hreflang="{HREFLANG[c.LANG]}" href="{SITE_URL}{path}">\n'
            f'<link rel="alternate" hreflang="{HREFLANG[o.LANG]}" href="{SITE_URL}{alt_path}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{SITE_URL}{path if c is content_ru else alt_path}">'
        )
    robots = '<meta name="robots" content="noindex">' if noindex else ""
    og_locale = "ru_KZ" if c.LANG == "ru" else "kk_KZ"
    return f"""<!doctype html>
<html lang="{c.LANG}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{robots}
<link rel="canonical" href="{SITE_URL}{path}">
{alternates}
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="ALFIMOV.KZ">
<meta property="og:locale" content="{og_locale}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{SITE_URL}{path}">
<meta property="og:image" content="{SITE_URL}{image or '/assets/og.png'}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/brand/apple-touch-icon.png">
<link rel="manifest" href="/assets/brand/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONT_URL}">
<link rel="stylesheet" href="/assets/style.css?v={ASSET_VER}">
<script>document.documentElement.classList.add('js')</script>
<script type="application/ld+json">{json.dumps(graph, ensure_ascii=False)}</script>
</head>
<body>
{header(c, alt_path)}
<main>
{body}
</main>
{footer(c)}
<script src="/assets/main.js?v={ASSET_VER}" defer></script>
</body>
</html>
"""


def faq_block(c, items, num):
    qs = "".join(
        f'<details class="qa"><summary>{e(q)}{icon("plus", "ic qa-ic")}</summary><p>{e(a)}</p></details>'
        for q, a in items
    )
    return f"""
<section class="sec" id="faq">
  <div class="wrap split">
    <div class="split-head rv">{eyebrow(num, c.HOME['faq_eyebrow'])}<h2>{e(c.UI['faq_title'])}</h2></div>
    <div class="faq rv">{qs}</div>
  </div>
</section>"""


def flow(steps, loop_text=None):
    """Схема пути: горизонтальная на десктопе, вертикальная на мобиле."""
    items = "".join(
        f'<li style="--i:{i}"><span class="flow-n">{i + 1:02d}</span><h3>{e(t)}</h3><p>{e(d)}</p></li>'
        for i, (t, d) in enumerate(steps)
    )
    loop = f'<p class="flow-loop">↺ {e(loop_text)}</p>' if loop_text else ""
    return f'<div class="flow rv" style="--n:{len(steps)}"><ol>{items}</ol>{loop}</div>'


def service_rows(c, exclude=None):
    rows = []
    n = 0
    for s in c.SERVICES:
        if s["slug"] == exclude:
            continue
        n += 1
        rows.append(
            f'<a class="row-link" href="{url(c, s["slug"])}"><span class="row-n">{n:02d}</span>'
            f'<span class="row-t">{e(s["name"])}</span><span class="row-d">{e(s["short"])}</span>'
            f'<span class="row-p">{e(price_text(c, s["slug"], short=True))}</span>'
            f'{icon("arrow", "ic row-arrow")}</a>'
        )
    return f'<div class="rows rv">{"".join(rows)}</div>'


def clients_strip(c):
    if not c.CLIENTS:
        return ""
    names = "".join(f"<li>{e(n)}</li>" for n in c.CLIENTS)
    return f'<section class="clients"><div class="wrap clients-in"><p>{e(c.HOME["clients_title"])}</p><ul>{names}</ul></div></section>'


def cases_block(c, num):
    if not c.CASES:
        return ""
    cards = []
    for k in c.CASES:
        metrics = "".join(
            f'<div class="m"><dt>{e(label)}</dt><dd><span class="m-before">{e(before)}</span>'
            f'{icon("arrow", "ic ic-sm")}<span class="m-after">{e(after)}</span></dd></div>'
            for label, before, after in k["metrics"]
        )
        cards.append(
            f'<article class="case rv"><header><h3>{e(k["name"])}</h3><p class="case-niche">{e(k["niche"])}'
            f'{" · " + e(k["period"]) if k.get("period") else ""}</p></header>'
            f'<dl class="case-metrics">{metrics}</dl>'
            f'<div class="case-text"><p><b>{e(c.UI.get("case_task", "Задача"))}.</b> {e(k["task"])}</p>'
            f'<p><b>{e(c.UI.get("case_solution", "Решение"))}.</b> {e(k["solution"])}</p></div></article>'
        )
    h = c.HOME
    return f"""
<section class="sec" id="cases">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow(num, h['cases_eyebrow'])}<h2>{e(h['cases_title'])}</h2></div>
    <div class="cases">{"".join(cards)}</div>
  </div>
</section>"""


# ---------------------------------------------------------------- pages

def build_home(c):
    h, ui = c.HOME, c.UI
    title_post = f" {e(h['hero_title_post'])}" if h.get("hero_title_post") else ""
    facts = "".join(f'<li><b>{e(a)}</b><span>{e(b)}</span></li>' for a, b in h["hero_facts"])

    directions = []
    for i, (name, desc, links) in enumerate(h["directions"], 1):
        ls = "".join(f'<a href="{link(c, t)}">{e(label)} {icon("arrow", "ic ic-sm")}</a>' for label, t in links)
        directions.append(
            f'<li class="dir rv"><span class="dir-n">{i:02d}</span><h3>{e(name)}</h3>'
            f'<p>{e(desc)}</p><div class="dir-links">{ls}</div></li>'
        )
    all_q, all_label, all_slug = h["directions_all"]

    sources = "".join(f"<li>{e(s)}</li>" for s in h["analytics_sources"])
    result = "".join(f"<li>{e(r)}</li>" for r in h["analytics_result"])
    pipeline = '<span class="pipe-arrow">→</span>'.join(f"<span>{e(p)}</span>" for p in h["automation_pipeline"])
    auto = "".join(
        f'<li class="rv"><span class="auto-n">{i:02d}</span><h3>{e(t)}</h3><p>{e(d)}</p></li>'
        for i, (t, d) in enumerate(h["automation"], 1)
    )

    n = iter(f"{i:02d}" for i in range(1, 20))
    body = f"""
<section class="hero">
  <div class="wrap">
    <p class="hero-kicker rv">{e(h['hero_kicker'])}</p>
    <h1 class="rv">{e(h['hero_title_pre'])} <em>{e(h['hero_title_accent'])}</em>{title_post}</h1>
    <div class="hero-row">
      <p class="hero-lead rv">{e(h['hero_lead'])}</p>
      <div class="hero-cta rv">
        <a class="btn btn-lg" href="#lead">{e(ui['cta'])} {icon('arrow', 'ic ic-sm')}</a>
        <a class="tlink" href="{'#cases' if c.CASES else '#approach'}">{e(h['cases_eyebrow'] if c.CASES else h['hero_cta_secondary'])} {icon('arrow-down', 'ic ic-sm')}</a>
      </div>
    </div>
    <ul class="facts rv">{facts}</ul>
  </div>
</section>
{clients_strip(c)}
<section class="sec" id="services">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow(next(n), h['directions_eyebrow'])}<h2>{e(h['directions_title'])}</h2><p>{e(h['directions_lead'])}</p></div>
    <ol class="dirs">{"".join(directions)}</ol>
    <a class="dir-all rv" href="{url(c, all_slug)}"><span>{e(all_q)}</span><b>{e(all_label)}</b>{icon('arrow')}</a>
  </div>
</section>
<section class="sec sec-soft" id="approach">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow(next(n), h['approach_eyebrow'])}<h2>{e(h['approach_title'])}</h2><p>{e(h['approach_lead'])}</p></div>
    {flow(h['approach'], h['approach_loop'])}
  </div>
</section>
<section class="sec" id="analytics">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow(next(n), h['analytics_eyebrow'])}<h2>{e(h['analytics_title'])}</h2><p>{e(h['analytics_lead'])}</p></div>
    <div class="merge rv">
      <ul class="merge-src">{sources}</ul>
      <div class="merge-join" aria-hidden="true"><span></span></div>
      <div class="merge-out"><h3>{e(h['analytics_result_title'])}</h3><ul>{result}</ul></div>
    </div>
  </div>
</section>
<section class="sec sec-dark" id="automation">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow(next(n), h['automation_eyebrow'])}<h2>{e(h['automation_title'])}</h2><p>{e(h['automation_lead'])}</p></div>
    <p class="pipe rv">{pipeline}</p>
    <ul class="auto">{auto}</ul>
  </div>
</section>
{cases_block(c, next(n))}
{faq_block(c, h['faq'], next(n))}
{lead_form(c, 'home')}
"""
    path = url(c)
    alt = url(other_lang(c))
    return path, page(
        c, path=path, title=h["meta_title"], desc=h["meta_desc"], body=body, alt_path=alt,
        schema=[
            {"@type": "WebSite", "@id": f"{SITE_URL}/#site", "url": f"{SITE_URL}/", "name": "ALFIMOV.KZ", "inLanguage": c.LANG},
            faq_schema(h["faq"]),
        ],
    )


def build_service(c, s):
    ui, h = c.UI, c.HOME
    path = url(c, s["slug"])
    alt = url(other_lang(c), s["slug"])
    intro = "".join(f"<p>{e(p)}</p>" for p in s["intro"])
    includes = "".join(
        f'<li class="rv"><span class="inc-n">{i:02d}</span><div><h3>{e(t)}</h3><p>{e(d)}</p></div></li>'
        for i, (t, d) in enumerate(s["includes"], 1)
    )
    for_whom = "".join(f"<li>{e(x)}</li>" for x in s["for_whom"])
    body = f"""
<section class="hero hero-svc">
  <div class="wrap">
    <nav class="crumbs rv" aria-label="breadcrumbs"><a href="{url(c)}">{e(ui['breadcrumbs_home'])}</a><span>/</span><a href="{url(c)}#services">{e(ui['nav_services'])}</a></nav>
    <h1 class="rv">{e(s['h1'])}</h1>
    <div class="hero-row">
      <p class="hero-lead rv">{e(s['lead'])}</p>
      <div class="hero-cta rv">
        <div class="price"><span>{e(ui['price_label'])}</span><b>{e(price_text(c, s['slug']))}</b><small>{e(ui['price_note'])}</small></div>
        <a class="btn btn-lg" href="#lead">{e(ui['cta'])} {icon('arrow', 'ic ic-sm')}</a>
      </div>
    </div>
  </div>
</section>
<section class="sec">
  <div class="wrap split">
    <div class="split-head rv">{eyebrow('01', s['name'])}</div>
    <div class="prose rv">{intro}</div>
  </div>
</section>
<section class="sec sec-soft">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow('02', s['name'])}<h2>{e(ui['includes_title'])}</h2></div>
    <ul class="incl">{includes}</ul>
  </div>
</section>
<section class="sec">
  <div class="wrap split">
    <div class="split-head rv">{eyebrow('03', s['name'])}<h2>{e(ui['for_whom_title'])}</h2></div>
    <ul class="dash rv">{for_whom}</ul>
  </div>
</section>
<section class="sec sec-soft">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow('04', s['name'])}<h2>{e(ui['steps_title'])}</h2></div>
    {flow(s['steps'])}
  </div>
</section>
{faq_block(c, s['faq'], '05')}
{lead_form(c, s['slug'])}
<section class="sec">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow('06', s['name'])}<h2>{e(ui['other_services'])}</h2></div>
    {service_rows(c, exclude=s['slug'])}
  </div>
</section>
"""
    schema = [
        {
            "@type": "Service",
            "name": s["h1"],
            "description": s["meta_desc"],
            "serviceType": s["name"],
            "provider": {"@id": f"{SITE_URL}/#org"},
            "areaServed": {"@type": "Country", "name": "Kazakhstan"},
            "url": SITE_URL + path,
            "inLanguage": c.LANG,
            **offer_schema(c, s["slug"]),
        },
        faq_schema(s["faq"]),
        breadcrumbs_schema([(ui["breadcrumbs_home"], url(c)), (s["name"], path)]),
    ]
    return path, page(c, path=path, title=s["meta_title"], desc=s["meta_desc"], body=body, schema=schema, alt_path=alt)


def build_contacts(c):
    k, ui = c.CONTACTS, c.UI
    path = url(c, "kontakty")
    alt = url(other_lang(c), "kontakty")
    body = f"""
<section class="hero hero-svc">
  <div class="wrap">
    <nav class="crumbs rv" aria-label="breadcrumbs"><a href="{url(c)}">{e(ui['breadcrumbs_home'])}</a></nav>
    <h1 class="rv">{e(k['h1'])}</h1>
    <p class="hero-lead rv">{e(k['lead'])}</p>
    <div class="clinks clinks-lg rv">{contact_links()}</div>
  </div>
</section>
<section class="sec">
  <div class="wrap split">
    <div class="split-head rv">{eyebrow('01', k['area_title'])}<h2>{e(k['area_title'])}</h2></div>
    <div class="prose rv"><p>{e(k['area_text'])}</p></div>
  </div>
</section>
{lead_form(c, 'contacts')}
"""
    schema = [breadcrumbs_schema([(ui["breadcrumbs_home"], url(c)), (k["h1"], path)])]
    return path, page(c, path=path, title=k["meta_title"], desc=k["meta_desc"], body=body, schema=schema, alt_path=alt)


def build_404():
    c, ui = content_ru, content_ru.UI
    kz = content_kz.UI
    body = f"""
<section class="hero hero-svc">
  <div class="wrap">
    <p class="hero-kicker">404</p>
    <h1>{e(ui['not_found_title'])}</h1>
    <p class="hero-lead">{e(ui['not_found_text'])}<br><span class="muted">{e(kz['not_found_text'])}</span></p>
    <div class="hero-cta"><a class="btn btn-lg" href="/">{e(ui['not_found_btn'])}</a><a class="tlink" href="/kz/">{e(kz['not_found_btn'])} {icon('arrow', 'ic ic-sm')}</a></div>
  </div>
</section>
<section class="sec"><div class="wrap">{service_rows(c)}</div></section>
"""
    return page(c, path="/404.html", title="404 — ALFIMOV.KZ", desc=ui["not_found_text"], body=body, schema=[], alt_path="/kz/", noindex=True)


# ---------------------------------------------------------------- blog

BLOG_PATH = "/blog/"
BLOG_UI = {
    "nav": "Блог",
    "title": "Блог о маркетинге и рекламе в Казахстане",
    "meta_title": "Блог о маркетинге и рекламе в Казахстане | Alfimov",
    "meta_desc": "Разборы и практические материалы агентства Alfimov: таргет, контекст, SEO, SMM и аналитика для бизнеса в Казахстане.",
    "lead": "Практические разборы о рекламе и маркетинге: как устроены кампании, что считать и какие решения за этим стоят.",
    "toc": "Содержание",
    "summary": "Коротко",
    "read": "мин чтения",
    "related": "Читайте также",
    "all": "Все статьи",
    "cta_title": "Нужна помощь с продвижением?",
    "cta_lead": "Расскажите о задаче — разберём ваш случай и предложим план на месяц.",
}
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря")


def post_date(a, field="publish_at"):
    dt = blog.parse_dt(a.get(field)) or blog.parse_dt(a.get("publish_at")) or blog.now()
    return dt.date().isoformat()


def human_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def article_path(a):
    return f"{BLOG_PATH}{a['slug']}/"


def post_meta(a):
    parts = [human_date(post_date(a)), f"{blog.read_minutes(a)} {BLOG_UI['read']}"]
    if a.get("category"):
        parts.insert(0, a["category"])
    return " · ".join(e(p) for p in parts)


def post_cards(posts):
    return "".join(
        f'<a class="post-card rv" href="{article_path(a)}">'
        f'<span class="post-meta">{post_meta(a)}</span>'
        f'<h3>{e(a["title"])}</h3><p>{e(a["description"] or a["lead"])}</p>'
        f'<span class="tlink">{e(content_ru.UI["more"])} {icon("arrow", "ic ic-sm")}</span></a>'
        for a in posts
    )


def build_blog_index(posts):
    c, ui = content_ru, content_ru.UI
    body = f"""
<section class="hero hero-svc">
  <div class="wrap">
    <nav class="crumbs rv" aria-label="breadcrumbs"><a href="{url(c)}">{e(ui['breadcrumbs_home'])}</a><span>/</span><span>{e(BLOG_UI['nav'])}</span></nav>
    <h1 class="rv">{e(BLOG_UI['title'])}</h1>
    <p class="hero-lead rv">{e(BLOG_UI['lead'])}</p>
  </div>
</section>
<section class="sec sec-tight">
  <div class="wrap"><div class="post-grid">{post_cards(posts)}</div></div>
</section>
{lead_form(c, 'blog', BLOG_UI['cta_title'], BLOG_UI['cta_lead'])}
"""
    schema = [
        {"@type": "Blog", "@id": f"{SITE_URL}{BLOG_PATH}#blog", "name": BLOG_UI["title"], "url": f"{SITE_URL}{BLOG_PATH}",
         "publisher": {"@id": f"{SITE_URL}/#org"}, "inLanguage": "ru-KZ",
         "blogPost": [{"@type": "BlogPosting", "headline": a["title"], "url": f"{SITE_URL}{article_path(a)}",
                       "datePublished": post_date(a)} for a in posts]},
        breadcrumbs_schema([(ui["breadcrumbs_home"], url(c)), (BLOG_UI["nav"], BLOG_PATH)]),
    ]
    return page(c, path=BLOG_PATH, title=BLOG_UI["meta_title"], desc=BLOG_UI["meta_desc"], body=body, schema=schema, alt_path=None)


def build_article(a, posts):
    """Страница статьи. posts — вышедшие статьи (для «Читайте также»)."""
    c, ui = content_ru, content_ru.UI
    path = article_path(a)
    body_html, toc = blog.markdown(a["body_md"])
    others = [p for p in posts if p["slug"] != a["slug"]]
    by_slug = {p["slug"]: p for p in others}
    related = [by_slug[s] for s in a["related"] if s in by_slug]
    related += [p for p in others if p not in related][: max(0, 3 - len(related))]

    toc_html = ""
    if len(toc) >= 2:
        items = "".join(f'<li><a href="#{aid}">{e(t)}</a></li>' for aid, t in toc)
        toc_html = f'<nav class="art-toc" aria-label="{e(BLOG_UI["toc"])}"><p class="eyebrow">{e(BLOG_UI["toc"])}</p><ol>{items}</ol></nav>'
    cover = f'<img class="art-cover" src="{e(a["cover_path"])}" alt="{e(a["title"])}" loading="lazy">' if a["cover_path"] else ""
    summary = (f'<aside class="art-summary"><p class="eyebrow"><span>→</span>{e(BLOG_UI["summary"])}</p>'
               f'<p>{e(a["summary"])}</p></aside>') if a["summary"] else ""
    author = f' · {e(a["author"])}' if a["author"] else ""
    faq = faq_block(c, a["faq"], "?") if a["faq"] else ""
    related_html = ""
    if related:
        related_html = f"""
<section class="sec sec-soft">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow('→', BLOG_UI['related'])}<h2>{e(BLOG_UI['related'])}</h2></div>
    <div class="post-grid">{post_cards(related)}</div>
    <p class="post-all"><a class="tlink" href="{BLOG_PATH}">{e(BLOG_UI['all'])} {icon('arrow', 'ic ic-sm')}</a></p>
  </div>
</section>"""

    body = f"""
<section class="hero hero-svc hero-art">
  <div class="wrap">
    <nav class="crumbs rv" aria-label="breadcrumbs"><a href="{url(c)}">{e(ui['breadcrumbs_home'])}</a><span>/</span><a href="{BLOG_PATH}">{e(BLOG_UI['nav'])}</a></nav>
    <p class="post-meta rv">{post_meta(a)}{author}</p>
    <h1 class="rv">{e(a['title'])}</h1>
    {f'<p class="hero-lead rv">{e(a["lead"])}</p>' if a['lead'] else ''}
  </div>
</section>
<section class="sec sec-tight">
  <div class="wrap art{' art-has-toc' if toc_html else ''}">
    {toc_html}
    <article class="art-body">
      {cover}
      {summary}
      <div class="md">{body_html}</div>
    </article>
  </div>
</section>
{faq}
{related_html}
{lead_form(c, 'blog:' + a['slug'], BLOG_UI['cta_title'], BLOG_UI['cta_lead'])}
"""
    image = a["cover_path"] or None
    posting = {
        "@type": "BlogPosting",
        "headline": a["title"],
        "description": a["description"],
        "datePublished": post_date(a),
        "dateModified": post_date(a, "updated_at"),
        "inLanguage": "ru-KZ",
        "mainEntityOfPage": f"{SITE_URL}{path}",
        "image": f"{SITE_URL}{image or '/assets/og.png'}",
        "author": {"@type": "Person", "name": a["author"]} if a["author"] else {"@id": f"{SITE_URL}/#org"},
        "publisher": {"@id": f"{SITE_URL}/#org"},
    }
    if a["keywords"]:
        posting["keywords"] = ", ".join(a["keywords"])
    if a["category"]:
        posting["articleSection"] = a["category"]
    schema = [posting, breadcrumbs_schema([(ui["breadcrumbs_home"], url(c)), (BLOG_UI["nav"], BLOG_PATH), (a["title"], path)])]
    if a["faq"]:
        schema.append(faq_schema(a["faq"]))
    return path, page(c, path=path, title=a["seo_title"] or f"{a['title']} | Alfimov", desc=a["description"] or a["lead"],
                      body=body, schema=schema, alt_path=None, og_type="article", image=image)


# ---------------------------------------------------------------- build

def write(path, content):
    target = DIST / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def sitemap(paths, single=()):
    """paths — страницы с парой RU/KZ; single — [(путь, lastmod)] без перевода (блог)."""
    today = date.today().isoformat()
    ru_paths = [p for p in paths if not p.startswith("/kz/")]
    rows = []
    for ru in ru_paths:
        kz = "/kz" + ru
        for p in (ru, kz):
            rows.append(
                f"<url><loc>{SITE_URL}{p}</loc><lastmod>{today}</lastmod>"
                f'<xhtml:link rel="alternate" hreflang="ru-KZ" href="{SITE_URL}{ru}"/>'
                f'<xhtml:link rel="alternate" hreflang="kk-KZ" href="{SITE_URL}{kz}"/>'
                f'<xhtml:link rel="alternate" hreflang="x-default" href="{SITE_URL}{ru}"/></url>'
            )
    for p, lastmod in single:
        rows.append(f"<url><loc>{SITE_URL}{p}</loc><lastmod>{lastmod or today}</lastmod></url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )


def php_str(v):
    return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC, DIST)

    paths = []
    for c in LANGS:
        for p, doc in [build_home(c), *(build_service(c, s) for s in c.SERVICES), build_contacts(c)]:
            write(p, doc)
            paths.append(p)
    write("/404.html", build_404())

    posts = blog.live()
    single = []
    if posts:
        write(BLOG_PATH, build_blog_index(posts))
        single.append((BLOG_PATH, max(post_date(a, "updated_at") for a in posts)))
        for a in posts:
            p, doc = build_article(a, posts)
            write(p, doc)
            single.append((p, post_date(a, "updated_at")))
    (DIST / "sitemap.xml").write_text(sitemap(paths, single), encoding="utf-8")
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nDisallow: /api/\n\nSitemap: {SITE_URL}/sitemap.xml\nHost: {SITE_URL}\n",
        encoding="utf-8",
    )

    token, chat = os.environ.get("TG_BOT_TOKEN", ""), os.environ.get("TG_CHAT_ID", "")
    (DIST / "api" / "config.php").write_text(
        f"<?php\nreturn ['tg_token' => {php_str(token)}, 'tg_chat' => {php_str(chat)}];\n", encoding="utf-8"
    )
    print(f"Built {len(paths)} pages + blog {len(posts)} → {DIST}")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import http.server
        import functools

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
        print("http://localhost:8000")
        http.server.ThreadingHTTPServer(("127.0.0.1", 8000), handler).serve_forever()
