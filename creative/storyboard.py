"""Brief -> validated storyboard (scenes with voiceover, on-screen text and image prompt)."""
from __future__ import annotations

from . import llm
from .compliance import check_copy, check_image_prompt

WORDS_PER_SECOND = 2.5
SYSTEM = ("You are a creative strategist for short-form video ads. Never make medical or health-outcome "
          "claims. Keep voiceover short enough to be spoken in the scene's duration.")


def build_prompt(brief: dict) -> str:
    return (
        f"Write a {brief['duration_s']}-second storyboard for {brief['brand']}, {brief['product']}.\n"
        f"Audience: {brief['audience']}. Tone: {brief['tone']}. Platform: {brief['platform']}. "
        f"Final call to action: {brief['cta']}.\n"
        'Reply with ONLY JSON: {"scenes": [{"id": 1, "duration_s": 6, "voiceover": "...", '
        '"on_screen_text": "...", "visual_prompt": "..."}]}\n'
        f"Use 3-8 scenes whose durations sum to about {brief['duration_s']} seconds."
    )


def make_validator(brief: dict):
    def validate(obj) -> None:
        scenes = obj.get("scenes") if isinstance(obj, dict) else None
        if not isinstance(scenes, list) or not 3 <= len(scenes) <= 8:
            raise ValueError("'scenes' must be a list of 3-8 scenes")
        total = 0
        for i, s in enumerate(scenes, 1):
            if s.get("id") != i:
                raise ValueError(f"scene ids must be sequential starting at 1 (got {s.get('id')} at position {i})")
            for key in ("voiceover", "on_screen_text", "visual_prompt"):
                if not isinstance(s.get(key), str) or not s[key].strip():
                    raise ValueError(f"scene {i} missing {key}")
            d = s.get("duration_s")
            if isinstance(d, bool) or not isinstance(d, (int, float)) or d <= 0:
                raise ValueError(f"scene {i} needs a positive duration_s")
            limit = d * WORDS_PER_SECOND
            if len(s["voiceover"].split()) > limit:
                raise ValueError(f"scene {i} voiceover has {len(s['voiceover'].split())} words; max {limit:.0f} for {d}s")
            total += d
        if abs(total - brief["duration_s"]) > 3:
            raise ValueError(f"durations sum to {total}s; target is {brief['duration_s']}s")
    return validate


def check_storyboard(scenes: list[dict]) -> list[dict]:
    problems = []
    for s in scenes:
        for field, checker in (("voiceover", check_copy), ("on_screen_text", check_copy),
                               ("visual_prompt", check_image_prompt)):
            for p in checker(s[field]):
                problems.append({"scene": s["id"], "field": field, "problem": p})
    return problems


def generate_storyboard(brief: dict, provider: str = "mock", model: str = "mock-large",
                        complete_fn=None) -> tuple[list[dict], float]:
    obj, attempts = llm.complete_json(build_prompt(brief), make_validator(brief), system=SYSTEM,
                                      complete_fn=complete_fn, provider=provider, model=model)
    return obj["scenes"], sum(a.cost_usd for a in attempts)
