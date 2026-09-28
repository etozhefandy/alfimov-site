#!/usr/bin/env python3
"""Генератор статического сайта alfimov.kz (без зависимостей, только stdlib).

    python3 build.py            # собирает сайт в dist/
    python3 build.py --serve    # собирает и поднимает http://localhost:8000

Форма заявок: если заданы переменные окружения TG_BOT_TOKEN и TG_CHAT_ID,
в dist/api/config.php пишутся эти значения (в CI — из GitHub Secrets).
"""
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

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
STATIC = ROOT / "static"

SITE_URL = "https://alfimov.kz"
BRAND = "Alfimov"
PHONE_DISPLAY = "+7 776 902 66 69"
PHONE_TEL = "+77769026669"
WHATSAPP_URL = "https://wa.me/77769026669"
TELEGRAMS = ["fandylol", "etozhefandy"]
FONT_URL = "https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700;800&display=swap"
ASSET_VER = date.today().strftime("%Y%m%d")

LANGS = [content_ru, content_kz]
HREFLANG = {"ru": "ru-KZ", "kk": "kk-KZ"}

e = html.escape


# ---------------------------------------------------------------- icons

ICONS = {
    "meta": '<path d="M4 15c0-4 2-8 4.5-8 2.2 0 3.6 3 5.5 6s3 4 4.5 4c1.6 0 2.5-1.5 2.5-4s-1.3-6-3.8-6c-2 0-3.5 2.6-5.2 5.4C10.3 15.3 9 17 7 17c-1.8 0-3-1-3-2Z"/>',
    "tiktok": '<path d="M14 3v11.5a3.5 3.5 0 1 1-3.5-3.5"/><path d="M14 3c.5 2.8 2.4 4.6 5 5"/>',
    "smm": '<rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17" cy="7" r=".6" fill="currentColor"/>',
    "context": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/><path d="M8 10.5h5M10.5 8v5"/>',
    "seo": '<path d="M3 20h18"/><path d="M6 16v-4M11 16V8M16 16v-6"/><path d="m5 8 5-4 4 3 5-4"/>',
    "research": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "complex": '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="4" r="1.6"/><circle cx="20" cy="12" r="1.6"/><circle cx="12" cy="20" r="1.6"/><circle cx="4" cy="12" r="1.6"/><path d="M12 5.6V9M18.4 12H15M12 18.4V15M5.6 12H9"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "phone": '<path d="M5 4h3.5l1.5 4.5-2 1.5a11 11 0 0 0 6 6l1.5-2 4.5 1.5V19a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/>',
    "whatsapp": '<path d="M4 20l1.2-4A8 8 0 1 1 8 18.8Z"/><path d="M9 9.5c0 3 2.5 5.5 5.5 5.5l1-1.5-2-1-1 .8c-1-.5-2-1.5-2.3-2.3l.8-1-1-2-1 .5Z"/>',
    "telegram": '<path d="M21 4 3 11l6 2.2L18 7l-7 7.5V20l3-3.5 4 3Z"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
}


def icon(name, cls="ic"):
    return (
        f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'
    )


# ---------------------------------------------------------------- helpers

def url(c, slug=""):
    """Путь страницы с языковым префиксом, всегда со слешем на конце."""
    return f"{c.PREFIX}/{slug + '/' if slug else ''}"


def other_lang(c):
    return content_kz if c is content_ru else content_ru


