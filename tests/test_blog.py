"""Тесты блога: хранилище, расписание, markdown, сборка, ИИ-автор (без сети), сервер админки.

    python3 -m unittest discover tests -v
"""
import http.client
import json
import shutil
import sys
import tempfile
import threading
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import blog  # noqa: E402
import build  # noqa: E402
import seo_writer  # noqa: E402


def art(slug, **kw):
    a = {"slug": slug, "title": f"Статья {slug}", "description": "Описание", "body_md": "## Раздел\n\nТекст.\n"}
    a.update(kw)
    return a


def past(hours=1):
    return (blog.now() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M")


def future(days=1):
    return (blog.now() + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M")


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._orig = (blog.ARTICLES_DIR, build.DIST)
        blog.ARTICLES_DIR = self.tmp / "articles"
        build.DIST = self.tmp / "dist"

    def tearDown(self):
        blog.ARTICLES_DIR, build.DIST = self._orig
        shutil.rmtree(self.tmp)


class StoreTest(Tmp):
    def test_save_load_roundtrip(self):
        blog.save(art("pervaya-statya", faq=[["Вопрос?", "Ответ."]], keywords=["таргет"]))
        a = blog.get("pervaya-statya")
        self.assertEqual(a["faq"], [["Вопрос?", "Ответ."]])
        self.assertEqual(a["status"], "draft")
        self.assertTrue(a["created_at"])

    def test_validation(self):
        with self.assertRaisesRegex(ValueError, "Адрес"):
            blog.save(art("Плохой адрес"))
        with self.assertRaisesRegex(ValueError, "дата выхода"):
            blog.save(art("bez-daty", status="scheduled"))
        with self.assertRaisesRegex(ValueError, "Обложка"):
            blog.save(art("oblozhka", cover_path="https://evil.example/x.png"))

    def test_rename_moves_file_and_keeps_created(self):
        a = blog.save(art("old-slug"))
        blog.save({**a, "slug": "new-slug"}, old_slug="old-slug")
        self.assertIsNone(blog.get("old-slug"))
        self.assertEqual(blog.get("new-slug")["created_at"], a["created_at"])

    def test_duplicate_slug_rejected(self):
        blog.save(art("one"))
        blog.save(art("two"))
        with self.assertRaisesRegex(ValueError, "занят"):
            blog.save(art("two"), old_slug="one")

    def test_related_drops_self(self):
        a = blog.save(art("self", related=["self", "other"]))
        self.assertEqual(a["related"], ["other"])

    def test_schedule_states(self):
        blog.save(art("draft"))
        blog.save(art("later", status="scheduled", publish_at=future()))
        blog.save(art("due", status="scheduled", publish_at=past()))
        states = {a["slug"]: blog.state(a) for a in blog.load_all()}
        self.assertEqual(states, {"draft": "draft", "later": "scheduled", "due": "live"})
        self.assertEqual([a["slug"] for a in blog.live()], ["due"])

    def test_slugify_ru_kz(self):
        self.assertEqual(blog.slugify("Таргет в Алматы: цены 2026"), "target-v-almaty-tseny-2026")
        self.assertEqual(blog.slugify("Қазақша жарнама"), "kazaksha-zharnama")


class MarkdownTest(unittest.TestCase):
    def test_blocks_and_toc(self):
        md = ("Вступление с **жирным** и [ссылкой](/smm/).\n\n## Первый раздел\n\n- один\n- два\n\n"
              "### Подраздел\n\n1. шаг\n2. шаг\n\n## Первый раздел\n\n> цитата\n\n"
              "| A | B |\n|---|---|\n| 1 | 2 |\n")
        out, toc = blog.markdown(md)
        self.assertIn("<strong>жирным</strong>", out)
        self.assertIn('<a href="/smm/">ссылкой</a>', out)
        self.assertIn("<ul><li>один</li><li>два</li></ul>", out)
        self.assertIn("<ol>", out)
        self.assertIn('<h3 id="podrazdel">', out)
        self.assertIn("<blockquote>", out)
        self.assertIn("<td>1</td>", out)
        self.assertEqual([t for _, t in toc], ["Первый раздел", "Первый раздел"])
        self.assertEqual(toc[0][0] != toc[1][0], True)  # уникальные якоря

    def test_h1_downgraded_and_html_escaped(self):
        out, _ = blog.markdown("# Заголовок\n\n<script>alert(1)</script> [x](javascript:alert(1))")
        self.assertIn("<h2", out)
        self.assertNotIn("<h1", out)
        self.assertNotIn("<script>", out)
        self.assertIn('href="#"', out)

    def test_external_link_new_tab(self):
        out, _ = blog.markdown("[внешняя](https://example.com)")
        self.assertIn('rel="noopener"', out)


class BuildTest(Tmp):
    def test_only_live_articles_built(self):
        blog.save(art("vyshla", status="scheduled", publish_at=past(), faq=[["Q?", "A."]]))
        blog.save(art("zavtra", status="scheduled", publish_at=future()))
        blog.save(art("chernovik"))
        build.build()
        self.assertTrue((build.DIST / "blog" / "vyshla" / "index.html").is_file())
        self.assertFalse((build.DIST / "blog" / "zavtra").exists())
        self.assertFalse((build.DIST / "blog" / "chernovik").exists())
        page = (build.DIST / "blog" / "vyshla" / "index.html").read_text()
        self.assertIn('"@type": "BlogPosting"', page)
        self.assertIn('"@type": "FAQPage"', page)
        self.assertIn('<link rel="canonical" href="https://alfimov.kz/blog/vyshla/">', page)
        self.assertNotIn('hreflang="kk-KZ" href="https://alfimov.kz/kz/blog', page)
        sm = (build.DIST / "sitemap.xml").read_text()
        self.assertIn("https://alfimov.kz/blog/vyshla/", sm)
        self.assertNotIn("zavtra", sm)
        self.assertIn('href="/blog/"', (build.DIST / "index.html").read_text())
        self.assertNotIn('href="/blog/"', (build.DIST / "kz" / "index.html").read_text())

    def test_no_blog_without_live_articles(self):
        blog.save(art("chernovik"))
        build.build()
        self.assertFalse((build.DIST / "blog").exists())
        self.assertNotIn("/blog/", (build.DIST / "index.html").read_text())
        self.assertNotIn("/blog/", (build.DIST / "sitemap.xml").read_text())

    def test_related_prefers_chosen(self):
        for s in ("a1", "a2", "a3", "a4"):
            blog.save(art(s, status="scheduled", publish_at=past()))
        a = blog.save(art("main", status="scheduled", publish_at=past(), related=["a4"]))
        _, doc = build.build_article(a, blog.live())
        rel = doc.split("Читайте также")[-1]
        self.assertLess(rel.index("/blog/a4/"), rel.index("/blog/a1/") if "/blog/a1/" in rel else len(rel))
        self.assertEqual(rel.count('class="post-card'), 3)


class FakeStream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.msg


class FakeClient:
    def __init__(self, payload, stop="end_turn"):
        self.calls = []
        text = json.dumps(payload, ensure_ascii=False)
        msg = SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=text)])
        self.messages = SimpleNamespace(stream=lambda **kw: (self.calls.append(kw), FakeStream(msg))[1])


