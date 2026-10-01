# ai-creative-pipeline

[![CI](https://github.com/geocustomss/ai-creative-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/geocustomss/ai-creative-pipeline/actions/workflows/ci.yml)

From a one-paragraph brief to a compliance-checked storyboard, rubric-optimized image prompts, and (optionally) real
voiceover and image assets, with a manifest of exactly what was planned, created or failed.

The interesting part isn't "call an image API": it's the **prompt-iteration loop with a log**. Every candidate prompt,
its score and why it was kept or dropped is recorded in `iterations.jsonl`, so improvement is measurable instead of
guesswork. (The brand "Lumen Wellness" is fictional.)

```
brief.json ─► storyboard (LLM, validated: scene count, durations, words-per-second voiceover limit)
                  │
                  ├─► compliance check on voiceover / on-screen text / image prompts ─► flags "needs human review"
                  ▼
        per scene: score image prompt on a rubric ─► LLM rewrites what's missing ─► re-score ─► keep best compliant
                  ▼
        manifest.json + storyboard.md (+ iterations.jsonl)
                  ▼  --live only, and only if compliance passed
        ElevenLabs voiceover · OpenAI image generation   (a failed asset is recorded, not fatal)
```

## Quickstart (no API keys needed)

```bash
python -m unittest discover -s tests -v
python -m creative brief.json --out out          # dry run: writes the plan, calls no paid asset APIs
python -m creative brief.json --provider anthropic --model claude-haiku-4-5-20251001 --live   # real run
```

Live mode needs `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` and `OPENAI_API_KEY`. Output goes to `out/`
(`audio/`, `images/`, `storyboard.md`, `manifest.json`, `iterations.jsonl`).

## Sample run (mock model: shows the loop working, not real creative quality)

```
dry run: nothing generated  |  LLM cost $0.003250  |  human review needed: False

scene  sec  prompt score    voiceover
1      6     10 -> 100      Another night, scrolling instead of sleeping. Sound fam
2      6     10 -> 100      Lumen helps you build a gentle evening routine, one sma
3      6     10 -> 100      Dim the lights, breathe slowly, and let your day settle
4      6     10 -> 100      Members tell us evenings feel calmer and mornings less 
5      6     10 -> 100      Start your free week tonight.

wrote out/storyboard.md, manifest.json, iterations.jsonl
```

The rubric scores camera, lighting, style, length, "no text baked into the image" and 9:16 framing. A weak starter
prompt scores 10; the loop reports what's missing and asks for rewrites targeting only those gaps.

## Design decisions

- **Dry run is the default.** Paid APIs are only called with `--live`, and only when the storyboard passes compliance.
- **Hard rules versus soft scores.** A candidate with a prohibited element (pills, logos, before/after) can never be
  kept, however well it scores. This is tested with an adversarial model reply.
- **Voiceover length is validated against scene duration** (2.5 words/second), so scripts don't overrun the video.
- **Partial failure is normal.** One rate-limited image shouldn't lose the other nine; the manifest records per-asset status.
- **Text is overlaid, not generated.** Image models are unreliable at text, so the rubric penalizes text in the image
  and the storyboard carries `on_screen_text` separately.

## Limitations / next steps

- The rubric is a proxy. Close the loop with real signals: human ratings, then ad performance by creative variant.
- Add a video step (e.g. Higgsfield or another video model) and assemble the final cut with ffmpeg.
- Provider adapters follow public REST docs but aren't covered by tests (no keys in CI); verify against current docs.
- The compliance lists are illustrative; ad platforms' policies change, and health categories need legal review.
