"""Rubric-driven prompt iteration with a persistent log of every candidate and score."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import llm
from .compliance import IMAGE_AVOID, check_image_prompt

RUBRIC = {  # name: (points, test)
    "camera": (20, lambda p: re.search(r"close-up|wide shot|medium shot|overhead|handheld|shallow depth", p, re.I)),
    "lighting": (20, lambda p: re.search(r"soft|warm|golden hour|window light|lamp light|natural light|backlit", p, re.I)),
    "style": (20, lambda p: re.search(r"cinematic|documentary|photoreal|film grain|muted", p, re.I)),
    "length": (20, lambda p: 25 <= len(p.split()) <= 60),
    "no_text_in_image": (10, lambda p: not re.search(r"\b(text|caption|words|letters)\b", p, re.I)),
    "aspect": (10, lambda p: "9:16" in p),
}
SYSTEM = "You write precise prompts for image generation models. Reply with JSON only."


def score_prompt(prompt: str) -> dict:
    earned, missing = 0, []
    for name, (points, test) in RUBRIC.items():
        if test(prompt):
            earned += points
        else:
            missing.append(name)
    return {"score": earned, "missing": missing, "violations": check_image_prompt(prompt)}


def _rewrite_prompt(current: str, missing: list[str], n: int) -> str:
    return (f"Rewrite this image-generation prompt to fix what's missing. Reply ONLY JSON "
            f'{{"prompts": [...]}} with {n} rewrites.\n'
            f"Current prompt: {current}\nMissing: {', '.join(missing) or 'nothing'}\n"
            f"Avoid: {', '.join(p.strip(chr(92) + 'b') for p in IMAGE_AVOID)}. Keep the original subject; "
            "never ask for text or logos inside the image. Vertical 9:16 framing.")


def _validate(obj) -> None:
    prompts = obj.get("prompts") if isinstance(obj, dict) else None
    if not isinstance(prompts, list) or not prompts or not all(isinstance(p, str) and p.strip() for p in prompts):
        raise ValueError("'prompts' must be a non-empty list of strings")


def improve(prompt: str, scene_id: int, rounds: int = 2, variants: int = 2, target: int = 90,
            provider: str = "mock", model: str = "mock-large", complete_fn=None,
            log_path: str | None = None) -> dict:
    """Iteratively rewrite `prompt`. Only compliant candidates can become the best prompt."""
    log = Path(log_path) if log_path else None
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)

    def record(round_no: int, text: str, s: dict, kept: bool) -> None:
        if log:
            with log.open("a") as f:
                f.write(json.dumps({"ts": time.time(), "scene": scene_id, "round": round_no, "prompt": text,
                                    "score": s["score"], "missing": s["missing"], "violations": s["violations"],
                                    "kept": kept}) + "\n")

    best, best_s, cost = prompt, score_prompt(prompt), 0.0
    initial = best_s["score"]
    record(0, best, best_s, True)
    used = 0
    for r in range(1, rounds + 1):
        if best_s["score"] >= target and not best_s["violations"]:
            break
        used = r
        obj, attempts = llm.complete_json(_rewrite_prompt(best, best_s["missing"], variants), _validate,
                                          system=SYSTEM, complete_fn=complete_fn, provider=provider, model=model)
        cost += sum(a.cost_usd for a in attempts)
        improved = False
        for cand in obj["prompts"]:
            s = score_prompt(cand)
            wins = not s["violations"] and (s["score"] > best_s["score"] or bool(best_s["violations"]))
            record(r, cand, s, wins)
            if wins:
                best, best_s, improved = cand, s, True
        if not improved:
            break
    return {"prompt": best, "score": best_s["score"], "initial_score": initial, "rounds": used, "cost_usd": cost,
            "violations": best_s["violations"]}
