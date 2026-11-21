import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build  # noqa: E402
import seo_audit  # noqa: E402

GOOD_DESC = "Описание страницы нормальной длины для поисковой выдачи, чтобы проверка не ругалась на слишком короткий текст."


def page(title, h1=1, desc=GOOD_DESC, body="", links=(), path=None, head=""):
    heads = "".join("<h1>Заголовок</h1>" for _ in range(h1))
    a = "".join(f'<a href="{x}">x</a>' for x in links)
    words = " ".join(["слово"] * 350)
    canon = f'<link rel="canonical" href="https://x.kz{path}">' if path else ""
    return (f'<html><head><title>{title}</title><meta name="description" content="{desc}">{canon}{head}</head>'
            f"<body><main>{heads}{body}<p>{words}</p>{a}</main></body></html>")


class AuditRulesTest(unittest.TestCase):
    def make(self, files):
        d = Path(tempfile.mkdtemp())
        for rel, html in files.items():
            f = d / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(html, encoding="utf-8")
        return {(i.severity, i.title) for i in seo_audit.audit(d)}, seo_audit.audit(d)

    def test_clean_pair(self):
        found, _ = self.make({"index.html": page("Главная страница агентства", links=["/a/"], path="/"),
                              "a/index.html": page("Страница услуги агентства", links=["/"], desc=GOOD_DESC + " Услуга.", path="/a/")})
        self.assertEqual(found, set())

    def test_llms_txt_link_not_broken(self):
        # /llms.txt — PHP-маршрут на хостинге, не файл в dist/; ссылку на него (rel=alternate в <head>
        # каждой страницы) аудит не должен считать битой.
        found, _ = self.make({"index.html": page("Главная страница агентства", links=["/llms.txt"], path="/")})
        self.assertEqual(found, set())

    def test_detects_problems(self):
        found, _ = self.make({
            "index.html": page("Одинаковый заголовок страницы", h1=2, links=["/nope/", "/b/"],
                               body='<h2>a</h2><h4>b</h4><img src="/x.png">'),
            "b/index.html": page("Одинаковый заголовок страницы", h1=0, desc="Коротко"),
            "c/index.html": page("Очень длинный заголовок страницы, который точно не влезет в выдачу Google"),
        })
        for expected in [("critical", "Битая внутренняя ссылка"), ("critical", "Одинаковый title"),
                         ("critical", "На странице не один H1"), ("warning", "Пропущен уровень заголовка"),
                         ("warning", "Картинка без alt"), ("warning", "Нет входящих ссылок (страница-сирота)"),
                         ("warning", "Title длиннее 60 символов (Google обрежет)"), ("info", "Description короткий")]:
            self.assertIn(expected, found)


def alt(**langs):
    return "".join(f'<link rel="alternate" hreflang="{k.replace("_", "-")}" href="https://x.kz{v}">' for k, v in langs.items())


class LinksMetaTest(unittest.TestCase):
    """canonical, hreflang RU↔KZ, карта сайта, JSON-LD, ссылки на 301 (21.11.2026)."""

    def run_audit(self, files):
        d = Path(tempfile.mkdtemp())
        for rel, text in files.items():
            f = d / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")
        return {(i.severity, i.title) for i in seo_audit.audit(d) if i.severity != "info"}

    def pair(self, kz_head=None, ru_extra="", sitemap=None, extra=None):
        ru = alt(ru_KZ="/", kk_KZ="/kz/")
        files = {
            "index.html": page("Главная страница агентства", links=["/kz/"], path="/", head=ru + ru_extra),
            "kz/index.html": page("Агенттіктің басты беті тексеру", links=["/"], path="/kz/",
                                  desc=GOOD_DESC + " KZ.", head=alt(kk_KZ="/kz/", ru_KZ="/") if kz_head is None else kz_head),
            "_blog/sitemap.tpl": sitemap if sitemap is not None else "<urlset><url><loc>https://x.kz/</loc></url><url><loc>https://x.kz/kz/</loc></url></urlset>",
        }
        files.update(extra or {})
        return self.run_audit(files)

    def test_clean_pair_with_hreflang_and_sitemap(self):
        self.assertEqual(self.pair(), set())

    def test_canonical_to_other_page(self):
        found = self.run_audit({"index.html": page("Главная страница агентства", path="/a/")})
        self.assertIn(("critical", "canonical указывает на другую страницу"), found)

    def test_missing_canonical(self):
        self.assertIn(("critical", "Не один canonical"), self.run_audit({"index.html": page("Главная страница агентства")}))

    def test_hreflang_without_return_link(self):
        found = self.pair(kz_head=alt(kk_KZ="/kz/"))
        self.assertIn(("critical", "Языковая пара не ссылается обратно (hreflang)"), found)

    def test_hreflang_to_missing_page(self):
        found = self.pair(ru_extra=alt(en="/en/"))
        self.assertIn(("critical", "hreflang ведёт на несуществующую или закрытую страницу"), found)

    def test_sitemap_missing_page_and_unlisted_page(self):
        sm = "<urlset><url><loc>https://x.kz/</loc></url><url><loc>https://x.kz/kz/politika/</loc></url></urlset>"
        found = self.pair(sitemap=sm)
        self.assertIn(("critical", "В карте сайта несуществующая страница"), found)
        self.assertIn(("warning", "Страницы нет в карте сайта"), found)

    def test_sitemap_noindex_page(self):
        sm = "<urlset><url><loc>https://x.kz/</loc></url><url><loc>https://x.kz/kz/</loc></url><url><loc>https://x.kz/lp/</loc></url></urlset>"
        found = self.pair(sitemap=sm, extra={"lp/index.html": '<html><head><meta name="robots" content="noindex"></head></html>'})
        self.assertIn(("critical", "В карте сайта страница, закрытая от поиска"), found)

    def test_broken_json_ld(self):
        found = self.pair(ru_extra='<script type="application/ld+json">{"@context": "https://schema.org", "name": "x",}</script>')
        self.assertIn(("critical", "Разметка JSON-LD не разбирается"), found)
        found = self.pair(ru_extra='<script type="application/ld+json">{"@context": "https://schema.org", "name": "x"}</script>')
        self.assertIn(("critical", "В разметке JSON-LD нет @type"), found)

    def test_link_to_redirect(self):
        ht = "RewriteRule ^old/?$ /kz/ [L,R=301]\nRewriteRule ^blog$ /blog/ [L,R=301]\n"
        d = Path(tempfile.mkdtemp())
        for rel, text in {".htaccess": ht, "kz/index.html": page("Агенттіктің басты беті тексеру", path="/kz/"),
                          "index.html": page("Главная страница агентства", links=["/kz/", "/old/", "/blog/"], path="/")}.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(text, encoding="utf-8")
        hits = [i.detail for i in seo_audit.audit(d) if i.title == "Ссылка ведёт на адрес с переадресацией (301)"]
        self.assertEqual(hits, ["/old/"])   # /blog/ живой: «^blog$ → /blog/» только добавляет слэш


class RealSiteTest(unittest.TestCase):
    """Статическая часть сайта не должна давать critical и warning (ссылки на /blog/ — живые, PHP)."""

    def test_site_is_clean(self):
        tmp = Path(tempfile.mkdtemp())
        orig = build.DIST
        build.DIST = tmp / "dist"
        try:
            build.build()
            bad = [str(i) for i in seo_audit.audit(build.DIST) if i.severity != "info"]
        finally:
            build.DIST = orig
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
