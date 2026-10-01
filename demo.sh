#!/usr/bin/env bash
# Run with: bash demo.sh
# Recording helper: prints each command, then runs it. Use PAUSE=0 for an instant run.
set -e
PAUSE=${PAUSE:-1.5}
run() { echo; echo "\$ $*"; sleep "$PAUSE"; "$@"; sleep "$PAUSE"; }
run python -m creative brief.json --out out
run cat out/storyboard.md
run head -3 out/iterations.jsonl
