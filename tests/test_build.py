"""Сборка: оформление для PHP-блога и правила хостинга. PHP-часть — tests/php/test_blog.php (запускается отсюда)."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parent.parent


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build.build()

    def test_parts_for_php_blog(self):
        p = json.loads((build.DIST / "_blog" / "parts.json").read_text(encoding="utf-8"))
        for mark in ("%%PATH%%", "%%TITLE%%", "%%DESC%%", "%%BODY%%", "%%IMAGE%%", "%%OGTYPE%%", '"__SCHEMA__"'):
            self.assertIn(mark, p["shell"])
        self.assertIn('href="/blog/"', p["shell"])  # «Блог» в меню
        self.assertIn("%%SOURCE%%", p["lead_form"])
        self.assertIn("%%ITEMS%%", p["faq_wrap"])
        self.assertTrue(p["services"])

    def test_home_marker_and_no_static_blog(self):
        self.assertRegex((build.DIST / "index.html").read_text(encoding="utf-8"), r"<!--BLOG-HOME:\d\d-->")
        self.assertNotIn("BLOG-HOME", (build.DIST / "kz" / "index.html").read_text(encoding="utf-8"))
        self.assertFalse((build.DIST / "blog").exists())
        self.assertFalse((build.DIST / "sitemap.xml").exists())  # её отдаёт PHP вместе со статьями
        self.assertIn("</urlset>", (build.DIST / "_blog" / "sitemap.tpl").read_text(encoding="utf-8"))

    def test_hosting_rules(self):
        ht = (build.DIST / ".htaccess").read_text(encoding="utf-8")
        for rule in ("_blog/router.php?route=home", "route=article&slug=$1", "admin/api.php?r=$1/$2"):
            self.assertIn(rule, ht)
        self.assertIn("RewriteCond %{THE_REQUEST} \\s/+_blog/", ht)
        # «Require all denied» пишет отказы в лог ошибок → fail2ban хостинга банит IP посетителя.
        self.assertFalse((build.DIST / "_blog" / ".htaccess").exists())
        self.assertFalse((build.DIST / "admin" / ".htaccess").exists())
        self.assertNotIn("Require all denied", ht)
        robots = (build.DIST / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Disallow: /admin/", robots)
        for bot in ("OAI-SearchBot", "PerplexityBot", "ClaudeBot", "Google-Extended"):
            self.assertIn(f"User-agent: {bot}\nAllow: /", robots)
        self.assertIn("route=llms", ht)
        self.assertTrue((build.DIST / f"{build.INDEXNOW_KEY}.txt").is_file())

    @unittest.skipUnless(shutil.which("php"), "нужен php")
    def test_php_suite(self):
        for f in sorted((build.DIST).rglob("*.php")):
            r = subprocess.run(["php", "-l", str(f)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = subprocess.run(["php", str(ROOT / "tests" / "php" / "test_blog.php")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
