import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import blog
import build


def article(slug, at, status="scheduled"):
    return blog.normalize({"slug": slug, "title": slug.title(), "body_md": "Текст", "status": status,
                           "publish_at": at.strftime("%Y-%m-%dT%H:%M")})


class ScheduledTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.old_dir, blog.ARTICLES_DIR = blog.ARTICLES_DIR, self.tmp / "articles"
        self.addCleanup(setattr, blog, "ARTICLES_DIR", self.old_dir)
        base = blog.now().replace(second=0, microsecond=0)
        self.past, self.future = base - timedelta(days=1), base + timedelta(days=2)
        for a in (article("old-post", self.past), article("new-post", self.future), article("draft-post", self.future, "draft")):
            blog.save(a)

    def test_freeze_moves_clock(self):
        blog.freeze(self.future)
        try:
            self.assertEqual({a["slug"] for a in blog.live()}, {"old-post", "new-post"})
        finally:
            blog.freeze(None)
        self.assertEqual({a["slug"] for a in blog.live()}, {"old-post"})

    def test_future_times_only_scheduled(self):
        self.assertEqual(build.future_times(), [blog.parse_dt(self.future.strftime("%Y-%m-%dT%H:%M"))])

    def test_snapshot_holds_future_article_and_is_hidden(self):
        dist = self.tmp / "dist"
        build.build(out=dist, quiet=True)
        self.assertFalse((dist / "blog" / "new-post").exists())
        [snap] = [p for p in (dist / build.SCHEDULED).iterdir() if p.is_dir()]
        m = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("blog/new-post/index.html", m["files"])
        self.assertIn("blog/index.html", m["files"])
        self.assertNotIn("blog/draft-post/index.html", m["files"])
        self.assertEqual(m["at_unix"], int(build.future_times()[0].timestamp()))
        self.assertTrue((dist / build.SCHEDULED / ".htaccess").is_file())
        self.assertIs(build.OUT, build.DIST)

    @unittest.skipUnless(shutil.which("php"), "нужен php")
    def test_php_applies_due_snapshot_once(self):
        dist = self.tmp / "dist"
        build.build(out=dist, quiet=True)
        [mf] = list((dist / build.SCHEDULED).glob("*/manifest.json"))
        m = json.loads(mf.read_text(encoding="utf-8"))
        script = dist / build.SCHEDULED / "publish.php"
        out = subprocess.run(["php", str(script)], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out, "")  # дата ещё не наступила
        m["at_unix"] = 1
        mf.write_text(json.dumps(m), encoding="utf-8")
        out = subprocess.run(["php", str(script)], capture_output=True, text=True, check=True).stdout
        self.assertIn("опубликовано по расписанию", out)
        self.assertTrue((dist / "blog" / "new-post" / "index.html").is_file())
        out = subprocess.run(["php", str(script)], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out, "")  # повторно не применяется


if __name__ == "__main__":
    unittest.main()
