#!/usr/bin/env bash
# Commit state/ and push, retrying when a parallel company job pushed first.
# Each company writes only its own files, so the rebase never conflicts.
set -euo pipefail
git config user.name "job-alerts-bot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add state
if git diff --cached --quiet; then
  echo "no state changes"
  exit 0
fi
git commit -q -m "$1"
for i in 1 2 3 4 5 6; do
  if git pull -q --rebase && git push -q; then
    exit 0
  fi
  sleep $((RANDOM % 8 + 2))
done
echo "could not push state" >&2
exit 1
