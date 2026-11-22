#!/usr/bin/env bash
# Push the included multi-commit Git history to a newly created empty repository.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
REPO_URL="${1:-}"
if [[ -z "$REPO_URL" ]]; then
  echo 'Usage: ./publish-to-github.sh https://github.com/YOUR_USERNAME/folio-linux.git' >&2
  echo 'Create an EMPTY GitHub repository before running this script.' >&2
  exit 2
fi
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo 'Git history missing. Extract the full ZIP, including its hidden .git folder.' >&2
  exit 2
fi
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi
git branch -M main
printf 'Pushing source and %s preserved commits to %s\n' "$(git rev-list --count HEAD)" "$REPO_URL"
git push -u origin main
printf '\nDone. Your GitHub repository has the full source, files, and commit history.\n'
