"""Brief -> storyboard -> improved image prompts -> (optionally) voiceover + images, with a manifest."""
from __future__ import annotations

import json
from pathlib import Path

from . import llm, providers
from .iterate import improve
from .storyboard import check_storyboard, generate_storyboard


def run(brief: dict, out_dir: str, live: bool = False, provider: str = "mock", model: str = "mock-large",
        complete_fn=None, rounds: int = 2, tts=None, imager=None) -> dict:
    out = Path(out_dir)
    (out / "audio").mkdir(parents=True, exist_ok=True)
    (out / "images").mkdir(parents=True, exist_ok=True)
    scenes, cost = generate_storyboard(brief, provider, model, complete_fn)
    blocked = check_storyboard(scenes)

    assets = []
    for s in scenes:
        res = improve(s["visual_prompt"], s["id"], rounds=rounds, provider=provider, model=model,
                      complete_fn=complete_fn, log_path=str(out / "iterations.jsonl"))
        cost += res["cost_usd"]
        assets.append({
            "scene": s["id"], "duration_s": s["duration_s"],
            "voiceover": {"text": s["voiceover"], "path": f"audio/scene{s['id']}.mp3", "status": "planned"},
            "image": {"prompt": res["prompt"], "prompt_score": res["score"], "initial_score": res["initial_score"],
                      "path": f"images/scene{s['id']}.png", "status": "planned"},
            "on_screen_text": s["on_screen_text"]})

    if live and blocked:
        note = "live generation skipped: storyboard has compliance problems"
    elif live:
        note = "live generation attempted"
        tts, imager = tts or providers.elevenlabs_tts, imager or providers.openai_image
        for a in assets:  # a failed asset is recorded, not fatal
            for kind, fn, arg in (("voiceover", tts, a["voiceover"]["text"]), ("image", imager, a["image"]["prompt"])):
                try:
                    fn(arg, str(out / a[kind]["path"]))
                    a[kind]["status"] = "created"
                except llm.LLMError as e:
                    a[kind]["status"] = f"failed: {e}"
    else:
        note = "dry run: nothing generated"

    manifest = {"brief": brief, "note": note, "llm_cost_usd": round(cost, 6),
                "needs_human_review": bool(blocked), "compliance_problems": blocked, "assets": assets}
    (out / "storyboard.json").write_text(json.dumps(scenes, indent=2))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (out / "storyboard.md").write_text(_markdown(brief, assets, blocked))
    return manifest


def _markdown(brief: dict, assets: list[dict], blocked: list[dict]) -> str:
    lines = [f"# Storyboard: {brief['brand']} ({brief['platform']}, {brief['duration_s']}s)", ""]
    if blocked:
        lines += ["> **Needs human review:** " + "; ".join(
            f"scene {b['scene']} {b['field']}: {b['problem']}" for b in blocked), ""]
    lines += ["| # | sec | voiceover | on-screen | image prompt (score) |", "|---|---|---|---|---|"]
    for a in assets:
        lines.append(f"| {a['scene']} | {a['duration_s']} | {a['voiceover']['text']} | {a['on_screen_text']} | "
                     f"{a['image']['prompt']} ({a['image']['initial_score']} -> {a['image']['prompt_score']}) |")
    return "\n".join(lines) + "\n"
