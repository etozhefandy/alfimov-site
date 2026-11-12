#!/usr/bin/env python3
"""Генератор статического сайта alfimov.kz (без зависимостей, только stdlib).

    python3 build.py            # собирает сайт в dist/
    python3 build.py --serve    # собирает и поднимает http://localhost:8000

Дизайн по design brief: Marketing × Data × Technology — белый, почти чёрный,
серые и один синий акцент; типографика и сетка вместо декора.
"""
import base64
import hashlib
import html
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "engine"))
import enginekit  # noqa: E402  (общий движок сайтов — git submodule engine/, etozhefandy/site-engine)
import seo_audit  # noqa: E402  (из движка)
import content_kz  # noqa: E402
import content_ru  # noqa: E402
import lp_guestory  # noqa: E402
import lp_render  # noqa: E402


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
# Шрифты: заголовки с засечками Source Serif 4 + текст IBM Plex Sans + цифры и метки IBM Plex Mono.
# Все три полностью покрывают казахский (ә ғ қ ң ө ұ ү һ і) — проверено по таблицам символов шрифтов.
# Заголовочный шрифт — отдельным запросом с display=optional: если не успел прогрузиться почти сразу (он
# предзагружен через preload), браузер весь показ страницы держит запасной Georgia и не подменяет её потом
# «на лету» — не должно быть заметного скачка шрифта после печати заголовка. Текстовым шрифтам (они мельче,
# подмена не бросается в глаза) оставлен обычный display=swap — так текст не ждёт загрузки шрифта вообще.
# С редизайна 11.11.2026 заголовки — тот же IBM Plex Sans (жирный), засечки Source Serif больше не грузим.
FONT_URL_BODY = "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap"
# CSP script-src без 'unsafe-inline': каждый инлайн-скрипт разрешён по точному хэшу его содержимого,
# не по тегу. Хэши собираются по ходу сборки (csp_hash) и в конце прописываются в dist/.htaccess
# вместо %%SCRIPT_HASHES%%. Текст скрипта всегда берётся из той же переменной, что идёт в HTML, —
# хэш гарантированно совпадёт с тем, что реально отрендерилось.
CSP_SCRIPT_HASHES = set()


def csp_hash(script_text):
    digest = hashlib.sha256(script_text.encode("utf-8")).digest()
    token = "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"
    CSP_SCRIPT_HASHES.add(token)
    return script_text


# Microsoft Clarity — тепловые карты кликов и прокрутки, записи визитов (clarity.microsoft.com). Пусто — не ставится.
# Поля ввода Clarity по умолчанию скрывает (телефоны в записи не попадают). Источники Clarity разрешены в CSP (static/.htaccess).
CLARITY_ID = "z0he5x2t9s"
CLARITY_JS = (
    '(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};'
    't=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;y=l.getElementsByTagName(r)[0];'
    f'y.parentNode.insertBefore(t,y)}})(window,document,"clarity","script","{CLARITY_ID}");'
) if CLARITY_ID else ""
CLARITY_TAG = f"<script>{csp_hash(CLARITY_JS)}</script>" if CLARITY_JS else ""

JS_CLASS_ADDER = "document.documentElement.classList.add('js')"
csp_hash(JS_CLASS_ADDER)

ASSET_VER = hashlib.md5(
    b"".join((STATIC / "assets" / f).read_bytes() for f in ("style.css", "main.js"))
).hexdigest()[:8]

LANGS = [content_ru, content_kz]
HREFLANG = {"ru": "ru-KZ", "kk": "kk-KZ"}
PRIVACY_PATH = "/politika-konfidencialnosti/"

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
        # legalName/taxID — реквизиты для доверия (контакты/политика), без streetAddress: агентство
        # работает удалённо, без офиса для визитов — PostalAddress с улицей читался бы как заявка
        # на физическую точку, а это не так (см. находку local-SEO аудита: country-only — верно).
        "legalName": content_ru.LEGAL["entity"],
        "taxID": content_ru.LEGAL["iin"],
        "address": {"@type": "PostalAddress", "addressCountry": "KZ"},
        "areaServed": {"@type": "Country", "name": "Kazakhstan"},
        "contactPoint": {"@type": "ContactPoint", "telephone": PHONE_TEL, "contactType": "sales",
                         "areaServed": "KZ", "availableLanguage": ["ru", "kk"]},
        "knowsAbout": [s["name"] for s in content_ru.SERVICES],
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
    # Блог — только русский (статьи на русском). Страницы блога собирает PHP на хостинге (_blog/).
    blog_link = f'<a href="{BLOG_PATH}">{e(BLOG_UI["nav"])}</a>' if c is content_ru else ""
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
      <a class="btn btn-sm" href="#lead-form">{e(ui['cta'])}</a>
    </nav>
    <button class="burger" type="button" aria-controls="nav" aria-expanded="false" aria-label="Menu">{icon('menu')}</button>
  </div>
  <div class="sprog" aria-hidden="true"></div>
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
        + f'<a class="clink" href="{INSTAGRAM_URL}" target="_blank" rel="noopener" aria-label="Instagram @{INSTAGRAM}">{icon("instagram")}@{INSTAGRAM}</a>'
    )