PAYLOAD = {
    "slug": "stoimost-targeta", "title": "Сколько стоит таргет", "seo_title": "Стоимость таргета",
    "description": "d", "lead": "l", "summary": "s", "category": "Таргет", "keywords": ["стоимость таргета"],
    "body_md": "## Раздел\n\nТекст", "faq": [{"q": "Вопрос?", "a": "Ответ."}], "related": ["est", "net-takoy"],
}


class WriterTest(unittest.TestCase):
    def test_generate_maps_fields(self):
        c = FakeClient(PAYLOAD)
        out = seo_writer.generate("Стоимость таргета", ["стоимость таргета"], "", 1200,
                                  [{"slug": "est", "title": "Есть"}], client=c)
        self.assertEqual(out["faq"], [["Вопрос?", "Ответ."]])
        self.assertEqual(out["related"], ["est"])
        kw = c.calls[0]
        self.assertEqual(kw["model"], seo_writer.MODEL)
        self.assertEqual(kw["output_config"]["format"]["type"], "json_schema")
        self.assertIn("/target-facebook-instagram/", kw["system"])
        self.assertIn("est — Есть", kw["messages"][0]["content"])

    def test_refusal_and_truncation(self):
        with self.assertRaisesRegex(seo_writer.WriterError, "отказался"):
            seo_writer.generate("x", client=FakeClient(PAYLOAD, stop="refusal"))
        with self.assertRaisesRegex(seo_writer.WriterError, "лимит"):
            seo_writer.generate("x", client=FakeClient(PAYLOAD, stop="max_tokens"))

    def test_empty_topic(self):
        with self.assertRaises(seo_writer.WriterError):
            seo_writer.generate("  ", client=FakeClient(PAYLOAD))


class AdminServerTest(Tmp):
    def setUp(self):
        super().setUp()
        import admin
        self.admin = admin
        self.srv = admin.http.server.ThreadingHTTPServer(("127.0.0.1", 0), admin.Handler)
        self.port = self.srv.server_address[1]
        self._hosts = admin.ALLOWED_HOSTS
        admin.ALLOWED_HOSTS = {f"127.0.0.1:{self.port}"}
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.admin.ALLOWED_HOSTS = self._hosts
        super().tearDown()

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Content-Type": "application/json", **(headers or {})}
        c.request(method, path, json.dumps(body) if body is not None else None, h)
        r = c.getresponse()
        data = r.read()
        return r.status, data

    def test_crud_and_preview(self):
        st, _ = self.req("POST", "/admin/api/articles", {"article": art("proba")})
        self.assertEqual(st, 200)
        st, data = self.req("GET", "/admin/api/articles")
        self.assertEqual([a["slug"] for a in json.loads(data)["articles"]], ["proba"])
        st, data = self.req("GET", "/admin/preview/proba/")
        self.assertEqual(st, 200)
        self.assertIn("Статья proba", data.decode())
        st, _ = self.req("POST", "/admin/api/articles", {"article": art("Плохо")})
        self.assertEqual(st, 400)
        st, _ = self.req("DELETE", "/admin/api/articles/proba")
        self.assertEqual(st, 200)

    def test_rejects_foreign_origin_and_host(self):
        st, _ = self.req("POST", "/admin/api/articles", {"article": art("x")}, {"Origin": "https://evil.example"})
        self.assertEqual(st, 403)
        st, _ = self.req("GET", "/admin/api/articles", headers={"Host": "evil.example"})
        self.assertEqual(st, 403)

    def test_static_no_traversal(self):
        st, _ = self.req("GET", "/../admin.py")
        self.assertEqual(st, 404)
        st, _ = self.req("GET", "/assets/style.css")
        self.assertEqual(st, 200)


if __name__ == "__main__":
    unittest.main()