def org_schema():
    return {
        "@type": "ProfessionalService",
        "@id": f"{SITE_URL}/#org",
        "name": BRAND,
        "url": f"{SITE_URL}/",
        "logo": f"{SITE_URL}/assets/logo.png",
        "image": f"{SITE_URL}/assets/og.png",
        "telephone": PHONE_TEL,
        "priceRange": "$$",
        "address": {"@type": "PostalAddress", "addressCountry": "KZ"},
        "areaServed": {"@type": "Country", "name": "Kazakhstan"},
        "sameAs": [f"https://t.me/{t}" for t in TELEGRAMS],
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


# ---------------------------------------------------------------- partials

def header(c, alt_path):
    ui = c.UI
    nav_services = "".join(
        f'<li><a href="{url(c, s["slug"])}">{e(s["name"])}</a></li>' for s in c.SERVICES
    )
    return f"""
<header class="hdr">
  <div class="wrap hdr-in">
    <a class="logo" href="{url(c)}" aria-label="{BRAND} — {e(ui['brand_tagline'])}">alfimov<span>.</span></a>
    <nav class="nav" id="nav" aria-label="Main">
      <div class="dd">
        <a href="{url(c)}#services">{e(ui['nav_services'])}</a>
        <ul class="dd-menu">{nav_services}</ul>
      </div>
      <a href="{url(c)}#how">{e(ui['nav_how'])}</a>
      <a href="{url(c)}#faq">{e(ui['nav_faq'])}</a>
      <a href="{url(c, 'kontakty')}">{e(ui['nav_contacts'])}</a>
      <a class="lang" href="{alt_path}" hreflang="{other_lang(c).LANG}" aria-label="{e(ui['lang_switch_label'])}">{e(ui['lang_switch'])}</a>
      <a class="btn btn-sm" href="#lead">{e(ui['cta'])}</a>
    </nav>
    <button class="burger" type="button" aria-controls="nav" aria-expanded="false" aria-label="Menu">{icon('menu')}</button>
  </div>
</header>"""


def contact_links():
    tg = "".join(
        f'<a class="chip" href="https://t.me/{t}" target="_blank" rel="noopener">{icon("telegram")}@{t}</a>'
        for t in TELEGRAMS
    )
    return (
        f'<a class="chip" href="tel:{PHONE_TEL}">{icon("phone")}{PHONE_DISPLAY}</a>'
        f'<a class="chip" href="{WHATSAPP_URL}" target="_blank" rel="noopener">{icon("whatsapp")}WhatsApp</a>'
        + tg
    )


def lead_form(c, source):
    ui = c.UI
    return f"""
<section class="lead" id="lead">
  <div class="wrap lead-in">
    <div class="lead-copy">
      <h2>{e(ui['form_title'])}</h2>
      <p>{e(ui['form_lead'])}</p>
      <p class="muted">{e(ui['or_write'])}</p>
      <div class="chips">{contact_links()}</div>
    </div>
    <form class="form" action="/api/send.php" method="post" data-ok="{e(ui['form_ok'])}" data-err="{e(ui['form_err'])}" data-sending="{e(ui['form_sending'])}">
      <input type="hidden" name="source" value="{e(source)}">
      <input type="hidden" name="lang" value="{c.LANG}">
      <input type="hidden" name="ts" value="">
      <div class="hp" aria-hidden="true"><label>Company<input type="text" name="company" tabindex="-1" autocomplete="off"></label></div>
      <label class="fld"><span>{e(ui['form_name'])}</span><input type="text" name="name" required maxlength="80" autocomplete="name"></label>
      <label class="fld"><span>{e(ui['form_phone'])}</span><input type="text" name="contact" required maxlength="80" autocomplete="tel" inputmode="tel"></label>
      <label class="fld"><span>{e(ui['form_message'])}</span><textarea name="message" rows="3" maxlength="1000"></textarea></label>
      <button class="btn btn-lg" type="submit">{e(ui['form_submit'])}</button>
      <p class="consent">{e(ui['form_consent'])}</p>
      <p class="form-status" role="status" aria-live="polite"></p>
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
    <div>
      <a class="logo" href="{url(c)}">alfimov<span>.</span></a>
      <p class="muted">{e(ui['footer_about'])}</p>
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
      </ul>
    </div>
  </div>
  <div class="wrap ftr-bottom muted">© {date.today().year} {BRAND}. {e(ui['rights'])}</div>
</footer>"""


def page(c, *, path, title, desc, body, schema, alt_path, noindex=False):
    graph = {"@context": "https://schema.org", "@graph": [org_schema(), *schema]}
    o = other_lang(c)
    alternates = ""
    if not noindex:
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
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:locale" content="{og_locale}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{SITE_URL}{path}">
<meta property="og:image" content="{SITE_URL}/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0f1115">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONT_URL}">
<link rel="stylesheet" href="/assets/style.css?v={ASSET_VER}">
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


