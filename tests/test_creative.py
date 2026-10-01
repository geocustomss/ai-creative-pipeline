import json
import tempfile
import unittest
from pathlib import Path

from creative import llm, mock
from creative.compliance import check_copy, check_image_prompt
from creative.iterate import improve, score_prompt
from creative.pipeline import run
from creative.storyboard import check_storyboard, generate_storyboard, make_validator

llm.register_mock(mock.handler)
BRIEF = json.load(open("brief.json"))


def scene(i=1, d=6, vo="Short line.", text="Hi", vp="a person"):
    return {"id": i, "duration_s": d, "voiceover": vo, "on_screen_text": text, "visual_prompt": vp}


class ComplianceTest(unittest.TestCase):
    def test_copy_and_image_rules(self):
        self.assertTrue(check_copy("A miracle cure"))
        self.assertTrue(check_copy("see the before and after"))
        self.assertEqual(check_copy("Calmer evenings, one small step"), [])
        self.assertTrue(check_image_prompt("a pill bottle with a logo"))
        self.assertEqual(check_image_prompt("a person reading by a window"), [])


class StoryboardTest(unittest.TestCase):
    def setUp(self):
        self.validate = make_validator(BRIEF)

    def test_valid_storyboard_passes(self):
        scenes, _ = generate_storyboard(BRIEF)
        self.assertEqual(len(scenes), 5)
        self.assertEqual(check_storyboard(scenes), [])

    def test_rejects_voiceover_too_long_for_duration(self):
        scenes = [scene(i) for i in range(1, 6)]
        scenes[2]["voiceover"] = " ".join(["word"] * 30)
        with self.assertRaisesRegex(ValueError, "voiceover"):
            self.validate({"scenes": scenes})

    def test_rejects_bad_duration_total_and_ids(self):
        with self.assertRaisesRegex(ValueError, "sum"):
            self.validate({"scenes": [scene(i, d=2) for i in range(1, 4)]})
        bad_ids = [scene(1), scene(3), scene(4), scene(5), scene(6)]
        with self.assertRaisesRegex(ValueError, "sequential"):
            self.validate({"scenes": bad_ids})

    def test_flags_claims_per_field(self):
        problems = check_storyboard([scene(vo="This cures insomnia", vp="a pill on a table")])
        self.assertEqual({(p["scene"], p["field"]) for p in problems}, {(1, "voiceover"), (1, "visual_prompt")})


class IterateTest(unittest.TestCase):
    def test_scoring(self):
        weak = score_prompt("a person lying awake in bed")
        self.assertEqual(weak["score"], 10)
        self.assertIn("camera", weak["missing"])
        strong = score_prompt("medium shot of a person in bed, soft warm lamp light, cinematic documentary style, "
                              "muted colors, calm mood, quiet bedroom, shallow depth of field, vertical 9:16")
        self.assertEqual((strong["score"], strong["missing"]), (100, []))

    def test_improve_raises_score_and_logs_every_candidate(self):
        log = tempfile.mktemp(suffix=".jsonl")
        res = improve("a person lying awake in bed looking at a phone at night", 1, log_path=log)
        self.assertGreater(res["score"], res["initial_score"])
        rows = [json.loads(l) for l in Path(log).read_text().splitlines()]
        self.assertEqual(rows[0]["round"], 0)
        self.assertTrue(any(r["kept"] and r["round"] == 1 for r in rows))

    def test_non_compliant_candidates_are_never_kept(self):
        def evil(prompt, **kw):
            text = "medium shot, soft warm light, cinematic muted, vertical 9:16 of a pill bottle with a logo"
            return llm.Completion(json.dumps({"prompts": [text]}), "mock", "m")
        res = improve("a person in bed", 1, complete_fn=evil)
        self.assertEqual(res["prompt"], "a person in bed")
        self.assertEqual(res["violations"], [])

    def test_stops_early_when_target_met(self):
        calls = []
        def count(prompt, **kw):
            calls.append(1)
            return llm.complete(prompt, **kw)
        great = ("medium shot of a person in bed, soft warm lamp light, cinematic documentary style, muted colors, "
                 "calm mood, quiet bedroom, shallow depth of field, vertical 9:16")
        res = improve(great, 1, complete_fn=count)
        self.assertEqual((res["rounds"], len(calls)), (0, 0))


class PipelineTest(unittest.TestCase):
    def test_dry_run_writes_plan_and_creates_nothing(self):
        out = tempfile.mkdtemp()
        m = run(BRIEF, out)
        self.assertEqual(m["note"], "dry run: nothing generated")
        self.assertFalse(m["needs_human_review"])
        self.assertTrue(all(a["image"]["status"] == "planned" for a in m["assets"]))
        self.assertTrue(all(a["image"]["prompt_score"] > a["image"]["initial_score"] for a in m["assets"]))
        for name in ("storyboard.json", "storyboard.md", "manifest.json", "iterations.jsonl"):
            self.assertTrue((Path(out) / name).exists(), name)

    def test_live_mode_with_fake_providers_and_partial_failure(self):
        out = tempfile.mkdtemp()
        def tts(text, path):
            Path(path).write_bytes(b"audio")
        def imager(prompt, path):
            if "scene3" in path:
                raise llm.LLMError("rate limited")
            Path(path).write_bytes(b"png")
        m = run(BRIEF, out, live=True, tts=tts, imager=imager)
        statuses = [a["image"]["status"] for a in m["assets"]]
        self.assertEqual(statuses.count("created"), 4)
        self.assertTrue(statuses[2].startswith("failed"))
        self.assertTrue((Path(out) / "audio" / "scene1.mp3").exists())

    def test_live_mode_is_blocked_when_storyboard_has_claims(self):
        bad = json.dumps({"scenes": [
            {"id": i, "duration_s": 10, "voiceover": "This will cure your insomnia." if i == 1 else "Sleep well.",
             "on_screen_text": "Hi", "visual_prompt": "a person in bed"} for i in range(1, 4)]})
        called = []
        out = tempfile.mkdtemp()
        m = run(BRIEF, out, live=True, tts=lambda *a: called.append(1), imager=lambda *a: called.append(1),
                complete_fn=lambda p, **kw: llm.Completion(
                    bad if "storyboard" in p else mock.handler("", p, "m"), "mock", "m"))
        self.assertTrue(m["needs_human_review"])
        self.assertEqual(called, [])
        self.assertIn("skipped", m["note"])


if __name__ == "__main__":
    unittest.main()