def lead_form(c, source, title=None, lead=None, num="→", links=False):
    ui = c.UI
    title = title or c.HOME["final_title"]
    lead = lead or c.HOME["final_lead"]
    return f"""
<section class="final" id="lead">
  <div class="wrap final-in">
    <div class="final-copy rv">
      <h2>{e(title)}</h2>
      <p>{e(lead)}</p>
      {f'<div class="clinks">{contact_links()}</div>' if links else ''}
    </div>
    <form class="form rv" id="lead-form" action="/api/send.php" method="post" data-ok="{e(ui['form_ok'])}" data-err="{e(ui['form_err'])}" data-sending="{e(ui['form_sending'])}">
      <input type="hidden" name="source" value="{e(source)}">
      <input type="hidden" name="lang" value="{c.LANG}">
      <input type="hidden" name="ts" value="">
      <div class="hp" aria-hidden="true"><label>Company<input type="text" name="company" tabindex="-1" autocomplete="off"></label></div>
      <label class="fld"><span>{e(ui['form_name'])}</span><input type="text" name="name" required maxlength="80" autocomplete="name"></label>
      <label class="fld"><span>{e(ui['form_phone'])}</span><input type="tel" name="contact" required maxlength="18" autocomplete="tel" inputmode="tel" placeholder="+7 (___) ___-__-__" data-phone data-err="{e(ui['form_phone_err'])}"></label>
      <label class="fld"><span>{e(ui['form_message'])}</span><textarea name="message" rows="2" maxlength="1000"></textarea></label>
      <button class="btn btn-lg" type="submit">{e(ui['form_submit'])} {icon('arrow', 'ic ic-sm')}</button>
      <p class="form-status" role="status" aria-live="polite"></p>
      <p class="consent">{e(ui['form_consent'])} <a href="{PRIVACY_PATH}">{e(ui.get('footer_privacy', ''))}</a></p>
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
  <div class="wrap ftr-bottom"><span>© {date.today().year} ALFIMOV.KZ</span><span>{e(ui['rights'])}</span><a href="{PRIVACY_PATH}">{e(ui.get('footer_privacy', ''))}</a></div>
</footer>"""


def page(c, *, path, title, desc, body, schema, alt_path, noindex=False, og_type="website", image=None, dark_top=False):
    if image is None:
        card_title = re.sub(r"\s*[|—]\s*(ALFIMOV\.KZ|Alfimov)\s*$", "", title, flags=re.I).strip() or title
        image = enginekit.og_card(DIST, path, card_title, dark="#0c1011", accent="#1769ff", domain="ALFIMOV.KZ")
    # Кнопка шапки ведёт к форме (#lead-form). На страницах без формы (политика) — к форме на «Контактах».
    lead_href = "#lead-form" if 'id="lead-form"' in body else url(c, "kontakty") + "#lead-form"
    graph = {"@context": "https://schema.org", "@graph": [org_schema(), *schema]}
    graph_json = csp_hash(json.dumps(graph, ensure_ascii=False))
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
{CLARITY_TAG}
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{robots}
<link rel="canonical" href="{SITE_URL}{path}">
{alternates}
<link rel="alternate" type="text/markdown" href="/llms.txt" title="llms.txt">
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
<link rel="preload" as="style" href="{FONT_URL_BODY}">
<link rel="stylesheet" href="{FONT_URL_BODY}" media="print" class="js-async-css">
<noscript><link rel="stylesheet" href="{FONT_URL_BODY}"></noscript>
<link rel="stylesheet" href="/assets/style.css?v={ASSET_VER}">
<script>{JS_CLASS_ADDER}</script>
<script type="application/ld+json">{graph_json}</script>
</head>
<body{' class="dark-top"' if dark_top else ''}>
{header(c, alt_path).replace('href="#lead-form"', f'href="{lead_href}"')}
<main>
{body}
</main>
{footer(c)}
<a class="mcta btn btn-lg" href="{lead_href}" hidden>{e(c.UI['cta'])} {icon('arrow', 'ic ic-sm')}</a>
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


