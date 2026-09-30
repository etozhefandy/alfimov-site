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


class PlanTest(unittest.TestCase):
    def ideas(self, *keys):
        return {"ideas": [{"topic": k, "main_keyword": k, "keywords": [k]} for k in keys]}

    def test_two_per_week_tue_thu_skips_taken_and_used(self):
        from datetime import datetime
        import blog
        start = datetime(2026, 9, 30, 21, 0, tzinfo=blog.TZ)  # среда
        articles = [{"keywords": ["Уже Есть"], "publish_at": "2026-10-01T10:13"},  # четверг занят
                    {"keywords": [], "publish_at": ""}]
        plan = topic_ideas.with_plan(self.ideas("a", "уже есть", "b", "c"), articles, per_week=2, start=start)
        dates = [i["suggested_date"] for i in plan["ideas"]]
        self.assertEqual(dates, ["2026-10-06T10:00", "", "2026-10-08T10:00", "2026-10-13T10:00"])
        self.assertEqual([i["used"] for i in plan["ideas"]], [False, True, False, False])

    def test_three_per_week_and_bad_value(self):
        from datetime import datetime
        import blog
        start = datetime(2026, 9, 30, 9, 0, tzinfo=blog.TZ)
        plan = topic_ideas.with_plan(self.ideas("a", "b", "c"), [], per_week=3, start=start)
        self.assertEqual([i["suggested_date"][:10] for i in plan["ideas"]], ["2026-10-02", "2026-10-05", "2026-10-07"])
        self.assertEqual(topic_ideas.with_plan(self.ideas("a"), [], per_week=9, start=start)["per_week"], 2)

    def test_no_cache(self):
        self.assertEqual(topic_ideas.with_plan(None)["ideas"], [])


if __name__ == "__main__":
    unittest.main()
