#!/usr/bin/env bash
set -euo pipefail

# Official actionlint release; CI uses Ubuntu x86_64.
actionlint_version='1.7.12'
actionlint_digest='8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8'

main() {
  lint_directory=$(mktemp -d)
  trap 'rm -rf "$lint_directory"' EXIT
  download_actionlint
  verify_actionlint_archive
  run_actionlint
}

download_actionlint() {
  local releases='https://github.com/rhysd/actionlint/releases/download'
  local filename="actionlint_${actionlint_version}_linux_amd64.tar.gz"
  curl --fail --silent --show-error --location --retry 3 --max-time 60 \
    "$releases/v$actionlint_version/$filename" \
    --output "$lint_directory/actionlint.tar.gz"
}

verify_actionlint_archive() {
  printf '%s  %s\n' "$actionlint_digest" "$lint_directory/actionlint.tar.gz" |
    sha256sum --check
}

run_actionlint() {
  tar -xzf "$lint_directory/actionlint.tar.gz" -C "$lint_directory" actionlint
  "$lint_directory/actionlint" \
    -shellcheck='' -pyflakes='' .github/workflows/*.yml
}

main