def type_words(parts, rot=None):
    """Печатающийся заголовок (.type, style.css): каждое слово — свой <span> с индексом --i,
    чтобы текст появлялся по словам в порядке чтения, а не всей строкой/всеми строками сразу.
    parts — [(текст, em)], em оборачивает слово в <em> (акцент)."""
    out, i = [], 0
    for text, em in parts:
        if not text:
            continue
        for word in text.split(" "):
            if not word:
                continue
            if rot and word == rot[0][0].split(" ")[0]:
                # Слово-«карусель»: в HTML (и для Google) — первое слово списка, main.js по очереди меняет его на
                # остальные; у каждого своё время на экране в секундах (content_*.HOME['hero_rot']).
                data = "|".join(f"{w}~{t}" for w, t in rot)
                # После слова — перенос строки: длина сменяющегося слова уходит в пустое место в конце строки,
                # остальной заголовок не «ездит» (ширину под самое длинное слово держит .rot в style.css).
                span = f'<span class="tw tw-i-{min(i, 40)} rot" data-rot="{e(data)}">{e(word)}</span><br class="rot-br">'
                rot = None
            else:
                span = f'<span class="tw tw-i-{min(i, 40)}">{e(word)}</span>'
            out.append(f"<em>{span}</em>" if em else span)
            i += 1
    return " ".join(out)


def flow(steps, loop_text=None):
    """Схема пути: горизонтальная на десктопе, вертикальная на мобиле."""
    items = "".join(
        f'<li class="flow-i-{min(i, 15)}"><span class="flow-n">{i + 1:02d}</span><h3>{e(t)}</h3><p>{e(d)}</p></li>'
        for i, (t, d) in enumerate(steps)
    )
    loop = f'<p class="flow-loop">↺ {e(loop_text)}</p>' if loop_text else ""
    n = len(steps)
    if not 1 <= n <= 12:
        raise ValueError(f"flow(): {n} шагов — нет готового класса flow-n-{n} в style.css (сейчас 1..12)")
    return f'<div class="flow rv flow-n-{n}"><ol>{items}</ol>{loop}</div>'


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

def home_blog_block(c, n):
    """Свежие статьи на главной (только RU) подставляет PHP на хостинге вместо метки — см. _blog/lib.php."""
    return f"<!--BLOG-HOME:{next(n)}-->" if c is content_ru else ""


def hero_form(c):
    """Короткая форма на первом экране главной (имя + телефон) — та же отправка, что у формы внизу."""
    ui, h = c.UI, c.HOME
    return f"""<form class="form form-card rv" id="hero-form" action="/api/send.php" method="post" data-ok="{e(ui['form_ok'])}" data-err="{e(ui['form_err'])}" data-sending="{e(ui['form_sending'])}">
      <input type="hidden" name="source" value="home-hero">
      <input type="hidden" name="lang" value="{c.LANG}">
      <input type="hidden" name="ts" value="">
      <div class="hp" aria-hidden="true"><label>Company<input type="text" name="company" tabindex="-1" autocomplete="off"></label></div>
      <p class="form-card-t">{e(h['hero_form_title'])}</p>
      <p class="form-card-l">{e(h['hero_form_lead'])}</p>
      <label class="fld"><span>{e(ui['form_name'])}</span><input type="text" name="name" required maxlength="80" autocomplete="name"></label>
      <label class="fld"><span>{e(ui['form_phone'])}</span><input type="tel" name="contact" required maxlength="18" autocomplete="tel" inputmode="tel" placeholder="+7 (___) ___-__-__" data-phone data-err="{e(ui['form_phone_err'])}"></label>
      <button class="btn btn-lg" type="submit">{e(h['hero_form_btn'])} {icon('arrow', 'ic ic-sm')}</button>
      <p class="form-status" role="status" aria-live="polite"></p>
      <p class="consent">{e(ui['form_consent'])} <a href="{PRIVACY_PATH}">{e(ui.get('footer_privacy', ''))}</a></p>
    </form>"""


# Плитки услуг на главной: размеры по порядку c.SERVICES (первая — большая тёмная, четвёртая — широкая синяя).
BENTO_SIZES = ["big", "", "", "wide blue", "", "", "wide"]


def bento(c):
    tiles = []
    for i, s in enumerate(c.SERVICES):
        size = BENTO_SIZES[i] if i < len(BENTO_SIZES) else ""
        tiles.append(
            f'<a class="tile {size} rv" href="{url(c, s["slug"])}"><b>{e(s["name"])}</b>'
            f'<span>{e(s["short"])}</span>{icon("arrow", "ic tile-arrow")}</a>'
        )
    return f'<div class="bento">{"".join(tiles)}</div>'


