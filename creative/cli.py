import argparse
import json

from . import llm, mock
from .pipeline import run


def main() -> None:
    llm.register_mock(mock.handler)
    p = argparse.ArgumentParser(prog="creative")
    p.add_argument("brief", nargs="?", default="brief.json")
    p.add_argument("--out", default="out")
    p.add_argument("--provider", default="mock")
    p.add_argument("--model", default="mock-large")
    p.add_argument("--rounds", type=int, default=2)
    p.add_argument("--live", action="store_true",
                   help="actually call ElevenLabs/OpenAI (needs ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, OPENAI_API_KEY)")
    args = p.parse_args()
    with open(args.brief) as f:
        brief = json.load(f)
    m = run(brief, args.out, args.live, args.provider, args.model, rounds=args.rounds)
    print(f"{m['note']}  |  LLM cost ${m['llm_cost_usd']:.6f}  |  human review needed: {m['needs_human_review']}\n")
    print(f"{'scene':<7}{'sec':<5}{'prompt score':<16}voiceover")
    for a in m["assets"]:
        print(f"{a['scene']:<7}{a['duration_s']:<5}{a['image']['initial_score']:>3} -> {a['image']['prompt_score']:<9}"
              f"{a['voiceover']['text'][:55]}")
    print(f"\nwrote {args.out}/storyboard.md, manifest.json, iterations.jsonl")


if __name__ == "__main__":
    main()
