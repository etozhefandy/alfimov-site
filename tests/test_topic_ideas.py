import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import seo_writer  # noqa: E402
import topic_ideas  # noqa: E402


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
        msg = SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=json.dumps(payload))])
        self.messages = SimpleNamespace(stream=lambda **kw: (self.calls.append(kw), FakeStream(msg))[1])


class CollectTest(unittest.TestCase):
    def test_merges_engines_and_normalizes(self):
        def fetch(url):
            if "google" in url:
                return ["Таргет Инстаграм  Цена", "таргет алматы"]
            return ["таргет инстаграм цена"]
        found = topic_ideas.collect(seeds=["таргет"], patterns=["{s}"], fetch=fetch, workers=2)
        self.assertEqual(found["таргет инстаграм цена"], {"google", "yandex"})
        self.assertEqual(found["таргет алматы"], {"google"})


class ProposeTest(unittest.TestCase):
    IDEA = {"topic": "Сколько стоит таргет", "main_keyword": "таргет цена", "keywords": ["таргет цена"],
            "intent": "коммерческий", "service": "target-facebook-instagram", "why": "спрос"}

    def test_prompt_and_parse(self):
        client = FakeClient({"ideas": [self.IDEA, {**self.IDEA, "service": "nope"}]})
        ideas = topic_ideas.propose({"таргет цена": {"google", "yandex"}}, ["Старая статья"], "TikTok", client=client)
        self.assertEqual(ideas[0]["service"], "target-facebook-instagram")
        self.assertEqual(ideas[1]["service"], "")  # неизвестная услуга не выдумывается
        prompt = client.calls[0]["messages"][0]["content"]
        self.assertIn("таргет цена  [Google+Яндекс]", prompt)
        self.assertIn("Старая статья", prompt)
        self.assertIn("TikTok", prompt)
        self.assertEqual(client.calls[0]["model"], seo_writer.MODEL)

    def test_empty_queries(self):
        with self.assertRaises(seo_writer.WriterError):
            topic_ideas.propose({}, client=FakeClient({"ideas": []}))

    def test_refusal(self):
        with self.assertRaises(seo_writer.WriterError):
            topic_ideas.propose({"x": {"google"}}, client=FakeClient({}, stop="refusal"))


if __name__ == "__main__":
    unittest.main()