def build_home(c):
    h, ui = c.HOME, c.UI
    facts = "".join(f'<li><b>{e(a)}</b><span>{e(b)}</span></li>' for a, b in h["hero_facts"])

    visible = {s["slug"] for s in c.SERVICES}
    shown = lambda t: t.startswith("#") or t in visible  # noqa: E731
    dirs = [(n, d, [l for l in ls if shown(l[1])]) for n, d, ls in h["directions"]]
    dirs = [x for x in dirs if x[2]]
    directions = []
    for i, (name, desc, links) in enumerate(dirs, 1):
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
    clients = "".join(f"<li>{e(x)}</li>" for x in c.CLIENTS)
    why = "".join(f'<li class="rv"><b>{e(a)}</b><span>{e(b)}</span></li>' for a, b in h["hero_facts"])
    body = f"""
<section class="hx">
  <div class="hx-bg" aria-hidden="true"></div>
  <div class="wrap hx-grid">
    <div class="hx-copy">
      <p class="hero-kicker rv">{e(h['hero_kicker'])}</p>
      <h1 class="type">{type_words([(h['hero_title_pre'], False), (h['hero_title_accent'], True), (h.get('hero_title_post', ''), False)], h.get('hero_rot'))}</h1>
      <p class="hero-lead rv">{e(h['hero_lead'])}</p>
      <div class="hero-cta rv">
        <a class="btn btn-lg" href="#hero-form">{e(ui['cta'])} {icon('arrow', 'ic ic-sm')}</a>
        <a class="tlink" href="#approach">{e(h['hero_cta_secondary'])} {icon('arrow-down', 'ic ic-sm')}</a>
      </div>
    </div>
    {hero_form(c)}
  </div>
  {f'<div class="wrap hx-clients"><p>{e(h["clients_title"])}</p><div class="marq"><ul>{clients}</ul><ul aria-hidden="true">{clients}</ul></div></div>' if c.CLIENTS else ''}
</section>
<section class="sec sec-soft" id="services">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow(next(n), h['directions_eyebrow'])}<h2>{e(h['directions_title'])}</h2><p>{e(h['directions_lead'])}</p></div>
    {bento(c)}
  </div>
</section>
<section class="sec" id="approach">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow(next(n), h['approach_eyebrow'])}<h2>{e(h['approach_title'])}</h2><p>{e(h['approach_lead'])}</p></div>
    {flow(h['approach'], h['approach_loop'])}
  </div>
</section>
<section class="sec sec-soft" id="why">
  <div class="wrap">
    <div class="sec-head rv">{eyebrow(next(n), h['why_eyebrow'])}<h2>{e(h['why_title'])}</h2></div>
    <ul class="why">{why}</ul>
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
{home_blog_block(c, n)}
{faq_block(c, h['faq'], next(n))}
{lead_form(c, 'home')}
"""
    path = url(c)
    alt = url(other_lang(c))
    return path, page(
        c, path=path, title=h["meta_title"], desc=h["meta_desc"], body=body, alt_path=alt, dark_top=True,
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
    <h1 class="type">{type_words([(s['h1'], False)])}</h1>
    <div class="hero-row">
      <p class="hero-lead rv">{e(s['lead'])}</p>
      <div class="hero-cta rv">
        <a class="btn btn-lg" href="#lead-form">{e(ui['cta'])} {icon('arrow', 'ic ic-sm')}</a>
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
<section class="sec sec-tight-b">
  <div class="wrap">
    <div class="price-box rv">
      <div class="price"><span>{e(ui['price_label'])}</span><b>{e(price_text(c, s['slug']))}</b><small>{e(ui['price_note'])}</small></div>
      <a class="btn btn-lg" href="#lead-form">{e(ui['cta'])} {icon('arrow', 'ic ic-sm')}</a>
    </div>
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


def legal_block(num):
    """Реквизиты — пока только у alfimov.kz (RU), см. content_ru.LEGAL."""
    g = content_ru.LEGAL
    rows = "".join(f"<p>{e(line)}</p>" for line in (
        g["entity"], f"Адрес: г. {g['city']}, {g['street']}", f"ИИН: {g['iin']}", f"ИИК: {g['iik']}",
        g["bank"], f"БИК: {g['bik']}", g["signatory"],
    ))
    return f"""
<section class="sec">
  <div class="wrap split">
    <div class="split-head rv">{eyebrow(num, content_ru.CONTACTS['legal_title'])}<h2>{e(content_ru.CONTACTS['legal_title'])}</h2></div>
    <div class="prose rv">{rows}</div>
  </div>
</section>"""


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
{legal_block('02') if c is content_ru else ""}
{lead_form(c, 'contacts')}
"""
    schema = [breadcrumbs_schema([(ui["breadcrumbs_home"], url(c)), (k["h1"], path)])]
    return path, page(c, path=path, title=k["meta_title"], desc=k["meta_desc"], body=body, schema=schema, alt_path=alt)


def build_privacy():
    c, ui = content_ru, content_ru.UI
    g = content_ru.LEGAL
    k = content_ru.PRIVACY
    path = PRIVACY_PATH
    secs = "".join(
        f'<div class="prose rv"><h2>{e(title)}</h2><p>{e(text.format(**g))}</p></div>'
        for title, text in k["sections"]
    )
    body = f"""
<section class="hero hero-svc">
  <div class="wrap">
    <nav class="crumbs rv" aria-label="breadcrumbs"><a href="{url(c)}">{e(ui['breadcrumbs_home'])}</a></nav>
    <h1 class="rv">{e(k['h1'])}</h1>
    <p class="hero-lead rv">{e(k['lead'])}</p>
  </div>
</section>
<section class="sec"><div class="wrap">{secs}</div></section>
"""
    schema = [breadcrumbs_schema([(ui["breadcrumbs_home"], url(c)), (k["h1"], path)])]
    return path, page(c, path=path, title=k["meta_title"], desc=k["meta_desc"], body=body, schema=schema, alt_path=None)


NOT_FOUND_FORM = {
    "ru": ("Есть вопросы?", "Не нашли, что искали? Оставьте телефон — перезвоним, ответим на вопросы и подскажем, с чего начать рекламу."),
    "kk": ("Сұрақтарыңыз бар ма?", "Іздегеніңізді таппадыңыз ба? Телефоныңызды қалдырыңыз — қайта қоңырау шалып, сұрақтарға жауап береміз және жарнаманы неден бастау керектігін айтамыз."),
}


def build_404(c):
    """Страница «не найдено» на языке сайта: /404.html (RU) и /kz/404.html (KZ) — какую показать, решает .htaccess по адресу."""
    ui = c.UI
    title, lead = NOT_FOUND_FORM[c.LANG]
    path = url(c) + "404.html"
    body = f"""
<section class="hero hero-svc">
  <div class="wrap">
    <p class="hero-kicker">404</p>
    <h1>{e(ui['not_found_title'])}</h1>
    <p class="hero-lead">{e(ui['not_found_text'])}</p>
    <div class="hero-cta"><a class="btn btn-lg" href="{url(c)}">{e(ui['not_found_btn'])}</a></div>
  </div>
</section>
<section class="sec"><div class="wrap">{service_rows(c)}</div></section>
{lead_form(c, '404', title, lead)}
"""
    return page(c, path=path, title="404 — ALFIMOV.KZ", desc=ui["not_found_text"], body=body, schema=[], alt_path=None, noindex=True)


# ---------------------------------------------------------------- blog

BLOG_PATH = "/blog/"
BLOG_UI = {
    "nav": "Блог",
    "home_title": "Свежие статьи",
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


def blog_parts():
    """Детали оформления для PHP-блога (_blog/parts.json): каркас страницы с метками %%…%%,
    форма заявки, FAQ, иконки и подписи. Так шапка, подвал и стили блога всегда совпадают с сайтом."""
    c = content_ru
    shell = page(c, path="%%PATH%%", title="%%TITLE%%", desc="%%DESC%%", body="%%BODY%%", schema=["__SCHEMA__"],
                 alt_path=None, og_type="%%OGTYPE%%", image="%%IMAGE%%")
    faq_item = f'<details class="qa"><summary>%%Q%%{icon("plus", "ic qa-ic")}</summary><p>%%A%%</p></details>'
    faq_wrap = faq_block(c, [], "%%NUM%%")
    assert '<div class="faq rv"></div>' in faq_wrap
    return {
        "site_url": SITE_URL,
        "blog_path": BLOG_PATH,
        "shell": shell,
        "lead_form": lead_form(c, "%%SOURCE%%", BLOG_UI["cta_title"], BLOG_UI["cta_lead"]),
        "faq_item": faq_item,
        "faq_wrap": faq_wrap.replace('<div class="faq rv"></div>', '<div class="faq rv">%%ITEMS%%</div>'),
        "icon_arrow_sm": icon("arrow", "ic ic-sm"),
        "ui": {**BLOG_UI, "breadcrumbs_home": c.UI["breadcrumbs_home"], "more": c.UI["more"]},
        "services": [{"slug": x["slug"], "name": x["name"], "short": x["short"], "price": price_text(c, x["slug"])}
                     for x in c.SERVICES],
    }


# По теме статьи (её category + keywords + title) подбираем ближайшую услугу для попапа под статьёй —
# первое совпадение побеждает, порядок важен (частное — раньше общего: TikTok раньше общего «таргета»).
BLOG_POPUP_RULES = [
    (["tiktok", "тикток", "тик ток"], "target-tiktok"),
    (["таргет", "instagram", "инстаграм", "facebook", "фейсбук", " meta ", "meta ads"], "target-facebook-instagram"),
    (["контекст", "google ads", "гугл рекл", "яндекс директ", "директ", "поисковая реклама"], "kontekstnaya-reklama"),
    (["seo", "сео", "продвижение сайта", "поисковое продвижение", "поисковой выдач"], "seo-prodvizhenie"),
    (["smm", "смм", "ведение инстаграм", "ведение соцсет", "контент-план", "контент план"], "smm"),
    (["исследован", "анализ рынка", "аналитика рынка", "анализ конкурент"], "marketingovye-issledovaniya"),
]
BLOG_POPUP_DEFAULT = "kompleksnyj-marketing"


def blog_popup_php():
    """_blog/popup.php: попап под статьёй с предложением проконсультироваться по теме статьи (движок лишь
    зовёт site_article_popup($article), если файл есть — static/_blog/lib.php, render_article()). Услуги и
    тексты берём из content_ru.SERVICES, чтобы не дублировать их тут руками и не разойтись при правке."""
    by_slug = {s["slug"]: s for s in content_ru.SERVICES_ALL}
    for needles, slug in BLOG_POPUP_RULES:
        assert slug in by_slug, f"blog_popup: нет услуги {slug!r} в content_ru.SERVICES"
    assert BLOG_POPUP_DEFAULT in by_slug

    def row(slug):
        s = by_slug[slug]
        return (f"    {php_str(slug)} => ['name' => {php_str(s['name'])}, 'short' => {php_str(s['short'])}, "
                f"'url' => {php_str(url(content_ru, slug))}],")

    used = {slug for _, slug in BLOG_POPUP_RULES} | {BLOG_POPUP_DEFAULT}
    services_php = "\n".join(row(slug) for slug in used)
    rules_php = ",\n".join(
        "    [[" + ", ".join(php_str(n) for n in needles) + "], " + php_str(slug) + "]"
        for needles, slug in BLOG_POPUP_RULES
    )
    wa_icon = icon("whatsapp").replace("'", "\\'")
    return f"""<?php
// Сгенерировано сборкой сайта (build.py: blog_popup_php) — не править руками.
// Попап под статьёй блога: по теме статьи (category, keywords, заголовок) подбирает ближайшую услугу
// агентства и предлагает бесплатную консультацию в WhatsApp. Показывается один раз за визит, после того
// как человек прочитал часть статьи (main.js: .art-popup), закрывается крестиком.
declare(strict_types=1);

const BLOG_POPUP_WA = {php_str(WHATSAPP_URL)};
const BLOG_POPUP_DEFAULT = {php_str(BLOG_POPUP_DEFAULT)};
const BLOG_POPUP_RULES = [
{rules_php},
];
const BLOG_POPUP_SERVICES = [
{services_php}
];

function site_article_popup(array $a): string
{{
    // сначала ищем по одной только категории статьи — так заголовок/ключевые слова статьи про SMM,
    // упоминающие «Instagram» (это же канал SMM), не перехватывает более раннее правило про таргет;
    // категория реже бывает многословной и почти всегда недвусмысленно называет саму услугу
    $category = mb_strtolower($a['category']);
    $text = $category . ' ' . mb_strtolower(implode(' ', $a['keywords']) . ' ' . $a['title']);
    $slug = BLOG_POPUP_DEFAULT;
    foreach ([$category, $text] as $pass) {{
        foreach (BLOG_POPUP_RULES as [$needles, $target]) {{
            foreach ($needles as $n) {{
                if (str_contains($pass, $n)) {{ $slug = $target; break 3; }}
            }}
        }}
    }}
    $s = BLOG_POPUP_SERVICES[$slug] ?? BLOG_POPUP_SERVICES[BLOG_POPUP_DEFAULT];
    $e = fn($v) => htmlspecialchars((string) $v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    $wa = BLOG_POPUP_WA . '?text=' . rawurlencode(sprintf('Здравствуйте! Прочитал(а) статью «%s» — хочу консультацию по теме «%s».', $a['title'], $s['name']));
    return '
<aside class="art-popup" id="art-popup" data-popup-slug="' . $e($slug) . '" hidden>
  <button class="art-popup-close" type="button" aria-label="Закрыть">&times;</button>
  <p class="art-popup-eyebrow">Читаете про «' . $e($s['name']) . '»?</p>
  <p class="art-popup-text">' . $e($s['short']) . ' Бесплатная консультация — обсудим именно вашу задачу.</p>
  <div class="art-popup-row">
    <a class="btn btn-sm" href="' . $e($wa) . '" target="_blank" rel="noopener" data-popup-cta>{wa_icon}Написать в WhatsApp</a>
    <a class="art-popup-more" href="' . $e($s['url']) . '">Подробнее об услуге →</a>
  </div>
</aside>';
}}
"""


# ---------------------------------------------------------------- build

def write(path, content):
    target = DIST / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


LASTMOD_FILE = ROOT / "sitemap-lastmod.json"


def page_lastmod(paths):
    """lastmod по странице: сегодня — только если её HTML реально изменился с прошлой сборки (хэш),
    иначе — дата из прошлого раза. Карта хэшей живёт в sitemap-lastmod.json (коммитится в репозиторий),
    иначе каждый деплой показывал бы в sitemap сегодняшнюю дату для всех страниц сразу, даже без правок."""
    today = date.today().isoformat()
    prev = json.loads(LASTMOD_FILE.read_text(encoding="utf-8")) if LASTMOD_FILE.is_file() else {}
    out = {}
    for p in paths:
        target = DIST / p.lstrip("/")
        if p.endswith("/"):
            target = target / "index.html"
        content = target.read_bytes() if target.is_file() else b""
        h = hashlib.sha256(content).hexdigest()
        prior = prev.get(p, {})
        out[p] = {"hash": h, "date": prior.get("date", today) if prior.get("hash") == h else today}
    LASTMOD_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {p: v["date"] for p, v in out.items()}


def sitemap(paths):
    """Страницы с парой RU/KZ. Статьи блога в карту добавляет PHP на хостинге (_blog/sitemap.tpl)."""
    ru_paths = [p for p in paths if not p.startswith("/kz/")]
    all_pairs = [p for ru in ru_paths for p in (ru, "/kz" + ru)]
    lastmod = page_lastmod(all_pairs)
    rows = []
    for ru in ru_paths:
        kz = "/kz" + ru
        for p in (ru, kz):
            rows.append(
                f"<url><loc>{SITE_URL}{p}</loc><lastmod>{lastmod[p]}</lastmod>"
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


# IndexNow: мгновенное уведомление Bing (→ ChatGPT, Copilot) и Яндекса о новых и изменённых страницах.
INDEXNOW_KEY = "c4a1f0e2b7d94e1f8a3c6b5d2e9f7a10"


def llms_txt():
    """/llms.txt — краткая справка о сайте для нейросетей (формат llmstxt.org). Статьи дописывает PHP."""
    c = content_ru
    svc = "\n".join(f"- [{s['name']}]({SITE_URL}{url(c, s['slug'])}): {s['short']} Цена: {price_text(c, s['slug'])}."
                    for s in c.SERVICES)
    return (
        f"# ALFIMOV.KZ — маркетинговое агентство в Казахстане\n\n"
        f"> {c.HOME['hero_lead']} Работаем со всем Казахстаном удалённо (Алматы, Астана, Шымкент и другие города). "
        f"Клиенты: {', '.join(c.CLIENTS)}.\n\n"
        f"Контакты: телефон и WhatsApp {PHONE_DISPLAY}, Telegram @{TELEGRAMS[0]}, Instagram @{INSTAGRAM}, "
        f"[форма заявки]({SITE_URL}/kontakty/). Сайт на русском и казахском ({SITE_URL}/kz/).\n\n"
        f"## Услуги\n\n{svc}\n\n"
        f"Рекламный бюджет оплачивается отдельно от работы агентства.\n\n"
        f"## Блог\n\n%%ARTICLES%%\n"
    )


# Настройки сайта для общего движка (enginekit.REQUIRED / DEFAULTS). Тексты ниши для ИИ — site/prompts.php.
# Код первой настройки админки — только у владельца; здесь — его sha256. Имя cookie — прежнее, чтобы не разлогинить.
def site_consts():
    return {
        "SITE_CLARITY": CLARITY_ID,   # пульт берёт отсюда ссылку на проект Clarity
        "SITE_HOST": "alfimov.kz", "SITE_URL": SITE_URL, "SITE_BRAND": BRAND, "SITE_BRAND_UPPER": "ALFIMOV.KZ",
        "SITE_DATA": "alfimov-data", "SITE_INDEXNOW_KEY": INDEXNOW_KEY,
        "SITE_SETUP_SHA256": "5d90752c03e149d521e3a97043a8a776a552318744d6c5527618fdc0eb191efb",
        "SITE_COOKIE": "alf_admin", "SITE_PHONE": PHONE_DISPLAY, "SITE_TG_LABEL": "продвижение", "SITE_TG_HUB_UP": 0,
        "SITE_LEAD_NAME": True, "SITE_LEAD_CONSENT": False, "NICHE_AUTHOR": "",
    }


def php_str(v):
    return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    enginekit.install(DIST)                              # общий движок: блог, ИИ, очередь статей, SEO, админка, заявки, бот
    shutil.copytree(STATIC, DIST, dirs_exist_ok=True)    # файлы сайта поверх движка

    paths = []
    for c in LANGS:
        for p, doc in [build_home(c), *(build_service(c, s) for s in c.SERVICES), build_contacts(c)]:
            write(p, doc)
            paths.append(p)
    write("/404.html", build_404(content_ru))
    write("/kz/404.html", build_404(content_kz))
    p, doc = build_privacy()
    write(p, doc)
    paths.append(p)
    # Рекламные страницы заказчиков (/lp/…): не в sitemap, noindex. Ответы опроса — для проверки в lp-send.php.
    lp = {}
    for client in [lp_guestory.CLIENT]:
        for p in client["pages"]:
            write(f"/lp/{client['slug']}/{p['slug']}/", lp_render.render(client, p))
        lp[client["slug"]] = lp_render.answers(client)
    (DIST / "api" / "_lp-clients.json").write_text(json.dumps(lp, ensure_ascii=False), encoding="utf-8")

    # Блог и админка — общий движок (engine/) на хостинге; здесь — настройки сайта, тексты ниши и оформление.
    enginekit.write_site_php(DIST, site_consts())
    enginekit.write_prompts(DIST, ROOT / "site" / "prompts.php")
    missing = enginekit.check_htaccess(DIST)
    if missing:
        raise SystemExit("В static/.htaccess нет правил движка: " + "; ".join(missing))
    (DIST / "_blog" / "parts.json").write_text(json.dumps(blog_parts(), ensure_ascii=False), encoding="utf-8")
    (DIST / "_blog" / "popup.php").write_text(blog_popup_php(), encoding="utf-8")
    (DIST / "_blog" / "sitemap.tpl").write_text(sitemap(paths), encoding="utf-8")
    # Статьи из репозитория — стартовый набор: админка один раз переносит их на хостинг при настройке.
    seed = ROOT / "content" / "articles"
    if seed.is_dir():
        shutil.copytree(seed, DIST / "_blog" / "seed")
    (DIST / "robots.txt").write_text(enginekit.robots_txt(SITE_URL, extra_public_api=["lp-send.php"]), encoding="utf-8")
    (DIST / "_blog" / "llms.tpl").write_text(llms_txt(), encoding="utf-8")
    (DIST / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8")
    # Какая сборка сейчас на хостинге: https://alfimov.kz/version.txt
    import subprocess
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    (DIST / "version.txt").write_text(f"{sha or 'local'}\n", encoding="utf-8")

    token, chat = os.environ.get("TG_BOT_TOKEN", ""), os.environ.get("TG_CHAT_ID", "")
    (DIST / "api" / "config.php").write_text(
        f"<?php\nreturn ['tg_token' => {php_str(token)}, 'tg_chat' => {php_str(chat)}];\n", encoding="utf-8"
    )
    # CSP script-src: хэши всех инлайн-скриптов, встреченных при сборке (csp_hash) — собрались выше,
    # пока строились все страницы (page()). Плейсхолдер — в static/.htaccess.
    ht_path = DIST / ".htaccess"
    ht = ht_path.read_text(encoding="utf-8")
    if "%%SCRIPT_HASHES%%" not in ht:
        raise SystemExit("В static/.htaccess нет %%SCRIPT_HASHES%% — CSP script-src будет без хэшей")
    ht_path.write_text(ht.replace("%%SCRIPT_HASHES%%", " ".join(sorted(CSP_SCRIPT_HASHES))), encoding="utf-8")
    print(f"Built {len(paths)} pages → {DIST}")
    issues = seo_audit.audit(DIST)
    for i in issues:
        if i.severity != "info":
            print(f"  {i}")
    print(f"  {seo_audit.summary(issues)}")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import http.server
        import functools

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
        print("http://localhost:8000")
        http.server.ThreadingHTTPServer(("127.0.0.1", 8000), handler).serve_forever()