def faq_block(c, items, anchor="faq"):
    qs = "".join(
        f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in items
    )
    return f'<section class="sec" id="{anchor}"><div class="wrap narrow"><h2>{e(c.UI["faq_title"])}</h2><div class="faq">{qs}</div></div></section>'


def steps_block(title, steps, anchor=""):
    items = "".join(
        f'<li><span class="num">{i:02d}</span><h3>{e(t)}</h3><p>{e(d)}</p></li>'
        for i, (t, d) in enumerate(steps, 1)
    )
    aid = f' id="{anchor}"' if anchor else ""
    return f'<section class="sec sec-dark"{aid}><div class="wrap"><h2>{e(title)}</h2><ol class="steps">{items}</ol></div></section>'


def service_cards(c, exclude=None):
    cards = []
    for s in c.SERVICES:
        if s["slug"] == exclude:
            continue
        cls = "card card-feature" if s["slug"] == "kompleksnyj-marketing" else "card"
        cards.append(
            f'<a class="{cls}" href="{url(c, s["slug"])}">'
            f'<span class="card-ic">{icon(s["icon"])}</span>'
            f'<h3>{e(s["name"])}</h3><p>{e(s["short"])}</p>'
            f'<span class="more">{e(c.UI["more"])} {icon("arrow", "ic ic-sm")}</span></a>'
        )
    return f'<div class="cards">{"".join(cards)}</div>'


# ---------------------------------------------------------------- pages

def build_home(c):
    h, ui = c.HOME, c.UI
    points = "".join(f"<li>{icon('check', 'ic ic-sm')}{e(p)}</li>" for p in h["hero_points"])
    why = "".join(f'<div class="why"><h3>{e(t)}</h3><p>{e(d)}</p></div>' for t, d in h["why"])
    body = f"""
<section class="hero">
  <div class="wrap">
    <p class="kicker">{e(h['hero_kicker'])}</p>
    <h1>{e(h['hero_title'])}</h1>
    <p class="hero-lead">{e(h['hero_lead'])}</p>
    <div class="hero-cta">
      <a class="btn btn-lg" href="#lead">{e(ui['cta'])}</a>
      <a class="btn btn-lg btn-ghost" href="#services">{e(ui['nav_services'])}</a>
    </div>
    <ul class="hero-points">{points}</ul>
  </div>
</section>
<section class="sec" id="services">
  <div class="wrap">
    <h2>{e(ui['services_title'])}</h2>
    <p class="sec-lead">{e(ui['services_lead'])}</p>
    {service_cards(c)}
  </div>
</section>
<section class="sec sec-soft">
  <div class="wrap">
    <h2>{e(h['why_title'])}</h2>
    <div class="whys">{why}</div>
  </div>
</section>
{steps_block(h['how_title'], h['how'], 'how')}
{faq_block(c, h['faq'])}
{lead_form(c, 'home')}
"""
    path = url(c)
    alt = url(other_lang(c))
    return path, page(
        c, path=path, title=h["meta_title"], desc=h["meta_desc"], body=body, alt_path=alt,
        schema=[
            {"@type": "WebSite", "@id": f"{SITE_URL}/#site", "url": f"{SITE_URL}/", "name": BRAND, "inLanguage": c.LANG},
            faq_schema(h["faq"]),
        ],
    )


