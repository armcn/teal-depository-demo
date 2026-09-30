#!/usr/bin/env bash
set -euo pipefail

main() {
  local message=$1
  cd storage
  configure_commit_identity
  git add -- site
  if git diff --cached --quiet; then
    echo 'No site changes to commit.'
    return
  fi
  commit_and_push_site "$message"
}

configure_commit_identity() {
  git config user.name 'github-actions[bot]'
  git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
}

commit_and_push_site() {
  git commit -m "$1"
  # Refuse concurrent edits. Never force push or resolve a conflict automatically.
  git push origin HEAD:published
}

main "$@"
