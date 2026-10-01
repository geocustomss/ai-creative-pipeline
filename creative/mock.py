"""Template stand-in for a model so the pipeline runs offline. Not a quality benchmark."""
import json
import re

SCENES = [
    (6, "Another night, scrolling instead of sleeping. Sound familiar?", "Can't wind down?",
     "a person lying awake in bed looking at a phone at night"),
    (6, "Lumen helps you build a gentle evening routine, one small step at a time.", "One small step",
     "hands setting a phone on a nightstand beside a glass of water"),
    (6, "Dim the lights, breathe slowly, and let your day settle.", "Let the day settle",
     "a calm living room with a person stretching on a rug"),
    (6, "Members tell us evenings feel calmer and mornings less rushed.", "Calmer evenings",
     "a person smiling over a mug of tea by a window"),
    (6, "Start your free week tonight.", "Start your free week",
     "a person opening a phone app while sitting on a sofa"),
]
FIXES = {"camera": "medium shot, shallow depth of field", "lighting": "soft warm lamp light",
         "style": "cinematic documentary style, muted colors", "aspect": "vertical 9:16"}


def handler(system: str, prompt: str, model: str) -> str:
    if "Rewrite this image-generation prompt" in prompt:
        cur = re.search(r"Current prompt: (.*)\n", prompt).group(1)
        missing = [m.strip() for m in re.search(r"Missing: (.*)\n", prompt).group(1).split(",")]
        fixes = [FIXES[m] for m in missing if m in FIXES]
        return json.dumps({"prompts": [", ".join([cur] + fixes), ", ".join([cur] + fixes[:1])]})
    return json.dumps({"scenes": [
        {"id": i, "duration_s": d, "voiceover": v, "on_screen_text": t, "visual_prompt": p}
        for i, (d, v, t, p) in enumerate(SCENES, 1)]})