def build_service(c, s):
    ui = c.UI
    path = url(c, s["slug"])
    alt = url(other_lang(c), s["slug"])
    intro = "".join(f"<p>{e(p)}</p>" for p in s["intro"])
    includes = "".join(
        f'<li><span class="inc-ic">{icon("check", "ic ic-sm")}</span><div><h3>{e(t)}</h3><p>{e(d)}</p></div></li>'
        for t, d in s["includes"]
    )
    for_whom = "".join(f"<li>{e(x)}</li>" for x in s["for_whom"])
    body = f"""
<section class="hero hero-svc">
  <div class="wrap">
    <nav class="crumbs" aria-label="breadcrumbs"><a href="{url(c)}">{e(ui['breadcrumbs_home'])}</a><span>/</span><a href="{url(c)}#services">{e(ui['nav_services'])}</a></nav>
    <span class="hero-ic">{icon(s['icon'])}</span>
    <h1>{e(s['h1'])}</h1>
    <p class="hero-lead">{e(s['lead'])}</p>
    <div class="hero-cta"><a class="btn btn-lg" href="#lead">{e(ui['cta'])}</a></div>
  </div>
</section>
<section class="sec">
  <div class="wrap narrow prose">{intro}</div>
</section>
<section class="sec sec-soft">
  <div class="wrap">
    <h2>{e(ui['includes_title'])}</h2>
    <ul class="includes">{includes}</ul>
  </div>
</section>
<section class="sec">
  <div class="wrap narrow">
    <h2>{e(ui['for_whom_title'])}</h2>
    <ul class="bullets">{for_whom}</ul>
  </div>
</section>
{steps_block(ui['steps_title'], s['steps'])}
{faq_block(c, s['faq'])}
{lead_form(c, s['slug'])}
<section class="sec">
  <div class="wrap">
    <h2>{e(ui['other_services'])}</h2>
    {service_cards(c, exclude=s['slug'])}
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
    <nav class="crumbs" aria-label="breadcrumbs"><a href="{url(c)}">{e(ui['breadcrumbs_home'])}</a></nav>
    <h1>{e(k['h1'])}</h1>
    <p class="hero-lead">{e(k['lead'])}</p>
    <div class="chips chips-lg">{contact_links()}</div>
  </div>
</section>
<section class="sec">
  <div class="wrap narrow">
    <h2>{e(k['area_title'])}</h2>
    <p>{e(k['area_text'])}</p>
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
<section class="hero">
  <div class="wrap">
    <p class="kicker">404</p>
    <h1>{e(ui['not_found_title'])}</h1>
    <p class="hero-lead">{e(ui['not_found_text'])}</p>
    <p class="muted">{e(kz['not_found_text'])}</p>
    <div class="hero-cta"><a class="btn btn-lg" href="/">{e(ui['not_found_btn'])}</a><a class="btn btn-lg btn-ghost" href="/kz/">{e(kz['not_found_btn'])}</a></div>
  </div>
</section>
<section class="sec"><div class="wrap">{service_cards(c)}</div></section>
"""
    return page(c, path="/404.html", title=f"404 — {BRAND}", desc=ui["not_found_text"], body=body, schema=[], alt_path="/kz/", noindex=True)


# ---------------------------------------------------------------- build

def write(path, content):
    target = DIST / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def sitemap(paths):
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
    (DIST / "sitemap.xml").write_text(sitemap(paths), encoding="utf-8")
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nDisallow: /api/\n\nSitemap: {SITE_URL}/sitemap.xml\nHost: {SITE_URL}\n",
        encoding="utf-8",
    )

    token, chat = os.environ.get("TG_BOT_TOKEN", ""), os.environ.get("TG_CHAT_ID", "")
    (DIST / "api" / "config.php").write_text(
        f"<?php\nreturn ['tg_token' => {php_str(token)}, 'tg_chat' => {php_str(chat)}];\n", encoding="utf-8"
    )
    print(f"Built {len(paths)} pages → {DIST}" + ("" if token and chat else "  (форма: TG_BOT_TOKEN/TG_CHAT_ID не заданы)"))


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import http.server
        import functools

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
        print("http://localhost:8000")
        http.server.ThreadingHTTPServer(("127.0.0.1", 8000), handler).serve_forever()
