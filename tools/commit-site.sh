#!/usr/bin/env bash
set -euo pipefail
cd storage
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add -- site
if git diff --cached --quiet; then
  echo 'No site changes to commit.'
  exit 0
fi
git commit -m "$1"
# No force push and no automatic conflict resolution. A concurrent manual write fails closed.
git push origin HEAD:published
