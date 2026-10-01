# Demo and screenshot plan

## 1. Record a GIF / Loom of the whole flow
```bash
bash demo.sh       # prints each command, pauses, runs it (PAUSE=0 bash demo.sh for an instant run)
```
Record it with any of: Loom (also good for the walkthrough video), [asciinema](https://asciinema.org) + `agg` to make a GIF,
[ScreenToGif](https://www.screentogif.com) (Windows) or [Kap](https://getkap.co) (macOS). Terminal tips: dark theme,
font size 18+, ~100 columns wide, short prompt (`export PS1='$ '`), and no personal paths or API keys on screen.

## 2. Hero screenshot
Capture `storyboard.md` rendered on GitHub (table of scenes with the prompt score going from 10 to 100), plus 2-3 generated images if you run `--live`.

Save as `docs/demo.png` (or `docs/demo.gif`) and add this under the first paragraph of the README:
```markdown
![demo](docs/demo.gif)
```

## 3. Things to point at while narrating
- `iterations.jsonl` is the prompt-iteration log: every candidate, score, and whether it was kept.
- Dry run is the default; `--live` only runs when compliance passes.
- The manifest records per-asset status, so one failed image doesn't lose the rest.

## 4. Before you publish
Run `--live` once and commit 2-3 of the best images into `docs/` for the README.
