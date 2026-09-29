import base64
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import blog  # noqa: E402
import image_gen  # noqa: E402


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener_returning(*responses):
    calls = []

    def opener(req, timeout=None):
        calls.append(json.loads(req.data))
        r = responses[len(calls) - 1]
        if isinstance(r, Exception):
            raise r
        return FakeResp(json.dumps(r).encode())
    return opener, calls


def http_error(code, message):
    body = io.BytesIO(json.dumps({"error": {"message": message}}).encode())
    return urllib.error.HTTPError(image_gen.API_URL, code, "err", {}, body)


class PromptTest(unittest.TestCase):
    def test_idea_wins_and_style_bans_cliches(self):
        p = image_gen.build_prompt("cover", "Заголовок", "", "кофейня вечером")
        self.assertIn("кофейня вечером", p)
        self.assertNotIn("Заголовок", p)
        self.assertIn("No text", p)
        self.assertIn("no rockets", p)

    def test_title_used_without_idea(self):
        self.assertIn("«Сколько стоит таргет»", image_gen.build_prompt("inline", "Сколько стоит таргет"))

    def test_nothing_to_draw(self):
        with self.assertRaises(image_gen.ImageError):
            image_gen.build_prompt("cover")


class GenerateTest(unittest.TestCase):
    def test_gpt_image_webp(self):
        img = b"WEBPDATA"
        opener, calls = opener_returning({"data": [{"b64_json": base64.b64encode(img).decode()}]})
        raw, ext = image_gen.generate("cover", "Тема", key="k", opener=opener)
        self.assertEqual((raw, ext), (img, ".webp"))
        self.assertEqual(calls[0]["model"], image_gen.MODEL)
        self.assertEqual(calls[0]["output_format"], "webp")
        self.assertEqual(calls[0]["size"], "1536x1024")

    def test_fallback_to_dalle(self):
        png = b"\x89PNGfake"
        opener, calls = opener_returning(http_error(400, "model not available"),
                                         {"data": [{"b64_json": base64.b64encode(png).decode()}]})
        raw, ext = image_gen.generate("inline", idea="схема", key="k", opener=opener)
        self.assertEqual([c["model"] for c in calls], [image_gen.MODEL, "dall-e-3"])
        self.assertIn(ext, (".jpg", ".png"))

    def test_bad_key_no_fallback(self):
        opener, calls = opener_returning(http_error(401, "Incorrect API key provided"))
        with self.assertRaises(image_gen.ImageError) as cm:
            image_gen.generate("cover", "Тема", key="k", opener=opener)
        self.assertEqual(len(calls), 1)
        self.assertIn("ключ", str(cm.exception))

    def test_missing_key(self):
        orig = image_gen.api_key
        image_gen.api_key = lambda: ""
        try:
            with self.assertRaises(image_gen.ImageError):
                image_gen.generate("cover", "Тема")
        finally:
            image_gen.api_key = orig


class MarkdownImageTest(unittest.TestCase):
    def test_figure_from_local_image(self):
        html, _ = blog.markdown("Текст\n\n![Схема воронки](/assets/blog/x-img.webp)\n\nДальше")
        self.assertIn('<figure><img src="/assets/blog/x-img.webp" alt="Схема воронки" loading="lazy">', html)
        self.assertIn("<figcaption>Схема воронки</figcaption>", html)

    def test_external_image_not_rendered(self):
        html, _ = blog.markdown("![x](https://evil.example/a.png)")
        self.assertNotIn("<img", html)


if __name__ == "__main__":
    unittest.main()
